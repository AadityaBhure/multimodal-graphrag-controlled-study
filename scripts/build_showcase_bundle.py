"""Showcase data bundle: one deterministic, checksummed export of the frozen study outputs for the showcase app.

The app (showcase/) reads only showcase/bundle/. Study-level numbers are copied from the frozen analyses
(documentation/*/analysis_local.json); per-question views come from the stored run records, using the same metric
functions as the analyses. Nothing is re-estimated; the builder is read-only on every study output.

    .venv\\Scripts\\python.exe scripts\\build_showcase_bundle.py           build showcase/bundle/
    .venv\\Scripts\\python.exe scripts\\build_showcase_bundle.py --check   rebuild in memory, compare with the committed bundle
"""
from pathlib import Path
from collections import Counter
import gzip, hashlib, json, math, re, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.agentic import analysis as A
from research.evaluation.benchmark import BenchmarkReader, digest
from showcase.lib.traces import ar_steps

OUT = ROOT / 'showcase/bundle'
DOC = ROOT / 'documentation'
DATA = ROOT / 'data/MMG_STARK_MAG'
BENCH = DATA / 'benchmark'
WORK = ROOT / 'artifacts/showcase/work'           # Stores scratch space (must lie outside the frozen data root)
RUNS = {'RQ1': DOC / 'rq1_repair/runs_local', 'RQ2': DOC / 'rq2_repair/runs_local', 'RQ3': DOC / 'phase9/runs_local', 'RQ4': DOC / 'rq4/runs_local'}
ANALYSIS = {'RQ1': DOC / 'rq1_repair/analysis_local.json', 'RQ2': DOC / 'rq2_repair/analysis_local.json',
            'RQ3': DOC / 'phase9/analysis_local.json', 'RQ4': DOC / 'rq4/analysis_local.json'}
METHODS = {'RQ1': ['CM-B0', 'CM-B1', 'CM-01', 'CM-02', 'CM-03'], 'RQ2': ['CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03'],
           'RQ3': ['AR-B0', 'AR-B1', 'AR-01', 'AR-02', 'AR-03'], 'RQ4': ['INT-1', 'AR-B0', 'AR-B1']}
CONTROLS = {'RQ1': ['CM-B0', 'CM-B1'], 'RQ2': ['CF-B0', 'CF-B1'], 'RQ3': ['AR-B0', 'AR-B1'], 'RQ4': ['AR-B0', 'AR-B1']}
# Pareto axes exactly as in each study's analysis (higher-is-better, lower-is-better)
PARETO_AXES = {'RQ1': (['answer_f1', 'mrr'], ['input_tokens', 'latency']), 'RQ2': (['answer_f1'], ['input_tokens', 'latency']),
               'RQ3': (['answer_f1', 'source_f1'], ['total_tokens', 'latency'])}
RENAME = {'f1': 'answer_f1', 'exact_match': 'answer_em', 'recall@5': 'recall_at_5', 'intrinsic_total_ms': 'latency', 'intrinsic_ms': 'latency',
          'context_management_ms': 'cm_ms'}
OFFICIAL_EDGES = 19_919_698
REL = {'AUTHOR-WRITES-PAPER': 'WRITES', 'AUTHOR-AFFILIATED_WITH-INSTITUTION': 'AFFILIATED_WITH', 'PAPER-CITES-PAPER': 'CITES',
       'PAPER-HAS_TOPIC-FIELD_OF_STUDY': 'HAS_TOPIC'}
REL_ID = {0: 'AUTHOR-AFFILIATED_WITH-INSTITUTION', 1: 'PAPER-CITES-PAPER', 2: 'PAPER-HAS_TOPIC-FIELD_OF_STUDY', 3: 'AUTHOR-WRITES-PAPER'}
REL_TYPES = {'WRITES': ('author', 'paper'), 'AFFILIATED_WITH': ('author', 'institution'), 'CITES': ('paper', 'paper'), 'HAS_TOPIC': ('paper', 'field_of_study')}
EXAMPLE_FAMILY = 'generated:69a22c3b4989b07ed6c3'   # a text+graph+structured family present in RQ1, RQ2 and RQ3
GRAPH_VIEW_NODES, GRAPH_VIEW_EDGES = 60, 140         # display cap only; the caption states what is shown


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def norm(k):
    return RENAME.get(k, k)


def records(rq, method):
    out = [load(p) for p in sorted((RUNS[rq] / method / 'records').glob('*.json'))]
    assert out and all(r['system_id'] == method and r['split'] == 'validation' for r in out), (rq, method)
    return sorted(out, key=lambda r: r['query_id'])


def diag(r):
    return json.loads(r['output']['diagnostics']) if r.get('output') and r['output'].get('diagnostics') else {}


def explanation(raw):
    """The model's stated reason, from its JSON answer; the raw text if it is not JSON."""
    try:
        a = json.loads(raw)
        if isinstance(a, dict):
            return a.get('explanation')
    except (TypeError, ValueError):
        pass
    return (raw or '')[:800] or None


def orient(t, a, b):
    """A paired result for (a - b) re-expressed as (b - a): exact sign flip of the delta and its interval; p unchanged."""
    ci = t.get('ci95')
    neg = lambda x: -x + 0.                                   # + 0. turns -0.0 into 0.0
    return {**t, 'a': b, 'b': a, 'delta': neg(t['delta']) if t['delta'] is not None else None, 'ci95': [neg(ci[1]), neg(ci[0])] if ci else None}


