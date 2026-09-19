"""OCR engine abstraction.

The pipeline never depends on a specific OCR vendor. ``OcrEngine`` is a small
protocol; ``TesseractOcrEngine`` is the shipped default (pytesseract). The
engine is injected so tests can substitute a deterministic fake — OCR quality
is never assumed.

Honesty rule (AGENT.md "no fake implementations" + FR-022): when the OCR
binary is unavailable the engine raises :class:`OcrUnavailableError` with a
clear, retryable message. The pipeline converts that into a FAILED document
with a recorded error; it never substitutes guessed text.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("app.processing.ocr")


class OcrUnavailableError(RuntimeError):
    """Raised when the OCR engine cannot run (missing dependency or binary)."""


@dataclass(frozen=True)
class OcrResult:
    """Text and confidence returned by an OCR engine.

    ``confidence`` is 0.0-1.0 or ``None`` when the engine cannot quantify it.
    """

    text: str
    confidence: float | None = None


class OcrEngine(Protocol):
    """Anything that converts raw image bytes into text."""

    def ocr(self, image_bytes: bytes) -> OcrResult: ...


class TesseractOcrEngine:
    """pytesseract-backed engine wrapping the system ``tesseract`` binary.

    ``tesseract_cmd`` may be provided explicitly (else ``OCR_TESSERACT_CMD``,
    else the tesseract binary on ``PATH``). The binary is resolved lazily at
    call time so tests can construct the engine without tesseract installed.
    """

    def __init__(
        self,
        *,
        tesseract_cmd: str | None = None,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._tesseract_cmd = tesseract_cmd or os.environ.get("OCR_TESSERACT_CMD")
        self.confidence_threshold = confidence_threshold

    # -- OcrEngine -------------------------------------------------------------

    def ocr(self, image_bytes: bytes) -> OcrResult:
        try:
            import pytesseract  # type: ignore[import-untyped]
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - depends on host env
            logger.warning("OCR support packages are not installed")
            raise OcrUnavailableError(
                "OCR support is not installed (pip install pytesseract pillow)."
            ) from exc

        if self._tesseract_cmd:
            if shutil.which(self._tesseract_cmd) is None:
                raise self._binary_missing()
            pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError as exc:
            raise self._binary_missing() from exc

        # Never point OCR at a raw, untrusted byte stream: decode the image so
        # only supported pixel formats reach the engine.
        try:
            from io import BytesIO

            image: Image.Image = Image.open(BytesIO(image_bytes))
            image.load()
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT, lang="eng"
            )
        except OcrUnavailableError:
            raise
        except Exception as exc:  # OCR failures are runtime conditions, not bugs
            logger.error("tesseract OCR failed", exc_info=True)
            raise OcrUnavailableError(f"OCR failure: {type(exc).__name__}.") from exc

        text = self._join_word_boxes(data)
        confidence = self._mean_confidence(data)
        return OcrResult(text=text, confidence=confidence)

    # -- helpers ---------------------------------------------------------------

    def _binary_missing(self) -> OcrUnavailableError:
        cmd = self._tesseract_cmd or "tesseract (on PATH)"
        return OcrUnavailableError(
            f"Tesseract OCR binary is not available ({cmd}). "
            "Install tesseract and set OCR_TESSERACT_CMD, then retry processing."
        )

    @staticmethod
    def _join_word_boxes(data: dict[str, list[object]]) -> str:
        """Rebuild text from per-word OCR data, using line/paragraph breaks.

        Only words with ``conf`` above 0 are treated as real text; the others
        are dropped rather than guessed, which feeds the confidence calculation.
        """
        text = data.get("text", [])
        conf = _as_int_list(data.get("conf", []))
        line_nums = _as_int_list(data.get("line_num", []))
        block_nums = _as_int_list(data.get("block_num", []))

        lines: list[str] = []
        current_line: list[str] = []
        current_line_num: object = None
        current_block: object = None

        for word, word_conf, line_num, block_num in zip(
            text, conf, line_nums, block_nums, strict=False
        ):
            if not isinstance(word, str) or word_conf <= 0:
                continue
            if line_num != current_line_num:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = []
                current_line_num = line_num
                current_block = block_num
            elif current_block is not None and block_num != current_block:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = []
                current_block = block_num
            current_line.append(word)

        if current_line:
            lines.append(" ".join(current_line))
        return "\n".join(lines)

    @staticmethod
    def _mean_confidence(data: dict[str, list[object]]) -> float | None:
        conf = _as_int_list(data.get("conf", []))
        valid = [value for value in conf if 0 <= value <= 100]
        if not valid:
            return None
        return round(sum(valid) / len(valid) / 100.0, 4)


def _as_int_list(values: list[object]) -> list[int]:
    result: list[int] = []
    for value in values:
        try:
            result.append(int(str(value)))
        except (TypeError, ValueError):
            result.append(-1)
    return result