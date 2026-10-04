"""Graph-first retrieval with supporting text restricted to candidate papers."""
from time import perf_counter

import networkx as nx

from src.config import settings
from src.embedder import Embedder
from src.graph_builder import load_graph
from src.formatter import format_graph_context, log_query_result
from src.llm import ANSWER_INSTRUCTIONS, GRAPH_SYSTEM_PROMPT, LLM
from src.schemas import CandidatePaper, GraphEdgeEvidence, GraphSeed, RetrievedChunk
from src.text_index import TextIndex


class GraphRAG:
    def __init__(self, embedder: Embedder | None = None, text_index: TextIndex | None = None,
                 graph: nx.Graph | None = None, llm: LLM | None = None):
        self.graph = graph if graph is not None else load_graph()
        self.text_index = text_index or TextIndex.load()
        self.embedder = embedder or Embedder()
        self.llm = llm or LLM()
        self.node_ids = sorted(self.graph.nodes)
        self.node_embeddings = self.embedder.embed_texts([self.graph.nodes[n]["description"] for n in self.node_ids])
        self.paper_chunk_indices = {}
        for i, chunk in enumerate(self.text_index.chunks):
            self.paper_chunk_indices.setdefault(chunk.paper_id, []).append(i)

    def select_seeds(self, query: str, seed_k: int = settings.graph_seed_k) -> list[GraphSeed]:
        if seed_k <= 0:
            raise ValueError("seed_k must be positive")
        scores = self.node_embeddings @ self.embedder.embed_query(query)
        order = sorted(range(len(self.node_ids)), key=lambda i: (-float(scores[i]), self.node_ids[i]))[:seed_k]
        return [GraphSeed(node_id=self.node_ids[i], label=self.graph.nodes[self.node_ids[i]]["label"],
                          node_type=self.graph.nodes[self.node_ids[i]]["node_type"], score=float(scores[i])) for i in order]

    def retrieve_graph(self, query: str, seed_k: int = settings.graph_seed_k,
                       depth: int = settings.graph_depth) -> dict:
        if depth < 0:
            raise ValueError("depth must be nonnegative")
        start = perf_counter()
        seeds = self.select_seeds(query, seed_k)
        distances = {s.node_id: dict(nx.single_source_shortest_path_length(self.graph, s.node_id, cutoff=depth)) for s in seeds}
        discovered = set().union(*(set(lengths) for lengths in distances.values()))
        subgraph = self.graph.subgraph(discovered)
        candidates = []
        for nid, data in sorted(subgraph.nodes(data=True)):
            if data["node_type"] != "Paper":
                continue
            supporters = [s for s in seeds if nid in distances[s.node_id]]
            score = max(s.score / (1 + distances[s.node_id][nid]) for s in supporters)
            candidates.append(CandidatePaper(paper_id=data["paper_id"], title=data["label"],
                              graph_score=score, supporting_seed_ids=[s.node_id for s in supporters]))
        candidates.sort(key=lambda p: (-p.graph_score, p.paper_id))
        candidates = candidates[:settings.graph_max_papers]
        edges = []
        for _, _, data in subgraph.edges(data=True):
            source, target = data["source"], data["target"]
            edges.append(GraphEdgeEvidence(source_id=source, source_label=self.graph.nodes[source]["label"],
                relation=data["relation"], target_id=target, target_label=self.graph.nodes[target]["label"]))
        edges.sort(key=lambda e: (e.source_id, e.relation, e.target_id))
        return {"seed_nodes": seeds, "graph_edges": edges, "candidate_papers": candidates,
                "node_count": len(subgraph), "edge_count": subgraph.number_of_edges(),
                "node_ids": sorted(discovered), "seed_distances": distances, "depth": depth,
                "retrieval_time_ms": (perf_counter() - start) * 1000}

    def retrieve_supporting_chunks(self, query: str, candidate_paper_ids: list[str],
                                   per_paper_k: int = settings.graph_per_paper_chunks) -> list[RetrievedChunk]:
        if per_paper_k <= 0:
            raise ValueError("per_paper_k must be positive")
        q = self.embedder.embed_query(query)
        results, seen = [], set()
        for paper_id in candidate_paper_ids:
            indices = self.paper_chunk_indices.get(paper_id, [])
            if not indices:
                continue
            scores = self.text_index.embeddings[indices] @ q
            order = sorted(range(len(indices)), key=lambda i: (-float(scores[i]), self.text_index.chunks[indices[i]].chunk_id))[:per_paper_k]
            for i in order:
                chunk = self.text_index.chunks[indices[i]]
                if chunk.chunk_id in seen:
                    continue
                seen.add(chunk.chunk_id)
                results.append(RetrievedChunk(rank=len(results) + 1, chunk_id=chunk.chunk_id,
                    paper_id=chunk.paper_id, title=chunk.title, score=float(scores[i]), text=chunk.text))
        return results

    def answer(self, query: str) -> dict:
        start = perf_counter()
        graph_result = self.retrieve_graph(query)
        chunks = self.retrieve_supporting_chunks(query, [p.paper_id for p in graph_result["candidate_papers"]])
        retrieval_ms = (perf_counter() - start) * 1000
        context, ids = format_graph_context(graph_result["graph_edges"], chunks)
        user_prompt = f"{ANSWER_INSTRUCTIONS}\n\nQuestion: {query}\n\n{context}"
        generation_start = perf_counter()
        generation = self.llm.generate(GRAPH_SYSTEM_PROMPT, user_prompt)
        generation_ms = (perf_counter() - generation_start) * 1000
        result = {"mode": "graph_rag", "question": query, **generation,
                "seed_nodes": [s.model_dump() for s in graph_result["seed_nodes"]],
                "graph_edges": [e.model_dump() for e in graph_result["graph_edges"]],
                "candidate_papers": [p.model_dump() for p in graph_result["candidate_papers"]],
                "supporting_chunks": [c.model_dump() for c in chunks],
                "node_count": graph_result["node_count"], "edge_count": graph_result["edge_count"],
                "depth": graph_result["depth"], "context": context, "context_chunk_ids": ids,
                "system_prompt": GRAPH_SYSTEM_PROMPT, "user_prompt": user_prompt,
                "retrieval_time_ms": retrieval_ms, "generation_time_ms": generation_ms,
                "total_time_ms": (perf_counter() - start) * 1000}
        log_query_result(result)
        return result