def test_row(a, b, t):
    return {'a': a, 'b': b, 'delta': t['mean_delta'], 'ci95': t.get('ci95_family_bootstrap'), 'p': t.get('p_sign_flip'), 'p_holm': t.get('p_holm'),
            'significant': bool(t.get('significant')), 'n': t.get('n'), 'families': t.get('n_families')}


# ------------------------------------------------------------------------------------------------------------- results
def rq1_results():
    a = load(ANALYSIS['RQ1'])
    desc, ci, strata, n = {}, {}, {}, {}
    for t in a['tables']:
        m, k = t['method'], norm(t['metric'])
        if t['cohort'] == 'all':
            desc.setdefault(m, {})[k] = t['mean']; ci.setdefault(m, {})[k] = t['ci95']
        else:
            dim, val = t['cohort'].split(':', 1)
            strata.setdefault(dim, {}).setdefault(val, {}).setdefault(m, {})[k] = t['mean']
            n[(dim, val)] = max(n.get((dim, val), 0), t['n'] + t['n_null'])
    for m in METHODS['RQ1']:                                   # answer F1 on answerable questions: n-weighted mean of the answerable strata
        parts = [(strata['stress'][s][m]['answer_f1'], n[('stress', s)]) for s in ('normal', 'noisy', 'conflict')]
        desc[m]['answerable_f1'] = sum(v * w for v, w in parts) / sum(w for _, w in parts)
    order = METHODS['RQ1']
    tests = []
    for c in a['paired_f1']:
        row = {'a': c['a'], 'b': c['b'], 'delta': c['mean'], 'ci95': c['ci95'], 'p': c['p_cluster_sign_permutation'], 'p_holm': c.get('p_holm'),
               'significant': (c.get('p_holm') or 1.) < .05, 'n': c['n'], 'families': c['independent_query_families']}
        tests.append(orient(row, c['a'], c['b']) if order.index(c['a']) < order.index(c['b']) else row)   # later method first
    hi, lo = PARETO_AXES['RQ1']
    return {'descriptive': desc, 'ci95': ci, 'tests': {'answer_f1': tests}, 'pareto': A.pareto({m: desc[m] for m in order}, hi, lo),
            'strata': {dim: {v: {m: {k: x.get(k) for k in ('answer_f1', 'mrr', 'gold_coverage', 'input_tokens')} for m, x in ms.items()}
                             for v, ms in vals.items()} for dim, vals in strata.items() if dim in ('stress', 'modality')},
            'strata_n': {'%s:%s' % k: v for k, v in sorted(n.items())},
            'initialisation_ms': a['initialisation_ms_per_method'], 'cohort': {'queries': 32, 'families': 8}}


def rq_results(rq):
    a = load(ANALYSIS[rq])
    desc = {m: {norm(k): v for k, v in a['descriptive'][m].items()} for m in a['descriptive']}
    tests = {norm(metric): [test_row(*k.split(' vs '), t) for k, t in sorted(pairs.items())] for metric, pairs in a['paired_tests'].items()}
    out = {'descriptive': desc, 'tests': tests, 'errors': a.get('errors')}
    if rq in ('RQ2', 'RQ3'):
        out['pareto'] = a['pareto']
        hi, lo = PARETO_AXES[rq]
        assert A.pareto({m: desc[m] for m in METHODS[rq]}, hi, lo) == a['pareto'], rq
    if rq == 'RQ2':
        sup = load(DOC / 'rq2_repair/supportability.json')
        out.update(cohort={'queries': a['bundles'], 'families': a['families']}, method_diagnostics=a['method_diagnostics'],
                   supportability={'counts': sup['counts'], 'rule': sup['rule']},
                   strata=split_strata(a['strata']), strata_n={k: v['n'] for k, v in a['strata'].items()})
    if rq == 'RQ3':
        out.update(cohort={'queries': a['cohort'], 'families': a['families']}, stop_reasons=a['stop_reasons'], statuses=a['statuses'],
                   failure_taxonomy=a['failure_taxonomy'], strata=split_strata(a['strata']))
    if rq == 'RQ4':
        out.update(cohort={'queries': 28, 'families': 14}, selection={k: v for k, v in a['selection'].items() if not k.endswith('sha256')},
                   strata=split_strata({k: {m: {'answer_f1': v} for m, v in ms.items()} for k, ms in a['strata'].items()}))
    return out


def split_strata(flat):
    out = {}
    for key, ms in flat.items():
        dim, val = key.split(':', 1)
        out.setdefault(dim, {})[val] = {m: {norm(k): v for k, v in x.items()} for m, x in ms.items() if isinstance(x, dict)}
    return out


# ------------------------------------------------------------------------------------------------------------- graph view
def canonical_edge(edge_id, inverse, source, target, relation):
    assert (int(edge_id) >= OFFICIAL_EDGES) == bool(inverse), (edge_id, inverse)
    if inverse:
        return {'source': int(target), 'target': int(source), 'edge': int(edge_id) - OFFICIAL_EDGES, 'rel': REL[relation]}
    return {'source': int(source), 'target': int(target), 'edge': int(edge_id), 'rel': REL[relation]}


