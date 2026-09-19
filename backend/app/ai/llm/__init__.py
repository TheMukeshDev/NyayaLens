"""LLM provider abstraction (AI-Architecture.md §15, Model Independence)."""

from app.ai.llm.errors import (
    LLMError,
    LLMOutputValidationError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.llm.models import ChatMessage, LLMResponse, LLMUsage
from app.ai.llm.provider import (
    LLMProvider,
    OpenAICompatibleLLMProvider,
    build_llm_provider,
)

__all__ = [
    "ChatMessage",
    "LLMError",
    "LLMOutputValidationError",
    "LLMProvider",
    "LLMProviderUnavailableError",
    "LLMRateLimitError",
    "LLMResponse",
    "LLMTimeoutError",
    "LLMUsage",
    "OpenAICompatibleLLMProvider",
    "build_llm_provider",
]