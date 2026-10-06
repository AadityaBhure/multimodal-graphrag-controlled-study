"""Full-source, bounded-memory Phase 3 audits; never constructs a benchmark."""
from collections import Counter
from datetime import date, datetime, timezone
import gc
from importlib.metadata import version
import json
import time
import unicodedata

import numpy as np
import pyarrow.parquet as pq

from research.data.build import write_json
from research.common.config import PROJECT_ROOT
from research.data.representations import SCHEMAS, RAW_FIELDS
from scripts.audit_stark_mag import StreamingMetadata, TensorReader, PrimitiveUnpickler, process_memory


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rows(paths):
    for path in paths:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=4096):
            yield from batch.to_pylist()


def source_null(value):
    # Independent audit interpretation of the audited source's missing sentinels.
    return value is None or value in (-1, "-1", "") or isinstance(value, float) and np.isnan(value)


def audit_nodes(b):
    paths = {"canonical": "canonical/canonical_entities.parquet", "nodes": "graph/nodes.parquet",
             "aliases": "canonical/alias_registry.parquet", "text": "text/text_documents.parquet"}
    streams = {}
    for name, path in paths.items():
        require(pq.read_schema(b.root / path) == SCHEMAS[name], f"Schema isolation: {name}")
        streams[name] = rows([b.root / path])
    streams["structured"] = rows(sorted((b.work / "node_shards").glob("structured-*.parquet")))
    counts, missing, namespaces = Counter(), Counter(), Counter()
    samples = {}

    def consume(node_id, raw):
        typ = raw["type"]
        counts[typ] += 1
        label = raw["title"] if typ == "paper" else raw["DisplayName"]
        label = None if source_null(label) else label
        c, g = next(streams["canonical"]), next(streams["nodes"])
        require(c == dict(canonical_id=f"stark:{node_id}", stark_node_id=node_id, source_id=raw["id"],
                         mag_id=raw["mag_id"], entity_type=typ, display_name=label), f"Registry source mismatch {node_id}")
        require(g == dict(node_id=node_id, canonical_id=f"stark:{node_id}", node_type=typ, label=label, search_text=label),
                f"Graph semantic leakage/source mismatch {node_id}")
        if label is None:
            missing[typ] += 1
            samples.setdefault("missing_name", g)
        normalized_alias = " ".join(unicodedata.normalize("NFKC", label).casefold().split()) if label is not None else ""
        if normalized_alias:
            a = next(streams["aliases"])
            require(a == dict(alias=normalized_alias, canonical_id=f"stark:{node_id}", stark_node_id=node_id, entity_type=typ),
                    f"Alias mismatch {node_id}")
        if typ != "paper":
            return
        t, s = next(streams["text"]), next(streams["structured"])
        require(t == dict(paper_id=node_id, title=raw["title"], abstract=raw["abstract"],
                          content=raw["title"] + "\n\n" + raw["abstract"]), f"Text source/leakage mismatch {node_id}")
        require(s["paper_id"] == node_id, "Structured identity mismatch")
        for column, source in (("publication_date", "Date"), ("publication_year", "Year"),
                               ("citation_count", "PaperCitationCount"), ("paper_rank", "PaperRank"), ("document_type", "DocType")):
            value = raw.get(source)
            expected = None if source_null(value) else date.fromisoformat(value) if source == "Date" else value
            require(s[column] == expected, f"Structured value/NULL mismatch {node_id}/{column}")
            if expected is None:
                missing[column] += 1
        chosen = None
        for prefix, name_key, namespace in (("JournalId", "JournalDisplayName", "journal"),
                ("ConferenceSeriesId", "ConferenceSeriesDisplayName", "conference_series"),
                ("ConferenceInstanceId", "ConferenceInstancesDisplayName", "conference_instance")):
            vid, name = raw.get(prefix), raw.get(name_key)
            if not source_null(vid) or not source_null(name):
                chosen = (namespace, None if source_null(vid) else str(int(vid)), None if source_null(name) else name, namespace)
                break
        if chosen is None:
            original = raw.get("OriginalVenue")
            chosen = (None, None, None, None) if source_null(original) else ("original_venue", None, original, None)
        require(tuple(s[k] for k in ("venue_namespace", "venue_id", "venue_name", "venue_type")) == chosen,
                f"Venue precedence/NULL mismatch {node_id}")
        namespaces[str(chosen[0])] += 1
        payload = json.loads(s["raw_source_json"])
        require(set(payload) == set(RAW_FIELDS), "Structured raw payload leaks fields")
        for key, value in payload.items():
            expected = raw.get(key)
            if isinstance(expected, float) and not np.isfinite(expected):
                expected = {"nonfinite_float": repr(expected)}
            require(value == expected, f"Raw audit column changed {node_id}/{key}")
        samples.setdefault("paper", {"canonical": c, "graph": g, "text": t, "structured": s})
        if s["publication_year"] is None:
            samples.setdefault("null_structured", s)

    scan = json.loads((b.root / "_build/pickle_scan.json").read_text())
    with (b.source / "node_info.pkl").open("rb", buffering=4*1024*1024) as file:
        StreamingMetadata(file, set(scan["referenced_memo_ids"]), consume).load()
    for name, stream in streams.items():
        require(next(stream, None) is None, f"Unexpected extra {name} rows")
    require(sum(counts.values()) == b.options.source_nodes and counts["paper"] == b.options.source_papers, "Node counts")
    return {"entity_counts": dict(counts), "missing_values": dict(missing), "venue_namespaces": dict(namespaces), "samples": samples}


