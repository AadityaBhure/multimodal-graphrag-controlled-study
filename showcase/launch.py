"""Start the showcase with its theme (the same command locally and in the container).

    python showcase/launch.py                      recorded results only (any host)
    python showcase/launch.py --profile full       also live questions (needs the research data and a local model server)
    python showcase/launch.py --port 8501 --address 0.0.0.0
"""
from pathlib import Path
import argparse, os, subprocess, sys

APP = Path(__file__).resolve().parent / 'app.py'
THEME = {'theme.base': 'light', 'theme.primaryColor': '#1d4ed8', 'theme.backgroundColor': '#ffffff',
         'theme.secondaryBackgroundColor': '#f8fafc', 'theme.textColor': '#0f172a'}
SERVER = {'server.headless': 'true', 'server.fileWatcherType': 'none', 'browser.gatherUsageStats': 'false', 'client.toolbarMode': 'viewer'}


def command(port, address):
    args = [sys.executable, '-m', 'streamlit', 'run', str(APP), '--server.port', str(port), '--server.address', address]
    for k, v in {**THEME, **SERVER}.items():
        args += ['--' + k, v]
    return args


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', choices=('showcase', 'full'), default=os.environ.get('SHOWCASE_PROFILE', 'showcase'))
    ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8501')))
    ap.add_argument('--address', default='127.0.0.1')
    a = ap.parse_args()
    env = {**os.environ, 'SHOWCASE_PROFILE': a.profile}
    sys.exit(subprocess.call(command(a.port, a.address), env=env, cwd=str(APP.parents[1])))
