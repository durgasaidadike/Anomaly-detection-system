from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ensemble_result_models import EnsembleResult
from feature_vector_models import FeatureVector
from machine_learning_engine import MachineLearningEngine
from ml_inference_engine import MLInferenceEngine
from ml_model_registry import MLModelRegistry
from score_calibration import ScoreCalibrationEngine
from score_fusion import WeightedScoreFusion
from score_semantics import ScoreDirection


MODULE_PATH = Path(__file__).with_name(
    "machine_learning_engine.py"
)


def read_module_source() -> str:
    return MODULE_PATH.read_text(
        encoding="utf-8"
    )


def parse_module() -> ast.Module:
    return ast.parse(
        read_module_source()
    )


def make_engine() -> MachineLearningEngine:
    class Model:
        @property
        def model_name(self) -> str:
            return "test-model"

        @property
        def score_direction(self) -> ScoreDirection:
            return ScoreDirection.LOWER_IS_MORE_ANOMALOUS

        def predict(
            self,
            vector: FeatureVector,
        ) -> float:
            return -0.2

    registry = MLModelRegistry()
    registry.register(Model())

    inference_engine = MLInferenceEngine(
        registry=registry
    )

    calibration_engine = ScoreCalibrationEngine(
        {
            "test-model": lambda score: score,
        }
    )

    fusion_engine = WeightedScoreFusion(
        {
            "test-model": 1.0,
        }
    )

    return MachineLearningEngine(
        registry=registry,
        inference_engine=inference_engine,
        calibration_engine=calibration_engine,
        fusion_engine=fusion_engine,
    )


def make_vector() -> FeatureVector:
    return FeatureVector(
        pattern_id="architecture-pattern",
        knowledge_id="architecture-knowledge",
        features={
            "feature_a": 0.5,
        },
        feature_names=(
            "feature_a",
        ),
    )


def test_engine_accepts_only_feature_vectors():
    engine = make_engine()

    with pytest.raises(TypeError):
        engine.predict(
            {
                "raw_event": "file_deleted",
            }
        )


def test_engine_rejects_incomplete_feature_vectors():
    engine = make_engine()

    vector = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={},
        feature_names=(
            "feature_a",
        ),
    )

    with pytest.raises(ValueError):
        engine.predict(vector)


def test_engine_produces_ensemble_result():
    engine = make_engine()

    result = engine.predict(
        make_vector()
    )

    assert isinstance(
        result,
        EnsembleResult,
    )


def test_engine_exposes_only_ml_result_to_downstream_boundary():
    engine = make_engine()

    result = engine.predict(
        make_vector()
    )

    assert hasattr(
        result,
        "anomaly_score",
    )

    assert hasattr(
        result,
        "model_scores",
    )

    assert hasattr(
        result,
        "metadata",
    )

    assert not hasattr(
        result,
        "risk_level",
    )

    assert not hasattr(
        result,
        "recommended_action",
    )


def test_engine_does_not_retain_behavioral_history():
    engine = make_engine()

    forbidden_state_names = {
        "history",
        "behavior_history",
        "behavioral_history",
        "patterns",
        "candidate_patterns",
        "behavior_profiles",
    }

    assert not (
        forbidden_state_names
        & set(engine.__dict__.keys())
    )


def test_engine_state_contains_only_orchestration_dependencies():
    engine = make_engine()

    assert set(engine.__dict__.keys()) == {
        "_registry",
        "_inference_engine",
        "_calibration_engine",
        "_fusion_engine",
    }


def test_engine_has_no_training_interface():
    tree = parse_module()

    forbidden_methods = {
        "train",
        "fit",
        "retrain",
        "learn",
        "update_model",
        "save_model",
    }

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]

    method_names = {
        function.name
        for function in functions
    }

    assert not (
        forbidden_methods & method_names
    )


def test_engine_has_no_recovery_interface():
    tree = parse_module()

    forbidden_names = {
        "recover",
        "restore",
        "backup",
        "recovery",
    }

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]

    method_names = {
        function.name.lower()
        for function in functions
    }

    assert not any(
        any(
            forbidden in name
            for forbidden in forbidden_names
        )
        for name in method_names
    )


def test_engine_has_no_database_import():
    tree = parse_module()

    forbidden_modules = {
        "pymongo",
        "motor",
        "sqlalchemy",
        "sqlite3",
        "mongodb",
    }

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module.split(".")[0]
                )

    assert not (
        forbidden_modules
        & imported_modules
    )


def test_engine_has_no_flask_import():
    tree = parse_module()

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module.split(".")[0]
                )

    assert "flask" not in imported_modules

def test_engine_does_not_import_decision_engine():
    tree = parse_module()

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module
                )

    assert all(
        "decision_engine" not in module
        for module in imported_modules
    )


def test_engine_does_not_import_recovery_manager():
    tree = parse_module()

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module
                )

    assert all(
        "recovery_manager" not in module
        for module in imported_modules
    )


def test_engine_does_not_import_candidate_pattern_manager():
    tree = parse_module()

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module
                )

    assert all(
        "candidate_pattern_manager" not in module
        for module in imported_modules
    )


def test_engine_does_not_import_mongodb_or_persistence_layer():
    tree = parse_module()

    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(
                    alias.name.lower()
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(
                    node.module.lower()
                )

    forbidden_tokens = {
        "repository",
        "database",
        "persistence",
        "mongodb",
        "mongo",
    }

    assert not any(
        any(
            token in module
            for token in forbidden_tokens
        )
        for module in imported_modules
    )


def test_engine_does_not_mutate_feature_vector():
    engine = make_engine()

    vector = make_vector()

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


def test_engine_can_process_multiple_vectors_without_cross_request_state():
    engine = make_engine()

    first = FeatureVector(
        pattern_id="pattern-1",
        knowledge_id="knowledge-1",
        features={
            "feature_a": 0.1,
        },
        feature_names=(
            "feature_a",
        ),
    )

    second = FeatureVector(
        pattern_id="pattern-2",
        knowledge_id="knowledge-2",
        features={
            "feature_a": 0.9,
        },
        feature_names=(
            "feature_a",
        ),
    )

    first_result = engine.predict(first)
    second_result = engine.predict(second)

    assert first_result.pattern_id == (
        "pattern-1"
    )

    assert second_result.pattern_id == (
        "pattern-2"
    )

    assert first_result.knowledge_id == (
        "knowledge-1"
    )

    assert second_result.knowledge_id == (
        "knowledge-2"
    )
