from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ConfidenceStatus(str, Enum):
    """
    Processing state of a Confidence Engine evaluation.
    """

    SUCCESS = "success"
    COLD_START = "cold_start"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


CONFIDENCE_DIMENSIONS = (
    "history_availability",
    "candidate_completeness",
    "behavioral_consistency",
    "session_maturity",
    "behavioral_stability",
)


@dataclass(frozen=True)
class ConfidenceResult:
    """
    Immutable result produced by the Confidence Engine.

    Confidence represents the reliability of behavioral understanding,
    not anomaly probability.
    """

    status: ConfidenceStatus
    score: Optional[float]
    candidate_pattern_id: Optional[str]
    historical_pattern_count: int
    dimension_scores: Dict[str, Optional[float]]
    reliability_summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = self.status

        if not isinstance(status, ConfidenceStatus):
            try:
                status = ConfidenceStatus(status)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid confidence status: {self.status!r}"
                ) from exc

            object.__setattr__(self, "status", status)

        if self.historical_pattern_count < 0:
            raise ValueError(
                "historical_pattern_count cannot be negative"
            )

        if status == ConfidenceStatus.FAILED:
            if self.score is not None:
                raise ValueError(
                    "FAILED confidence results must not contain a score"
                )
        else:
            if self.score is None:
                raise ValueError(
                    "Non-failed confidence results must contain a score"
                )

            self._validate_score(self.score, "score")

        dimension_scores = copy.deepcopy(self.dimension_scores)

        for dimension, value in dimension_scores.items():
            if dimension not in CONFIDENCE_DIMENSIONS:
                raise ValueError(
                    f"Unknown confidence dimension: {dimension!r}"
                )

            if value is not None:
                self._validate_score(
                    value,
                    f"dimension_scores[{dimension!r}]",
                )

        object.__setattr__(
            self,
            "dimension_scores",
            dimension_scores,
        )

        object.__setattr__(
            self,
            "reliability_summary",
            copy.deepcopy(self.reliability_summary),
        )

        object.__setattr__(
            self,
            "metadata",
            copy.deepcopy(self.metadata),
        )

    @staticmethod
    def _validate_score(
        value: float,
        field_name: str,
    ) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"{field_name} must be numeric"
            )

        if not math.isfinite(float(value)):
            raise ValueError(
                f"{field_name} must be finite"
            )

        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(
                f"{field_name} must be between 0.0 and 1.0"
            )

    def is_failed(self) -> bool:
        return self.status == ConfidenceStatus.FAILED

    def is_available(self) -> bool:
        """
        Indicates whether a confidence score was successfully produced,
        including valid degraded states such as cold start or insufficient
        behavioral evidence.
        """
        return self.status != ConfidenceStatus.FAILED

    def get_dimension_score(
        self,
        dimension: str,
    ) -> Optional[float]:
        return self.dimension_scores.get(dimension)
