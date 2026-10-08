"""Streamlit presentation only; data/evidence are rendered as text, never executable HTML."""
import json
from research.evaluation.contracts import SystemOutput
from research.baselines.structured import QueryPlan,compile_plan


def graph_dot(nodes,edges):
    if len(nodes)>101 or len(edges)>100:raise ValueError('Graph display exceeds bounded view.')
    lines=['digraph G {','rankdir=LR;','node [shape=box, style="rounded", fontsize=11];']
    for node in nodes:
        label=node.get('label')
        display=f"{node['node_id']} | {node.get('node_type','entity')}\n"+(label[:100] if label is not None else '[source label NULL]')
        lines.append(f'"{int(node["node_id"])}" [label={json.dumps(display,ensure_ascii=False)}];')
    for edge in edges:
        label=edge['relation']+(' (inverse)' if edge.get('derived_inverse') else '')
        lines.append(f'"{int(edge["source"])}" -> "{int(edge["target"])}" [label={json.dumps(label)}, fontsize=9];')
    return '\n'.join(lines+['}'])


def show_evidence(st,run):
    output=SystemOutput.model_validate(run['output'])
    st.caption('Results for: '+run['question'])
    st.write('Returned paper IDs',list(output.ranked_paper_ids or ()))
    if not output.evidence:st.info('No evidence returned. See the execution trace for unsupported intent or missing graph seeds.')
    for item in output.evidence or ():
        retained=item.evidence_id in (output.retained_evidence_ids or ())
        with st.expander(f'{item.source_type.upper()} · {item.canonical_id} · '+('in context' if retained else 'outside context budget')):
            payload=json.loads(item.payload) if item.payload else {}
            st.caption(f'Evidence ID: {item.evidence_id} · source-specific score: {item.score:.5f}')
            if item.source_type=='text':
                st.subheader(payload.get('title','Text evidence'))
                st.text(payload.get('abstract',payload.get('content','')))
            elif item.source_type=='graph':
                st.write('Title',payload.get('title'))
                if payload.get('path'):
                    st.dataframe(payload['path'],hide_index=True,width='stretch')
                    if payload.get('nodes'):st.graphviz_chart(graph_dot(payload['nodes'],payload['path']))
                else:st.caption('The selected seed is itself a paper; no traversal path was needed.')
            else:st.json(payload,expanded=True)
            st.json({'provenance':[p.model_dump() for p in item.provenance],'metadata':json.loads(item.metadata or '{}')},expanded=False)
    diagnostics=json.loads(output.diagnostics or '{}')
    plan=diagnostics.get('structured',{}).get('plan')
    if plan:
        st.subheader('Structured predicate plan')
        sql,args=compile_plan(QueryPlan.model_validate(plan),diagnostics['structured']['result_limit'])
        st.code(sql,language='sql');st.write('Bound parameters',args)
    for error in output.errors:st.error(f'{error.stage} · {error.code}: {error.message}')


def show_answer(st,run):
    result=SystemOutput.model_validate(run['output'])
    if not run['generation_attempts']:
        st.caption('No answer generated. Retrieval-only execution makes zero LLM calls.')
    elif result.answer_ids is not None:
        if result.answer_ids:st.success('Grounded paper IDs: '+', '.join(map(str,result.answer_ids)))
        else:st.info('The model abstained (empty answer set). This does not prove the question is unanswerable.')
        st.code(result.answer or '',language='json')
    else:st.warning('No valid answer was produced. Details remain in the trace.')
