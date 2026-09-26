"""Shared FastAPI dependencies."""

from app.ai.action_center.service import (
    ActionCenterService,
    build_action_center_service,
)
from app.ai.analysis.service import DocumentUnderstandingService
from app.ai.comparison.service import DocumentComparisonService, build_comparison_service
from app.ai.embeddings.repository import VectorRepository
from app.ai.qa.service import QuestionAnsweringService, build_qa_service
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.supabase import get_supabase_client
from app.repositories.analysis import AnalysisRepository
from app.repositories.audit import AuditLogRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing import ProcessingRepository
from app.services.processing import DocumentProcessingService
from app.services.storage import DocumentStorage, get_document_storage

__all__ = [
    "AuthenticatedUser",
    "get_current_user",
    "DocumentStorage",
    "get_document_storage",
    "DocumentRepository",
    "get_document_repository",
    "AuditLogRepository",
    "get_audit_repository",
    "QuestionAnsweringService",
    "get_qa_service",
    "DocumentComparisonService",
    "get_comparison_service",
    "ActionCenterService",
    "get_action_center_service",
    "DocumentUnderstandingService",
    "get_understanding_service",
    "DocumentProcessingService",
    "get_processing_service",
]

_qa_service: QuestionAnsweringService | None = None
_comparison_service: DocumentComparisonService | None = None
_action_center_service: ActionCenterService | None = None
_understanding_service: DocumentUnderstandingService | None = None
_processing_service: DocumentProcessingService | None = None


def get_document_repository() -> DocumentRepository:
    """Return a service-role, owner-scoped document repository."""
    return DocumentRepository()


def get_audit_repository() -> AuditLogRepository:
    """Return the server-side audit log repository."""
    return AuditLogRepository()


def get_qa_service() -> QuestionAnsweringService:
    """Return the shared document-grounded Q&A service (built lazily).

    Built once because it assembles the configured embedding/LLM providers.
    """
    global _qa_service
    if _qa_service is None:
        _qa_service = build_qa_service()
    return _qa_service


def get_comparison_service() -> DocumentComparisonService:
    """Return the shared document comparison service (built lazily)."""
    global _comparison_service
    if _comparison_service is None:
        _comparison_service = build_comparison_service()
    return _comparison_service


def get_action_center_service() -> ActionCenterService:
    """Return the shared Action Center service (built lazily)."""
    global _action_center_service
    if _action_center_service is None:
        _action_center_service = build_action_center_service(storage=get_document_storage())
    return _action_center_service


def get_processing_service() -> DocumentProcessingService:
    """Return the shared document processing pipeline (built lazily).

    Assembles the same service the standalone worker uses, so a platform with no
    long-lived worker process (serverless) can run the identical pipeline
    in-request. Imported lazily because the pipeline pulls in every AI
    provider, which must not be constructed during application import.
    """
    global _processing_service
    if _processing_service is None:
        from app.workers.document_worker import build_default_service

        _processing_service = build_default_service()
    return _processing_service


def get_understanding_service() -> DocumentUnderstandingService:
    """Return the shared document-understanding read service (built lazily).

    Builds with no LLM because the read path only assembles persisted,
    already-validated analysis rows — it never generates content.
    """
    global _understanding_service
    if _understanding_service is None:
        client = get_supabase_client()
        _understanding_service = DocumentUnderstandingService(
            llm=None,
            analyses=AnalysisRepository(client=client),
            processing=ProcessingRepository(client=client),
            vectors=VectorRepository(client=client),
        )
    return _understanding_service