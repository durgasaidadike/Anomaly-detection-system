from __future__ import annotations

from typing import Any

import numpy as np

from feature_vector_models import FeatureVector
from ml_model_contracts import MLModel


class _SklearnModelAdapter:
    """
    Base adapter for PRISM's sklearn-backed anomaly models.

    The adapter is responsible only for translating a PRISM
    FeatureVector into the numerical matrix expected by the
    underlying estimator and returning that estimator's raw
    model score.

    It does not normalize scores, fuse scores, classify risk,
    or make decisions.
    """

    def __init__(self, estimator: Any) -> None:
        self._estimator = estimator

    @staticmethod
    def _feature_row(vector: FeatureVector) -> np.ndarray:
        if not isinstance(vector, FeatureVector):
            raise TypeError(
                "ML model adapters require a FeatureVector."
            )

        if not vector.is_complete():
            raise ValueError(
                f"Feature vector for pattern "
                f"'{vector.pattern_id}' is incomplete."
            )

        values = vector.as_vector()

        return np.asarray(
            values,
            dtype=float,
        ).reshape(1, -1)

    @staticmethod
    def _extract_scalar(
        result: Any,
        *,
        model_name: str,
    ) -> float:
        values = np.asarray(result)

        if values.size != 1:
            raise ValueError(
                f"Model '{model_name}' returned an unexpected "
                "prediction shape."
            )

        return float(values.reshape(-1)[0])


class IsolationForestAdapter(
    _SklearnModelAdapter,
):
    """
    Adapter for a fitted sklearn IsolationForest estimator.
    """

    @property
    def model_name(self) -> str:
        return "IsolationForest"

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        row = self._feature_row(vector)

        result = self._estimator.decision_function(row)

        return self._extract_scalar(
            result,
            model_name=self.model_name,
        )


class LocalOutlierFactorAdapter(
    _SklearnModelAdapter,
):
    """
    Adapter for a fitted sklearn LocalOutlierFactor estimator
    configured for novelty detection.
    """

    @property
    def model_name(self) -> str:
        return "LocalOutlierFactor"

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        row = self._feature_row(vector)

        result = self._estimator.score_samples(row)

        return self._extract_scalar(
            result,
            model_name=self.model_name,
        )


class OneClassSVMAdapter(
    _SklearnModelAdapter,
):
    """
    Adapter for a fitted sklearn OneClassSVM estimator.
    """

    @property
    def model_name(self) -> str:
        return "OneClassSVM"

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        row = self._feature_row(vector)

        result = self._estimator.decision_function(row)

        return self._extract_scalar(
            result,
            model_name=self.model_name,
        )


class EllipticEnvelopeAdapter(
    _SklearnModelAdapter,
):
    """
    Adapter for a fitted sklearn EllipticEnvelope estimator.
    """

    @property
    def model_name(self) -> str:
        return "EllipticEnvelope"

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        row = self._feature_row(vector)

        result = self._estimator.decision_function(row)

        return self._extract_scalar(
            result,
            model_name=self.model_name,
        )
