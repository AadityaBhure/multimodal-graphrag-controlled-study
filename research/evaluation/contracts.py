"""Strict execution contracts; legacy Phase 1 contracts remain compatible."""
from datetime import datetime
from typing import Annotated, Literal, Protocol
from pydantic import Field, model_validator
from research.common.contracts import Contract, Identifier, EvidenceItem, MethodError

Count = Annotated[int, Field(strict=True, ge=0)]
Duration = Annotated[float, Field(ge=0)]
PaperID = Annotated[int, Field(strict=True, ge=0)]


class Observation(Contract):
    retrieval_ms: Duration | None = None
    generation_ms: Duration | None = None
    retrieval_calls: Count | None = None
    tool_calls: Count | None = None
    llm_calls: Count | None = None
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    token_measurement_source: Identifier | None = None

    @model_validator(mode='after')
    def token_source(self):
        if (self.input_tokens is not None or self.output_tokens is not None) and not self.token_measurement_source:
            raise ValueError('Token usage requires measurement provenance')
        return self


class SystemInput(Contract):
    query_id: Identifier
    question: Identifier
    seed: Count
    overlay: str | None = None


class SystemOutput(Contract):
    errors: tuple[MethodError, ...] = ()
    diagnostics: str | None = None
    answer: str | None = None
    answer_ids: tuple[PaperID, ...] | None = None
    ranked_paper_ids: tuple[PaperID, ...] | None = None
    evidence: tuple[EvidenceItem, ...] | None = None
    context: str | None = None
    retained_evidence_ids: tuple[str, ...] | None = None
    context_tokens: Count | None = None
    tokenizer: Identifier | None = None
    baseline_context_characters: Annotated[int, Field(gt=0)] | None = None
    baseline_context_source: Identifier | None = None
    observation: Observation = Field(default_factory=Observation)

    @model_validator(mode='after')
    def measurements(self):
        if self.context_tokens is not None and (not self.tokenizer or self.context is None):
            raise ValueError('Context tokens require context and tokenizer identity')
        if self.baseline_context_characters is not None and not self.baseline_context_source:
            raise ValueError('Context reduction requires an identified comparable baseline')
        if self.retained_evidence_ids is not None and not set(self.retained_evidence_ids) <= {e.evidence_id for e in (self.evidence or ())}:
            raise ValueError('Retained evidence was not retrieved')
        by_id = {}
        for e in (self.evidence or ()):
            if e.evidence_id in by_id and by_id[e.evidence_id] != e:
                raise ValueError('Conflicting duplicate evidence ID')
            by_id[e.evidence_id] = e
        return self


class EvaluationSystem(Protocol):
    system_id: str
    version: str
    fingerprint: str
    def execute(self, request: SystemInput) -> SystemOutput: ...


class VerifiedLabels(Contract):
    modality: str
    hop: str
    hop_count: int | None
    status: Literal['programmatically_verified', 'unverified']
    human_review_status: str


class RunRecord(Contract):
    experiment_id: Identifier
    timestamp: datetime
    query_id: Identifier
    split: Literal['train', 'validation', 'test', 'human_test']
    source_type: Literal['official_synthetic', 'generated', 'official_human']
    labels: VerifiedLabels
    stress: tuple[Literal['normal', 'noisy', 'conflict', 'unanswerable'], ...]
    system_id: Identifier
    config_id: Identifier
    config_hash: Identifier
    model_ids: tuple[str, ...]
    embedding_model: str | None
    seed: Count
    query_seed: Count
    retrieval_parameters: dict
    evidence_ids: tuple[str, ...]
    answer: str | None
    answer_ids: tuple[PaperID, ...] | None
    gold_ids: tuple[PaperID, ...]
    output: SystemOutput | None
    metrics: dict[str, float | None]
    total_latency_ms: Duration
    observation: Observation
    errors: tuple[MethodError, ...]
    provenance: dict

    @model_validator(mode='after')
    def aware(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError('Timestamp must be timezone aware')
        if self.errors and self.answer_ids is not None:
            raise ValueError('Failed queries cannot carry successful output')
        return self


class RunEvent(Contract):
    timestamp: datetime
    experiment_id: Identifier
    query_id: str | None = None
    event: Literal['started', 'completed', 'error', 'interrupted', 'recovered_interruption']
    details: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def aware(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError('Event timestamp must be timezone aware')
        return self


class ReviewDecision(Contract):
    query_id: Identifier
    decision: Literal['pending', 'pass', 'reject']
    reviewer: str
    reason: str
    reviewed_at: datetime | None
    corrected_modality_annotation: str | None = None
    corrected_hop_annotation: str | None = None


class ReleaseMetadata(Contract):
    benchmark_manifest_sha256: Identifier
    test_content_freeze_id: Identifier
    status: Literal['pending', 'released']
    leakage_adjudicated: bool
    released_by: Identifier
    decisions: tuple[ReviewDecision, ...]


class AgentFusionAnnotations(Contract):
    """Future evaluator inputs only; no agent/fusion algorithm or inferred gold."""
    required_sources: tuple[Literal['text', 'graph', 'structured'], ...] | None = None
    unnecessary_call_flags: tuple[bool, ...] | None = None
    should_stop: bool | None = None
    required_fusion_evidence_ids: tuple[str, ...] | None = None
    gold_entity_alignments: tuple[tuple[str, str], ...] | None = None
    expected_conflict_action: str | None = None
    annotation_source: str | None = None
