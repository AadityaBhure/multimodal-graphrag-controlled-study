"""Acquire exact official processed MAG bytes; no graph construction or views."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import time
from zipfile import ZipFile

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/MMG_STARK_MAG"
RAW = DATA / "raw/stark_mag"
BUILD = DATA / "_build"
REPO = "snap-stanford/stark"
REVISION = "88269e23e90587f99476c5dd74e235a0877e69be"
UPSTREAM_COMMIT = "b246b9490b1dc216892ce78303140014506932c1"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    metadata = json.loads((ROOT / "documentation/phase2/upstream/hf_info.json").read_text())
    if metadata["sha"] != REVISION:
        raise ValueError("Dataset metadata revision differs from the pinned source")
    files = [f for f in metadata["siblings"] if f["rfilename"].startswith(("qa/mag/", "skb/mag/schema/"))
             or f["rfilename"] == "skb/mag/processed.zip"]
    total = sum(f["size"] for f in files)
    free = shutil.disk_usage(ROOT).free
    if free < total * 3 + 4 * 1024**3:
        raise RuntimeError("Insufficient free space for download, cache and extracted source")
    RAW.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "raw_manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous["dataset_revision"] != REVISION:
            raise ValueError("Refusing to mix revisions in an existing raw directory")
        for f in previous["files"]:
            if sha256(RAW / f["path"]) != f["sha256"]:
                raise ValueError(f"Previously staged source changed: {f['path']}")
    else:
        previous = {"files": []}
    prior = {f["path"]: f for f in previous["files"]}
    entries = []
    print(f"Pinned {REPO}@{REVISION}: {len(files)} files, {total:,} download bytes; {free:,} bytes free", flush=True)
    for f in files:
        name = f["rfilename"]
        target = RAW / name
        if not target.exists():
            for attempt in range(3):
                try:
                    cached = hf_hub_download(REPO, name, repo_type="dataset", revision=REVISION,
                                             cache_dir=str(BUILD / "hf-cache"), token=False)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = BUILD / (hashlib.sha256(name.encode()).hexdigest() + ".stage")
            shutil.copyfile(cached, temporary)
            temporary.replace(target)
        digest = sha256(target)
        if target.stat().st_size != f["size"]:
            raise ValueError(f"Incorrect file size: {name}")
        if "lfs" in f:
            if digest != f["lfs"]["sha256"]:
                raise ValueError(f"Official SHA-256 mismatch: {name}")
        else:
            blob = hashlib.sha1(f"blob {f['size']}\0".encode() + target.read_bytes()).hexdigest()
            if blob != f["blobId"]:
                raise ValueError(f"Official Git blob mismatch: {name}")
        entries.append({"path": name, "bytes": f["size"], "sha256": digest,
                        "source_url": f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{name}",
                        "source_blob_id": f["blobId"], "official_lfs_sha256": f.get("lfs", {}).get("sha256"),
                        "acquired_at": prior.get(name, {}).get("acquired_at", now()), "kind": "official_download"})
        print(f"Verified {name}: {f['size']:,} bytes", flush=True)
    archive_path = RAW / "skb/mag/processed.zip"
    archive_hash = sha256(archive_path)
    with ZipFile(archive_path) as archive:
        required = sum(i.file_size for i in archive.infolist())
        if shutil.disk_usage(ROOT).free < required + 1024**3:
            raise RuntimeError("Insufficient disk space for archive extraction")
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative = "extracted/" + info.filename
            target = (RAW / relative).resolve()
            if not target.is_relative_to((RAW / "extracted").resolve()):
                raise ValueError("Archive contains a path outside extraction directory")
            if not target.exists():
                temporary = BUILD / (hashlib.sha256(relative.encode()).hexdigest() + ".extract")
                with archive.open(info) as source, temporary.open("wb") as dest:
                    shutil.copyfileobj(source, dest, length=4 * 1024 * 1024)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary.replace(target)
            # Streaming comparison also verifies archive CRC without reading the whole member into RAM.
            expected = hashlib.sha256()
            with archive.open(info) as source:
                for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
                    expected.update(block)
            digest = sha256(target)
            if target.stat().st_size != info.file_size or digest != expected.hexdigest():
                raise ValueError(f"Extracted member differs from official archive: {relative}")
            entries.append({"path": relative, "bytes": info.file_size, "sha256": digest,
                            "source_archive": "skb/mag/processed.zip", "source_archive_sha256": archive_hash,
                            "archive_member": info.filename, "archive_crc32": f"{info.CRC:08x}",
                            "acquired_at": prior.get(relative, {}).get("acquired_at", now()),
                            "kind": "unchanged_official_archive_member"})
            print(f"Verified extracted {info.filename}: {info.file_size:,} bytes", flush=True)
    manifest = {"schema_version": "1.0", "dataset": "STaRK-MAG official processed source",
                "repository": REPO, "dataset_revision": REVISION,
                "upstream_loader_commit": UPSTREAM_COMMIT,
                "staging_script_sha256": sha256(Path(__file__)),
                "audit_parser_version": "phase2-v1",
                "audit_script_sha256": sha256(ROOT / "scripts/audit_stark_mag.py"),
                "method": "Official MagSKB hf_hub_download acquisition primitive, pinned revision; no SKB constructor",
                "stark_qa_installed": False, "stark_qa_pypi_version_inspected": "1.1.0",
                "versions": {n: importlib.metadata.version(n) for n in ("huggingface-hub", "torch", "numpy", "requests")},
                "python": sys.version, "created_at": previous.get("created_at", now()), "verified_at": now(),
                "download_bytes": total, "total_staged_bytes": sum(f["bytes"] for f in entries),
                "files": entries}
    payload = json.dumps(manifest, indent=2) + "\n"
    tmp = BUILD / "raw_manifest.json.tmp"
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(manifest_path)
    (ROOT / "documentation/phase2/raw_manifest.json").write_text(payload, encoding="utf-8")
    print(f"Manifest complete: {len(entries)} files; {manifest['total_staged_bytes']:,} staged bytes", flush=True)


if __name__ == "__main__":
    main()
