import pytest

from ml_model_registry import MLModelRegistry


class DummyModel:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def model_name(self) -> str:
        return self._name

    def predict(self, vector):
        return 0.5


def test_registry_starts_empty():
    registry = MLModelRegistry()

    assert registry.count() == 0
    assert registry.names() == ()
    assert registry.models() == ()


def test_registry_registers_model():
    registry = MLModelRegistry()
    model = DummyModel("IsolationForest")

    registry.register(model)

    assert registry.count() == 1
    assert registry.get("IsolationForest") is model


def test_registry_preserves_registration_order():
    registry = MLModelRegistry()

    registry.register(DummyModel("IsolationForest"))
    registry.register(DummyModel("LocalOutlierFactor"))
    registry.register(DummyModel("OneClassSVM"))

    assert registry.names() == (
        "IsolationForest",
        "LocalOutlierFactor",
        "OneClassSVM",
    )


def test_registry_returns_models_as_tuple():
    registry = MLModelRegistry()

    first = DummyModel("IsolationForest")
    second = DummyModel("LocalOutlierFactor")

    registry.register(first)
    registry.register(second)

    assert registry.models() == (
        first,
        second,
    )


def test_duplicate_model_name_is_rejected():
    registry = MLModelRegistry()

    registry.register(
        DummyModel("IsolationForest")
    )

    with pytest.raises(ValueError):
        registry.register(
            DummyModel("IsolationForest")
        )


@pytest.mark.parametrize(
    "model",
    [
        None,
        object(),
    ],
)
def test_invalid_model_is_rejected(model):
    registry = MLModelRegistry()

    with pytest.raises(ValueError):
        registry.register(model)


def test_empty_model_name_is_rejected():
    registry = MLModelRegistry()

    with pytest.raises(ValueError):
        registry.register(DummyModel(""))


def test_missing_predict_method_is_rejected():
    registry = MLModelRegistry()

    class InvalidModel:
        model_name = "InvalidModel"

    with pytest.raises(ValueError):
        registry.register(InvalidModel())


def test_registry_does_not_expose_mutable_model_mapping():
    registry = MLModelRegistry()

    registry.register(
        DummyModel("IsolationForest")
    )

    assert not isinstance(
        registry.models(),
        dict,
    )
