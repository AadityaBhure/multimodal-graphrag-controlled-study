"""Dependency contracts; concrete methods belong to later phases."""
from typing import Protocol

from .contracts import ContextPackage, EvidenceItem, MethodResult, RetrievalBundle


class Retriever(Protocol):
    def retrieve(self, query_id: str, query: str) -> tuple[EvidenceItem, ...]: ...


class ContextManager(Protocol):
    def manage(self, evidence: RetrievalBundle | ContextPackage, query: str) -> ContextPackage: ...


class Fusion(Protocol):
    def fuse(self, bundle: RetrievalBundle, query: str) -> ContextPackage: ...


class AgenticRetriever(Protocol):
    def retrieve(self, query_id: str, query: str) -> RetrievalBundle: ...


class Generator(Protocol):
    def generate(self, query: str, context: ContextPackage) -> str: ...


class ResearchMethod(Protocol):
    def run(self, query_id: str, query: str) -> MethodResult: ...
