"""Benchmark contracts extend the Phase 1 immutable contract, without metrics."""
from typing import Literal
from pydantic import Field, model_validator
from research.common.contracts import Contract, Identifier
from research.common.config import ConfigSection, UniqueKeyLoader
from pathlib import Path
import yaml


class BenchmarkConfig(ConfigSection):
    schema_version: Literal['1.0'] = '1.0'
    benchmark_version: str
    seed: int = 42
    base_items_per_class_split: int = Field(default=2, ge=1)
    max_generated_answers: int = Field(default=2000, ge=1)
    validation_review_fraction: float = Field(default=.2, gt=0, le=1)
    duckdb_memory_limit: str = '512MB'
    duckdb_threads: int = Field(default=2, ge=1, le=4)
    text_claims: dict[str, tuple[str, ...]]


def load_benchmark_config(path):
    return BenchmarkConfig.model_validate(yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueKeyLoader))


class Reasoning(Contract):
    hop_count: int | None = Field(default=None, ge=1)
    multi_hop: bool | None = None
    complexity: Literal['single-hop', 'multi-hop-2', 'multi-hop-3+', 'unverified']
    difficulty: Literal['controlled', 'unverified']


class Stress(Contract):
    noisy: bool = False
    conflict: bool = False
    unanswerable: bool = False


class BenchmarkQuery(Contract):
    query_id: Identifier
    source_query_id: str
    split: Literal['train', 'validation', 'test', 'human_test']
    question: Identifier
    answer_type: Literal['paper_set'] = 'paper_set'
    answerable: bool
    modalities: tuple[Literal['text', 'graph', 'structured'], ...]
    modality_class: Literal['T', 'G', 'S', 'TG', 'TS', 'GS', 'TGS', 'unverified']
    reasoning: Reasoning
    stress: Stress
    gold_answer_ids: tuple[int, ...]
    gold_evidence: dict
    provenance: dict

    @model_validator(mode='after')
    def consistency(self):
        if len(set(self.gold_answer_ids)) != len(self.gold_answer_ids):
            raise ValueError('Duplicate gold IDs')
        if self.answerable != bool(self.gold_answer_ids) or self.stress.unanswerable == self.answerable:
            raise ValueError('Answerability and authoritative gold disagree')
        if len(set(self.modalities)) != len(self.modalities):
            raise ValueError('Duplicate modality')
        mapping = {'text': 'T', 'graph': 'G', 'structured': 'S'}
        cls = ''.join(mapping[m] for m in ('text','graph','structured') if m in self.modalities)
        if self.modality_class != (cls or 'unverified'):
            raise ValueError('Modality taxonomy mismatch')
        if self.reasoning.hop_count is not None:
            n = self.reasoning.hop_count
            if self.reasoning.multi_hop != (n > 1):
                raise ValueError('Hop taxonomy mismatch')
            expected='single-hop' if n==1 else 'multi-hop-2' if n==2 else 'multi-hop-3+'
            if self.reasoning.complexity!=expected:
                raise ValueError('Reasoning complexity mismatch')
        if self.provenance.get('source')=='generated' and (not self.modalities or self.reasoning.hop_count is None):
            raise ValueError('Generated taxonomy must be verified')
        return self
