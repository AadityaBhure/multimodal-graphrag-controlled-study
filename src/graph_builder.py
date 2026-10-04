"""Deterministic metadata graph; no inferred or extracted relations."""
import json
from pathlib import Path

import networkx as nx

from src.config import GRAPH_STORAGE_DIR

from src.schemas import PaperMetadata


def concept_label(value: str) -> str:
    return value.title()


def build_graph(papers: list[PaperMetadata]) -> nx.Graph:
    graph = nx.Graph()
    for paper in sorted(papers, key=lambda p: p.paper_id):
        pid = f"PAPER::{paper.paper_id}"
        description = (f"{paper.title}. Research area: {paper.research_area}. "
                       f"Techniques: {', '.join(paper.techniques)}. Modalities: {', '.join(paper.modalities)}.")
        graph.add_node(pid, node_type="Paper", label=paper.title,
                       description=description, paper_id=paper.paper_id)
        concepts = [("AREA", "ResearchArea", paper.research_area, "Research category", "BELONGS_TO")]
        concepts += [("TECH", "Technique", concept_label(t), "Technique", "USES") for t in paper.techniques]
        concepts += [("MOD", "Modality", concept_label(m), "Knowledge representation modality", "USES_MODALITY") for m in paper.modalities]
        for prefix, node_type, label, description_prefix, relation in concepts:
            cid = f"{prefix}::{label}"
            graph.add_node(cid, node_type=node_type, label=label, description=f"{description_prefix}: {label}")
            graph.add_edge(pid, cid, relation=relation, source=pid, target=cid)
    return graph


def save_graph(graph: nx.Graph, path: Path = GRAPH_STORAGE_DIR / "graph.json") -> None:
    data = {"nodes": [{"id": nid, **attrs} for nid, attrs in sorted(graph.nodes(data=True))],
            "edges": sorted([{"source": a["source"], "relation": a["relation"], "target": a["target"]}
                              for _, _, a in graph.edges(data=True)], key=lambda e: (e["source"], e["target"]))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_graph(path: Path = GRAPH_STORAGE_DIR / "graph.json") -> nx.Graph:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        graph = nx.Graph()
        allowed = {"Paper", "ResearchArea", "Technique", "Modality"}
        for node in data["nodes"]:
            nid = node["id"]
            if nid in graph or node["node_type"] not in allowed or not node["label"] or not node["description"]:
                raise ValueError("Invalid or duplicate graph node")
            attrs = {k: v for k, v in node.items() if k != "id"}
            if attrs["node_type"] == "Paper" and nid != f"PAPER::{attrs['paper_id']}":
                raise ValueError("Invalid paper identity")
            graph.add_node(nid, **attrs)
        relations = {"ResearchArea": "BELONGS_TO", "Technique": "USES", "Modality": "USES_MODALITY"}
        for edge in data["edges"]:
            source, target, relation = edge["source"], edge["target"], edge["relation"]
            if source not in graph or target not in graph or graph.has_edge(source, target):
                raise ValueError("Invalid or duplicate graph edge")
            if graph.nodes[source]["node_type"] != "Paper" or relations.get(graph.nodes[target]["node_type"]) != relation:
                raise ValueError("Invalid graph relation")
            graph.add_edge(source, target, source=source, target=target, relation=relation)
        if sum(d["node_type"] == "Paper" for _, d in graph.nodes(data=True)) != 12:
            raise ValueError("Expected exactly 12 Paper nodes")
        return graph
    except Exception as exc:
        raise RuntimeError(f"Cannot load graph at {path}. Run python scripts/build_all.py to rebuild. ({exc})") from exc
