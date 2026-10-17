"""Deployment settings, read from environment variables (no machine-specific paths).

SHOWCASE_PROFILE      showcase (default): replay of recorded runs only; runs on any host with the pinned requirements.
                      full: also allows live questions through the research pipeline and a local model server.
SHOWCASE_OLLAMA_URL   model server for the full profile (default http://127.0.0.1:11434).
SHOWCASE_LIVE_RUNS    live runs allowed per browser session (default 8).
"""
import os

PROFILE = os.environ.get('SHOWCASE_PROFILE', 'showcase').strip().lower()
if PROFILE not in ('showcase', 'full'):
    PROFILE = 'showcase'
OLLAMA_URL = os.environ.get('SHOWCASE_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
LIVE_RUNS_PER_SESSION = max(0, int(os.environ.get('SHOWCASE_LIVE_RUNS', '8') or 0))
MAX_QUESTION_CHARS = 500
LIVE_TIMEOUT_S = 900
