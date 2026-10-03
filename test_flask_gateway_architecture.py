import ast
from pathlib import Path

from flask_gateway import create_app

ROOT = Path(__file__).resolve().parent

# The Gateway is a communication layer only. It may depend on
# the standard library and Flask, and nothing else.
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "logging",
    "collections",
    "typing",
    "flask",
    "flask_gateway_validation",
}

# Business / intelligence / persistence dependencies the Gateway
# must never absorb. Flask must never perform ML, build Candidate
# Patterns, store behavioral history, or execute recovery.
FORBIDDEN_IMPORT_ROOTS = {
    "numpy",
    "scipy",
    "pandas",
    "sklearn",
    "torch",
    "tensorflow",
    "pymongo",
    "motor",
    "sqlalchemy",
    "sqlite3",
    "database",
    "model",
    "utils",
    "decision",
    "decision_engine",
    "machine_learning_engine",
    "ml_inference_engine",
    "behavior_analyzer",
    "behavioral_knowledge",
    "behavioral_identity",
    "candidate_pattern_manager",
    "final_pattern_repository",
    "similarity_engine",
    "drift_engine",
    "confidence_engine",
    "feature_extractor",
    "recovery_manager",
}

# Source-level business operations that must never appear in the
# Gateway: the legacy app.py pipeline calls these directly.
FORBIDDEN_SOURCE_TOKENS = (
    "train_models",
    "get_scores",
    "normalize_score",
    "calculate_weighted_score",
    "get_risk_label",
    "get_action",
    "save_event",
    "candidate_pattern",
    "behavioral_history",
    "anomaly_score",
    "restore_backup",
)

# Statelessness guard: the specification defines the Gateway as
# stateless, processing each request independently.
FORBIDDEN_STATE_TOKENS = (
    "session[",
    "active_sessions",
    "behavior_history",
    "event_history",
    "request_history",
)


def parse_module():
    path = ROOT / "flask_gateway.py"
    return ast.parse(
        path.read_text(
            encoding="utf-8"
        ),
        filename=str(path),
    )


def imported_modules():
    tree = parse_module()
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(
                    alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(
                    node.module.split(".")[0]
                )
    return modules


def read_source() -> str:
    return (
        ROOT / "flask_gateway.py"
    ).read_text(
        encoding="utf-8"
    )


def test_gateway_imports_no_business_or_ml_modules():
    imported = imported_modules()

    forbidden = imported & FORBIDDEN_IMPORT_ROOTS

    assert forbidden == set()


def test_gateway_imports_only_communication_dependencies():
    imported = imported_modules()

    unexpected = imported - ALLOWED_IMPORT_ROOTS

    assert unexpected == set()


def test_gateway_source_contains_no_business_operations():
    content = read_source()

    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in content


def test_gateway_does_not_store_request_state():
    source = (
        ROOT / "flask_gateway.py"
    )
    content = source.read_text(
        encoding="utf-8"
    )

    forbidden = {
        "session[",
        "active_sessions",
        "behavior_history",
        "event_history",
        "request_history",
    }

    for token in forbidden:
        assert token not in content


def test_gateway_has_no_persistent_state_tokens():
    content = read_source()

    for token in FORBIDDEN_STATE_TOKENS:
        assert token not in content


def test_required_endpoints_are_registered():
    app = create_app(
        lambda payload: payload
    )
    routes = {
        rule.rule
        for rule in app.url_map.iter_rules()
    }

    assert "/analyze-event" in routes
    assert "/health" in routes
    assert "/status" in routes


def test_endpoint_methods_match_specification():
    app = create_app(
        lambda payload: payload
    )
    rules = {
        rule.rule: rule.methods
        for rule in app.url_map.iter_rules()
    }

    assert rules["/analyze-event"] == {
        "OPTIONS",
        "POST",
    }
    assert rules["/health"] == {
        "OPTIONS",
        "HEAD",
        "GET",
    }
    assert rules["/status"] == {
        "OPTIONS",
        "HEAD",
        "GET",
    }