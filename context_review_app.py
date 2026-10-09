"""Read-only RQ1 review viewer; no model, retrieval or generation execution."""
import json
from pathlib import Path
import streamlit as st
from research.common.config import PROJECT_ROOT
from research.ui.views import graph_dot
D=PROJECT_ROOT/'documentation/phase7'
def main():
    st.set_page_config(page_title='RQ1 Context Review',layout='wide')
    st.title('Context Management Review')
    st.caption('Saved Phase 7 validation artifacts · read only · no retrieval or generation calls')
    if not (D/'summary.json').exists():st.info('The Phase 7 comparison is not yet materialized.');return
    summary=json.loads((D/'summary.json').read_text(encoding='utf-8'))
    st.table([{k:r[k] for k in ('method','queries','gold_coverage','recall@5','context_characters','context_ms','fallback_count')} for r in summary])
    st.image(str(D/'pareto.png'));st.caption('Retrieval/context quality only. Answer metrics and evidence-annotation coverage are unavailable.')
    method=st.selectbox('Context method',[r['method'] for r in summary])
    records=[json.loads(x) for x in (D/'runs'/method/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    index=st.selectbox('Validation query',range(len(records)),format_func=lambda i:records[i]['query_id'])
    r=records[index];diagnostics=json.loads(r['output']['diagnostics']);st.json({'labels':r['labels'],'stress':r['stress'],'metrics':r['metrics']},expanded=False)
    manifest=json.loads((D/'pool_manifest.json').read_text(encoding='utf-8'));row=next(x for x in manifest['files'] if x['query_id']==r['query_id'])
    pool=json.loads((D/row['path']).read_text(encoding='utf-8'));st.write(pool['question'])
    left,right=st.columns(2)
    with left:
        st.subheader('Before context control');st.caption(f"{len(pool['nodes'])} nodes · {len(pool['edges'])} edges")
        st.dataframe([{k:n[k] for k in ('node_id','label','node_type','depth','overlay')} for n in pool['nodes']],hide_index=True,width='stretch')
    selected=set(diagnostics['selected_nodes']);keys=set(diagnostics['selected_edges'])
    with right:
        st.subheader('After context control');st.caption(f"{len(selected)} nodes · {len(keys)} edges · {len(r['output']['context'])} characters")
        st.dataframe([{k:n[k] for k in ('node_id','label','node_type','depth','overlay')} for n in pool['nodes'] if n['node_id'] in selected],hide_index=True,width='stretch')
    edges=[e for e in pool['edges'] if e['key'] in keys][:25];ids={e['source'] for e in edges}|{e['target'] for e in edges}
    if edges:st.graphviz_chart(graph_dot([n for n in pool['nodes'] if n['node_id'] in ids],edges));st.caption('Visualization capped at 25 selected edges; full selection remains in diagnostics.')
    st.subheader('Selection and optimization diagnostics');st.json(diagnostics,expanded=False)
    st.subheader('Exact context');st.code(r['output']['context'],language=None)
if __name__=='__main__':main()
