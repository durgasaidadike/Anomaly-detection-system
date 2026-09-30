from __future__ import annotations

from sklearn.covariance import EllipticEnvelope
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

from ensemble_result_models import EnsembleResult
from feature_vector_models import FeatureVector
from machine_learning_engine import MachineLearningEngine
from ml_inference_engine import MLInferenceEngine
from ml_model_adapters import (
    EllipticEnvelopeAdapter,
    IsolationForestAdapter,
    LocalOutlierFactorAdapter,
    OneClassSVMAdapter,
)
from ml_model_registry import MLModelRegistry
from score_calibration import ScoreCalibrationEngine
from score_fusion import WeightedScoreFusion


def make_training_data():
    return [
        [0.10, 0.20, 0.30, 0.40],
        [0.12, 0.21, 0.29, 0.41],
        [0.11, 0.19, 0.31, 0.39],
        [0.13, 0.22, 0.28, 0.42],
        [0.09, 0.18, 0.32, 0.38],
        [0.14, 0.23, 0.27, 0.43],
        [0.08, 0.17, 0.33, 0.37],
        [0.15, 0.24, 0.26, 0.44],
        [0.10, 0.21, 0.30, 0.40],
        [0.11, 0.20, 0.29, 0.41],
        [0.12, 0.19, 0.31, 0.39],
        [0.13, 0.22, 0.28, 0.42],
        [0.09, 0.18, 0.32, 0.38],
        [0.14, 0.23, 0.27, 0.43],
        [0.08, 0.17, 0.33, 0.37],
        [0.15, 0.24, 0.26, 0.44],
    ]
def make_feature_vector() -> FeatureVector:
    return FeatureVector(
        pattern_id="four-model-pattern",
        knowledge_id="four-model-knowledge",
        features={
            "feature_1": 0.11,
            "feature_2": 0.20,
            "feature_3": 0.30,
            "feature_4": 0.40,
        },
        feature_names=(
            "feature_1",
            "feature_2",
            "feature_3",
            "feature_4",
        ),
    )


def build_real_model_adapters():
    training_data = make_training_data()

    isolation_forest = IsolationForest(
        random_state=42,
        n_estimators=50,
    )
    isolation_forest.fit(training_data)

    lof = LocalOutlierFactor(
        novelty=True,
    )
    lof.fit(training_data)

    one_class_svm = OneClassSVM()
    one_class_svm.fit(training_data)

    elliptic_envelope = EllipticEnvelope(
        random_state=42,
    )
    elliptic_envelope.fit(training_data)

    return (
        IsolationForestAdapter(
            isolation_forest
        ),
        LocalOutlierFactorAdapter(
            lof
        ),
        OneClassSVMAdapter(
            one_class_svm
        ),
        EllipticEnvelopeAdapter(
            elliptic_envelope
        ),
    )


def build_engine():
    adapters = build_real_model_adapters()

    registry = MLModelRegistry()

    for adapter in adapters:
        registry.register(adapter)

    inference_engine = MLInferenceEngine(
        registry=registry
    )

    calibration_functions = {
        adapter.model_name: lambda score: score
        for adapter in adapters
    }

    calibration_engine = ScoreCalibrationEngine(
        calibration_functions
    )

    fusion_weights = {
        adapter.model_name: 1.0
        for adapter in adapters
    }

    fusion_engine = WeightedScoreFusion(
        fusion_weights
    )

    engine = MachineLearningEngine(
        registry=registry,
        inference_engine=inference_engine,
        calibration_engine=calibration_engine,
        fusion_engine=fusion_engine,
    )

    return engine, adapters

def test_real_four_model_prism_pipeline():
    engine, adapters = build_engine()

    result = engine.predict(
        make_feature_vector()
    )

    assert isinstance(
        result,
        EnsembleResult,
    )

    assert result.pattern_id == (
        "four-model-pattern"
    )

    assert result.knowledge_id == (
        "four-model-knowledge"
    )

    assert result.successful_model_count() == 4
    assert result.failed_model_count() == 0

    assert len(result.model_scores) == 4
    assert len(result.calibrated_scores) == 4

    assert set(
        score.model_name
        for score in result.model_scores
    ) == set(
        adapter.model_name
        for adapter in adapters
    )

    assert set(
        score.model_name
        for score in result.calibrated_scores
    ) == set(
        adapter.model_name
        for adapter in adapters
    )

    assert result.metadata.successful_model_names == (
        tuple(
            adapter.model_name
            for adapter in adapters
        )
    )

    assert result.metadata.failed_model_names == ()

    assert isinstance(
        result.anomaly_score,
        float,
    )


def test_real_four_model_pipeline_produces_finite_scores():
    import math

    engine, _ = build_engine()

    result = engine.predict(
        make_feature_vector()
    )

    assert math.isfinite(
        result.anomaly_score
    )

    for score in result.model_scores:
        assert math.isfinite(
            score.score
        )

    for score in result.calibrated_scores:
        assert math.isfinite(
            score.calibrated_score
        )


def test_real_four_model_pipeline_preserves_input():
    engine, _ = build_engine()

    vector = make_feature_vector()

    original_features = dict(
        vector.features
    )

    original_names = vector.feature_names

    engine.predict(vector)

    assert vector.features == (
        original_features
    )

    assert vector.feature_names == (
        original_names
    )

