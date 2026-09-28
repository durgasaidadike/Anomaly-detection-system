from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional

from confidence_calculator import ConfidenceCalculator
from confidence_evaluator import ConfidenceEvaluator
from confidence_result import (
    ConfidenceResult,
    ConfidenceStatus,
)

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """
    Orchestrates Confidence evaluation for an active Candidate Pattern.

    Responsibilities:
    - retrieve relevant historical Final Patterns
    - preserve user/session isolation
    - evaluate behavioral reliability
    - aggregate confidence dimensions
    - produce immutable ConfidenceResult

    This component does NOT:
    - perform anomaly detection
    - calculate Similarity
    - calculate Drift
    - perform Machine Learning
    - modify Candidate Patterns
    - modify Final Patterns
    - persist behavioral history
    - access MongoDB directly
    """

    def __init__(
        self,
        repository: Any,
        evaluator: Optional[ConfidenceEvaluator] = None,
        calculator: Optional[ConfidenceCalculator] = None,
    ) -> None:
        if repository is None:
            raise ValueError(
                "repository cannot be None"
            )

        self._repository = repository
        self._evaluator = (
            evaluator or ConfidenceEvaluator()
        )
        self._calculator = (
            calculator or ConfidenceCalculator()
        )

    # ---------------------------------------------------------
    # Primary public API
    # ---------------------------------------------------------

    def calculateConfidence(
        self,
        candidate_pattern: Any,
        behavioral_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        session_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        similarity_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        drift_metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> ConfidenceResult:
        """
        Calculate behavioral confidence for the Candidate Pattern.
        """

        try:
            if candidate_pattern is None:
                return self._failed_result(
                    None,
                    historical_pattern_count=0,
                    message=(
                        "Candidate Pattern cannot be None"
                    ),
                )

            historical_patterns = (
                self.retrieveBehaviorHistory(
                    candidate_pattern
                )
            )

            if not historical_patterns:
                status = (
                    ConfidenceStatus.COLD_START
                )
            else:
                status = (
                    ConfidenceStatus.SUCCESS
                )

            return self.generateConfidenceMetric(
                candidate_pattern=candidate_pattern,
                historical_patterns=historical_patterns,
                status=status,
                behavioral_metadata=(
                    behavioral_metadata
                ),
                session_metadata=session_metadata,
                similarity_metadata=(
                    similarity_metadata
                ),
                drift_metadata=drift_metadata,
            )

        except Exception as exc:
            logger.exception(
                "Confidence evaluation failed."
            )

            return self._failed_result(
                candidate_pattern,
                historical_pattern_count=0,
                message=str(exc),
            )

    # ---------------------------------------------------------
    # Historical retrieval
    # ---------------------------------------------------------

    def retrieveBehaviorHistory(
        self,
        candidate_pattern: Any,
    ) -> List[Any]:
        """
        Retrieve historical Final Patterns belonging only to the
        same user as the Candidate Pattern.

        A Candidate Pattern without a user identity never shares
        history with another identity-less Candidate Pattern.

        The current session itself is excluded.
        """

        if candidate_pattern is None:
            return []

        user_id = getattr(
            candidate_pattern,
            "user_id",
            None,
        )

        # Critical isolation rule:
        # None must never become a shared user bucket.
        if user_id is None:
            return []

        repository = self._resolve_repository()

        get_all = getattr(
            repository,
            "get_all",
            None,
        )

        if not callable(get_all):
            raise AttributeError(
                "Repository must provide get_all()"
            )

        historical_patterns = get_all()

        current_session_id = getattr(
            candidate_pattern,
            "session_id",
            None,
        )

        result: List[Any] = []

        for pattern in historical_patterns:
            historical_user_id = getattr(
                pattern,
                "user_id",
                None,
            )

            if historical_user_id != user_id:
                continue

            historical_session_id = getattr(
                pattern,
                "session_id",
                None,
            )

            if (
                current_session_id is not None
                and historical_session_id
                == current_session_id
            ):
                continue

            result.append(pattern)

        return result

    # ---------------------------------------------------------
    # Reliability evaluation
    # ---------------------------------------------------------

    def evaluateReliability(
        self,
        candidate_pattern: Any,
        historical_patterns: Optional[
            List[Any]
        ] = None,
        behavioral_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        session_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        similarity_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        drift_metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate the independent Confidence dimensions.

        Similarity and Drift metadata are passed through as documented
        inputs, but their numeric scores are not used to calculate
        Confidence.
        """

        if historical_patterns is None:
            historical_patterns = (
                self.retrieveBehaviorHistory(
                    candidate_pattern
                )
            )

        return self._evaluator.evaluate(
            candidate_pattern=candidate_pattern,
            historical_patterns=historical_patterns,
            behavioral_metadata=(
                behavioral_metadata
            ),
            session_metadata=session_metadata,
            similarity_metadata=(
                similarity_metadata
            ),
            drift_metadata=drift_metadata,
        )

    # ---------------------------------------------------------
    # Candidate completeness API
    # ---------------------------------------------------------

    def analyzeBehaviorCompleteness(
        self,
        candidate_pattern: Any,
        behavioral_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        session_metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> float:
        """
        Return only the Candidate Pattern completeness dimension.
        """

        evaluation = self._evaluator.evaluate(
            candidate_pattern=candidate_pattern,
            historical_patterns=[],
            behavioral_metadata=(
                behavioral_metadata
            ),
            session_metadata=session_metadata,
        )

        return float(
            evaluation["dimension_scores"][
                "candidate_completeness"
            ]
        )

    # ---------------------------------------------------------
    # Metric generation
    # ---------------------------------------------------------

    def generateConfidenceMetric(
        self,
        candidate_pattern: Any,
        historical_patterns: List[Any],
        status: ConfidenceStatus,
        behavioral_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        session_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        similarity_metadata: Optional[
            Mapping[str, Any]
        ] = None,
        drift_metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> ConfidenceResult:
        """
        Evaluate dimensions, aggregate them, and create the immutable
        ConfidenceResult.
        """

        evaluation = self.evaluateReliability(
            candidate_pattern=candidate_pattern,
            historical_patterns=historical_patterns,
            behavioral_metadata=(
                behavioral_metadata
            ),
            session_metadata=session_metadata,
            similarity_metadata=(
                similarity_metadata
            ),
            drift_metadata=drift_metadata,
        )

        dimension_scores = evaluation[
            "dimension_scores"
        ]

        score, calculation_details = (
            self._calculator.calculate_with_details(
                dimension_scores
            )
        )

        metadata = dict(
            evaluation.get("metadata", {})
        )

        metadata["calculation"] = (
            calculation_details
        )

        metadata["status_reason"] = (
            "No historical Final Patterns were "
            "available for this user."
            if status == ConfidenceStatus.COLD_START
            else "Sufficient historical behavioral "
            "information was available."
        )

        return ConfidenceResult(
            status=status,
            score=score,
            candidate_pattern_id=(
                evaluation[
                    "candidate_pattern_id"
                ]
            ),
            historical_pattern_count=len(
                historical_patterns
            ),
            dimension_scores=dimension_scores,
            reliability_summary=(
                evaluation[
                    "reliability_summary"
                ]
            ),
            metadata=metadata,
        )

    # ---------------------------------------------------------
    # Repository adapter support
    # ---------------------------------------------------------

    def _resolve_repository(self) -> Any:
        """
        Accept either the repository itself or the existing
        FinalPatternRepositoryAdapter.
        """

        get_repository = getattr(
            self._repository,
            "get_repository",
            None,
        )

        if callable(get_repository):
            return get_repository()

        return self._repository

    # ---------------------------------------------------------
    # Failure handling
    # ---------------------------------------------------------

    def _failed_result(
        self,
        candidate_pattern: Any,
        historical_pattern_count: int,
        message: str,
    ) -> ConfidenceResult:
        candidate_pattern_id = None

        if candidate_pattern is not None:
            candidate_pattern_id = getattr(
                candidate_pattern,
                "pattern_id",
                None,
            )

            if candidate_pattern_id is None:
                candidate_pattern_id = getattr(
                    candidate_pattern,
                    "session_id",
                    None,
                )

        return ConfidenceResult(
            status=ConfidenceStatus.FAILED,
            score=None,
            candidate_pattern_id=(
                str(candidate_pattern_id)
                if candidate_pattern_id is not None
                else None
            ),
            historical_pattern_count=(
                historical_pattern_count
            ),
            dimension_scores={},
            reliability_summary={},
            metadata={
                "error": message,
            },
        )
