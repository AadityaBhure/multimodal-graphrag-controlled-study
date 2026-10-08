"""Versioned fixed baseline controls and credentials at the configuration boundary."""
from typing import Literal
from pydantic import Field
from research.common.config import ConfigSection, PROJECT_ROOT, load_config


class BaselineOptions(ConfigSection):
    top_k: int = Field(default=5,ge=1,le=100)
    seed_k: int = Field(default=3,ge=1,le=20)
    seed_pool: int = Field(default=64,ge=1,le=256)
    graph_depth: int = Field(default=2,ge=1,le=3)
    max_nodes: int = Field(default=2000,ge=1,le=10000)
    max_edges: int = Field(default=20000,ge=1,le=100000)
    per_node_edges: int = Field(default=128,ge=1,le=1024)
    max_context_chars: int = Field(default=24000,ge=100,le=100000)
    max_completion_tokens: int = Field(default=1024,ge=32,le=4096)
    temperature: Literal[0] = 0
    model: Literal['openai/gpt-oss-120b'] = 'openai/gpt-oss-120b'
    embedding: Literal['sentence-transformers/all-MiniLM-L6-v2'] = 'sentence-transformers/all-MiniLM-L6-v2'
    embedding_revision: Literal['1110a243fdf4706b3f48f1d95db1a4f5529b4d41'] = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
    memory_limit: Literal['512MB'] = '512MB'
    threads: int = Field(default=2,ge=1,le=4)
    cache: bool = True


def groq_key():
    # Never print this value or include it in baseline configuration/identity.
    return load_config(environ=None,dotenv_path=PROJECT_ROOT/'.env').groq_api_key.get_secret_value()
