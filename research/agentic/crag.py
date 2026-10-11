"""AR-02 CRAG-inspired corrective retrieval (Phase 1D §6.3 + addendum §3).

Local MiniLM cross-encoder -> Platt-calibrated probabilities -> GOOD / AMBIGUOUS / BAD with thresholds frozen from a
dev-partition grid search. No web, no strip refinement, no training of the evaluator.
"""
import itertools
import json
import math
from pathlib import Path
from research.agentic.policies import Policy
from research.agentic.rule_router import first_source, next_unqueried, SOURCE_ORDER
from research.agentic.evidence import render

LOWER_GRID = (0.20, 0.25, 0.30, 0.35, 0.40)
UPPER_GRID = (0.60, 0.65, 0.70, 0.75, 0.80)
MAX_CORRECTION_ROUNDS = 2
MAX_PAIR_LENGTH = 512
STATES = ('GOOD', 'AMBIGUOUS', 'BAD')


class CrossEncoderEvaluator:
    """Deterministic local scoring of (query, evidence text) pairs; batch size 1, fixed threads."""
    def __init__(self, model_dir, threads=2):
        self.model_dir, self.threads, self.model, self.tokenizer = Path(model_dir), threads, None, None
        self.config = json.loads((self.model_dir / 'config.json').read_text(encoding='utf-8'))
        from research.evaluation.benchmark import digest
        self.fingerprint = {p.name: digest(p) for p in sorted(self.model_dir.iterdir()) if p.is_file() and p.suffix in ('.safetensors', '.json', '.txt')}

    def load(self):
        if self.model is not None:
            return
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        torch.set_num_threads(self.threads)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir, local_files_only=True, dtype=torch.float32).eval()

    def raw_scores(self, query, texts):
        self.load()
        import torch
        out = []
        with torch.inference_mode():
            for text in texts:
                enc = self.tokenizer(query, text, truncation=True, max_length=MAX_PAIR_LENGTH, return_tensors='pt')
                out.append(float(self.model(**enc).logits.reshape(-1)[0]))
        return out


class Platt:
    def __init__(self, coef, intercept):
        self.coef, self.intercept = float(coef), float(intercept)

    def prob(self, raw):
        z = self.coef * raw + self.intercept
        return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))

    @staticmethod
    def fit(raw_scores, labels):
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        x = np.asarray(raw_scores, dtype=float).reshape(-1, 1)
        model = LogisticRegression(solver='lbfgs', C=1.0, class_weight='balanced', max_iter=1000, random_state=42).fit(x, np.asarray(labels, dtype=int))
        return Platt(model.coef_[0][0], model.intercept_[0])


def classify(probs, lower, upper):
    """Phase 1D rule. Empty evidence is BAD."""
    if not probs:
        return 'BAD'
    if max(probs) >= upper:
        return 'GOOD'
    if all(p <= lower for p in probs):
        return 'BAD'
    return 'AMBIGUOUS'


def macro_f1(truth, pred):
    f1s = []
    for c in STATES:
        tp = sum(t == c and p == c for t, p in zip(truth, pred)); fp = sum(t != c and p == c for t, p in zip(truth, pred))
        fn = sum(t == c and p != c for t, p in zip(truth, pred))
        f1s.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.)
    return sum(f1s) / len(f1s)


def fit_thresholds(samples):
    """samples: [(truth_state, [calibrated probs])]. Grid search with the addendum's exact tie-break chain."""
    truth = [s[0] for s in samples]
    rows = []
    for lower, upper in itertools.product(LOWER_GRID, UPPER_GRID):
        if not lower < upper:
            continue
        pred = [classify(s[1], lower, upper) for s in samples]
        rows.append({'lower': lower, 'upper': upper, 'macro_f1': macro_f1(truth, pred),
                     'errors': sum(t != p for t, p in zip(truth, pred)), 'margin': round(upper - lower, 10)})
    best = sorted(rows, key=lambda r: (-r['macro_f1'], r['errors'], -r['margin'], r['lower'], r['upper']))[0]
    return best, rows


class CorrectiveRAG(Policy):
    def __init__(self, *args, evaluator, platt, lower, upper, calibration_hash='unbound', **kw):
        self.evaluator, self.platt, self.lower, self.upper, self.calibration_hash = evaluator, platt, lower, upper, calibration_hash
        super().__init__(*args, **kw)

    def fingerprint_parts(self):
        return {'evaluator': self.evaluator.fingerprint, 'platt': [self.platt.coef, self.platt.intercept], 'lower': self.lower,
                'upper': self.upper, 'calibration': self.calibration_hash, 'rounds': MAX_CORRECTION_ROUNDS}

    def evaluate(self, request, memory):
        items = memory.ordered()
        if not items:
            return 'BAD', [], [], False
        try:
            raw = self.evaluator.raw_scores(request.question, [render(e) for e in items])
            probs = [self.platt.prob(r) for r in raw]
            return classify(probs, self.lower, self.upper), raw, probs, False
        except Exception:                                   # Phase 1D: evaluator failure => AMBIGUOUS
            return 'AMBIGUOUS', [], [], True

    def run(self, request, memory, trace):
        q = request.question
        self.retrieve(request, memory, trace, 1, first_source(q), q, reason='initial_router_source')
        rounds, step = 0, 1
        while True:
            state, raw, probs, failed = self.evaluate(request, memory)
            trace.events.append({'kind': 'evaluation', 'round': rounds, 'state': state, 'evaluator_failed': failed, 'evidence_ids': [e.evidence_id for e in memory.ordered()],
                                 'raw_scores': raw, 'calibrated': probs, 'lower': self.lower, 'upper': self.upper})
            trace.extra['last_state'] = state
            if state == 'GOOD':
                trace.stop_reason = 'good'
                return {'kind': 'generate'}
            remaining = [s for s in SOURCE_ORDER if s not in trace.queried]
            if rounds >= MAX_CORRECTION_ROUNDS:
                trace.stop_reason = 'max_correction_rounds'
                break
            if not remaining:
                trace.stop_reason = 'sources_exhausted'
                break
            if state == 'AMBIGUOUS':
                add = [next_unqueried(q, trace.queried)]
            else:                                           # BAD: all remaining unqueried sources, deterministic T->G->S order
                add = remaining
            for source in add:
                step += 1
                self.retrieve(request, memory, trace, step, source, q, reason='correction_' + state.lower())
            rounds += 1
        if trace.extra['last_state'] == 'BAD':
            trace.status = 'insufficient_evidence'          # recorded; the shared generator still produces the (likely empty) answer
        return {'kind': 'generate'}
