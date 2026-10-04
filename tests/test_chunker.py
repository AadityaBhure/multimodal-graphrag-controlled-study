import pytest

from src.chunker import chunk_document
from src.schemas import load_metadata


def test_lengths_overlap_and_ids():
    paper = load_metadata()[0]
    chunks = chunk_document(" ".join(f"word{i}" for i in range(1000)), paper)
    assert [c.word_count for c in chunks] == [450, 450, 250]
    assert [c.chunk_id for c in chunks] == [f"P001_C{i:04d}" for i in range(3)]
    assert all(c.word_count == len(c.text.split()) <= 450 for c in chunks)
    assert all(a.text.split()[-75:] == b.text.split()[:75] for a, b in zip(chunks, chunks[1:]))
    assert all(c.paper_id == "P001" for c in chunks)


@pytest.mark.parametrize("count,expected", [(0, 0), (1, 1), (450, 1), (451, 2), (825, 2)])
def test_boundary_lengths(count, expected):
    assert len(chunk_document("x " * count, load_metadata()[0])) == expected


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_document("word", load_metadata()[0], 75, 75)
