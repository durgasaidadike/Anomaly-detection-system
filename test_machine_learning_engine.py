import pytest

from ensemble_result_models import EnsembleResult
from feature_vector_models import FeatureVector
from ml_inference_engine import MLInferenceEngine
from ml_model_registry import MLModelRegistry
from score_calibration import ScoreCalibrationEngine
from score_fusion import WeightedScoreFusion
from score_semantics import ScoreDirection
from machine_learning_engine import MachineLearningEngine


class StubModel:
    def __init__(
        self,
        name: str,
        score: float,
        *,
        direction=ScoreDirection.LOWER_IS_MORE_ANOMALOUS,
    ):
        self._name = name
        self._score = score
        self._direction = direction

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def score_direction(self) -> ScoreDirection:
        return self._direction

    def predict(self, vector: FeatureVector) -> float:
        return self._score


class FailingModel:
    def __init__(self, name: str):
        self._name = name

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def score_direction(self) -> ScoreDirection:
        return ScoreDirection.LOWER_IS_MORE_ANOMALOUS

    def predict(self, vector: FeatureVector) -> float:
        raise RuntimeError("model unavailable")


def make_vector() -> FeatureVector:
    return FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "operation.modify": 0.8,
            "temporal.burst": 0.2,
        },
        feature_names=(
            "operation.modify",
            "temporal.burst",
        ),
    )


def make_engine(
    *,
    model_one,
    model_two,
    calibration_functions,
    weights,
):
    registry = MLModelRegistry()

    registry.register(model_one)
    registry.register(model_two)

    inference_engine = MLInferenceEngine(
        registry=registry,
    )

    calibration_engine = ScoreCalibrationEngine(
        calibration_functions
    )

    fusion_engine = WeightedScoreFusion(
        weights
    )

    return MachineLearningEngine(
        registry=registry,
        inference_engine=inference_engine,
        calibration_engine=calibration_engine,
        fusion_engine=fusion_engine,
    )


def test_public_engine_returns_ensemble_result():
    engine = make_engine(
        model_one=StubModel(
            "model_a",
            -0.2,
        ),
        model_two=StubModel(
            "model_b",
            -0.4,
        ),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(make_vector())

    assert isinstance(result, EnsembleResult)


def test_public_engine_preserves_pattern_identity():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(make_vector())

    assert result.pattern_id == "pattern-1"
    assert result.knowledge_id == "knowledge-1"


def test_public_engine_collects_model_scores():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(make_vector())

    assert tuple(
        score.model_name
        for score in result.model_scores
    ) == (
        "model_a",
        "model_b",
    )
def test_public_engine_calibrates_each_model():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score * 2.0,
            "model_b": lambda score: score * 3.0,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(make_vector())

    assert result.calibrated_scores[0].canonical_score == pytest.approx(
        0.2
    )

    assert result.calibrated_scores[0].calibrated_score == pytest.approx(
        0.4
    )

    assert result.calibrated_scores[1].canonical_score == pytest.approx(
        0.4
    )

    assert result.calibrated_scores[1].calibrated_score == pytest.approx(
        1.2
    )


def test_public_engine_fuses_calibrated_scores():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(make_vector())

    assert result.anomaly_score == pytest.approx(
        0.3
    )


def test_public_engine_builds_metadata():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(make_vector())

    assert result.metadata.configured_model_names == (
        "model_a",
        "model_b",
    )

    assert result.metadata.successful_model_names == (
        "model_a",
        "model_b",
    )

    assert result.metadata.failed_model_names == ()


def test_public_engine_preserves_partial_model_failure():
    registry = MLModelRegistry()

    registry.register(
        StubModel("model_a", -0.2)
    )

    registry.register(
        FailingModel("model_b")
    )

    inference_engine = MLInferenceEngine(
        registry=registry,
    )

    calibration_engine = ScoreCalibrationEngine(
        {
            "model_a": lambda score: score,
        }
    )

    fusion_engine = WeightedScoreFusion(
        {
            "model_a": 1.0,
            "model_b": 1.0,
        }
    )

    engine = MachineLearningEngine(
        registry=registry,
        inference_engine=inference_engine,
        calibration_engine=calibration_engine,
        fusion_engine=fusion_engine,
    )

    result = engine.predict(make_vector())

    assert result.successful_model_count() == 1
    assert result.failed_model_count() == 1

    assert result.metadata.successful_model_names == (
        "model_a",
    )

    assert result.metadata.failed_model_names == (
        "model_b",
    )

    assert result.failures[0].model_name == "model_b"

def test_public_engine_rejects_wrong_input_type():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    with pytest.raises(TypeError):
        engine.predict("not-a-feature-vector")


def test_public_engine_rejects_incomplete_feature_vector():
    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    incomplete_vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "operation.modify": 0.8,
        },
        feature_names=(
            "operation.modify",
            "temporal.burst",
        ),
    )

    with pytest.raises(ValueError):
        engine.predict(incomplete_vector)


def test_public_engine_fails_when_every_model_fails():
    registry = MLModelRegistry()

    registry.register(FailingModel("model_a"))
    registry.register(FailingModel("model_b"))

    inference_engine = MLInferenceEngine(
        registry=registry,
    )

    calibration_engine = ScoreCalibrationEngine({})

    fusion_engine = WeightedScoreFusion(
        {
            "model_a": 1.0,
            "model_b": 1.0,
        }
    )

    engine = MachineLearningEngine(
        registry=registry,
        inference_engine=inference_engine,
        calibration_engine=calibration_engine,
        fusion_engine=fusion_engine,
    )

    with pytest.raises(RuntimeError):
        engine.predict(make_vector())


def test_public_engine_does_not_modify_feature_vector():
    vector = make_vector()

    original_features = dict(vector.features)
    original_names = vector.feature_names

    engine = make_engine(
        model_one=StubModel("model_a", -0.2),
        model_two=StubModel("model_b", -0.4),
        calibration_functions={
            "model_a": lambda score: score,
            "model_b": lambda score: score,
        },
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    engine.predict(vector)

    assert vector.features == original_features
    assert vector.feature_names == original_names

