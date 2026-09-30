from __future__ import annotations

import ast
from pathlib import Path


ML_ENGINE_FILES = (
    "ml_model_contracts.py",
    "ml_result_models.py",
    "prediction_validator.py",
    "ml_model_adapters.py",
    "ml_model_registry.py",
    "ml_inference_results.py",
    "ml_inference_engine.py",
    "score_semantics.py",
    "score_calibration.py",
    "score_fusion.py",
    "ensemble_result_models.py",
    "machine_learning_engine.py",
)

FORBIDDEN_IMPORT_TOKENS = {
    "pymongo",
    "motor",
    "sqlalchemy",
    "sqlite3",
    "flask",
    "decision_engine",
    "recovery_manager",
    "candidate_pattern_manager",
    "pattern_repository",
    "repository",
    "database",
    "persistence",
}

FORBIDDEN_OPERATION_NAMES = {
    "train",
    "fit",
    "retrain",
    "learn",
    "update_model",
}


def module_paths():
    root = Path(__file__).parent

    return tuple(
        root / filename
        for filename in ML_ENGINE_FILES
    )


def parse_file(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(
            encoding="utf-8"
        )
    )


def imported_module_names(tree: ast.Module):
    names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(
                    alias.name.lower()
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(
                    node.module.lower()
                )

    return names


def function_names(tree: ast.Module):
    return {
        node.name.lower()
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


def test_all_ml_engine_source_files_exist():
    missing = [
        str(path)
        for path in module_paths()
        if not path.exists()
    ]

    assert not missing, (
        "Missing Module 11 source files: "
        + ", ".join(missing)
    )


def test_ml_engine_has_no_forbidden_imports():
    violations = []

    for path in module_paths():
        tree = parse_file(path)

        imported = imported_module_names(tree)

        for module in imported:
            for forbidden in FORBIDDEN_IMPORT_TOKENS:
                if forbidden in module:
                    violations.append(
                        (
                            path.name,
                            module,
                        )
                    )

    assert not violations, violations
def test_ml_engine_has_no_training_operations():
    violations = []

    for path in module_paths():
        tree = parse_file(path)

        functions = function_names(tree)

        forbidden = (
            functions
            & FORBIDDEN_OPERATION_NAMES
        )

        if forbidden:
            violations.append(
                (
                    path.name,
                    sorted(forbidden),
                )
            )

    assert not violations, violations


def test_ml_engine_does_not_define_recovery_operations():
    recovery_tokens = {
        "recover",
        "restore",
        "backup",
    }

    violations = []

    for path in module_paths():
        tree = parse_file(path)

        functions = function_names(tree)

        for function in functions:
            if any(
                token in function
                for token in recovery_tokens
            ):
                violations.append(
                    (
                        path.name,
                        function,
                    )
                )

    assert not violations, violations


def test_ml_engine_does_not_define_risk_decision_operations():
    decision_tokens = {
        "classify_risk",
        "calculate_risk",
        "risk_level",
        "recommended_action",
        "make_decision",
    }

    violations = []

    for path in module_paths():
        tree = parse_file(path)

        functions = function_names(tree)

        for function in functions:
            if any(
                token in function
                for token in decision_tokens
            ):
                violations.append(
                    (
                        path.name,
                        function,
                    )
                )

    assert not violations, violations


def test_ml_engine_does_not_reference_behavioral_history():
    history_tokens = {
        "history",
        "behavioral_history",
        "behavior_history",
        "candidate_patterns",
        "behavior_profiles",
    }

    violations = []

    for path in module_paths():
        tree = parse_file(path)

        for node in ast.walk(tree):
            if isinstance(
                node,
                ast.Name,
            ):
                if node.id.lower() in history_tokens:
                    violations.append(
                        (
                            path.name,
                            node.id,
                        )
                    )

            elif isinstance(
                node,
                ast.Attribute,
            ):
                if node.attr.lower() in history_tokens:
                    violations.append(
                        (
                            path.name,
                            node.attr,
                        )
                    )

    assert not violations, violations

