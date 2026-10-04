"""Run from project root: python scripts/build_text_index.py."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.text_index import build_text_index

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        print(build_text_index())
    except Exception as exc:
        logging.error("Build failed: %s", exc)
        sys.exit(1)
