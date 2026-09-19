"""Embedding provider abstraction and implementations.

The pipeline is model-agnostic (docs/04_AI/AI-Architecture.md §16): documents
and queries are embedded through an :class:`EmbeddingProvider`, so swapping the
model provider never touches retrieval or persistence code.

Providers:

* :class:`DeterministicEmbeddingProvider` — hashed bag-of-words vectors with
  L2 normalization. Default for development/tests and the hermetic test suite
  (no network, no keys); terms that matter produce reproducible, meaningful
  cosine similarity.
* :class:`OpenAICompatibleEmbeddingProvider` — POST ``/embeddings`` on an
  OpenAI-compatible endpoint over HTTPS (production path, no new SDK).

No dimension is hardcoded here into the database; :attr:`EmbeddingProvider.dimension`
reports the *model's* dimension, which the operator confirms before building
the vector index (``public.ensure_embedding_index``).
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections.abc import Callable, Sequence
from typing import Any

import httpx

from app.ai.embeddings.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingProviderUnavailableError,
)
from app.ai.transport import RequestThrottle, RetryPolicy, is_retryable_status

_DEFAULT_DIMENSION = 512
_REQUEST_TIMEOUT_SECONDS = 30.0

_Monotonic = Callable[[], float]
_Sleeper = Callable[[float], None]

# Tokens that carry no legal-meaning signal for the deterministic provider.
_STOPWORDS = frozenset(
    [
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
        "has", "have", "he", "her", "his", "if", "in", "is", "it", "its", "may",
        "no", "not", "of", "on", "or", "shall", "she", "should", "so", "that",
        "the", "their", "them", "then", "there", "they", "this", "to", "upon",
        "was", "were", "will", "with", "would", "you", "your", "pursuant",
        "subject", "withing",
    ]
)

Vector = list[float]


class EmbeddingProvider:
    """Produces embedding vectors for text under a configured model."""

    @property
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    def embed(self, texts: Sequence[str]) -> list[Vector]:
        """Return one L2-normalized vector per input text (same order)."""
        raise NotImplementedError

    def embed_one(self, text: str) -> Vector:
        vectors = self.embed([text])
        return vectors[0]


def content_tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, dropping stopwords and 1-char noise."""
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOPWORDS and len(token) >= 2
    ]


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Reproducible hashed bag-of-words embeddings (no network required).

    Suitable for development and for hermetic retrieval tests where the exact
    vectors are known and stable across runs/platforms.
    """

    def __init__(
        self,
        *,
        model_name: str = "nyayalens/embeddings-deterministic-v1",
        dimension: int = _DEFAULT_DIMENSION,
        batch_size: int = 64,
    ) -> None:
        if dimension < 1:
            raise ValueError("dimension must be a positive integer")
        self._model_name = model_name
        self._dimension = dimension
        self._batch_size = batch_size

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[Vector]:
        vectors: list[Vector] = []
        for offset in range(0, len(texts), self._batch_size):
            vectors.extend(
                self._embed_vector(text)
                for text in texts[offset : offset + self._batch_size]
            )
        return vectors

    def _embed_vector(self, text: str) -> Vector:
        vector = [0.0] * self._dimension
        for token in content_tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "little") % self._dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embeddings via an OpenAI-compatible ``/embeddings`` endpoint."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        api_key: str = "",
        dimension: int | None = None,
        batch_size: int = 64,
        timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
        retry_policy: RetryPolicy | None = None,
        requests_per_minute: int = 0,
        transport: httpx.BaseTransport | None = None,
        monotonic: _Monotonic = time.monotonic,
        sleeper: _Sleeper = time.sleep,
    ) -> None:
        if dimension is not None and dimension < 1:
            raise ValueError("dimension must be a positive integer")
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._dimension = dimension
        self._batch_size = batch_size
        self._timeout = timeout_seconds
        self._policy = retry_policy or RetryPolicy(
            max_attempts=1,
            base_delay_seconds=1.0,
            max_delay_seconds=1.0,
        )
        self._throttle = RequestThrottle(
            requests_per_minute=requests_per_minute,
            monotonic=monotonic,
            sleeper=sleeper,
        )
        self._transport = transport
        self._monotonic = monotonic
        self._sleeper = sleeper

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            raise EmbeddingProviderUnavailableError(
                "The embedding dimension is unknown until the provider is first called."
            )
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[Vector]:
        vectors: list[Vector] = []
        for offset in range(0, len(texts), self._batch_size):
            batch = list(texts[offset : offset + self._batch_size])
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[Vector]:
        payload: dict[str, Any] = {"model": self._model_name, "input": texts}
        if self._dimension is not None:
            payload["dimensions"] = self._dimension
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        attempt = 0
        while True:
            attempt += 1
            self._throttle.wait()
            try:
                with httpx.Client(
                    timeout=self._timeout, transport=self._transport
                ) as client:
                    response = client.post(
                        f"{self._base_url}/embeddings", json=payload, headers=headers
                    )
            except httpx.HTTPError as exc:
                if attempt < self._policy.max_attempts:
                    self._sleeper(self._policy.delay_for(attempt))
                    continue
                raise EmbeddingProviderUnavailableError(
                    "The embedding provider could not be reached."
                ) from exc

            if is_retryable_status(response.status_code):
                if attempt >= self._policy.max_attempts:
                    raise EmbeddingProviderUnavailableError(
                        "The embedding provider is currently unavailable."
                    )
                self._sleeper(self._policy.delay_for(attempt))
                continue
            if response.status_code >= 400:
                raise EmbeddingProviderUnavailableError(
                    "The embedding provider rejected the request."
                )
            return self._parse_embeddings(response)

    def _parse_embeddings(self, response: httpx.Response) -> list[Vector]:
        try:
            data = response.json()["data"]
            indexed = sorted(data, key=lambda item: item["index"])
            vectors: list[Vector] = [list(item["embedding"]) for item in indexed]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingProviderUnavailableError(
                "The embedding provider returned an unexpected response."
            ) from exc

        if not vectors:
            raise EmbeddingProviderUnavailableError(
                "The embedding provider returned no embeddings."
            )
        if self._dimension is None:
            self._dimension = len(vectors[0])
        elif any(len(vector) != self._dimension for vector in vectors):
            raise EmbeddingDimensionMismatchError(
                "The embedding provider returned vectors of an unexpected dimension."
            )
        return vectors


def build_embedding_provider(
    *,
    provider: str,
    model_name: str,
    dimension: int | None = None,
    batch_size: int = 64,
    api_url: str = "",
    api_key: str = "",
    timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
    max_attempts: int = 3,
    retry_base_delay_seconds: float = 1.0,
    retry_max_delay_seconds: float = 10.0,
    requests_per_minute: int = 0,
) -> EmbeddingProvider:
    """Assemble the configured embedding provider from setting values."""
    if provider == "deterministic":
        return DeterministicEmbeddingProvider(
            model_name=model_name,
            dimension=dimension or _DEFAULT_DIMENSION,
            batch_size=batch_size,
        )
    if provider == "openai-compatible":
        if not api_url:
            raise ValueError("openai-compatible embedding provider requires api_url")
        return OpenAICompatibleEmbeddingProvider(
            model_name=model_name,
            base_url=api_url,
            api_key=api_key,
            dimension=dimension,
            batch_size=batch_size,
            timeout_seconds=timeout_seconds,
            retry_policy=RetryPolicy(
                max_attempts=max_attempts,
                base_delay_seconds=retry_base_delay_seconds,
                max_delay_seconds=retry_max_delay_seconds,
            ),
            requests_per_minute=requests_per_minute,
        )
    raise ValueError(f"unsupported embedding provider: {provider}")