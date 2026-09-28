from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class FeatureGroups:
    """
    Numerically prepared feature groups extracted from one
    behavioral pattern.

    Each group preserves a distinct behavioral characteristic
    before the groups are combined into a FeatureVector.
    """

    operation: Mapping[str, float]
    temporal: Mapping[str, float]
    sequence: Mapping[str, float]
    contextual: Mapping[str, float]
    session: Mapping[str, float]
    intelligence: Mapping[str, float]
    recurrence: Mapping[str, float]
    drift: Mapping[str, float]

    def as_groups(self) -> dict[str, Mapping[str, float]]:
        """
        Return the separated feature groups by category.
        """

        return {
            "operation": self.operation,
            "temporal": self.temporal,
            "sequence": self.sequence,
            "contextual": self.contextual,
            "session": self.session,
            "intelligence": self.intelligence,
            "recurrence": self.recurrence,
            "drift": self.drift,
        }
