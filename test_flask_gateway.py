import ast
from concurrent.futures import ThreadPoolExecutor

import pytest

from flask_gateway import FlaskGateway, create_app
from flask_gateway_event_adapter import (
    RawEventPayloadAdapter,
)
from flask_gateway_validation import GatewayPayloadValidator


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


def test_validator_accepts_json_object_without_undocumented_fields():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        {
            "event_type": "MODIFIED",
            "file_path": "/example/file.txt",
        }
    )

    assert result.valid is True
    assert result.error is None
    assert result.missing_fields == ()


def test_validator_rejects_non_mapping_payload():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        ["not", "an", "object"]
    )

    assert result.valid is False
    assert result.error == (
        "Payload must be a JSON object."
    )


def test_validator_reports_configured_missing_fields():
    validator = GatewayPayloadValidator(
        required_fields=(
            "event_type",
            "file_path",
        )
    )

    result = validator.validate(
        {
            "event_type": "MODIFIED",
        }
    )

    assert result.valid is False
    assert result.error == (
        "Missing required fields."
    )
    assert result.missing_fields == (
        "file_path",
    )


def test_gateway_reports_missing_configured_fields():
    processor = FakeProcessor()

    validator = GatewayPayloadValidator(
        required_fields=(
            "event_type",
            "file_path",
        )
    )

    app = create_app(
        event_processor=processor,
        validator=validator,
    )

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json={
            "event_type": "MODIFIED",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing required fields.",
        "missing_fields": [
            "file_path",
        ],
    }

    assert processor.calls == []


def test_gateway_accepts_payload_when_configured_fields_are_present():
    processor = FakeProcessor()

    validator = GatewayPayloadValidator(
        required_fields=(
            "event_type",
            "file_path",
        )
    )

    app = create_app(
        event_processor=processor,
        validator=validator,
    )

    client = app.test_client()

    payload = {
        "event_type": "MODIFIED",
        "file_path": "/example/file.txt",
    }

    response = client.post(
        "/analyze-event",
        json=payload,
    )

    assert response.status_code == 200
    assert processor.calls == [payload]


def test_gateway_supports_configurable_large_request_limit():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
        max_content_length=64,
    )

    client = app.test_client()

    response = client.post(
        "/analyze-event",
        json={
            "payload": "x" * 256,
        },
    )

    assert response.status_code == 413
    assert response.get_json() == {
        "error": "Request payload is too large.",
    }

    assert processor.calls == []


def test_gateway_does_not_require_a_payload_limit_by_default():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    assert app.config["MAX_CONTENT_LENGTH"] is None


def test_gateway_rejects_invalid_validator():
    processor = FakeProcessor()

    with pytest.raises(TypeError):
        FlaskGateway(
            event_processor=processor,
            validator=object(),
        )


def test_gateway_processes_concurrent_requests_independently():
    processor = FakeProcessor()
    app = create_app(
        event_processor=processor,
    )

    payloads = [
        {
            "request_id": f"request-{index}",
            "event_type": "MODIFIED",
            "file_path": f"/example/file-{index}.txt",
        }
        for index in range(20)
    ]

    def send_request(payload):
        with app.test_client() as client:
            response = client.post(
                "/analyze-event",
                json=payload,
            )

            return (
                response.status_code,
                response.get_json(),
            )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(
                send_request,
                payloads,
            )
        )

    assert len(results) == len(payloads)

    for status_code, response_payload in results:
        assert status_code == 200
        assert response_payload["received"] is True

    received_payloads = [
        payload
        for payload in processor.calls
    ]

    assert len(received_payloads) == len(payloads)
    assert {
        payload["request_id"]
        for payload in received_payloads
    } == {
        payload["request_id"]
        for payload in payloads
    }


def test_gateway_does_not_reuse_previous_request_payload():
    processor = FakeProcessor()
    app = create_app(
        event_processor=processor,
    )

    with app.test_client() as client:
        first_payload = {
            "request_id": "first",
            "value": "alpha",
        }
        second_payload = {
            "request_id": "second",
            "value": "beta",
        }

        first_response = client.post(
            "/analyze-event",
            json=first_payload,
        )
        second_response = client.post(
            "/analyze-event",
            json=second_payload,
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert processor.calls == [
        first_payload,
        second_payload,
    ]
def test_analyze_event_rejects_get_requests():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    client = app.test_client()

    response = client.get(
        "/analyze-event"
    )

    assert response.status_code == 405

    assert response.get_json() == {
        "error": "HTTP method not allowed.",
    }

    assert processor.calls == []


def test_health_rejects_post_requests():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    client = app.test_client()

    response = client.post(
        "/health",
        json={
            "unexpected": True,
        },
    )

    assert response.status_code == 405

    assert response.get_json() == {
        "error": "HTTP method not allowed.",
    }

    assert processor.calls == []


def test_status_rejects_post_requests():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    client = app.test_client()

    response = client.post(
        "/status",
        json={
            "unexpected": True,
        },
    )

    assert response.status_code == 405

    assert response.get_json() == {
        "error": "HTTP method not allowed.",
    }

    assert processor.calls == []


def test_unknown_endpoint_returns_json_error():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    client = app.test_client()

    response = client.post(
        "/does-not-exist",
        json={
            "event_type": "MODIFIED",
        },
    )

    assert response.status_code == 404

    assert response.get_json() == {
        "error": "Endpoint not found.",
    }

    assert processor.calls == []


def test_gateway_registers_expected_endpoints():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    routes = {
        (
            rule.rule,
            method,
        )
        for rule in app.url_map.iter_rules()
        for method in rule.methods
        if method not in {
            "HEAD",
            "OPTIONS",
        }
    }

    assert (
        "/health",
        "GET",
    ) in routes

    assert (
        "/status",
        "GET",
    ) in routes

    assert (
        "/analyze-event",
        "POST",
    ) in routes


def test_health_does_not_invoke_processor():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert processor.calls == []


def test_status_does_not_invoke_processor():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    with app.test_client() as client:
        response = client.get("/status")

    assert response.status_code == 200
    assert processor.calls == []


def test_validator_sanitize_returns_independent_copy():
    validator = GatewayPayloadValidator()

    original = {
        "event_type": "MODIFIED",
        "metadata": {
            "value": 10,
        },
        "items": [
            {
                "name": "file.txt",
            }
        ],
    }

    sanitized = validator.sanitize(original)

    assert sanitized == original
    assert sanitized is not original
    assert sanitized["metadata"] is not original["metadata"]
    assert sanitized["items"] is not original["items"]
    assert sanitized["items"][0] is not original["items"][0]


def test_validator_rejects_nan():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        {
            "value": float("nan"),
        }
    )

    assert result.valid is False
    assert result.error == (
        "Payload contains a non-finite numeric value."
    )


