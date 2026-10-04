"""Build and validate aligned chunks, embeddings, and FAISS artifacts."""
import json
import logging
from pathlib import Path

import faiss
import numpy as np

from src.chunker import chunk_document
from src.config import PAPERS_DIR, TEXT_STORAGE_DIR
from src.embedder import EMBEDDING_DIM, Embedder
from src.pdf_loader import extract_pdf_text
from src.schemas import Chunk, check_paper_files, load_metadata

logger = logging.getLogger(__name__)
REBUILD = "Run python scripts/build_all.py to rebuild artifacts."


class TextIndex:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, index):
        self.chunks, self.embeddings, self.index = chunks, embeddings, index
        n = len(chunks)
        if n == 0 or embeddings.shape != (n, EMBEDDING_DIM) or index.ntotal != n or index.d != EMBEDDING_DIM:
            raise ValueError(f"Text artifact counts/dimensions disagree. {REBUILD}")
        if embeddings.dtype != np.float32 or not isinstance(index, faiss.IndexFlatIP):
            raise ValueError(f"Expected float32 embeddings and IndexFlatIP. {REBUILD}")
        if not np.isfinite(embeddings).all() or not np.allclose(np.linalg.norm(embeddings, axis=1), 1, atol=1e-5):
            raise ValueError(f"Invalid embedding normalization. {REBUILD}")
        if len({c.chunk_id for c in chunks}) != n:
            raise ValueError(f"Duplicate chunk IDs. {REBUILD}")
        for c in chunks:
            if c.word_count != len(c.text.split()) or c.chunk_id != f"{c.paper_id}_C{c.chunk_index:04d}":
                raise ValueError(f"Invalid chunk {c.chunk_id}. {REBUILD}")
        if not np.array_equal(index.reconstruct_n(0, n), embeddings):
            raise ValueError(f"FAISS vectors differ from saved embeddings. {REBUILD}")

    @classmethod
    def load(cls, directory: Path = TEXT_STORAGE_DIR):
        try:
            chunks = [Chunk.model_validate(c) for c in json.loads((directory / "chunks.json").read_text(encoding="utf-8"))]
            embeddings = np.load(directory / "embeddings.npy", allow_pickle=False)
            index = faiss.read_index(str(directory / "faiss.index"))
            return cls(chunks, embeddings, index)
        except Exception as exc:
            raise RuntimeError(f"Cannot load text artifacts from {directory}. {REBUILD} ({exc})") from exc


def build_text_index(embedder: Embedder | None = None, directory: Path = TEXT_STORAGE_DIR) -> dict:
    papers = load_metadata()
    check_paper_files(papers)
    chunks = []
    parsed = 0
    for paper in papers:
        try:
            text = extract_pdf_text(PAPERS_DIR / paper.filename)
            paper_chunks = chunk_document(text, paper)
            if not paper_chunks:
                raise ValueError("No chunks extracted")
        except Exception as exc:
            logger.warning("Skipping %s (%s): %s", paper.paper_id, paper.filename, exc)
            continue
        chunks.extend(paper_chunks)
        parsed += 1
        logger.info("Parsed %s: %d chunks", paper.paper_id, len(paper_chunks))
    if parsed < 5:
        raise RuntimeError(f"Only {parsed} PDFs parsed; at least 5 required. Check data/papers and metadata mappings.")
    embedder = embedder or Embedder()
    embeddings = embedder.embed_texts([c.text for c in chunks])
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)
    TextIndex(chunks, embeddings, index)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "chunks.json").write_text(json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(directory / "embeddings.npy", embeddings)
    faiss.write_index(index, str(directory / "faiss.index"))
    loaded = TextIndex.load(directory)
    return {"papers_configured": len(papers), "pdfs_parsed": parsed,
            "pdfs_skipped": len(papers) - parsed, "chunks": len(loaded.chunks),
            "dimension": loaded.index.d, "vectors": loaded.index.ntotal}
