"""Macro tables recomputed exclusively from validated per-query records."""
from collections import defaultdict


def aggregate(records):
    records = list(records)
    identities = {(r.experiment_id, r.config_hash, r.provenance.get('benchmark_manifest_sha256'),
                   r.provenance.get('representation_manifest_sha256'), r.provenance.get('dataset_version'),
                   r.provenance.get('benchmark')) for r in records}
    if len(identities) > 1 or len({r.query_id for r in records}) != len(records):
        raise ValueError('Cannot aggregate mixed versions/configurations or duplicate queries')
    groups = defaultdict(list)
    for r in records:
        names = ['overall', 'source/' + r.source_type, 'split/' + r.split,
                 'modality/' + r.labels.modality, 'hop/' + r.labels.hop]
        if r.source_type in ('official_synthetic', 'official_human'):
            names.append('official_overall')
        if r.source_type == 'generated':
            names.append('generated_controlled')
        if r.split == 'human_test':
            names.append('human_test')
        names += ['stress/' + s for s in r.stress]
        names += ['source_modality/' + r.source_type + '/' + r.labels.modality,
                  'split_source/' + r.split + '/' + r.source_type]
        for name in names:
            groups[name].append(r)
    rows = []
    for name, items in sorted(groups.items()):
        metrics = sorted({key for r in items for key in r.metrics})
        for metric in metrics:
            values = [r.metrics[metric] for r in items if r.metrics.get(metric) is not None]
            rows.append({'cohort': name, 'metric': metric, 'n_queries': len(items),
                         'n_errors': sum(bool(r.errors) for r in items), 'n_available': len(values),
                         'n_null': len(items) - len(values), 'mean': sum(values) / len(values) if values else None})
    return rows
