"""The only research module that reads environment variables or dotenv files."""
import os
from pathlib import Path, PureWindowsPath
from typing import Annotated, Literal, Mapping

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
import yaml

from .serialization import content_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class ModelConfig(ConfigSection):
    embedding: Annotated[str, Field(min_length=1)] = "sentence-transformers/all-MiniLM-L6-v2"
    generator: Annotated[str, Field(min_length=1)] = "openai/gpt-oss-120b"
    temperature: float = 0

    @field_validator("temperature")
    @classmethod
    def frozen_temperature(cls, value):
        if value != 0:
            raise ValueError("The approved generation temperature is zero")
        return value


class DatasetConfig(ConfigSection):
    name: str = "MMG-STaRK-MAG"
    version: str = "unbuilt"
    benchmark_version: str = "unbuilt"


class PathConfig(ConfigSection):
    dataset: str = "data/MMG_STARK_MAG"
    experiments: str = "artifacts/experiments"

    @field_validator("dataset", "experiments")
    @classmethod
    def portable_path(cls, value):
        normalized = value.replace("\\", "/")
        if not normalized or normalized.startswith("/") or Path(normalized).is_absolute() or PureWindowsPath(value).drive or ".." in normalized.split("/"):
            raise ValueError("Use a nonempty project-relative path without parent traversal")
        return Path(normalized).as_posix()


class LoggingConfig(ConfigSection):
    level: str = "INFO"

    @field_validator("level")
    @classmethod
    def valid_level(cls, value):
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported log level")
        return value


class RepresentationConfig(ConfigSection):
    version: str = "MMG-STaRK-MAG-v1"
    source_revision: str = "88269e23e90587f99476c5dd74e235a0877e69be"
    source_nodes: int = 1872968
    source_papers: int = 700244
    source_edges: int = 19919698
    node_batch_size: int = Field(default=10000, ge=1)
    edge_batch_size: int = Field(default=100000, ge=1)
    embedding_batch_size: int = Field(default=64, ge=1)
    embedding_shard_size: int = Field(default=4096, ge=1)
    embedding_backend: Literal["onnx-cuda-fp32"] = "onnx-cuda-fp32"
    embedding_dimension: int = 384
    embedding_max_tokens: int = 256
    derived_inverses: bool = True
    duckdb_memory_limit: str = "512MB"
    duckdb_threads: int = Field(default=2, ge=1, le=8)
    leakage_policy_version: str = "phase3-approved-v1"


class ResearchConfig(ConfigSection):
    schema_version: str = "1.0"
    seed: Annotated[int, Field(ge=0, le=2**32-1)] = 42
    models: ModelConfig = Field(default_factory=ModelConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    representations: RepresentationConfig | None = None
    groq_api_key: SecretStr = Field(default=SecretStr(""), exclude=True, repr=False)

    @field_validator("schema_version")
    @classmethod
    def known_version(cls, value):
        if value != "1.0":
            raise ValueError("Unsupported configuration schema version")
        return value

    def public_dict(self) -> dict:
        return self.model_dump(mode="json", exclude_none=True)

    def config_hash(self) -> str:
        return content_hash(self.public_dict())

    def resolve_path(self, name: str, project_root: Path = PROJECT_ROOT) -> Path:
        if name not in PathConfig.model_fields:
            raise ValueError("Unknown configured path")
        root = project_root.resolve()
        path = (root / getattr(self.paths, name)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Configured path resolves outside project root")
        return path


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently dropping experimental controls."""


def _mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise ValueError("YAML keys must be unique strings")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_config(path: Path = PROJECT_ROOT / "configs/base.yaml", *,
                environ: Mapping[str, str] | None = None,
                dotenv_path: Path | None = None) -> ResearchConfig:
    """Precedence: defaults < YAML < RESEARCH__ overrides; key from dotenv < env.

    No implicit dotenv import, environment mutation or directory creation.
    Unknown prefixed variables fail rather than silently changing controls.
    """
    data = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a YAML mapping")
    if "groq_api_key" in data:
        raise ValueError("Credentials belong in environment/dotenv, never YAML")
    env = dict(os.environ if environ is None else environ)
    sections = {"models": ModelConfig, "dataset": DatasetConfig, "paths": PathConfig, "logging": LoggingConfig,
                "representations": RepresentationConfig}
    for name, value in sorted(env.items()):
        if not name.startswith("RESEARCH__"):
            continue
        keys = name.removeprefix("RESEARCH__").lower().split("__")
        if keys == ["seed"]:
            data["seed"] = value
        elif len(keys) == 2 and keys[0] in sections and keys[1] in sections[keys[0]].model_fields:
            if not isinstance(data.get(keys[0], {}), dict):
                raise ValueError(f"{keys[0]} must be a mapping")
            data.setdefault(keys[0], {})[keys[1]] = value
        else:
            raise ValueError(f"Unknown research environment setting: {name}")
    credentials = dotenv_values(dotenv_path) if dotenv_path is not None else {}
    data["groq_api_key"] = env.get("GROQ_API_KEY", credentials.get("GROQ_API_KEY") or "")
    return ResearchConfig.model_validate(data)
