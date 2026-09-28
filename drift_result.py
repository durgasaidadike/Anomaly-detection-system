from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class DriftStatus(str, Enum):
    """
    Processing states returned by the Drift Engine.
    """

    SUCCESS = "SUCCESS"
    COLD_START = "COLD_START"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DriftResult:
    """
    Immutable result produced by the Drift Engine.

    The result contains only drift-analysis information.
    It does not contain anomaly decisions, ML predictions,
    confidence decisions, or recovery actions.
    """

    status: DriftStatus

    score: Optional[float]

    candidate_pattern_id: Optional[str]

    historical_pattern_count: int

    dimension_scores: Dict[str, Optional[float]] = field(
        default_factory=dict
    )

    comparison_summary: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Validate the result contract.
        """

        if self.historical_pattern_count < 0:
            raise ValueError(
                "historical_pattern_count cannot be negative."
            )

        if self.score is not None:
            if not 0.0 <= self.score <= 1.0:
                raise ValueError(
                    "Drift score must be between 0.0 and 1.0."
                )

        for dimension, value in self.dimension_scores.items():
            if value is None:
                continue

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"Drift dimension score for "
                    f"'{dimension}' must be between 0.0 and 1.0."
                )

        if self.status != DriftStatus.SUCCESS and self.score is not None:
            raise ValueError(
                "Non-success Drift results cannot contain a score."
            )

    def is_successful(self) -> bool:
        """
        Return True when drift evaluation completed successfully.
        """

        return self.status == DriftStatus.SUCCESS
