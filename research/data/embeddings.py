"""Float32 MiniLM encoding, durable shards, and exact flat inner-product index."""
import gc
import json
from pathlib import Path
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from research.data.build import write_json
from scripts.audit_stark_mag import digest


class Encoder:
    def __init__(self, builder, parity_texts):
        import torch
        from sentence_transformers import SentenceTransformer
        import onnxruntime as ort
        from huggingface_hub import try_to_load_from_cache
        torch.set_num_threads(4)
        if builder.config.models.embedding != "sentence-transformers/all-MiniLM-L6-v2":
            raise ValueError("Phase 3 requires the approved frozen MiniLM model")
        self.model = SentenceTransformer(builder.config.models.embedding, device="cpu", local_files_only=True,
                                         revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41")
        if self.model.max_seq_length != builder.options.embedding_max_tokens:
            raise ValueError("Frozen model truncation length differs from configuration")
        path = builder.root / "text/faiss/model.onnx"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self.model[0].auto_model.set_attn_implementation("eager")
            class ExportEncoder(torch.nn.Module):
                def __init__(self, model):
                    super().__init__()
                    self.transformer = model[0].auto_model
                def forward(self, input_ids, attention_mask, token_type_ids):
                    tokens = self.transformer(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids).last_hidden_state
                    mask = attention_mask.unsqueeze(-1).to(tokens.dtype)
                    pooled = (tokens * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
                    return torch.nn.functional.normalize(pooled, p=2, dim=1)
            wrapper = ExportEncoder(self.model).eval()
            inputs = self.model.tokenize(["A short research paper", "A second paper about graph retrieval."])
            names = ["input_ids", "attention_mask", "token_type_ids"]
            temp = path.with_suffix(".onnx.tmp")
            with torch.no_grad():
                torch.onnx.export(wrapper, tuple(inputs[name] for name in names), str(temp),
                                  input_names=names, output_names=["embeddings"],
                                  dynamic_axes={**{name: {0: "batch", 1: "sequence"} for name in names}, "embeddings": {0: "batch"}},
                                  opset_version=17, dynamo=False, external_data=False)
            temp.replace(path)
        ort.preload_dlls(directory="")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=[
            ("CUDAExecutionProvider", {"use_tf32": "0", "gpu_mem_limit": str(3 * 1024**3), "arena_extend_strategy": "kSameAsRequested"})])
        if self.session.get_providers()[0] != "CUDAExecutionProvider":
            raise RuntimeError("GPU provider unavailable; no silent backend substitution")
        expected = self.model.encode(parity_texts, batch_size=16, normalize_embeddings=True, show_progress_bar=False)
        actual = self.encode(parity_texts, batch_size=16)
        difference = float(np.max(np.abs(expected - actual)))
        cosine = np.sum(expected * actual, axis=1)
        if not np.allclose(expected, actual, atol=2e-5, rtol=1e-4) or float(cosine.min()) < .99999:
            raise ValueError(f"ONNX/PyTorch parity failed: max diff {difference}")
        weights = try_to_load_from_cache(builder.config.models.embedding, "model.safetensors")
        self.metadata = {"model": builder.config.models.embedding,
                         "model_revision": self.model[0].auto_model.config._commit_hash,
                         "source_weights_sha256": digest(Path(weights)) if isinstance(weights, str) else None,
                         "onnx_sha256": digest(path), "precision": "float32", "max_seq_length": self.model.max_seq_length,
                         "provider": "CUDAExecutionProvider", "tf32": False,
                         "normalization": "attention-mask mean pooling then L2 normalization",
                         "parity_samples": len(parity_texts), "parity_max_abs_error": difference,
                         "parity_min_cosine": float(cosine.min()), "parity_tolerance": {"atol": 2e-5, "rtol": 1e-4}}
        write_json(builder.root / "text/faiss/encoder.json", self.metadata)
        print(f"Encoder parity passed: max absolute error {difference:.3g}", flush=True)

    def encode(self, texts, batch_size=64):
        results = []
        for start in range(0, len(texts), batch_size):
            features = self.model.tokenize(texts[start:start+batch_size])
            feed = {key: value.numpy().astype(np.int64, copy=False) for key, value in features.items()
                    if key in {"input_ids", "attention_mask", "token_type_ids"}}
            value = self.session.run(["embeddings"], feed)[0]
            if not np.isfinite(value).all() or not np.allclose(np.linalg.norm(value, axis=1), 1, atol=1e-5):
                raise ValueError("Invalid normalized embeddings")
            results.append(value)
        return np.concatenate(results).astype(np.float32, copy=False)


def build_embeddings(builder):
    if builder.complete("embeddings"):
        return
    if not builder.complete("nodes"):
        raise ValueError("Text representation must complete first")
    started = time.perf_counter()
    source = builder.root / "text/text_documents.parquet"
    parquet = pq.ParquetFile(source)
    # Deterministic actual papers spanning the file, plus short/Unicode/truncated cases.
    parity = ["graph retrieval", "Café Δ multilingual query", "token " * 600]
    for i in sorted(set([0, parquet.num_row_groups // 2, parquet.num_row_groups-1])):
        parity.extend(parquet.read_row_group(i, columns=["content"]).column(0).to_pylist()[:10])
    encoder = Encoder(builder, parity)
    output = builder.root / "text/faiss/embeddings"
    output.mkdir(parents=True, exist_ok=True)
    markers = builder.work / "embedding_shards"
    markers.mkdir(exist_ok=True)
    paths, total, batch_size = [], 0, builder.options.embedding_batch_size
    text_hash = digest(source)
    for i, batch in enumerate(parquet.iter_batches(batch_size=builder.options.embedding_shard_size, columns=["paper_id", "content"])):
        path, ids_path = output / f"vectors-{i:06d}.npy", output / f"ids-{i:06d}.npy"
        marker = markers / f"{i:06d}.json"
        ids = batch.column(0).to_numpy()
        if marker.exists():
            previous = json.loads(marker.read_text())
            if previous["config_hash"] != builder.hash or previous["text_sha256"] != text_hash or previous["encoder_sha256"] != encoder.metadata["onnx_sha256"]:
                raise ValueError("Embedding checkpoint provenance mismatch")
            if digest(path) != previous["vectors_sha256"] or digest(ids_path) != previous["ids_sha256"]:
                raise ValueError("Embedding checkpoint checksum mismatch")
        else:
            texts = batch.column(1).to_pylist()
            while True:
                try:
                    vectors = encoder.encode(texts, batch_size)
                    break
                except Exception as exc:
                    if batch_size == 1 or not any(word in str(exc).lower() for word in ("out of memory", "allocate", "allocation")):
                        raise
                    batch_size = max(1, batch_size // 2)
                    print(f"Reducing embedding batch size to {batch_size}", flush=True)
            if vectors.shape != (len(ids), builder.options.embedding_dimension):
                raise ValueError("Embedding shape mismatch")
            for target, value in ((path, vectors), (ids_path, ids)):
                temporary = target.with_suffix(".tmp")
                with temporary.open("wb") as file:
                    np.save(file, value, allow_pickle=False)
                temporary.replace(target)
            write_json(marker, {"config_hash": builder.hash, "text_sha256": text_hash,
                               "encoder_sha256": encoder.metadata["onnx_sha256"], "rows": len(ids),
                               "vectors_sha256": digest(path), "ids_sha256": digest(ids_path), "effective_batch_size": batch_size})
        total += len(ids)
        paths.extend([path, ids_path])
        if i % 5 == 0:
            print(f"Embeddings: {total:,}/{builder.options.source_papers:,}; {time.perf_counter()-started:.1f}s elapsed", flush=True)
    if total != builder.options.source_papers:
        raise ValueError("Embedding row count mismatch")
    paths.extend([builder.root / "text/faiss/model.onnx", builder.root / "text/faiss/encoder.json"])
    builder.finish("embeddings", paths, started, rows=total, dimension=builder.options.embedding_dimension,
                   encoder=encoder.metadata)


def populate_flat_index(index, vector_paths, rows, dimension):
    """Reserve the exact flat code store once, avoiding reallocations at this scale.

    IndexFlat stores contiguous float32 bytes; validate against normal add() in tests.
    """
    import faiss
    index.codes.resize(rows * dimension * 4)
    storage = faiss.rev_swig_ptr(index.get_xb(), rows * dimension).reshape(rows, dimension)
    position = 0
    for path in vector_paths:
        vectors = np.load(path, allow_pickle=False)
        if vectors.dtype != np.float32 or vectors.shape[1] != dimension:
            raise ValueError("Invalid embedding shard")
        storage[position:position+len(vectors)] = vectors
        position += len(vectors)
    if position != rows:
        raise ValueError("Embedding count mismatch")
    index.ntotal = rows


def build_faiss(builder):
    import faiss
    if builder.complete("faiss"):
        return
    if not builder.complete("embeddings"):
        raise ValueError("All embedding shards must complete first")
    started = time.perf_counter()
    root = builder.root / "text/faiss"
    vectors = sorted((root / "embeddings").glob("vectors-*.npy"))
    index = faiss.IndexFlatIP(builder.options.embedding_dimension)
    populate_flat_index(index, vectors, builder.options.source_papers, builder.options.embedding_dimension)
    path = root / "index.faiss"
    temp = path.with_suffix(".tmp")
    faiss.write_index(index, str(temp))
    del index
    gc.collect()
    temp.replace(path)
    mapping = root / "row_to_paper_id.npy"
    ids = np.lib.format.open_memmap(mapping.with_suffix(".tmp"), mode="w+", dtype=np.int64, shape=(builder.options.source_papers,))
    cursor = 0
    for shard in sorted((root / "embeddings").glob("ids-*.npy")):
        values = np.load(shard, allow_pickle=False)
        ids[cursor:cursor+len(values)] = values
        cursor += len(values)
    ids.flush()
    del ids
    mapping.with_suffix(".tmp").replace(mapping)
    builder.finish("faiss", [path, mapping], started, rows=cursor, index_type="IndexFlatIP", metric="inner_product")
