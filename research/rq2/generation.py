"""Durable per-stage generation journal; ambiguous dispatches are never retried."""
import json
from pathlib import Path
from filelock import FileLock
from research.common.serialization import content_hash
from research.experiments.runner import write
from research.baselines.generation import PROMPT

class Journal:
    def __init__(self, root, final_generator, intermediate_generator):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.generators = {'final': final_generator, 'intermediate': intermediate_generator}
        self.version = content_hash({k: {'version': v.version,
            'options': v.options.model_dump(mode='json')} for k, v in self.generators.items()})

    def call(self, stage, question, context, seed, binding):
        role = 'final' if stage == 'final' else 'intermediate'
        key = content_hash({'stage': stage, 'question': question, 'context': context,
            'seed': seed, 'binding': binding, 'generator': self.version, 'prompt': PROMPT})
        path = self.root / (key + '.json')
        with FileLock(str(path) + '.lock', timeout=0):
            if path.exists():
                record = json.loads(path.read_text(encoding='utf-8'))
                if record['status'] != 'complete':
                    raise RuntimeError('Ambiguous/failed API stage requires manual reconciliation; refusing retry')
                if record['response_hash'] != content_hash([record['raw'], record['usage']]):
                    raise ValueError('Generation journal response corruption')
                return record['raw'], record['usage'], True
            write(path, {'key': key, 'stage': stage, 'status': 'dispatched', 'binding': binding})
            # On transport failure leave dispatch intact: billed tokens may be unknown.
            raw, usage = self.generators[role].generate(question, context, seed)
            write(path, {'key': key, 'stage': stage, 'status': 'complete', 'binding': binding,
                'raw': raw, 'usage': usage, 'response_hash': content_hash([raw, usage])})
            return raw, usage, False
