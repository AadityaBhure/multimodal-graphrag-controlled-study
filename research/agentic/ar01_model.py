"""AR-01 t5-base route classifier (A/B/C): training per addendum §2.2 and deterministic inference."""
import json
import random
from pathlib import Path
from research.common.serialization import canonical_json, content_hash

LABELS = ('A', 'B', 'C')
MAX_SOURCE, MAX_TARGET = 256, 2
HYPER = {'lr': 3e-5, 'weight_decay': 0.01, 'seed': 42, 'max_epochs': 10, 'patience': 2, 'batch_size': 16,
         'max_source_length': MAX_SOURCE, 'max_target_length': MAX_TARGET, 'label_smoothing': 0.0, 'optimizer': 'AdamW'}


def _seed(seed):
    import numpy as np, torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(False)


def _batches(pairs, tokenizer, batch_size, shuffle, seed):
    import torch
    order = list(range(len(pairs)))
    if shuffle:
        random.Random(seed).shuffle(order)
    for i in range(0, len(order), batch_size):
        chunk = [pairs[j] for j in order[i:i + batch_size]]
        enc = tokenizer([q for q, _ in chunk], max_length=MAX_SOURCE, truncation=True, padding=True, return_tensors='pt')
        lab = tokenizer([l for _, l in chunk], max_length=MAX_TARGET, truncation=True, padding=True, return_tensors='pt').input_ids
        lab[lab == tokenizer.pad_token_id] = -100
        yield enc, lab


def train(model_dir, train_pairs, dev_pairs, out_dir, threads=10, log=print, max_epochs=None, device='auto'):
    """train_pairs/dev_pairs: [(question, 'A'|'B'|'C')]. Returns the training report (also written to out_dir).
    device='auto' uses CUDA when available (float32, same recipe); the device is recorded in the report."""
    import torch
    from transformers import T5ForConditionalGeneration, AutoTokenizer
    torch.set_num_threads(threads); _seed(HYPER['seed'])
    dev = torch.device('cuda' if device == 'auto' and torch.cuda.is_available() else ('cpu' if device == 'auto' else device))
    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = T5ForConditionalGeneration.from_pretrained(model_dir, local_files_only=True, dtype=torch.float32).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=HYPER['lr'], weight_decay=HYPER['weight_decay'])
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    counts = {c: sum(1 for _, l in train_pairs if l == c) for c in LABELS}
    dcounts = {c: sum(1 for _, l in dev_pairs if l == c) for c in LABELS}
    report = {'hyper': HYPER, 'train_counts': counts, 'dev_counts': dcounts, 'epochs': [], 'best_epoch': None, 'stopped': None,
              'device': str(dev), 'gpu': torch.cuda.get_device_name(0) if dev.type == 'cuda' else None}
    best, bad = float('inf'), 0
    limit = max_epochs or HYPER['max_epochs']
    report['max_epochs_used'] = limit
    for epoch in range(1, limit + 1):
        model.train(); tl, n = 0., 0
        for enc, lab in _batches(train_pairs, tok, HYPER['batch_size'], True, HYPER['seed'] + epoch):
            enc, lab = enc.to(dev), lab.to(dev)
            loss = model(**enc, labels=lab).loss
            loss.backward(); opt.step(); opt.zero_grad()
            tl += float(loss) * lab.shape[0]; n += lab.shape[0]
        model.eval(); dl, dn = 0., 0
        with torch.inference_mode():
            for enc, lab in _batches(dev_pairs, tok, 32, False, 0):
                enc, lab = enc.to(dev), lab.to(dev)
                dl += float(model(**enc, labels=lab).loss) * lab.shape[0]; dn += lab.shape[0]
        row = {'epoch': epoch, 'train_loss': tl / n, 'dev_loss': dl / dn}
        report['epochs'].append(row); log('EPOCH', row, flush=True)
        if row['dev_loss'] < best - 1e-12:
            best, bad = row['dev_loss'], 0; report['best_epoch'] = epoch
            model.save_pretrained(out / 'best', safe_serialization=True); tok.save_pretrained(out / 'best')
        else:
            bad += 1
            if bad >= HYPER['patience']:
                report['stopped'] = 'early_stopping_patience_%d' % HYPER['patience']; break
        (out / 'training_report.json').write_text(canonical_json(report) + '\n', encoding='utf-8', newline='\n')
    report['stopped'] = report['stopped'] or 'max_epochs'
    (out / 'training_report.json').write_text(canonical_json(report) + '\n', encoding='utf-8', newline='\n')
    return report


class T5Router:
    """Deterministic greedy inference; invalid decoded output is reported as invalid (policy falls back to B)."""
    def __init__(self, model_dir, threads=2):
        self.model_dir, self.threads, self.model, self.tok = Path(model_dir), threads, None, None
        from research.evaluation.benchmark import digest
        self.fingerprint = {p.name: digest(p) for p in sorted(self.model_dir.iterdir()) if p.is_file()}

    def load(self):
        if self.model is not None:
            return
        import torch
        from transformers import T5ForConditionalGeneration, AutoTokenizer
        torch.set_num_threads(self.threads)
        self.tok = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        self.model = T5ForConditionalGeneration.from_pretrained(self.model_dir, local_files_only=True, dtype=torch.float32).eval()
        self.ids = [self.tok(c, add_special_tokens=False).input_ids[0] for c in LABELS]

    def predict(self, question):
        self.load()
        import torch
        enc = self.tok(question, max_length=MAX_SOURCE, truncation=True, return_tensors='pt')
        with torch.inference_mode():
            gen = self.model.generate(**enc, max_new_tokens=MAX_TARGET, do_sample=False, num_beams=1)
            start = torch.full((1, 1), self.model.config.decoder_start_token_id)
            logits = self.model(**enc, decoder_input_ids=start).logits[0, -1]
        probs = torch.softmax(logits[self.ids], dim=0).tolist()
        text = self.tok.decode(gen[0], skip_special_tokens=True).strip()
        return {'label': text if text in LABELS else None, 'raw': text, 'valid': text in LABELS,
                'probs': dict(zip(LABELS, probs))}
