"""Build all local artifacts in specification order."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_graph import build_and_verify_graph
from src.config import PAPERS_DIR, TEXT_STORAGE_DIR, GRAPH_STORAGE_DIR
from src.schemas import check_paper_files, load_metadata
from src.text_index import build_text_index


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if not PAPERS_DIR.is_dir():
            raise FileNotFoundError(f"PDF folder missing: {PAPERS_DIR}")
        for directory in (TEXT_STORAGE_DIR, GRAPH_STORAGE_DIR):
            directory.mkdir(parents=True, exist_ok=True)
        papers = load_metadata()
        if len(papers) != 12:
            raise ValueError(f"Expected 12 metadata records; found {len(papers)}")
        check_paper_files(papers)
        report = build_text_index()
        report.update(build_and_verify_graph())
    except Exception as exc:
        logging.error("Build failed: %s", exc)
        return 1
    print("\n========================================\nBUILD COMPLETE")
    for label, key in [("Papers configured", "papers_configured"), ("PDFs parsed successfully", "pdfs_parsed"),
                       ("PDFs skipped", "pdfs_skipped"), ("Chunks created", "chunks"),
                       ("Embedding dimension", "dimension"), ("FAISS vectors", "vectors"),
                       ("Graph nodes", "graph_nodes"), ("Graph edges", "graph_edges")]:
        print(f"{label}: {report[key]}")
    print("Ready:\nstreamlit run app.py\n========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
