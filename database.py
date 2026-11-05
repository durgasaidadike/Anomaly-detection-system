import copy
import os
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient

from persistence_port import PersistencePort

DEFAULT_MONGODB_URI = "mongodb://localhost:27017/"
DEFAULT_MONGODB_DATABASE = "anomaly_detection"
DEFAULT_MONGODB_SERVER_SELECTION_TIMEOUT_MS = 5000


def _resolve_string_setting(
    explicit_value: Optional[str],
    environment_variable: str,
    default_value: str,
) -> str:
    value = (
        explicit_value
        if explicit_value is not None
        else os.getenv(environment_variable, default_value)
    )
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{environment_variable} must be a non-empty string"
        )
    return value.strip()


def _resolve_timeout_setting(
    explicit_value: Optional[int],
) -> int:
    if explicit_value is not None:
        if isinstance(explicit_value, bool):
            raise ValueError(
                "PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"
            )
        if isinstance(explicit_value, int):
            timeout = explicit_value
        elif isinstance(explicit_value, str):
            try:
                timeout = int(explicit_value)
            except ValueError:
                raise ValueError(
                    "PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"
                )
        else:
            raise ValueError(
                "PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"
            )
    else:
        raw_value = os.getenv(
            "PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS"
        )
        if raw_value is None:
            timeout = DEFAULT_MONGODB_SERVER_SELECTION_TIMEOUT_MS
        else:
            try:
                timeout = int(raw_value)
            except ValueError:
                raise ValueError(
                    "PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"
                )

    if timeout <= 0:
        raise ValueError(
            "PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"
        )

    return timeout


class MongoDBPersistence(PersistencePort):
    """
    PRISM Module 17
    MongoDB Persistence Implementation

    Concrete implementation of PersistencePort using PyMongo.
    This is the only file allowed to import PyMongo directly.
    All other modules must depend on PersistencePort.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
        server_selection_timeout_ms: Optional[int] = None,
    ):
        self._connection_string = _resolve_string_setting(
            connection_string,
            "PRISM_MONGODB_URI",
            DEFAULT_MONGODB_URI,
        )
        self._database_name = _resolve_string_setting(
            database_name,
            "PRISM_MONGODB_DATABASE",
            DEFAULT_MONGODB_DATABASE,
        )
        self._server_selection_timeout_ms = (
            _resolve_timeout_setting(
                server_selection_timeout_ms
            )
        )
        self._client = MongoClient(
            self._connection_string,
            serverSelectionTimeoutMS=(
                self._server_selection_timeout_ms
            ),
        )
        self._db = self._client[self._database_name]
        self._events_collection = self._db["events"]
        self._baseline_inventory_collection = (
            self._db["baseline_inventory"]
        )
        self._directory_snapshots_collection = (
            self._db["directory_snapshots"]
        )
        self._directory_validations_collection = (
            self._db["directory_validations"]
        )
        self._watcher_registrations_collection = (
            self._db["watcher_registrations"]
        )

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def save_event(self, event_data: dict) -> str:
        document = copy.deepcopy(event_data)
        document["timestamp"] = self._utc_now()
        result = self._events_collection.insert_one(document)
        return str(result.inserted_id)

    def save_baseline_entry(self, entry_data: dict) -> str:
        document = copy.deepcopy(entry_data)
        document["persisted_at"] = self._utc_now()
        result = self._baseline_inventory_collection.insert_one(document)
        return str(result.inserted_id)

    def save_directory_snapshot(self, snapshot_data: dict) -> str:
        document = copy.deepcopy(snapshot_data)
        document["persisted_at"] = self._utc_now()
        result = self._directory_snapshots_collection.insert_one(document)
        return str(result.inserted_id)

    def save_validation_result(self, validation_data: dict) -> str:
        document = copy.deepcopy(validation_data)
        document["persisted_at"] = self._utc_now()
        result = self._directory_validations_collection.insert_one(document)
        return str(result.inserted_id)

    def save_watcher_registration(self, registration_data: dict) -> str:
        document = copy.deepcopy(registration_data)
        document["persisted_at"] = self._utc_now()
        result = self._watcher_registrations_collection.insert_one(document)
        return str(result.inserted_id)


# Default instance for backward compatibility
_default_persistence = MongoDBPersistence()


# Module-level functions for backward compatibility (legacy code support)
def save_event(event_data):
    return _default_persistence.save_event(event_data)


def save_baseline(entry_data):
    return _default_persistence.save_baseline_entry(entry_data)


def save_baseline_entry(entry_data):
    return _default_persistence.save_baseline_entry(entry_data)


def save_directory_snapshot(snapshot_data):
    return _default_persistence.save_directory_snapshot(snapshot_data)


def save_validation_result(validation_data):
    return _default_persistence.save_validation_result(validation_data)


def save_watcher_registration(registration_data):
    return _default_persistence.save_watcher_registration(registration_data)