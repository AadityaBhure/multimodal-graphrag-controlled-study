"""Shared normalized local embeddings for both retrieval modes."""
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import settings

EMBEDDING_DIM = 384


class Embedder:
    def __init__(self, model_name: str = settings.embedding_model):
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, EMBEDDING_DIM), dtype=np.float32)
        arr = np.asarray(self.model.encode(texts, normalize_embeddings=True,
                                          show_progress_bar=False), dtype=np.float32)
        if arr.shape != (len(texts), EMBEDDING_DIM):
            raise ValueError("Embedding dimension mismatch: expected 384. Use the specified model and rebuild artifacts.")
        if not np.isfinite(arr).all() or not np.allclose(np.linalg.norm(arr, axis=1), 1, atol=1e-5):
            raise ValueError("Embeddings must be finite normalized vectors")
        return arr

    def embed_query(self, query: str) -> np.ndarray:
        if not query.strip():
            raise ValueError("Question must not be empty")
        return self.embed_texts([query])[0]
