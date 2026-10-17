import json
import pandas as pd
import streamlit as st
from showcase.lib import state, ui
from showcase.lib.fmt import fmt

C, B = state.content(), state.bundle()
R = C['reproducibility']
man = B.manifest

ui.page_header('Explore', 'Reproducibility', R['page_intro'])
ui.toc([('how', 'How results are protected'), ('bundle', 'This app’s data'), ('setup', 'Setup'), ('rebuild', 'Rebuild')])

ui.section('How results are protected', 'how')
for t in R['points'] + C['evaluation']['protocol']:
    st.markdown('- ' + t)

ui.section('This app’s data', 'bundle')
c1, c2 = st.columns([2, 1])
with c1:
    ui.kpi('Bundle checksum (SHA-256)', man['bundle_sha256'][:24] + '…', 'all %d files verified at start-up' % len(man['files']) if B.verified
           else 'verification FAILED for: ' + ', '.join(k for k, ok in B.checks.items() if not ok))
with c2:
    ui.kpi('Run records exported', fmt(sum(n for rq in man['records'].values() for n in rq.values()), 'count'), 'across the four studies')
st.dataframe(pd.DataFrame([{'File': k, 'Bytes': fmt(v['bytes'], 'count'), 'SHA-256': v['sha256'], 'Verified': '✅' if B.checks.get(k) else '❌'}
                           for k, v in sorted(man['files'].items())]), hide_index=True, width='stretch')
st.markdown('**Built from these frozen sources**')
st.dataframe(pd.DataFrame([{'Source': k, 'SHA-256': v} for k, v in sorted(man['sources'].items())]), hide_index=True, width='stretch')
st.markdown('**Run records per study and method**')
st.dataframe(pd.DataFrame([{'Study': 'Part %s' % rq[-1], 'Method': m, 'Records': n} for rq, ms in sorted(man['records'].items()) for m, n in ms.items()]),
             hide_index=True, width='content')
st.download_button('Download all study results (JSON)', json.dumps(B.results, indent=1, sort_keys=True).encode('utf-8'),
                   file_name='showcase_results.json', mime='application/json')

ui.section('Setup', 'setup')
st.markdown('- **Answer model:** one locally served `gpt-oss:20b` model for every method and study (temperature 0, fixed seed per question, '
            'low reasoning effort, JSON output, 1,024-token cap per call).\n'
            '- **Retrievers:** MiniLM sentence embeddings with a FAISS index (text), bounded graph traversal (graph), read-only DuckDB queries (structured).\n'
            '- **Evaluation:** validation questions only; the locked test set is out of scope.')

ui.section('Rebuild', 'rebuild')
st.markdown('From the repository root:')
st.code('python scripts/build_showcase_bundle.py           # export the bundle from the frozen study outputs\n'
        'python scripts/build_showcase_bundle.py --check   # confirm the committed bundle is reproduced byte for byte\n'
        'python showcase/launch.py                         # start this app', language='bash')

ui.nav_footer(*state.neighbours('pages/p11_repro.py'))
