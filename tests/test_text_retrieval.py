from dataclasses import replace
from unittest.mock import patch

from src.config import settings
from src.formatter import format_context
from src.llm import LLM
from src.text_rag import TextRAG


def test_corrective_retrieval(embedder, text_index):
    results = TextRAG(embedder, text_index).retrieve("corrective retrieval")
    assert len(results) == 5
    assert any(c.paper_id == "P010" for c in results)
    assert [c.rank for c in results] == list(range(1, 6))
    assert all(a.score >= b.score for a, b in zip(results, results[1:]))
    ids = {c.chunk_id for c in text_index.chunks}
    assert all(c.chunk_id in ids for c in results)
    assert sum(c.paper_id == "P010" for c in results) > 1


def test_context_budget(embedder, text_index):
    chunks = TextRAG(embedder, text_index).retrieve("corrective retrieval")
    first, _ = format_context(chunks[:1])
    context, ids = format_context(chunks, len(first) + 10)
    assert context == first
    assert ids == [chunks[0].chunk_id]
    tiny, tiny_ids = format_context(chunks, 30)
    assert len(tiny) == 30 and tiny_ids == [chunks[0].chunk_id]


def test_missing_key_preserves_evidence(embedder, text_index):
    result = TextRAG(embedder, text_index, LLM(replace(settings, groq_api_key=""))).answer("corrective retrieval")
    assert result["status"] == "generation_disabled"
    assert result["retrieved_chunks"] and result["context_chunk_ids"]
    assert len(result["context"]) <= settings.max_context_chars


def test_api_error_preserves_evidence(embedder, text_index):
    llm = LLM(replace(settings, groq_api_key="test-key"))
    with patch("src.llm.Groq", side_effect=RuntimeError("test-key simulated failure")):
        result = TextRAG(embedder, text_index, llm).answer("corrective retrieval")
    assert result["status"] == "generation_error" and result["retrieved_chunks"]
    assert "test-key" not in result["generation_error"]
