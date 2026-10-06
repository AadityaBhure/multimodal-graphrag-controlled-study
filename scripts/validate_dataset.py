"""Audit Phase 3 representations without generating benchmark records."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.data.build import Builder
from research.data.validation import validate

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase3.yaml")
    parser.add_argument("--section", choices=("all", "nodes", "sql", "edges", "csr", "faiss"), default="all")
    args = parser.parse_args()
    print(validate(Builder(args.config), args.section))
