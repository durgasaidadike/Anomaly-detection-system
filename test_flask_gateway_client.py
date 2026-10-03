import pytest
import requests

from flask_gateway_client import (
    FlaskGatewayClient,
    GatewayTransportError,
)
from flask_gateway_event_adapter import (
    RawEventPayloadAdapter,
)
from watcher import (
    EventDispatcher,
    RawEvent,
)


class FakeResponse:
    def __init__(
        self,
        status_code,
        payload=None,
    ):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(
            self._payload,
            Exception,
        ):
            raise self._payload

        return self._payload


class FakeHttpClient:
    def __init__(
        self,
        response=None,
        exception=None,
    ):
        self.response = response
        self.exception = exception
        self.calls = []
        self.closed = False

    def post(
        self,
        url,
        **kwargs,
    ):
        self.calls.append(
            {
                "url": url,
                "kwargs": kwargs,
            }
        )

        if self.exception is not None:
            raise self.exception

        return self.response

    def close(self):
        self.closed = True


def make_event():
    return RawEvent(
        timestamp="2026-10-03T12:00:00+05:30",
        event_type="MODIFIED",
        source_path="C:/workspace/report.txt",
        destination_path=None,
        file_name="report.txt",
        extension=".txt",
        directory="C:/workspace",
        is_directory=False,
        file_size=128,
    )


def test_client_requires_valid_base_url():
    with pytest.raises(TypeError):
        FlaskGatewayClient(
            base_url=None,
        )

    with pytest.raises(ValueError):
        FlaskGatewayClient(
            base_url="ftp://example.com",
        )

    with pytest.raises(ValueError):
        FlaskGatewayClient(
            base_url="http://",
        )


def test_client_rejects_invalid_timeout():
    with pytest.raises(TypeError):
        FlaskGatewayClient(
            base_url="http://localhost:5000",
            timeout="10",
        )

    with pytest.raises(ValueError):
        FlaskGatewayClient(
            base_url="http://localhost:5000",
            timeout=0,
        )


def test_client_sends_raw_event_as_json():
    fake = FakeHttpClient(
        response=FakeResponse(
            200,
            {
                "status": "accepted",
            },
        )
    )

    client = FlaskGatewayClient(
        base_url="http://localhost:5000/",
        http_client=fake,
        timeout=5,
    )

    result = client.send_event(
        make_event()
    )

    assert result == {
        "status": "accepted",
    }

    assert len(fake.calls) == 1

    call = fake.calls[0]

    assert call["url"] == (
        "http://localhost:5000/analyze-event"
    )

    assert call["kwargs"]["timeout"] == 5

    assert call["kwargs"]["json"] == {
        "timestamp": "2026-10-03T12:00:00+05:30",
        "event_type": "MODIFIED",
        "source_path": "C:/workspace/report.txt",
        "destination_path": None,
        "file_name": "report.txt",
        "extension": ".txt",
        "directory": "C:/workspace",
        "is_directory": False,
        "file_size": 128,
    }


def test_client_returns_successful_json_response():
    fake = FakeHttpClient(
        response=FakeResponse(
            200,
            {
                "processing_status": "SUCCESS",
            },
        )
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    assert client.send_event(
        make_event()
    ) == {
        "processing_status": "SUCCESS",
    }


def test_client_handles_gateway_http_failure():
    fake = FakeHttpClient(
        response=FakeResponse(
            500,
            {
                "error": "Request processing failed.",
            },
        )
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    with pytest.raises(
        GatewayTransportError,
        match="unsuccessful HTTP response",
    ) as exc_info:
        client.send_event(
            make_event()
        )

    assert exc_info.value.status_code == 500

    assert exc_info.value.response_payload == {
        "error": "Request processing failed.",
    }


def test_client_handles_timeout():
    fake = FakeHttpClient(
        exception=requests.exceptions.Timeout()
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
        timeout=2,
    )

    with pytest.raises(
        GatewayTransportError,
        match="Gateway request timed out",
    ):
        client.send_event(
            make_event()
        )


def test_client_handles_connection_failure():
    fake = FakeHttpClient(
        exception=requests.exceptions.ConnectionError()
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    with pytest.raises(
        GatewayTransportError,
        match="Gateway request failed",
    ):
        client.send_event(
            make_event()
        )


def test_client_rejects_invalid_gateway_json():
    fake = FakeHttpClient(
        response=FakeResponse(
            200,
            ValueError("invalid json"),
        )
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    with pytest.raises(
        GatewayTransportError,
        match="invalid JSON response",
    ):
        client.send_event(
            make_event()
        )


def test_client_accepts_injected_http_client():
    fake = FakeHttpClient(
        response=FakeResponse(
            200,
            {},
        )
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    assert client.endpoint == (
        "http://localhost:5000/analyze-event"
    )


def test_client_closes_owned_http_client():
    fake = FakeHttpClient(
        response=FakeResponse(
            200,
            {},
        )
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    client.close()

    assert fake.closed is False


def test_watchdog_dispatcher_can_use_gateway_client():
    fake = FakeHttpClient(
        response=FakeResponse(
            200,
            {
                "status": "accepted",
            },
        )
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    dispatcher = EventDispatcher(
        client.send_event
    )

    dispatcher.dispatch(
        make_event()
    )

    assert len(fake.calls) == 1
    assert fake.calls[0]["url"].endswith(
        "/analyze-event"
    )


def test_failed_gateway_transport_does_not_mutate_raw_event():
    fake = FakeHttpClient(
        exception=requests.exceptions.ConnectionError()
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    event = make_event()

    original_payload = (
        RawEventPayloadAdapter.to_payload(
            event
        )
    )

    with pytest.raises(
        GatewayTransportError,
    ):
        client.send_event(event)

    assert (
        RawEventPayloadAdapter.to_payload(event)
        == original_payload
    )


def test_watchdog_dispatch_preserves_failure_boundary():
    fake = FakeHttpClient(
        exception=requests.exceptions.ConnectionError()
    )

    client = FlaskGatewayClient(
        "http://localhost:5000",
        http_client=fake,
    )

    dispatcher = EventDispatcher(
        client.send_event
    )

    event = make_event()

    with pytest.raises(
        GatewayTransportError
    ):
        dispatcher.dispatch(event)

    assert (
        RawEventPayloadAdapter.to_payload(event)
        == {
            "timestamp": "2026-10-03T12:00:00+05:30",
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