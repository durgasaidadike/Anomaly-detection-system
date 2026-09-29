from feature_vector_models import FeatureVector
from ml_model_contracts import MLModel


class DummyModel:
    @property
    def model_name(self) -> str:
        return "DummyModel"

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
    assert model.predict(vector) == 0.5
