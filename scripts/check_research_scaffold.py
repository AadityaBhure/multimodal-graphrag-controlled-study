"""Offline Phase 1 smoke check; never runs retrieval, generation or evaluation."""
import io
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.common.config import load_config, ResearchConfig
from research.common.logging import ExperimentLogger
from research.common.reproducibility import seed_everything
from research.experiments.contracts import ExperimentSpec, prepare_experiment


def main():
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]

    def run(*args):
        return subprocess.check_output([*git, *args], cwd=ROOT)

    baseline = run("rev-parse", "baseline-mvp-v1^{commit}").decode().strip()
    if not baseline.startswith("4592d10"):
        raise RuntimeError("The approved baseline reference has changed")
    names = run("ls-tree", "-r", "--name-only", "baseline-mvp-v1").decode().splitlines()
    checked = []
    for name in names:
        if name == "documentation/Research_Decision_Log.md":
            continue  # The roadmap explicitly requires appending Phase 1 decisions.
        expected = run("rev-parse", f"baseline-mvp-v1:{name}").strip()
        actual = run("hash-object", "--path", name, name).strip()
        if actual != expected:
            raise RuntimeError(f"Frozen baseline file changed: {name}")
        checked.append(name)
    archive = run("show", "baseline-mvp-v1:documentation/baseline_phase0/storage_snapshot.zip")
    with ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():
            if (ROOT / name).read_bytes() != z.read(name):
                raise RuntimeError(f"Frozen storage changed: {name}")
        storage_count = len(z.namelist())

    config = load_config(environ={})
    # Two fresh processes prove independence from insertion order/process hash state.
    code = "from research.common.config import load_config; print(load_config(environ={}).config_hash())"
    hashes = [subprocess.check_output([sys.executable, "-c", code], cwd=ROOT).decode().strip() for _ in range(2)]
    if hashes != [config.config_hash()] * 2:
        raise RuntimeError("Configuration hashes differ across processes")
    fixture_config = ResearchConfig.model_validate({**config.public_dict(),
        "dataset": {"name": "synthetic-unit-fixture", "version": "synthetic-v1", "benchmark_version": "not-a-benchmark"}})
    spec = ExperimentSpec(method_id="phase1-contract-smoke", split="fixture", git_commit=baseline)
    directory = prepare_experiment(fixture_config, spec)
    with ExperimentLogger(directory / "events.jsonl", directory.name) as logger:
        logger.emit("scaffold_smoke", synthetic=True, model_calls=0,
                    seeding=seed_everything(fixture_config.seed), config_hash=fixture_config.config_hash())
    result = {"status": "pass", "baseline_commit": baseline,
              "frozen_files_verified": len(checked), "storage_files_verified": storage_count,
              "config_hash": config.config_hash(), "fresh_process_hashes": hashes,
              "fixture_directory": directory.relative_to(ROOT).as_posix(),
              "model_calls": 0, "dataset_acquisition": False}
    out = ROOT / "documentation/phase1"
    out.mkdir(parents=True, exist_ok=True)
    (out / "scaffold_smoke.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
