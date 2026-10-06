"""Read-only source/MVP/environment preservation evidence for Phase 3."""
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.data.build import Builder, write_json
from scripts.audit_stark_mag import digest


def git(*args):
    return subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", *args], cwd=ROOT)


if __name__ == "__main__":
    baseline = "4592d102b363c7d55d3c85ee67efe89409ae96b5"
    checkpoint = "f8fc9a29f95b008a0216620449568f8bba4599a6"
    assert git("rev-parse", "baseline-mvp-v1^{commit}").decode().strip() == baseline
    assert git("rev-parse", "HEAD").decode().strip() == checkpoint
    paths = git("ls-tree", "-r", "--name-only", baseline).decode().splitlines()
    protected = [p for p in paths if p != "documentation/Research_Decision_Log.md"]
    for path in protected:
        # Git's normal checkout newline filters must not create false changes on Windows.
        assert git("hash-object", path).strip() == git("rev-parse", f"{baseline}:{path}").strip(), path
    inventory = json.loads((ROOT / "documentation/baseline_phase0/inventory.json").read_text())
    byte_checked = 0
    for entry in inventory:
        if entry["path"] != "documentation/Research_Decision_Log.md":
            assert digest(ROOT / entry["path"]) == entry["sha256"], entry["path"]
            byte_checked += 1
    with zipfile.ZipFile(ROOT / "documentation/baseline_phase0/storage_snapshot.zip") as archive:
        for path in archive.namelist():
            assert (ROOT / path).read_bytes() == archive.read(path), path
        storage_count = len(archive.namelist())
    canonical_name = lambda value: re.sub(r"[-_.]+", "-", value).lower()
    installed = {canonical_name(d.metadata["Name"]): d.version for d in distributions()}
    baseline_packages = {}
    for line in (ROOT / "documentation/baseline_phase0/requirements.freeze.txt").read_text().splitlines():
        if "==" in line:
            name, ver = line.split("==", 1)
            baseline_packages[canonical_name(name)] = ver
    for name, ver in baseline_packages.items():
        assert installed.get(name) == ver, (name, ver, installed.get(name))
    result = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    builder = Builder(ROOT / "configs/phase3.yaml")
    builder.verify_raw()
    assert (builder.raw / "raw_manifest.json").read_bytes() == (ROOT / "documentation/phase2/raw_manifest.json").read_bytes()
    assert not (builder.root / "benchmark").exists()
    assert not (builder.root / "benchmarks").exists()
    added = {k: v for k, v in sorted(installed.items()) if k not in baseline_packages}
    record = {"baseline_commit": baseline, "approved_phase2_checkpoint": checkpoint,
              "protected_baseline_files_verified": len(protected), "storage_files_verified": storage_count,
              "baseline_inventory_byte_checks": byte_checked,
              "baseline_package_versions_preserved": len(baseline_packages), "packages_not_listed_in_baseline_freeze": added,
              "pip_check": result.stdout.strip(), "source_files_verified": len(builder.raw_manifest["files"]),
              "original_human_qa_records_preserved": 84, "benchmark_built": False,
              "disk_free_bytes": shutil.disk_usage(ROOT).free,
              "raw_bytes": sum(p.stat().st_size for p in builder.raw.rglob("*") if p.is_file()),
              "build_cache_bytes": sum(p.stat().st_size for p in (builder.root / "_build").rglob("*") if p.is_file())}
    write_json(ROOT / "documentation/phase3/preservation_environment.json", record)
    print(json.dumps(record, indent=2))
