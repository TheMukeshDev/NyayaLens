"""AI document understanding orchestration.

Runs the three structured analyses behind the document-understanding feature
set (summary, clause extraction, attention analysis) against deterministic
extraction output, persists only schema-validated results and returns the
evidence-referenced read model. See ``service`` for the honesty guarantees:
no fabrications, no legal score, explicit abstention.
"""

from app.ai.analysis.service import DocumentUnderstandingService, StructuredLLM

__all__ = ["DocumentUnderstandingService", "StructuredLLM"]