"""Deterministic clause detection within sections (heuristic, not AI).

A clause is a numbered/lettered item inside a section (e.g. ``3.1``, ``(b)``,
``Clause 4.2``). Detection is structural — boundaries are list-item markers,
and the ``clause_type`` is a keyword match on the item's own heading text, not
a judgment about the clause's legal significance (FR-007; AI-Architecture §9).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.document_processing.models import LineRef

# Order matters: the most specific markers are matched first so that sub-clause
# numbers win over the (less specific) plain-number pattern.
_MARKERS = [
    re.compile(r"^\s*CLAUSE\s+([0-9]+(?:\.[0-9]+)+)\s*[-–—:.]?\s*(.*?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([0-9]+(?:\.[0-9]+)+)[.)]?\s+(.+?)\s*$"),
    re.compile(r"^\s*\(([0-9]+)\)\s+(.+?)\s*$"),
    re.compile(r"^\s*\(([a-z])\)\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([0-9]+)[.)]\s+(.+?)\s*$"),
]

_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "TERMINATION": ("terminat",),
    "COMPENSATION": ("compensat", "salar", "remunerat", "wage"),
    "PAYMENT": ("payment",),
    "CONFIDENTIALITY": ("confidential", "non-disclosure", "nondisclosure", "non disclosure"),
    "NON_COMPETE": ("non-compete", "non compete", "noncompete"),
    "INTELLECTUAL_PROPERTY": ("intellectual", "proprietary", "copyright", "trademark", "patent"),
    "LIABILITY": ("liabilit",),
    "INDEMNIFICATION": ("indemnif",),
    "DISPUTE_RESOLUTION": ("dispute", "arbitration", "litigation", "jurisdiction"),
    "GOVERNING_LAW": ("governing law",),
    "NOTICE": ("notice",),
    "LEAVE": ("leave",),
    "PROBATION": ("probation",),
    "RENEWAL": ("renew",),
    "DATA_PROTECTION": ("data protection", "personal data", "privacy"),
    "DEFAULT": ("default", "breach"),
}


@dataclass(frozen=True)
class ClauseMarker:
    """A detected clause-boundary marker."""

    line_index: int
    number: str | None
    title: str | None


def detect_clause_markers(lines: list[LineRef], start: int, end: int) -> list[ClauseMarker]:
    """Return clause-boundary line indices for ``lines[start:end]``.

    A marker is accepted at the start of a block (after a blank line) or as a
    continuation of a run of items at the same numbering depth (``1.1``,
    ``1.2``...). Deeper markers can nest inside shallower ones; a change in
    depth without a blank line is treated as body text rather than a marker.
    """
    markers: list[ClauseMarker] = []
    prev_blank = True
    prev_depth: int | None = None
    for index in range(start, end):
        text = lines[index].text.strip()
        if not text:
            prev_blank = True
            prev_depth = None
            continue
        parsed = _parse_marker(text)
        if parsed is not None:
            depth = _marker_depth(parsed[0])
            if prev_blank or (prev_depth is not None and depth == prev_depth):
                markers.append(ClauseMarker(line_index=index, number=parsed[0], title=parsed[1]))
                prev_depth = depth
            else:
                prev_depth = None
        else:
            prev_depth = None
        prev_blank = False
    return markers


def _marker_depth(number: str) -> int:
    """Return the nesting depth of a marker number (``1.1`` -> 2, ``9`` -> 1)."""
    if any(char.isalpha() for char in number):
        return 1
    return number.count(".") + 1


def _parse_marker(text: str) -> tuple[str, str | None] | None:
    for pattern in _MARKERS:
        match = pattern.match(text)
        if match:
            number = match.group(1) or ""
            title = _short_title(match.group(2).strip().rstrip(".:;"))
            return number, title or None
    return None


def _short_title(raw: str) -> str:
    """Trim a trailing sentence from an item title when it reads like a title.

    ``1.1 Restrictions. The Employee shall ...`` keeps just ``Restrictions``,
    while genuine prose (``Confidentiality. Data will be handled...``) is
    truncated at the first sentence boundary only when the first segment is
    short enough to plausibly be a heading.
    """
    match = re.match(r"^(.{1,80}?)[.]\s+([A-Z])", raw)
    return match.group(1).strip() if match else raw.strip()


def clause_type_from_title(title: str | None) -> str | None:
    """Map a clause heading to a controlled type via keywords (or ``None``)."""
    if not title:
        return None
    lowered = title.lower()
    for clause_type, keywords in _TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return clause_type
    return None