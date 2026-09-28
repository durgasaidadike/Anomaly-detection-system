from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence


@dataclass(frozen=True)
class ConfidenceEvaluationConfig:
    """
    Configurable normalization targets.

    These are engineering defaults, not architectural thresholds.
    They can be tuned later without changing the Confidence contract.
    """

    history_target: int = 5
    observation_target: int = 10
    session_duration_target_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.history_target <= 0:
            raise ValueError(
                "history_target must be greater than zero"
            )

        if self.observation_target <= 0:
            raise ValueError(
                "observation_target must be greater than zero"
            )

        if self.session_duration_target_seconds <= 0.0:
            raise ValueError(
                "session_duration_target_seconds must be greater than zero"
            )


class ConfidenceEvaluator:
    """
    Evaluates the reliability of behavioral understanding.

    This component:
    - reads Candidate Pattern evidence
    - reads relevant historical patterns
    - evaluates evidence quality
    - does not mutate either Candidate or history
    - does not perform anomaly detection
    - does not use Similarity/Drift magnitudes
    """

    def __init__(
        self,
        config: Optional[ConfidenceEvaluationConfig] = None,
    ) -> None:
        self._config = config or ConfidenceEvaluationConfig()

    @property
    def config(self) -> ConfidenceEvaluationConfig:
        return self._config

    def evaluate(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
        behavioral_metadata: Optional[Mapping[str, Any]] = None,
        session_metadata: Optional[Mapping[str, Any]] = None,
        similarity_metadata: Optional[Mapping[str, Any]] = None,
        drift_metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate all documented confidence dimensions.

        Similarity and Drift metadata are accepted because they are part
        of the Module 09 input contract. Their numeric magnitudes are
        intentionally not used to calculate Confidence.
        """

        if candidate_pattern is None:
            raise ValueError(
                "candidate_pattern cannot be None"
            )

        history = list(historical_patterns or [])

        behavioral_metadata = dict(
            behavioral_metadata or {}
        )
        session_metadata = dict(
            session_metadata or {}
        )
        similarity_metadata = dict(
            similarity_metadata or {}
        )
        drift_metadata = dict(
            drift_metadata or {}
        )

        candidate_snapshot = self._extract_candidate_snapshot(
            candidate_pattern
        )

        dimension_scores = {
            "history_availability": (
                self._evaluate_history_availability(history)
            ),
            "candidate_completeness": (
                self._evaluate_candidate_completeness(
                    candidate_snapshot,
                    behavioral_metadata,
                    session_metadata,
                )
            ),
            "behavioral_consistency": (
                self._evaluate_behavioral_consistency(
                    candidate_snapshot
                )
            ),
            "session_maturity": (
                self._evaluate_session_maturity(
                    candidate_snapshot
                )
            ),
            "behavioral_stability": (
                self._evaluate_behavioral_stability(
                    candidate_snapshot
                )
            ),
        }

        return {
            "dimension_scores": dimension_scores,
            "candidate_pattern_id": (
                self._get_candidate_pattern_id(
                    candidate_pattern
                )
            ),
            "historical_pattern_count": len(history),
            "reliability_summary": (
                self._build_reliability_summary(
                    candidate_snapshot,
                    dimension_scores,
                )
            ),
            "metadata": {
                "similarity_metadata_available": bool(
                    similarity_metadata
                ),
                "drift_metadata_available": bool(
                    drift_metadata
                ),
                "behavioral_metadata_available": bool(
                    behavioral_metadata
                ),
                "session_metadata_available": bool(
                    session_metadata
                ),
            },
        }

    # ---------------------------------------------------------
    # Candidate extraction
    # ---------------------------------------------------------

    def _extract_candidate_snapshot(
        self,
        candidate_pattern: Any,
    ) -> Dict[str, Any]:
        observation_count = self._safe_observation_count(
            candidate_pattern
        )

        metadata = getattr(
            candidate_pattern,
            "metadata",
            None,
        )

        operational = getattr(
            candidate_pattern,
            "operational_characteristics",
            {},
        )

        temporal = getattr(
            candidate_pattern,
            "temporal_characteristics",
            {},
        )

        sequential = getattr(
            candidate_pattern,
            "sequential_characteristics",
            [],
        )

        contextual = getattr(
            candidate_pattern,
            "contextual_characteristics",
            {},
        )

        relationships = getattr(
            candidate_pattern,
            "relationship_characteristics",
            [],
        )

        session = getattr(
            candidate_pattern,
            "session_characteristics",
            {},
        )

        context_object = getattr(
            candidate_pattern,
            "context",
            None,
        )

        return {
            "observation_count": observation_count,
            "metadata": metadata,
            "operational": (
                operational
                if isinstance(operational, dict)
                else {}
            ),
            "temporal": (
                temporal
                if isinstance(temporal, dict)
                else {}
            ),
            "sequential": (
                sequential
                if isinstance(sequential, list)
                else []
            ),
            "contextual": (
                contextual
                if isinstance(contextual, dict)
                else {}
            ),
            "relationships": (
                relationships
                if isinstance(relationships, list)
                else []
            ),
            "session": (
                session
                if isinstance(session, dict)
                else {}
            ),
            "context_object": context_object,
        }

    @staticmethod
    def _safe_observation_count(
        candidate_pattern: Any,
    ) -> int:
        method = getattr(
            candidate_pattern,
            "observation_count",
            None,
        )

        if callable(method):
            try:
                return max(0, int(method()))
            except (TypeError, ValueError):
                return 0

        metadata = getattr(
            candidate_pattern,
            "metadata",
            None,
        )

        count = getattr(
            metadata,
            "observation_count",
            0,
        )

        try:
            return max(0, int(count))
        except (TypeError, ValueError):
            return 0

    # ---------------------------------------------------------
    # Dimension evaluation
    # ---------------------------------------------------------

    def _evaluate_history_availability(
        self,
        historical_patterns: Sequence[Any],
    ) -> float:
        """
        Convert historical evidence availability into [0, 1].

        Zero history remains true cold start.
        More history increases confidence progressively.
        """

        count = len(historical_patterns)

        if count <= 0:
            return 0.0

        return self._saturate(
            count / self._config.history_target
        )

    def _evaluate_candidate_completeness(
        self,
        snapshot: Dict[str, Any],
        behavioral_metadata: Mapping[str, Any],
        session_metadata: Mapping[str, Any],
    ) -> float:
        """
        Evaluate how much behavioral information is currently represented.

        Evidence families:
        - observations
        - operational characteristics
        - temporal characteristics
        - sequence
        - relationships
        - session characteristics
        - contextual information
        """

        observation_count = snapshot["observation_count"]

        observation_score = self._saturate(
            observation_count
            / self._config.observation_target
        )

        context_object = snapshot["context_object"]

        context_values = getattr(
            context_object,
            "values",
            None,
        )

        has_context_evidence = (
            bool(snapshot["contextual"])
            or (
                isinstance(context_values, dict)
                and bool(context_values)
            )
        )

        evidence_flags = [
            observation_count > 0,
            bool(snapshot["operational"]),
            bool(snapshot["temporal"]),
            bool(snapshot["sequential"]),
            bool(snapshot["relationships"]),
            bool(snapshot["session"]),
            has_context_evidence,
        ]

        structural_score = sum(
            1 for flag in evidence_flags if flag
        ) / len(evidence_flags)

        metadata_score = self._metadata_completeness(
            behavioral_metadata,
            session_metadata,
        )

        # Evidence completeness is deliberately transparent:
        # behavioral volume + structural coverage + metadata quality.
        return self._saturate(
            (
                observation_score
                + structural_score
                + metadata_score
            )
            / 3.0
        )

    @staticmethod
    def _metadata_completeness(
        behavioral_metadata: Mapping[str, Any],
        session_metadata: Mapping[str, Any],
    ) -> float:
        combined = {}

        combined.update(behavioral_metadata)
        combined.update(session_metadata)

        if not combined:
            return 0.0

        meaningful_values = 0

        for value in combined.values():
            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            meaningful_values += 1

        return meaningful_values / max(
            1,
            len(combined),
        )

    def _evaluate_behavioral_consistency(
        self,
        snapshot: Dict[str, Any],
    ) -> float:
        """
        Prefer the consistency already maintained by the Candidate Pattern.
        """

        session = snapshot["session"]

        value = session.get(
            "behavioral_consistency"
        )

        if isinstance(value, (int, float)):
            return self._saturate(float(value))

        # Graceful fallback for very early/legacy Candidate Patterns.
        intervals = snapshot["temporal"].get(
            "time_between_operations",
            [],
        )

        if len(intervals) <= 1:
            return 1.0 if snapshot["observation_count"] > 0 else 0.0

        numeric_intervals = [
            float(interval)
            for interval in intervals
            if isinstance(interval, (int, float))
        ]

        if not numeric_intervals:
            return 0.0

        average = (
            sum(numeric_intervals)
            / len(numeric_intervals)
        )

        if average == 0.0:
            return 1.0

        mean_deviation = (
            sum(
                abs(interval - average)
                for interval in numeric_intervals
            )
            / len(numeric_intervals)
        )

        return self._saturate(
            1.0 - (
                mean_deviation
                / average
            )
        )

    def _evaluate_session_maturity(
        self,
        snapshot: Dict[str, Any],
    ) -> float:
        """
        Confidence grows as the active session accumulates evidence.

        Uses:
        - observation maturity
        - session-duration maturity
        """

        observation_score = self._saturate(
            snapshot["observation_count"]
            / self._config.observation_target
        )

        temporal = snapshot["temporal"]

        duration = temporal.get(
            "duration_seconds",
            snapshot["session"].get(
                "session_length_seconds",
                0.0,
            ),
        )

        try:
            duration = max(0.0, float(duration))
        except (TypeError, ValueError):
            duration = 0.0

        duration_score = self._saturate(
            duration
            / self._config.session_duration_target_seconds
        )

        return self._saturate(
            (observation_score + duration_score)
            / 2.0
        )

    def _evaluate_behavioral_stability(
        self,
        snapshot: Dict[str, Any],
    ) -> float:
        """
        Estimate behavioral stability from consistency plus contextual
        stability.

        Context history is used only when it exists; the evaluator does
        not treat absence of context as instability.
        """

        consistency = self._evaluate_behavioral_consistency(
            snapshot
        )

        context_stability = self._evaluate_context_stability(
            snapshot
        )

        if context_stability is None:
            return consistency

        return self._saturate(
            (consistency + context_stability)
            / 2.0
        )

    def _evaluate_context_stability(
        self,
        snapshot: Dict[str, Any],
    ) -> Optional[float]:
        context_object = snapshot["context_object"]

        values = getattr(
            context_object,
            "values",
            None,
        )

        if not isinstance(values, dict):
            return None

        history_lengths = []

        for key, value in values.items():
            if not key.endswith("__history"):
                continue

            if isinstance(value, list):
                history_lengths.append(
                    len(value)
                )

        if not history_lengths:
            return None

        observation_count = snapshot["observation_count"]

        if observation_count <= 0:
            return 0.0

        # A context history length near one means the contextual
        # understanding has remained stable. More changes reduce
        # stability progressively.
        average_changes = (
            sum(
                max(0, length - 1)
                for length in history_lengths
            )
            / len(history_lengths)
        )

        change_rate = average_changes / observation_count

        return self._saturate(
            1.0 - change_rate
        )

    # ---------------------------------------------------------
    # Summary helpers
    # ---------------------------------------------------------

    @staticmethod
    def _build_reliability_summary(
        snapshot: Dict[str, Any],
        dimension_scores: Mapping[str, float],
    ) -> Dict[str, Any]:
        return {
            "observation_count": (
                snapshot["observation_count"]
            ),
            "behavioral_evidence_present": (
                snapshot["observation_count"] > 0
            ),
            "dimensions_evaluated": list(
                dimension_scores.keys()
            ),
            "lowest_dimension": (
                min(
                    dimension_scores,
                    key=dimension_scores.get,
                )
                if dimension_scores
                else None
            ),
        }

    @staticmethod
    def _get_candidate_pattern_id(
        candidate_pattern: Any,
    ) -> Optional[str]:
        value = getattr(
            candidate_pattern,
            "pattern_id",
            None,
        )

        if value is not None:
            return str(value)

        session_id = getattr(
            candidate_pattern,
            "session_id",
            None,
        )

        return (
            str(session_id)
            if session_id is not None
            else None
        )

    @staticmethod
    def _saturate(value: float) -> float:
        return max(
            0.0,
            min(1.0, float(value)),
        )
