from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RECOVERY_FILES = (
    "recovery_models.py",
    "recovery_manager.py",
    "recovery_verification.py",
    "backup_manager_port.py",
    "recovery_filesystem_port.py",
    "recovery_action_adapters.py",
    "decision_recovery_adapter.py",
)


def read_tree(filename: str) -> ast.Module:
    path = ROOT / filename
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def read_source_lower(filename: str) -> str:
    path = ROOT / filename
    return path.read_text(encoding="utf-8").lower()


def imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def called_attribute_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def function_names(tree: ast.Module) -> set[str]:
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


FORBIDDEN_PERSISTENCE_IMPORTS = {
    "pymongo",
    "motor",
    "sqlalchemy",
    "sqlite3",
    "mongodb",
    "database",
    "persistence",
}

FORBIDDEN_ML_IMPORTS = {
    "sklearn",
    "numpy",
    "torch",
    "machine_learning_engine",
    "ml_inference_engine",
    "ml_model_registry",
    "ml_model_adapters",
    "score_fusion",
    "score_calibration",
}

FORBIDDEN_FILESYSTEM_IMPORTS = {
    "shutil",
}

FORBIDDEN_FILESYSTEM_ATTRIBUTES = {
    "remove",
    "rename",
    "replace",
    "unlink",
    "rmtree",
    "move",
    "copy",
    "copy2",
    "copytree",
}

FORBIDDEN_DECISION_OPERATIONS = {
    "make_decision",
    "classify_risk",
    "determine_action",
    "evaluate_threshold",
    "calculate_risk",
}


def test_all_recovery_source_files_exist():
    missing = [
        filename
        for filename in RECOVERY_FILES
        if not (ROOT / filename).exists()
    ]
    assert not missing, f"Missing recovery files: {missing}"


def test_recovery_layer_has_no_persistence_imports():
    violations = []
    for filename in RECOVERY_FILES:
        imported = {
            module.lower()
            for module in imported_modules(read_tree(filename))
        }
        forbidden = imported & FORBIDDEN_PERSISTENCE_IMPORTS
        if forbidden:
            violations.append((filename, sorted(forbidden)))
    assert not violations, violations


def test_recovery_layer_has_no_ml_imports():
    violations = []
    for filename in RECOVERY_FILES:
        imported = {
            module.lower()
            for module in imported_modules(read_tree(filename))
        }
        forbidden = imported & FORBIDDEN_ML_IMPORTS
        if forbidden:
            violations.append((filename, sorted(forbidden)))
    assert not violations, violations


def test_recovery_layer_has_no_filesystem_module_imports():
    violations = []
    for filename in RECOVERY_FILES:
        imported = {
            module.lower()
            for module in imported_modules(read_tree(filename))
        }
        forbidden = imported & FORBIDDEN_FILESYSTEM_IMPORTS
        if forbidden:
            violations.append((filename, sorted(forbidden)))
    assert not violations, violations


def test_recovery_manager_does_not_import_engine_implementations():
    tree = read_tree("recovery_manager.py")
    imported = {
        module.lower()
        for module in imported_modules(tree)
    }
    assert "decision_engine" not in imported
    assert "backup_manager" not in imported
    assert "machine_learning_engine" not in imported
    assert "candidate_pattern_manager" not in imported


def test_decision_adapter_does_not_import_engines_or_storage():
    tree = read_tree("decision_recovery_adapter.py")
    imported = {
        module.lower()
        for module in imported_modules(tree)
    }
    allowed = {
        "decision_models",
        "recovery_models",
        "typing",
    }
    unexpected = imported - allowed
    assert not unexpected, unexpected


def test_ports_are_interfaces_without_filesystem_calls():
    for filename in (
        "backup_manager_port.py",
        "recovery_filesystem_port.py",
    ):
        attributes = called_attribute_names(read_tree(filename))
        violations = attributes & FORBIDDEN_FILESYSTEM_ATTRIBUTES
        assert not violations, (filename, violations)


def test_recovery_manager_implements_no_filesystem_mutation():
    tree = read_tree("recovery_manager.py")
    imported = {
        module.lower()
        for module in imported_modules(tree)
    }
    assert "shutil" not in imported
    assert "os" not in imported
    violations = (
        called_attribute_names(tree) & FORBIDDEN_FILESYSTEM_ATTRIBUTES
    )
    assert not violations, violations
    source = read_source_lower("recovery_manager.py")
    for token in (
        "shutil",
        "os.remove",
        "os.rename",
        "os.replace",
        "path.unlink",
        "path.rename",
        "pymongo",
        "mongodb",
    ):
        assert token not in source, token


def test_action_adapters_implement_no_filesystem_mutation():
    tree = read_tree("recovery_action_adapters.py")
    imported = {
        module.lower()
        for module in imported_modules(tree)
    }
    assert "shutil" not in imported
    assert "os" not in imported
    source = read_source_lower("recovery_action_adapters.py")
    for token in (
        "shutil",
        "os.remove",
        "os.rename",
        "os.replace",
        "path.unlink",
        "path.rename",
        "pymongo",
        "mongodb",
    ):
        assert token not in source, token


def test_action_adapters_import_only_ports_and_contracts():
    imported = {
        module.lower()
        for module in imported_modules(
            read_tree("recovery_action_adapters.py")
        )
    }
    allowed = {
        "typing",
        "backup_manager_port",
        "recovery_filesystem_port",
        "recovery_models",
    }
    assert not (imported - allowed), (imported - allowed)


def test_recovery_manager_does_not_define_decision_operations():
    violations = (
        function_names(read_tree("recovery_manager.py"))
        & FORBIDDEN_DECISION_OPERATIONS
    )
    assert not violations, violations


def test_recovery_manager_is_not_a_second_decision_engine():
    source = read_source_lower("recovery_manager.py")
    for token in (
        "anomaly_score",
        "classify_risk",
        "make_decision",
        "determine_action",
        "evaluated_from_score",
    ):
        assert token not in source, token
