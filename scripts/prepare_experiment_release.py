"""Bind separate human-review exports to an immutable benchmark release."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import BenchmarkReader, read_json, release_gate
from research.evaluation.contracts import ReleaseMetadata
from research.experiments.runner import write


def prepare_release(benchmark_root, exports, output, *, released_by, leakage_adjudicated):
    reader=BenchmarkReader(benchmark_root)
    output=Path(output).resolve()
    if output.is_relative_to(reader.root.parent):
        raise ValueError('Review metadata must be outside canonical dataset stores')
    decisions=[]
    for path in exports:
        exported=read_json(path)
        if exported.get('benchmark') != reader.manifest['benchmark_version']:
            raise ValueError('Review export benchmark version mismatch')
        decisions.extend(exported['decisions'])
    value=ReleaseMetadata(benchmark_manifest_sha256=reader.manifest_hash,
        test_content_freeze_id=reader.manifest['test_content_freeze_id'],status='released',
        leakage_adjudicated=leakage_adjudicated,released_by=released_by,decisions=decisions)
    # Validate in a temporary sibling before promoting; never alter an existing release.
    if output.exists():
        raise ValueError('Refusing to overwrite release metadata')
    output.parent.mkdir(parents=True,exist_ok=True)
    candidate=output.with_name(output.name+'.candidate.json')
    if candidate.exists():
        raise ValueError('Unresolved release candidate already exists')
    try:
        write(candidate,value.model_dump(mode='json'))
        result=release_gate(reader,candidate)
        candidate.rename(output)
        return result
    finally:
        if candidate.exists():candidate.unlink()


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Explicit human release attestation; does not create review decisions.')
    p.add_argument('--benchmark',default='data/MMG_STARK_MAG/benchmark')
    p.add_argument('--export',action='append',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--released-by',required=True)
    p.add_argument('--leakage-adjudicated',action='store_true',required=True)
    a=p.parse_args()
    print(prepare_release(a.benchmark,a.export,a.output,released_by=a.released_by,leakage_adjudicated=a.leakage_adjudicated))
