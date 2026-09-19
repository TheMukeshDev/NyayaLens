"""Versioned prompt builders (v1).

Every builder keeps instructions and document data structurally separate
(Prompt-Strategy.md §2): data is only ever placed inside the evidence fence of
the user message, never in the system message, and the immutable grounding
system prompt (``core.system_prompt``) enforces the injection defense, the
legal boundary and abstention.

Tasks (Prompt-Strategy.md §5-§12, AI-Architecture.md §7-§9):
summary, clause extraction, attention analysis, Q&A, comparison, action.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.ai.prompts import core
from app.ai.prompts.models import Prompt
from app.ai.prompts.registry import prompt
from app.ai.prompts.schemas import (
    ActionOutput,
    AttentionOutput,
    ClauseExtractionOutput,
    ComparisonOutput,
    ProfessionalQuestionsOutput,
    QAOutput,
    SummaryOutput,
)

_QA_BLUEPRINT = """{
  "answer": "Plain-language answer, grounded in the evidence.",
  "evidence_state": "DOCUMENT-GROUNDED",
  "citations": [{"chunk_id": "matches a supplied [Source N]"}],
  "follow_up": "Practical question for a professional, or null.",
  "confidence": "LOW|MEDIUM|HIGH",
  "abstention_reason": "Required when evidence_state is INSUFFICIENT-EVIDENCE."
}"""

_SUMMARY_BLUEPRINT = """{
  "evidence_state": "DOCUMENT-GROUNDED",
  "overview": "2-3 sentence neutral overview.",
  "document_type": "Detected type, e.g. 'Employment Agreement'.",
  "purpose": "Stated purpose of the document.",
  "parties": ["Named parties as they appear"],
  "key_terms": ["Terms that matter, e.g. '120,000 USD annual salary'"],
  "obligations": ["Plain-language obligations"],
  "important_conditions": ["Matters that deserve attention"],
  "abstention_reason": "Set when INSUFFICIENT-EVIDENCE."
}"""

_CLAUSE_BLUEPRINT = """{
  "evidence_state": "DOCUMENT-GROUNDED",
  "clauses": [{
    "clause_number": "1.1",
    "clause_type": "Termination",
    "title": "Notice",
    "original_text": "The clause text as written in the document.",
    "explanation": "Plain-language explanation of what it says."
  }],
  "abstention_reason": "Set when INSUFFICIENT-EVIDENCE."
}"""

_ATTENTION_BLUEPRINT = """{
  "evidence_state": "DOCUMENT-GROUNDED",
  "attention_items": [{
    "attention_level": "HIGH|MEDIUM|LOW",
    "area": "What deserves closer review",
    "reason": "Why it may deserve review",
    "source_support": "The document text that supports this observation",
    "practical_question": "A question the user could ask a professional"
  }],
  "abstention_reason": "Set when INSUFFICIENT-EVIDENCE."
}"""

_COMPARISON_BLUEPRINT = """{
  "change_type": "ADDED|REMOVED|MODIFIED|UNCHANGED",
  "importance": "HIGH|MEDIUM|LOW",
  "before": "Text in the earlier version, or null.",
  "after": "Text in the later version, or null.",
  "explanation": "What changed and why it may matter.",
  "evidence_state": "DOCUMENT-GROUNDED",
  "abstention_reason": "Set when INSUFFICIENT-EVIDENCE."
}"""

_ACTION_BLUEPRINT = """{
  "evidence_state": "DOCUMENT-GROUNDED",
  "actions": [{
    "title": "Short practical action title.",
    "priority": "HIGH|MEDIUM|LOW",
    "reason": "Why this action is suggested.",
    "source": {"clause": "Referenced clause"},
    "practical_question": "A question for a professional, or null."
  }],
  "abstention_reason": "Set when INSUFFICIENT-EVIDENCE."
}"""

_QUESTIONS_BLUEPRINT = """{
  "evidence_state": "DOCUMENT-GROUNDED",
  "questions": [{
    "question": "A question the user can raise with a qualified professional.",
    "source": {"clause": "The cited clause number", "section": "The cited section"}
  }],
  "abstention_reason": "Set when INSUFFICIENT-EVIDENCE."
}"""


@prompt("summary", "v1")
def build_summary_prompt(*, content: str, document_type: str | None = None) -> Prompt:
    sections = [
        core.task_section(
            "Write a structured summary of the document below. Summarize what the "
            "document says neutrally, without assumptions, dramatic language or "
            "legal conclusions. Attribute every statement to the supplied text."
        ),
        core.metadata_section(document_type=document_type or ""),
        core.evidence_section(content),
        core.rules_section(
            core.shared_rules()
            + [
                "Obligations and conditions must be stated in plain language.",
                'Use "may" if the duty is conditional or reciprocal.',
            ]
        ),
        core.output_section(_SUMMARY_BLUEPRINT),
    ]
    return Prompt(
        name="summary",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.4,
        max_tokens=1200,
        response_schema=SummaryOutput,
    )


@prompt("clause_extraction", "v1")
def build_clause_extraction_prompt(*, clauses: Sequence[str]) -> Prompt:
    numbered = "\n".join(
        f"[Clause {index}] {text}".strip()
        for index, text in enumerate(clauses, start=1)
    )
    sections = [
        core.task_section(
            "For every listed clause, classify its type, give its number and "
            "title if present, keep the original text verbatim, and explain the "
            "clause in plain language. Distinguish what the clause says from what "
            "might deserve extra review. If a clause is ambiguous, say so."
        ),
        core.evidence_section(numbered),
        core.rules_section(
            core.shared_rules()
            + [
                "original_text must be verbatim from the supplied clause, never rephrased.",
                "Choose clause_type from the allowed enum; use Other only when none fit.",
                "An ambiguous clause is a review signal, not proof of invalidity.",
            ]
        ),
        core.output_section(_CLAUSE_BLUEPRINT),
    ]
    return Prompt(
        name="clause_extraction",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.1,
        max_tokens=2000,
        response_schema=ClauseExtractionOutput,
    )


@prompt("attention", "v1")
def build_attention_prompt(*, content: str, document_type: str | None = None) -> Prompt:
    sections = [
        core.task_section(
            "Identify the parts of the document below that may deserve closer "
            "review (areas requiring attention). Base each observation on the "
            "supplied text and frame it as a review signal — never as a "
            "guaranteed legal risk, and never as a legal conclusion."
        ),
        core.metadata_section(document_type=document_type or ""),
        core.evidence_section(content),
        core.rules_section(
            core.shared_rules()
            + [
                "Attention signals may include unusual obligations, financial commitments, "
                "long notice periods, termination conditions, restrictions, liability, "
                "indemnification, renewals, ambiguous wording or missing expected information.",
                "Use HIGH only for items that truly warrant prioritized review.",
                "source_support must quote or cite the exact document text that supports the item.",
            ]
        ),
        core.output_section(_ATTENTION_BLUEPRINT),
    ]
    return Prompt(
        name="attention",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.3,
        max_tokens=1500,
        response_schema=AttentionOutput,
    )


@prompt("qa", "v1")
def build_qa_prompt(*, question: str, context: str) -> Prompt:
    sections = [
        core.task_section(
            "Answer the user's question using only the supplied evidence. Answer "
            "in plain language suitable for a non-expert."
        ),
        core.evidence_section(context),
        core.question_section(question),
        core.rules_section(
            core.shared_rules()
            + core.abstain_rules()
            + [
                "Cite the matching [Source N] block for every document-specific claim.",
                "If sources conflict, describe both and flag professional review.",
                'General information that is not established by the document must only be '
                'labelled "GENERAL-INFORMATION" and never presented as document content.',
            ]
        ),
        core.output_section(_QA_BLUEPRINT),
    ]
    return Prompt(
        name="qa",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.2,
        max_tokens=1000,
        response_schema=QAOutput,
    )


@prompt("comparison", "v1")
def build_comparison_prompt(*, before: str, after: str) -> Prompt:
    sections = [
        core.task_section(
            "Compare the two clause variants below and classify the change."
        ),
        core.evidence_section(
            f"BEFORE (untouched earlier version):\n{before}\n\n"
            f"AFTER (newer version):\n{after}"
        ),
        core.rules_section(
            core.shared_rules()
            + [
                "change_type is ADDED, REMOVED, MODIFIED or UNCHANGED.",
                "before/after must repeat the supplied text when present (null otherwise).",
                "Score importance by business consequence, not word count.",
                "If the variants cannot be matched reliably, abstain.",
            ]
        ),
        core.output_section(_COMPARISON_BLUEPRINT),
    ]
    return Prompt(
        name="comparison",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.1,
        max_tokens=800,
        response_schema=ComparisonOutput,
    )


@prompt("action", "v1")
def build_action_prompt(
    *,
    summary: str,
    attention: Sequence[str],
    key_clauses: Sequence[str],
) -> Prompt:
    attention_text = "\n".join(f"- {item}".strip() for item in attention) or "None."
    clauses_text = "\n".join(f"- {clause}".strip() for clause in key_clauses) or "None."
    sections = [
        core.task_section(
            "Suggest practical, non-directive next steps for the user based on the "
            "analysis below. Actions help the user prepare for professional "
            'discussion; never tell the user to "do not sign" or to take an '
            "affirmative legal position, and never make legal judgments."
        ),
        core.metadata_section(summary=summary),
        core.evidence_section(
            f"ATTENTION ITEMS:\n{attention_text}\n\nKEY CLAUSES:\n{clauses_text}"
        ),
        core.rules_section(
            core.shared_rules()
            + [
                "Each action must be practical, non-directive and tied to a cited item.",
                "Suggest professional review for high-stakes, ambiguous or conflicting provisions.",
                "Do not generate litigation strategy or legal advice.",
            ]
        ),
        core.output_section(_ACTION_BLUEPRINT),
    ]
    return Prompt(
        name="action",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.3,
        max_tokens=1000,
        response_schema=ActionOutput,
    )


@prompt("professional_questions", "v1")
def build_professional_questions_prompt(
    *,
    attention: Sequence[str],
    key_clauses: Sequence[str],
    user_context: str | None = None,
) -> Prompt:
    attention_text = "\n".join(f"- {item}".strip() for item in attention) or "None."
    clauses_text = "\n".join(f"- {clause}".strip() for clause in key_clauses) or "None."
    context_text = user_context.strip() if user_context else ""
    sections = [
        core.task_section(
            "Generate questions the user may raise with a qualified legal "
            "professional, based on the document analysis below. Questions help "
            "the user prepare for that discussion. Never tell the user what "
            "legal decision to make, never predict an outcome, and never "
            "suggest that a provision is enforceable or invalid."
        ),
        core.evidence_section(
            f"KEY CLAUSES:\n{clauses_text}\n\nATTENTION ITEMS:\n{attention_text}"
        ),
        core.metadata_section(user_context=context_text),
        core.rules_section(
            core.shared_rules()
            + [
                "Base every question on the supplied evidence; do not invent clauses.",
                "Every document-grounded question must quote its source clause, "
                'for example "source": {"clause": "1.1", "section": "1"}).',
                "Do not ask broadly about legal strategy or legal rights.",
                "If the evidence is insufficient to support any question, abstain.",
            ]
        ),
        core.output_section(_QUESTIONS_BLUEPRINT),
    ]
    return Prompt(
        name="professional_questions",
        version="v1",
        messages=(core.system_prompt(), core.user_message(_join(sections))),
        temperature=0.3,
        max_tokens=700,
        response_schema=ProfessionalQuestionsOutput,
    )


def _join(sections: list[str]) -> str:
    return "\n\n".join(section for section in sections if section)