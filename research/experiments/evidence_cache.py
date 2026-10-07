"""Content-addressed immutable evidence bundles for future fixed-evidence comparisons."""
from pathlib import Path
from filelock import FileLock
from research.common.contracts import RetrievalBundle
from research.common.config import PROJECT_ROOT
from research.common.serialization import content_hash, canonical_json
from research.evaluation.benchmark import read_json
from research.experiments.config import durable_write


class EvidenceCache:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if any(self.root.is_relative_to((PROJECT_ROOT / name).resolve()) for name in ('data', 'storage')):
            raise ValueError('Evidence cache must be outside canonical stores')

    @staticmethod
    def identity(*, query_id, query_sha256, representation_sha256, retriever_id, retriever_version, parameters, seed):
        return dict(query_id=query_id, query_sha256=query_sha256, representation_sha256=representation_sha256,
                    retriever_id=retriever_id, retriever_version=retriever_version, parameters=parameters, seed=seed)

    def put(self, identity, bundle: RetrievalBundle):
        if bundle.query_id != identity['query_id']:
            raise ValueError('Cache query mismatch')
        key = content_hash(identity)
        self.root.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.root/(key+'.lock')), timeout=0):
            path=self.root/(key+'.json')
            value={'identity':identity,'bundle':bundle.model_dump(mode='json'),'bundle_sha256':bundle.bundle_hash()}
            if path.exists():
                if read_json(path) != value:
                    raise ValueError('Immutable evidence cache collision')
            else:
                durable_write(path, canonical_json(value)+'\n')
        return key

    def get(self, identity):
        path=self.root/(content_hash(identity)+'.json')
        if not path.exists():
            return None
        value=read_json(path)
        bundle=RetrievalBundle.model_validate(value['bundle'])
        if value['identity'] != identity or bundle.bundle_hash() != value['bundle_sha256'] or bundle.query_id != identity['query_id']:
            raise ValueError('Evidence cache corruption')
        return bundle
