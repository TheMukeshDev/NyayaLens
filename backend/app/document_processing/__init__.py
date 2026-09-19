"""Document processing pipeline (extraction only — no AI, no fabrication).

Implements the deterministic part of docs/03_TECH/System-Architecture.md §§17-23:

* ``extractor`` — text extraction from PDF / DOCX / images (OCR injection)
* ``ocr`` — OCR engine abstraction (Tesseract default, fake-able for tests)
* ``section_parser`` — structural section detection
* ``clause_detector`` — structural clause detection + controlled clause types
* ``entities`` — deterministic entity extraction (dates, amounts, parties, refs)
* ``chunker`` — clause-aware chunks with page/confidence/uncertainty metadata
* ``pipeline`` — end-to-end orchestration

Guarantees (FR-003, FR-006, AGENT.md "no fake implementations"): extraction is
never legal interpretation, no text is ever invented, and unrecoverable input
(empty text, missing OCR) raises so the worker marks the document FAILED with
a recorded reason rather than guessing.
"""