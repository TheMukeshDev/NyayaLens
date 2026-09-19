"""Document comparison schemas (docs/03_TECH/API-Specification.md §19).

Requests compare two owned documents; responses expose the persisted
``comparisons`` / ``comparison_changes`` rows (Database-Schema.md §12). Claims
made by every response:

* ``ChangeOut`` entries exist only when clauses provably differ between the
  versions — the backend detects changes deterministically and the model never
  invents, removes or reclassifies one.
* ``citation_a`` / ``citation_b`` always point at real, owner-scoped clauses in
  the respective document (or are ``None`` when the clause has no counterpart
  on that side).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.prompts.schemas import ChangeType, RelativeImportance


class ComparisonRequest(BaseModel):
    """Two documents (both owned by the authenticated user) to compare."""

    document_a_id: UUID = Field(description="The earlier document version.")
    document_b_id: UUID = Field(description="The newer document version.")


class ChangeCitationOut(BaseModel):
    """One side of a change, resolved to a real clause in one document."""

    document_id: UUID
    section_id: UUID | None = None
    clause_id: UUID | None = None
    section: str
    clause: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source_text: str


class ChangeOut(BaseModel):
    """One detected change with both sides quoted and cited."""

    type: ChangeType
    section: str
    clause: str | None = None
    before: str | None = None
    after: str | None = None
    explanation: str
    importance: RelativeImportance | None = None
    citation_a: ChangeCitationOut | None = None
    citation_b: ChangeCitationOut | None = None


class ComparisonOut(BaseModel):
    """A comparison run between two owned documents."""

    comparison_id: UUID
    document_a_id: UUID
    document_b_id: UUID
    status: str
    summary: str | None = None
    created_at: str
    completed_at: str | None = None


class ComparisonChangesData(BaseModel):
    """The detected changes of one comparison, oldest stored first."""

    comparison_id: UUID
    changes: list[ChangeOut] = Field(default_factory=list)