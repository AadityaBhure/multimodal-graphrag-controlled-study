"""Frozen Phase 9 train/dev partition (addendum §2.1): SHA-256 of query_id, 90 % train / 10 % dev.

Eligible pool: official-synthetic train + generated train. Validation, official validation,
test and human-test never enter this pool.
"""
import hashlib

PARTITION_VERSION = 'phase9-ar01-partition-v1'


def bucket(query_id):
    return int(hashlib.sha256(query_id.encode('utf-8')).hexdigest()[:16], 16) % 100


def is_dev(query_id):
    return bucket(query_id) < 10


def build(reader):
    pool = [q for q in reader.records('train')]
    train, dev = [], []
    for q in pool:
        (dev if is_dev(q.query_id) else train).append(q.query_id)
    families = {}
    for q in pool:
        if q.provenance['source'] == 'generated':
            families.setdefault(q.query_id.rsplit(':', 1)[0], set()).add('dev' if is_dev(q.query_id) else 'train')
    straddling = sorted(f for f, s in families.items() if len(s) == 2)
    return {'version': PARTITION_VERSION, 'rule': 'dev iff int(sha256(query_id)[:16],16) % 100 < 10',
            'pool_size': len(pool), 'train': sorted(train), 'dev': sorted(dev),
            'generated_families': len(families), 'generated_families_straddling_train_dev': straddling}