def context_graph(context):
    """Nodes and relations exactly as written in the [GRAPH] section of a model context.

    The section runs from '[GRAPH]' to the next pass-through section header ([STRUCTURED] or [TEXT]), which may follow the
    last graph line without a line break. Lines with an evidence-ID prefix are evaluation overlays (conflict variants) and
    are counted, not drawn."""
    nodes, edges, overlays = {}, {}, 0
    ctx = context or ''
    head = '[GRAPH]\n'
    start = ctx.find(head)
    if start < 0:
        return nodes, edges, overlays
    body = ctx[start + len(head):]
    cut = [i for i in (body.find('[STRUCTURED]'), body.find('[TEXT]')) if i >= 0]
    body = body[:min(cut)] if cut else body
    dec = json.JSONDecoder()
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith('{'):
            overlays += line.split(' ', 1)[0].endswith(':overlay')
            continue
        o, _ = dec.raw_decode(line)
        if 'node_id' in o:
            nodes.setdefault(int(o['node_id']), {'label': o.get('label'), 'type': o.get('node_type'), 'overlay': bool(o.get('evaluation_overlay'))})
        elif 'canonical_official_edge_id' in o:                    # CM-01 units: canonical direction already
            e = {'source': int(o['source_id']), 'target': int(o['target_id']), 'edge': int(o['canonical_official_edge_id']), 'rel': REL[o['relation']]}
            edges.setdefault(e['edge'], e)
        elif 'edge_id' in o:
            e = canonical_edge(o['edge_id'], o.get('derived_inverse'), o['source'], o['target'], o['relation'])
            edges.setdefault(e['edge'], e)
    return nodes, edges, overlays


MIN_DIST, EDGE_LEN, PAD = 105., 125., 60.


def _relax(pts, min_dist=MIN_DIST):
    ids = sorted(pts)
    for _ in range(120):
        moved = False
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                dx, dy = pts[b][0] - pts[a][0], pts[b][1] - pts[a][1]
                d = (dx * dx + dy * dy) ** .5
                if d < min_dist:
                    if d < 1e-6:
                        dx, dy, d = 1., .37, 1.07
                    push = (min_dist - d) / 2 + .5
                    ux, uy = dx / d, dy / d
                    pts[a][0] -= ux * push; pts[a][1] -= uy * push
                    pts[b][0] += ux * push; pts[b][1] += uy * push
                    moved = True
        if not moved:
            break
    return pts


def component_layout(sub):
    import networkx as nx
    nodes = sorted(sub)
    if len(nodes) == 1:
        return {nodes[0]: [0., 0.]}
    if len(nodes) == 2:
        return {nodes[0]: [0., 0.], nodes[1]: [EDGE_LEN, 0.]}
    raw = nx.kamada_kawai_layout(sub)
    pts = {k: [float(v[0]), float(v[1])] for k, v in raw.items()}
    lens = [((pts[a][0] - pts[b][0]) ** 2 + (pts[a][1] - pts[b][1]) ** 2) ** .5 for a, b in sub.edges()] or [1.]
    f = EDGE_LEN / ((sum(lens) / len(lens)) or 1.)
    pts = {k: [x * f, y * f] for k, (x, y) in pts.items()}
    cx = sum(p[0] for p in pts.values()) / len(pts); cy = sum(p[1] for p in pts.values()) / len(pts)
    sxx = sum((p[0] - cx) ** 2 for p in pts.values()); syy = sum((p[1] - cy) ** 2 for p in pts.values())
    sxy = sum((p[0] - cx) * (p[1] - cy) for p in pts.values())
    theta = .5 * math.atan2(2 * sxy, sxx - syy); c, sn = math.cos(-theta), math.sin(-theta)
    pts = {k: [(p[0] - cx) * c - (p[1] - cy) * sn, (p[0] - cx) * sn + (p[1] - cy) * c] for k, p in pts.items()}
    if pts[min(pts)][0] > 0:
        pts = {k: [-p[0], p[1]] for k, p in pts.items()}
    return _relax(pts)


def pack_layout(node_ids, edge_pairs):
    """Deterministic layout: each connected component laid out on its own, components packed into rows."""
    import networkx as nx
    g = nx.Graph(); g.add_nodes_from(sorted(node_ids)); g.add_edges_from(sorted(edge_pairs))
    comps = []
    for nodes in nx.connected_components(g):
        pts = component_layout(g.subgraph(nodes))
        xs = [p[0] for p in pts.values()]; ys = [p[1] for p in pts.values()]
        comps.append({'pts': pts, 'minx': min(xs), 'miny': min(ys), 'w': max(xs) - min(xs) + 2 * PAD, 'h': max(ys) - min(ys) + 2 * PAD, 'key': min(nodes)})
    comps.sort(key=lambda c: (-(c['w'] * c['h']), c['key']))
    total = sum(c['w'] * c['h'] for c in comps)
    target = max([c['w'] for c in comps] + [(total * 1.6) ** .5]) if comps else 0
    x = y = row_h = 0.; out = {}
    for c in comps:
        if x > 0 and x + c['w'] > target:
            x, y, row_h = 0., y + row_h, 0.
        for n, (px, py) in c['pts'].items():
            out[n] = (round(x + (px - c['minx']) + PAD, 1), round(y + (py - c['miny']) + PAD, 1))
        x += c['w']; row_h = max(row_h, c['h'])
    return out


