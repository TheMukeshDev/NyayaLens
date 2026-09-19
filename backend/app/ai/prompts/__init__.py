"""Versioned, safety-hardened prompts (Prompt-Strategy.md).

Every prompt separates instructions from document data, treats uploaded
documents as untrusted content, resists prompt injection, avoids unsupported
legal conclusions, and supports abstention. Version ids follow
``{name}_prompt_{version}``.
"""

from app.ai.prompts.core import (
    evidence_section,
    metadata_section,
    output_section,
    question_section,
    rules_section,
    system_prompt,
    task_section,
)
from app.ai.prompts.models import Prompt
from app.ai.prompts.prompts import (
    build_action_prompt,
    build_attention_prompt,
    build_clause_extraction_prompt,
    build_comparison_prompt,
    build_qa_prompt,
    build_summary_prompt,
)
from app.ai.prompts.registry import get_prompt, latest_version, list_prompt_ids, prompt
from app.ai.prompts.schemas import (
    ActionOutput,
    AttentionOutput,
    ChangeType,
    Citation,
    ClauseExtractionOutput,
    ClauseType,
    ComparisonOutput,
    EvidenceState,
    QAOutput,
    RelativeImportance,
    SummaryOutput,
)

__all__ = [
    "ActionOutput",
    "AttentionOutput",
    "ChangeType",
    "Citation",
    "ClauseExtractionOutput",
    "ClauseType",
    "ComparisonOutput",
    "EvidenceState",
    "Prompt",
    "QAOutput",
    "RelativeImportance",
    "SummaryOutput",
    "build_action_prompt",
    "build_attention_prompt",
    "build_clause_extraction_prompt",
    "build_comparison_prompt",
    "build_qa_prompt",
    "build_summary_prompt",
    "evidence_section",
    "get_prompt",
    "latest_version",
    "list_prompt_ids",
    "metadata_section",
    "output_section",
    "prompt",
    "question_section",
    "rules_section",
    "system_prompt",
    "task_section",
]