"""Read-only official-source audit with streaming metadata and chunked tensors.

No torch import, graph object, adjacency, research view or benchmark creation.
Pickle execution is restricted to primitive metadata; tensor globals are mapped
to inert layout descriptors and never imported or executed from the payload.
"""
import argparse
import ast
from collections import Counter, defaultdict, OrderedDict
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import pickle
import pickletools
import struct
import sys
import time
from zipfile import ZipFile, ZIP_STORED

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/MMG_STARK_MAG/raw/stark_mag"
BUILD = ROOT / "data/MMG_STARK_MAG/_build"
SAFE_OPS = {"PROTO", "FRAME", "EMPTY_DICT", "MEMOIZE", "MARK", "BININT1", "BININT2", "BININT",
            "LONG1", "LONG4", "SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "BINFLOAT",
            "BINGET", "LONG_BINGET", "BINPUT", "LONG_BINPUT", "SETITEM", "SETITEMS", "STOP",
            "NONE", "NEWTRUE", "NEWFALSE"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def scan_pickle(path):
    needed, ops = set(), Counter()
    last = 0
    with Path(path).open("rb", buffering=4 * 1024 * 1024) as f:
        for op, arg, pos in pickletools.genops(f):
            if op.name not in SAFE_OPS:
                raise ValueError(f"Unsupported metadata pickle opcode: {op.name}")
            ops[op.name] += 1
            if op.name in {"BINGET", "LONG_BINGET"}:
                needed.add(arg)
            if pos - last > 128 * 1024 * 1024:
                print(f"Metadata pre-scan: {pos:,} bytes", flush=True)
                last = pos
    return needed, dict(ops)


class SelectiveMemo:
    def __init__(self, needed):
        self.needed, self.values, self.next_id = needed, {}, 0

    def __len__(self):
        return self.next_id

    def __setitem__(self, key, value):
        self.next_id = max(self.next_id, key + 1)
        if key in self.needed:
            self.values[key] = value

    def __getitem__(self, key):
        return self.values[key]


class RecordSink:
    def __init__(self, callback):
        self.callback = callback
        self.count = 0

    def __setitem__(self, key, value):
        self.callback(key, value)
        self.count += 1


class StreamingMetadata(pickle._Unpickler):
    def __init__(self, file, needed, callback):
        super().__init__(file)
        self.memo = SelectiveMemo(needed)
        self.sink = RecordSink(callback)
        self.first_dict = True
        self.dispatch = {ord(op.code): self.dispatch[ord(op.code)] for op in pickletools.opcodes if op.name in SAFE_OPS}
        self.dispatch[pickle.EMPTY_DICT[0]] = StreamingMetadata.empty_dict

    def empty_dict(self):
        self.append(self.sink if self.first_dict else {})
        self.first_dict = False

    def find_class(self, module, name):
        raise ValueError("Metadata globals are forbidden")


class PrimitiveUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("Type dictionaries must not contain executable globals")


def tensor_descriptor(storage, offset, shape, stride, requires_grad, hooks):
    return {"storage": storage, "offset": offset, "shape": tuple(shape), "stride": tuple(stride)}


class TensorHeader(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {("torch._utils", "_rebuild_tensor_v2"): tensor_descriptor,
                   ("torch", "LongStorage"): "int64", ("collections", "OrderedDict"): OrderedDict}
        if (module, name) not in allowed:
            raise ValueError(f"Unsupported tensor header global: {module}.{name}")
        return allowed[module, name]

    def persistent_load(self, value):
        kind, dtype, key, device, size = value
        if kind != "storage" or dtype != "int64" or device != "cpu":
            raise ValueError("Unsupported tensor storage")
        return {"key": key, "elements": size, "dtype": dtype}


class TensorReader:
    def __init__(self, path):
        self.path = Path(path)
        with ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith("/data.pkl"))
            self.layout = TensorHeader(io.BytesIO(z.read(name))).load()
            storage_name = name.rsplit("/", 1)[0] + "/data/" + self.layout["storage"]["key"]
            info = z.getinfo(storage_name)
            if info.compress_type != ZIP_STORED or info.file_size != self.layout["storage"]["elements"] * 8:
                raise ValueError("Tensor storage must be uncompressed int64 bytes")
            byteorder_name = name.rsplit("/", 1)[0] + "/byteorder"
            self.byteorder = z.read(byteorder_name).decode() if byteorder_name in z.namelist() else "little"
            if self.byteorder != "little":
                raise ValueError("Unsupported tensor byte order")
        with self.path.open("rb") as f:
            f.seek(info.header_offset)
            header = f.read(30)
            if header[:4] != b"PK\x03\x04":
                raise ValueError("Invalid ZIP local header")
            filename_len, extra_len = struct.unpack_from("<HH", header, 26)
            self.start = info.header_offset + 30 + filename_len + extra_len
        self.storage_bytes = info.file_size

    def read(self, start, count, row=None):
        shape, stride = self.layout["shape"], self.layout["stride"]
        if len(shape) not in {1, 2} or stride[-1] != 1 or start < 0 or count < 0 or start + count > shape[-1]:
            raise ValueError("Unsupported tensor slice")
        if len(shape) == 2 and (row is None or not 0 <= row < shape[0]):
            raise ValueError("Tensor row required")
        offset = self.layout["offset"] + start + (row * stride[0] if row is not None else 0)
        if (offset + count) * 8 > self.storage_bytes:
            raise ValueError("Tensor view exceeds storage")
        with self.path.open("rb") as f:
            f.seek(self.start + offset * 8)
            values = np.fromfile(f, dtype="<i8", count=count)
        if len(values) != count:
            raise ValueError("Truncated tensor storage")
        return values


def absent(value):
    return value is None or (isinstance(value, float) and math.isnan(value)) or value == -1 or value == "-1" or value == ""


def process_memory():
    if sys.platform != "win32":
        return {"peak_working_set_bytes": None}
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("peak", "current", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]
    data = Counters()
    data.cb = ctypes.sizeof(data)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle), ctypes.byref(data), data.cb)
    return {"peak_working_set_bytes": data.peak if ok else None,
            "current_working_set_bytes": data.current if ok else None}


