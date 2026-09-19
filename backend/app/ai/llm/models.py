"""LLM value types shared across providers.

These types carry model, usage and latency metadata so the observability layer
(AI-Architecture.md §22) can track ``model``, ``task``, ``latency`` and
``token usage`` without ever logging full document content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ChatMessage:
    """One message in a chat conversation (role + content)."""

    role: Literal["system", "user", "assistant"]
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class LLMUsage:
    """Token usage reported by the provider (safe observability metadata)."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    """A completed generation plus its safe metadata."""

    content: str
    model: str
    finish_reason: str
    usage: LLMUsage | None
    duration_ms: int