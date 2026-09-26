from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any, Dict, Optional


class PatternComparator:
    """
    Compares the behavioral representation of a Candidate Pattern
    with a historical Final Pattern.

    The comparator measures behavioral resemblance only.

    It does not:
    - perform anomaly detection
    - perform machine learning
    - modify either pattern
    - access persistence
    - make security decisions
    """

    DIMENSIONS = (
        "operational",
        "temporal",
        "sequential",
        "contextual",
        "relationship",
        "session",
    )

    def compare(
        self,
        candidate_pattern: Any,
        historical_pattern: Any,
    ) -> Dict[str, Optional[float]]:
        """
        Compare the supported behavioral dimensions.

        A dimension receives None when there is not enough
        behavioral information on either side to perform a
        meaningful comparison.

        Returned scores are otherwise normalized to [0.0, 1.0].
        """

        return {
            "operational": self.compare_dimension(
                getattr(
                    candidate_pattern,
                    "operational_characteristics",
                    None,
                ),
                getattr(
                    historical_pattern,
                    "operational_characteristics",
                    None,
                ),
            ),
            "temporal": self.compare_dimension(
                getattr(
                    candidate_pattern,
                    "temporal_characteristics",
                    None,
                ),
                getattr(
                    historical_pattern,
                    "temporal_characteristics",
                    None,
                ),
            ),
            "sequential": self.compare_dimension(
                getattr(
                    candidate_pattern,
                    "sequential_characteristics",
                    None,
                ),
                getattr(
                    historical_pattern,
                    "sequential_characteristics",
                    None,
                ),
            ),
            "contextual": self.compare_dimension(
                getattr(
                    candidate_pattern,
                    "contextual_characteristics",
                    None,
                ),
                getattr(
                    historical_pattern,
                    "contextual_characteristics",
                    None,
                ),
            ),
            "relationship": self.compare_dimension(
                getattr(
                    candidate_pattern,
                    "relationship_characteristics",
                    None,
                ),
                getattr(
                    historical_pattern,
                    "relationship_characteristics",
                    None,
                ),
            ),
            "session": self.compare_dimension(
                getattr(
                    candidate_pattern,
                    "session_characteristics",
                    None,
                ),
                getattr(
                    historical_pattern,
                    "session_characteristics",
                    None,
                ),
            ),
        }

    def compare_dimension(
        self,
        candidate_value: Any,
        historical_value: Any,
    ) -> Optional[float]:
        """
        Compare two values belonging to one behavioral dimension.

        Returns:
            None -> insufficient behavioral information
            0.0..1.0 -> normalized resemblance
        """

        if not self._has_information(candidate_value):
            return None

        if not self._has_information(historical_value):
            return None

        return self._value_similarity(
            candidate_value,
            historical_value,
        )


    def _value_similarity(
        self,
        candidate_value: Any,
        historical_value: Any,
    ) -> float:
        """
        Recursively calculate structural similarity.
        """

        if candidate_value is None and historical_value is None:
            return 1.0

        if candidate_value is None or historical_value is None:
            return 0.0

        if isinstance(candidate_value, bool) or isinstance(
            historical_value,
            bool,
        ):
            return 1.0 if candidate_value == historical_value else 0.0

        if isinstance(candidate_value, (int, float)) and isinstance(
            historical_value,
            (int, float),
        ):
            return self._numeric_similarity(
                float(candidate_value),
                float(historical_value),
            )

        if isinstance(candidate_value, datetime) and isinstance(
            historical_value,
            datetime,
        ):
            return 1.0 if candidate_value == historical_value else 0.0

        if isinstance(candidate_value, dict) and isinstance(
            historical_value,
            dict,
        ):
            return self._mapping_similarity(
                candidate_value,
                historical_value,
            )

        if isinstance(candidate_value, (list, tuple)) and isinstance(
            historical_value,
            (list, tuple),
        ):
            return self._sequence_similarity(
                candidate_value,
                historical_value,
            )

        if isinstance(candidate_value, str) and isinstance(
            historical_value,
            str,
        ):
            return self._string_similarity(
                candidate_value,
                historical_value,
            )

        return (
            1.0
            if candidate_value == historical_value
            else 0.0
        )

    @staticmethod
    def _numeric_similarity(
        candidate_value: float,
        historical_value: float,
    ) -> float:
        """
        Compare numeric behavioral values.

        Identical values score 1.0.

        For different finite values, similarity decreases
        proportionally to their relative distance.
        """

        if not isfinite(candidate_value) or not isfinite(
            historical_value
        ):
            return 0.0

        if candidate_value == historical_value:
            return 1.0

        scale = max(
            abs(candidate_value),
            abs(historical_value),
            1.0,
        )

        distance = abs(
            candidate_value - historical_value
        )

        return max(
            0.0,
            min(
                1.0,
                1.0 - (distance / scale),
            ),
        )

    def _mapping_similarity(
        self,
        candidate_value: Dict[Any, Any],
        historical_value: Dict[Any, Any],
    ) -> float:
        """
        Compare dictionary-based behavioral structures.

        Keys are compared across the union of both mappings.
        """

        keys = set(candidate_value) | set(historical_value)

        if not keys:
            return 1.0

        total = 0.0

        for key in keys:
            candidate_has_key = key in candidate_value
            historical_has_key = key in historical_value

            if not candidate_has_key or not historical_has_key:
                continue

            total += self._value_similarity(
                candidate_value[key],
                historical_value[key],
            )

        common_keys = (
            set(candidate_value) & set(historical_value)
        )

        if not common_keys:
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                total / len(keys),
            ),
        )

    def _sequence_similarity(
        self,
        candidate_value: tuple | list,
        historical_value: tuple | list,
    ) -> float:
        """
        Compare ordered behavioral structures.

        Positional resemblance is combined with a length
        consistency factor so that both sequence content
        and workflow size contribute to the result.
        """

        candidate_length = len(candidate_value)
        historical_length = len(historical_value)

        if candidate_length == 0 and historical_length == 0:
            return 1.0

        if candidate_length == 0 or historical_length == 0:
            return 0.0

        shared_length = min(
            candidate_length,
            historical_length,
        )

        positional_score = sum(
            self._value_similarity(
                candidate_value[index],
                historical_value[index],
            )
            for index in range(shared_length)
        ) / shared_length

        length_similarity = min(
            candidate_length,
            historical_length,
        ) / max(
            candidate_length,
            historical_length,
        )

        return max(
            0.0,
            min(
                1.0,
                positional_score * length_similarity,
            ),
        )

    @staticmethod
    def _string_similarity(
        candidate_value: str,
        historical_value: str,
    ) -> float:
        """
        Compare textual behavioral values.

        Exact values receive full similarity.
        Otherwise token overlap is used to preserve partial
        behavioral resemblance.
        """

        candidate_text = candidate_value.strip().lower()
        historical_text = historical_value.strip().lower()

        if candidate_text == historical_text:
            return 1.0

        if not candidate_text or not historical_text:
            return 0.0

        candidate_tokens = set(
            candidate_text.split()
        )

        historical_tokens = set(
            historical_text.split()
        )

        union = candidate_tokens | historical_tokens

        if not union:
            return 1.0

        intersection = (
            candidate_tokens & historical_tokens
        )

        return len(intersection) / len(union)

    @staticmethod
    def _has_information(value: Any) -> bool:
        """
        Determine whether a behavioral value contains
        meaningful information.

        Empty containers and None are considered unavailable.
        Numeric zero and False remain valid information.
        """

        if value is None:
            return False

        if isinstance(value, (dict, list, tuple, set)):
            return len(value) > 0

        if isinstance(value, str):
            return bool(value.strip())

        return True

