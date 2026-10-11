"""Frozen fusion controls and gold-free cached inputs."""
from typing import Literal
from pydantic import Field
from research.common.contracts import Contract, RetrievalBundle
from research.common.serialization import content_hash

METHODS = ('CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03')
SOURCES = ('text', 'graph', 'structured')

class Options(Contract):
    method: Literal['CF-B0', 'CF-B1', 'CF-01', 'CF-02', 'CF-03']
    budget: int = Field(default=24000, ge=300)
    structural_limit: Literal[5] = 5
    total_limit: Literal[10] = 10
    intermediate_tokens: Literal[220] = 220
    selector: Literal['distinct-query-token-coverage-v1'] = 'distinct-query-token-coverage-v1'
    resolver: Literal['exact-id-then-unique-normalized-alias'] = 'exact-id-then-unique-normalized-alias'

class FrozenInput(Contract):
    question: str
    bundle: RetrievalBundle
    overlay_hash: str | None = None
    # Tuples keep the resolution reference immutable and separate from evidence.
    canonical_ids: tuple[str, ...] = ()
    aliases: tuple[tuple[str, tuple[str, ...]], ...] = ()
    provenance: str = '{}'

    def fingerprint(self):
        return content_hash(self.model_dump(mode='json'))

def evidence(item):
    return tuple(e for source in SOURCES for e in getattr(item.bundle, source + '_evidence'))
