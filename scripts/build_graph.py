"""Build and verify the deterministic metadata graph."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networkx as nx

from src.graph_builder import build_graph, load_graph, save_graph
from src.schemas import load_metadata


def build_and_verify_graph():
    graph = build_graph(load_metadata())
    if sum(d["node_type"] == "Paper" for _, d in graph.nodes(data=True)) != 12:
        raise ValueError("Expected 12 Paper nodes")
    save_graph(graph)
    restored = load_graph()
    if not nx.utils.graphs_equal(graph, restored):
        raise RuntimeError("Graph round trip changed nodes, edges, or attributes")
    return {"graph_nodes": len(restored), "graph_edges": restored.number_of_edges()}


if __name__ == "__main__":
    try:
        print(build_and_verify_graph())
    except Exception as exc:
        logging.error("Graph build failed: %s", exc)
        sys.exit(1)
