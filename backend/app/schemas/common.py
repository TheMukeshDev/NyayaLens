"""Shared API schemas: consistent success and error envelopes."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Body of the standard error envelope."""

    code: str
    message: str
    details: list[str] | None = None


class ErrorResponse(BaseModel):
    """Standard error response (never leaks internals)."""

    success: bool = False
    error: ErrorDetail


class SuccessResponse(BaseModel, Generic[T]):  # noqa: UP046
    """Standard success envelope defined in the API specification."""

    success: bool = True
    data: T | None = Field(default=None)
    message: str | None = None
