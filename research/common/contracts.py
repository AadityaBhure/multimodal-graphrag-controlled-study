"""Versioned contracts only; no retrieval or experimental methods implemented.

Nested collections use tuples. Arbitrary payloads/metadata are canonical JSON
strings so frozen evidence cannot be mutated through a nested dictionary.
"""
from datetime import date, datetime
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .serialization import canonical_json, content_hash

Identifier = Annotated[str, Field(min_length=1, pattern=r"\S")]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
SourceType = Literal["text", "graph", "structured"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal["1.0"] = "1.0"


class CanonicalEntity(Contract):
    canonical_id: Identifier
    stark_node_id: str | int | None
    mag_id: str | int | None
    entity_type: Identifier
    display_name: Identifier | None


class TextDocument(Contract):
    text_id: Identifier
    paper_id: Identifier
    title: Identifier
    abstract: str | None
    content: Identifier
    abstract_missing: bool

    @model_validator(mode="after")
    def validate_text(self):
        missing = not bool(self.abstract and self.abstract.strip())
        if missing != self.abstract_missing:
            raise ValueError("abstract_missing must match the actual abstract")
        expected = self.title + "\n\n" + (self.abstract or "")
        if self.content != expected:
            raise ValueError("Text content must be title plus abstract separated by two newlines")
        return self


class GraphNode(Contract):
    node_id: Identifier
    canonical_id: Identifier
    node_type: Identifier
    label: Identifier | None
    search_text: Identifier | None


class GraphEdge(Contract):
    edge_id: Identifier
    source_id: Identifier
    relation: Identifier
    target_id: Identifier
    derived_inverse: bool = False


class StructuredPaper(Contract):
    paper_id: Identifier
    publication_date: date | None
    publication_year: Annotated[int, Field(ge=1, le=9999)] | None
    venue_id: str | None
    venue_name: str | None
    venue_type: str | None
    citation_count: Annotated[int, Field(ge=0)] | None
    paper_rank: NonNegative | None

    @model_validator(mode="after")
    def consistent_date(self):
        if self.publication_date and self.publication_year is not None and self.publication_date.year != self.publication_year:
            raise ValueError("Publication date and year disagree")
        return self


def json_object(value: str) -> str:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return canonical_json(parsed)


class Provenance(Contract):
    dataset_version: Identifier
    source_id: Identifier
    locator: Identifier


class EvidenceItem(Contract):
    evidence_id: Identifier
    source_type: SourceType
    canonical_id: Identifier
    content: str | None = None
    payload: str | None = None
    score: float
    provenance: Annotated[tuple[Provenance, ...], Field(min_length=1)]
    metadata: str = "{}"

    @field_validator("metadata", "payload")
    @classmethod
    def canonical_objects(cls, value):
        return None if value is None else json_object(value)

    @model_validator(mode="after")
    def has_evidence(self):
        if not (self.content and self.content.strip()) and self.payload is None:
            raise ValueError("Evidence requires content or a JSON payload")
        return self


class Timings(Contract):
    text_ms: NonNegative = 0
    graph_ms: NonNegative = 0
    structured_ms: NonNegative = 0
    retrieval_ms: NonNegative = 0
    generation_ms: NonNegative = 0
    total_ms: NonNegative = 0


class Calls(Contract):
    text: Annotated[int, Field(ge=0)] = 0
    graph: Annotated[int, Field(ge=0)] = 0
    structured: Annotated[int, Field(ge=0)] = 0
    llm: Annotated[int, Field(ge=0)] = 0


class RetrievalBundle(Contract):
    query_id: Identifier
    text_evidence: tuple[EvidenceItem, ...] = ()
    graph_evidence: tuple[EvidenceItem, ...] = ()
    structured_evidence: tuple[EvidenceItem, ...] = ()
    timings: Timings = Field(default_factory=Timings)
    calls: Calls = Field(default_factory=Calls)

    @model_validator(mode="after")
    def consistent_sources(self):
        ids = []
        for source in ("text", "graph", "structured"):
            items = getattr(self, f"{source}_evidence")
            if any(e.source_type != source for e in items):
                raise ValueError("Evidence is in the wrong source partition")
            ids.extend(e.evidence_id for e in items)
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique within a bundle")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.model_dump(mode="json")).encode("utf-8")

    def bundle_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class ContextPackage(Contract):
    query_id: Identifier
    serialized_context: str
    included_evidence_ids: tuple[Identifier, ...]
    token_count: Annotated[int, Field(ge=0)] | None
    token_counter: str | None = None
    character_count: Annotated[int, Field(ge=0)]
    byte_count: Annotated[int, Field(ge=0)]
    method_id: Identifier

    @model_validator(mode="after")
    def check_sizes(self):
        if self.character_count != len(self.serialized_context) or self.byte_count != len(self.serialized_context.encode("utf-8")):
            raise ValueError("Context sizes must reflect the actual serialized context")
        if self.token_count is not None and not self.token_counter:
            raise ValueError("Token counts require an identified counter/tokenizer")
        if len(set(self.included_evidence_ids)) != len(self.included_evidence_ids):
            raise ValueError("Duplicate included evidence ID")
        return self


class Metric(Contract):
    name: Identifier
    value: float | None
    unit: str | None = None


class MethodError(Contract):
    stage: Identifier
    code: Identifier
    message: Identifier
    retryable: bool = False


class MethodResult(Contract):
    method_id: Identifier
    query_id: Identifier
    answer: str | None
    evidence_ids: tuple[Identifier, ...]
    metrics: tuple[Metric, ...] = ()
    timings: Timings = Field(default_factory=Timings)
    errors: tuple[MethodError, ...] = ()


class ExperimentRecord(Contract):
    experiment_id: Identifier
    timestamp: datetime
    config_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    git_commit: Identifier
    dataset_version: Identifier
    benchmark_version: Identifier
    query_id: Identifier
    method_id: Identifier
    llm_model: Identifier
    embedding_model: Identifier
    params: str
    seed: Annotated[int, Field(ge=0, le=2**32-1)]
    evidence: tuple[EvidenceItem, ...]
    answer: str | None
    gold_answer_ids: tuple[Identifier, ...] = ()
    metrics: tuple[Metric, ...] = ()
    latency: Timings = Field(default_factory=Timings)
    calls: Calls = Field(default_factory=Calls)
    context_size: Annotated[int, Field(ge=0)] | None = None
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    cost: NonNegative | None = None
    cost_currency: str | None = None
    errors: tuple[MethodError, ...] = ()

    _params = field_validator("params")(json_object)

    @model_validator(mode="after")
    def check_observation(self):
        if self.timestamp.utcoffset() is None:
            raise ValueError("Experiment timestamp must include a timezone")
        if self.cost is not None and not self.cost_currency:
            raise ValueError("Cost requires a currency")
        return self
