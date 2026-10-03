from __future__ import annotations

from typing import Any, Mapping

from watcher import RawEvent


class RawEventPayloadAdapter:
    """
    Converts the existing PRISM RawEvent contract between its
    Python representation and the JSON representation used by
    the Flask Gateway.

    This adapter performs transport conversion only.

    It does not:
    - analyze behavior
    - calculate features
    - perform ML
    - make decisions
    - persist history
    - execute recovery
    """

    REQUIRED_FIELDS = (
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

    @classmethod
    def to_payload(
        cls,
        event: RawEvent,
    ) -> dict[str, Any]:
        if not isinstance(event, RawEvent):
            raise TypeError(
                "event must be a RawEvent."
            )

        return event.to_dict()

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> RawEvent:
        if not isinstance(payload, Mapping):
            raise TypeError(
                "RawEvent payload must be a mapping."
            )

        missing = tuple(
            field
            for field in cls.REQUIRED_FIELDS
            if field not in payload
        )

        if missing:
            raise ValueError(
                "Missing required RawEvent fields: "
                + ", ".join(missing)
            )

        timestamp = payload["timestamp"]

        if not isinstance(timestamp, str):
            raise TypeError(
                "RawEvent timestamp must be a string."
            )

        event_type = payload["event_type"]

        if not isinstance(event_type, str):
            raise TypeError(
                "RawEvent event_type must be a string."
            )

        source_path = payload["source_path"]

        if not isinstance(source_path, str):
            raise TypeError(
                "RawEvent source_path must be a string."
            )

        destination_path = payload["destination_path"]

        if (
            destination_path is not None
            and not isinstance(destination_path, str)
        ):
            raise TypeError(
                "RawEvent destination_path must be a string or None."
            )

        file_name = payload["file_name"]

        if not isinstance(file_name, str):
            raise TypeError(
                "RawEvent file_name must be a string."
            )

        extension = payload["extension"]

        if not isinstance(extension, str):
            raise TypeError(
                "RawEvent extension must be a string."
            )

        directory = payload["directory"]

        if not isinstance(directory, str):
            raise TypeError(
                "RawEvent directory must be a string."
            )

        is_directory = payload["is_directory"]

        if not isinstance(is_directory, bool):
            raise TypeError(
                "RawEvent is_directory must be a boolean."
            )

        file_size = payload["file_size"]

        if (
            not isinstance(file_size, int)
            or isinstance(file_size, bool)
        ):
            raise TypeError(
                "RawEvent file_size must be an integer."
            )

        if file_size < 0:
            raise ValueError(
                "RawEvent file_size cannot be negative."
            )

        return RawEvent(
            timestamp=timestamp,
            event_type=event_type,
            source_path=source_path,
            destination_path=destination_path,
            file_name=file_name,
            extension=extension,
            directory=directory,
            is_directory=is_directory,
            file_size=file_size,
        )