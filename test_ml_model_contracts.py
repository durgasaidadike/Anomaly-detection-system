from feature_vector_models import FeatureVector
from ml_model_contracts import MLModel
from score_semantics import ScoreDirection


class DummyModel:
    @property
    def model_name(self) -> str:
        return "DummyModel"

    @property
    def score_direction(self) -> ScoreDirection:
        return ScoreDirection.LOWER_IS_MORE_ANOMALOUS

    def predict(
        self,
        vector: FeatureVector,
    ) -> float:
        return 0.5


def test_model_contract_accepts_feature_vector():
    model: MLModel = DummyModel()

    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-pattern-1",
        features={
            "operation.modify_ratio": 0.8,
        },
        feature_names=(
            "operation.modify_ratio",
        ),
    )

    assert model.model_name == "DummyModel"
    assert (
        model.score_direction
        == ScoreDirection.LOWER_IS_MORE_ANOMALOUS
    )
    assert model.predict(vector) == 0.5
