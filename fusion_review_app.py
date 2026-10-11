"""Read-only Phase 8 viewer. No retrieval, API calls, or benchmark editing."""
import json
from pathlib import Path
import streamlit as st

D = Path(__file__).resolve().parent / 'documentation/phase8'
st.set_page_config(page_title='RQ2 Fusion Comparison', layout='wide')
st.title('RQ2 Fusion Comparison')
st.caption('Read-only cached validation artifacts. No retrieval or generation runs from this page.')
manifest = json.loads((D / 'bundle_manifest.json').read_text(encoding='utf-8'))
query = st.selectbox('Validation query', [row['query_id'] for row in manifest['files']])
row = next(row for row in manifest['files'] if row['query_id'] == query)
frozen = json.loads((D / row['path']).read_text(encoding='utf-8'))
st.write(frozen['question'])
st.code('Identical incoming bundle SHA-256: ' + row['bundle_hash'])
with st.expander('Exact incoming evidence and provenance'):
    st.json(frozen)
method = st.selectbox('Fusion method', ['CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03'])
mode = st.selectbox('Execution', ['context_only', 'generation'])
records = D / mode / method / 'records.jsonl'
record = next((json.loads(line) for line in records.read_text(encoding='utf-8').splitlines() if json.loads(line)['query_id'] == query), None) if records.exists() else None
if record is None:
    st.info('No execution artifact for this selection. Generation requires separate explicit approval.')
else:
    output = record['output']
    diagnostics = json.loads(output['diagnostics'])
    st.write('Status:', diagnostics['generation_status'])
    st.json({'metrics': record['metrics'], 'observations': record['observation']})
    st.subheader('Fused context')
    st.code(output['context'] or 'NULL — late-fusion final context requires intermediate generation', language=None)
    for title, key in [('Entity alignments', 'alignments'), ('Selector decisions', 'selector'),
                       ('Source-specific inputs', 'source_contexts'), ('Intermediate and final responses', 'stage_results')]:
        with st.expander(title): st.json(diagnostics.get(key, []))
    with st.expander('Complete execution trace'): st.json(diagnostics)
