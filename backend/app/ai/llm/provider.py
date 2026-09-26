"""LLM provider abstraction and the OpenAI-compatible implementation.

The application talks to language models only through :class:`LLMProvider`
(AI-Architecture.md §15, Model Independence):

* ``generate()`` — free-text generation.
* ``structured_generate()`` — generation constrained to a schema-validated JSON
  object (AI-Architecture.md §12, Prompt-Strategy.md §18).

Implemented providers:

* :class:`OpenAICompatibleLLMProvider` — POST ``/chat/completions`` on an
  OpenAI-compatible endpoint over HTTPS (production path; no new SDK).
* :class:`GeminiInteractionsLLMProvider` — POST ``/interactions`` using
    Gemini's native Interactions API contract.

Call policy is uniform (``app.ai.transport``): configurable timeout, an
exponential-backoff retry policy for transient failures only, and an optional
client-side request throttle. Keys stay on the backend and are never exposed to
the frontend.

The provider NEVER fabricates output: if the upstream is unreachable, rate
limits, times out, returns an empty completion or an unparseable payload, the
call fails with a controlled :class:`LLMError` subclass — it does not invent an
answer.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from typing import Any, Literal, override

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.llm.errors import (
    LLMError,
    LLMOutputValidationError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.llm.models import ChatMessage, LLMResponse, LLMUsage
from app.ai.transport import RequestThrottle, RetryPolicy, is_retryable_status

_Monotonic = Callable[[], float]
_Sleeper = Callable[[float], None]

_RESPONSE_FORMAT = Literal["text", "json_object"]
_RETRY_AFTER_CAP_SECONDS = 60.0


class LLMProvider:
    """Provider-independent chat-completion interface."""

    @property
    def model_name(self) -> str:
        raise NotImplementedError

    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: _RESPONSE_FORMAT = "text",
    ) -> LLMResponse:
        """Generate a completion for *messages* (no fabricated output)."""
        raise NotImplementedError

    def structured_generate[T: BaseModel](
        self,
        messages: Sequence[ChatMessage],
        *,
        schema: type[T],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> T:
        """Generate and validate structured JSON output against *schema*."""
        response = self.generate(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format="json_object",
        )
        return parse_structured_content(response.content, schema)


def parse_structured_content[T: BaseModel](content: str, schema: type[T]) -> T:
    """Validate raw model output against *schema*, raising a controlled error.

    Strips a trailing ```json ... ``` code fence if the model returned one, then
    validates. Malformed or schema-mismatched output is never accepted blindly
    (Prompt-Strategy.md §18).
    """
    text = _strip_code_fence(content)
    try:
        return schema.model_validate_json(text)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise LLMOutputValidationError(
            "The model returned output that did not match the required schema."
        ) from exc


class OpenAICompatibleLLMProvider(LLMProvider):
    """Chat completions via an OpenAI-compatible ``/chat/completions`` endpoint."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        api_key: str = "",
        timeout_seconds: float = 60.0,
        retry_policy: RetryPolicy | None = None,
        requests_per_minute: int = 0,
        transport: httpx.BaseTransport | None = None,
        monotonic: _Monotonic = time.monotonic,
        sleeper: _Sleeper = time.sleep,
    ) -> None:
        if not model_name:
            raise LLMProviderUnavailableError("No LLM model is configured.")
        if not base_url:
            raise LLMProviderUnavailableError("No LLM provider endpoint is configured.")
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._policy = retry_policy or RetryPolicy(
            max_attempts=1,
            base_delay_seconds=1.0,
            max_delay_seconds=1.0,
        )
        self._throttle = RequestThrottle(
            requests_per_minute=requests_per_minute,
            monotonic=monotonic,
            sleeper=sleeper,
        )
        self._transport = transport
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
            self._client = httpx.Client(
                timeout=httpx.Timeout(self._timeout_seconds),
                transport=self._transport,
                limits=limits,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def __del__(self) -> None:
        self.close()

    @property
    @override
    def model_name(self) -> str:
        return self._model_name

    @override
    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: _RESPONSE_FORMAT = "text",
    ) -> LLMResponse:
        if not messages:
            raise LLMError("At least one message is required.")
        payload = self._build_payload(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )
        headers = _headers(self._api_key)
        started = self._monotonic()
        attempt = 0
        while True:
            attempt += 1
            self._throttle.wait()
            try:
                response = self._post(payload, headers)
            except httpx.TimeoutException as exc:
                if attempt >= self._policy.max_attempts:
                    raise LLMTimeoutError("The LLM provider did not respond in time.") from exc
                self._sleeper(self._policy.delay_for(attempt))
                continue
            except httpx.HTTPError as exc:
                if attempt >= self._policy.max_attempts:
                    raise LLMProviderUnavailableError(
                        "The LLM provider could not be reached."
                    ) from exc
                self._sleeper(self._policy.delay_for(attempt))
                continue
            status = response.status_code
            if 200 <= status < 300:
                return self._parse_response(response, started)
            if is_retryable_status(status):
                if attempt >= self._policy.max_attempts:
                    if status == 429:
                        raise LLMRateLimitError(
                            "The LLM provider is rate-limiting requests right now."
                        )
                    raise LLMProviderUnavailableError("The LLM provider is currently unavailable.")
                delay = (
                    self._retry_after(response)
                    if status == 429
                    else self._policy.delay_for(attempt)
                )
                self._sleeper(delay)
                continue
            raise LLMProviderUnavailableError("The LLM provider rejected the request.")

    def _build_payload(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None,
        temperature: float | None,
        response_format: _RESPONSE_FORMAT,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": [message.to_dict() for message in messages],
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _post(self, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        """Perform one POST using persistent connection pool."""
        client = self._get_client()
        return client.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
        )

    def _parse_response(self, response: httpx.Response, started: float) -> LLMResponse:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderUnavailableError(
                "The LLM provider returned an unexpected response."
            ) from exc
        choices = data.get("choices") or []
        finish_reason = str(choices[0].get("finish_reason") or "stop") if choices else "stop"
        content = str(choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        if not content:
            raise LLMProviderUnavailableError("The LLM provider returned an empty completion.")
        usage = _usage_of(data.get("usage"))
        duration_ms = max(0, int((self._monotonic() - started) * 1000))
        return LLMResponse(
            content=content,
            model=str(data.get("model") or self._model_name),
            finish_reason=finish_reason,
            usage=usage,
            duration_ms=duration_ms,
        )

    def _retry_after(self, response: httpx.Response) -> float:
        header = response.headers.get("retry-after")
        if header and header.isdigit():
            return min(float(header), _RETRY_AFTER_CAP_SECONDS)
        return self._policy.delay_for(1)


class GeminiInteractionsLLMProvider(LLMProvider):
    """Gemini Interactions API provider (``/v1beta/interactions``)."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        api_key: str = "",
        api_revision: str = "2026-05-20",
        timeout_seconds: float = 60.0,
        retry_policy: RetryPolicy | None = None,
        requests_per_minute: int = 0,
        transport: httpx.BaseTransport | None = None,
        monotonic: _Monotonic = time.monotonic,
        sleeper: _Sleeper = time.sleep,
    ) -> None:
        if not model_name:
            raise LLMProviderUnavailableError("No LLM model is configured.")
        if not base_url:
            raise LLMProviderUnavailableError("No LLM provider endpoint is configured.")
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._api_revision = api_revision
        self._timeout_seconds = timeout_seconds
        self._policy = retry_policy or RetryPolicy(
            max_attempts=1, base_delay_seconds=1.0, max_delay_seconds=1.0
        )
        self._throttle = RequestThrottle(
            requests_per_minute=requests_per_minute, monotonic=monotonic, sleeper=sleeper
        )
        self._transport = transport
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
            self._client = httpx.Client(
                timeout=httpx.Timeout(self._timeout_seconds),
                transport=self._transport,
                limits=limits,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def __del__(self) -> None:
        self.close()

    @property
    @override
    def model_name(self) -> str:
        return self._model_name

    @override
    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: _RESPONSE_FORMAT = "text",
    ) -> LLMResponse:
        if not messages:
            raise LLMError("At least one message is required.")
        del max_tokens, temperature
        prompt = _interactions_input(messages, response_format)
        payload = {"model": self._model_name, "input": prompt}
        headers = {
            "Content-Type": "application/json",
            "Api-Revision": self._api_revision,
        }
        if self._api_key:
            headers["x-goog-api-key"] = self._api_key
        started = self._monotonic()
        attempt = 0
        while True:
            attempt += 1
            self._throttle.wait()
            try:
                client = self._get_client()
                response = client.post(
                    f"{self._base_url}/interactions", json=payload, headers=headers
                )
            except httpx.TimeoutException as exc:
                if attempt >= self._policy.max_attempts:
                    raise LLMTimeoutError("The LLM provider did not respond in time.") from exc
                self._sleeper(self._policy.delay_for(attempt))
                continue
            except httpx.HTTPError as exc:
                if attempt >= self._policy.max_attempts:
                    raise LLMProviderUnavailableError(
                        "The LLM provider could not be reached."
                    ) from exc
                self._sleeper(self._policy.delay_for(attempt))
                continue
            if 200 <= response.status_code < 300:
                return self._parse_response(response, started)
            if is_retryable_status(response.status_code):
                if attempt >= self._policy.max_attempts:
                    if response.status_code == 429:
                        raise LLMRateLimitError(
                            "The LLM provider is rate-limiting requests right now."
                        )
                    raise LLMProviderUnavailableError("The LLM provider is currently unavailable.")
                self._sleeper(self._policy.delay_for(attempt))
                continue
            raise LLMProviderUnavailableError("The LLM provider rejected the request.")

    def _parse_response(self, response: httpx.Response, started: float) -> LLMResponse:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderUnavailableError(
                "The LLM provider returned an unexpected response."
            ) from exc
        content: list[str] = []
        for step in data.get("steps") or []:
            if step.get("type") != "model_output":
                continue
            for item in step.get("content") or []:
                if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                    content.append(str(item["text"]))
        text = "\n".join(content).strip()
        if not text:
            raise LLMProviderUnavailableError("The LLM provider returned an empty completion.")
        usage_data = data.get("usage") or {}
        usage = (
            LLMUsage(
                prompt_tokens=int(usage_data.get("total_input_tokens", 0)),
                completion_tokens=int(usage_data.get("total_output_tokens", 0)),
                total_tokens=int(usage_data.get("total_tokens", 0)),
            )
            if usage_data
            else None
        )
        return LLMResponse(
            content=text,
            model=str(data.get("model") or self._model_name),
            finish_reason=str(data.get("status") or "completed"),
            usage=usage,
            duration_ms=max(0, int((self._monotonic() - started) * 1000)),
        )


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _interactions_input(messages: Sequence[ChatMessage], response_format: _RESPONSE_FORMAT) -> str:
    prompt = "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)
    if response_format == "json_object":
        prompt += "\n\nReturn only valid JSON. Do not wrap it in markdown code fences."
    return prompt


def _usage_of(value: object) -> LLMUsage | None:
    if not isinstance(value, dict):
        return None
    prompt = value.get("prompt_tokens")
    completion = value.get("completion_tokens")
    total = value.get("total_tokens")
    if not (
        isinstance(prompt, (int, float))
        and isinstance(completion, (int, float))
        and isinstance(total, (int, float))
    ):
        return None
    return LLMUsage(
        prompt_tokens=int(prompt),
        completion_tokens=int(completion),
        total_tokens=int(total),
    )


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    return match.group(1) if match else text


def build_llm_provider(
    *,
    provider: str,
    model_name: str,
    api_url: str,
    api_key: str = "",
    timeout_seconds: float = 60.0,
    max_attempts: int = 3,
    retry_base_delay_seconds: float = 1.0,
    retry_max_delay_seconds: float = 10.0,
    retry_jitter_seconds: float = 0.0,
    requests_per_minute: int = 0,
) -> LLMProvider:
    """Assemble the configured LLM provider from setting values."""
    if provider == "openai-compatible":
        return OpenAICompatibleLLMProvider(
            model_name=model_name,
            base_url=api_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            retry_policy=RetryPolicy(
                max_attempts=max_attempts,
                base_delay_seconds=retry_base_delay_seconds,
                max_delay_seconds=retry_max_delay_seconds,
                jitter_seconds=retry_jitter_seconds,
            ),
            requests_per_minute=requests_per_minute,
        )
    if provider == "gemini-interactions":
        return GeminiInteractionsLLMProvider(
            model_name=model_name,
            base_url=api_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            retry_policy=RetryPolicy(
                max_attempts=max_attempts,
                base_delay_seconds=retry_base_delay_seconds,
                max_delay_seconds=retry_max_delay_seconds,
                jitter_seconds=retry_jitter_seconds,
            ),
            requests_per_minute=requests_per_minute,
        )
    raise ValueError(f"unsupported llm provider: {provider}")