def test_validator_rejects_positive_infinity():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        {
            "value": float("inf"),
        }
    )

    assert result.valid is False


def test_validator_rejects_negative_infinity():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        {
            "value": float("-inf"),
        }
    )

    assert result.valid is False


def test_validator_rejects_unsupported_value_type():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        {
            "value": object(),
        }
    )

    assert result.valid is False
    assert result.error == (
        "Payload contains an unsupported value type."
    )


def test_validator_rejects_non_string_object_keys():
    validator = GatewayPayloadValidator()

    result = validator.validate(
        {
            123: "invalid",
        }
    )

    assert result.valid is False
    assert result.error == (
        "JSON object keys must be strings."
    )


def test_gateway_passes_sanitized_payload_to_processor():
    received = []

    def processor(payload):
        received.append(payload)

        return {
            "received": True,
        }

    app = create_app(processor)

    payload = {
        "event_type": "MODIFIED",
        "metadata": {
            "value": 42,
        },
    }

    with app.test_client() as client:
        response = client.post(
            "/analyze-event",
            json=payload,
        )

    assert response.status_code == 200
    assert received == [payload]

    assert received[0] is not payload
    assert received[0]["metadata"] is not payload["metadata"]


def test_routing_errors_never_invoke_processor():
    processor = FakeProcessor()

    app = create_app(
        event_processor=processor,
    )

    with app.test_client() as client:
        not_found = client.post(
            "/unknown-endpoint",
            json={
                "event_type": "MODIFIED",
            },
        )

        method_error = client.get(
            "/analyze-event"
        )

    assert not_found.status_code == 404
    assert method_error.status_code == 405

    assert processor.calls == []


def test_gateway_accepts_existing_raw_event_payload():
    received = []

    def processor(payload):
        received.append(payload)

        event = RawEventPayloadAdapter.from_payload(
            payload
        )

        return {
            "event_type": event.event_type,
            "file_name": event.file_name,
        }

    app = create_app(
        event_processor=processor,
        validator=GatewayPayloadValidator(
            required_fields=(
                "timestamp",
                "event_type",
                "source_path",
                "destination_path",
                "file_name",
                "extension",
                "directory",
                "is_directory",
                "file_size",
            )
        ),
    )

    event = RawEventPayloadAdapter.to_payload(
        RawEventPayloadAdapter.from_payload(
            {
                "timestamp": "2026-10-03T10:15:00+05:30",
                "event_type": "MODIFIED",
                "source_path": "C:/workspace/report.txt",
                "destination_path": None,
                "file_name": "report.txt",
                "extension": ".txt",
                "directory": "C:/workspace",
                "is_directory": False,
                "file_size": 128,
            }
        )
    )

    with app.test_client() as client:
        response = client.post(
            "/analyze-event",
            json=event,
        )

    assert response.status_code == 200

    assert response.get_json() == {
        "event_type": "MODIFIED",
        "file_name": "report.txt",
    }

    assert received == [event]


def test_processor_failure_is_logged(caplog):
    def failing_processor(payload):
        raise RuntimeError(
            "internal failure"
        )

    app = create_app(
        event_processor=failing_processor,
    )

    client = app.test_client()

    with caplog.at_level("ERROR"):
        response = client.post(
            "/analyze-event",
            json={
                "event_type": "MODIFIED",
            },
        )

    assert response.status_code == 500

    assert any(
        "Behavioral pipeline processing failed."
        in record.message
        for record in caplog.records
    )


def test_processor_timeout_is_logged(caplog):
    def timeout_processor(payload):
        raise TimeoutError(
            "internal timeout"
        )

    app = create_app(
        event_processor=timeout_processor,
    )

    client = app.test_client()

    with caplog.at_level("ERROR"):
        response = client.post(
            "/analyze-event",
            json={
                "event_type": "MODIFIED",
            },
        )

    assert response.status_code == 504

    assert any(
        "Behavioral pipeline request timed out."
        in record.message
        for record in caplog.records
    )


def test_authorizer_failure_is_logged_and_denies_request(caplog):
    processor = FakeProcessor()

    def failing_authorizer(_request):
        raise RuntimeError(
            "internal authorization failure"
        )

    app = create_app(
        event_processor=processor,
        authorizer=failing_authorizer,
    )

    client = app.test_client()

    with caplog.at_level("ERROR"):
        response = client.post(
            "/analyze-event",
            json={
                "event_type": "MODIFIED",
            },
        )

    assert response.status_code == 403

    assert response.get_json() == {
        "error": "Request not authorized.",
    }

    assert processor.calls == []

    assert any(
        "Authorization handler failed."
        in record.message
        for record in caplog.records
    )