"""Separate Streamlit research workspace. No scientific algorithms live here."""
import json
from pathlib import Path
import streamlit as st
from research.common.config import PROJECT_ROOT
from research.ui.service import ResearchService,performance,comparison
from research.ui.explorer import DatasetExplorer
from research.ui.views import show_evidence,show_answer,graph_dot

EXAMPLES=json.loads((Path(__file__).with_name('examples.json')).read_text(encoding='utf-8'))
METHOD_NAMES={'B1':'Text RAG','B2':'GraphRAG','B3':'Structured retrieval','B4':'Fixed multi-source'}


@st.cache_resource
def get_service():return ResearchService()


@st.cache_resource
def get_explorer():return DatasetExplorer()


def remember(run):
    history=[r for r in st.session_state.history if r['run_id']!=run['run_id']]
    st.session_state.history=(history+[run])[-20:]


def main():
    st.set_page_config(page_title='STaRK Research Lab',page_icon='🔬',layout='wide')
    st.markdown('''<style>
    .block-container {max-width:1480px;padding-top:2rem;}
    [data-testid="stMetric"] {border:1px solid #d9e3e7;border-radius:12px;padding:16px;}
    .research-tag {font-size:.8rem;letter-spacing:.12em;color:#147d78;font-weight:700;}
    </style><div class="research-tag">MMG–STaRK–MAG / RESEARCH WORKSPACE</div>''',unsafe_allow_html=True)
    st.title('Research Lab')
    st.caption('Inspect real data, compare B1–B4, and follow every evidence item into its context.')
    for name,value in {'history':[],'current_run':None,'comparisons':[],'question':EXAMPLES[0]['question'],'method':'B1',
                       'comparison_question':EXAMPLES[0]['question'],'paper_rows':[],'paper_detail':None,'neighborhood':None}.items():
        if name not in st.session_state:st.session_state[name]=value
    with st.sidebar:
        st.header('Run controls')
        st.success('Retrieval only by default')
        st.caption('Groq runs only when you press the explicit generation button. No background generation or batch experiments.')
        st.divider();st.write('**Frozen baseline settings**')
        st.caption('Top-K 5 · graph depth 2 · 3 seeds\n\n24,000-character context cap\n\nGroq: openai/gpt-oss-120b\n\nTemperature 0 · max completion 1,024')
        st.caption('Dataset: 700,244 papers\n\n1,872,968 nodes\n\n19,919,698 official directed edges')
        if st.button('Release loaded data',key='release_data'):
            get_service().close();get_explorer().close();st.success('Data resources released. Saved session results remain available.')
        st.caption('Separate from the Phase 0 demo. No dataset or benchmark edits.')
    playground,explorer,compare,dashboard,trace=st.tabs(['Query playground','Dataset explorer','Compare methods','Performance','Execution trace'])
    with playground:
        st.subheader('Ask a research question')
        a,b=st.columns([4,1])
        example=a.selectbox('Representative example',[e['label'] for e in EXAMPLES],key='example')
        if b.button('Load example',key='load_example',width='stretch'):
            selected=next(e for e in EXAMPLES if e['label']==example)
            st.session_state.question=selected['question'];st.session_state.method=selected['method']
            st.session_state.comparison_question=selected['question']
        st.caption(next(e['note'] for e in EXAMPLES if e['label']==example))
        question=st.text_area('Question',key='question',height=130,max_chars=12000)
        method=st.selectbox('Baseline',list(METHOD_NAMES),key='method',format_func=lambda v:v+' · '+METHOD_NAMES[v])
        submitted=st.button('Retrieve evidence — no LLM',key='retrieve',type='primary')
        if submitted:
            try:
                with st.spinner('Running '+method+' on the frozen representations…'):
                    run=get_service().retrieve(question,method)
                st.session_state.current_run=run;remember(run)
            except Exception as exc:st.error('Retrieval could not complete ('+type(exc).__name__+'). Check the local dataset and configuration.')
        run=st.session_state.current_run
        if run:
            st.divider();st.subheader(run['method']+' · retrieved evidence')
            show_evidence(st,run)
            changed=question.strip()!=run['question'] or method!=run['method']
            if changed:st.warning('The question or method differs from these results. Retrieve again before generating.')
            st.subheader('Grounded answer')
            st.caption('This sends the displayed question and retained context to Groq. Maximum 1,024 completion tokens; one request per snapshot.')
            disabled=changed or bool(run['generation_attempts']) or bool(run['output']['errors']) or not run['output']['retained_evidence_ids']
            if st.button('Generate grounded answer with Groq',key='generate',disabled=disabled):
                try:
                    with st.spinner('Generating from this evidence snapshot…'):
                        run=get_service().generate(run,explicit_request=True)
                    st.session_state.current_run=run;remember(run)
                except Exception as exc:st.error('Generation was not started ('+type(exc).__name__+'). Retrieve a new valid snapshot to retry.')
            show_answer(st,run)
    with explorer:
        st.subheader('Explore the frozen dataset')
        st.caption('Browse at most 20 papers and 25 relationships at a time. Explorer data never enters a model prompt.')
        with st.form('paper_search_form'):
            term=st.text_input('Paper title contains',key='paper_search')
            search=st.form_submit_button('Search papers',key='search_papers')
        if search:
            try:st.session_state.paper_rows=get_explorer().papers(term);st.session_state.paper_term=term
            except Exception as exc:st.error('Paper search unavailable ('+type(exc).__name__+').')
        if st.session_state.paper_rows:
            st.dataframe(st.session_state.paper_rows,hide_index=True,width='stretch')
            if st.button('Next 20 papers',key='next_papers'):
                st.session_state.paper_rows=get_explorer().papers(st.session_state.get('paper_term',''),st.session_state.paper_rows[-1]['paper_id']);st.rerun()
        elif search:st.info('No matching papers.')
        with st.form('paper_form'):
            paper_id=st.number_input('STaRK paper ID',min_value=0,max_value=1872967,value=1172724,step=1,key='paper_id')
            open_paper=st.form_submit_button('Open paper',key='open_paper')
        if open_paper:
            try:st.session_state.paper_detail=get_explorer().paper(int(paper_id))
            except Exception as exc:st.error('Paper unavailable ('+type(exc).__name__+').')
        detail=st.session_state.paper_detail
        if detail:
            st.markdown('**'+detail['text']['title']+'**');st.text(detail['text']['abstract'])
            left,right=st.columns(2)
            with left:st.write('Canonical identity');st.json(detail['registry'],expanded=True)
            with right:st.write('Recorded structured attributes');st.json(detail['structured'],expanded=True)
            st.caption('NULL is preserved as unknown. Venue namespace and document type remain separate.')
        elif open_paper:st.info('This ID is not a paper in the text view.')
        with st.form('graph_form'):
            node=st.number_input('Graph node ID',min_value=0,max_value=1872967,value=1172724,step=1,key='node_id')
            offset=st.number_input('Relationship offset',min_value=0,value=0,step=25,key='edge_offset')
            open_graph=st.form_submit_button('Inspect 25 relationships',key='open_graph')
        if open_graph:
            try:st.session_state.neighborhood=get_explorer().neighbors(int(node),int(offset))
            except Exception as exc:st.error('Neighborhood unavailable ('+type(exc).__name__+').')
        neighborhood=st.session_state.neighborhood
        if neighborhood:
            st.caption(f"Showing {len(neighborhood['rows'])} of {neighborhood['degree']} traversal relationships. Inverse rows are derived, not additional official source edges.")
            if neighborhood['rows']:
                st.graphviz_chart(graph_dot(neighborhood['nodes'],neighborhood['rows']))
                st.dataframe(neighborhood['rows'],hide_index=True,width='stretch')
            else:st.info('No relationships at this offset.')
    with compare:
        st.subheader('Same question, independent baselines')
        with st.form('comparison_form'):
            comparison_question=st.text_area('Comparison question',key='comparison_question',max_chars=12000)
            methods=st.multiselect('Methods',['B1','B2','B3','B4'],default=['B1','B2','B3','B4'],key='comparison_methods')
            compare_now=st.form_submit_button('Compare retrieval — no LLM',key='compare',type='primary')
        if compare_now:
            if not methods:st.warning('Select at least one method.')
            else:
                runs=[];progress=st.progress(0,text='Retrieving independently…')
                for i,selected in enumerate(methods):
                    try:
                        run=get_service().retrieve(comparison_question,selected);runs.append(run);remember(run)
                    except Exception as exc:st.error(selected+' failed ('+type(exc).__name__+').')
                    progress.progress((i+1)/len(methods),text=selected+' complete')
                st.session_state.comparisons=runs
        runs=st.session_state.comparisons
        if runs:
            st.caption('Comparison results for: '+runs[0]['question'])
            st.dataframe([performance(r) for r in runs],hide_index=True,width='stretch')
            st.dataframe(comparison(runs),hide_index=True,width='stretch')
            st.caption('Scores and source-order ranks are method-specific. These are interactive inspections, not benchmark accuracy estimates.')
            for run in runs:
                with st.expander(run['method']+' evidence and predicate plan'):show_evidence(st,run)
    with dashboard:
        st.subheader('Measured performance')
        history=st.session_state.history
        if history:
            rows=[performance(r) for r in history];columns=st.columns(4)
            columns[0].metric('Recorded inspections',len(rows));columns[1].metric('LLM calls',sum(r['llm_calls'] or 0 for r in rows))
            for col,key,label in ((columns[2],'input_tokens','Measured input tokens'),(columns[3],'output_tokens','Measured output tokens')):
                values=[r[key] for r in rows if r[key] is not None];col.metric(label,sum(values) if values else '—')
            st.dataframe(rows,hide_index=True,width='stretch')
            st.caption('Last 20 inspections. Unavailable metrics remain NULL; token totals include only measured usage. Gold-dependent metrics are unavailable for ad hoc questions. No monetary estimate without pricing metadata.')
        else:st.info('Run retrieval to populate this dashboard. Nothing executes automatically.')
        with st.expander('Saved Phase 6 validation results — read only'):
            path=PROJECT_ROOT/'documentation/phase6/comparison.json'
            if path.exists():
                st.dataframe(json.loads(path.read_text(encoding='utf-8')),hide_index=True,width='stretch')
                st.caption('Historical smoke results, not a full benchmark. Opening this table makes no calls and does not supply gold to any prompt.')
    with trace:
        st.subheader('Follow the complete execution')
        if not st.session_state.history:st.info('Retrieve evidence first to inspect a trace.')
        else:
            runs=st.session_state.history
            index=st.selectbox('Inspection',range(len(runs)),format_func=lambda i:runs[i]['method']+' · '+runs[i]['question'][:75]+' · '+runs[i]['run_id'][:8],key='trace_index')
            run=runs[index];out=run['output']
            st.write('1. Query and frozen controls');st.json({k:v for k,v in run.items() if k not in ('output','generation_attempts')},expanded=False)
            st.write('2. Source execution');st.json(json.loads(out['diagnostics'] or '{}'),expanded=True)
            st.write('3. Evidence inclusion');st.json({'retrieved': [e['evidence_id'] for e in (out['evidence'] or [])], 'retained':out['retained_evidence_ids']},expanded=True)
            st.write('4. Exact constructed context');st.code(out['context'] or '',language=None)
            st.write('5. Generation and measurements');st.json({'answer':out['answer'],'answer_ids':out['answer_ids'],'observation':out['observation'],'attempts':run['generation_attempts'],'errors':out['errors']},expanded=True)
            st.download_button('Download this inspection as JSON',json.dumps(run,ensure_ascii=False,indent=2),file_name='research-inspection-'+run['run_id']+'.json',mime='application/json',key='download_trace')
