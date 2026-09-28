from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureMatrix:
    """
    ML-ready matrix formed from multiple FeatureVector instances.

    Each row corresponds to exactly one behavioral pattern.
    Each column corresponds to one feature name.
    """

    feature_names: tuple[str, ...]
    rows: tuple[tuple[float, ...], ...]
    pattern_ids: tuple[str, ...]
    knowledge_ids: tuple[str, ...]

    def row_count(self) -> int:
        """Return the number of feature-vector rows."""
        return len(self.rows)

    def column_count(self) -> int:
        """Return the number of feature columns."""
        return len(self.feature_names)

    def as_matrix(self) -> tuple[tuple[float, ...], ...]:
        """Return the numerical matrix."""
        return self.rows
