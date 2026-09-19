"""Query processing for document-grounded Q&A (RAG-Architecture.md §8).

    question -> query processing -> embedding -> retrieval

The user's question is normalized (collapsed whitespace) and a deterministic
keyword *concept query* is derived with the same tokenizer the deterministic
embedding provider uses (``content_tokens``), so exact legal terms that matter
for retrieval — termination, notice, salary — keep their weight even when the
question asks about several topics at once (multi-hop questions). The original,
stripped question is always preserved verbatim for answer generation; the
concept query is a retrieval aid only and is never shown to the model or user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.embeddings.provider import content_tokens

_MIN_QUESTION_CHARACTERS = 3
_MAX_QUESTION_CHARACTERS = 2000


@dataclass(frozen=True)
class ProcessedQuery:
    """The normalized question and its retrieval concept query."""

    original: str
    normalized: str
    concept_query: str


class QueryProcessor:
    """Normalize a question and expand it into a retrieval concept query."""

    def process(self, question: str) -> ProcessedQuery:
        original = question.strip()
        if not original:
            raise ValueError("question must not be empty")
        if len(original) > _MAX_QUESTION_CHARACTERS:
            raise ValueError("question is too long")
        normalized = _normalize(original)
        if len(normalized) < _MIN_QUESTION_CHARACTERS:
            raise ValueError("question is too short")
        return ProcessedQuery(
            original=original,
            normalized=normalized,
            concept_query=" ".join(content_tokens(normalized)),
        )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()