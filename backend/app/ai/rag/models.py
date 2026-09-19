"""Retrieval result types (retrieval only — answers are out of scope here).

These types are the output of the retrieval half of RAG
(docs/04_AI/RAG-Architecture.md §9-§13):

    retrieval -> metadata filtering -> reranking -> evidence threshold
    -> context builder

No answer generation, prompt assembly or LLM call happens here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

EvidenceState = Literal["DOCUMENT_GROUNDED", "INSUFFICIENT_EVIDENCE"]


@dataclass(frozen=True)
class RetrievedChunk:
    """One chunk returned by similarity search, with its source metadata."""

    chunk_id: UUID
    document_id: UUID
    user_id: UUID
    section_id: UUID | None
    clause_id: UUID | None
    chunk_index: int
    content: str
    page_start: int | None
    page_end: int | None
    token_count: int | None
    metadata: dict[str, object]
    similarity: float
    score: float
    embedding_model: str | None
    embedding_dimension: int | None


@dataclass(frozen=True)
class SourceBlock:
    """A single evidence block ready for prompt/context assembly."""

    order: int
    chunk_id: UUID
    section: str | None
    clause: str | None
    page_start: int | None
    page_end: int | None
    content: str


@dataclass(frozen=True)
class BuiltContext:
    """The assembled retrieval context (structured + flattened text)."""

    text: str
    blocks: list[SourceBlock] = field(default_factory=list)
    estimated_tokens: int = 0


@dataclass(frozen=True)
class RetrievalResult:
    """The complete outcome of one retrieval request."""

    query: str
    document_id: UUID | None
    evidence_state: EvidenceState
    sources: list[RetrievedChunk] = field(default_factory=list)
    context: BuiltContext | None = None