def audit_sql(b):
    path = (b.root / "structured/stark_mag.duckdb").as_posix()
    with b.duckdb(path, read_only=True) as con:
        for name, relative in (("registry", "canonical/canonical_entities.parquet"), ("text_view", "text/text_documents.parquet"),
                               ("graph_nodes", "graph/nodes.parquet"), ("aliases", "canonical/alias_registry.parquet")):
            con.execute(f"CREATE TEMP VIEW {name} AS SELECT * FROM read_parquet('{(b.root / relative).as_posix()}')")
        for table, key, expected in (("registry", "stark_node_id", b.options.source_nodes), ("graph_nodes", "node_id", b.options.source_nodes),
                                     ("text_view", "paper_id", b.options.source_papers), ("papers_structured", "paper_id", b.options.source_papers)):
            value = con.execute(f"SELECT count(*),count(DISTINCT {key}),count({key}) FROM {table}").fetchone()
            require(value == (expected, expected, expected), f"Uniqueness/NULL identity: {table}")
        joined = con.execute("SELECT count(*) FROM registry c JOIN graph_nodes g ON c.stark_node_id=g.node_id JOIN text_view t ON t.paper_id=c.stark_node_id JOIN papers_structured s ON s.paper_id=c.stark_node_id WHERE c.entity_type='paper'").fetchone()[0]
        require(joined == b.options.source_papers, "Cross-view join coverage")
        # Exact two-way multiset equality also verifies persisted DuckDB NULLs, types and raw audit table.
        glob = (b.work / "node_shards/structured-*.parquet").as_posix()
        left = "SELECT p.*, CAST(r.raw_source_json AS VARCHAR) AS raw_source_json FROM papers_structured p JOIN papers_structured_source r USING(paper_id)"
        right = f"SELECT * FROM read_parquet('{glob}')"
        mismatch = con.execute(f"SELECT count(*) FROM (({left} EXCEPT ALL {right}) UNION ALL ({right} EXCEPT ALL {left}))").fetchone()[0]
        require(mismatch == 0, "DuckDB differs from audited source projection")
        names = [r[0] for r in con.execute("DESCRIBE papers_structured").fetchall()]
        require(names == SCHEMAS["structured"].names[:-1], "Structured schema isolation")
        predicates = {}
        for predicate in ("publication_year IS NULL", "citation_count IS NULL", "paper_rank IS NULL", "publication_date IS NULL",
                          "publication_year >= 2000 AND citation_count >= 100", "venue_namespace='journal'", "venue_namespace='original_venue' AND venue_id IS NULL"):
            persisted = con.execute(f"SELECT count(*) FROM papers_structured WHERE {predicate}").fetchone()[0]
            source = con.execute(f"SELECT count(*) FROM read_parquet('{glob}') WHERE {predicate}").fetchone()[0]
            require(persisted == source, f"Predicate mismatch: {predicate}")
            predicates[predicate] = persisted
        alias_rows, unique_aliases = con.execute("SELECT count(*),count(DISTINCT alias) FROM aliases").fetchone()
        ambiguous = con.execute("SELECT count(*) FROM (SELECT alias FROM aliases GROUP BY alias HAVING count(*)>1)").fetchone()[0]
        return {"joined_papers": joined, "duckdb_exact_projection_mismatches": mismatch, "predicates": predicates,
                "alias_rows": alias_rows, "distinct_aliases": unique_aliases, "ambiguous_aliases_preserved": ambiguous}


