"""Server-side upload validation: file type, file size, filename sanitization.

Uploaded files are untrusted (docs/05_SECURITY/SECURITY-Architecture.md §3).
Validation here is the security boundary — it must never be relaxed based on
client-supplied metadata:

* The declared extension must be in the supported set.
* The magic bytes of the content must match the declared type (so a renamed
  ``.exe`` or a spoofed Content-Type header is rejected).
* The size must be within the configured limit.
* The filename is sanitized before it is stored or echoed anywhere.

Supported MVP types: PDF, DOCX, JPG, PNG.
No file content is ever logged here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from app.core.config import settings
from app.core.errors import ErrorCodes

# extension -> (canonical MIME type, magic bytes the content must start with)
_FILE_TYPES: Final[dict[str, tuple[str, bytes]]] = {
    "pdf": ("application/pdf", b"%PDF-"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"PK\x03\x04",
    ),
    "jpg": ("image/jpeg", b"\xff\xd8\xff"),
    "jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    "png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}

_ALLOWED_MIME_TYPES: Final = {info[0] for info in _FILE_TYPES.values()}

# Characters that are dangerous in filenames (path separators, quotes, etc.).
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/<>:"|?*\x00-\x1f\x7f]+')

_MAX_FILENAME_LENGTH = 200

_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


@dataclass(frozen=True)
class ValidationOutcome:
    """Result of validating an uploaded file.

    When ``valid`` is ``False`` the caller should return an error using
    ``error_code`` / ``status_code`` / ``message``.
    """

    valid: bool
    mime_type: str | None = None
    extension: str | None = None
    error_code: str | None = None
    status_code: int | None = None
    message: str | None = None


def supported_mime_types() -> set[str]:
    """Return the set of MIME types the backend accepts for uploads."""
    return _ALLOWED_MIME_TYPES


def _configured_extensions() -> set[str]:
    return {
        ext.strip().lower() for ext in settings.allowed_upload_extensions.split(",") if ext.strip()
    }


def sanitize_filename(raw: str | None) -> str:
    """Return a safe basename derived from *raw*.

    Removes any path components, control characters, and characters dangerous
    in filenames/headers; collapses excessive length while preserving the
    extension; and neutralizes names that would be meaningless or reserved.
    """
    if not raw:
        return "document"

    # Keep only the basename (strip any client-supplied path, both separators).
    name = raw.replace("\\", "/").split("/")[-1]
    name = _UNSAFE_FILENAME_CHARS.sub("", name).strip(" .")
    if not name:
        return "document"

    reserved_stem = name if "." not in name else name.rsplit(".", 1)[0]
    if reserved_stem.upper() in _WINDOWS_RESERVED:
        name = "document-" + name

    if len(name) > _MAX_FILENAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if ext and len(ext) <= 10:
            name = stem[: _MAX_FILENAME_LENGTH - len(ext) - 1] + dot + ext
        else:
            name = name[:_MAX_FILENAME_LENGTH]

    return name or "document"


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _invalid(code: str, status_code: int, message: str) -> ValidationOutcome:
    return ValidationOutcome(
        valid=False,
        error_code=code,
        status_code=status_code,
        message=message,
    )


def validate_upload_declaration(filename: str, size_bytes: int) -> ValidationOutcome:
    """Validate the name and size a client declares *before* sending any bytes.

    Used by the direct-to-storage upload flow: the API signs an upload URL from
    this declaration instead of buffering the file. The declaration is a cheap
    pre-check only -- the authoritative type/size check is the magic-byte
    validation :func:`validate_uploaded_file` runs once the object is stored.
    """
    if not filename:
        return _invalid(ErrorCodes.INVALID_FILE, 400, "A file is required.")

    extension = _extension_of(sanitize_filename(filename))
    if extension not in _FILE_TYPES or extension not in _configured_extensions():
        return _invalid(
            ErrorCodes.UNSUPPORTED_FILE_TYPE,
            415,
            "Unsupported file type. Supported types: PDF, DOCX, JPG, PNG.",
        )

    if size_bytes <= 0:
        return _invalid(ErrorCodes.INVALID_FILE, 400, "The uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return _invalid(
            ErrorCodes.FILE_TOO_LARGE,
            413,
            f"The uploaded file exceeds the maximum allowed size of "
            f"{settings.max_upload_size_mb} MB.",
        )

    mime_type, _magic = _FILE_TYPES[extension]
    return ValidationOutcome(valid=True, mime_type=mime_type, extension=extension)


def validate_uploaded_file(filename: str, content: bytes) -> ValidationOutcome:
    """Validate an uploaded file against type, magic bytes and size limits.

    Filename *must* already be the raw client-supplied name when provided by
    the caller; validation computes its own sanitized basename so a client
    cannot smuggle path components past the type check.
    """
    if not filename:
        return _invalid(ErrorCodes.INVALID_FILE, 400, "A file is required.")

    sanitized = sanitize_filename(filename)
    extension = _extension_of(sanitized)
    allowed = _configured_extensions()

    if extension not in _FILE_TYPES or extension not in allowed:
        return _invalid(
            ErrorCodes.UNSUPPORTED_FILE_TYPE,
            415,
            "Unsupported file type. Supported types: PDF, DOCX, JPG, PNG.",
        )

    if not content:
        return _invalid(ErrorCodes.INVALID_FILE, 400, "The uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        return _invalid(
            ErrorCodes.FILE_TOO_LARGE,
            413,
            f"The uploaded file exceeds the maximum allowed size of "
            f"{settings.max_upload_size_mb} MB.",
        )

    mime_type, magic = _FILE_TYPES[extension]
    if not content.startswith(magic):
        return _invalid(
            ErrorCodes.INVALID_FILE,
            400,
            "The file content does not match its declared file type.",
        )

    return ValidationOutcome(
        valid=True,
        mime_type=mime_type,
        extension=extension,
    )
