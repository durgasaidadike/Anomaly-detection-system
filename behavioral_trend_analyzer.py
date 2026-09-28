from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence


class BehavioralTrendAnalyzer:
    """
    Analyzes long-term behavioral evolution between an active
    Candidate Pattern and historical Final Patterns.

    This class measures Drift characteristics only.

    It does NOT:
    - calculate Similarity
    - calculate Confidence
    - perform ML
    - modify Candidate Patterns
    - modify Final Patterns
    - persist history
    - make anomaly decisions
    """

    DIMENSIONS = (
        "behavioral_workflow",
        "operation_frequency",
        "temporal_characteristics",
        "working_rhythm",
        "behavioral_relationships",
        "session_characteristics",
        "contextual_behavior",
    )

    SESSION_IDENTITY_KEYS = {
        "session_id",
        "user_id",
        "session_start_time",
        "session_end_time",
        "created_at",
        "finalized_at",
    }

    def __init__(
        self,
        minimum_history: int = 2,
    ) -> None:
        if minimum_history < 1:
            raise ValueError(
                "minimum_history must be at least 1."
            )

        self.minimum_history = minimum_history

    def analyze(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Dict[str, Optional[float]]:
        """
        Analyze all defined Drift dimensions.

        Returns a dictionary containing one normalized Drift
        measurement for each dimension.

        A value of:
            0.0 -> no measurable change
            1.0 -> maximum detected change

        None means the dimension could not be evaluated from
        the supplied behavioral information.
        """

        history = list(historical_patterns)

        if len(history) < self.minimum_history:
            return {
                dimension: None
                for dimension in self.DIMENSIONS
            }

        return {
            "behavioral_workflow": (
                self.analyze_behavioral_workflow(
                    candidate_pattern,
                    history,
                )
            ),
            "operation_frequency": (
                self.analyze_operation_frequency(
                    candidate_pattern,
                    history,
                )
            ),
            "temporal_characteristics": (
                self.analyze_temporal_characteristics(
                    candidate_pattern,
                    history,
                )
            ),
            "working_rhythm": (
                self.analyze_working_rhythm(
                    candidate_pattern,
                    history,
                )
            ),
            "behavioral_relationships": (
                self.analyze_behavioral_relationships(
                    candidate_pattern,
                    history,
                )
            ),
            "session_characteristics": (
                self.analyze_session_characteristics(
                    candidate_pattern,
                    history,
                )
            ),
            "contextual_behavior": (
                self.analyze_contextual_behavior(
                    candidate_pattern,
                    history,
                )
            ),
        }

    def analyze_behavioral_workflow(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure change in behavioral workflow structure.

        Workflow is represented primarily by the ordered
        operation sequence.
        """

        candidate_sequence = self._get_value(
            candidate_pattern,
            "sequential_characteristics",
        )

        historical_sequences = [
            self._get_value(
                pattern,
                "sequential_characteristics",
            )
            for pattern in historical_patterns
        ]

        candidate_operations = self._operation_sequence(
            candidate_sequence
        )

        historical_operations = [
            self._operation_sequence(sequence)
            for sequence in historical_sequences
        ]

        historical_operations = [
            sequence
            for sequence in historical_operations
            if sequence
        ]

        if not candidate_operations or not historical_operations:
            return None

        baseline = self._most_representative_sequence(
            historical_operations
        )

        return self._sequence_drift(
            candidate_operations,
            baseline,
        )

    def analyze_operation_frequency(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure change in operation-frequency distribution.
        """

        candidate_characteristics = self._get_value(
            candidate_pattern,
            "operational_characteristics",
        )

        candidate_counts = self._extract_operation_counts(
            candidate_characteristics
        )

        historical_distributions = []

        for pattern in historical_patterns:
            characteristics = self._get_value(
                pattern,
                "operational_characteristics",
            )

            counts = self._extract_operation_counts(
                characteristics
            )

            distribution = self._normalize_counts(counts)

            if distribution:
                historical_distributions.append(
                    distribution
                )

        if not candidate_counts or not historical_distributions:
            return None

        candidate_distribution = self._normalize_counts(
            candidate_counts
        )

        baseline = self._average_distributions(
            historical_distributions
        )

        return self._distribution_drift(
            candidate_distribution,
            baseline,
        )

    def analyze_temporal_characteristics(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure change in temporal behavior.

        Absolute session timestamps are intentionally excluded.
        Relative behavioral timing remains relevant.
        """

        candidate = self._get_value(
            candidate_pattern,
            "temporal_characteristics",
        )

        historical = [
            self._get_value(
                pattern,
                "temporal_characteristics",
            )
            for pattern in historical_patterns
        ]

        return self._mapping_drift(
            candidate,
            historical,
        )

    def analyze_working_rhythm(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure change in working rhythm.

        The Candidate/Final Pattern may represent working rhythm
        inside temporal characteristics.
        """

        candidate_temporal = self._get_value(
            candidate_pattern,
            "temporal_characteristics",
        )

        historical_temporal = [
            self._get_value(
                pattern,
                "temporal_characteristics",
            )
            for pattern in historical_patterns
        ]

        candidate_rhythm = self._extract_working_rhythm(
            candidate_temporal
        )

        historical_rhythms = [
            self._extract_working_rhythm(
                temporal
            )
            for temporal in historical_temporal
        ]

        historical_rhythms = [
            rhythm
            for rhythm in historical_rhythms
            if rhythm is not None
        ]

        if candidate_rhythm is None or not historical_rhythms:
            return None

        numeric_values = [
            float(value)
            for value in historical_rhythms
            if self._is_number(value)
        ]

        if not numeric_values or not self._is_number(
            candidate_rhythm
        ):
            return self._value_drift(
                candidate_rhythm,
                self._representative_value(
                    historical_rhythms
                ),
            )

        baseline = sum(numeric_values) / len(numeric_values)

        return self._numeric_drift(
            float(candidate_rhythm),
            baseline,
        )

    def analyze_behavioral_relationships(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure change in behavioral relationships.
        """

        candidate_relationships = self._get_value(
            candidate_pattern,
            "relationship_characteristics",
        )

        historical_relationships = [
            self._get_value(
                pattern,
                "relationship_characteristics",
            )
            for pattern in historical_patterns
        ]

        candidate_set = self._relationship_set(
            candidate_relationships
        )

        historical_sets = [
            self._relationship_set(
                relationships
            )
            for relationships in historical_relationships
        ]

        historical_sets = [
            values
            for values in historical_sets
            if values
        ]

        if not candidate_set or not historical_sets:
            return None

        baseline = set().union(*historical_sets)

        if not baseline:
            return None

        intersection = len(
            candidate_set & baseline
        )

        union = len(
            candidate_set | baseline
        )

        if union == 0:
            return 0.0

        return self._clamp(
            1.0 - (intersection / union)
        )

    def analyze_session_characteristics(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure evolution of session-level behavior.

        Session identity and absolute lifecycle timestamps are
        excluded because they identify a session rather than
        describe long-term behavioral change.
        """

        candidate = self._get_value(
            candidate_pattern,
            "session_characteristics",
        )

        historical = [
            self._get_value(
                pattern,
                "session_characteristics",
            )
            for pattern in historical_patterns
        ]

        return self._mapping_drift(
            candidate,
            historical,
            ignored_keys=self.SESSION_IDENTITY_KEYS,
        )

    def analyze_contextual_behavior(
        self,
        candidate_pattern: Any,
        historical_patterns: Sequence[Any],
    ) -> Optional[float]:
        """
        Measure contextual behavioral evolution.
        """

        candidate = self._get_value(
            candidate_pattern,
            "contextual_characteristics",
        )

        historical = [
            self._get_value(
                pattern,
                "contextual_characteristics",
            )
            for pattern in historical_patterns
        ]

        return self._mapping_drift(
            candidate,
            historical,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_value(
        pattern: Any,
        attribute: str,
    ) -> Any:
        if pattern is None:
            return None

        if isinstance(pattern, dict):
            return pattern.get(attribute)

        return getattr(
            pattern,
            attribute,
            None,
        )

    @staticmethod
    def _extract_operation_counts(
        characteristics: Any,
    ) -> Dict[str, float]:
        if not isinstance(characteristics, dict):
            return {}

        counts = characteristics.get(
            "operation_counts"
        )

        if not isinstance(counts, dict):
            return {}

        result: Dict[str, float] = {}

        for operation, count in counts.items():
            if isinstance(count, (int, float)):
                result[str(operation)] = float(count)

        return result

    @staticmethod
    def _normalize_counts(
        counts: Dict[str, float],
    ) -> Dict[str, float]:
        total = sum(counts.values())

        if total <= 0:
            return {}

        return {
            key: value / total
            for key, value in counts.items()
        }

    @staticmethod
    def _average_distributions(
        distributions: Sequence[Dict[str, float]],
    ) -> Dict[str, float]:
        if not distributions:
            return {}

        keys = set()

        for distribution in distributions:
            keys.update(distribution.keys())

        count = len(distributions)

        return {
            key: sum(
                distribution.get(key, 0.0)
                for distribution in distributions
            ) / count
            for key in keys
        }

    @staticmethod
    def _distribution_drift(
        candidate: Dict[str, float],
        baseline: Dict[str, float],
    ) -> Optional[float]:
        if not candidate or not baseline:
            return None

        keys = set(candidate) | set(baseline)

        distance = sum(
            abs(
                candidate.get(key, 0.0)
                - baseline.get(key, 0.0)
            )
            for key in keys
        )

        # Total variation distance, normalized to [0, 1].
        return BehavioralTrendAnalyzer._clamp(
            distance / 2.0
        )

    @staticmethod
    def _operation_sequence(
        sequence: Any,
    ) -> List[str]:
        if not isinstance(sequence, list):
            return []

        result = []

        for entry in sequence:
            if isinstance(entry, dict):
                operation = entry.get(
                    "operation_type"
                )
            else:
                operation = entry

            if operation is not None:
                result.append(str(operation))

        return result

    @staticmethod
    def _most_representative_sequence(
        sequences: Sequence[List[str]],
    ) -> List[str]:
        """
        Select the historical sequence with the highest
        frequency among exact sequence representations.

        This is intentionally deterministic and avoids mutating
        the historical data.
        """

        if not sequences:
            return []

        counter = Counter(
            tuple(sequence)
            for sequence in sequences
        )

        return list(
            counter.most_common(1)[0][0]
        )

    @staticmethod
    def _sequence_drift(
        candidate: List[str],
        baseline: List[str],
    ) -> Optional[float]:
        if not candidate or not baseline:
            return None

        max_length = max(
            len(candidate),
            len(baseline),
        )

        if max_length == 0:
            return 0.0

        differences = 0

        for index in range(max_length):
            candidate_value = (
                candidate[index]
                if index < len(candidate)
                else None
            )

            baseline_value = (
                baseline[index]
                if index < len(baseline)
                else None
            )

            if candidate_value != baseline_value:
                differences += 1

        return BehavioralTrendAnalyzer._clamp(
            differences / max_length
        )

    @staticmethod
    def _extract_working_rhythm(
        temporal: Any,
    ) -> Any:
        if not isinstance(temporal, dict):
            return None

        return temporal.get(
            "working_rhythm"
        )

    @staticmethod
    def _relationship_set(
        relationships: Any,
    ) -> set:
        if not isinstance(relationships, list):
            return set()

        normalized = set()

        for relationship in relationships:
            if isinstance(relationship, dict):
                normalized.add(
                    repr(
                        sorted(
                            relationship.items(),
                            key=lambda item: str(
                                item[0]
                            ),
                        )
                    )
                )
            else:
                normalized.add(
                    repr(relationship)
                )

        return normalized

    @classmethod
    def _mapping_drift(
        cls,
        candidate: Any,
        historical: Sequence[Any],
        ignored_keys: Optional[Iterable[str]] = None,
    ) -> Optional[float]:
        if not isinstance(candidate, dict):
            return None

        valid_historical = [
            value
            for value in historical
            if isinstance(value, dict)
        ]

        if not valid_historical:
            return None

        ignored = set(ignored_keys or [])

        keys = set(candidate.keys())

        for mapping in valid_historical:
            keys.update(mapping.keys())

        keys = {
            key
            for key in keys
            if key not in ignored
        }

        if not keys:
            return None

        dimension_drifts = []

        for key in keys:
            candidate_value = candidate.get(key)

            historical_values = [
                mapping.get(key)
                for mapping in valid_historical
                if key in mapping
            ]

            if not historical_values:
                continue

            representative = cls._representative_value(
                historical_values
            )

            drift = cls._value_drift(
                candidate_value,
                representative,
            )

            if drift is not None:
                dimension_drifts.append(drift)

        if not dimension_drifts:
            return None

        return sum(dimension_drifts) / len(
            dimension_drifts
        )

    @classmethod
    def _value_drift(
        cls,
        candidate: Any,
        baseline: Any,
    ) -> Optional[float]:
        if candidate is None or baseline is None:
            return None

        if cls._is_number(candidate) and cls._is_number(
            baseline
        ):
            return cls._numeric_drift(
                float(candidate),
                float(baseline),
            )

        if isinstance(candidate, dict) and isinstance(
            baseline,
            dict,
        ):
            return cls._mapping_drift(
                candidate,
                [baseline],
            )

        if isinstance(candidate, (list, tuple, set)) and isinstance(
            baseline,
            (list, tuple, set),
        ):
            candidate_set = {
                repr(value)
                for value in candidate
            }

            baseline_set = {
                repr(value)
                for value in baseline
            }

            union = candidate_set | baseline_set

            if not union:
                return 0.0

            intersection = (
                candidate_set & baseline_set
            )

            return cls._clamp(
                1.0
                - (
                    len(intersection)
                    / len(union)
                )
            )

        return 0.0 if candidate == baseline else 1.0

    @staticmethod
    def _numeric_drift(
        candidate: float,
        baseline: float,
    ) -> float:
        denominator = abs(candidate) + abs(
            baseline
        )

        if denominator == 0.0:
            return 0.0

        return BehavioralTrendAnalyzer._clamp(
            abs(candidate - baseline)
            / denominator
        )

    @staticmethod
    def _representative_value(
        values: Sequence[Any],
    ) -> Any:
        if not values:
            return None

        numeric_values = [
            float(value)
            for value in values
            if BehavioralTrendAnalyzer._is_number(
                value
            )
        ]

        if len(numeric_values) == len(values):
            return sum(numeric_values) / len(
                numeric_values
            )

        counter = Counter(
            repr(value)
            for value in values
        )

        representative_repr = counter.most_common(
            1
        )[0][0]

        for value in values:
            if repr(value) == representative_repr:
                return value

        return values[0]

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(
            value,
            (int, float),
        ) and not isinstance(
            value,
            bool,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )
