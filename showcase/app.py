"""Multi-Modal GraphRAG showcase. Run from the repository root:

    streamlit run showcase/app.py          (or: python showcase/launch.py, which also applies the theme)

Every number on screen comes from the verified data bundle in showcase/bundle/ (built from the frozen study outputs).
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from showcase import config
from showcase.lib import state, ui
from showcase.lib.bundle import BundleError

_present = st.query_params.get('present') == '1'
st.set_page_config(page_title='Multi-Modal GraphRAG', page_icon=':material/hub:', layout='wide',
                   initial_sidebar_state='collapsed' if _present else 'expanded')
if 'presenting' not in st.session_state:
    st.session_state.presenting = _present

sections = {}
for f, title, icon, url, sec in state.PAGES:
    sections.setdefault(sec, []).append(st.Page(f, title=title, icon=icon, url_path=url, default=url == 'problem'))
nav = st.navigation(sections, position='sidebar', expanded=True)

ui.inject_css(state.presenting())
try:
    bundle = state.bundle()
except BundleError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    if config.PROFILE == 'full':
        ui.html(ui.badge('Live questions enabled', 'live'))
    else:
        ui.html(ui.badge('Recorded results', 'replay'))

    def _toggle():
        if st.session_state.presenting:
            st.query_params['present'] = '1'
        elif 'present' in st.query_params:
            del st.query_params['present']
    st.toggle('Presentation mode', key='presenting', on_change=_toggle, help='Larger text and a cleaner screen for projecting.')
    st.caption('Data bundle `%s` · %s' % (bundle.sha256[:12], 'checksums verified' if bundle.verified else 'CHECKSUM MISMATCH'))

if not bundle.verified:
    st.error('Some data files do not match their recorded checksums, so their content is withheld. See Reproducibility.')
nav.run()
