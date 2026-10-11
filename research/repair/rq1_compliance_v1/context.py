"""Fixed mixed-source envelope; only graph context varies between CM methods."""
from research.baselines.system import build_context
from research.common.serialization import content_hash

def pass_through(items,sources):
    """Reuse Phase6 serializer and equal per-active-source character allocation."""
    budget=24000//len(sources)
    result={}
    for source in sources:
        if source=='graph':continue
        context,retained,truncated=build_context(tuple(e for e in items if e.source_type==source),(source,),budget)
        result[source]={'context':context,'retained':retained,'truncated':truncated,
            'sha256':content_hash({'context':context,'retained':retained,'truncated':truncated})}
    return result,budget

def assemble(passed,sources,graph_context):
    budget=24000//len(sources)
    graph='[GRAPH]\n'+graph_context
    if len(graph)>budget:raise ValueError('Graph budget exceeded')
    text=''.join(graph if s=='graph' else passed[s]['context'] for s in sources)
    if len(text)>24000:raise ValueError('Global budget exceeded')
    return text
