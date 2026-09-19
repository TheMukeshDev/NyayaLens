"""Versioned prompt value type.

A :class:`Prompt` is the immutable, assembled request for one AI task: system +
user messages (instructions and data already separated), generation settings
and the structured-output schema it must satisfy. Prompts carry a ``version``
so model/prompt changes stay traceable (Prompt-Strategy.md §16,
AI-Evaluation.md §15).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from app.ai.llm.models import ChatMessage


@dataclass(frozen=True)
class Prompt:
    """An assembled, versioned prompt with its generation contract."""

    name: str
    version: str
    messages: tuple[ChatMessage, ...]
    temperature: float | None = None
    max_tokens: int | None = None
    response_schema: type[BaseModel] | None = None

    @property
    def version_id(self) -> str:
        """Stable identifier, e.g. ``qa_prompt_v1`` (Prompt-Strategy.md §16)."""
        return f"{self.name}_prompt_{self.version}"

    def to_openai_messages(self) -> list[dict[str, str]]:
        """Render messages for an OpenAI-compatible chat endpoint."""
        return [message.to_dict() for message in self.messages]

    def render(self) -> str:
        """Flatten the prompt for inspection/logging without document content."""
        return "\n\n---\n\n".join(message.content for message in self.messages)