"""Traditional chunk-level FAISS retrieval."""
from time import perf_counter

from src.config import settings
from src.embedder import Embedder
from src.formatter import format_context, log_query_result
from src.llm import ANSWER_INSTRUCTIONS, LLM, TEXT_SYSTEM_PROMPT
from src.schemas import RetrievedChunk
from src.text_index import TextIndex


class TextRAG:
    def __init__(self, embedder: Embedder | None = None, text_index: TextIndex | None = None, llm: LLM | None = None):
        self.text_index = text_index or TextIndex.load()
        self.embedder = embedder or Embedder()
        self.last_retrieval_time_ms = 0.0
        self.llm = llm or LLM()

    def retrieve(self, query: str, top_k: int = settings.text_top_k) -> list[RetrievedChunk]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        start = perf_counter()
        q = self.embedder.embed_query(query).reshape(1, -1)
        scores, indices = self.text_index.index.search(q, min(top_k, len(self.text_index.chunks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            chunk = self.text_index.chunks[int(idx)]
            results.append(RetrievedChunk(rank=len(results) + 1, chunk_id=chunk.chunk_id,
                paper_id=chunk.paper_id, title=chunk.title, score=float(score), text=chunk.text))
        self.last_retrieval_time_ms = (perf_counter() - start) * 1000
        return results

    def answer(self, query: str) -> dict:
        start = perf_counter()
        chunks = self.retrieve(query)
        retrieval_ms = (perf_counter() - start) * 1000
        context, ids = format_context(chunks)
        user_prompt = f"{ANSWER_INSTRUCTIONS}\n\nQuestion: {query}\n\nRETRIEVED EVIDENCE\n{context}"
        generation_start = perf_counter()
        generation = self.llm.generate(TEXT_SYSTEM_PROMPT, user_prompt)
        generation_ms = (perf_counter() - generation_start) * 1000
        result = {"mode": "text_rag", "question": query, **generation,
                "retrieved_chunks": [c.model_dump() for c in chunks],
                "context": context, "context_chunk_ids": ids,
                "system_prompt": TEXT_SYSTEM_PROMPT, "user_prompt": user_prompt,
                "retrieval_time_ms": retrieval_ms, "generation_time_ms": generation_ms,
                "total_time_ms": (perf_counter() - start) * 1000}
        log_query_result(result)
        return result
