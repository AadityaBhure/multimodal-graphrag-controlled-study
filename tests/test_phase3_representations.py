"""Small adversarial fixtures for physical representation semantics and recovery."""
import json
import time
from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from research.data.build import Builder
from research.data.embeddings import populate_flat_index
from research.data.representations import normalized, nullable, venue, SCHEMAS


def paper(**changes):
    return dict(new_id=12, id=7, mag_id=100, type="paper", title="  Exact title  ", abstract="Abstract\n",
                **changes)


def test_text_source_whitespace_and_isolation():
    row = paper(Year=2020, DisplayName="Not the title", OriginalVenue="Private venue", Authors="Someone")
    result = normalized(12, row)
    assert result["text"] == [{"paper_id": 12, "title": "  Exact title  ", "abstract": "Abstract\n",
                                "content": "  Exact title  \n\nAbstract\n"}]
    assert result["nodes"][0]["search_text"] == "  Exact title  "
    assert "Authors" not in json.loads(result["structured"][0]["raw_source_json"])


@pytest.mark.parametrize("missing", [None, -1, "-1", "", float("nan")])
def test_missing_names_are_null_without_fabricated_alias(missing):
    result = normalized(4, {"new_id": 4, "id": 2, "mag_id": 101, "type": "author", "DisplayName": missing})
    assert result["canonical"][0]["display_name"] is None
    assert result["nodes"][0]["label"] is None
    assert result["nodes"][0]["node_id"] == 4
    assert result["aliases"] == []


def test_missing_fields_not_derived_from_date_or_zero_filled():
    result = normalized(12, paper(Date="2020-04-03", Year=-1, PaperCitationCount=0, PaperRank=-1))
    value = result["structured"][0]
    assert value["publication_year"] is None
    assert value["citation_count"] == 0
    assert value["paper_rank"] is None
    assert json.loads(value["raw_source_json"])["Year"] == -1
    assert nullable(0) == 0


@pytest.mark.parametrize("source,expected", [
    ({"JournalId": 5, "ConferenceSeriesId": 6, "OriginalVenue": "Fallback"}, ("journal", "5", None, "journal")),
    ({"JournalDisplayName": "Only name", "ConferenceSeriesId": 6}, ("journal", None, "Only name", "journal")),
    ({"JournalId": -1, "ConferenceSeriesId": 6, "ConferenceInstanceId": 7}, ("conference_series", "6", None, "conference_series")),
    ({"ConferenceInstanceId": 7, "ConferenceInstancesDisplayName": "Meeting"}, ("conference_instance", "7", "Meeting", "conference_instance")),
    ({"OriginalVenue": "Unclassified", "DocType": "Journal"}, ("original_venue", None, "Unclassified", None)),
    ({"DocType": "Journal"}, (None, None, None, None)),
])
def test_venue_precedence_and_no_inferred_taxonomy(source, expected):
    assert tuple(venue(source).values()) == expected


def test_global_id_guard_and_alias_ambiguity():
    with pytest.raises(ValueError, match="Global source ID"):
        normalized(13, paper())
    one = normalized(1, dict(new_id=1, id=99, mag_id=9, type="author", DisplayName="Ａlice  Smith"))
    two = normalized(2, dict(new_id=2, id=100, mag_id=10, type="author", DisplayName="alice smith"))
    assert one["aliases"][0]["alias"] == two["aliases"][0]["alias"]
    assert one["aliases"][0]["stark_node_id"] != two["aliases"][0]["stark_node_id"]


def tiny_builder(tmp_path):
    b = Builder.__new__(Builder)
    b.root = tmp_path
    b.work = tmp_path / "_build"
    b.work.mkdir()
    b.hash = "synthetic-fixture"
    b.options = SimpleNamespace(source_nodes=4, source_edges=2, derived_inverses=True,
                                duckdb_memory_limit="64MB", duckdb_threads=1)
    return b