def graph_view(nodes, edges, labels, flags, priority=()):
    """Display subgraph (bounded) with a precomputed layout. flags: {node_id: {'gold','answer','seed','anchor'}}."""
    total_nodes, total_edges = len(nodes), len(edges)
    rank = {n: i for i, n in enumerate(priority)}
    def key(n):
        f = flags.get(n, {})
        return (not f.get('gold'), not f.get('answer'), not f.get('anchor'), not f.get('seed'), rank.get(n, 10 ** 9), n)
    shown = set(sorted(nodes, key=key)[:GRAPH_VIEW_NODES])
    shown_edges = [e for _, e in sorted(edges.items()) if e['source'] in shown and e['target'] in shown][:GRAPH_VIEW_EDGES]
    pos = pack_layout(shown, [(e['source'], e['target']) for e in shown_edges])
    out_nodes = []
    for n in sorted(shown):
        info = nodes[n]; lab = labels.get(n, {})
        label = info.get('label') or lab.get('label'); typ = info.get('type') or lab.get('type')
        out_nodes.append({'id': n, 'label': label or 'stark:%d' % n, 'type': typ, 'x': pos[n][0], 'y': pos[n][1],
                          **{k: True for k, v in sorted(flags.get(n, {}).items()) if v}})
    for e in shown_edges:                                         # relation endpoints must have the relation's node types
        types = {o['id']: o['type'] for o in out_nodes}
        assert (types[e['source']], types[e['target']]) == REL_TYPES[e['rel']], e
    return {'nodes': out_nodes, 'edges': [{'s': e['source'], 't': e['target'], 'rel': e['rel'], 'edge': e['edge']} for e in shown_edges],
            'total_nodes': total_nodes, 'total_edges': total_edges, 'shown_nodes': len(out_nodes), 'shown_edges': len(shown_edges)}


# ------------------------------------------------------------------------------------------------------------- explorers
def rq1_explorer(store, titles):
    from research.common.serialization import content_hash
    by_q = {}
    pools = {}
    for m in METHODS['RQ1']:
        for r in records('RQ1', m):
            q = r['query_id']
            if q not in pools:
                pool = load(DOC / 'rq1_repair/inputs' / (content_hash(q) + '.json'))['pool']
                pools[q] = {'nodes': {int(n['node_id']): {'label': n.get('label'), 'type': n.get('node_type'), 'relevance': n.get('relevance')} for n in pool['nodes']},
                            'edges': len(pool['edges']), 'seeds': [int(s['node_id'] if isinstance(s, dict) else s) for s in pool.get('seeds', [])]}
            p = pools[q]; d = diag(r); mt, o = r['metrics'], r['observation']
            nodes, edges, overlays = context_graph(r['output']['context'])
            for e in edges.values():
                for end in (e['source'], e['target']):
                    nodes.setdefault(end, {'label': None, 'type': None})
            missing = [n for n, v in nodes.items() if (v.get('label') is None or v.get('type') is None) and n not in p['nodes']]
            looked = store.nodes(missing) if missing else {}
            labels = {n: {'label': (p['nodes'].get(n) or {}).get('label') or (looked.get(n) or {}).get('label'),
                          'type': (p['nodes'].get(n) or {}).get('type') or (looked.get(n) or {}).get('node_type')} for n in nodes}
            gold, ans = set(r['gold_ids']), set(r['answer_ids'])
            flags = {n: {'gold': n in gold, 'answer': n in ans, 'seed': n in set(p['seeds'])} for n in nodes}
            prio = sorted(nodes, key=lambda n: (-((p['nodes'].get(n) or {}).get('relevance') or 0.), n))
            lat = d['context_ms'] + o['generation_ms'] if d.get('context_ms') is not None and o.get('generation_ms') is not None else None
            notes = {'kept_nodes': len(nodes), 'kept_relations': len(edges), 'pool_nodes': len(p['nodes']), 'pool_relations': p['edges'],
                     'graph_budget_chars': d.get('graph_budget'), 'overlay_items': overlays}
            if m == 'CM-B1':
                notes['paper_limit'] = d.get('fixed_paper_limit')
            if m == 'CM-01':
                notes.update(seed_relations=d.get('k_seed'), hops=d.get('m_hops'), trees=len(d.get('tree_scores') or []),
                             candidate_units=d.get('candidate_unit_count'), selected_units=len(d.get('selected_unit_ids') or []))
            if m == 'CM-02':
                notes.update(prized_nodes=sum(v > 0 for v in (d.get('node_prizes') or {}).values()),
                             prized_relations=sum(v > 0 for v in (d.get('edge_prizes') or {}).values()), edge_cost=d.get('edge_cost'),
                             pruned_leaves=len(d.get('pruned_leaves') or []))
            if m == 'CM-03':
                notes.update(keywords=d.get('keywords'), seeds=len(d.get('seed_ids') or []), converged=d.get('convergence'),
                             stop=d.get('reason'), connectors=len(d.get('connector_nodes') or []), pruned=len(d.get('pruned_nodes') or []))
            entry = {'answer_ids': r['answer_ids'], 'explanation': explanation(r['answer']), 'errors': r['errors'],
                     'metrics': {'answer_f1': mt.get('f1'), 'answer_em': mt.get('exact_match'), 'mrr': mt.get('mrr'), 'gold_coverage': mt.get('gold_coverage'),
                                 'context_tokens': mt.get('context_tokens'), 'input_tokens': mt.get('input_tokens'), 'output_tokens': mt.get('output_tokens'),
                                 'llm_calls': mt.get('llm_calls'), 'latency': lat, 'cm_ms': d.get('context_ms')},
                     'notes': notes, 'context': r['output']['context'], 'graph': graph_view(nodes, edges, labels, flags, prio)}
            by_q.setdefault(q, {})[m] = entry
            titles.update(r['gold_ids']); titles.update(r['answer_ids'])
    return {'methods': METHODS['RQ1'], 'queries': sorted(by_q), 'by_query': by_q}


