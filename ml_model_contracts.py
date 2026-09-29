from __future__ import annotations

from typing import Protocol

from feature_vector_models import FeatureVector
from score_semantics import ScoreDirection


class MLModel(Protocol):
    """
    Contract implemented by every PRISM anomaly-detection model.

    A model receives one standardized FeatureVector and returns
    one numerical prediction score together with its score semantics.
    """

    @property
    def model_name(self) -> str:
        ...

    @property
    def score_direction(self) -> ScoreDirection:
        """
        Describe how the raw model score relates to anomaly severity.
        """
        ...

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        """
        Evaluate one FeatureVector and return the model's
        raw numerical prediction score.
        """
        ...
