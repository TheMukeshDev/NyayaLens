"""Embedding + vector retrieval tests (hermetic, known synthetic documents).

Covers, end to end against in-memory fakes:

* Processing stores per-chunk embeddings with model metadata.
* Retrieval returns the top chunks for a user's own documents.
* Document-scoped retrieval never leaks chunks from another document.
* Cross-user retrieval never returns another user's chunks — even when that
  user's content is near-identical to the query's.
* Evidence threshold -> INSUFFICIENT_EVIDENCE (no fabricated context).
* Metadata filtering narrows candidate evidence.
* Top-K honours the 8-12 initial target.
* Reranking promotes exact-term matches.
* Vector index reconciliation is callable with the configured dimension.
* An embedding provider failure fails the document honestly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.ai.embeddings.errors import EmbeddingProviderUnavailableError
from app.ai.embeddings.provider import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    Vector,
)
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.rag.context import ContextBuilder
from app.ai.rag.models import RetrievedChunk
from app.ai.rag.reranking import SimpleReranker
from app.ai.rag.retrieval import VectorRetrievalService
from app.document_processing.chunker import Chunker
from app.document_processing.extractor import TextExtractor
from app.document_processing.pipeline import DocumentProcessingPipeline
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.services.documents import DocumentService
from app.services.processing import DocumentProcessingService
from app.services.storage.supabase import SupabaseDocumentStorage
from tests.fakes import BUCKET, FakeSupabase
from tests.sample_docs import docx_bytes

MODEL = "test-model-v1"
DIMENSION = 256

TERMINATION_DOC = (
    "1. TERMINATION",
    "1.1 Notice. The Employee may terminate this Agreement by giving 90 days written notice.",
    "1.2 Severance. The Employer shall pay severance compensation for each completed year.",
    "",
    "2. COMPENSATION",
    "The Employee shall receive an annual salary of 120,000 USD.",
)

CONFIDENTIALITY_DOC = (
    "1. CONFIDENTIALITY",
    "Confidential Information shall be kept strictly private and never disclosed to third parties.",
    "",
    "2. RETURN OF PROPERTY",
    "Upon termination the Employee shall return all company property and records.",
)


@pytest.fixture()
def fake() -> FakeSupabase:
    return FakeSupabase()


def _document_service(fake: FakeSupabase) -> DocumentService:
    return DocumentService(
        repository=DocumentRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        audit=AuditLogRepository(client=fake),
    )


def _embedding_service(fake: FakeSupabase) -> EmbeddingService:
    return EmbeddingService(
        provider=DeterministicEmbeddingProvider(model_name=MODEL, dimension=DIMENSION),
        vectors=VectorRepository(client=fake),
    )


def _pipeline_service(fake: FakeSupabase) -> DocumentProcessingService:
    pipeline = DocumentProcessingPipeline(
        extractor=TextExtractor(ocr_engine=None),
        chunker=Chunker(),
    )
    document_service = _document_service(fake)
    return DocumentProcessingService(
        pipeline=pipeline,
        document_service=document_service,
        processing=ProcessingRepository(client=fake),
        storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
        embeddings=_embedding_service(fake),
    )


def _upload(fake: FakeSupabase, user_id, filename: str, content: bytes) -> UUID:
    document = _document_service(fake).upload(
        user_id=user_id, filename=filename, content=content
    )
    _pipeline_service(fake).process(row=_row_by_id(fake, document.id))
    return UUID(str(document.id))


def _row_by_id(fake: FakeSupabase, document_id) -> dict:
    return next(row for row in fake.rows_of("documents") if row["id"] == str(document_id))


def _retrieval(
    fake: FakeSupabase, *, top_k: int | None = None, min_similarity: float = 0.2
) -> VectorRetrievalService:
    return VectorRetrievalService(
        embeddings=_embedding_service(fake),
        vectors=VectorRepository(client=fake),
        context_builder=ContextBuilder(),
        top_k=top_k or 10,
        min_similarity=min_similarity,
        reranker=SimpleReranker(),
    )


def _chunks(fake: FakeSupabase) -> list[dict]:
    return fake.rows_of("document_chunks")


class TestEmbeddingIndexing:
    def test_processing_stores_embeddings_with_metadata(self, fake):
        user_id = uuid4()
        document_id = _upload(fake, user_id, "agreement.docx", docx_bytes(*TERMINATION_DOC))

        chunks = _chunks(fake)
        assert chunks
        for chunk in chunks:
            assert chunk["document_id"] == str(document_id)
            assert chunk["user_id"] == str(user_id)
            assert isinstance(chunk.get("embedding"), list)
            assert len(chunk["embedding"]) == DIMENSION
            assert chunk["embedding_model"] == MODEL
            assert chunk["embedding_dimension"] == DIMENSION

    def test_embedding_provider_failure_fails_document_honestly(self, fake):
        class UnavailableProvider(EmbeddingProvider):
            @property
            def model_name(self) -> str:
                return "boom-model"

            @property
            def dimension(self) -> int:
                return 8

            def embed(self, texts) -> list[Vector]:
                raise EmbeddingProviderUnavailableError("no provider configured")

        pipeline = DocumentProcessingPipeline(
            extractor=TextExtractor(ocr_engine=None),
            chunker=Chunker(),
        )
        service = DocumentProcessingService(
            pipeline=pipeline,
            document_service=_document_service(fake),
            processing=ProcessingRepository(client=fake),
            storage=SupabaseDocumentStorage(client=fake, bucket=BUCKET),
            embeddings=EmbeddingService(
                provider=UnavailableProvider(),
                vectors=VectorRepository(client=fake),
            ),
        )
        _document_service(fake).upload(
            user_id=uuid4(), filename="a.docx", content=docx_bytes(*TERMINATION_DOC)
        )
        result = service.process(row=fake.rows_of("documents")[0])

        assert result.status == "FAILED"
        assert "search index" in (result.processing_error or "")

    def test_vector_index_reconciliation(self, fake):
        VectorRepository(client=fake).ensure_embedding_index(dimension=DIMENSION)
        assert fake.embedding_index == {"dimension": DIMENSION}


class TestSemanticRetrieval:
    def test_retrieves_relevant_chunk_from_own_document(self, fake):
        user_id = uuid4()
        document_id = _upload(fake, user_id, "employment.docx", docx_bytes(*TERMINATION_DOC))

        result = _retrieval(fake).retrieve(
            user_id=user_id, query="termination notice period for the employee"
        )

        assert result.evidence_state == "DOCUMENT_GROUNDED"
        assert result.sources
        assert all(source.document_id == document_id for source in result.sources)
        assert "90 days" in result.sources[0].content
        assert result.context is not None
        assert "[Source 1]" in result.context.text
        assert "Section: 1 TERMINATION" in result.context.text

    def test_metadata_filtering_restricts_evidence(self, fake):
        user_id = uuid4()
        _upload(fake, user_id, "employment.docx", docx_bytes(*TERMINATION_DOC))

        result = _retrieval(fake).retrieve(
            user_id=user_id,
            query="annual salary 120000 USD payment amount",
            metadata_filter={"section": "1 TERMINATION"},
        )

        # The only match is the COMPENSATION chunk; the section filter must
        # exclude it, so the evidence is insufficient (never fabricated).
        assert result.evidence_state == "INSUFFICIENT_EVIDENCE"
        assert result.sources == []


class TestDocumentScopedRetrieval:
    def test_document_filter_never_mixes_documents(self, fake):
        user_id = uuid4()
        termination = _upload(fake, user_id, "a.docx", docx_bytes(*TERMINATION_DOC))
        confidentiality = _upload(fake, user_id, "b.docx", docx_bytes(*CONFIDENTIALITY_DOC))

        scoped = _retrieval(fake).retrieve(
            user_id=user_id,
            query="confidential information must not be disclosed",
            document_id=confidentiality,
        )
        assert scoped.evidence_state == "DOCUMENT_GROUNDED"
        assert scoped.sources
        assert all(source.document_id == confidentiality for source in scoped.sources)

        # The same query scoped to the OTHER document yields nothing.
        excluded = _retrieval(fake).retrieve(
            user_id=user_id,
            query="confidential information must not be disclosed",
            document_id=termination,
        )
        assert excluded.evidence_state == "INSUFFICIENT_EVIDENCE"
        assert excluded.sources == []


class TestCrossUserIsolation:
    def test_never_retrieves_another_users_chunks(self, fake):
        user_a = uuid4()
        user_b = uuid4()
        doc_a = _upload(fake, user_a, "a.docx", docx_bytes(*TERMINATION_DOC))
        # User B owns near-identical content: the strongest leak scenario.
        _upload(fake, user_b, "b.docx", docx_bytes(*TERMINATION_DOC))

        result = _retrieval(fake).retrieve(
            user_id=user_a, query="termination 90 days written notice"
        )

        assert result.sources
        assert all(source.user_id == user_a for source in result.sources)
        assert all(source.document_id == doc_a for source in result.sources)


class TestEvidenceThreshold:
    def test_unrelated_query_is_insufficient(self, fake):
        user_id = uuid4()
        _upload(fake, user_id, "employment.docx", docx_bytes(*TERMINATION_DOC))

        result = _retrieval(fake).retrieve(
            user_id=user_id, query="quantum physics entanglement theory"
        )

        assert result.evidence_state == "INSUFFICIENT_EVIDENCE"
        assert result.sources == []
        assert result.context is not None
        assert result.context.text == ""


class TestTopK:
    LONG_DOC = tuple(
        [
            "1. GENERAL",
            *(f"{i}. Both parties undertake mutual duties of cooperation under this agreement."
              for i in range(1, 15)),
        ]
    )

    def test_top_k_honours_initial_8_12_target(self, fake):
        user_id = uuid4()
        _upload(fake, user_id, "long.docx", docx_bytes(*self.LONG_DOC))

        for top_k in (8, 10, 12):
            result = _retrieval(fake, min_similarity=0.05).retrieve(
                user_id=user_id,
                query="parties mutual cooperation duties agreement",
                top_k=top_k,
            )
            assert 1 <= len(result.sources) <= top_k
            assert result.evidence_state == "DOCUMENT_GROUNDED"

        # Default top_k (10) also stays inside the 8-12 band.
        default = _retrieval(fake, min_similarity=0.05).retrieve(
            user_id=user_id, query="parties mutual cooperation duties agreement"
        )
        assert 8 <= len(default.sources) <= 12


class TestReranking:
    def test_exact_term_match_can_outrank_higher_similarity(self):
        before = [
            RetrievedChunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                section_id=None,
                clause_id=None,
                chunk_index=1,
                content="Confidential information and trade secrets.",
                page_start=1,
                page_end=1,
                token_count=7,
                metadata={"section": "3 CONFIDENTIALITY"},
                similarity=0.9,
                score=0.9,
                embedding_model=MODEL,
                embedding_dimension=DIMENSION,
            ),
            RetrievedChunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                section_id=None,
                clause_id=None,
                chunk_index=2,
                content="The notice period for termination is ninety days.",
                page_start=2,
                page_end=2,
                token_count=10,
                metadata={"section": "1 TERMINATION"},
                similarity=0.5,
                score=0.5,
                embedding_model=MODEL,
                embedding_dimension=DIMENSION,
            ),
        ]

        reranked = SimpleReranker().rerank(before, "notice period ninety days termination")

        assert len(reranked) == 2
        assert reranked[0].content.startswith("The notice period")
        assert reranked[0].score > reranked[1].score