# Multi-Modal GraphRAG — showcase app

An interactive presentation of the four studies: the problem, how it was split into parts, the strategies compared in each
part, the metrics and statistics, the results, the combined system, and a page to try questions.

Every number on screen comes from one checksummed data bundle (`showcase/bundle/`) exported from the frozen study outputs.
All on-screen text lives in `showcase/content/content.yaml`; findings bind their numbers to the bundle by name, so text
and results cannot drift apart.

## Run

From the repository root:

```bash
python showcase/launch.py
```

Opens on <http://127.0.0.1:8501>. Options: `--port 8610`, `--address 0.0.0.0`, `--profile full`.

| Profile | What it does | Needs |
|---|---|---|
| `showcase` (default) | All pages; "Try a question" replays the recorded runs | `pip install -r showcase/requirements.txt` |
| `full` | Adds live questions: any retrieval policy × fusion method, answered by the local model | The research environment (`.venv`), the data in `data/MMG_STARK_MAG`, and a model server at `SHOWCASE_OLLAMA_URL` (default `http://127.0.0.1:11434`) with `gpt-oss:20b` |

Live runs reuse recorded responses when the request is identical and keep new responses in `artifacts/showcase/live_stages`,
so repeating a run is instant. Each browser session may start `SHOWCASE_LIVE_RUNS` live runs (default 8); one live run
executes at a time. Live answers are demonstrations, not evaluated results.

## Deploy

Container (recorded results; no research code or data inside):

```bash
docker build -t mmg-showcase showcase
```

```bash
docker run --rm -p 8501:8501 mmg-showcase
```

Hosted Streamlit services: entry point `showcase/app.py`, requirements `showcase/requirements.txt`. The app adapts its
styling to a dark browser theme if the host does not apply the launch theme.

## Presenting

- Toggle **Presentation mode** in the sidebar (larger text, cleaner screen), or open any page with `?present=1`.
- Each page starts with an "On this page" strip; every explorer view is encoded in the address bar, so a link reopens it.

## Rebuild and check the data

```bash
python scripts/build_showcase_bundle.py
```

```bash
python scripts/build_showcase_bundle.py --check
```

`--check` rebuilds the bundle in memory and confirms the committed files are reproduced byte for byte.

## Tests

```bash
python -m pytest tests/test_showcase.py -q
```

Covers bundle checksums, agreement with the frozen analyses, every content placeholder, deterministic number formatting,
metric parity with the research code, trace ordering, and a render of every page in both profiles.

## Layout

```
showcase/
  app.py            entry point and navigation       launch.py   theme + server flags (local and container)
  config.py         profile and live-run settings     Dockerfile  container for the showcase profile
  content/          all on-screen text (YAML)         bundle/     checksummed data exported from the studies
  lib/              bundle loader, content binding, formatting, UI kit, charts, graph and trace views, explorers, live engine
  pages/            one file per page
```
