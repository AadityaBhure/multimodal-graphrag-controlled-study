"""Canonical RQ2 fusion (Phase 1D §5.1–5.3). Pure functions over the frozen cached bundle: no retrieval, no model.

CF-B0 / CF-B1 reuse the historical implementations unchanged (research/rq2/fusion.py).
"""
import json
import re
from research.common.serialization import canonical_json
from research.rq2.contracts import SOURCES, evidence
from research.rq2.fusion import pack, separated, resolve, normalize, serialize, paper_id

LABEL = {'text': '[TEXT]', 'graph': '[GRAPH]', 'structured': '[STRUCTURED]'}


# ------------------------------------------------------------------ CF-01 (KAG-inspired entity alignment)
def global_resolve(item, frozen, registry):
    """S2: an ambiguous exact alias resolves only if exactly one candidate has the item's own entity type."""
    payload = json.loads(item.payload) if item.payload else {}
    meta = json.loads(item.metadata)
    alias = payload.get('title') or payload.get('display_name') or meta.get('alias')
    candidates = dict(frozen.aliases).get(normalize(alias), ()) if isinstance(alias, str) else ()
    own = (registry.get(item.canonical_id) or {}).get('entity_type')
    typed = [c for c in candidates if own and (registry.get(c) or {}).get('entity_type') == own]
    return (typed[0], 'global_type_resolver') if len(typed) == 1 else (None, 'unaligned')


def body(item):
    """Item facts without provenance (provenance is serialized once per group)."""
    obj = json.loads(serialize(item)); obj.pop('provenance', None)
    return canonical_json(obj)


def render_group(key, members, registry, aligned):
    if aligned:
        lines = ['[ENTITY %s | %s]' % (key, (registry.get(key) or {}).get('display_name') or '')]
    else:
        lines = ['[UNALIGNED %s]' % key]
    for source in SOURCES:
        part = [m for m in members if m.source_type == source]
        if part:
            lines.append(LABEL[source]); lines.extend(body(m) for m in part)
    lines.append('[PROVENANCE]')
    lines.append(canonical_json({m.evidence_id: [p.model_dump(mode='json') for p in m.provenance] for m in members}))
    return '\n'.join(lines)


def cf01(frozen, budget, registry):
    items = evidence(frozen)                                  # Text -> Graph -> Structured, retriever order within source
    d = {'alignments': [], 'fallback': None, 'group_truncated': False, 'truncated_group': None}
    groups, aligned = {}, {}
    for item in items:
        cid, rule = resolve(item, frozen)
        if cid is None and rule == 'ambiguous_alias':
            cid, rule = global_resolve(item, frozen, registry)
        key = cid if cid is not None else item.evidence_id
        groups.setdefault(key, []).append(item); aligned[key] = cid is not None
        d['alignments'].append({'evidence_id': item.evidence_id, 'canonical_id': cid, 'rule': rule})
    d['resolved'] = sum(a['canonical_id'] is not None for a in d['alignments'])
    d['unresolved'] = len(items) - d['resolved']
    d['global_resolver_uses'] = sum(a['rule'] == 'global_type_resolver' for a in d['alignments'])
    if d['resolved'] == 0:
        context, kept, _ = separated(items, budget)
        d['fallback'] = 'source_separated'
        return context, tuple(kept), d
    def score(members): return max((m.score or 0.) for m in members)
    order = sorted(groups, key=lambda k: (-score(groups[k]), -len({m.source_type for m in groups[k]}), k))
    d['group_order'] = [{'key': k, 'aligned': aligned[k], 'group_score': score(groups[k]),
                         'source_coverage': len({m.source_type for m in groups[k]}), 'members': [m.evidence_id for m in groups[k]]} for k in order]
    context, kept = '', []
    for k in order:
        block = render_group(k, groups[k], registry, aligned[k])
        sep = '\n' if context else ''
        if len(context) + len(sep) + len(block) <= budget:
            context += sep + block; kept.extend(groups[k]); continue
        # Next full group does not fit: add its highest-ranked items only if they fit, then stop (budget reached).
        ranked = sorted(groups[k], key=lambda m: -(m.score or 0.))   # stable: retriever order breaks ties
        chosen = []
        for m in ranked:
            trial = render_group(k, [x for x in groups[k] if x in chosen + [m]], registry, aligned[k])
            if len(context) + len(sep) + len(trial) <= budget:
                chosen.append(m)
        if chosen:
            context += sep + render_group(k, [x for x in groups[k] if x in chosen], registry, aligned[k]); kept.extend(x for x in groups[k] if x in chosen)
            d['group_truncated'] = True; d['truncated_group'] = k
        break
    d['groups_included'] = len({a for a in order if any(m in kept for m in groups[a])})
    return context, tuple(kept), d


