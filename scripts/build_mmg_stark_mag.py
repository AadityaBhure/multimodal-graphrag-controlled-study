"""Phase 3 builder CLI; no benchmark construction."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.data.build import Builder


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase3.yaml")
    parser.add_argument("--stage", required=True, choices=["nodes", "structured", "edges", "csr", "embeddings", "faiss", "manifest"])
    args = parser.parse_args()
    builder = Builder(args.config)
    if args.stage in {"embeddings", "faiss"}:
        from research.data.embeddings import build_embeddings, build_faiss
        (build_embeddings if args.stage == "embeddings" else build_faiss)(builder)
    elif args.stage == "manifest":
        from research.data.validation import manifest
        manifest(builder)
    else:
        getattr(builder, args.stage)()
