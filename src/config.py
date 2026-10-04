"""Project-relative configuration shared by build, retrieval, and UI."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PAPERS_DIR = DATA_DIR / "papers"
STORAGE_DIR = PROJECT_ROOT / "storage"
TEXT_STORAGE_DIR = STORAGE_DIR / "text"
GRAPH_STORAGE_DIR = STORAGE_DIR / "graph"
load_dotenv(PROJECT_ROOT / ".env")


def positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip(), repr=False)
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    text_top_k: int = field(default_factory=lambda: positive_int("TEXT_TOP_K", 5))
    graph_seed_k: int = field(default_factory=lambda: positive_int("GRAPH_SEED_K", 3))
    graph_depth: int = field(default_factory=lambda: positive_int("GRAPH_DEPTH", 2))
    graph_max_papers: int = field(default_factory=lambda: positive_int("GRAPH_MAX_PAPERS", 5))
    graph_per_paper_chunks: int = field(default_factory=lambda: positive_int("GRAPH_PER_PAPER_CHUNKS", 2))
    chunk_size_words: int = field(default_factory=lambda: positive_int("CHUNK_SIZE_WORDS", 450))
    chunk_overlap_words: int = field(default_factory=lambda: positive_int("CHUNK_OVERLAP_WORDS", 75))
    max_context_chars: int = field(default_factory=lambda: positive_int("MAX_CONTEXT_CHARS", 24000))

    def __post_init__(self):
        if self.chunk_overlap_words >= self.chunk_size_words:
            raise ValueError("CHUNK_OVERLAP_WORDS must be smaller than CHUNK_SIZE_WORDS")

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


settings = Settings()
