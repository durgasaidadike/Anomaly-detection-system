from __future__ import annotations

import logging
from typing import Any, List, Optional

from pattern_comparator import PatternComparator
from similarity_calculator import SimilarityCalculator
from similarity_result import SimilarityResult, SimilarityStatus


logger = logging.getLogger(__name__)


class SimilarityEngine:
    """
    Orchestrates behavioral similarity evaluation.

    Responsibilities:
        - Retrieve historical Final Patterns through the repository boundary.
        - Preserve user isolation.
        - Compare the Candidate Pattern against historical behavior.
        - Generate the similarity metric.
        - Return a structured SimilarityResult.

    This class does NOT:
        - access MongoDB directly
        - modify Candidate Patterns
        - modify Final Patterns
        - store historical knowledge
        - perform Machine Learning
        - perform anomaly detection
        - perform recovery
    """

    def __init__(
        self,
        repository: Any,
        comparator: Optional[PatternComparator] = None,
        calculator: Optional[SimilarityCalculator] = None,
    ) -> None:
        if repository is None:
            raise ValueError(
                "A Pattern Repository is required."
            )

        self._repository = repository
        self._comparator = (
            comparator or PatternComparator()
        )
        self._calculator = (
            calculator or SimilarityCalculator()
        )

    def evaluate(
        self,
        candidate_pattern: Any,
    ) -> SimilarityResult:
        """
        Perform one stateless similarity evaluation.

        Every invocation performs a fresh retrieval and comparison.
        """

        candidate_pattern_id = self._candidate_identifier(
            candidate_pattern
        )

        try:
            if candidate_pattern is None:
                return SimilarityResult(
                    status=SimilarityStatus.INSUFFICIENT_DATA,
                    score=None,
                    candidate_pattern_id=None,
                    best_match_pattern_id=None,
                    compared_pattern_count=0,
                    comparison_summary={
                        "reason": "candidate_pattern_missing",
                    },
                    metadata={
                        "module": "SimilarityEngine",
                    },
                )

            historical_patterns = (
                self.retrieve_historical_patterns(
                    candidate_pattern
                )
            )

            if not historical_patterns:
                return SimilarityResult(
                    status=SimilarityStatus.COLD_START,
                    score=None,
                    candidate_pattern_id=candidate_pattern_id,
                    best_match_pattern_id=None,
                    compared_pattern_count=0,
                    comparison_summary={
                        "reason": "no_historical_patterns_for_user",
                    },
                    metadata={
                        "module": "SimilarityEngine",
                        "user_id": getattr(
                            candidate_pattern,
                            "user_id",
                            None,
                        ),
                    },
                )

            best_result = None

            for historical_pattern in historical_patterns:
                dimension_scores = (
                    self._comparator.compare(
                        candidate_pattern,
                        historical_pattern,
                    )
                )

                score_details = (
                    self._calculator.calculate_with_details(
                        dimension_scores
                    )
                )

                score = score_details["score"]

                if score is None:
                    continue

                comparison = {
                    "pattern_id": getattr(
                        historical_pattern,
                        "pattern_id",
                        None,
                    ),
                    "score": score,
                    "dimension_scores": dimension_scores,
                    "calculation": score_details,
                }

                if (
                    best_result is None
                    or score > best_result["score"]
                ):
                    best_result = comparison

            if best_result is None:
                return SimilarityResult(
                    status=SimilarityStatus.INSUFFICIENT_DATA,
                    score=None,
                    candidate_pattern_id=candidate_pattern_id,
                    best_match_pattern_id=None,
                    compared_pattern_count=len(
                        historical_patterns
                    ),
                    comparison_summary={
                        "reason": (
                            "historical_patterns_available_but_"
                            "insufficient_behavioral_information"
                        ),
                    },
                    metadata={
                        "module": "SimilarityEngine",
                    },
                )


            return SimilarityResult(
                status=SimilarityStatus.SUCCESS,
                score=best_result["score"],
                candidate_pattern_id=candidate_pattern_id,
                best_match_pattern_id=(
                    best_result["pattern_id"]
                ),
                compared_pattern_count=len(
                    historical_patterns
                ),
                dimension_scores=best_result[
                    "dimension_scores"
                ],
                comparison_summary={
                    "selection": "highest_similarity",
                    "best_match_score": best_result["score"],
                    "dimensions_used": best_result[
                        "calculation"
                    ]["available_dimensions"],
                    "dimensions_unavailable": best_result[
                        "calculation"
                    ]["unavailable_dimensions"],
                },
                metadata={
                    "module": "SimilarityEngine",
                    "user_id": getattr(
                        candidate_pattern,
                        "user_id",
                        None,
                    ),
                },
            )

        except Exception as exc:
            logger.exception(
                "Similarity evaluation failed for candidate '%s'.",
                candidate_pattern_id,
            )

            return SimilarityResult(
                status=SimilarityStatus.FAILED,
                score=None,
                candidate_pattern_id=candidate_pattern_id,
                best_match_pattern_id=None,
                compared_pattern_count=0,
                comparison_summary={
                    "reason": "comparison_failure",
                },
                metadata={
                    "module": "SimilarityEngine",
                    "error_type": type(exc).__name__,
                },
            )

    def retrieve_historical_patterns(
        self,
        candidate_pattern: Any,
    ) -> List[Any]:
        """
        Retrieve historical Final Patterns through the repository.

        Only patterns belonging to the same user are eligible.
        No direct storage access is performed here.
        """

        patterns = self._repository.get_all()

        if patterns is None:
            return []

        candidate_user_id = getattr(
            candidate_pattern,
            "user_id",
            None,
        )

        return [
            pattern
            for pattern in patterns
            if getattr(
                pattern,
                "user_id",
                None,
            )
            == candidate_user_id
        ]

    def compare_patterns(
        self,
        candidate_pattern: Any,
        historical_pattern: Any,
    ) -> dict:
        """
        Compare one Candidate Pattern against one Final Pattern.

        This method exposes the comparison stage separately for
        downstream orchestration and contract-level testing.
        """

        return self._comparator.compare(
            candidate_pattern,
            historical_pattern,
        )

    def generate_similarity_metric(
        self,
        dimension_scores: dict,
    ) -> Optional[float]:
        """
        Generate the normalized similarity metric from
        dimension-level comparison results.
        """

        return self._calculator.calculate(
            dimension_scores
        )

    @staticmethod
    def _candidate_identifier(
        candidate_pattern: Any,
    ) -> Optional[str]:
        """
        Return a stable identifier available on CandidatePattern.

        CandidatePattern does not carry a FinalPattern-style
        pattern_id, therefore session_id identifies the active
        behavioral pattern during this stage.
        """

        if candidate_pattern is None:
            return None

        return getattr(
            candidate_pattern,
            "session_id",
            None,
        )