def audit(raw, output, chunk_size=100_000):
    import csv
    started = time.perf_counter()
    manifest = json.loads((raw / "raw_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = raw / entry["path"]
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"Source integrity failure: {entry['path']}")
    p = raw / "extracted/processed"
    type_maps = {}
    for name in ("node_type_dict", "edge_type_dict"):
        with (p / (name + ".pkl")).open("rb") as f:
            type_maps[name] = PrimitiveUnpickler(f).load()
    node_map, edge_map = type_maps["node_type_dict"], type_maps["edge_type_dict"]
    readers = {name: TensorReader(p / (name + ".pt")) for name in ("node_types", "edge_types", "edge_index")}
    n = readers["node_types"].layout["shape"][0]
    nodes = readers["node_types"].read(0, n)  # Only 15 MB, not an in-memory graph.
    if set(np.unique(nodes)) != set(node_map):
        raise ValueError("Node types do not match dictionary")
    node_counts = {node_map[int(k)]: int(v) for k, v in zip(*np.unique(nodes, return_counts=True))}
    e = readers["edge_types"].layout["shape"][0]
    if readers["edge_index"].layout["shape"] != (2, e):
        raise ValueError("Edge tensor dimensions disagree")
    relations, endpoint_types = Counter(), Counter()
    self_loops = 0
    for start in range(0, e, chunk_size):
        count = min(chunk_size, e - start)
        types = readers["edge_types"].read(start, count)
        src = readers["edge_index"].read(start, count, 0)
        dst = readers["edge_index"].read(start, count, 1)
        if min(int(src.min()), int(dst.min())) < 0 or max(int(src.max()), int(dst.max())) >= n:
            raise ValueError("Out-of-range edge endpoint")
        self_loops += int(np.count_nonzero(src == dst))
        for k, v in zip(*np.unique(types, return_counts=True)):
            if int(k) not in edge_map:
                raise ValueError("Unknown relation type")
            relations[edge_map[int(k)]] += int(v)
        combos = nodes[src] * 100 + types * 10 + nodes[dst]
        for k, v in zip(*np.unique(combos, return_counts=True)):
            endpoint_types[(int(k) // 100, (int(k) // 10) % 10, int(k) % 10)] += int(v)
    print(f"Audited {n:,} nodes and {e:,} stored directed edges", flush=True)
    attributes = defaultdict(lambda: defaultdict(lambda: {"present": 0, "missing_or_sentinel": 0, "value_types": Counter(), "samples": []}))
    seen = np.zeros(n, dtype=np.bool_)
    metadata_counts = Counter()
    date_year_disagreements = 0

    def record(node_id, row):
        nonlocal date_year_disagreements
        if not isinstance(node_id, int) or not 0 <= node_id < n or seen[node_id]:
            raise ValueError("Invalid or duplicate metadata node ID")
        if row["new_id"] != node_id or row["type"] != node_map[int(nodes[node_id])]:
            raise ValueError("Metadata ID/type disagrees with tensors")
        seen[node_id] = True
        typ = row["type"]
        metadata_counts[typ] += 1
        for key, value in row.items():
            field = attributes[typ][key]
            field["present"] += 1
            field["value_types"][type(value).__name__] += 1
            if absent(value):
                field["missing_or_sentinel"] += 1
            elif len(field["samples"]) < 2:
                sample = repr(value)[:180]
                if sample not in field["samples"]:
                    field["samples"].append(sample)
        if typ == "paper" and not absent(row.get("Date")) and not absent(row.get("Year")):
            if str(row["Date"])[:4] != str(row["Year"]):
                date_year_disagreements += 1
        if sum(metadata_counts.values()) % 250_000 == 0:
            print(f"Streamed {sum(metadata_counts.values()):,} metadata records", flush=True)

    metadata_path = p / "node_info.pkl"
    metadata_hash = next(f["sha256"] for f in manifest["files"] if f["path"].endswith("/node_info.pkl"))
    cache = BUILD / "pickle_scan.json"
    scan = json.loads(cache.read_text()) if cache.exists() else {}
    if scan.get("source_sha256") == metadata_hash:
        needed, ops = set(scan["referenced_memo_ids"]), scan["opcode_counts"]
        if set(ops) - SAFE_OPS:
            raise ValueError("Unsupported cached metadata opcode")
    else:
        needed, ops = scan_pickle(metadata_path)
        BUILD.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"source_sha256": metadata_hash, "referenced_memo_ids": sorted(needed), "opcode_counts": ops}))
    with metadata_path.open("rb", buffering=4 * 1024 * 1024) as f:
        loader = StreamingMetadata(f, needed, record)
        sink = loader.load()
    if not seen.all() or dict(metadata_counts) != node_counts:
        raise ValueError("Metadata coverage does not match tensor counts")
    qa = {}
    ids_by_file = {}
    findings = []
    for name in ("stark_qa.csv", "stark_qa_human_generated_eval.csv"):
        path = raw / "qa/mag/stark_qa" / name
        ids, total_answers, multiple, empty = set(), 0, 0, 0
        answer_types, invalid_answers = Counter(), []
        with path.open(encoding="utf-8", newline="") as f:
            rows = csv.DictReader(f)
            columns = rows.fieldnames
            for row in rows:
                query_id = int(row["id"])
                if query_id in ids or not row["query"].strip():
                    raise ValueError("Duplicate query ID or empty question")
                ids.add(query_id)
                answers = ast.literal_eval(row["answer_ids"])
                if not isinstance(answers, list) or any(type(i) is not int for i in answers):
                    raise ValueError("Unsupported official answer-list format")
                for answer_id in answers:
                    typ = node_map[int(nodes[answer_id])] if 0 <= answer_id < n else "out_of_range"
                    answer_types[typ] += 1
                    if typ != "paper":
                        invalid_answers.append({"query_id": query_id, "answer_id": answer_id, "actual_node_type": typ})
                total_answers += len(answers)
                multiple += len(answers) > 1
                empty += not answers
        ids_by_file[name] = ids
        qa[name] = {"rows": len(ids), "columns": columns, "answer_references": total_answers,
                    "multiple_answer_queries": multiple, "empty_answer_queries": empty,
                    "all_answer_ids_valid_paper_nodes": not invalid_answers,
                    "answer_node_type_counts": dict(answer_types), "non_paper_answer_references": invalid_answers}
        if invalid_answers:
            findings.append({"kind": "official_qa_non_paper_answers", "file": name,
                             "references": invalid_answers, "source_modified": False})
    splits = {}
    for path in sorted((raw / "qa/mag/split").glob("*.index")):
        values = [int(x) for x in path.read_text().splitlines() if x.strip()]
        if len(values) != len(set(values)) or not set(values).issubset(ids_by_file["stark_qa.csv"]):
            raise ValueError("Invalid split query IDs")
        splits[path.stem] = set(values)
    a, b, c = (splits[s] for s in ("train", "val", "test"))
    if a & b or b & c or a & c or a | b | c != ids_by_file["stark_qa.csv"]:
        raise ValueError("Official primary splits are not a disjoint complete partition")
    if not splits["test-0.1"].issubset(c):
        raise ValueError("test-0.1 is not a test subset")
    result = {"schema_version": "1.0", "status": "pass_with_findings" if findings else "pass", "findings": findings,
              "audited_at": datetime.now(timezone.utc).isoformat(),
              "dataset_revision": manifest["dataset_revision"], "manifest_files_verified": len(manifest["files"]),
              "node_count": n, "node_counts": node_counts, "edge_count": e, "relation_counts": dict(relations),
              "endpoint_type_counts": [{"source": node_map[s], "relation": edge_map[r], "target": node_map[t], "count": count}
                                       for (s, r, t), count in sorted(endpoint_types.items())],
              "self_loops": self_loops, "type_maps": type_maps,
              "tensor_layouts": {name: reader.layout for name, reader in readers.items()},
              "tensor_byteorder": "little; upstream legacy headers omit byteorder; counts/bounds verified",
              "attributes": dict(attributes), "metadata_rows": sink.count, "metadata_ids_complete": True,
              "date_year_disagreements": date_year_disagreements,
              "qa": qa, "split_counts": {k: len(v) for k, v in splits.items()},
              "splits_disjoint_and_complete": True, "test_01_is_subset": True,
              "human_split": "Separate official human-generated CSV; no separate index file",
              "resources": {"elapsed_seconds": time.perf_counter() - started, "edge_chunk_size": chunk_size,
                            "node_type_array_bytes": nodes.nbytes, "metadata_seen_mask_bytes": seen.nbytes,
                            "referenced_memo_entries": len(needed), "full_graph_loaded": False,
                            **process_memory()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "node_counts", "relation_counts", "split_counts", "resources")}, indent=2), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--output", type=Path, default=ROOT / "documentation/phase2/audit_stark_mag.json")
    parser.add_argument("--chunk-size", type=int, default=100_000)
    args = parser.parse_args()
    if not 1 <= args.chunk_size <= 1_000_000:
        parser.error("chunk-size must be between 1 and 1000000")
    audit(args.raw_dir, args.output, args.chunk_size)