def audit_edges(b):
    file = b.root / "graph/edges.parquet"
    require(pq.read_schema(file) == SCHEMAS["edges"], "Graph edge schema")
    index, types = TensorReader(b.source / "edge_index.pt"), TensorReader(b.source / "edge_types.pt")
    with (b.source / "edge_type_dict.pkl").open("rb") as stream:
        names = PrimitiveUnpickler(stream).load()
    counts = Counter()
    next_source_id = {False: 0, True: 0}
    for batch in pq.ParquetFile(file).iter_batches(batch_size=10000):
        cols = {n: batch.column(i).to_numpy(zero_copy_only=False) for i, n in enumerate(batch.schema.names) if n != "relation"}
        ids, flags = cols["source_edge_id"], cols["derived_inverse"]
        # A batch can straddle the final short original/inverse block. Audit contiguous runs.
        cuts = np.r_[0, np.flatnonzero((np.diff(ids) != 1) | (flags[1:] != flags[:-1]))+1, len(ids)]
        expected_names = []
        for left, right in zip(cuts[:-1], cuts[1:]):
            start, count, inverse = int(ids[left]), int(right-left), bool(flags[left])
            require(start == next_source_id[inverse], "Source edge coverage/uniqueness")
            next_source_id[inverse] += count
            require(0 <= start < start+count <= b.options.source_edges, "Source edge ID bounds")
            source, target = index.read(start, count, 0), index.read(start, count, 1)
            rel = types.read(start, count)
            if inverse:
                source, target = target, source
            for key, expected in (("source_id", source), ("target_id", target), ("relation_id", rel),
                                  ("edge_id", np.arange(start, start+count)+(b.options.source_edges if inverse else 0))):
                require(np.array_equal(cols[key][left:right], expected), f"Source edge mismatch: {key}")
            require(np.all(source >= 0) and np.all(target >= 0) and np.all(source < b.options.source_nodes) and np.all(target < b.options.source_nodes), "Endpoint bounds")
            expected_names.extend(names[int(r)] for r in rel)
            unique, number = np.unique(rel, return_counts=True)
            for r, n in zip(unique, number):
                counts[(names[int(r)], inverse)] += int(n)
        require(batch.column("relation").to_pylist() == expected_names, "Official relation spelling mismatch")
    result = {"official": {}, "derived_inverse": {}}
    for (name, inverse), count in counts.items():
        result["derived_inverse" if inverse else "official"][name] = count
    expected = json.loads((PROJECT_ROOT / "documentation/phase2/audit_stark_mag.json").read_text())["relation_counts"]
    require(result["official"] == expected, "Official relation counts changed")
    require(result["derived_inverse"] == (expected if b.options.derived_inverses else {}), "Inverse counts")
    return result