def rq2_explorer(titles):
    from scripts.report_rq2_canonical import row
    sup = load(DOC / 'rq2_repair/supportability.json')['rows']
    by_q = {}
    for m in METHODS['RQ2']:
        for r in records('RQ2', m):
            q = r['query_id']; d = diag(r); x = row(r, sup)
            stages = [{'stage': s['stage'].split(':')[1] if s['stage'].count(':') >= 2 else s['stage'],
                       'detail': ':'.join(s['stage'].split(':')[2:-1]) or None,
                       'input_tokens': s['usage'].get('input_tokens'), 'output_tokens': s['usage'].get('output_tokens'), 'ms': s['usage'].get('generation_ms')}
                      for s in d.get('llm_stages', [])]
            detail = {}
            if m == 'CF-01':
                detail = {'groups': d.get('groups_included'), 'resolved': d.get('resolved'), 'unresolved': d.get('unresolved'),
                          'alignment_rules': dict(sorted(Counter(a['rule'] for a in d.get('alignments', [])).items())),
                          'group_order': [{'key': g['key'], 'members': g['members'], 'score': g['group_score'], 'sources': g['source_coverage']}
                                          for g in d.get('group_order', [])[:12]], 'truncated': d.get('group_truncated')}
            if m == 'CF-02':
                detail = {'structural_candidates': d.get('structural_candidates'), 'semantic_candidates': d.get('semantic_candidates'),
                          'selected': d.get('selected_structural'), 'semantic_fill': d.get('semantic_fill'), 'fallback': d.get('selector_fallback'),
                          'invalid_ids': d.get('selector_invalid_ids')}
            if m == 'CF-03':
                detail = {'findings': [{k: f.get(k) for k in ('source', 'status', 'candidate_answer', 'confidence', 'supporting_evidence', 'invalid_supporting_ids')}
                                       for f in d.get('source_findings', [])], 'fusion_retry': d.get('fusion_retry')}
            entry = {'answer_ids': r['answer_ids'], 'explanation': explanation(r['answer']), 'errors': r['errors'],
                     'metrics': {k: x[k] for k in ('answer_f1', 'answer_em', 'mrr', 'recall_at_5', 'input_tokens', 'output_tokens', 'total_tokens',
                                                   'llm_calls', 'context_characters', 'coverage_text', 'coverage_graph', 'coverage_structured')} | {'latency': x['intrinsic_ms']},
                     'source_counts': d.get('source_counts'), 'stages': stages, 'detail': detail, 'context': r['output']['context']}
            by_q.setdefault(q, {})[m] = entry
            titles.update(r['gold_ids']); titles.update(r['answer_ids'])
    return {'methods': METHODS['RQ2'], 'queries': sorted(by_q), 'by_query': by_q,
            'support': {q: {k: sup[q][k] for k in ('class', 'gold', 'gold_in_bundle')} for q in sorted(by_q)}}


def rq3_explorer(titles):
    from scripts.report_phase9 import intrinsic, adapt
    by_q = {}
    for m in METHODS['RQ3']:
        for r in records('RQ3', m):
            q = r['query_id']; d = diag(r); pm = A.per_record(r)
            steps, llm = ar_steps(m, d)
            metrics = {k: pm.get(k) for k in ('answer_f1', 'answer_em', 'recall_at_5', 'source_f1', 'unnecessary_retrieval', 'stopping_accuracy',
                                               'retrieval_calls', 'llm_calls', 'input_tokens', 'output_tokens', 'total_tokens')}
            metrics['latency'] = intrinsic(r)
            by_q.setdefault(q, {})[m] = {'answer_ids': r['answer_ids'], 'explanation': explanation(r['answer']), 'errors': r['errors'],
                                         'sources_called': pm['sources_called'], 'stop_reason': pm['stop_reason'], 'status': pm['status'],
                                         'failure_labels': A.failure_labels(adapt(r), r['gold_ids']), 'metrics': metrics, 'steps': steps, 'llm': llm,
                                         'context': r['output']['context']}
            titles.update(r['gold_ids']); titles.update(r['answer_ids'])
    return {'methods': METHODS['RQ3'], 'queries': sorted(by_q), 'by_query': by_q}


