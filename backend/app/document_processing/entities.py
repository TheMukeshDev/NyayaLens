"""Deterministic entity extraction (dates, amounts, parties, references).

Entities are recognized from surface patterns only. This is extraction, not
interpretation: nothing here evaluates the meaning, legality, or risk of a
document (docs/01_PRODUCT/FEATURE-REQUIREMENTS.md FR-006; the AI layer,
``app/ai``, is what performs judgment-based entity linking later).

Named-person/organization NER is intentionally out of scope here (see
AI-Architecture.md §17, "Entity extraction: Yes/Hybrid").
"""

from __future__ import annotations

import re
from datetime import datetime

from app.document_processing.models import ExtractedEntity

_MONTHS = [
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
]

_DAY = r"(?:3[01]|[12][0-9]|0?[1-9])"
_MONTH_NAME = r"(?:" + "|".join(_MONTHS) + r")"
_YEAR = r"(?:19|20)[0-9]{2}"

_MONTH_FIRST = re.compile(
    rf"\b({_MONTH_NAME})\s+({_DAY})(?:st|nd|rd|th)?,?\s*(?:,?\s*)({_YEAR})\b",
    re.IGNORECASE,
)
_DAY_FIRST = re.compile(
    rf"\b({_DAY})(?:st|nd|rd|th)?\s+({_MONTH_NAME})\s*,?\s*({_YEAR})\b", re.IGNORECASE
)
_ISO_DATE = re.compile(rf"\b({_YEAR})[-/](0?[1-9]|1[0-2])[-/]({_DAY})\b")
_SLASH_DATE = re.compile(rf"\b({_DAY})[-/](0?[1-9]|1[0-2])[-/]({_YEAR})\b")

_SYMBOL_AMOUNT = re.compile(r"[₹$€£]\s?\d{1,3}(?:[,\d]{3})*(?:\.\d{1,2})?")
_NAMED_AMOUNT = re.compile(
    r"\b(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(usd|inr|eur|gbp|rupees?|dollars?|euros?)\b",
    re.IGNORECASE,
)

_PARTY = re.compile(
    r"\b(?:Party\s+[A-F]|Employer|Employee|Client|Vendor|Customer|Service\s+Provider"
    r"|Landlord|Tenant|Lessor|Lessee)\b",
    re.IGNORECASE,
)

_WORD_REF = re.compile(
    r"\b(?:Section|Clause|Subclause|Sub[ -]Clause)\s+([0-9]+(?:\.[0-9]+)*)\b", re.IGNORECASE
)
_REF_UNNAMED = re.compile(r"\b([0-9]{1,2}\.[0-9]{1,2})\b")


def extract_entities(text: str, *, page: int | None) -> list[ExtractedEntity]:
    """Extract entities from *text*, deduplicated in first-seen order."""
    entities: list[ExtractedEntity] = []
    seen: set[tuple[str, str]] = set()

    def push(entity_type: str, value: str, normalized: str | None) -> None:
        key = (entity_type, normalized or value)
        if key not in seen:
            entities.append(
                ExtractedEntity(
                    type=entity_type, value=value, normalized=normalized, page=page
                )
            )
            seen.add(key)

    for entity in _dates_from(text):
        push(entity.type, entity.value, entity.normalized)
    for entity in _amounts_from(text):
        push(entity.type, entity.value, entity.normalized)
    for entity in _parties_from(text):
        push(entity.type, entity.value, entity.normalized)
    for entity in _references_from(text):
        push(entity.type, entity.value, entity.normalized)
    return entities


def _dates_from(text: str) -> list[ExtractedEntity]:
    found: list[ExtractedEntity] = []

    def push(value: str, iso: str | None) -> None:
        found.append(ExtractedEntity(type="DATE", value=value, normalized=iso))

    for month, day, year in _MONTH_FIRST.findall(text):
        push(f"{month.title()} {_strip_ordinal(day)}, {year}", _iso(year, _month_num(month), day))
    for day, month, year in _DAY_FIRST.findall(text):
        push(f"{_strip_ordinal(day)} {month.title()} {year}", _iso(year, _month_num(month), day))
    for year, month, day in _ISO_DATE.findall(text):
        value = f"{year}-{int(month):02d}-{int(day):02d}"
        push(value, _iso(year, month, day))
    for day, month, year in _SLASH_DATE.findall(text):
        push(f"{day}/{month}/{year}", None)
    return found


def _amounts_from(text: str) -> list[ExtractedEntity]:
    found: list[ExtractedEntity] = []
    for match in _SYMBOL_AMOUNT.findall(text):
        digits = "".join(re.findall(r"\d", match))
        found.append(ExtractedEntity(type="AMOUNT", value=match, normalized=digits))
    for number, currency in _NAMED_AMOUNT.findall(text):
        found.append(
            ExtractedEntity(
                type="AMOUNT",
                value=f"{number} {currency.upper()}",
                normalized=re.sub(r"[^\d]", "", number),
            )
        )
    return found


def _parties_from(text: str) -> list[ExtractedEntity]:
    found: list[ExtractedEntity] = []
    for match in _PARTY.findall(text):
        found.append(
            ExtractedEntity(type="PARTY", value=match, normalized=_party_key(match))
        )
    return found


def _references_from(text: str) -> list[ExtractedEntity]:
    found: list[ExtractedEntity] = []
    word_refs = _WORD_REF.findall(text)
    for match in word_refs:
        found.append(
            ExtractedEntity(type="CROSS_REFERENCE", value=match, normalized=match)
        )
    # Bare sub-clause numbers ("3.1") are only treated as references when the
    # text already uses explicit Section/Clause wording, which avoids mistaking
    # decimal amounts for clause references.
    if word_refs:
        for match in _REF_UNNAMED.findall(text):
            if match not in word_refs:
                found.append(
                    ExtractedEntity(type="CROSS_REFERENCE", value=match, normalized=match)
                )
    return found


def _month_num(month: str) -> str:
    lowered = month.lower()
    for index, name in enumerate(_MONTHS, start=1):
        if name == lowered or name.startswith(lowered):
            return str(index)
    return ""


def _iso(year: str, month: str, day: str) -> str | None:
    try:
        return datetime(int(year), int(month), int(day)).date().isoformat()
    except ValueError:
        return None


def _party_key(value: str) -> str:
    return re.sub(r"[^A-Za-z]", "_", value.strip()).upper()


def _strip_ordinal(value: str) -> str:
    return re.sub(r"(st|nd|rd|th)$", "", value)