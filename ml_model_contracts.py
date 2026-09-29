from __future__ import annotations

from typing import Protocol

from feature_vector_models import FeatureVector


class MLModel(Protocol):
    """
    Contract implemented by every PRISM anomaly-detection model.

    A model receives one standardized FeatureVector and returns
    one numerical prediction score.
    """

    @property
    def model_name(self) -> str:
        """
        Return the stable name of the model.
        """
        ...

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        """
        Evaluate one FeatureVector and return the model's
        numerical prediction score.
        """
        ...
