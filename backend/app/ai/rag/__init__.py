"""RAG retrieval layer (retrieval only — no answer generation).

Implements docs/04_AI/RAG-Architecture.md §9-§13 and AI-Architecture.md §16:

    query embedding -> ownership-scoped vector search -> metadata filtering
    -> reranking -> evidence threshold -> context builder

Also provides the SQL-level security boundary: every search filters by the
authenticated user inside the database function, so cross-user retrieval is
impossible even though the server uses a service-role key.
"""

from __future__ import annotations

from app.ai.rag.context import ContextBuilder
from app.ai.rag.models import BuiltContext, RetrievalResult, RetrievedChunk, SourceBlock
from app.ai.rag.reranking import SimpleReranker
from app.ai.rag.retrieval import VectorRetrievalService

__all__ = [
    "BuiltContext",
    "ContextBuilder",
    "RetrievalResult",
    "RetrievedChunk",
    "SimpleReranker",
    "SourceBlock",
    "VectorRetrievalService",
]