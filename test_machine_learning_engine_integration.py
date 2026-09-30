import pytest

from ensemble_result_models import EnsembleResult
from feature_extractor import FeatureExtractor
from feature_vector_models import FeatureVector
from machine_learning_engine import MachineLearningEngine
from ml_inference_engine import MLInferenceEngine
from ml_model_registry import MLModelRegistry
from score_calibration import ScoreCalibrationEngine
from score_fusion import WeightedScoreFusion
from score_semantics import ScoreDirection


class ControlledModel:
    def __init__(
        self,
        name: str,
        score: float,
        direction: ScoreDirection = (
            ScoreDirection.LOWER_IS_MORE_ANOMALOUS
        ),
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
        assert isinstance(vector, FeatureVector)
        assert vector.is_complete()
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
        raise RuntimeError("controlled model failure")


def build_feature_vector() -> FeatureVector:
    extractor = FeatureExtractor()

    groups = extractor.separate_features(
        operation={
            "modify_ratio": 0.8,
        },
        temporal={
            "burst_score": 0.2,
        },
        sequence={
            "transition_score": 0.5,
        },
        contextual={
            "directory_score": 0.4,
        },
        session={
            "session_length": 12.0,
        },
        intelligence={
            "confidence": 0.9,
        },
        recurrence={
            "pattern_recurrence": 3.0,
        },
        drift={
            "drift_score": 0.1,
        },
    )

    features, feature_names = extractor.construct_features(
        groups
    )

    return extractor.build_feature_vector(
        pattern_id="pattern-integration-1",
        knowledge_id="knowledge-integration-1",
        features=features,
        feature_names=feature_names,
    )


def build_engine(models, weights):
    registry = MLModelRegistry()

    for model in models:
        registry.register(model)

    inference_engine = MLInferenceEngine(
        registry=registry,
    )

    calibration_engine = ScoreCalibrationEngine(
        {
            model.model_name: lambda score: score
            for model in models
            if not isinstance(model, FailingModel)
        }
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


def test_module_10_feature_vector_reaches_module_11():
    vector = build_feature_vector()

    assert isinstance(vector, FeatureVector)
    assert vector.is_complete()

    engine = build_engine(
        models=(
            ControlledModel(
                "model_a",
                -0.2,
            ),
            ControlledModel(
                "model_b",
                -0.4,
            ),
        ),
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(vector)

    assert isinstance(result, EnsembleResult)


def test_end_to_end_identity_is_preserved():
    vector = build_feature_vector()

    engine = build_engine(
        models=(
            ControlledModel(
                "model_a",
                -0.2,
            ),
            ControlledModel(
                "model_b",
                -0.4,
            ),
        ),
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(vector)

    assert result.pattern_id == vector.pattern_id
    assert result.knowledge_id == vector.knowledge_id

def test_end_to_end_model_scores_are_available():
    vector = build_feature_vector()

    engine = build_engine(
        models=(
            ControlledModel(
                "model_a",
                -0.2,
            ),
            ControlledModel(
                "model_b",
                -0.4,
            ),
        ),
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(vector)

    assert len(result.model_scores) == 2

    assert {
        score.model_name
        for score in result.model_scores
    } == {
        "model_a",
        "model_b",
    }


def test_end_to_end_calibration_and_fusion_are_applied():
    vector = build_feature_vector()

    registry = MLModelRegistry()

    registry.register(
        ControlledModel(
            "model_a",
            -0.2,
        )
    )

    registry.register(
        ControlledModel(
            "model_b",
            -0.6,
        )
    )

    inference_engine = MLInferenceEngine(
        registry=registry,
    )

    calibration_engine = ScoreCalibrationEngine(
        {
            "model_a": lambda score: score * 2.0,
            "model_b": lambda score: score * 4.0,
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

    result = engine.predict(vector)

    # Raw model_a = -0.2
    # canonical anomaly score = 0.2
    # calibrated = 0.4
    #
    # Raw model_b = -0.6
    # canonical anomaly score = 0.6
    # calibrated = 2.4
    #
    # Equal-weight fusion = 1.4

    assert result.calibrated_scores[0].calibrated_score == (
        pytest.approx(0.4)
    )

    assert result.calibrated_scores[1].calibrated_score == (
        pytest.approx(2.4)
    )

    assert result.anomaly_score == pytest.approx(1.4)


def test_partial_model_failure_reaches_final_result():
    vector = build_feature_vector()

    engine = build_engine(
        models=(
            ControlledModel(
                "model_a",
                -0.2,
            ),
            FailingModel(
                "model_b",
            ),
            ControlledModel(
                "model_c",
                -0.6,
            ),
        ),
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
            "model_c": 1.0,
        },
    )

    result = engine.predict(vector)

    assert result.successful_model_count() == 2
    assert result.failed_model_count() == 1

    assert {
        score.model_name
        for score in result.model_scores
    } == {
        "model_a",
        "model_c",
    }

    assert result.metadata.successful_model_names == (
        "model_a",
        "model_c",
    )

    assert result.metadata.failed_model_names == (
        "model_b",
    )


def test_feature_vector_is_not_modified_by_ml_engine():
    vector = build_feature_vector()

    original_features = dict(vector.features)
    original_names = vector.feature_names

    engine = build_engine(
        models=(
            ControlledModel(
                "model_a",
                -0.2,
            ),
            ControlledModel(
                "model_b",
                -0.4,
            ),
        ),
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    engine.predict(vector)

    assert vector.features == original_features
    assert vector.feature_names == original_names


def test_output_is_suitable_for_decision_engine_boundary():
    vector = build_feature_vector()

    engine = build_engine(
        models=(
            ControlledModel(
                "model_a",
                -0.2,
            ),
            ControlledModel(
                "model_b",
                -0.4,
            ),
        ),
        weights={
            "model_a": 1.0,
            "model_b": 1.0,
        },
    )

    result = engine.predict(vector)

    # These are the ML -> Decision boundary data.
    assert isinstance(result.anomaly_score, float)
    assert result.model_scores
    assert result.metadata is not None

    # ML does not produce a business decision here.
    assert not hasattr(result, "risk_level")
    assert not hasattr(result, "recommended_action")
