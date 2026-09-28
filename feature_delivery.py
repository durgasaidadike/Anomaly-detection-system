from __future__ import annotations

from typing import Protocol

from feature_vector_models import FeatureVector


class FeatureVectorSink(Protocol):
    """
    Contract for a downstream component that receives one
    ML-ready FeatureVector.

    The Feature Extractor knows only this contract.
    It does not know how the ML Engine performs inference.
    """

    def accept_feature_vector(
        self,
        vector: FeatureVector,
    ) -> None:
        """
        Accept one feature vector for downstream processing.
        """
        ...
