from __future__ import annotations

import math
from collections.abc import Callable, Mapping


Normalizer = Callable[[float], float]


class NormalizationEngine:
    """
    Applies explicitly supplied normalization rules to numerical
    behavioral features.

    The engine does not invent normalization rules or behavioral
    transformations. Each feature's numerical transformation is
    supplied by the caller.
    """

    @staticmethod
    def normalize_features(
        features: Mapping[str, float],
        normalizers: Mapping[str, Normalizer],
    ) -> dict[str, float]:
        """
        Normalize numerical features using the supplied rules.

        Every feature must have an explicitly supplied normalizer.

        Raises:
            ValueError: if a feature has no normalization rule,
                        or if input/output values are invalid.
        """

        normalized: dict[str, float] = {}

        for feature_name, value in features.items():
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Feature '{feature_name}' must have a numerical value."
                )

            numeric_value = float(value)

            if not math.isfinite(numeric_value):
                raise ValueError(
                    f"Feature '{feature_name}' contains a non-finite value."
                )

            normalizer = normalizers.get(feature_name)

            if normalizer is None:
                raise ValueError(
                    f"No normalization rule supplied for "
                    f"feature '{feature_name}'."
                )

            normalized_value = normalizer(numeric_value)

            if not isinstance(normalized_value, (int, float)):
                raise ValueError(
                    f"Normalizer for feature '{feature_name}' "
                    f"must return a numerical value."
                )

            normalized_value = float(normalized_value)

            if not math.isfinite(normalized_value):
                raise ValueError(
                    f"Normalizer for feature '{feature_name}' "
                    f"returned a non-finite value."
                )

            normalized[feature_name] = normalized_value

        return normalized
