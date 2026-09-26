"""Document-grounded Q&A orchestration.

Implements the full Q&A pipeline (docs/04_AI/AI-Architecture.md §10,
docs/04_AI/RAG-Architecture.md, API-Specification.md §15-§16):

    question -> query processing -> embedding + pgvector retrieval
    (ownership-scoped in SQL) -> evidence selection -> prompt -> LLM
    (schema-validated, never fabricating) -> answer validation
    -> citation validation -> response

Honesty rules enforced here:

* No evidence above the relevance threshold: the answer is INSUFFICIENT-EVIDENCE
  without ever calling the LLM.
* The model abstains, or the LLM is unconfigured/unavailable: the service
  abstains with a controlled reason — it never fills in a guess.
* The answer is document-grounded but no citation survives backend validation
  (existence, document membership, ownership, section/page metadata): the
  service abstains instead of presenting uncitable content.
* Citations are backend-resolved from *retrieved* chunks only; fabricated or
  cross-user/cross-document chunks are dropped, never presented.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.ai.analysis.service import StructuredLLM
from app.ai.embeddings.provider import build_embedding_provider
from app.ai.embeddings.repository import VectorRepository
from app.ai.embeddings.service import EmbeddingService
from app.ai.llm.errors import LLMError, LLMOutputValidationError
from app.ai.prompts.models import Prompt
from app.ai.prompts.prompts import build_qa_prompt
from app.ai.prompts.schemas import EvidenceState, QAOutput
from app.ai.rag.context import ContextBuilder
from app.ai.rag.models import RetrievalResult, RetrievedChunk
from app.ai.rag.query import ProcessedQuery, QueryProcessor
from app.ai.rag.reranking import SimpleReranker
from app.ai.rag.retrieval import VectorRetrievalService
from app.ai.validators.citations import CitationValidator, ValidatedCitation
from app.core.config import settings
from app.core.errors import DocumentNotFoundError
from app.core.supabase import get_supabase_client
from app.repositories.citations import CitationRepository
from app.repositories.documents import DocumentRepository
from app.schemas.qa import CitationOut, QAAnswerOut, RelatedSectionOut

logger = logging.getLogger("app.ai.qa")

_NO_EVIDENCE = (
    "The document does not appear to contain information to answer this "
    "question."
)
_TOKEN_FAILED = "The AI could not produce a valid answer right now."
_LIMIT_REACHED = "The answer could not be backed by any validated citation."
_NOT_CONFIGURED = "AI answers are not configured for this environment."


class QuestionAnsweringService:
    """Answers a single document-grounded question for an authenticated user."""

    def __init__(
        self,
        *,
        retrieval: VectorRetrievalService,
        documents: DocumentRepository,
        citations: CitationValidator,
        llm: StructuredLLM | None,
        query_processor: QueryProcessor | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._retrieval = retrieval
        self._documents = documents
        self._citations = citations
        self._llm = llm
        self._query_processor = query_processor or QueryProcessor()
        self._context_builder = context_builder or ContextBuilder()

    def answer(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        question: str,
    ) -> QAAnswerOut:
        """Answer *question* about *document_id*, grounded in the document."""
        document = self._documents.get_by_id_and_user(user_id, document_id)
        if document is None:
            raise DocumentNotFoundError()

        processed = self._query_processor.process(question)
        result = self._retrieval.retrieve(
            user_id=user_id,
            query=processed.normalized,
            document_id=document_id,
        )
        sources = self._select_evidence(
            result,
            processed,
            user_id=user_id,
            document_id=document_id,
        )
        if not sources:
            return self._abstain(
                document_id=document_id,
                reason=_NO_EVIDENCE,
                model_name=None,
                prompt_version=None,
            )

        prompt = build_qa_prompt(
            question=processed.original,
            context=self._context_builder.build(
                sources,
                document_title=_document_title(document),
            ).text,
        )

        llm = self._llm
        if llm is None:
            return self._abstain(
                document_id=document_id,
                reason=_NOT_CONFIGURED,
                model_name=None,
                prompt_version=prompt.version_id,
            )

        output = self._generate(llm, prompt)
        if output is None:
            return self._abstain(
                document_id=document_id,
                reason=_TOKEN_FAILED,
                model_name=llm.model_name,
                prompt_version=prompt.version_id,
            )
        if output.evidence_state == EvidenceState.INSUFFICIENT_EVIDENCE:
            return self._abstain(
                document_id=document_id,
                reason=output.abstention_reason or _NO_EVIDENCE,
                model_name=llm.model_name,
                prompt_version=prompt.version_id,
            )

        citations = self._citations.validate(
            user_id=user_id,
            document_id=document_id,
            cited_ids=[citation.chunk_id for citation in output.citations],
            retrieved=sources,
        )
        if output.evidence_state == EvidenceState.DOCUMENT_GROUNDED and not citations:
            return self._abstain(
                document_id=document_id,
                reason=_LIMIT_REACHED,
                model_name=llm.model_name,
                prompt_version=prompt.version_id,
            )

        return QAAnswerOut(
            document_id=document_id,
            answer=output.answer,
            evidence_state=output.evidence_state,
            citations=[_to_citation_out(item) for item in citations],
            related_sections=_related_sections(sources),
            model_name=llm.model_name,
            prompt_version=prompt.version_id,
        )

    # -- pipeline steps ------------------------------------------------------

    def _select_evidence(
        self,
        result: RetrievalResult,
        processed: ProcessedQuery,
        *,
        user_id: UUID,
        document_id: UUID,
    ) -> list[RetrievedChunk]:
        """Return the evidence pieces for the answer, deduplicated.

        The primary pass uses the normalized question. When nothing clears the
        relevance threshold, one second-chance pass runs against the keyword
        concept query so multi-hop questions (notice period + severance salary,
        ...) can still surface their sources. Results are merges and sorted by
        relevance, so ``[Source 1]`` is the strongest evidence.
        """
        chunks = list(result.sources)
        if not chunks and processed.concept_query:
            expanded = self._retrieval.retrieve(
                user_id=user_id,
                query=processed.concept_query,
                document_id=document_id,
            )
            chunks = list(expanded.sources)
        seen: set[UUID] = set()
        merged: list[RetrievedChunk] = []
        for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            merged.append(chunk)
        return merged

    def _generate(self, llm: StructuredLLM, prompt: Prompt) -> QAOutput | None:
        """Generate a schema-validated answer with one schema-failure retry.

        Any LLM failure returns ``None`` so the caller abstains honestly — the
        service never invents an answer to avoid surfacing an error.
        """
        try:
            return llm.structured_generate(
                prompt.messages,
                schema=QAOutput,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMOutputValidationError:
            pass
        except LLMError as exc:
            logger.warning("Q&A generation failed: %s", _message(exc))
            return None
        try:
            return llm.structured_generate(
                prompt.messages,
                schema=QAOutput,
                max_tokens=prompt.max_tokens,
                temperature=prompt.temperature,
            )
        except LLMError as exc:
            logger.warning("Q&A generation failed: %s", _message(exc))
            return None

    def _abstain(
        self,
        *,
        document_id: UUID,
        reason: str,
        model_name: str | None,
        prompt_version: str | None,
    ) -> QAAnswerOut:
        return QAAnswerOut(
            document_id=document_id,
            answer=None,
            evidence_state=EvidenceState.INSUFFICIENT_EVIDENCE,
            abstention_reason=reason,
            model_name=model_name,
            prompt_version=prompt_version,
        )


# -- assembly helpers -----------------------------------------------------------


def build_qa_service(*, client: Any | None = None) -> QuestionAnsweringService:
    """Assemble the Q&A service from settings + the Supabase client.

    The LLM is optional: when no model/endpoint is configured the service
    returns INSUFFICIENT-EVIDENCE with a controlled message instead of
    fabricating an answer.
    """
    client = client or get_supabase_client()
    embeddings = EmbeddingService(
        provider=_build_embedding_provider(),
        vectors=VectorRepository(client=client),
    )
    retrieval = VectorRetrievalService(
        embeddings=embeddings,
        vectors=VectorRepository(client=client),
        context_builder=ContextBuilder(),
        top_k=settings.retrieval_top_k,
        min_similarity=settings.retrieval_min_similarity,
        reranker=SimpleReranker(),
    )
    return QuestionAnsweringService(
        retrieval=retrieval,
        documents=DocumentRepository(client=client),
        citations=CitationValidator(CitationRepository(client=client)),
        llm=_build_llm(),
    )


def _build_llm() -> StructuredLLM | None:
    """Build the configured LLM provider, or ``None`` when not configured."""
    if not settings.llm_enabled or not settings.llm_model or not settings.llm_api_url:
        return None
    from app.ai.llm.provider import build_llm_provider

    return build_llm_provider(
        provider=settings.llm_provider,
        model_name=settings.llm_model,
        api_url=settings.llm_api_url,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_request_timeout_seconds,
        max_attempts=settings.llm_max_attempts,
        retry_base_delay_seconds=settings.llm_retry_base_delay_seconds,
        retry_max_delay_seconds=settings.llm_retry_max_delay_seconds,
        retry_jitter_seconds=settings.llm_retry_jitter_seconds,
        requests_per_minute=settings.llm_max_requests_per_minute,
    )


def _build_embedding_provider() -> Any:
    return build_embedding_provider(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model,
        dimension=settings.embedding_dimension,
        batch_size=settings.embedding_batch_size,
        api_url=settings.embedding_api_url,
        api_key=settings.embedding_api_key,
        timeout_seconds=settings.embedding_request_timeout_seconds,
        max_attempts=settings.embedding_max_attempts,
        retry_base_delay_seconds=settings.embedding_retry_base_delay_seconds,
        retry_max_delay_seconds=settings.embedding_retry_max_delay_seconds,
        requests_per_minute=settings.embedding_max_requests_per_minute,
    )


# -- projection helpers ---------------------------------------------------------


def _to_citation_out(item: ValidatedCitation) -> CitationOut:
    return CitationOut(
        id=item.id,
        chunk_id=item.chunk_id,
        document_id=item.document_id,
        section_id=item.section_id,
        clause_id=item.clause_id,
        section=item.section,
        clause=item.clause,
        page_start=item.page_start,
        page_end=item.page_end,
        source_text=item.source_text,
    )


def _related_sections(sources: list[RetrievedChunk]) -> list[RelatedSectionOut]:
    seen: set[str] = set()
    sections: list[RelatedSectionOut] = []
    for source in sources:
        label = _string_of(source.metadata.get("section"))
        if not label or label in seen:
            continue
        seen.add(label)
        sections.append(
            RelatedSectionOut(
                label=label,
                section_id=source.section_id,
                page_start=source.page_start,
                page_end=source.page_end,
            )
        )
    return sections


def _document_title(document: dict[str, Any]) -> str | None:
    return (
        document.get("display_name")
        or document.get("original_filename")
        or None
    )


def _string_of(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _message(exc: Exception) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[: 500]