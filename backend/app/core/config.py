"""Application configuration.

Values are read from the environment, optionally from a ``.env`` file in the
backend root. Only ``.env.example`` is committed; real secrets must never be
committed.

The backend is Supabase-native: authentication is verified against Supabase
Auth JWTs and persistence uses the Supabase client. There is no local
PostgreSQL and no SQLAlchemy/Alembic-managed schema.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables.

    Environment variables are read case-insensitively. ``SUPABASE_DB_URL`` /
    ``DATABASE_URL`` are optional and used only by external tooling that needs
    raw SQL access (e.g. the Supabase CLI); application persistence goes
    through the Supabase client.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "NyayaLens API"
    app_version: str = "0.1.0"
    api_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Supabase project URL (shared with frontend).
    supabase_url: str = ""

    # Publishable (anon) key — safe for user-scoped, RLS-protected requests.
    supabase_anon_key: str = ""

    # Service-role key — bypasses RLS. NEVER a frontend/NEXT_PUBLIC_ variable.
    supabase_service_role_key: str = ""

    # JWT signing secret used by Supabase Auth to sign access tokens. The
    # backend verifies incoming bearer tokens offline against this secret.
    supabase_jwt_secret: str = ""

    # Optional raw connection strings for external SQL tooling only.
    supabase_db_url: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_DB_URL", "DATABASE_URL", "supabase_db_url"),
    )
    supabase_db_direct_url: str | None = None

    # Document upload limits (US-003).
    max_upload_size_mb: int = 20
    allowed_upload_extensions: str = "pdf,docx,jpg,jpeg,png"

    # Supabase Storage: one private bucket for legal documents. Must never be
    # public; browser access is issued server-side as short-lived signed URLs.
    storage_bucket: str = "legal-documents"
    signed_url_expires_seconds: int = 900

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    frontend_url: str | None = None
    backend_url: str | None = None

    # Shared secret guarding the internal (non-user-facing) endpoints, notably
    # the scheduled document-processing drain. Vercel sends it automatically as
    # `Authorization: Bearer $CRON_SECRET` on cron invocations. It is never a
    # NEXT_PUBLIC_ variable, and the endpoints stay disabled when it is unset so
    # they can never become an unauthenticated privileged surface.
    cron_secret: str = ""

    # AI embeddings + retrieval (docs/04_AI/AI-Architecture.md §16,
    # docs/04_AI/RAG-Architecture.md §6-§12). The vector dimension is NOT
    # hardcoded in the database until the model is configured: see
    # public.ensure_embedding_index(dim) and the embeddings migration.
    embedding_provider: str = "deterministic"
    embedding_model: str = "nyayalens/embeddings-deterministic-v1"
    # Optional. Deterministic provider default when unset; other providers may
    # declare their own dimension. Used to confirm the vector index dimension.
    embedding_dimension: int | None = None
    embedding_batch_size: int = 64
    # OpenAI-compatible embeddings endpoint (provider = "openai-compatible").
    embedding_api_url: str = ""
    embedding_api_key: str = ""

    # Embedding provider call policy (server-side only; keys never reach the
    # browser). Applied to OpenAI-compatible embeddings providers.
    embedding_request_timeout_seconds: float = 30.0
    embedding_max_attempts: int = 3
    embedding_retry_base_delay_seconds: float = 1.0
    embedding_retry_max_delay_seconds: float = 10.0
    embedding_max_requests_per_minute: int = 0  # 0 = unlimited

    # Initial retrieval target: top 8-12 chunks (RAG-Architecture.md §9).
    retrieval_top_k: int = 10
    # Relevance floor for candidate evidence (type + tune per model).
    retrieval_min_similarity: float = 0.35

    # AI generation (docs/04_AI/AI-Architecture.md §9-§15). The LLM provider is
    # an internal abstraction; the model is configured per environment and never
    # hardcoded. API keys are backend-only and must never be exposed to the
    # frontend (like the Supabase service-role key).
    llm_provider: str = "openai-compatible"
    # Set false for hosted demos or quota outages; AI features abstain without
    # making upstream model requests.
    llm_enabled: bool = True
    llm_model: str = ""
    # OpenAI-compatible chat-completions endpoint (provider = "openai-compatible").
    llm_api_url: str = ""
    llm_api_key: str = ""

    # LLM call policy (backend-only): timeout, retry policy and client-side rate
    # limiting. Request budgets protect cost and the upstream quota
    # (AI-Architecture.md §21); 0 requests/minute means unlimited.
    llm_request_timeout_seconds: float = 60.0
    llm_max_attempts: int = 3
    llm_retry_base_delay_seconds: float = 1.0
    llm_retry_max_delay_seconds: float = 10.0
    llm_retry_jitter_seconds: float = 0.0
    llm_max_requests_per_minute: int = 0

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"development", "testing", "production"}:
            raise ValueError("environment must be development, testing or production")
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be a valid logging level")
        return value

    @field_validator("max_upload_size_mb")
    @classmethod
    def _validate_max_upload(cls, value: int) -> int:
        if value < 1 or value > 1000:
            raise ValueError("max_upload_size_mb must be between 1 and 1000")
        return value

    @field_validator("embedding_provider")
    @classmethod
    def _validate_embedding_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"deterministic", "openai-compatible"}:
            raise ValueError(
                "embedding_provider must be 'deterministic' or 'openai-compatible'"
            )
        return value

    @field_validator("embedding_dimension")
    @classmethod
    def _validate_embedding_dimension(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("embedding_dimension must be a positive integer")
        return value

    @field_validator("retrieval_top_k")
    @classmethod
    def _validate_retrieval_top_k(cls, value: int) -> int:
        if value < 8 or value > 12:
            raise ValueError("retrieval_top_k must be between 8 and 12")
        return value

    @field_validator("retrieval_min_similarity")
    @classmethod
    def _validate_retrieval_min_similarity(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("retrieval_min_similarity must be between 0 and 1")
        return value

    @field_validator("llm_provider")
    @classmethod
    def _validate_llm_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"openai-compatible"}:
            raise ValueError("llm_provider must be 'openai-compatible'")
        return value

    @field_validator("llm_max_attempts")
    @classmethod
    def _validate_llm_max_attempts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("llm_max_attempts must be at least 1")
        return value

    @field_validator("llm_max_requests_per_minute")
    @classmethod
    def _validate_llm_rpm(cls, value: int) -> int:
        if value < 0:
            raise ValueError("llm_max_requests_per_minute must not be negative")
        return value

    @field_validator("embedding_max_attempts")
    @classmethod
    def _validate_embedding_max_attempts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("embedding_max_attempts must be at least 1")
        return value

    @field_validator("embedding_max_requests_per_minute")
    @classmethod
    def _validate_embedding_rpm(cls, value: int) -> int:
        if value < 0:
            raise ValueError("embedding_max_requests_per_minute must not be negative")
        return value

    @model_validator(mode="after")
    def _validate_provider_delays(self) -> Settings:
        for prefix in ("embedding", "llm"):
            base = getattr(self, f"{prefix}_retry_base_delay_seconds")
            maximum = getattr(self, f"{prefix}_retry_max_delay_seconds")
            timeout = getattr(self, f"{prefix}_request_timeout_seconds")
            for name, value in (
                (f"{prefix}_retry_base_delay_seconds", base),
                (f"{prefix}_retry_max_delay_seconds", maximum),
                (f"{prefix}_request_timeout_seconds", timeout),
            ):
                if value < 0:
                    raise ValueError(f"{name} must not be negative")
            if maximum < base:
                raise ValueError(
                    f"{prefix}_retry_max_delay_seconds must be >= "
                    f"{prefix}_retry_base_delay_seconds"
                )
        return self

    @model_validator(mode="after")
    def _require_openai_compatible_url(self) -> Settings:
        if self.embedding_provider == "openai-compatible" and not self.embedding_api_url:
            raise ValueError(
                "embedding_provider 'openai-compatible' requires EMBEDDING_API_URL"
            )
        return self

    @model_validator(mode="after")
    def _require_production_credentials(self) -> Settings:
        if self.is_production:
            missing = [
                name
                for name, value in {
                    "SUPABASE_URL": self.supabase_url,
                    "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
                    "SUPABASE_JWT_SECRET": self.supabase_jwt_secret,
                "CRON_SECRET": self.cron_secret,
                }.items()
                if not value or value.startswith("YOUR_")
            ]
            if missing:
                raise ValueError(f"production requires configured: {', '.join(missing)}")
        return self

    @model_validator(mode="after")
    def _require_production_ai_config(self) -> Settings:
        if not self.is_production or not self.llm_enabled:
            return self
        missing = [
            name
            for name, value in {
                "LLM_MODEL": self.llm_model,
                "LLM_API_URL": self.llm_api_url,
                "LLM_API_KEY": self.llm_api_key,
            }.items()
            if not value or value.startswith("YOUR_")
        ]
        if self.embedding_provider == "openai-compatible":
            for name, value in {
                "EMBEDDING_MODEL": self.embedding_model,
                "EMBEDDING_API_URL": self.embedding_api_url,
                "EMBEDDING_API_KEY": self.embedding_api_key,
            }.items():
                if not value or value.startswith("YOUR_"):
                    missing.append(name)
        if missing:
            raise ValueError(f"production requires configured: {', '.join(missing)}")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production


settings = Settings()
