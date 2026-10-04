"""Synthetic-only research tests; no network, models, or benchmark execution."""
import ast
from datetime import datetime, timezone
import importlib
import io
import json
from pathlib import Path
import pkgutil
import random

import numpy as np
from pydantic import ValidationError
import pytest

import research
from research.common.config import load_config, ResearchConfig
from research.common.contracts import (
    CanonicalEntity, TextDocument, GraphNode, GraphEdge, StructuredPaper,
    Provenance, EvidenceItem, RetrievalBundle, ContextPackage, MethodResult,
    ExperimentRecord, Metric,
)
from research.common.logging import ExperimentLogger
from research.common.reproducibility import seed_everything
from research.experiments.contracts import ExperimentSpec, experiment_manifest, prepare_experiment

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def corpus():
    return json.loads((ROOT / "tests/fixtures/research/corpus.json").read_text(encoding="utf-8"))


def evidence(source="text", evidence_id="e:1"):
    return EvidenceItem(evidence_id=evidence_id, source_type=source, canonical_id="paper:fixture:1",
                        content="Synthetic evidence", score=0.5,
                        provenance=(Provenance(dataset_version="synthetic-v1", source_id="text:fixture:1", locator="fixture"),))


def test_corpus_contract_roundtrips_and_joins(corpus):
    assert corpus["synthetic"] is True
    mapping = {"entities": CanonicalEntity, "text": TextDocument, "nodes": GraphNode,
               "edges": GraphEdge, "structured": StructuredPaper}
    for key, cls in mapping.items():
        for row in corpus[key]:
            obj = cls.model_validate(row)
            assert cls.model_validate_json(obj.model_dump_json()) == obj
    ids = {e["canonical_id"] for e in corpus["entities"]}
    node_ids = {e["node_id"] for e in corpus["nodes"]}
    assert all(e["canonical_id"] in ids for e in corpus["nodes"])
    assert all(e["source_id"] in node_ids and e["target_id"] in node_ids for e in corpus["edges"])
    assert {e["paper_id"] for e in corpus["text"]} == {e["paper_id"] for e in corpus["structured"]}
    # Known synthetic cross-view join, computed from explicit records.
    authored = {e["target_id"] for e in corpus["edges"] if e["relation"] == "WRITES"}
    recent = {e["paper_id"] for e in corpus["structured"] if e["publication_year"] >= 2022}
    assert authored & recent == {"paper:fixture:2"}


def test_evidence_and_remaining_contract_roundtrips():
    e = evidence()
    bundle = RetrievalBundle(query_id="q:fixture", text_evidence=(e,))
    context = ContextPackage(query_id=bundle.query_id, serialized_context="é", included_evidence_ids=(e.evidence_id,),
                             token_count=None, character_count=1, byte_count=2, method_id="fixture")
    result = MethodResult(method_id="fixture", query_id=bundle.query_id, answer="Synthetic", evidence_ids=(e.evidence_id,))
    record = ExperimentRecord(experiment_id="fixture", timestamp=datetime.now(timezone.utc),
        config_hash=ResearchConfig().config_hash(), git_commit="fixture-only", dataset_version="synthetic-v1",
        benchmark_version="fixture-only", query_id=bundle.query_id, method_id="fixture",
        llm_model="not-called", embedding_model="not-called", params='{"b":2,"a":1}', seed=42,
        evidence=(e,), answer="Synthetic", cost=None)
    for obj in (e, bundle, context, result, record):
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj
    assert record.params == '{"a":1,"b":2}'
    assert record.cost is None


def test_bundle_is_deeply_immutable_and_byte_stable():
    e = EvidenceItem(**{**evidence().model_dump(), "payload": '{"b":2,"a":{"x":1}}'})
    b = RetrievalBundle(query_id="q", text_evidence=[e])
    before = b.canonical_bytes()
    decoded_payload = json.loads(e.payload)
    decoded_payload["a"]["x"] = 3
    assert b.canonical_bytes() == before
    with pytest.raises(ValidationError):
        b.text_evidence[0].score = 3
    with pytest.raises(ValidationError):
        b.calls.text = 2
    with pytest.raises(TypeError):
        b.text_evidence[0] = evidence()
    restored = RetrievalBundle.model_validate_json(before)
    assert restored.canonical_bytes() == before
    assert restored.bundle_hash() == b.bundle_hash()


@pytest.mark.parametrize("mutation", [
    {"graph_evidence": (evidence(),)},
    {"text_evidence": (evidence(), evidence())},
    {"text_evidence": (evidence(),), "structured_evidence": (evidence("structured"),)},
])
def test_invalid_bundles_rejected(mutation):
    with pytest.raises(ValidationError):
        RetrievalBundle(query_id="q", **mutation)


