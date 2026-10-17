"""Shared, cached app state: the verified bundle, the content file, navigation and URL parameters."""
import streamlit as st
from showcase.lib.bundle import Bundle
from showcase.lib.content import load_content

PAGES = [  # (file, title, icon, url path, section)
    ('pages/p01_problem.py', 'The problem', ':material/help:', 'problem', 'The problem'),
    ('pages/p02_parts.py', 'Four parts', ':material/account_tree:', 'parts', 'The problem'),
    ('pages/p03_data.py', 'Data and benchmark', ':material/database:', 'data', 'The problem'),
    ('pages/p04_metrics.py', 'Metrics and statistics', ':material/functions:', 'metrics', 'The problem'),
    ('pages/p05_rq1.py', 'Part 1 · Context management', ':material/filter_alt:', 'context', 'The studies'),
    ('pages/p06_rq2.py', 'Part 2 · Fusion', ':material/merge:', 'fusion', 'The studies'),
    ('pages/p07_rq3.py', 'Part 3 · Retrieval control', ':material/route:', 'retrieval-control', 'The studies'),
    ('pages/p08_rq4.py', 'Part 4 · Combined system', ':material/hub:', 'combined', 'The studies'),
    ('pages/p09_summary.py', 'Conclusions', ':material/flag:', 'conclusions', 'Takeaways'),
    ('pages/p10_try.py', 'Try a question', ':material/play_circle:', 'try', 'Explore'),
    ('pages/p11_repro.py', 'Reproducibility', ':material/verified:', 'reproducibility', 'Explore'),
]


@st.cache_resource(show_spinner=False)
def bundle():
    return Bundle()


@st.cache_resource(show_spinner=False)
def content():
    return load_content()


def presenting():
    return bool(st.session_state.get('presenting'))


def neighbours(path):
    i = [p[0] for p in PAGES].index(path)
    prev = (PAGES[i - 1][0], PAGES[i - 1][1]) if i > 0 else None
    nxt = (PAGES[i + 1][0], PAGES[i + 1][1]) if i + 1 < len(PAGES) else None
    return prev, nxt


def param(name, allowed, default):
    """A URL query parameter restricted to allowed values (shareable links); anything else falls back to default."""
    v = st.query_params.get(name)
    return v if v in allowed else default


def set_param(name, value):
    if st.query_params.get(name) != value:
        st.query_params[name] = value


def title_of(paper_id):
    return bundle().title(paper_id)
