from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


class FeatureValidator:
    """
    Validates the structural and numerical integrity of an ML feature
    representation.

    This validator does not determine whether a feature is behaviorally
    useful, redundant, or statistically important.
    """

    @staticmethod
    def validate(
        *,
        pattern_id: str,
        knowledge_id: str,
        features: Mapping[str, float],
        feature_names: Sequence[str],
    ) -> None:
        """
        Validate a feature representation before vector formation.

        Raises:
            ValueError: when the representation violates the structural
                        or numerical contract.
        """

        if not isinstance(pattern_id, str) or not pattern_id.strip():
            raise ValueError("pattern_id must be a non-empty string.")

        if not isinstance(knowledge_id, str) or not knowledge_id.strip():
            raise ValueError("knowledge_id must be a non-empty string.")

        normalized_names = tuple(feature_names)

        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError("Feature names must be unique.")

        feature_keys = set(features.keys())
        declared_keys = set(normalized_names)

        missing_features = declared_keys - feature_keys

        if missing_features:
            raise ValueError(
                f"Feature representation is incomplete. "
                f"Missing features: {tuple(sorted(missing_features))}"
            )

        undeclared_features = feature_keys - declared_keys

        if undeclared_features:
            raise ValueError(
                f"Feature representation contains undeclared features: "
                f"{tuple(sorted(undeclared_features))}"
            )

        for feature_name in normalized_names:
            value = features[feature_name]

            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Feature '{feature_name}' must be numerical."
                )

            numeric_value = float(value)

            if not math.isfinite(numeric_value):
                raise ValueError(
                    f"Feature '{feature_name}' must contain a finite value."
                )