def audit_csr(b):
    arrays = {name: np.load(b.root / f"graph/adjacency/{name}.npy", mmap_mode="r", allow_pickle=False)
              for name in ("indptr", "neighbors", "edge_ids", "relation_ids", "derived_inverse")}
    pointer = arrays["indptr"]
    total = b.options.source_edges * (2 if b.options.derived_inverses else 1)
    require(len(pointer) == b.options.source_nodes+1 and pointer[0] == 0 and pointer[-1] == total, "CSR pointers")
    require(np.all(pointer[1:] >= pointer[:-1]), "CSR pointer monotonicity")
    for name, array in arrays.items():
        require(len(array) == (b.options.source_nodes+1 if name == "indptr" else total), f"CSR dimensions {name}")
    path = (b.root / "graph/edges.parquet").as_posix()
    position = 0
    with b.duckdb() as con:
        batches = con.execute(f"SELECT source_id,target_id,edge_id,relation_id,derived_inverse FROM read_parquet('{path}') ORDER BY source_id,derived_inverse,target_id,edge_id").fetch_record_batch(100000)
        for batch in batches:
            end = position+batch.num_rows
            ids = np.searchsorted(pointer, np.arange(position, end, dtype=np.uint64), side="right")-1
            require(np.array_equal(ids, batch.column(0).to_numpy()), "CSR source row lookup")
            for i, name in enumerate(("neighbors", "edge_ids", "relation_ids", "derived_inverse"), 1):
                require(np.array_equal(arrays[name][position:end], batch.column(i).to_numpy(zero_copy_only=False)), f"CSR traversal mismatch {name}")
            position = end
    require(position == total, "CSR complete coverage")
    # Real paper -> author (inverse writes) -> paper (official writes) traversal.
    sample = None
    for paper in range(1172724, min(1173724, b.options.source_nodes)):
        start, end = map(int, pointer[paper:paper+2])
        hits = np.flatnonzero((arrays["relation_ids"][start:end] == 3) & arrays["derived_inverse"][start:end])
        if len(hits):
            author = int(arrays["neighbors"][start+hits[0]])
            a, z = map(int, pointer[author:author+2])
            candidates = arrays["neighbors"][a:z][(arrays["relation_ids"][a:z] == 3) & ~arrays["derived_inverse"][a:z]]
            require(paper in candidates, "Inverse traversal failed to return source paper")
            sample = {"paper": paper, "author": author, "author_papers": candidates[:10].tolist(), "author_paper_count": len(candidates)}
            break
    require(sample is not None, "No traversal sample")
    null_node = 9899
    null_start, null_end = map(int, pointer[null_node:null_node+2])
    require(null_end > null_start, "Known NULL-label author lost structural edges")
    return {"rows": b.options.source_nodes, "traversal_edges_checked": position, "traversal_sample": sample,
            "null_label_node_traversal": {"node_id": null_node, "degree": null_end-null_start,
                                           "neighbor_sample": arrays["neighbors"][null_start:min(null_end, null_start+5)].tolist()},
            "zero_degree_nodes": int(np.sum(pointer[1:] == pointer[:-1]))}


def audit_faiss(b):
    import faiss
    faiss.omp_set_num_threads(2)
    root = b.root / "text/faiss"
    index = faiss.read_index(str(root / "index.faiss"))
    require(index.ntotal == b.options.source_papers and index.d == b.options.embedding_dimension and index.metric_type == faiss.METRIC_INNER_PRODUCT, "FAISS metadata")
    mapping = np.load(root / "row_to_paper_id.npy", mmap_mode="r", allow_pickle=False)
    require(mapping.dtype == np.int64 and mapping.shape == (index.ntotal,), "FAISS mapping shape/type")
    offset, queries = 0, []
    for number, path in enumerate(sorted((root / "embeddings").glob("vectors-*.npy"))):
        vectors = np.load(path, allow_pickle=False)
        ids = np.load(path.with_name(path.name.replace("vectors-", "ids-")), allow_pickle=False)
        require(np.array_equal(ids, np.arange(1172724+offset, 1172724+offset+len(ids))), "Embedding global-ID mapping")
        require(np.array_equal(mapping[offset:offset+len(ids)], ids), "FAISS row mapping")
        require(np.array_equal(index.reconstruct_n(offset, len(ids)), vectors), "FAISS vector corruption")
        require(np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5), "Vector normalization")
        if number % 20 == 0:
            queries.append(vectors[0].copy())
        offset += len(ids)
    require(offset == index.ntotal, "FAISS total vectors")
    scores, hits = index.search(np.array(queries), 5)
    require(np.allclose(scores[:, 0], 1, atol=1e-5) and np.all(hits >= 0) and np.all(hits < index.ntotal), "FAISS retrieval sanity")
    result = {"rows_checked": offset, "dimension": index.d, "exact_vector_equality": True, "search_queries": len(queries),
              "sample_top5_paper_ids": mapping[hits[0]].tolist(), "sample_top5_scores": scores[0].tolist()}
    del index, mapping
    gc.collect()
    return result


def validate(b, section="all"):
    started = time.perf_counter()
    b.verify_raw()
    functions = {"nodes": audit_nodes, "sql": audit_sql, "edges": audit_edges, "csr": audit_csr, "faiss": audit_faiss}
    results = {}
    for name, operation in functions.items():
        if section not in ("all", name):
            continue
        start = time.perf_counter()
        result = operation(b)
        record = {"status": "pass", "config_hash": b.hash, "result": result,
                  "elapsed_seconds": time.perf_counter()-start, "resources": process_memory()}
        write_json(b.work / f"audit_{name}.json", json.loads(json.dumps(record, default=str)))
        results[name] = record
        print(f"Audit {name} passed in {record['elapsed_seconds']:.1f}s", flush=True)
    return {"status": "pass", "sections": list(results), "elapsed_seconds": time.perf_counter()-started}