def rq4_explorer(titles):
    from scripts.report_phase9 import intrinsic
    routes = {r['query_id']: diag(r).get('extra') for r in records('RQ3', 'AR-B1')}
    by_q = {}
    for r in records('RQ4', 'INT-1'):
        q = r['query_id']; d = diag(r); pm = A.per_record(r)
        ar = d['ar']
        # the AR stage stores no routing detail; the rule router is deterministic, so its route is the one recorded for the
        # same question in part 3 (checked: identical sources queried)
        extra = routes.get(q) if ar['method'] == 'AR-B1' else None
        if extra is not None:
            assert extra['route']['sources'] == ar['sources_called'], q
        steps, llm = ar_steps(ar['method'], {**ar, 'extra': extra or {}})
        cf = d['cf']
        stages = [{'stage': s['stage'].split(':')[1] if s['stage'].count(':') >= 2 else s['stage'], 'input_tokens': s['usage'].get('input_tokens'),
                   'output_tokens': s['usage'].get('output_tokens'), 'ms': s['usage'].get('generation_ms')} for s in cf.get('llm_stages', [])]
        metrics = {k: pm.get(k) for k in ('answer_f1', 'answer_em', 'recall_at_5', 'source_f1', 'retrieval_calls', 'llm_calls', 'input_tokens',
                                           'output_tokens', 'total_tokens')}
        metrics['latency'] = intrinsic(r)
        by_q[q] = {'INT-1': {'answer_ids': r['answer_ids'], 'explanation': explanation(r['answer']), 'errors': r['errors'],
                             'sources_called': pm['sources_called'], 'stop_reason': pm['stop_reason'], 'status': pm['status'], 'metrics': metrics,
                             'steps': steps, 'llm': llm, 'cm': {'graph_in': len(d['cm']['graph_in']), 'graph_kept': len(d['cm']['graph_kept']),
                                                                'papers': d['cm']['papers']},
                             'cf': {'method': cf.get('method'), 'source_counts': cf.get('source_counts'), 'stages': stages},
                             'context': r['output']['context']}}
        titles.update(r['gold_ids']); titles.update(r['answer_ids'])
    return {'methods': ['INT-1'], 'queries': sorted(by_q), 'by_query': by_q}


# ------------------------------------------------------------------------------------------------------------- foundation
def corpus_stats():
    m = load(DATA / 'manifest.json'); au = m['audits']
    e = au['edges']['result']['official']
    return {'papers': au['nodes']['result']['entity_counts']['paper'], 'entities': au['nodes']['result']['entity_counts'],
            'nodes': au['csr']['result']['rows'], 'relations': {'WRITES': e['author___writes___paper'], 'AFFILIATED_WITH': e['author___affiliated_with___institution'],
                                                               'HAS_TOPIC': e['paper___has_topic___field_of_study'], 'CITES': e['paper___cites___paper']},
            'official_relations': m['official_directed_edges'], 'text_documents': au['faiss']['result']['rows_checked'],
            'embedding_dimension': au['faiss']['result']['dimension'], 'embedding_model': m['build_configuration']['models']['embedding'],
            'structured_rows': au['sql']['result']['joined_papers'], 'structured_fields': ['publication_year', 'publication_date', 'citation_count', 'paper_rank',
                                                                                        'venue_namespace', 'venue_name', 'document_type']}


def overlay_summary(o):
    if not o:
        return None
    o = json.loads(o) if isinstance(o, str) else o
    if o.get('kind') == 'noisy':
        return {'kind': 'noisy', 'distractors': {s: len(v) for s, v in sorted((o.get('distractors') or {}).items())}}
    if o.get('kind') == 'conflict':
        i = o.get('injection') or {}
        return {'kind': 'conflict', 'paper_id': i.get('paper_id'), 'field': i.get('field'), 'shown_value': i.get('after'), 'source': i.get('source')}
    return {'kind': o.get('kind')}


