"""Consistent API error handling.

Every error returned to clients uses the same envelope (docs/03_TECH/API-Specification.md §3):

    {
      "success": false,
      "error": {
        "code": "DOCUMENT_NOT_FOUND",
        "message": "Document not found."
      }
    }

For validation failures the ``error`` object additionally carries a
``details`` list. Responses never expose stack traces, database errors,
filesystem paths or secrets.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_request_id

logger = logging.getLogger("app.errors")


class ErrorCodes:
    """Canonical machine-readable error codes (docs/03_TECH/API-Specification.md)."""

    AUTH_REQUIRED = "AUTH_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    FORBIDDEN = "FORBIDDEN"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_ACCESS_DENIED = "DOCUMENT_ACCESS_DENIED"
    INVALID_FILE = "INVALID_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    MALWARE_DETECTED = "MALWARE_DETECTED"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    STORAGE_ERROR = "STORAGE_ERROR"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_CITATION = "INVALID_CITATION"
    COMPARISON_FAILED = "COMPARISON_FAILED"
    COMPARISON_NOT_FOUND = "COMPARISON_NOT_FOUND"
    ACTION_CENTER_FAILED = "ACTION_CENTER_FAILED"
    ACTION_NOT_FOUND = "ACTION_NOT_FOUND"
    REPORT_GENERATION_FAILED = "REPORT_GENERATION_FAILED"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    BAD_REQUEST = "BAD_REQUEST"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def error_payload(code: str, message: str, details: list[str] | None = None) -> dict[str, Any]:
    """Build the standard error envelope."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"success": False, "error": error}


class ApiError(Exception):
    """Base application error serialized with the standard error envelope."""

    default_status_code = 500
    default_code = ErrorCodes.INTERNAL_ERROR
    default_message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status_code = status_code if status_code is not None else self.default_status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(ApiError):
    default_status_code = 404
    default_code = ErrorCodes.NOT_FOUND
    default_message = "The requested resource could not be found."


class DocumentNotFoundError(NotFoundError):
    default_code = ErrorCodes.DOCUMENT_NOT_FOUND
    default_message = "The requested document could not be found."


class ComparisonNotFoundError(NotFoundError):
    default_code = ErrorCodes.COMPARISON_NOT_FOUND
    default_message = "The requested comparison could not be found."


class ComparisonError(ApiError):
    default_status_code = 400
    default_code = ErrorCodes.COMPARISON_FAILED
    default_message = "A comparison requires two distinct documents."


class ActionNotFoundError(NotFoundError):
    default_code = ErrorCodes.ACTION_NOT_FOUND
    default_message = "The requested action could not be found."


class ReportNotFoundError(NotFoundError):
    default_code = ErrorCodes.REPORT_NOT_FOUND
    default_message = "The requested report could not be found."


class ActionCenterError(ApiError):
    default_status_code = 400
    default_code = ErrorCodes.ACTION_CENTER_FAILED
    default_message = "The Action Center could not be generated for this document."


class ReportGenerationError(ApiError):
    default_status_code = 400
    default_code = ErrorCodes.REPORT_GENERATION_FAILED
    default_message = "The review report could not be generated."


class UnauthorizedError(ApiError):
    default_status_code = 401
    default_code = ErrorCodes.AUTH_REQUIRED
    default_message = "Authentication is required."


class InvalidCredentialsError(ApiError):
    default_status_code = 401
    default_code = ErrorCodes.INVALID_CREDENTIALS
    default_message = "Invalid email or password."


class ForbiddenError(ApiError):
    default_status_code = 403
    default_code = ErrorCodes.FORBIDDEN
    default_message = "You do not have permission to perform this action."


class DocumentAccessDeniedError(ForbiddenError):
    default_code = ErrorCodes.DOCUMENT_ACCESS_DENIED
    default_message = "You do not have access to this document."


class ConflictError(ApiError):
    default_status_code = 409
    default_code = ErrorCodes.CONFLICT
    default_message = "The request conflicts with the current state of the resource."


