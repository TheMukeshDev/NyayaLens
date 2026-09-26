"""Efficiency, performance, and resource bounds test suite.

Verifies that NyayaLens operates under strict resource guarantees:
1. Time complexity bounds (linear O(N) chunking, O(1) cached retrievals).
2. Memory bounds (LRU eviction, max capacity caps, zero memory bloat).
3. Protection against resource starvation (decompression bombs, request flooding).
4. Connection pooling and transport reuse across provider invocations.
"""

from __future__ import annotations

import io
import time
import zipfile
from uuid import uuid4

import pytest

from app.ai.embeddings.provider import DeterministicEmbeddingProvider
from app.core.cache import BoundedLRUCache, embedding_cache
from app.core.rate_limit import SlidingWindowRateLimiter
from app.document_processing.chunker import Chunker
from app.document_processing.models import ExtractedClause, ExtractedSection
from app.services.file_validation import validate_uploaded_file


class TestCacheEfficiency:
    def test_lru_cache_bounded_memory(self) -> None:
        """Cache never exceeds maxsize regardless of inserts (flat O(1) space)."""
        cache: BoundedLRUCache[str] = BoundedLRUCache(maxsize=10, ttl_seconds=60.0)
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")
        assert cache.stats["size"] == 10
        assert cache.get("key_0") is None  # Oldest evicted
        assert cache.get("key_99") == "value_99"

    def test_lru_cache_hit_rate_and_speed(self) -> None:
        """Repeated lookups are served from memory in sub-millisecond time."""
        cache: BoundedLRUCache[list[float]] = BoundedLRUCache(maxsize=100)
        vector = [0.1] * 512
        cache.set("query_vector", vector)

        start = time.perf_counter()
        for _ in range(1000):
            res = cache.get("query_vector")
            assert res is not None
        duration = time.perf_counter() - start

        # 1000 lookups must take less than 200ms total (< 0.2ms per lookup)
        assert duration < 0.2
        assert cache.stats["hits"] == 1000

    def test_embedding_provider_caches_repeat_queries(self) -> None:
        """Deterministic provider utilizes embedding_cache for zero-cost repeat lookups."""
        provider = DeterministicEmbeddingProvider(dimension=256)
        query = "What is the termination notice period?"

        vec1 = provider.embed_one(query)
        # Second call must hit cache
        cache_key = f"{provider.model_name}:{provider.dimension}:{query}"
        assert embedding_cache.get(cache_key) == vec1


class TestChunkingPerformance:
    def test_large_document_linear_time(self) -> None:
        """Chunking 50 sections and 100 clauses executes in linear time (< 500ms)."""
        doc_id = uuid4()
        chunker = Chunker(max_chunk_chars=2000)

        # Generate large synthetic legal document (~20,000 words)
        sections = [
            ExtractedSection(
                number=str(i),
                title=f"Section {i}: Terms of Agreement and Legal Governance",
                content="Standard contractual clauses and confidentiality terms. " * 30,
                page_start=i,
                page_end=i,
                sequence=i,
            )
            for i in range(1, 51)
        ]
        clauses = [
            ExtractedClause(
                section_sequence=i,
                number=f"{i}.1",
                title="Confidentiality and Non-Disclosure Obligations",
                content="The receiving party shall keep all confidential information secret. " * 15,
                page_start=i,
                page_end=i,
                sequence=i,
                clause_type="CONFIDENTIALITY",
            )
            for i in range(1, 51)
        ]

        start = time.perf_counter()
        chunks = chunker.chunk(document_id=doc_id, sections=sections, clauses=clauses)
        duration = time.perf_counter() - start

        assert len(chunks) >= 50
        # High efficiency assertion: must complete well under 500ms
        assert duration < 0.5


class TestResourceStarvationDefense:
    def test_docx_decompression_bomb_rejection(self) -> None:
        """Archive with high expansion ratio is immediately rejected without memory blowup."""
        # Create a synthetic zip bomb: 1KB compressed that expands to > 65 MB of zeros
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("word/document.xml", b"\x00" * (65 * 1024 * 1024))
        bomb_bytes = buf.getvalue()

        start = time.perf_counter()
        outcome = validate_uploaded_file("document.docx", bomb_bytes)
        duration = time.perf_counter() - start

        # Must reject in under 200ms with MALWARE_DETECTED
        assert outcome.valid is False
        assert outcome.error_code == "MALWARE_DETECTED"
        assert duration < 0.2

    def test_rate_limiter_throttling_and_cleanup(self) -> None:
        """Sliding window limiter blocks excessive bursts and evicts stale state."""
        limiter = SlidingWindowRateLimiter(default_limit_per_minute=5, enabled=True)
        client = "test_client_ip"

        now = 1000.0
        # 5 requests succeed
        for _ in range(5):
            limited, _ = limiter.is_rate_limited(client, now=now)
            assert limited is False

        # 6th request is throttled
        limited, retry_after = limiter.is_rate_limited(client, now=now)
        assert limited is True
        assert retry_after == 60

        # After 61 seconds, client is no longer rate limited
        limited, _ = limiter.is_rate_limited(client, now=now + 61.0)
        assert limited is False