def foundation(store, reader, queries, titles):
    v = {q.query_id: q for q in reader.records('validation')}
    base = v[EXAMPLE_FAMILY + ':normal']
    rec = load(BENCH / base.model_dump(mode='json')['gold_evidence']['construction_record'])
    cand = {s: set(load(BENCH / x['path'])) for s, x in rec['candidate_sets'].items()}
    T, G, S = cand['text'], cand['graph'], cand['structured']
    overlap = {'text': len(T), 'graph': len(G), 'structured': len(S), 'text+graph': len(T & G), 'text+structured': len(T & S),
               'graph+structured': len(G & S), 'all': len(T & G & S)}
    assert sorted(T & G & S) == sorted(base.gold_answer_ids), 'example answer must be the overlap'
    pid = int(base.gold_answer_ids[0])
    text = store.texts([pid])[pid]; row = store.structured_rows([pid])[pid]
    cond = rec['conditions']
    phrases = cond['text']['phrases']
    hit = next((p for p in phrases if p.lower() in (text['abstract'] or '').lower()), None)
    # graph: witness path + the paper's direct neighbourhood (bounded, deterministic)
    csr = store.csr; s0, s1 = int(csr['indptr'][pid]), int(csr['indptr'][pid + 1])
    nb = [(int(csr['neighbors'][i]), int(csr['relation_ids'][i]), bool(csr['derived_inverse'][i]), int(csr['edge_ids'][i])) for i in range(s0, s1)]
    edges = {}
    for n, rel, inv, eid in nb:
        e = canonical_edge(eid, inv, pid, n, REL_ID[rel]); edges[e['edge']] = e
    for w in rec['graph_witness_paths'][str(pid)]:
        e = canonical_edge(w['edge_id'], w['derived_inverse'], w['source'], w['target'], REL_ID[w['relation_id']]); edges[e['edge']] = e
    witness = {canonical_edge(w['edge_id'], w['derived_inverse'], w['source'], w['target'], REL_ID[w['relation_id']])['edge']
               for w in rec['graph_witness_paths'][str(pid)]}
    ids = sorted({x for e in edges.values() for x in (e['source'], e['target'])})
    info = store.nodes(ids)
    labels = {n: {'label': info[n]['label'], 'type': info[n]['node_type']} for n in ids}
    keep, per = set(witness), Counter()
    for k, e in sorted(edges.items()):                         # neighbourhood cap per relation type (witness relations always kept)
        if k in witness:
            continue
        if per[e['rel'], e['source'] == pid] < (8 if e['rel'] in ('WRITES', 'HAS_TOPIC') else 4):
            keep.add(k); per[e['rel'], e['source'] == pid] += 1
    edges = {k: e for k, e in edges.items() if k in keep}
    nodes = {n: {} for e in edges.values() for n in (e['source'], e['target'])}
    anchor = int(cond['graph']['anchor_id'])
    flags = {n: {'gold': n == pid, 'anchor': n == anchor, 'witness': any(n in (edges[k]['source'], edges[k]['target']) for k in witness)} for n in nodes}
    graph = graph_view(nodes, edges, labels, flags)
    for e in graph['edges']:
        e['witness'] = e['edge'] in witness
    counter = {s: [{'id': int(i), 'title': None} for i in ids_[:3]] for s, ids_ in sorted(rec['modality_necessity_counterexamples'].items())}
    titles.update(int(i) for xs in rec['modality_necessity_counterexamples'].values() for i in xs[:3])
    variants = {}
    for stress in ('normal', 'noisy', 'conflict', 'unanswerable'):
        q = v[EXAMPLE_FAMILY + ':' + stress]
        variants[stress] = {'query_id': q.query_id, 'question': q.question, 'gold': [int(x) for x in q.gold_answer_ids], 'overlay': overlay_summary(reader.overlay(q))}
    return {'example': {'query_id': base.query_id, 'question': base.question, 'gold': pid, 'conditions': cond, 'candidates': overlap,
                        'necessity': {s: {'count': {'text': len((G & S) - T), 'graph': len((T & S) - G), 'structured': len((T & G) - S)}[s], 'examples': counter[s]}
                                      for s in ('text', 'graph', 'structured')},
                        'views': {'text': {'title': text['title'], 'abstract': text['abstract'], 'match': hit},
                                  'structured': {k: (str(x) if k == 'publication_date' and x is not None else x) for k, x in row.items()},
                                  'graph': graph, 'anchor': {'id': anchor, 'label': labels.get(anchor, {}).get('label')}},
                        'variants': variants},
            'corpus': corpus_stats(), 'benchmark': benchmark_stats(reader, queries)}


def benchmark_stats(reader, queries):
    s = load(BENCH / 'benchmark_stats.json')
    gen = [q for q in reader.records('validation') if q.query_id.startswith('generated:')]
    fams = sorted({A.family(q.query_id) for q in gen})
    mod = Counter(q.modality_class for q in gen if q.query_id.endswith(':normal'))
    return {'splits': s['split'], 'generated_validation': len(gen), 'families': len(fams), 'families_by_modality': dict(sorted(mod.items())),
            'variants': ['normal', 'noisy', 'conflict', 'unanswerable'],
            'cohorts': {rq: {'queries': len(qs), 'families': len({A.family(q) for q in qs}),
                             'variants': sorted({q.rsplit(':', 1)[1] for q in qs})} for rq, qs in sorted(queries.items())}}


def query_table(reader, cohorts, titles):
    v = {q.query_id: q for q in reader.records('validation')}
    sup = load(DOC / 'rq2_repair/supportability.json')['rows']
    out = {}
    for q in sorted(set().union(*cohorts.values())):
        b = v[q]
        out[q] = {'question': b.question, 'family': A.family(q), 'stress': q.rsplit(':', 1)[1], 'modality': b.modality_class,
                  'oracle_sources': sorted(A.ORACLE[b.modality_class], key=['text', 'graph', 'structured'].index),
                  'hop': b.model_dump(mode='json')['reasoning']['complexity'], 'answerable': b.answerable, 'gold': [int(x) for x in b.gold_answer_ids],
                  'studies': [rq for rq in sorted(cohorts) if q in cohorts[rq]], 'support': (sup.get(q) or {}).get('class'),
                  'overlay': overlay_summary(reader.overlay(b))}
        titles.update(int(x) for x in b.gold_answer_ids)
    return out


# ------------------------------------------------------------------------------------------------------------- stats demo
DEMO_PAIRS = [('RQ3', 'source_f1', 'AR-B1', 'AR-B0'), ('RQ3', 'total_tokens', 'AR-03', 'AR-B1'), ('RQ1', 'answer_f1', 'CM-01', 'CM-B1'),
              ('RQ4', 'source_f1', 'INT-1', 'AR-B0')]


