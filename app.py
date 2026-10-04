"""Presentation UI; retrieval algorithms live exclusively in src."""
import logging

import streamlit as st

from src.config import DATA_DIR, GRAPH_STORAGE_DIR, TEXT_STORAGE_DIR, settings
from src.embedder import Embedder
from src.graph_builder import load_graph
from src.graph_rag import GraphRAG
from src.schemas import load_metadata
from src.text_index import TextIndex
from src.text_rag import TextRAG

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
st.set_page_config(page_title="RAG Retrieval Lab", page_icon="📚", layout="wide")


@st.cache_resource
def load_services():
    metadata = load_metadata()
    text_index = TextIndex.load()
    graph = load_graph()
    embedder = Embedder()
    return metadata, text_index, TextRAG(embedder, text_index), GraphRAG(embedder, text_index, graph)


def show_status(paper_count, chunk_count, embedding_status="READY", text_status="READY", graph_status="READY"):
    with st.sidebar:
        st.header("System status")
        st.write(f"Embedding model: {embedding_status}")
        st.write(f"Text index: {text_status}")
        st.write(f"Graph: {graph_status}")
        st.write("Groq API: " + ("READY" if settings.groq_configured else "NOT CONFIGURED"))
        st.write(f"Papers configured: {paper_count}")
        st.write(f"Chunks indexed: {chunk_count}")
        st.caption(f"Embedding: {settings.embedding_model}")
        st.caption(f"Generation: {settings.groq_model}")
        st.caption("Groq READY means a key is configured; request errors appear with the evidence.")


def show_chunks(chunks, context_ids):
    for chunk in chunks:
        included = "in LLM context" if chunk["chunk_id"] in context_ids else "outside context budget"
        label = (f"#{chunk['rank']} · {chunk['paper_id']} · {chunk['chunk_id']} · "
                 f"score {chunk['score']:.4f} · {included}")
        with st.expander(label):
            st.markdown(f"**{chunk['title']}**")
            st.text(chunk["text"])


def show_result(result):
    st.subheader("Answer")
    st.caption(f"{result['mode']} · {result['question']}")
    if result["status"] == "generation_disabled":
        st.info(result["answer"])
    elif result["status"] == "generation_error":
        st.warning(result["answer"])
        st.error(result["generation_error"])
    else:
        st.markdown(result["answer"])
    cols = st.columns(3)
    for col, name in zip(cols, ("retrieval", "generation", "total")):
        col.metric(f"{name.title()} time", f"{result[name + '_time_ms']:.1f} ms")
    if result["mode"] == "text_rag":
        st.metric("Top-K chunks", len(result["retrieved_chunks"]))
        st.subheader("Retrieved evidence")
        show_chunks(result["retrieved_chunks"], result["context_chunk_ids"])
    else:
        cols = st.columns(4)
        for col, label, value in zip(cols, ("Seeds", "Graph nodes", "Graph edges", "Candidate papers"),
                                    (len(result["seed_nodes"]), result["node_count"], result["edge_count"], len(result["candidate_papers"]))):
            col.metric(label, value)
        st.subheader("Semantic graph seeds")
        st.dataframe(result["seed_nodes"], hide_index=True, width="stretch")
        st.subheader("Retrieved graph relations")
        st.caption(f"Bounded traversal: depth {result['depth']}. Relations are curated paper metadata.")
        st.dataframe(result["graph_edges"], hide_index=True, width="stretch")
        st.subheader("Candidate papers")
        st.dataframe(result["candidate_papers"], hide_index=True, width="stretch")
        st.subheader("Supporting PDF evidence")
        show_chunks(result["supporting_chunks"], result["context_chunk_ids"])
    with st.expander("Exact context sent to LLM"):
        st.caption(f"{len(result['context']):,} characters; included chunk IDs: {', '.join(result['context_chunk_ids'])}")
        st.text(result["context"])
    with st.expander("Exact LLM request messages"):
        st.text("SYSTEM\n" + result["system_prompt"])
        st.text("USER\n" + result["user_prompt"])


st.title("RAG Retrieval Lab")
st.write("Compare direct PDF chunk retrieval with graph-first paper selection over the same 12 research papers.")
st.caption("Same embeddings · Same Groq model · Temperature 0 · Visible evidence")

try:
    with st.spinner("Loading local indexes and embedding model…"):
        papers, index, text_rag, graph_rag = load_services()
except Exception as exc:
    text_exists = all((TEXT_STORAGE_DIR / f).is_file() for f in ("chunks.json", "embeddings.npy", "faiss.index"))
    graph_exists = (GRAPH_STORAGE_DIR / "graph.json").is_file()
    show_status("unknown", "unknown", "ERROR / NOT INITIALIZED",
                "ERROR / NOT VALIDATED" if text_exists else "MISSING",
                "ERROR / NOT VALIDATED" if graph_exists else "MISSING")
    st.error(str(exc))
    st.info("Check metadata and local artifacts. Build with: python scripts/build_all.py")
    st.stop()

show_status(len(papers), len(index.chunks))

demo, architecture, dataset = st.tabs(["Demo", "Architecture", "Dataset"])
with demo:
    mode = st.radio("Retrieval mode", ["Traditional RAG", "Basic GraphRAG"], horizontal=True)
    query = st.text_input("Question", value="How does CRAG handle bad retrieval?")
    st.caption("Graph example: Which agentic retrieval approaches use self-reflection?")
    if st.button("Run Query", type="primary"):
        if not query.strip():
            st.warning("Enter a question first.")
        else:
            with st.spinner("Retrieving evidence and generating an answer…"):
                try:
                    service = text_rag if mode == "Traditional RAG" else graph_rag
                    st.session_state["result"] = service.answer(query.strip())
                except Exception as exc:
                    st.session_state.pop("result", None)
                    st.error(str(exc))
    if "result" in st.session_state:
        show_result(st.session_state["result"])

with architecture:
    st.subheader("Traditional RAG")
    st.code("Question → shared local embedding → FAISS Top-K PDF chunks → shared Groq LLM → answer + evidence", language=None)
    st.write("The question is compared directly with PDF chunks. Multiple chunks from the same paper may appear.")
    st.subheader("Basic Graph-Aware RAG")
    st.code("Question → shared local embedding → semantic graph seeds → bounded traversal\n→ candidate papers → relevant chunks within those papers → shared Groq LLM → answer + evidence", language=None)
    st.write("The graph contains curated paper-to-technique, paper-to-area, and paper-to-modality relationships. Supporting text comes only from graph-selected papers.")
    st.write("Both modes use all-MiniLM-L6-v2, the same PDF corpus, and the same final Groq model at temperature 0. The comparison changes the retrieval representation.")
    st.info("This is a basic metadata graph-aware baseline, not Microsoft GraphRAG or an implementation of the research methods described in the papers.")

with dataset:
    st.subheader("Research corpus")
    st.dataframe([p.model_dump() for p in papers], hide_index=True, width="stretch")
    st.caption("Graph categories and techniques follow the supplied specification. PDF text is extracted without OCR.")
