"""Context builder for retrieved evidence (RAG-Architecture.md §13).

Assembles ordered evidence blocks the way the prompt layer expects them:

    [Source 1]
    Section: 8. Termination
    Page: 6
    Clause: 8.2

    Text:
    "..."
"""

from __future__ import annotations

from app.ai.rag.models import BuiltContext, RetrievedChunk, SourceBlock


class ContextBuilder:
    """Flattens retrieved chunks into structured, citable evidence text."""

    def build(
        self,
        sources: list[RetrievedChunk],
        *,
        document_title: str | None = None,
    ) -> BuiltContext:
        blocks = [
            SourceBlock(
                order=index + 1,
                chunk_id=source.chunk_id,
                section=_string_of(source.metadata.get("section")),
                clause=_string_of(source.metadata.get("clause")),
                page_start=source.page_start,
                page_end=source.page_end,
                content=source.content,
            )
            for index, source in enumerate(sources)
        ]
        estimated_tokens = sum(len(source.content.split()) for source in sources)
        return BuiltContext(
            text=_assemble(blocks, document_title=document_title),
            blocks=blocks,
            estimated_tokens=estimated_tokens,
        )


def _assemble(blocks: list[SourceBlock], *, document_title: str | None) -> str:
    lines: list[str] = []
    if document_title:
        lines.append(f"DOCUMENT: {document_title}\n")
    for block in blocks:
        lines.append(f"[Source {block.order}]")
        if block.section:
            lines.append(f"Section: {block.section}")
        if block.clause:
            lines.append(f"Clause: {block.clause}")
        if block.page_start is not None:
            page = (
                str(block.page_start)
                if block.page_end is None or block.page_end == block.page_start
                else f"{block.page_start}-{block.page_end}"
            )
            lines.append(f"Page: {page}")
        lines.append("")
        lines.append("Text:")
        lines.append(block.content)
        lines.append("")
    return "\n".join(lines).strip()


def _string_of(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None