"""Hash-verified read-only benchmark adapter and separate release gate."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from research.benchmark.contracts import BenchmarkQuery
from research.evaluation.contracts import ReleaseMetadata
from research.common.serialization import canonical_json


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


class BenchmarkReader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.manifest_path = self.root / 'benchmark_manifest.json'
        self.manifest_hash = digest(self.manifest_path)
        self.manifest = read_json(self.manifest_path)
        if self.manifest.get('content_frozen') is not True:
            raise ValueError('Benchmark must be frozen')
        self.files = {r['path']: r for r in self.manifest['files']}

    def verified_path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or relative not in self.files:
            raise ValueError('Unknown or escaping benchmark path')
        entry = self.files[relative]
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('Frozen benchmark file checksum mismatch: ' + relative)
        return path

    def records(self, split):
        relative = split + '.jsonl'
        path = self.verified_path(relative)
        if self.files[relative]['sha256'] != self.manifest['query_file_sha256'][split]:
            raise ValueError('Split hash disagrees with manifest')
        seen = set()
        with path.open(encoding='utf-8') as f:
            for line in f:
                q = BenchmarkQuery.model_validate_json(line)
                if q.query_id in seen or q.split != split:
                    raise ValueError('Duplicate query or wrong split')
                seen.add(q.query_id)
                yield q

    def overlay(self, query):
        relative = query.provenance.get('stress_record')
        if not relative:
            return None
        source = read_json(self.verified_path(relative))
        if source.get('canonical_data_modified') is not False:
            raise ValueError('Overlay may not modify canonical data')
        # Grading instructions, authoritative answers and counterexamples are never passed to a system.
        if query.stress.conflict:
            payload = {k: source[k] for k in ('source', 'paper_id', 'field', 'after', 'mutated_conflicting_evidence')}
            return canonical_json({'kind': 'conflict', 'injection': payload, 'canonical_data_modified': False})
        if query.stress.noisy:
            distractors = {kind: [{k: v for k, v in row.items() if k in ('paper_id', 'path')} for row in rows]
                           for kind, rows in source['distractors'].items()}
            return canonical_json({'kind': 'noisy', 'distractors': distractors, 'canonical_data_modified': False})
        raise ValueError('Unexpected stress overlay')


def release_gate(reader, release_path):
    if release_path is None:
        raise ValueError('Paper test requires separate review/release metadata')
    release = ReleaseMetadata.model_validate(read_json(release_path)).model_dump(mode='json')
    required = {q.query_id for split in ('test', 'human_test') for q in reader.records(split)}
    if (release.get('benchmark_manifest_sha256') != reader.manifest_hash or
        release.get('test_content_freeze_id') != reader.manifest['test_content_freeze_id'] or
        release.get('status') != 'released' or release.get('leakage_adjudicated') is not True or
        not str(release.get('released_by', '')).strip()):
        raise ValueError('Release status/binding/leakage adjudication missing or invalid')
    decisions = release.get('decisions', [])
    seen = set()
    for d in decisions:
        qid = d.get('query_id')
        if qid in seen:
            raise ValueError('Duplicate review decision')
        seen.add(qid)
        if qid in required:
            if d.get('decision') != 'pass' or not str(d.get('reviewer', '')).strip() or not str(d.get('reason', '')).strip():
                raise ValueError('Every test and human-test query needs attributed passing review')
            stamp = datetime.fromisoformat(d.get('reviewed_at', ''))
            if stamp.tzinfo is None:
                raise ValueError('Review timestamp needs timezone')
    if not required <= seen:
        raise ValueError('100% test and human-test verification required')
    return {'sha256': digest(release_path), 'required': len(required), 'verified': len(required),
            'status': 'released', 'released_by': release['released_by']}
