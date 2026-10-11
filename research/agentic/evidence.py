"""Evidence helpers shared by all Phase 9 policies: IDs, deterministic text rendering, memory."""
import json
from research.common.serialization import canonical_json


def canonical_paper(item):
    return int(item.canonical_id.removeprefix('stark:'))


def provenance_paper_ids(item):
    """Canonical paper plus every paper-type node carried in the evidence payload (path provenance)."""
    ids = {canonical_paper(item)}
    payload = json.loads(item.payload)
    for node in payload.get('nodes', ()) or ():
        if node.get('node_type') == 'paper':
            ids.add(int(node['node_id']))
    return ids


def render(item):
    """Deterministic, source-agnostic text of an evidence item for the CRAG evaluator (no learned transformation)."""
    payload = json.loads(item.payload)
    if item.source_type == 'text':
        return payload.get('content') or ((payload.get('title') or '') + '\n\n' + (payload.get('abstract') or ''))
    if item.source_type == 'graph':
        labels = {n['node_id']: (n.get('label') or f"stark:{n['node_id']}") for n in payload.get('nodes', ())}
        lines = [payload.get('title') or labels.get(payload['paper_id'], f"stark:{payload['paper_id']}")]
        for e in payload.get('path', ()):
            lines.append(f"{labels.get(e['source'], e['source'])} {e['relation']} {labels.get(e['target'], e['target'])}")
        return '\n'.join(lines)
    return '\n'.join(f'{k}: {v}' for k, v in payload.items())


class EvidenceMemory:
    """Cumulative, deduplicated (by evidence_id), acquisition-ordered evidence."""
    def __init__(self):
        self.items = {}
        self.queried = []          # ordered (source, normalized query) tool calls

    def add(self, items):
        new = []
        for item in items:
            if item.evidence_id not in self.items:
                self.items[item.evidence_id] = item
                new.append(item)
        return new

    def by_source(self, source):
        return [e for e in self.items.values() if e.source_type == source]

    def ordered(self):
        return list(self.items.values())
