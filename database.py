from pymongo import MongoClient
from datetime import datetime, timezone
import copy

from persistence_port import PersistencePort


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
        connection_string: str = "mongodb://localhost:27017/",
        database_name: str = "anomaly_detection",
        server_selection_timeout_ms: int = 5000
    ):
        self._client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=server_selection_timeout_ms
        )
        self._db = self._client[database_name]

        self._events_collection = self._db["events"]
        self._baseline_inventory_collection = self._db["baseline_inventory"]
        self._directory_snapshots_collection = self._db["directory_snapshots"]
        self._directory_validations_collection = self._db["directory_validations"]
        self._watcher_registrations_collection = self._db["watcher_registrations"]

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