def manifest(b):
    from pathlib import Path
    import platform
    from scripts.audit_stark_mag import digest
    stages = {}
    for name in ("nodes", "structured", "edges", "csr", "embeddings", "faiss"):
        require(b.complete(name), f"Stage incomplete: {name}")
        stages[name] = json.loads((b.work / f"{name}.complete.json").read_text())
    audits = {}
    for name in ("nodes", "sql", "edges", "csr", "faiss"):
        audits[name] = json.loads((b.work / f"audit_{name}.json").read_text())
        require(audits[name]["status"] == "pass" and audits[name]["config_hash"] == b.hash, f"Audit incomplete: {name}")
    b.verify_raw()
    files = [f for s in stages.values() for f in s["files"]]
    previous = b.root / "manifest.json"
    timestamp = json.loads(previous.read_text())["created_at"] if previous.exists() else datetime.now(timezone.utc).isoformat()
    implementation = [*Path("research/data").glob("*.py"), Path("research/common/config.py"),
                      Path("configs/phase3.yaml"), Path("scripts/build_mmg_stark_mag.py"), Path("scripts/validate_dataset.py")]
    result = {"schema_version": "1.0", "dataset_version": b.options.version, "status": "validated",
              "created_at": timestamp, "config_hash": b.hash, "build_configuration": b.config.public_dict(),
              "python_version": platform.python_version(),
              "approved_phase2_checkpoint": "f8fc9a29f95b008a0216620449568f8bba4599a6",
              "implementation_sha256": {p.as_posix(): digest(p) for p in implementation},
              "source_revision": b.options.source_revision, "official_directed_edges": b.options.source_edges,
              "derived_inverse_edges": b.options.source_edges if b.options.derived_inverses else 0,
              "authoritative_identity": "STaRK global node ID; CSR row uses identity mapping",
              "leakage_policy": b.options.leakage_policy_version,
              "text_content": "title + '\\n\\n' + abstract; only source title/abstract",
              "graph_semantics": "paper title only; source display names or NULL; inverse edges traversal only",
              "missing_values": "NULL; audited source sentinels retained in structured audit JSON",
              "benchmark": "unbuilt; original 84 human QA records unchanged; exclusions deferred to Phase 4",
              "packages": {p: version(p) for p in ("numpy", "pyarrow", "duckdb", "faiss-cpu", "torch", "sentence-transformers", "onnx", "onnxruntime-gpu")},
              "files": files, "output_bytes": sum(f["bytes"] for f in files), "build_stages": stages, "audits": audits,
              "schemas": {k: str(v) for k, v in SCHEMAS.items()}}
    result["field_definition_document"] = {"path": "documentation/phase3/Representation_Contract.md",
                                            "sha256": digest(Path("documentation/phase3/Representation_Contract.md"))}
    result["field_definitions"] = {
        "paper_id/node_id/stark_node_id": "Authoritative original STaRK global node ID, integer",
        "canonical_id": "stark: followed by the original global node ID",
        "canonical.source_id": "Original type-local ID retained for provenance",
        "mag_id": "Original Microsoft Academic Graph ID; not a cross-view join key",
        "content": "Exact source title, two newline characters, exact source abstract",
        "label/search_text": "Paper title only, or source entity DisplayName; NULL if absent",
        "source_edge_id": "Column ordinal in the original official directed edge tensor",
        "derived_inverse": "True only for swapped-endpoint traversal edges; never a source-edge claim",
        "publication_date/publication_year": "Source Date/Year independently preserved, nullable",
        "citation_count/paper_rank": "Source PaperCitationCount/PaperRank, not recomputed, nullable",
        "document_type": "Source DocType, independent of normalized venue classification",
        "venue_namespace/venue_id/venue_name/venue_type": "Approved journal > conference_series > conference_instance > original_venue precedence; missing components remain NULL",
        "raw_source_json": "Original structured-only audit columns with sentinels retained",
        "row_to_paper_id": "FAISS zero-based row ordinal to original STaRK paper node ID"}
    write_json(b.root / "manifest.json", result)
    target = Path("documentation/phase3")
    write_json(target / "representation_manifest.json", result)
    print(f"Validated manifest: {len(files)} files, {result['output_bytes']:,} bytes", flush=True)
