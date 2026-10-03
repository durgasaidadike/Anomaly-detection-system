import pytest

from flask_gateway_event_adapter import (
    RawEventPayloadAdapter,
)
from watcher import RawEvent


def make_raw_event():
    return RawEvent(
        timestamp="2026-10-03T10:15:00+05:30",
        event_type="MODIFIED",
        source_path="C:/workspace/report.txt",
        destination_path=None,
        file_name="report.txt",
        extension=".txt",
        directory="C:/workspace",
        is_directory=False,
        file_size=128,
    )


def test_raw_event_can_be_serialized_to_gateway_payload():
    event = make_raw_event()

    payload = RawEventPayloadAdapter.to_payload(
        event
    )

    assert payload == {
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


def test_gateway_payload_can_be_deserialized_to_raw_event():
    event = make_raw_event()

    payload = RawEventPayloadAdapter.to_payload(
        event
    )

    restored = RawEventPayloadAdapter.from_payload(
        payload
    )

    assert restored == event


def test_adapter_rejects_missing_required_field():
    event = make_raw_event()

    payload = RawEventPayloadAdapter.to_payload(
        event
    )

    del payload["file_size"]

    with pytest.raises(
        ValueError,
        match="Missing required RawEvent fields",
    ):
        RawEventPayloadAdapter.from_payload(
            payload
        )


def test_adapter_rejects_invalid_timestamp_type():
    payload = RawEventPayloadAdapter.to_payload(
        make_raw_event()
    )

    payload["timestamp"] = 123

    with pytest.raises(
        TypeError,
        match="timestamp must be a string",
    ):
        RawEventPayloadAdapter.from_payload(
            payload
        )


def test_adapter_rejects_invalid_event_type():
    payload = RawEventPayloadAdapter.to_payload(
        make_raw_event()
    )

    payload["event_type"] = 123

    with pytest.raises(
        TypeError,
        match="event_type must be a string",
    ):
        RawEventPayloadAdapter.from_payload(
            payload
        )


def test_adapter_rejects_invalid_directory_flag():
    payload = RawEventPayloadAdapter.to_payload(
        make_raw_event()
    )

    payload["is_directory"] = "false"

    with pytest.raises(
        TypeError,
        match="is_directory must be a boolean",
    ):
        RawEventPayloadAdapter.from_payload(
            payload
        )


def test_adapter_rejects_negative_file_size():
    payload = RawEventPayloadAdapter.to_payload(
        make_raw_event()
    )

    payload["file_size"] = -1

    with pytest.raises(
        ValueError,
        match="file_size cannot be negative",
    ):
        RawEventPayloadAdapter.from_payload(
            payload
        )


def test_adapter_rejects_non_raw_event():
    with pytest.raises(
        TypeError,
        match="event must be a RawEvent",
    ):
        RawEventPayloadAdapter.to_payload(
            {"event_type": "MODIFIED"}
        )