# ------------------------------------------------------------------ CF-02 (SAG-inspired dual path)
def provenance_key(item):
    return (item.canonical_id, tuple(sorted(json.dumps(p.model_dump(mode='json'), sort_keys=True) for p in item.provenance)))


def dedup(items):
    """Drop repeated evidence_ids and items whose (entity, provenance) duplicates an earlier candidate."""
    seen_ids, seen_prov, out, dropped = set(), set(), [], []
    for item in items:
        key = provenance_key(item)
        if item.evidence_id in seen_ids or key in seen_prov:
            dropped.append(item.evidence_id); continue
        seen_ids.add(item.evidence_id); seen_prov.add(key); out.append(item)
    return out, dropped


def one_line(item, width=200):
    text = item.content or item.payload or ''
    return re.sub(r'\s+', ' ', text).strip()[:width]


def manifest(structural, count_tokens, budget):
    lines, included = [], []
    for item in structural:
        prov = sorted({p.source_id for p in item.provenance})
        line = '%s | %s | %.4f | %s | %s' % (item.evidence_id, item.source_type, item.score or 0., one_line(item), ','.join(prov))
        if count_tokens('\n'.join(lines + [line])) > budget:
            break
        lines.append(line); included.append(item)
    return '\n'.join(lines), included


def parse_selection(raw, allowed, limit=5):
    """Strict JSON; returns (valid ids in order, invalid ids) or raises ValueError."""
    clean = raw.strip()
    if clean.startswith('```'):
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', clean)
    value = json.loads(clean)
    if not isinstance(value, dict) or not isinstance(value.get('selected_ids'), list) or not isinstance(value.get('reason', ''), str):
        raise ValueError('selector schema')
    valid, invalid = [], []
    for x in value['selected_ids']:
        x = str(x)
        (valid if x in allowed and x not in valid else invalid).append(x)
    return valid[:limit], invalid + valid[limit:]


def relevance_fallback(structural, limit=5):
    return [e.evidence_id for e in sorted(structural, key=lambda e: -(e.score or 0.))][:limit]


def cf02_context(structural_selected, semantic, budget, total=10):
    """Selected structural (selector order) + semantic fill in retriever order to `total`; trim to budget."""
    fill = semantic[:max(0, total - len(structural_selected))]
    chosen = list(structural_selected) + list(fill)
    trimmed = []
    def render(items):
        return '\n'.join(LABEL[e.source_type] + ' ' + serialize(e) for e in items)
    context = render(chosen)
    while len(context) > budget and chosen:
        victim = next((e for e in reversed(chosen) if e.source_type == 'text'), None) or chosen[-1]   # semantic tail first, then structural tail
        chosen.remove(victim); trimmed.append(victim.evidence_id); context = render(chosen)
    return context, tuple(chosen), trimmed


# ------------------------------------------------------------------ CF-03 (MegaRAG-inspired late fusion)
def parse_intermediate(raw, allowed):
    clean = raw.strip()
    if clean.startswith('```'):
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', clean)
    value = json.loads(clean)
    if (not isinstance(value, dict) or not isinstance(value.get('candidate_answer'), str)
            or not isinstance(value.get('supporting_evidence_ids'), list) or value.get('confidence') not in ('low', 'medium', 'high')):
        raise ValueError('intermediate schema')
    ids = [str(x) for x in value['supporting_evidence_ids']]
    valid = list(dict.fromkeys(x for x in ids if x in allowed))
    return {'candidate_answer': value['candidate_answer'], 'supporting_evidence_ids': valid, 'confidence': value['confidence'],
            'invalid_ids': [x for x in ids if x not in allowed]}


__all__ = ['cf01', 'dedup', 'manifest', 'parse_selection', 'relevance_fallback', 'cf02_context', 'parse_intermediate',
           'separated', 'pack', 'paper_id', 'evidence', 'SOURCES', 'LABEL']
