"""Single deterministic, resumable runner. No baseline or research algorithms."""
from datetime import datetime, timezone
from importlib.metadata import version
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import time
from filelock import FileLock
from research.common.config import PROJECT_ROOT
from research.common.contracts import MethodError
from research.common.reproducibility import seed_everything
from research.common.serialization import canonical_json, content_hash
from research.evaluation.aggregate import aggregate
from research.evaluation.benchmark import BenchmarkReader, digest, read_json, release_gate
from research.evaluation.contracts import RunRecord, RunEvent, SystemInput, SystemOutput, Observation, VerifiedLabels
from research.evaluation.metrics import answer_metrics, retrieval_metrics, context_metrics, coverage, AGENT_METRICS
from research.experiments.config import durable_write


def now():
    return datetime.now(timezone.utc)


def write(path, value):
    durable_write(path, canonical_json(value) + '\n')


def code_provenance():
    commit = subprocess.check_output(['git', '-c', f'safe.directory={PROJECT_ROOT.as_posix()}',
                                      'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, text=True).strip()
    files = sorted((PROJECT_ROOT / 'research').rglob('*.py')) + [PROJECT_ROOT / 'scripts/run_experiment.py']
    hashes = {p.relative_to(PROJECT_ROOT).as_posix(): digest(p) for p in files if p.exists()}
    return {'git_commit': commit, 'source_sha256': hashes, 'source_tree_hash': content_hash(hashes),
            'python_version': sys.version, 'packages': {name: version(name) for name in ('pydantic', 'numpy', 'PyYAML', 'filelock')}}


def compute_metrics(q, output, config, elapsed):
    result = answer_metrics(output.answer_ids if output else None, q.gold_answer_ids)
    result.update(retrieval_metrics(output.ranked_paper_ids if output else None, q.gold_answer_ids, config.ks))
    result.update(context_metrics(output.context if output else None,
        [e.evidence_id for e in output.evidence] if output and output.evidence is not None else None,
        output.retained_evidence_ids if output else None,
        tokens=output.context_tokens if output else None, tokenizer=output.tokenizer if output else None,
        baseline_characters=output.baseline_context_characters if output else None))
    # A paper answer is not an evidence annotation. Current benchmark does not supply this key.
    required_evidence = q.gold_evidence.get('evidence_ids')
    result['evidence_coverage'] = coverage([e.evidence_id for e in output.evidence] if output and output.evidence is not None else None, required_evidence)
    observation = output.observation if output else Observation()
    result.update({name: getattr(observation, name) for name in ('retrieval_ms', 'generation_ms',
        'retrieval_calls', 'tool_calls', 'llm_calls', 'input_tokens', 'output_tokens')})
    result['total_ms'] = elapsed
    result['estimated_cost'] = None
    if config.pricing and observation.input_tokens is not None and observation.output_tokens is not None:
        result['estimated_cost'] = (observation.input_tokens * config.pricing.input_per_million +
                                    observation.output_tokens * config.pricing.output_per_million) / 1e6
    result.update(dict.fromkeys(AGENT_METRICS + ('answer_relevance', 'faithfulness'))) 
    return result


def labels(q):
    verified = q.provenance.get('source') == 'generated' and q.modality_class != 'unverified' and q.reasoning.hop_count is not None
    return VerifiedLabels(modality=q.modality_class if verified else 'unverified',
        hop=q.reasoning.complexity if verified else 'unverified', hop_count=q.reasoning.hop_count if verified else None,
        status='programmatically_verified' if verified else 'unverified',
        human_review_status=q.provenance.get('annotation_status', 'unverified'))


def run(config, benchmark_root, output_dir, system, *, release_path=None, provenance=None):
    if (system.system_id, system.version) != (config.system_id, config.system_version):
        raise ValueError('System implementation/config mismatch')
    reader = BenchmarkReader(benchmark_root)
    output_dir = Path(output_dir).resolve()
    protected = [reader.root, PROJECT_ROOT / 'data', PROJECT_ROOT / 'storage']
    if any(output_dir.is_relative_to(p.resolve()) or p.resolve().is_relative_to(output_dir) for p in protected):
        raise ValueError('Experiment output overlaps protected data')
    release = release_gate(reader, release_path) if config.mode == 'paper_test' else None
    queries = [q for split in config.splits for q in reader.records(split)]
    if len({q.query_id for q in queries}) != len(queries):
        raise ValueError('Cross-split duplicate query ID')
    if config.query_ids:
        wanted = set(config.query_ids)
        queries = [q for q in queries if q.query_id in wanted]
        if {q.query_id for q in queries} != wanted:
            raise ValueError('Unknown selected query ID')
    if not queries:
        raise ValueError('Empty experiment')
    queries.sort(key=lambda q: (q.split, q.query_id))
    representation_path = reader.root.parent / 'manifest.json'
    dataset_version = 'synthetic-fixture-only'
    if representation_path.exists():
        if digest(representation_path) != reader.manifest['representation_manifest_sha256']:
            raise ValueError('Representation manifest binding mismatch')
        dataset_version = read_json(representation_path)['dataset_version']
    identity = {'system_fingerprint': system.fingerprint, 'dataset_version': dataset_version, 'expected_query_count': len(queries), 'config': config.model_dump(mode='json'), 'config_hash': content_hash(config.model_dump(mode='json')),
        'benchmark_manifest_sha256': reader.manifest_hash, 'benchmark_version': reader.manifest['benchmark_version'],
        'representation_manifest_sha256': reader.manifest['representation_manifest_sha256'],
        'query_selection_sha256': content_hash([q.query_id for q in queries]),
        'code': provenance if provenance is not None else code_provenance(), 'release': release}
    manifest = {'experiment_id': 'exp-' + content_hash(identity), **identity}
    output_dir.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output_dir / 'run.lock'), timeout=0):
        manifest_path = output_dir / 'manifest.json'
        if manifest_path.exists():
            if read_json(manifest_path) != manifest:
                raise ValueError('Incompatible existing experiment; refusing overwrite')
        else:
            if any(p.name != 'run.lock' for p in output_dir.iterdir()):
                raise ValueError('Nonempty unowned experiment directory')
            write(manifest_path, manifest)
        records_dir = output_dir / 'records'
        events_dir = output_dir / 'events'
        records_dir.mkdir(exist_ok=True)
        events_dir.mkdir(exist_ok=True)
        event_files = sorted(events_dir.glob('*.json'))
        if [p.name for p in event_files] != [f'{i:08d}.json' for i in range(len(event_files))]:
            raise ValueError('Event sequence is incomplete')
        event_number = len(event_files)
        def event(kind, qid, **details):
            nonlocal event_number
            obj = RunEvent(timestamp=now(), experiment_id=manifest['experiment_id'], query_id=qid, event=kind, details=details)
            write(events_dir / f'{event_number:08d}.json', obj.model_dump(mode='json'))
            event_number += 1
        seed_report = seed_everything(config.seed)
        expected_files = {content_hash(q.query_id) + '.json' for q in queries}
        if any(p.name not in expected_files for p in records_dir.glob('*.json')):
            raise ValueError('Unexpected saved query record')
        try:
            for q in queries:
                target = records_dir / (content_hash(q.query_id) + '.json')
                pending = output_dir / 'pending.json'
                if target.exists():
                    record = RunRecord.model_validate_json(target.read_text(encoding='utf-8'))
                    if record.experiment_id != manifest['experiment_id'] or record.query_id != q.query_id or record.gold_ids != q.gold_answer_ids or record.config_hash != identity['config_hash'] or record.provenance.get('query_sha256') != content_hash(q.model_dump(mode='json')):
                        raise ValueError('Saved record identity mismatch')
                    if pending.exists() and read_json(pending)['query_id'] == q.query_id:
                        event('completed', q.query_id, recovered_committed_record=True)
                        pending.unlink()
                    continue
                if pending.exists():
                    interrupted = read_json(pending)
                    event('recovered_interruption', interrupted['query_id'], previous_start=interrupted['timestamp'])
                    pending.unlink()
                query_seed = int(content_hash({'seed': config.seed, 'query_id': q.query_id})[:8], 16)
                seed_everything(query_seed)
                write(pending, {'query_id': q.query_id, 'timestamp': now().isoformat()})
                event('started', q.query_id)
                started = time.perf_counter()
                output = None
                errors = ()
                try:
                    request = SystemInput(query_id=q.query_id, question=q.question, seed=query_seed, overlay=reader.overlay(q))
                    output = SystemOutput.model_validate(system.execute(request))
                    errors = output.errors
                except Exception as exc:
                    # Do not leak arbitrary exception messages (API keys/provider payloads) to artifacts.
                    errors = (MethodError(stage='execute', code=type(exc).__name__, message='System execution failed; inspect local system diagnostics'),)
                except BaseException:
                    event('interrupted', q.query_id)
                    raise
                elapsed = (time.perf_counter() - started) * 1000
                record = RunRecord(experiment_id=manifest['experiment_id'], timestamp=now(), query_id=q.query_id,
                    split=q.split, source_type=q.provenance['source'], labels=labels(q),
                    stress=tuple(name for name in ('noisy','conflict','unanswerable') if getattr(q.stress,name)) or ('normal',),
                    system_id=config.system_id, config_id=config.config_id, config_hash=identity['config_hash'],
                    model_ids=config.model_ids, embedding_model=config.embedding_model, seed=config.seed, query_seed=query_seed,
                    retrieval_parameters=config.retrieval_parameters, evidence_ids=tuple(e.evidence_id for e in (output.evidence or ())) if output else (),
                    answer=output.answer if output else None, answer_ids=output.answer_ids if output else None,
                    gold_ids=q.gold_answer_ids, output=output, metrics=compute_metrics(q,output,config,elapsed),
                    total_latency_ms=elapsed, observation=output.observation if output else Observation(), errors=errors,
                    provenance={'dataset_version': dataset_version, 'benchmark': identity['benchmark_version'],
                        'fusion_method': config.fusion_method, 'context_method': config.context_method, 'agentic_method': config.agentic_method, 'benchmark_manifest_sha256': reader.manifest_hash,
                        'representation_manifest_sha256': identity['representation_manifest_sha256'], 'code': identity['code'],
                        'query_sha256': content_hash(q.model_dump(mode='json')), 'source': q.provenance,
                        'seeding': seed_report, 'pricing': config.pricing.model_dump() if config.pricing else None,
                        'synthetic_system': config.system_id in ('synthetic-fixture', 'synthetic-scripted'), 'release': release})
                write(target, record.model_dump(mode='json'))
                event('error' if errors else 'completed', q.query_id)
                pending.unlink()
        finally:
            materialize(output_dir)
        if digest(reader.manifest_path) != reader.manifest_hash:
            raise ValueError('Benchmark manifest changed during experiment')
        for split in config.splits:
            reader.verified_path(split + '.jsonl')
    return output_dir