def stats_demo(results):
    from scripts.report_phase9 import intrinsic
    def rows(rq, m):
        if rq == 'RQ1':
            return [{'query_id': r['query_id'], 'answer_f1': r['metrics']['f1']} for r in records('RQ1', m)]
        src = 'RQ4' if (rq == 'RQ4' and m == 'INT-1') else 'RQ3'
        return [{**A.per_record(r), 'latency': intrinsic(r)} for r in records(src, m)]
    out = []
    for rq, metric, a, b in DEMO_PAIRS:
        ra, rb = {x['query_id']: x[metric] for x in rows(rq, a)}, {x['query_id']: x[metric] for x in rows(rq, b)}
        deltas = {q: ra[q] - rb[q] for q in sorted(ra.keys() & rb.keys()) if ra[q] is not None and rb[q] is not None}
        fam = A.cluster_mean(deltas)
        reported = next(t for t in results[rq]['tests'][metric] if (t['a'], t['b']) == (a, b))
        p = A.sign_flip_p(deltas)
        assert abs(p - reported['p']) < 1e-12, (rq, metric, a, b, p, reported['p'])     # the demo reproduces the frozen p exactly
        out.append({'rq': rq, 'metric': metric, 'a': a, 'b': b, 'family_sums': {f: sum(x) for f, x in sorted(fam.items())},
                    'family_sizes': {f: len(x) for f, x in sorted(fam.items())}, 'per_query': deltas, 'reported': reported})
    return out


# ------------------------------------------------------------------------------------------------------------- write
def dump(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def build():
    from research.baselines.stores import Stores
    from research.baselines.config import BaselineOptions
    reader = BenchmarkReader(BENCH)
    results = {'RQ1': rq1_results(), 'RQ2': rq_results('RQ2'), 'RQ3': rq_results('RQ3'), 'RQ4': rq_results('RQ4')}
    for rq in results:
        results[rq].update(methods=METHODS[rq], controls=CONTROLS[rq], pareto_axes=dict(zip(('higher', 'lower'), PARETO_AXES.get(rq, ([], [])))))
    titles = set()
    store = Stores(DATA, WORK, BaselineOptions(), modalities=('text', 'graph', 'structured'))
    try:
        ex = {'RQ1': rq1_explorer(store, titles), 'RQ2': rq2_explorer(titles), 'RQ3': rq3_explorer(titles), 'RQ4': rq4_explorer(titles)}
        cohorts = {rq: e['queries'] for rq, e in ex.items()}
        queries = query_table(reader, cohorts, titles)
        found = foundation(store, reader, cohorts, titles)
        ids = sorted(titles); papers = {}
        for i in range(0, len(ids), 400):
            papers.update({str(k): v['label'] for k, v in store.nodes(ids[i:i + 400]).items()})
    finally:
        store.close()
    for s, ex_ in found['example']['necessity'].items():
        for x in ex_['examples']:
            x['title'] = papers.get(str(x['id']))
    files = {'results.json': dump(results), 'queries.json': dump(queries), 'papers.json': dump(papers), 'foundation.json': dump(found),
             'stats_demo.json': dump(stats_demo(results))}
    for rq, e in ex.items():
        files['explorer_%s.json.gz' % rq.lower()] = gzip.compress(dump(e), compresslevel=9, mtime=0)
    sources = sorted([*ANALYSIS.values(), DOC / 'rq2_repair/supportability.json', DOC / 'rq4/selection_local.json', DOC / 'SCOPE_REVISION_2026-10-15.json',
                      BENCH / 'validation.jsonl', BENCH / 'benchmark_stats.json', DATA / 'manifest.json'])
    manifest = {'bundle_version': 1, 'files': {k: {'sha256': hashlib.sha256(v).hexdigest(), 'bytes': len(v)} for k, v in sorted(files.items())},
                'sources': {p.relative_to(ROOT).as_posix(): digest(p) for p in sources},
                'records': {rq: {m: len(list((RUNS[rq] / m / 'records').glob('*.json'))) for m in (METHODS[rq] if rq != 'RQ4' else ['INT-1'])} for rq in RUNS}}
    manifest['bundle_sha256'] = hashlib.sha256(''.join('%s:%s\n' % (k, v['sha256']) for k, v in sorted(manifest['files'].items())).encode()).hexdigest()
    files['manifest.json'] = (json.dumps(manifest, indent=1, sort_keys=True) + '\n').encode('utf-8')
    return files


def main():
    files = build()
    if '--check' in sys.argv:
        bad = [k for k, v in files.items() if not (OUT / k).exists() or (OUT / k).read_bytes() != v]
        print('BUNDLE', 'IDENTICAL' if not bad else 'DIFFERS: ' + ', '.join(bad)); sys.exit(1 if bad else 0)
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in files.items():
        (OUT / k).write_bytes(v)
    m = json.loads(files['manifest.json'])
    print('WROTE showcase/bundle:', ', '.join('%s %.0f KB' % (k, len(v) / 1024) for k, v in sorted(files.items())), '| bundle', m['bundle_sha256'][:16])


if __name__ == '__main__':
    main()