class DuplicateDocumentError(ConflictError):
    default_code = ErrorCodes.DUPLICATE_DOCUMENT
    default_message = "A document with identical content is already uploaded."


class InvalidFileError(ApiError):
    default_status_code = 400
    default_code = ErrorCodes.INVALID_FILE
    default_message = "The uploaded file is invalid."


class FileTooLargeError(ApiError):
    default_status_code = 413
    default_code = ErrorCodes.FILE_TOO_LARGE
    default_message = "The uploaded file is too large."


class UnsupportedFileTypeError(ApiError):
    default_status_code = 415
    default_code = ErrorCodes.UNSUPPORTED_FILE_TYPE
    default_message = "Unsupported file type. Supported types: PDF, DOCX, JPG, PNG."


class ServiceUnavailableError(ApiError):
    default_status_code = 503
    default_code = ErrorCodes.SERVICE_UNAVAILABLE
    default_message = "Service is unavailable."


class StorageError(ApiError):
    """Document object storage is unavailable.

    Raised by storage implementations; the message is intentionally generic so
    no storage backend details (paths, keys, credentials) leak to clients.
    """

    default_status_code = 503
    default_code = ErrorCodes.STORAGE_ERROR
    default_message = "Document storage is currently unavailable."


_HTTP_STATUS_TO_CODE = {
    400: ErrorCodes.BAD_REQUEST,
    401: ErrorCodes.AUTH_REQUIRED,
    403: ErrorCodes.FORBIDDEN,
    404: ErrorCodes.NOT_FOUND,
    405: ErrorCodes.METHOD_NOT_ALLOWED,
    409: ErrorCodes.CONFLICT,
    413: ErrorCodes.FILE_TOO_LARGE,
    422: ErrorCodes.VALIDATION_ERROR,
    429: ErrorCodes.RATE_LIMITED,
    503: ErrorCodes.SERVICE_UNAVAILABLE,
}

_HTTP_STATUS_MESSAGE = {
    400: "The request is invalid.",
    401: "Authentication is required.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource could not be found.",
    405: "This method is not allowed for the requested resource.",
    409: "The request conflicts with the current state of the resource.",
    413: "The uploaded file is too large.",
    422: "Request validation failed.",
    429: "Too many requests. Please try again later.",
    503: "Service is unavailable.",
}


def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    extra = {
        "error_code": exc.code,
    }
    request_id = get_request_id()
    if request_id:
        extra["request_id"] = request_id
    logger.info(
        "api error",
        extra={**extra, "method": request.method, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.details),
    )


def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_STATUS_TO_CODE.get(exc.status_code, ErrorCodes.INTERNAL_ERROR)
    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else _HTTP_STATUS_MESSAGE.get(
            exc.status_code, _HTTP_STATUS_MESSAGE.get(500, ErrorCodes.INTERNAL_ERROR)
        )
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload(code, message))


def _format_validation_details(errors: Sequence[Any]) -> list[str]:
    details: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", []) if part not in (None, ""))
        message = error.get("msg", "Invalid value.")
        details.append(f"{location}: {message}" if location else message)
    return details[:20]


def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = _format_validation_details(exc.errors())
    return JSONResponse(
        status_code=422,
        content=error_payload(ErrorCodes.VALIDATION_ERROR, "Request validation failed.", details),
    )


def _handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    extra = {"method": request.method, "path": request.url.path}
    request_id = get_request_id()
    if request_id:
        extra["request_id"] = request_id
    logger.error("unhandled application error", exc_info=exc, extra=extra)
    return JSONResponse(
        status_code=500,
        content=error_payload(ErrorCodes.INTERNAL_ERROR, "An unexpected error occurred."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers that produce the standard error envelope."""
    app.add_exception_handler(ApiError, cast(Any, _handle_api_error))
    app.add_exception_handler(StarletteHTTPException, cast(Any, _handle_http_exception))
    app.add_exception_handler(RequestValidationError, cast(Any, _handle_validation_error))
    app.add_exception_handler(Exception, cast(Any, _handle_unhandled_exception))
