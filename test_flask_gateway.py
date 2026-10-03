import ast

import pytest

from flask_gateway import FlaskGateway, create_app


class FakeProcessor:
    def __init__(self):
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)

        return {
            "received": True,
            "payload": payload,
        }


def test_gateway_requires_callable_processor():
    with pytest.raises(TypeError):
        FlaskGateway(event_processor=None)


def test_health_endpoint():
    processor = FakeProcessor()
    app = create_app(processor)

    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
    }


def test_status_endpoint():
    processor = FakeProcessor()
    app = create_app(processor)

    client = app.test_client()

    response = client.get("/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ready",
    }


def test_analyze_event_requires_json():
    processor = FakeProcessor()
    app = create_app(processor)

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        data="not-json",
        content_type="text/plain",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "Request must contain a JSON object."
    )

    assert processor.calls == []


def test_analyze_event_requires_json_object():
    processor = FakeProcessor()
    app = create_app(processor)

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json=["not", "an", "object"],
    )

    assert response.status_code == 400
    assert processor.calls == []


def test_analyze_event_forwards_payload_without_business_processing():
    processor = FakeProcessor()
    app = create_app(processor)

    client = app.test_client()

    payload = {
        "event_type": "MODIFIED",
        "file_path": "/example/file.txt",
        "arbitrary_data": {
            "value": 123,
        },
    }

    response = client.post(
        "/analyze-event",
        json=payload,
    )

    assert response.status_code == 200

    assert processor.calls == [
        payload,
    ]

    assert response.get_json() == {
        "received": True,
        "payload": payload,
    }


def test_processor_failure_returns_http_500():
    def failing_processor(payload):
        raise RuntimeError("pipeline failure")

    app = create_app(failing_processor)

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json={
            "event_type": "MODIFIED",
        },
    )

    assert response.status_code == 500
    assert response.get_json()["error"] == (
        "Request processing failed."
    )


def test_processor_timeout_returns_http_504():
    def timeout_processor(payload):
        raise TimeoutError("pipeline timeout")

    app = create_app(timeout_processor)

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json={
            "event_type": "MODIFIED",
        },
    )

    assert response.status_code == 504
    assert response.get_json()["error"] == (
        "Request processing timed out."
    )


def test_authorizer_can_reject_request():
    processor = FakeProcessor()

    def deny(_request):
        return False

    app = create_app(
        event_processor=processor,
        authorizer=deny,
    )

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json={
            "event_type": "MODIFIED",
        },
    )

    assert response.status_code == 403
    assert processor.calls == []


def test_authorizer_allows_request():
    processor = FakeProcessor()

    def allow(_request):
        return True

    app = create_app(
        event_processor=processor,
        authorizer=allow,
    )

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json={
            "event_type": "MODIFIED",
        },
    )

    assert response.status_code == 200
    assert len(processor.calls) == 1


def test_gateway_module_has_no_forbidden_business_dependencies():
    with open(
        "flask_gateway.py",
        "r",
        encoding="utf-8",
    ) as file:
        source = file.read()

    tree = ast.parse(source)

    forbidden_modules = {
        "numpy",
        "sklearn",
        "database",
        "model",
        "decision",
        "recovery_manager",
        "candidate_pattern_manager",
        "behavior_analyzer",
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

    assert imported_modules.isdisjoint(
        forbidden_modules
    )