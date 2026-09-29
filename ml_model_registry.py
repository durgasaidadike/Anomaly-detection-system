from __future__ import annotations

from collections.abc import Iterator

from ml_model_contracts import MLModel


class MLModelRegistry:
    """
    Registry of loaded ML model implementations.

    The registry owns model lookup and registration only.
    It does not perform predictions, score fusion, or decisions.
    """

    def __init__(self) -> None:
        self._models: dict[str, MLModel] = {}

    def register(self, model: MLModel) -> None:
        if model is None:
            raise ValueError("ML model cannot be None.")

        model_name = getattr(model, "model_name", None)

        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError(
                "ML model must expose a non-empty model_name."
            )

        predict_method = getattr(model, "predict", None)

        if not callable(predict_method):
            raise ValueError(
                f"ML model '{model_name}' must provide a callable "
                "predict() method."
            )

        if model_name in self._models:
            raise ValueError(
                f"ML model '{model_name}' is already registered."
            )

        self._models[model_name] = model

    def get(self, model_name: str) -> MLModel | None:
        if not isinstance(model_name, str):
            return None

        return self._models.get(model_name)

    def names(self) -> tuple[str, ...]:
        return tuple(self._models.keys())

    def models(self) -> tuple[MLModel, ...]:
        return tuple(self._models.values())

    def count(self) -> int:
        return len(self._models)

    def __iter__(self) -> Iterator[MLModel]:
        return iter(self._models.values())
