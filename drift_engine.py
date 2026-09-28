from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from behavioral_trend_analyzer import BehavioralTrendAnalyzer
from drift_calculator import DriftCalculator
from drift_result import DriftResult, DriftStatus


logger = logging.getLogger(__name__)


class DriftEngine:
    """
    PRISM Module 08 - Drift Engine.

    Measures long-term behavioral evolution between the
    active Candidate Pattern and historical Final Patterns.

    The engine does NOT:
    - perform Machine Learning
    - calculate Similarity
    - calculate Confidence
    - modify Candidate Patterns
    - modify Final Patterns
    - store behavioral history
    - access MongoDB directly
    - perform recovery
    - make anomaly decisions
    """

    def __init__(
        self,
        repository: Any,
        analyzer: Optional[BehavioralTrendAnalyzer] = None,
        calculator: Optional[DriftCalculator] = None,
        minimum_history: int = 2,
    ) -> None:
        if repository is None:
            raise ValueError(
                "repository is required."
            )

        if minimum_history < 1:
            raise ValueError(
                "minimum_history must be at least 1."
            )

        self._repository = repository

        self._analyzer = (
            analyzer
            or BehavioralTrendAnalyzer(
                minimum_history=minimum_history
            )
        )

        self._calculator = (
            calculator
            or DriftCalculator()
        )

        self._minimum_history = minimum_history

    def calculateDrift(
        self,
        candidate_pattern: Any,
    ) -> DriftResult:
        """
        Evaluate behavioral Drift for the supplied Candidate Pattern.
        """

        candidate_pattern_id = (
            self._get_candidate_pattern_id(
                candidate_pattern
            )
        )

        try:
            historical_patterns = (
                self.retrieveBehaviorHistory(
                    candidate_pattern
                )
            )

            history_count = len(
                historical_patterns
            )

            if history_count == 0:
                return DriftResult(
                    status=DriftStatus.COLD_START,
                    score=None,
                    candidate_pattern_id=(
                        candidate_pattern_id
                    ),
                    historical_pattern_count=0,
                    comparison_summary={
                        "reason": (
                            "No eligible historical "
                            "behavioral patterns."
                        )
                    },
                    metadata={
                        "minimum_history": (
                            self._minimum_history
                        ),
                    },
                )

            if history_count < self._minimum_history:
                return DriftResult(
                    status=(
                        DriftStatus.INSUFFICIENT_DATA
                    ),
                    score=None,
                    candidate_pattern_id=(
                        candidate_pattern_id
                    ),
                    historical_pattern_count=(
                        history_count
                    ),
                    comparison_summary={
                        "reason": (
                            "Insufficient historical "
                            "behavioral sessions."
                        )
                    },
                    metadata={
                        "minimum_history": (
                            self._minimum_history
                        ),
                    },
                )

            return self.generateDriftMetric(
                candidate_pattern,
                historical_patterns,
            )

        except Exception:
            logger.exception(
                "Drift evaluation failed for "
                "candidate pattern '%s'.",
                candidate_pattern_id,
            )

            return DriftResult(
                status=DriftStatus.FAILED,
                score=None,
                candidate_pattern_id=(
                    candidate_pattern_id
                ),
                historical_pattern_count=0,
                comparison_summary={
                    "reason": (
                        "Drift evaluation "
                        "processing failure."
                    )
                },
                metadata={
                    "minimum_history": (
                        self._minimum_history
                    ),
                },
            )

    def analyzeBehaviorEvolution(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Dict[str, Optional[float]]:
        """
        Analyze the seven documented Drift dimensions.
        """

        return self._analyzer.analyze(
            candidate_pattern,
            historical_patterns,
        )

    def retrieveBehaviorHistory(
        self,
        candidate_pattern: Any,
    ) -> List[Any]:
        """
        Retrieve relevant historical Final Patterns.

        Only patterns belonging to the same user are eligible.

        A Candidate Pattern without a user identity is never allowed
        to share the repository's unscoped history bucket.
        """

        if candidate_pattern is None:
            return []

        candidate_user_id = getattr(
            candidate_pattern,
            "user_id",
            None,
        )

        # Security / isolation rule:
        # never compare an unscoped candidate against other
        # unscoped historical patterns.
        if candidate_user_id is None:
            return []

        patterns = self._repository.get_all()

        candidate_session_id = getattr(
            candidate_pattern,
            "session_id",
            None,
        )

        eligible_patterns = []

        for pattern in patterns:
            historical_user_id = getattr(
                pattern,
                "user_id",
                None,
            )

            if historical_user_id != candidate_user_id:
                continue

            historical_session_id = getattr(
                pattern,
                "session_id",
                None,
            )

            # The active Candidate Pattern must not be compared
            # against a historical record carrying the same
            # session identity.
            if (
                candidate_session_id is not None
                and historical_session_id
                == candidate_session_id
            ):
                continue

            eligible_patterns.append(
                pattern
            )

        return eligible_patterns

    def generateDriftMetric(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> DriftResult:
        """
        Analyze behavioral evolution and aggregate the
        dimension-level measurements into one Drift metric.
        """

        candidate_pattern_id = (
            self._get_candidate_pattern_id(
                candidate_pattern
            )
        )

        historical_count = len(
            historical_patterns
        )

        if historical_count < self._minimum_history:
            status = (
                DriftStatus.COLD_START
                if historical_count == 0
                else DriftStatus.INSUFFICIENT_DATA
            )

            return DriftResult(
                status=status,
                score=None,
                candidate_pattern_id=(
                    candidate_pattern_id
                ),
                historical_pattern_count=(
                    historical_count
                ),
                comparison_summary={
                    "reason": (
                        "Historical behavior "
                        "is insufficient for Drift."
                    )
                },
                metadata={
                    "minimum_history": (
                        self._minimum_history
                    ),
                },
            )

        dimension_scores = (
            self.analyzeBehaviorEvolution(
                candidate_pattern,
                historical_patterns,
            )
        )

        score, calculation_details = (
            self._calculator.calculate_with_details(
                dimension_scores
            )
        )

        if score is None:
            return DriftResult(
                status=DriftStatus.INSUFFICIENT_DATA,
                score=None,
                candidate_pattern_id=(
                    candidate_pattern_id
                ),
                historical_pattern_count=(
                    historical_count
                ),
                dimension_scores=dimension_scores,
                comparison_summary={
                    "reason": (
                        "No usable Drift dimensions "
                        "were available."
                    )
                },
                metadata={
                    "minimum_history": (
                        self._minimum_history
                    ),
                    "calculation": (
                        calculation_details
                    ),
                },
            )

        return DriftResult(
            status=DriftStatus.SUCCESS,
            score=score,
            candidate_pattern_id=(
                candidate_pattern_id
            ),
            historical_pattern_count=(
                historical_count
            ),
            dimension_scores=dimension_scores,
            comparison_summary={
                "dimensions_analyzed": (
                    calculation_details[
                        "available_dimensions"
                    ]
                ),
                "dimensions_unavailable": (
                    calculation_details[
                        "unavailable_dimensions"
                    ]
                ),
            },
            metadata={
                "minimum_history": (
                    self._minimum_history
                ),
                "calculation": (
                    calculation_details
                ),
            },
        )

    @staticmethod
    def _get_candidate_pattern_id(
        candidate_pattern: Any,
    ) -> Optional[str]:
        if candidate_pattern is None:
            return None

        pattern_id = getattr(
            candidate_pattern,
            "pattern_id",
            None,
        )

        if pattern_id is not None:
            return str(pattern_id)

        session_id = getattr(
            candidate_pattern,
            "session_id",
            None,
        )

        if session_id is not None:
            return str(session_id)

        return None
