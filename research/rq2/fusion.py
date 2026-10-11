"""Pure fusion: no store, model, network, or retrieval dependencies."""
import json
import re
import time
import unicodedata
from research.common.serialization import canonical_json
from .contracts import SOURCES, evidence

def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())

def paper_id(item):
    match = re.fullmatch(r'stark:(\d+)', item.canonical_id)
    return int(match[1]) if match else None

def serialize(item):
    # Full source content and provenance; omit bulky retrieval diagnostics, not facts.
    meta = json.loads(item.metadata)
    return canonical_json({'evidence_id': item.evidence_id, 'source': item.source_type,
        'canonical_id': item.canonical_id, 'content': item.content,
        'payload': json.loads(item.payload) if item.payload else None,
        'provenance': [p.model_dump(mode='json') for p in item.provenance],
        'overlay': {k: meta[k] for k in ('origin', 'overlay_sha256') if k in meta}})

def pack(items, budget, heading=''):
    """Atomic items, stable order, skip items that do not fit; never truncate facts."""
    context = heading
    kept = []
    for item in items:
        block = ('\n' if context else '') + serialize(item)
        if len(context) + len(block) <= budget:
            context += block
            kept.append(item)
    return context, kept

def separated(items, budget):
    sections, kept = [], []
    # Two separating newlines are charged to the common cap.
    per_source = (budget - 2) // 3
    for source in SOURCES:
        context, selected = pack([e for e in items if e.source_type == source], per_source,
                                 source.upper() + ' EVIDENCE')
        sections.append(context)
        kept.extend(selected)
    return '\n'.join(sections), kept, dict(zip(SOURCES, sections))

def resolve(item, frozen):
    known = set(frozen.canonical_ids)
    if item.canonical_id in known:
        return item.canonical_id, 'exact_canonical_id'
    meta = json.loads(item.metadata)
    sid = meta.get('stark_node_id')
    if type(sid) is int and 'stark:' + str(sid) in known:
        return 'stark:' + str(sid), 'exact_stark_id'
    payload = json.loads(item.payload) if item.payload else {}
    alias = payload.get('title') or payload.get('display_name') or meta.get('alias')
    matches = dict(frozen.aliases).get(normalize(alias), ()) if isinstance(alias, str) else ()
    if len(matches) == 1:
        return matches[0], 'exact_normalized_alias'
    return None, 'ambiguous_alias' if matches else 'unresolved'

def fuse(frozen, options):
    started = time.perf_counter()
    items = evidence(frozen)
    d = {'bundle_hash': frozen.bundle.bundle_hash(), 'input_fingerprint': frozen.fingerprint(),
         'incoming_ids': [e.evidence_id for e in items], 'alignments': [], 'selector': [],
         'entity_alignment_correctness': None, 'conflict_handling_accuracy': None,
         'resolution_scope': 'primary evidence entity; no NER or concept expansion',
         'additional_retrieval_calls': 0}
    parts = {}
    if options.method == 'CF-B0':
        context, kept = pack(items, options.budget)
    elif options.method in ('CF-B1', 'CF-03'):
        context, kept, parts = separated(items, options.budget)
    elif options.method == 'CF-01':
        groups = {}
        for item in items:
            entity, rule = resolve(item, frozen)
            key = entity or 'unresolved:' + item.evidence_id
            groups.setdefault(key, []).append(item)
            d['alignments'].append({'evidence_id': item.evidence_id, 'canonical_id': entity, 'rule': rule})
        context, kept = '', []
        for entity, group in groups.items():
            heading = ('\n' if context else '') + 'ENTITY ' + entity
            if len(context) + len(heading) > options.budget:
                continue
            block, selected = pack(group, options.budget - len(context), heading)
            if selected:
                context += block
                kept.extend(selected)
        d['groups'] = {key: [e.evidence_id for e in value] for key, value in groups.items()}
        d['unresolved_count'] = sum(row['canonical_id'] is None for row in d['alignments'])
    else:
        # Fixed lexical contextual selector. Structural payload only, never IDs/provenance.
        terms = set(re.findall(r'\w+', frozen.question.casefold()))
        structural = [e for e in items if e.source_type != 'text']
        scored = []
        for rank, item in enumerate(structural):
            words = set(re.findall(r'\w+', (item.payload or item.content or '').casefold()))
            overlap = sorted(terms & words)
            score = len(overlap) / len(terms) if terms else 0.
            scored.append((score, rank, item, overlap))
        scored.sort(key=lambda row: (-row[0], row[1]))
        selected = [row[2] for row in scored if row[0] > 0][:options.structural_limit]
        selected += [e for e in items if e.source_type == 'text'][:options.total_limit - len(selected)]
        context, kept = pack(selected, options.budget)
        for score, rank, item, overlap in scored:
            d['selector'].append({'evidence_id': item.evidence_id, 'source': item.source_type,
                'input_rank': rank, 'score': score, 'overlap': overlap,
                'selected': item in selected, 'retained': item in kept,
                'reason': 'selected' if item in selected else ('zero_overlap' if score == 0 else 'structural_limit')})
        for item in items:
            if item.source_type == 'text':
                d['selector'].append({'evidence_id': item.evidence_id, 'source': 'text',
                    'selected': item in selected, 'retained': item in kept,
                    'reason': 'semantic_fill' if item in selected else 'total_limit'})
    d['source_counts'] = {s: sum(e.source_type == s for e in kept) for s in SOURCES}
    d['source_coverage'] = {s: (sum(e.source_type == s for e in kept) / sum(e.source_type == s for e in items)
        if any(e.source_type == s for e in items) else None) for s in SOURCES}
    d['source_entity_redundancy'] = {s: (1 - len({e.canonical_id for e in kept if e.source_type == s}) /
        d['source_counts'][s] if d['source_counts'][s] else None) for s in SOURCES}
    d['retained_overlay_ids'] = [e.evidence_id for e in kept if json.loads(e.metadata).get('origin') == 'phase4_evaluation_overlay']
    d['source_contexts'] = parts
    d['fusion_ms'] = (time.perf_counter() - started) * 1000
    assert len(context) <= options.budget
    return context, tuple(kept), d
