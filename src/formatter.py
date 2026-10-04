"""Deterministic evidence serialization and readable query diagnostics."""
import logging
from uuid import uuid4

from src.config import settings
from src.schemas import GraphEdgeEvidence, RetrievedChunk


def format_context(chunks: list[RetrievedChunk], max_chars: int = settings.max_context_chars) -> tuple[str, list[str]]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    blocks, ids = [], []
    used = 0
    for chunk in chunks:
        block = (f"[{chunk.paper_id} | {chunk.chunk_id} | rank={chunk.rank} | score={chunk.score:.4f}]\n"
                 f"Title: {chunk.title}\n{chunk.text}")
        extra = len(block) + (2 if blocks else 0)
        if used + extra > max_chars:
            if not blocks:
                blocks.append(block[:max_chars])
                ids.append(chunk.chunk_id)
            break
        blocks.append(block)
        ids.append(chunk.chunk_id)
        used += extra
    return "\n\n".join(blocks), ids


def format_graph_context(edges: list[GraphEdgeEvidence], chunks: list[RetrievedChunk],
                         max_chars: int = settings.max_context_chars) -> tuple[str, list[str]]:
    grouped = {}
    for edge in edges:
        grouped.setdefault((edge.source_id, edge.source_label), []).append(edge)
    blocks = []
    for (source, label), paper_edges in sorted(grouped.items()):
        block = f"[{source.removeprefix('PAPER::')}] {label}\n" + "\n".join(
            f"-- {e.relation} --> {e.target_label}" for e in paper_edges)
        blocks.append(block)
    # Reserve most of the budget for actual PDF evidence, retaining whole graph blocks.
    graph_text = "GRAPH STRUCTURE\n"
    for block in blocks:
        if len(graph_text) + len(block) + 2 > max_chars // 3:
            break
        graph_text += block + "\n\n"
    prefix = graph_text + "SUPPORTING PAPER TEXT\n"
    if len(prefix) >= max_chars:
        return prefix[:max_chars], []
    text, ids = format_context(chunks, max_chars - len(prefix))
    return prefix + text, ids


def log_query_result(result: dict) -> None:
    logger = logging.getLogger("rag.query")
    result["query_id"] = str(uuid4())
    lines = ["=" * 40, f"QUERY ID: {result['query_id']}", f"MODE: {result['mode'].upper()}",
             f"QUESTION: {result['question']}", "QUERY EMBEDDING DIM: 384"]
    if result["mode"] == "graph_rag":
        lines.append("GRAPH SEEDS:")
        lines.extend(f"  {s['node_id']} score={s['score']:.4f}" for s in result["seed_nodes"])
        lines.extend([f"TRAVERSAL DEPTH: {result['depth']}", f"GRAPH NODES: {result['node_count']}",
                      f"GRAPH EDGES: {result['edge_count']}", "CANDIDATE PAPERS:"])
        lines.extend(f"  {p['paper_id']} graph_score={p['graph_score']:.4f}" for p in result["candidate_papers"])
        chunks = result["supporting_chunks"]
        lines.append("SUPPORTING CHUNKS:")
    else:
        chunks = result["retrieved_chunks"]
        lines.append("TOP CHUNKS:")
    lines.extend(f"  {c['chunk_id']} similarity={c['score']:.4f}" for c in chunks)
    lines.extend(f"{name.upper()} TIME: {result[name + '_time_ms']:.2f} ms" for name in ("retrieval", "generation", "total"))
    lines.extend([f"STATUS: {result['status']}", "=" * 40])
    message = "\n".join(lines)
    if settings.groq_api_key:
        message = message.replace(settings.groq_api_key, "[REDACTED]")
    logger.info(message)
    if result["generation_error"]:
        logger.warning("Generation error for query %s: %s", result["query_id"], result["generation_error"])