def materialize(directory):
    directory = Path(directory)
    records = [RunRecord.model_validate_json(p.read_text(encoding='utf-8')) for p in sorted((directory/'records').glob('*.json'))]
    records.sort(key=lambda r:(r.split,r.query_id))
    manifest = read_json(directory/'manifest.json')
    if any(r.experiment_id != manifest['experiment_id'] or r.config_hash != manifest['config_hash'] or
           r.provenance.get('benchmark_manifest_sha256') != manifest['benchmark_manifest_sha256'] or
           r.provenance.get('representation_manifest_sha256') != manifest['representation_manifest_sha256'] or
           r.provenance.get('dataset_version') != manifest['dataset_version'] or
           r.provenance.get('benchmark') != manifest['benchmark_version'] for r in records):
        raise ValueError('Records do not belong to experiment manifest')
    table = aggregate(records)
    durable_write(directory/'records.jsonl', ''.join(canonical_json(r.model_dump(mode='json'))+'\n' for r in records))
    events = [RunEvent.model_validate_json(p.read_text(encoding='utf-8')) for p in sorted((directory/'events').glob('*.json'))]
    durable_write(directory/'events.jsonl', ''.join(canonical_json(e.model_dump(mode='json'))+'\n' for e in events))
    complete = len(records) == manifest['expected_query_count']
    status = {'complete': complete, 'expected_queries': manifest['expected_query_count'], 'completed_queries': len(records),
              'errors': sum(bool(r.errors) for r in records), 'marker': 'COMPLETE' if complete else 'INCOMPLETE'}
    write(directory/'status.json', status)
    table = [{**row, 'run_complete': complete} for row in table]
    write(directory/'aggregate.json', table)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=['cohort','metric','n_queries','n_errors','n_available','n_null','mean','run_complete'])
    writer.writeheader()
    writer.writerows(table)
    durable_write(directory/'aggregate.csv', stream.getvalue())
    return records
