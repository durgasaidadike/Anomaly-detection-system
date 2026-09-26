from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class SimilarityStatus(str, Enum):
    """
    Lifecycle status of a similarity evaluation.
    """

    SUCCESS = "SUCCESS"
    COLD_START = "COLD_START"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SimilarityResult:
    """
    Immutable result produced by the Similarity Engine.

    The result contains behavioral similarity information only.
    It does not represent anomaly probability, trust, correctness,
    or a final security decision.
    """

    status: SimilarityStatus
    score: Optional[float]

    candidate_pattern_id: Optional[str]

    best_match_pattern_id: Optional[str]

    compared_pattern_count: int

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
        Validate the immutable result contract.
        """

        if self.score is not None:
            if not 0.0 <= self.score <= 1.0:
                raise ValueError(
                    "Similarity score must be between 0.0 and 1.0."
                )

        if self.compared_pattern_count < 0:
            raise ValueError(
                "Compared pattern count cannot be negative."
            )

        for dimension, value in self.dimension_scores.items():
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"Similarity score for dimension "
                    f"'{dimension}' must be between 0.0 and 1.0."
                )

        if self.status in (
            SimilarityStatus.COLD_START,
            SimilarityStatus.INSUFFICIENT_DATA,
            SimilarityStatus.FAILED,
        ):
            if self.score is not None:
                raise ValueError(
                    f"{self.status.value} results cannot contain "
                    "a similarity score."
                )

    def is_successful(self) -> bool:
        """
        Return True only when a valid similarity score was produced.
        """

        return (
            self.status == SimilarityStatus.SUCCESS
            and self.score is not None
        )
