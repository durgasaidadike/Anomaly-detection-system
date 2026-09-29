import pytest

from feature_vector_models import FeatureVector
from ml_inference_engine import MLInferenceEngine
from ml_model_registry import MLModelRegistry


class WorkingModel:
    def __init__(self, name, score):
        self._name = name
        self._score = score

    @property
    def model_name(self):
        return self._name

    def predict(self, vector):
        return self._score


class FailingModel:
    @property
    def model_name(self):
        return "FailingModel"

    def predict(self, vector):
        raise RuntimeError(
            "simulated model failure"
        )


def build_vector():
    return FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "feature-1": 0.1,
            "feature-2": 0.2,
        },
        feature_names=(
            "feature-1",
            "feature-2",
        ),
    )


def test_inference_engine_runs_registered_models():
    registry = MLModelRegistry()

    registry.register(
        WorkingModel(
            "IsolationForest",
            -0.25,
        )
    )

    registry.register(
        WorkingModel(
            "LocalOutlierFactor",
            -1.5,
        )
    )

    engine = MLInferenceEngine(registry)

    result = engine.predict(build_vector())

    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 0

    assert (
        result.evaluation.model_scores[0].model_name
        == "IsolationForest"
    )

    assert (
        result.evaluation.model_scores[0].score
        == -0.25
    )

    assert (
        result.evaluation.model_scores[1].model_name
        == "LocalOutlierFactor"
    )

    assert (
        result.evaluation.model_scores[1].score
        == -1.5
    )


def test_inference_engine_isolates_partial_model_failure():
    registry = MLModelRegistry()

    registry.register(
        WorkingModel(
            "IsolationForest",
            -0.25,
        )
    )

    registry.register(
        FailingModel()
    )

    registry.register(
        WorkingModel(
            "EllipticEnvelope",
            0.65,
        )
    )

    engine = MLInferenceEngine(registry)

    result = engine.predict(build_vector())

    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 1

    assert result.evaluation.model_scores[0].model_name == (
        "IsolationForest"
    )

    assert result.evaluation.model_scores[1].model_name == (
        "EllipticEnvelope"
    )

    assert result.failures[0].model_name == (
        "FailingModel"
    )


def test_inference_engine_rejects_non_feature_vector():
    registry = MLModelRegistry()

    engine = MLInferenceEngine(registry)

    with pytest.raises(TypeError):
        engine.predict(
            {
                "feature-1": 0.1,
            }
        )


def test_inference_engine_rejects_incomplete_vector():
    registry = MLModelRegistry()

    registry.register(
        WorkingModel(
            "IsolationForest",
            -0.25,
        )
    )

    engine = MLInferenceEngine(registry)

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
        engine.predict(vector)


def test_inference_engine_propagates_valid_model_score():
    registry = MLModelRegistry()

    registry.register(
        WorkingModel(
            "IsolationForest",
            -0.55,
        )
    )

    engine = MLInferenceEngine(registry)

    result = engine.predict(build_vector())

    assert result.evaluation.model_scores[0].score == (
        -0.55
    )


def test_inference_engine_handles_all_models_failing():
    registry = MLModelRegistry()

    registry.register(FailingModel())

    engine = MLInferenceEngine(registry)

    result = engine.predict(build_vector())

    assert result.successful_model_count() == 0
    assert result.failed_model_count() == 1
