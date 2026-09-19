"""Two-document comparison orchestration.

Runs the comparison pipeline from FR-013 and API-Specification.md §19:
deterministic clause matching produces provable ADDED/REMOVED/MODIFIED/UNCHANGED
changes; the model only explains MODIFIED pairs. Changes are never invented:
the model cannot add, remove or reclassify one. See ``service`` for the full
honesty contract.
"""

from app.ai.comparison.service import (
    DocumentComparisonService,
    build_comparison_service,
)

__all__ = ["DocumentComparisonService", "build_comparison_service"]