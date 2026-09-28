from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class FeatureVector:
    """
    Numerical representation of one behavioral pattern.

    One FeatureVector represents exactly one behavioral pattern.
    """

    pattern_id: str

    knowledge_id: str

    features: Dict[str, float]

    feature_names: tuple[str, ...]

    def as_vector(self) -> tuple[float, ...]:
        """
        Return feature values in the declared feature-name order.

        The ordering is deterministic so that the same feature
        column always represents the same characteristic.
        """

        return tuple(
            self.features[name]
            for name in self.feature_names
        )

    def dimension(self) -> int:
        """
        Return the number of features in this vector.
        """

        return len(self.feature_names)

    def is_complete(self) -> bool:
        """
        Return True when every declared feature exists.
        """

        return all(
            name in self.features
            for name in self.feature_names
        )
