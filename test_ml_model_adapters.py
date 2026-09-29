import numpy as np
import pytest

from feature_vector_models import FeatureVector
from ml_model_adapters import (
    EllipticEnvelopeAdapter,
    IsolationForestAdapter,
    LocalOutlierFactorAdapter,
    OneClassSVMAdapter,
)


class DecisionFunctionEstimator:
    def __init__(self, result):
        self.result = result

    def decision_function(self, values):
        return np.asarray([self.result])


class ScoreSamplesEstimator:
    def __init__(self, result):
        self.result = result

    def score_samples(self, values):
        return np.asarray([self.result])


def build_vector():
    return FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "feature-1": 0.10,
            "feature-2": 0.20,
            "feature-3": 0.30,
            "feature-4": 0.40,
        },
        feature_names=(
            "feature-1",
            "feature-2",
            "feature-3",
            "feature-4",
        ),
    )


@pytest.mark.parametrize(
    "adapter",
    [
        IsolationForestAdapter(
            DecisionFunctionEstimator(-0.23)
        ),
        OneClassSVMAdapter(
            DecisionFunctionEstimator(-0.91)
        ),
        EllipticEnvelopeAdapter(
            DecisionFunctionEstimator(0.65)
        ),
    ],
)
def test_decision_function_adapters_preserve_raw_score(adapter):
    vector = build_vector()

    result = adapter.predict(vector)

    assert result in (-0.23, -0.91, 0.65)


def test_lof_adapter_uses_score_samples():
    adapter = LocalOutlierFactorAdapter(
        ScoreSamplesEstimator(-1.78)
    )

    result = adapter.predict(build_vector())

    assert result == -1.78


def test_model_names_are_stable():
    assert (
        IsolationForestAdapter(
            DecisionFunctionEstimator(0.1)
        ).model_name
        == "IsolationForest"
    )

    assert (
        LocalOutlierFactorAdapter(
            ScoreSamplesEstimator(0.1)
        ).model_name
        == "LocalOutlierFactor"
    )

    assert (
        OneClassSVMAdapter(
            DecisionFunctionEstimator(0.1)
        ).model_name
        == "OneClassSVM"
    )

    assert (
        EllipticEnvelopeAdapter(
            DecisionFunctionEstimator(0.1)
        ).model_name
        == "EllipticEnvelope"
    )


@pytest.mark.parametrize(
    "adapter",
    [
        IsolationForestAdapter(
            DecisionFunctionEstimator(0.1)
        ),
        LocalOutlierFactorAdapter(
            ScoreSamplesEstimator(0.1)
        ),
        OneClassSVMAdapter(
            DecisionFunctionEstimator(0.1)
        ),
        EllipticEnvelopeAdapter(
            DecisionFunctionEstimator(0.1)
        ),
    ],
)
def test_adapter_rejects_non_feature_vector(adapter):
    with pytest.raises(TypeError):
        adapter.predict(
            {
                "feature-1": 0.1,
            }
        )


def test_adapter_rejects_incomplete_feature_vector():
    adapter = IsolationForestAdapter(
        DecisionFunctionEstimator(0.1)
    )

    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "feature-1": 0.1,
        },
        feature_names=(
            "feature-1",
            "feature-2",
        ),
    )

    with pytest.raises(ValueError):
        adapter.predict(vector)


def test_adapter_rejects_unexpected_prediction_shape():
    class BadEstimator:
        def decision_function(self, values):
            return np.asarray(
                [
                    [0.1, 0.2],
                ]
            )

    adapter = IsolationForestAdapter(
        BadEstimator()
    )

    with pytest.raises(ValueError):
        adapter.predict(build_vector())


def test_negative_scores_are_not_absorbed():
    adapter = IsolationForestAdapter(
        DecisionFunctionEstimator(-0.55)
    )

    result = adapter.predict(build_vector())

    assert result == -0.55


from sklearn.covariance import EllipticEnvelope
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM


def build_training_data():
    return np.array(
        [
            [0.10, 0.20, 0.30, 0.40],
            [0.11, 0.21, 0.31, 0.41],
            [0.12, 0.22, 0.32, 0.42],
            [0.13, 0.23, 0.33, 0.43],
            [0.14, 0.24, 0.34, 0.44],
            [0.15, 0.25, 0.35, 0.45],
            [0.16, 0.26, 0.36, 0.46],
            [0.17, 0.27, 0.37, 0.47],
            [0.18, 0.28, 0.38, 0.48],
            [0.19, 0.29, 0.39, 0.49],
            [0.20, 0.30, 0.40, 0.50],
            [0.21, 0.31, 0.41, 0.51],
            [0.22, 0.32, 0.42, 0.52],
            [0.23, 0.33, 0.43, 0.53],
            [0.24, 0.34, 0.44, 0.54],
            [0.25, 0.35, 0.45, 0.55],
            [0.26, 0.36, 0.46, 0.56],
            [0.27, 0.37, 0.47, 0.57],
            [0.28, 0.38, 0.48, 0.58],
            [0.29, 0.39, 0.49, 0.59],
        ]
    )


def test_real_isolation_forest_adapter():
    model = IsolationForest(
        random_state=42,
    )
    model.fit(build_training_data())

    adapter = IsolationForestAdapter(model)

    result = adapter.predict(build_vector())

    assert isinstance(result, float)
    assert np.isfinite(result)


def test_real_lof_adapter():
    model = LocalOutlierFactor(
        novelty=True,
    )
    model.fit(build_training_data())

    adapter = LocalOutlierFactorAdapter(model)

    result = adapter.predict(build_vector())

    assert isinstance(result, float)
    assert np.isfinite(result)


def test_real_one_class_svm_adapter():
    model = OneClassSVM(
        gamma="auto",
    )
    model.fit(build_training_data())

    adapter = OneClassSVMAdapter(model)

    result = adapter.predict(build_vector())

    assert isinstance(result, float)
    assert np.isfinite(result)


def test_real_elliptic_envelope_adapter():
    model = EllipticEnvelope(
        random_state=42,
    )
    model.fit(build_training_data())

    adapter = EllipticEnvelopeAdapter(model)

    result = adapter.predict(build_vector())

    assert isinstance(result, float)
    assert np.isfinite(result)
