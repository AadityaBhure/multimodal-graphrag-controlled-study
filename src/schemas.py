"""Validated data contracts and metadata loading."""
import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from src.config import DATA_DIR, PAPERS_DIR

logger = logging.getLogger(__name__)


class PaperMetadata(BaseModel):
    paper_id: str = Field(pattern=r"^P\d{3}$")
    filename: str = Field(min_length=1)
    title: str = Field(min_length=1)
    short_name: str = Field(min_length=1)
    research_area: str = Field(min_length=1)
    techniques: list[str] = Field(min_length=1)
    modalities: list[str] = Field(min_length=1)

    @field_validator("filename")
    @classmethod
    def filename_only(cls, value: str) -> str:
        if "/" in value or "\\" in value or ":" in value or not value.lower().endswith(".pdf"):
            raise ValueError("filename must be a PDF basename")
        return value


class Chunk(BaseModel):
    chunk_id: str
    paper_id: str
    title: str
    chunk_index: int = Field(ge=0)
    text: str
    word_count: int = Field(gt=0)


class RetrievedChunk(BaseModel):
    rank: int = Field(gt=0)
    chunk_id: str
    paper_id: str
    title: str
    score: float
    text: str


class GraphSeed(BaseModel):
    node_id: str
    label: str
    node_type: str
    score: float


class GraphEdgeEvidence(BaseModel):
    source_id: str
    source_label: str
    relation: str
    target_id: str
    target_label: str


class CandidatePaper(BaseModel):
    paper_id: str
    title: str
    graph_score: float
    supporting_seed_ids: list[str]


def load_metadata(path: Path = DATA_DIR / "metadata.json") -> list[PaperMetadata]:
    if not path.is_file():
        raise FileNotFoundError(f"Metadata missing: {path}")
    papers = [PaperMetadata.model_validate(record) for record in json.loads(path.read_text(encoding="utf-8"))["papers"]]
    if len({p.paper_id for p in papers}) != len(papers):
        raise ValueError("Duplicate paper IDs in metadata")
    if len({p.filename for p in papers}) != len(papers):
        raise ValueError("Duplicate filenames in metadata")
    return papers


def check_paper_files(papers: list[PaperMetadata], directory: Path = PAPERS_DIR) -> list[PaperMetadata]:
    missing = [p for p in papers if not (directory / p.filename).is_file()]
    for paper in missing:
        logger.warning("Missing PDF mapping: %s -> %s", paper.paper_id, directory / paper.filename)
    return missing
