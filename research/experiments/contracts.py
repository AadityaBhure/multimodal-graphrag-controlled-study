"""Create a reproducible, non-overwriting experiment workspace, not a runner."""
from pathlib import Path
from typing import Literal

from pydantic import Field

from research.common.config import PROJECT_ROOT, ResearchConfig
from research.common.contracts import Contract, Identifier
from research.common.serialization import canonical_json, content_hash


class ExperimentSpec(Contract):
    method_id: Identifier
    split: Literal["train", "validation", "test", "human_test", "fixture"]
    git_commit: Identifier
    trial: int = Field(default=0, ge=0)


def experiment_manifest(config: ResearchConfig, spec: ExperimentSpec) -> dict:
    identity = {"schema_version": "1.0", "config": config.public_dict(),
                "config_hash": config.config_hash(), "spec": spec.model_dump(mode="json")}
    return {"experiment_id": "exp-" + content_hash(identity), **identity}


def prepare_experiment(config: ResearchConfig, spec: ExperimentSpec, *, project_root: Path = PROJECT_ROOT) -> Path:
    manifest = experiment_manifest(config, spec)
    base = config.resolve_path("experiments", project_root)
    path = base / manifest["experiment_id"]
    if not path.resolve().is_relative_to(base):
        raise ValueError("Experiment directory resolves outside configured root")
    path.mkdir(parents=True, exist_ok=True)
    target = path / "manifest.json"
    expected = canonical_json(manifest) + "\n"
    try:
        with target.open("x", encoding="utf-8") as file:
            file.write(expected)
    except FileExistsError:
        if target.read_text(encoding="utf-8") != expected:
            raise ValueError("Existing experiment manifest differs; refusing to overwrite")
    return path