def test_csr_traversal_null_node_isolation_and_restart(tmp_path):
    b = tiny_builder(tmp_path)
    path = tmp_path / "graph/edges.parquet"
    path.parent.mkdir()
    # Node 3 is isolated. Node 1 can represent an unnamed author; labels never enter CSR.
    rows = [dict(edge_id=i, source_edge_id=i % 2, source_id=s, relation="author___writes___paper",
                 relation_id=3, target_id=t, derived_inverse=i >= 2)
            for i, (s, t) in enumerate(((1, 0), (1, 2), (0, 1), (2, 1)))]
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS["edges"]), path)
    b.finish("edges", [path], time.perf_counter())
    # Uncommitted temporary partial arrays are safely overwritten on restart.
    partial = b.work / "csr_arrays"
    partial.mkdir()
    (partial / "neighbors.npy").write_bytes(b"interrupted")
    b.csr()
    root = tmp_path / "graph/adjacency"
    assert np.load(root / "indptr.npy").tolist() == [0, 1, 3, 4, 4]
    assert np.load(root / "neighbors.npy").tolist() == [1, 0, 2, 1]
    assert np.load(root / "edge_ids.npy").tolist() == [2, 0, 1, 3]
    assert np.load(root / "derived_inverse.npy").tolist() == [True, False, False, True]
    before = (b.work / "csr.complete.json").read_bytes()
    b.csr()
    assert (b.work / "csr.complete.json").read_bytes() == before
    with (root / "neighbors.npy").open("ab") as file:
        file.write(b"tampering")
    with pytest.raises(ValueError, match="Completed artifact changed"):
        b.csr()


def test_preallocated_faiss_matches_normal_add_and_serialization(tmp_path):
    import faiss
    values = np.random.default_rng(91).normal(size=(17, 8)).astype(np.float32)
    faiss.normalize_L2(values)
    paths = []
    for i, chunk in enumerate((values[:5], values[5:12], values[12:])):
        path = tmp_path / f"{i}.npy"
        np.save(path, chunk)
        paths.append(path)
    expected = faiss.IndexFlatIP(8)
    expected.add(values)
    actual = faiss.IndexFlatIP(8)
    populate_flat_index(actual, paths, 17, 8)
    assert np.array_equal(actual.reconstruct_n(0, 17), values)
    for a, e in zip(actual.search(values, 4), expected.search(values, 4)):
        np.testing.assert_array_equal(a, e)
    path = tmp_path / "index.faiss"
    faiss.write_index(actual, str(path))
    restored = faiss.read_index(str(path))
    assert restored.ntotal == 17
    np.testing.assert_array_equal(restored.reconstruct_n(0, 17), values)


def test_embedding_shards_resume_after_interruption(tmp_path, monkeypatch):
    import research.data.embeddings as module
    b = tiny_builder(tmp_path)
    b.options.source_papers = 7
    b.options.embedding_shard_size = 3
    b.options.embedding_batch_size = 2
    b.options.embedding_dimension = 4
    source = tmp_path / "text/text_documents.parquet"
    source.parent.mkdir()
    pq.write_table(pa.table({"paper_id": list(range(7)), "content": [str(i) for i in range(7)]}), source)
    b.finish("nodes", [source], time.perf_counter())
    calls = []
    fail_once = [True]

    class FakeEncoder:
        def __init__(self, builder, parity_texts):
            root = builder.root / "text/faiss"
            root.mkdir(exist_ok=True)
            (root / "model.onnx").write_bytes(b"synthetic test model")
            (root / "encoder.json").write_text("{}")
            self.metadata = {"onnx_sha256": "synthetic-model"}

        def encode(self, texts, batch_size):
            if texts[0] == "3" and fail_once[0]:
                fail_once[0] = False
                raise RuntimeError("intentional interruption")
            calls.append(list(texts))
            return np.full((len(texts), 4), .5, dtype=np.float32)

    monkeypatch.setattr(module, "Encoder", FakeEncoder)
    with pytest.raises(RuntimeError, match="intentional interruption"):
        module.build_embeddings(b)
    marker = b.work / "embedding_shards/000000.json"
    previous = marker.read_bytes()
    assert not (b.work / "embeddings.complete.json").exists()
    module.build_embeddings(b)
    assert calls == [["0", "1", "2"], ["3", "4", "5"], ["6"]]
    assert marker.read_bytes() == previous
    assert b.complete("embeddings")
