from dataclasses import replace

import networkx as nx
import pytest

from src.config import settings
from src.graph_rag import GraphRAG
from src.llm import LLM


@pytest.fixture(scope="module")
def rag(embedder, text_index):
    return GraphRAG(embedder, text_index, llm=LLM(replace(settings, groq_api_key="")))


def test_self_reflection_candidates_and_edges(rag):
    result = rag.retrieve_graph("self reflection agentic retrieval")
    assert any(p.paper_id == "P011" for p in result["candidate_papers"])
    assert any(e.source_id == "PAPER::P011" and e.target_id == "TECH::Self-Reflection" for e in result["graph_edges"])
    assert len(result["candidate_papers"]) <= settings.graph_max_papers


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_depth_bound_and_scoring(rag, depth):
    result = rag.retrieve_graph("self reflection agentic retrieval", depth=depth)
    expected = set()
    for seed in result["seed_nodes"]:
        distances = nx.single_source_shortest_path_length(rag.graph, seed.node_id, cutoff=depth)
        expected.update(distances)
        assert result["seed_distances"][seed.node_id] == distances
        assert all(d <= depth for d in distances.values())
    assert set(result["node_ids"]) == expected
    for p in result["candidate_papers"]:
        nid = "PAPER::" + p.paper_id
        scores = [s.score / (1 + result["seed_distances"][s.node_id][nid])
                  for s in result["seed_nodes"] if nid in result["seed_distances"][s.node_id]]
        assert p.graph_score == max(scores)


def test_deterministic_ordering(rag):
    a = rag.retrieve_graph("self reflection agentic retrieval")
    b = rag.retrieve_graph("self reflection agentic retrieval")
    assert a["candidate_papers"] == b["candidate_papers"]
    assert a["graph_edges"] == b["graph_edges"]
    assert a["candidate_papers"] == sorted(a["candidate_papers"], key=lambda p: (-p.graph_score, p.paper_id))


def test_supporting_chunks_are_restricted(rag, monkeypatch):
    def forbidden(*args):
        raise AssertionError("Graph supporting retrieval must not call FAISS")
    monkeypatch.setattr(rag.text_index.index, "search", forbidden)
    ids = ["P011", "P012"]
    chunks = rag.retrieve_supporting_chunks("self reflection", ids)
    assert [c.paper_id for c in chunks] == ["P011", "P011", "P012", "P012"]
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert all(c.paper_id in ids for c in chunks)
    assert chunks[0].score >= chunks[1].score and chunks[2].score >= chunks[3].score


def test_graph_answer_without_key(rag):
    result = rag.answer("Which agentic retrieval approaches use self-reflection?")
    assert result["status"] == "generation_disabled"
    assert any(c["paper_id"] == "P011" for c in result["supporting_chunks"])
    assert len(result["context"]) <= settings.max_context_chars
    assert all(c["paper_id"] in {p["paper_id"] for p in result["candidate_papers"]} for c in result["supporting_chunks"])
