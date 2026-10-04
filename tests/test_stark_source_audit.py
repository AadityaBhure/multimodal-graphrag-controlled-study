"""Small regression fixtures for safely reading official archive formats."""
import io
import pickle
from pathlib import Path

import numpy as np
import pytest
import torch

from scripts.audit_stark_mag import (
    scan_pickle, StreamingMetadata, PrimitiveUnpickler, TensorHeader, TensorReader, absent,
)


def test_streaming_metadata_preserves_shared_memo_and_batches(tmp_path):
    shared = "shared key across records"
    expected = {i: {"id": i, "type": shared, "value": str(i), "missing": None} for i in range(2501)}
    path = tmp_path / "fixture.pkl"
    path.write_bytes(pickle.dumps(expected, protocol=4))
    needed, ops = scan_pickle(path)
    seen = []
    def callback(key, row):
        assert row == expected[key]
        seen.append(key)
    with path.open("rb") as f:
        reader = StreamingMetadata(f, needed, callback)
        sink = reader.load()
    assert sink.count == len(expected) and seen == list(expected)
    assert len(reader.memo.values) < reader.memo.next_id
    assert "SETITEMS" in ops


def test_executable_pickle_is_rejected(tmp_path):
    path = tmp_path / "unsafe.pkl"
    path.write_bytes(pickle.dumps(Path("never-open-this"), protocol=4))
    with pytest.raises(ValueError, match="opcode"):
        scan_pickle(path)
    with pytest.raises(ValueError, match="globals"):
        PrimitiveUnpickler(io.BytesIO(path.read_bytes())).load()
    with pytest.raises(ValueError, match="global"):
        TensorHeader(io.BytesIO(path.read_bytes())).load()


def test_tensor_reader_honors_shared_storage_offset_and_strides(tmp_path):
    tensor = torch.arange(30, dtype=torch.int64).reshape(3, 10)
    edge_path, type_path = tmp_path / "edges.pt", tmp_path / "types.pt"
    torch.save(tensor[:2], edge_path)
    torch.save(tensor[2], type_path)
    edge, types = TensorReader(edge_path), TensorReader(type_path)
    assert types.layout["offset"] == 20
    np.testing.assert_array_equal(types.read(2, 4), [22, 23, 24, 25])
    np.testing.assert_array_equal(edge.read(3, 3, 1), [13, 14, 15])
    with pytest.raises(ValueError):
        types.read(9, 2)
    with pytest.raises(ValueError):
        edge.read(0, 2)


@pytest.mark.parametrize("value", [None, -1, "-1", "", float("nan")])
def test_upstream_missing_sentinels(value):
    assert absent(value)


@pytest.mark.parametrize("value", [0, "0", "2024-01-01", "Example venue"])
def test_real_values_are_not_missing(value):
    assert not absent(value)
