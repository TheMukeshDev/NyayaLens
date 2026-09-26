"""LLM provider tests (hermetic — MockTransport, injected clock; no network)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.ai.llm.errors import (
    LLMError,
    LLMOutputValidationError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.llm.models import ChatMessage
from app.ai.llm.provider import (
    GeminiInteractionsLLMProvider,
    LLMProvider,
    OpenAICompatibleLLMProvider,
    build_llm_provider,
    parse_structured_content,
)
from app.ai.prompts.schemas import EvidenceState, QAOutput
from app.ai.transport import RetryPolicy

MODEL = "test-llm"
URL = "https://ai.test/v1"


def _chat_response(
    content: str,
    *,
    model: str = MODEL,
    usage: dict | None = None,
    finish: str = "stop",
) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish,
            }
        ],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _provider(
    handler,
    *,
    policy: RetryPolicy | None = None,
    requests_per_minute: int = 0,
    api_key: str = "sk-test-secret",
    clock: _FakeClock | None = None,
) -> OpenAICompatibleLLMProvider:
    clock = clock or _FakeClock()
    return OpenAICompatibleLLMProvider(
        model_name=MODEL,
        base_url=URL,
        api_key=api_key,
        timeout_seconds=5.0,
        retry_policy=policy or RetryPolicy(max_attempts=1),
        requests_per_minute=requests_per_minute,
        transport=httpx.MockTransport(handler),
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
    )


def _ok_handler(content: str = "It answers."):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(content))

    return handler


class TestLLMProviderBasics:
    def test_generate_returns_content_and_metadata(self):
        response = _provider(_ok_handler()).generate([ChatMessage("user", "Hello")])

        assert response.content == "It answers."
        assert response.model == MODEL
        assert response.finish_reason == "stop"
        assert response.usage is not None
        assert response.usage.prompt_tokens == 10
        assert response.usage.total_tokens == 15
        assert response.duration_ms >= 0

    def test_request_payload_uses_configured_endpoint_and_key(self):
        sent: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            sent.update(
                {
                    "url": str(request.url),
                    "auth": request.headers.get("authorization"),
                    "body": json.loads(request.content),
                }
            )
            return httpx.Response(200, json=_chat_response("ok"))

        _provider(handler).generate([ChatMessage("system", "be strict"), ChatMessage("user", "Hi")])

        assert sent["url"].endswith("/chat/completions")
        assert sent["auth"] == "Bearer sk-test-secret"
        body = sent["body"]
        assert body["model"] == MODEL
        assert body["stream"] is False
        assert [m["role"] for m in body["messages"]] == ["system", "user"]

    def test_gemini_interactions_uses_documented_contract(self):
        sent: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            sent.update(
                {
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "body": json.loads(request.content),
                }
            )
            return httpx.Response(
                200,
                json={
                    "id": "interaction-test",
                    "status": "completed",
                    "model": "gemini-3.8-flash",
                    "usage": {
                        "total_tokens": 20,
                        "total_input_tokens": 8,
                        "total_output_tokens": 12,
                    },
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": "AI learns patterns."}],
                        }
                    ],
                },
            )

        provider = GeminiInteractionsLLMProvider(
            model_name="gemini-3.8-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key="gemini-test-secret",
            retry_policy=RetryPolicy(max_attempts=1),
            transport=httpx.MockTransport(handler),
        )
        result = provider.generate([ChatMessage("user", "Explain AI")])

        assert sent["url"].endswith("/v1beta/interactions")
        assert sent["headers"]["x-goog-api-key"] == "gemini-test-secret"
        assert sent["headers"]["api-revision"] == "2026-05-20"
        assert sent["body"] == {"model": "gemini-3.8-flash", "input": "USER:\nExplain AI"}
        assert result.content == "AI learns patterns."
        assert result.usage is not None
        assert result.usage.prompt_tokens == 8
        assert result.usage.completion_tokens == 12

    def test_gemini_interactions_structured_output(self):
        qa = QAOutput(
            answer="Ninety days written notice.",
            evidence_state=EvidenceState.DOCUMENT_GROUNDED,
            citations=[{"chunk_id": "chunk_18"}],
        ).model_dump_json()

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert "Return only valid JSON" in body["input"]
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "steps": [{"type": "model_output", "content": [{"type": "text", "text": qa}]}],
                },
            )

        provider = GeminiInteractionsLLMProvider(
            model_name="gemini-3.8-flash",
            base_url="https://ai.test/v1beta",
            api_key="gemini-test-secret",
            retry_policy=RetryPolicy(max_attempts=1),
            transport=httpx.MockTransport(handler),
        )
        result = provider.structured_generate(
            [ChatMessage("user", "What is the notice period?")], schema=QAOutput
        )
        assert result.answer == "Ninety days written notice."

    def test_structured_generate_validates_schema(self):
        qa = QAOutput(
            answer="Ninety days written notice.",
            evidence_state=EvidenceState.DOCUMENT_GROUNDED,
            citations=[{"chunk_id": "chunk_18"}],
        ).model_dump_json()

        handler = _ok_handler(content=qa)
        result = _provider(handler).structured_generate(
            [ChatMessage("user", "What is the notice period?")], schema=QAOutput
        )

        assert result.answer == "Ninety days written notice."
        assert result.evidence_state == EvidenceState.DOCUMENT_GROUNDED
        assert result.citations[0].chunk_id == "chunk_18"

    def test_structured_generate_accepts_json_code_fence(self):
        content = '```json\n{"answer": "x", "citations": []}\n```'
        result = _provider(_ok_handler(content=content)).structured_generate(
            [ChatMessage("user", "Hi")], schema=QAOutput
        )
        assert result.answer == "x"

    def test_structured_generate_rejects_invalid_output(self):
        invalid = json.dumps({"answer": "x", "evidence_state": "NOT-A-STATE"})
        provider = _provider(_ok_handler(content=invalid))
        with pytest.raises(LLMOutputValidationError):
            provider.structured_generate([ChatMessage("user", "Hi")], schema=QAOutput)

    def test_structured_generate_rejects_malformed_json(self):
        provider = _provider(_ok_handler(content="{not json"))
        with pytest.raises(LLMOutputValidationError):
            provider.structured_generate([ChatMessage("user", "Hi")], schema=QAOutput)

    def test_empty_completion_never_fabricates(self):
        handler = _ok_handler(content="")
        with pytest.raises(LLMProviderUnavailableError):
            _provider(handler).generate([ChatMessage("user", "Hi")])

    def test_empty_choices_never_fabricates(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": [], "model": MODEL, "usage": {}})

        with pytest.raises(LLMProviderUnavailableError):
            _provider(handler).generate([ChatMessage("user", "Hi")])

    def test_missing_messages_raises(self):
        with pytest.raises(LLMError):
            _provider(_ok_handler()).generate([])

    def test_parse_structured_content_never_accepts_garbage(self):
        with pytest.raises(LLMOutputValidationError):
            parse_structured_content("not json at all", QAOutput)


class TestRetryPolicy:
    def test_retries_transient_server_error_then_succeeds(self):
        clock = _FakeClock()
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 3:
                return httpx.Response(503, json={"error": "boom"})
            return httpx.Response(200, json=_chat_response("recovered"))

        provider = _provider(
            handler,
            policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.5),
            clock=clock,
        )
        result = provider.generate([ChatMessage("user", "Hi")])

        assert result.content == "recovered"
        assert attempts["n"] == 3
        assert clock.slept == [0.5, 1.0]

    def test_retries_exhausted_raises_controlled_error(self):
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            return httpx.Response(503, json={"error": "boom"})

        with pytest.raises(LLMProviderUnavailableError):
            _provider(handler, policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.1)).generate(
                [ChatMessage("user", "Hi")]
            )
        assert attempts["n"] == 2

    def test_no_retry_on_client_error(self):
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            return httpx.Response(400, json={"error": "bad"})

        with pytest.raises(LLMProviderUnavailableError):
            _provider(handler, policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.1)).generate(
                [ChatMessage("user", "Hi")]
            )
        assert attempts["n"] == 1

    def test_429_honours_retry_after_then_succeeds(self):
        clock = _FakeClock()
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] == 1:
                return httpx.Response(
                    429, json={"error": "slow down"}, headers={"Retry-After": "2"}
                )
            return httpx.Response(200, json=_chat_response("ok"))

        result = _provider(
            handler,
            policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.25),
            clock=clock,
        ).generate([ChatMessage("user", "Hi")])

        assert result.content == "ok"
        assert attempts["n"] == 2
        assert clock.slept == [2.0]

    def test_429_exhausted_raises_rate_limit(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "slow down"})

        with pytest.raises(LLMRateLimitError):
            _provider(handler, policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.1)).generate(
                [ChatMessage("user", "Hi")]
            )

    def test_connection_error_retries_then_fails_safely(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        with pytest.raises(LLMProviderUnavailableError):
            _provider(handler, policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.1)).generate(
                [ChatMessage("user", "Hi")]
            )

    def test_timeout_retries_then_raises_timeout_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow upstream")

        with pytest.raises(LLMTimeoutError):
            _provider(handler, policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.1)).generate(
                [ChatMessage("user", "Hi")]
            )


class TestRateLimit:
    def test_throttle_spaces_requests(self):
        clock = _FakeClock()
        inner = {"n": 0}

        def counted(request: httpx.Request) -> httpx.Response:
            inner["n"] += 1
            return httpx.Response(200, json=_chat_response("ok"))

        provider = _provider(counted, requests_per_minute=2, clock=clock)
        provider.generate([ChatMessage("user", "a")])
        provider.generate([ChatMessage("user", "b")])

        assert inner["n"] == 2
        assert sum(clock.slept) >= 30.0

    def test_zero_requests_per_minute_does_not_throttle(self):
        clock = _FakeClock()
        provider = _provider(_ok_handler(), requests_per_minute=0, clock=clock)
        provider.generate([ChatMessage("user", "a")])
        provider.generate([ChatMessage("user", "b")])
        assert clock.slept == []


class TestSafeFailure:
    def test_errors_never_leak_secrets_or_urls(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom")

        provider = _provider(
            handler,
            policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.0),
            api_key="sk-super-secret-value",
        )
        with pytest.raises(LLMProviderUnavailableError) as excinfo:
            provider.generate([ChatMessage("user", "Hi")])
        message = str(excinfo.value)
        assert "sk-super-secret-value" not in message
        assert URL not in message

    def test_build_llm_provider_missing_config_is_controlled(self):
        with pytest.raises(LLMProviderUnavailableError):
            build_llm_provider(provider="openai-compatible", model_name="", api_url=URL)
        with pytest.raises(LLMProviderUnavailableError):
            build_llm_provider(provider="openai-compatible", model_name=MODEL, api_url="")

    def test_build_llm_provider_unsupported_provider(self):
        with pytest.raises(ValueError):
            build_llm_provider(provider="closedai", model_name=MODEL, api_url=URL)

    def test_build_llm_provider_returns_configured_provider(self):
        provider = build_llm_provider(
            provider="openai-compatible",
            model_name=MODEL,
            api_url=URL,
            api_key="sk-x",
            max_attempts=2,
            requests_per_minute=5,
        )
        assert provider.model_name == MODEL


class TestProviderAbstraction:
    def test_base_provider_is_abstract(self):
        with pytest.raises(NotImplementedError):
            LLMProvider().generate([ChatMessage("user", "Hi")])

    def test_keys_never_exposed_through_api_contract(self, client):
        openapi = client.get("/api/v1/openapi.json").json()
        text = json.dumps(openapi)
        assert "llm_api_key" not in text
        assert "embedding_api_key" not in text
        assert "service_role_key" not in text
