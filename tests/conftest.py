"""Retrieval tests use the built corpus and cached model, never Groq."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import pytest

from src.embedder import Embedder
from src.text_index import TextIndex


@pytest.fixture(scope="session")
def embedder():
    return Embedder()


@pytest.fixture(scope="session")
def text_index():
    return TextIndex.load()
