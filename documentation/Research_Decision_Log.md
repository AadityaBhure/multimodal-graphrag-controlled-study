# Research Decision Log

## Phase 0 — 2026-10-04

- Preserve the existing lowercase `documentation/` directory. Windows paths are case-insensitive; do not create a second `Documentation/` tree.
- Use the existing Windows CPython 3.12.14 virtual environment explicitly. Plain `python` resolves to a different MSYS2 interpreter.
- No Git repository existed in the project or its parent chain. Initialize local Git and preserve the current baseline; no remote or publication is configured.
- Remove a credential-like value from `.env.example` before committing. Leave the user's `.env` untouched and ignored. Recommend rotating the exposed example credential.
- Capture installed package versions and artifact checksums. Preserve built storage in a ZIP archive because working storage is ignored by Git. Do not rebuild or alter working retrieval artifacts.
- Store the configuration snapshot as JSON-compatible YAML, avoiding new dependencies for Phase 0.
- Add an audit script only; leave app.py and src retrieval/generation behavior unchanged.
- Initial live request failed under restricted networking. Automatic review then required explicit approval for transmitting excerpts to Groq. User granted approval; both live checks subsequently succeeded using the existing model.
- Sandbox process setup later failed. Approved elevated commands completed local audit work; no research design or environment substitution was made.
- Live answer checks are smoke tests, not a scientific evaluation. Record grounding/citation limitations rather than changing baseline prompts or methods.
