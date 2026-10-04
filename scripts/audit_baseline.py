"""Phase 0 audit; live generation is explicit and never prints credentials."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from dotenv import dotenv_values
from src.config import settings

OUT = ROOT / "documentation" / "baseline_phase0"


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False)
    if settings.groq_api_key:
        payload = payload.replace(settings.groq_api_key, "[REDACTED]")
    (OUT / name).write_text(payload, encoding="utf-8")


def inventory():
    from src.text_index import TextIndex
    from src.graph_builder import load_graph
    from src.schemas import load_metadata
    index, graph = TextIndex.load(), load_graph()
    config = asdict(settings)
    config.pop("groq_api_key")
    snapshot = {"python": platform.python_version(), "settings": config,
                "generation_temperature": 0, "embedding_dimension": index.index.d,
                "index_type": type(index.index).__name__,
                "env_names": sorted(dotenv_values(ROOT / ".env")),
                "counts": {"metadata_papers": len(load_metadata()),
                           "pdfs": len(list((ROOT / "data/papers").glob("*.pdf"))),
                           "chunks": len(index.chunks), "vectors": index.index.ntotal,
                           "graph_nodes": len(graph), "graph_edges": graph.number_of_edges()}}
    # JSON is also valid YAML; avoid introducing a dependency for the baseline.
    (ROOT / "configs/baseline_mvp_snapshot.yaml").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(p in {".venv", ".git", "__pycache__", ".pytest_cache"} for p in path.relative_to(ROOT).parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if path.name == ".env" or rel.startswith(("documentation/baseline_phase0/", "documentation/Phase_Reports/")):
            continue
        files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest()})
    save("inventory.json", files)
    print(json.dumps(snapshot, indent=2))


def live(mode, offline=False):
    from src.text_rag import TextRAG
    from src.graph_rag import GraphRAG
    service, question = (TextRAG(), "How does G-Retriever select a compact subgraph?") if mode == "text" else (GraphRAG(), "Which agentic retrieval approaches use self-reflection?")
    if offline:
        from dataclasses import replace
        from src.llm import LLM
        service.llm = LLM(replace(settings, groq_api_key=""))
    result = service.answer(question)
    save(f"{mode}_{'offline' if offline else 'live'}.json", result)
    print(json.dumps({k: result[k] for k in ("status", "answer", "generation_error", "context_chunk_ids")}, indent=2))
    assert result["context_chunk_ids"], "No evidence reached context"
    assert result["status"] == ("generation_disabled" if offline else "ok"), "Unexpected generation status"
    if mode == "graph":
        assert result["seed_nodes"] and result["candidate_papers"] and result["graph_edges"]
        candidates = {p["paper_id"] for p in result["candidate_papers"]}
        assert all(c["paper_id"] in candidates for c in result["supporting_chunks"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["inventory", "text", "graph", "ui"])
    parser.add_argument("--offline", action="store_true", help="Verify evidence without making API calls")
    args = parser.parse_args()
    if args.mode == "inventory":
        inventory()
    elif args.mode == "ui":
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=120)
        result = {"exceptions": [str(e.value) for e in app.exception],
                  "errors": [str(e.value) for e in app.error],
                  "tabs": [t.label for t in app.tabs]}
        save("ui_smoke.json", result)
        print(json.dumps(result))
        assert not result["exceptions"] and not result["errors"]
        assert result["tabs"] == ["Demo", "Architecture", "Dataset"]
    else:
        live(args.mode, args.offline)
