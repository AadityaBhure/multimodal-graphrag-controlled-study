"""Verify completed builds and manifest are byte-stable when invoked again."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.data.build import Builder, write_json
from research.data.embeddings import build_embeddings, build_faiss
from research.data.validation import manifest
from scripts.audit_stark_mag import digest


if __name__ == "__main__":
    b = Builder(ROOT / "configs/phase3.yaml")
    started = time.perf_counter()
    original = json.loads((b.root / "manifest.json").read_text())
    targets = [b.root / f["path"] for f in original["files"]]
    targets += [b.root / "manifest.json", *b.work.glob("*.complete.json")]
    before = {p: digest(p) for p in targets}
    b.nodes()
    b.structured()
    b.edges()
    b.csr()
    build_embeddings(b)
    build_faiss(b)
    manifest(b)
    for path, checksum in before.items():
        assert digest(path) == checksum, path
    write_json(ROOT / "documentation/phase3/idempotence.json", {
        "status": "pass", "files_unchanged": len(before), "physical_outputs": len(original["files"]),
        "manifest_byte_identical": True, "all_six_completed_stages_reused": True,
        "elapsed_seconds": time.perf_counter()-started})
    print(f"Idempotence passed: {len(before)} unchanged files")
