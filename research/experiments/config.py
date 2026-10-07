"""Explicit named runner configuration, without environment-dependent defaults."""
from pathlib import Path
from typing import Annotated, Literal
import yaml
from pydantic import Field, model_validator
from research.common.config import ConfigSection, UniqueKeyLoader


class Pricing(ConfigSection):
    source: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)


class RunnerConfig(ConfigSection):
    config_id: str = Field(min_length=1)
    system_id: str = Field(min_length=1)
    system_version: str = Field(min_length=1)
    seed: int = Field(default=42, ge=0, lt=2**32, strict=True)
    mode: Literal['development', 'paper_test'] = 'development'
    splits: tuple[Literal['train', 'validation', 'test', 'human_test'], ...] = ('validation',)
    query_ids: tuple[str, ...] = ()
    ks: tuple[Annotated[int, Field(strict=True)], ...] = (1, 5, 10)
    model_ids: tuple[str, ...] = ()
    embedding_model: str | None = None
    retrieval_parameters: dict = Field(default_factory=dict)
    pricing: Pricing | None = None
    fusion_method: str | None = None
    context_method: str | None = None
    agentic_method: str | None = None

    @model_validator(mode='after')
    def controls(self):
        if not self.splits or len(set(self.splits)) != len(self.splits):
            raise ValueError('Specify unique nonempty splits')
        if self.mode == 'development' and set(self.splits) & {'test', 'human_test'}:
            raise ValueError('Development runs are restricted to train/validation')
        if self.mode == 'paper_test' and not set(self.splits) <= {'test', 'human_test'}:
            raise ValueError('Paper test mode accepts only test/human_test')
        if not self.ks or any(k < 1 for k in self.ks) or len(set(self.ks)) != len(self.ks):
            raise ValueError('Specify unique positive K values')
        if len(set(self.query_ids)) != len(self.query_ids):
            raise ValueError('Duplicate query selection')
        if self.pricing and self.model_ids != (self.pricing.model_id,):
            raise ValueError('Pricing requires exactly the identified billed model')
        return self


def load_runner_config(path):
    return RunnerConfig.model_validate(yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueKeyLoader))


def durable_write(path, text):
    """Same-directory atomic replacement, flushed before promotion."""
    import os
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)
