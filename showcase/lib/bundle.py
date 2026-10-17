"""Read-only access to the frozen data bundle (showcase/bundle/), with checksum verification.

The bundle is produced by scripts/build_showcase_bundle.py. Every file is checked against manifest.json when the app
starts; a mismatch is reported on screen and the affected data is not shown.
"""
from pathlib import Path
import gzip, hashlib, json

BUNDLE = Path(__file__).resolve().parents[1] / 'bundle'


class BundleError(RuntimeError):
    pass


class Bundle:
    def __init__(self, root=BUNDLE):
        self.root = Path(root)
        mpath = self.root / 'manifest.json'
        if not mpath.exists():
            raise BundleError('The data bundle is missing (%s). Build it with scripts/build_showcase_bundle.py.' % mpath)
        self.manifest = json.loads(mpath.read_text(encoding='utf-8'))
        self.checks = {}
        for name, meta in sorted(self.manifest['files'].items()):
            p = self.root / name
            self.checks[name] = p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == meta['sha256']
        recomputed = hashlib.sha256(''.join('%s:%s\n' % (k, v['sha256']) for k, v in sorted(self.manifest['files'].items())).encode()).hexdigest()
        self.verified = all(self.checks.values()) and recomputed == self.manifest['bundle_sha256']
        self._cache = {}

    @property
    def sha256(self):
        return self.manifest['bundle_sha256']

    def _load(self, name):
        if name not in self._cache:
            if not self.checks.get(name):
                raise BundleError('Bundle file %s failed its checksum; it is not shown.' % name)
            raw = (self.root / name).read_bytes()
            self._cache[name] = json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
        return self._cache[name]

    @property
    def results(self):
        return self._load('results.json')

    @property
    def queries(self):
        return self._load('queries.json')

    @property
    def papers(self):
        return self._load('papers.json')

    @property
    def foundation(self):
        return self._load('foundation.json')

    @property
    def stats_demo(self):
        return self._load('stats_demo.json')

    def explorer(self, rq):
        return self._load('explorer_%s.json.gz' % rq.lower())

    def title(self, paper_id):
        return self.papers.get(str(paper_id))
