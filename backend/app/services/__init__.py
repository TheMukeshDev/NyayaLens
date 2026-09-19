"""Service layer.

Cross-cutting application services that are not persistence or routes:
document upload validation, storage, and (later) orchestration.

Persistence lives in ``app.repositories``; AI/LLM work lives in ``app.ai``.
"""

from .file_validation import (
    ValidationOutcome,
    sanitize_filename,
    supported_mime_types,
    validate_uploaded_file,
)

__all__ = [
    "ValidationOutcome",
    "sanitize_filename",
    "supported_mime_types",
    "validate_uploaded_file",
]