def test_invalid_contract_fields_rejected(corpus):
    with pytest.raises(ValidationError):
        TextDocument(**{**corpus["text"][0], "publication_year": 2021})
    with pytest.raises(ValidationError):
        TextDocument(**{**corpus["text"][0], "abstract_missing": True})
    with pytest.raises(ValidationError):
        StructuredPaper(**{**corpus["structured"][0], "publication_date": "2020-01-01"})
    with pytest.raises(ValidationError):
        EvidenceItem(**{**evidence().model_dump(), "score": float("nan")})
    with pytest.raises(ValidationError):
        EvidenceItem(**{**evidence().model_dump(), "payload": "[]"})
    with pytest.raises(ValidationError):
        ContextPackage(query_id="q", serialized_context="é", included_evidence_ids=(), token_count=1,
                       character_count=1, byte_count=1, method_id="fixture")
    with pytest.raises(ValidationError):
        Metric(name="invalid", value=float("inf"))


def test_config_precedence_hash_and_no_secret_leak(tmp_path):
    path = tmp_path / "base.yaml"
    path.write_text("seed: 1\nmodels:\n  generator: model-a\n", encoding="utf-8")
    dotenv = tmp_path / ".env"
    dotenv.write_text("GROQ_API_KEY=dotenv-value\n", encoding="utf-8")
    a = load_config(path, environ={"RESEARCH__SEED": "2", "GROQ_API_KEY": "private-value"}, dotenv_path=dotenv)
    b = load_config(path, environ={"RESEARCH__SEED": "2", "GROQ_API_KEY": "other-value"})
    assert a.seed == 2 and a.models.generator == "model-a"
    assert a.groq_api_key.get_secret_value() == "private-value"
    assert a.config_hash() == b.config_hash()
    assert "private-value" not in a.model_dump_json() + repr(a)
    assert "groq_api_key" not in a.public_dict()
    assert load_config(path, environ={}).config_hash() != a.config_hash()
    path.write_text("models: {generator: model-a}\nseed: 2\n", encoding="utf-8")
    assert load_config(path, environ={}).config_hash() == a.config_hash()
    assert load_config(path, environ={}, dotenv_path=dotenv).groq_api_key.get_secret_value() == "dotenv-value"


@pytest.mark.parametrize("text", ["seed: 1\nseed: 2", "unknown: 1", "[]", "seed: -1", "groq_api_key: forbidden",
                                     "schema_version: '2.0'", "models: {temperature: 0.5}", "seed: !!python/object:bad {}"])
def test_invalid_yaml_rejected(tmp_path, text):
    import yaml
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises((ValueError, yaml.YAMLError)):
        load_config(path, environ={})


def test_unknown_environment_and_path_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_config(environ={"RESEARCH__MODEL__GENERATOR": "typo"})
    for value in ("../escape", "C:\\escape", "/absolute", "\\\\host\\share"):
        with pytest.raises(ValidationError):
            ResearchConfig(paths={"experiments": value})
    assert ResearchConfig().resolve_path("experiments", tmp_path) == tmp_path / "artifacts/experiments"
    assert not (tmp_path / "artifacts").exists()


def test_seed_repeats_and_invalid_seed_fails():
    def draw():
        return random.random(), np.random.rand(3).tolist()
    seed_everything(42)
    a = draw()
    seed_everything(42)
    assert draw() == a
    seed_everything(43)
    assert draw() != a
    for seed in (-1, 2**32, True):
        with pytest.raises(ValueError):
            seed_everything(seed)


def test_experiment_identity_and_collision_safety(tmp_path):
    config = ResearchConfig()
    spec = ExperimentSpec(method_id="fixture", split="fixture", git_commit="fixture-only")
    a = experiment_manifest(config, spec)
    assert a == experiment_manifest(config, spec)
    assert a != experiment_manifest(config, spec.model_copy(update={"trial": 1}))
    path = prepare_experiment(config, spec, project_root=tmp_path)
    assert path.parent == tmp_path / "artifacts/experiments"
    assert prepare_experiment(config, spec, project_root=tmp_path) == path
    (path / "manifest.json").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        prepare_experiment(config, spec, project_root=tmp_path)
    assert (path / "manifest.json").read_text() == "tampered"


def test_logs_jsonl_console_redaction_and_handler_cleanup(tmp_path):
    path = tmp_path / "events.jsonl"
    stream = io.StringIO()
    for _ in range(2):
        with ExperimentLogger(path, "fixture", stream=stream, secrets=("private-value",)) as logger:
            logger.emit("event", message="private-value\nsecond line", nested={"api_key": "hidden", "items": ["private-value"]}, input_tokens=4)
        assert logger.logger.handlers == []
        with pytest.raises(RuntimeError):
            logger.emit("closed")
    raw = path.read_text(encoding="utf-8")
    assert raw == stream.getvalue()
    assert "private-value" not in raw and "hidden" not in raw
    rows = [json.loads(line) for line in raw.splitlines()]
    assert len(rows) == 2
    assert rows[0]["fields"]["input_tokens"] == 4
    assert rows[0]["fields"]["nested"]["items"] == ["[REDACTED]"]


def test_scaffold_imports_and_environment_boundary():
    for module in pkgutil.walk_packages(research.__path__, research.__name__ + "."):
        importlib.import_module(module.name)
    for path in (ROOT / "research").rglob("*.py"):
        if path.name == "config.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(n.name not in {"os", "dotenv"} and not n.name.startswith("src") for n in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module not in {"os", "dotenv"}
                assert not (node.module or "").startswith("src")
