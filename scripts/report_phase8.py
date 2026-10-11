"""Recompute cohort tables, fusion diagnostics and descriptive Pareto candidates."""
import csv
import io
import json
import statistics
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_phase8 import D
from research.rq2.contracts import METHODS, SOURCES
from research.evaluation.contracts import RunRecord
from research.evaluation.aggregate import aggregate
from research.experiments.runner import write
from research.evaluation.metrics import retrieval_metrics
from research.rq2.fusion import paper_id

def export(name, rows):
    write(D / (name + '.json'), rows)
    if not rows: return
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows({k: 'NULL' if v is None else v for k, v in row.items()} for row in rows)
    (D / (name + '.csv')).write_text(stream.getvalue(), encoding='utf-8', newline='')

def mean(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    return statistics.mean(values) if values else None

def frontier(rows, quality, cost):
    valid = [row for row in rows if row.get(quality) is not None and row.get(cost) is not None]
    return [row['method'] for row in valid if not any(other[quality] >= row[quality] and other[cost] <= row[cost]
        and (other[quality] > row[quality] or other[cost] < row[cost]) for other in valid)]

def main():
    for mode in ('context_only', 'generation'):
        if not (D / mode).exists(): continue
        tables, per_query, summary, examples = [], [], [], []
        for method in METHODS:
            path = D / mode / method / 'records.jsonl'
            if not path.exists(): continue
            records = [RunRecord.model_validate_json(line) for line in path.read_text(encoding='utf-8').splitlines()]
            tables.extend({'method': method, **row} for row in aggregate(records))
            method_rows = []
            for record in records:
                d = json.loads(record.output.diagnostics)
                row = {'method': method, 'query_id': record.query_id, 'modality': record.labels.modality,
                    'complexity': record.labels.hop, 'stress': '+'.join(record.stress), 'errors': len(record.errors),
                    'gold_count': len(record.gold_ids), 'gold_coverage': record.metrics['gold_coverage'],
                    'recall@5': record.metrics['recall@5'], 'mrr': record.metrics['mrr'],
                    'answer_f1': record.metrics['f1'], 'set_accuracy': record.metrics['set_accuracy'],
                    'context_characters': record.metrics['context_characters'],
                    'prepared_context_characters': d.get('prepared_context_characters'),
                    'fusion_ms': d['fusion_ms'], 'generation_ms': record.observation.generation_ms,
                    'total_ms': record.total_latency_ms, 'llm_calls': record.observation.llm_calls,
                    'input_tokens': record.observation.input_tokens, 'output_tokens': record.observation.output_tokens,
                    'retained_overlay_count': len(d['retained_overlay_ids']),
                    'unresolved_count': d.get('unresolved_count'), 'entity_alignment_correctness': None,
                    'conflict_handling_accuracy': None}
                kept_ids = set(record.output.retained_evidence_ids or ())
                retained = [e for e in record.output.evidence if e.evidence_id in kept_ids]
                canonical_papers = [paper_id(e) for e in retained if paper_id(e) is not None and json.loads(e.metadata).get('origin') != 'phase4_evaluation_overlay']
                row['gold_coverage_without_overlay'] = retrieval_metrics(canonical_papers, record.gold_ids, (5,))['gold_coverage'] if record.output.retained_evidence_ids is not None else None
                row['alignment_count'] = len(d['alignments']) if method == 'CF-01' else None
                row['cross_source_groups'] = sum(len({e.source_type for e in record.output.evidence if e.evidence_id in ids}) > 1 for ids in d.get('groups', {}).values()) if method == 'CF-01' else None
                for source in SOURCES:
                    row[source + '_count'] = d['source_counts'][source]
                    row[source + '_coverage'] = d['source_coverage'][source]
                    row[source + '_entity_redundancy'] = d['source_entity_redundancy'][source]
                row['source_coverage_mean'] = mean([{'v': row[s + '_coverage']} for s in SOURCES], 'v')
                row['token_total'] = (row['input_tokens'] + row['output_tokens']) if row['input_tokens'] is not None and row['output_tokens'] is not None else None
                per_query.append(row); method_rows.append(row)
            numeric = [k for k in method_rows[0] if k not in ('method', 'query_id', 'modality', 'complexity', 'stress')]
            summary.append({'method': method, 'queries': len(records), **{k: mean(method_rows, k) for k in numeric}})
            available = sorted((r for r in records if r.metrics['gold_coverage'] is not None), key=lambda r: (r.metrics['gold_coverage'], r.query_id))
            for kind, r in [('lowest_coverage', available[0]), ('highest_coverage', available[-1])] if available else []:
                examples.append({'method': method, 'kind': kind, 'query_id': r.query_id,
                    'gold_coverage': r.metrics['gold_coverage'], 'evidence_ids': r.output.retained_evidence_ids,
                    'note': 'retained-paper coverage, not generated-answer success' if mode == 'context_only' else 'inspect answer metrics separately'})
        export(mode + '_cohorts', tables)
        export(mode + '_per_query', per_query)
        export(mode + '_summary', summary)
        export(mode + '_representative_cases', examples)
        supplemental = []
        for method in METHODS:
            own = [r for r in per_query if r['method'] == method]
            if not own: continue
            for dimension in ('modality', 'complexity', 'stress'):
                for value in sorted({r[dimension] for r in own}):
                    subset = [r for r in own if r[dimension] == value]
                    for metric in ('source_coverage_mean', 'fusion_ms', 'retained_overlay_count', 'unresolved_count') + tuple(s + '_coverage' for s in SOURCES):
                        supplemental.append({'method': method, 'dimension': dimension, 'cohort': value,
                            'metric': metric, 'queries': len(subset), 'mean': mean(subset, metric),
                            'available': sum(r[metric] is not None for r in subset), 'null': sum(r[metric] is None for r in subset)})
        export(mode + '_fusion_cohorts', supplemental)
        pareto = []
        for quality, cost in [('gold_coverage', 'context_characters'), ('gold_coverage', 'fusion_ms'),
            ('source_coverage_mean', 'context_characters'), ('answer_f1', 'context_characters'),
            ('answer_f1', 'total_ms'), ('answer_f1', 'llm_calls'), ('answer_f1', 'token_total'),
            ('conflict_handling_accuracy', 'context_characters')]:
            candidates = frontier(summary, quality, cost)
            for row in summary:
                available = row.get(quality) is not None and row.get(cost) is not None
                pareto.append({'quality': quality, 'cost': cost, 'method': row['method'],
                    'quality_value': row.get(quality), 'cost_value': row.get(cost),
                    'pareto_candidate': row['method'] in candidates if available else None,
                    'status': 'descriptive_only' if available else 'unavailable'})
        export(mode + '_pareto', pareto)
        if mode == 'context_only':
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
            for axis, cost, label in zip(axes, ('context_characters', 'fusion_ms'), ('Mean context characters', 'Mean fusion time (ms)')):
                for row in summary:
                    if row['gold_coverage'] is not None:
                        axis.scatter(row[cost], row['gold_coverage'], label=row['method'])
                        axis.annotate(row['method'], (row[cost], row['gold_coverage']), xytext=(4, 5), textcoords='offset points', fontsize=8)
                axis.set_xlabel(label); axis.set_ylabel('Mean retained-paper gold coverage'); axis.grid(alpha=.2)
            fig.suptitle('24 paired validation queries; includes stress overlays; no generated answers\nCF-03 unavailable until generation; this is not an answer-quality ranking', fontsize=10)
            fig.tight_layout(); fig.savefig(D / 'context_only_pareto.png', dpi=160); plt.close(fig)
    print('Comparison tables regenerated from runner records; NULL values explicit')

if __name__ == '__main__': main()
