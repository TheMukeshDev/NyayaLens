"""Deterministic reranking of retrieved chunks (RAG-Architecture.md §11).

Blends the vector similarity with lexical term overlap. Exact legal terms
(clause numbers, names, monetary values) often matter more than pure semantic
distance, so a chunk that contains the query's exact terms can legitimately
outrank a semantically-close neighbour.
"""

from __future__ import annotations

from dataclasses import replace

from app.ai.embeddings.provider import content_tokens
from app.ai.rag.models import RetrievedChunk

_DEFAULT_SIMILARITY_WEIGHT = 0.65
_DEFAULT_LEXICAL_WEIGHT = 0.35


class SimpleReranker:
    """Blend vector similarity and lexical overlap into a single ``score``."""

    def __init__(
        self,
        *,
        similarity_weight: float = _DEFAULT_SIMILARITY_WEIGHT,
        lexical_weight: float = _DEFAULT_LEXICAL_WEIGHT,
    ) -> None:
        self._similarity_weight = similarity_weight
        self._lexical_weight = lexical_weight

    def rerank(self, chunks: list[RetrievedChunk], query: str) -> list[RetrievedChunk]:
        """Return the same chunks reordered by blended relevance."""
        query_tokens = set(content_tokens(query))
        reranked = [
            _rerank(chunk, query_tokens, self._similarity_weight, self._lexical_weight)
            for chunk in chunks
        ]
        return sorted(reranked, key=lambda chunk: chunk.score, reverse=True)


def _rerank(
    chunk: RetrievedChunk,
    query_tokens: set[str],
    similarity_weight: float,
    lexical_weight: float,
) -> RetrievedChunk:
    overlap = _lexical_overlap(query_tokens, content_tokens(chunk.content))
    score = similarity_weight * chunk.similarity + lexical_weight * overlap
    return replace(chunk, score=score)


def _lexical_overlap(query_tokens: set[str], content_tokens_list: list[str]) -> float:
    if not query_tokens:
        return 0.0
    content_set = set(content_tokens_list)
    matched = sum(1 for token in query_tokens if token in content_set)
    return matched / len(query_tokens)