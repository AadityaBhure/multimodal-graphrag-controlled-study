"""Deterministic overlapping word chunks, isolated by paper."""
from src.config import settings
from src.schemas import Chunk, PaperMetadata


def chunk_document(text: str, paper: PaperMetadata,
                   chunk_size: int = settings.chunk_size_words,
                   chunk_overlap: int = settings.chunk_overlap_words) -> list[Chunk]:
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size")
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        index = len(chunks)
        chunks.append(Chunk(chunk_id=f"{paper.paper_id}_C{index:04d}",
                            paper_id=paper.paper_id, title=paper.title,
                            chunk_index=index, text=" ".join(words[start:end]),
                            word_count=end - start))
        if end == len(words):
            break
        start = end - chunk_overlap
    return chunks
