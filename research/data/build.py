"""Bounded-memory, checkpointed physical representation builders."""
from collections import defaultdict
import json
from pathlib import Path
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from research.common.config import load_config
from research.data.representations import normalized, SCHEMAS
from scripts.audit_stark_mag import StreamingMetadata, TensorReader, PrimitiveUnpickler, digest, process_memory


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


class Builder:
    def __init__(self, config_path):
        self.config = load_config(Path(config_path))
        self.options = self.config.representations
        if self.options is None:
            raise ValueError("Representation build configuration required")
        self.root = self.config.resolve_path("dataset")
        self.raw = self.root / "raw/stark_mag"
        self.source = self.raw / "extracted/processed"
        self.work = self.root / "_build/phase3"
        self.work.mkdir(parents=True, exist_ok=True)
        self.hash = self.config.config_hash()
        self.raw_manifest = json.loads((self.raw / "raw_manifest.json").read_text(encoding="utf-8"))
        if self.raw_manifest["dataset_revision"] != self.options.source_revision:
            raise ValueError("Pinned source revision mismatch")
        spec = {"config_hash": self.hash, "source_revision": self.options.source_revision,
                "source_checksums": {f["path"]: f["sha256"] for f in self.raw_manifest["files"]}}
        lock = self.work / "build_spec.json"
        if lock.exists() and json.loads(lock.read_text()) != spec:
            raise ValueError("Build specification changed; use an explicitly versioned fresh build directory")
        if not lock.exists():
            write_json(lock, spec)

    def complete(self, name):
        marker = self.work / (name + ".complete.json")
        if not marker.exists():
            return False
        data = json.loads(marker.read_text())
        if data["config_hash"] != self.hash:
            raise ValueError("Checkpoint config mismatch")
        for file in data["files"]:
            path = self.root / file["path"]
            if not path.exists() or path.stat().st_size != file["bytes"] or digest(path) != file["sha256"]:
                raise ValueError(f"Completed artifact changed: {path}")
        print(f"Reusing verified stage {name}", flush=True)
        return True

    def finish(self, name, paths, started, **extra):
        files = [{"path": p.relative_to(self.root).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths]
        write_json(self.work / (name + ".complete.json"), {"config_hash": self.hash, "files": files,
                   "elapsed_seconds": time.perf_counter() - started, "resources": process_memory(), **extra})
        print(f"Completed {name} in {time.perf_counter()-started:.1f}s", flush=True)

    def verify_raw(self):
        for file in self.raw_manifest["files"]:
            if digest(self.raw / file["path"]) != file["sha256"]:
                raise ValueError(f"Raw source changed: {file['path']}")

    def duckdb(self, path=":memory:", read_only=False):
        import duckdb
        con = duckdb.connect(str(path), read_only=read_only)
        con.execute(f"SET memory_limit='{self.options.duckdb_memory_limit}'")
        con.execute(f"SET threads={self.options.duckdb_threads}")
        temp = (self.work / "duckdb_temp").as_posix().replace("'", "''")
        con.execute(f"SET temp_directory='{temp}'")
        con.execute("SET preserve_insertion_order=false")
        return con

    def merge(self, files, target, schema):
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".parquet.tmp")
        with pq.ParquetWriter(temp, schema, compression="zstd") as writer:
            for path in sorted(files):
                for batch in pq.ParquetFile(path).iter_batches(batch_size=self.options.node_batch_size):
                    writer.write_batch(batch)
        temp.replace(target)

    def nodes(self):
        if self.complete("nodes"):
            return
        started = time.perf_counter()
        self.verify_raw()
        scan = json.loads((self.root / "_build/pickle_scan.json").read_text())
        if scan["source_sha256"] != digest(self.source / "node_info.pkl"):
            raise ValueError("Metadata pre-scan checksum mismatch")
        shard_dir = self.work / "node_shards"
        shard_dir.mkdir(exist_ok=True)
        size = self.options.node_batch_size
        buffers = defaultdict(list)
        current, expected_id = 0, 0
        shard_marker = lambda i: shard_dir / f"{i:06d}.json"
        good = set()
        for marker in shard_dir.glob("*.json"):
            values = json.loads(marker.read_text())
            if values["config_hash"] != self.hash:
                raise ValueError("Node shard config mismatch")
            for file in values["files"]:
                if digest(shard_dir / file["name"]) != file["sha256"]:
                    raise ValueError("Node shard checksum mismatch")
            good.add(int(marker.stem))

        def flush(i):
            if i in good:
                return
            files = []
            for name, rows in buffers.items():
                if rows:
                    path = shard_dir / f"{name}-{i:06d}.parquet"
                    temp = path.with_suffix(".tmp")
                    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[name]), temp, compression="zstd")
                    temp.replace(path)
                    files.append({"name": path.name, "sha256": digest(path), "rows": len(rows)})
            write_json(shard_marker(i), {"config_hash": self.hash, "files": files})
            buffers.clear()
            if i % 20 == 0:
                print(f"Node shard {i} durable", flush=True)

        def consume(node_id, row):
            nonlocal current, expected_id
            if node_id != expected_id:
                raise ValueError("Source node order is not contiguous global ID order")
            expected_id += 1
            shard = node_id // size
            if shard != current:
                flush(current)
                current = shard
            if shard not in good:
                for key, values in normalized(node_id, row).items():
                    buffers[key].extend(values)

        with (self.source / "node_info.pkl").open("rb", buffering=4*1024*1024) as file:
            loader = StreamingMetadata(file, set(scan["referenced_memo_ids"]), consume)
            loader.load()
        flush(current)
        if expected_id != self.options.source_nodes:
            raise ValueError("Node count differs from audited source")
        targets = {"canonical": "canonical/canonical_entities.parquet", "aliases": "canonical/alias_registry.parquet",
                   "nodes": "graph/nodes.parquet", "text": "text/text_documents.parquet"}
        paths = []
        for name, relative in targets.items():
            path = self.root / relative
            self.merge(shard_dir.glob(f"{name}-*.parquet"), path, SCHEMAS[name])
            paths.append(path)
        mapping = self.root / "graph/identity_mapping.json"
        write_json(mapping, {"mapping": "identity", "csr_row_equals_stark_global_node_id": True,
                             "node_count": expected_id, "min_id": 0, "max_id": expected_id-1})
        paths.append(mapping)
        self.finish("nodes", paths, started, nodes=expected_id,
                    counts={name: pq.ParquetFile(self.root / relative).metadata.num_rows for name, relative in targets.items()})

    def structured(self):
        if self.complete("structured"):
            return
        if not self.complete("nodes"):
            raise ValueError("Nodes stage must complete first")
        started = time.perf_counter()
        target = self.root / "structured/stark_mag.duckdb"
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = self.work / "structured.duckdb"
        # An interrupted temporary DB is rebuilt transactionally; official/finished files are untouched.
        with self.duckdb(temp) as con:
            glob = (self.work / "node_shards/structured-*.parquet").as_posix()
            con.execute("BEGIN")
            con.execute(f"CREATE OR REPLACE TABLE papers_structured AS SELECT * EXCLUDE(raw_source_json) FROM read_parquet('{glob}')")
            con.execute(f"CREATE OR REPLACE TABLE papers_structured_source AS SELECT paper_id, raw_source_json::JSON AS raw_source_json FROM read_parquet('{glob}')")
            con.execute("COMMIT")
            con.execute("CHECKPOINT")
            count = con.execute("SELECT count(*) FROM papers_structured").fetchone()[0]
            if count != self.options.source_papers:
                raise ValueError("Structured paper count mismatch")
        temp.replace(target)
        self.finish("structured", [target], started, papers=count)

    def edges(self):
        if self.complete("edges"):
            return
        started = time.perf_counter()
        with (self.source / "edge_type_dict.pkl").open("rb") as file:
            relation_map = PrimitiveUnpickler(file).load()
        index, types = TensorReader(self.source / "edge_index.pt"), TensorReader(self.source / "edge_types.pt")
        total = self.options.source_edges
        if index.layout["shape"] != (2, total) or types.layout["shape"] != (total,):
            raise ValueError("Source edge dimensions mismatch")
        shard_dir = self.work / "edge_shards"
        shard_dir.mkdir(exist_ok=True)
        for start in range(0, total, self.options.edge_batch_size):
            stop = min(total, start+self.options.edge_batch_size)
            name = f"edges-{start:09d}"
            path, marker = shard_dir / (name+".parquet"), shard_dir / (name+".json")
            if marker.exists():
                done = json.loads(marker.read_text())
                if done["config_hash"] != self.hash or digest(path) != done["sha256"]:
                    raise ValueError("Edge shard mismatch")
                continue
            source = index.read(start, stop-start, 0)
            target = index.read(start, stop-start, 1)
            relations = types.read(start, stop-start).astype(np.int8)
            ids = np.arange(start, stop, dtype=np.int64)
            names = pa.array([relation_map[int(r)] for r in relations])
            arrays = [pa.array(ids), pa.array(ids), pa.array(source), names, pa.array(relations), pa.array(target), pa.array(np.zeros(stop-start, dtype=bool))]
            table = pa.Table.from_arrays(arrays, schema=SCHEMAS["edges"])
            if self.options.derived_inverses:
                inverse = pa.Table.from_arrays([pa.array(ids+total), pa.array(ids), pa.array(target), names, pa.array(relations), pa.array(source), pa.array(np.ones(stop-start, dtype=bool))], schema=SCHEMAS["edges"])
                table = pa.concat_tables([table, inverse])
            temp = path.with_suffix(".tmp")
            pq.write_table(table, temp, compression="zstd", row_group_size=self.options.edge_batch_size)
            temp.replace(path)
            write_json(marker, {"config_hash": self.hash, "sha256": digest(path)})
            if start % 2000000 == 0:
                print(f"Source edges staged: {stop:,}/{total:,}", flush=True)
        target = self.root / "graph/edges.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.merge(shard_dir.glob("*.parquet"), target, SCHEMAS["edges"])
        self.finish("edges", [target], started, source_edges=total,
                    derived_edges=total if self.options.derived_inverses else 0, relation_map=relation_map)

    def csr(self):
        if self.complete("csr"):
            return
        if not self.complete("edges"):
            raise ValueError("Edges stage must complete first")
        started = time.perf_counter()
        n = self.options.source_nodes
        total = self.options.source_edges * (2 if self.options.derived_inverses else 1)
        temp = self.work / "csr_arrays"
        temp.mkdir(exist_ok=True)
        arrays = {name: np.lib.format.open_memmap(temp / (name+".npy"), mode="w+", dtype=dtype, shape=(total,))
                  for name, dtype in (("neighbors", np.uint32), ("edge_ids", np.int64), ("relation_ids", np.uint8), ("derived_inverse", np.bool_))}
        degrees = np.zeros(n, dtype=np.uint64)
        source_path = (self.root / "graph/edges.parquet").as_posix()
        with self.duckdb() as con:
            batches = con.execute(f"SELECT source_id,target_id,edge_id,relation_id,derived_inverse FROM read_parquet('{source_path}') ORDER BY source_id,derived_inverse,target_id,edge_id").fetch_record_batch(100000)
            cursor = 0
            for batch in batches:
                columns = {name: batch.column(i).to_numpy(zero_copy_only=False) for i, name in enumerate(batch.schema.names)}
                count = batch.num_rows
                for name, key in (("neighbors", "target_id"), ("edge_ids", "edge_id"), ("relation_ids", "relation_id"), ("derived_inverse", "derived_inverse")):
                    arrays[name][cursor:cursor+count] = columns[key]
                values, counts = np.unique(columns["source_id"], return_counts=True)
                np.add.at(degrees, values, counts.astype(np.uint64))
                cursor += count
            if cursor != total:
                raise ValueError("CSR traversal edge count mismatch")
        pointer = np.lib.format.open_memmap(temp / "indptr.npy", mode="w+", dtype=np.uint64, shape=(n+1,))
        pointer[0] = 0
        np.cumsum(degrees, out=pointer[1:])
        pointer.flush()
        del pointer
        for array in arrays.values():
            array.flush()
        arrays.clear()
        del array
        output = self.root / "graph/adjacency"
        output.mkdir(parents=True, exist_ok=True)
        paths = []
        for path in sorted(temp.glob("*.npy")):
            target = output / path.name
            path.replace(target)
            paths.append(target)
        self.finish("csr", paths, started, nodes=n, traversal_edges=total,
                    order="source_id, derived_inverse, target_id, edge_id")
