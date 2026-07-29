from pymongo import MongoClient
from datetime import datetime, timezone
import copy


client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

db = client["anomaly_detection"]

events_collection = db["events"]
baseline_inventory_collection = db["baseline_inventory"]
directory_snapshots_collection = db["directory_snapshots"]
directory_validations_collection = db["directory_validations"]
watcher_registrations_collection = db["watcher_registrations"]


def utc_now():
    return datetime.now(timezone.utc)


def save_event(event_data):
    document = copy.deepcopy(event_data)
    document["timestamp"] = utc_now()
    result = events_collection.insert_one(document)
    return str(result.inserted_id)


def save_baseline_entry(entry_data):
    document = copy.deepcopy(entry_data)
    document["persisted_at"] = utc_now()
    result = baseline_inventory_collection.insert_one(document)
    return str(result.inserted_id)


def save_directory_snapshot(snapshot_data):
    document = copy.deepcopy(snapshot_data)
    document["persisted_at"] = utc_now()
    result = directory_snapshots_collection.insert_one(document)
    return str(result.inserted_id)


def save_validation_result(validation_data):
    document = copy.deepcopy(validation_data)
    document["persisted_at"] = utc_now()
    result = directory_validations_collection.insert_one(document)
    return str(result.inserted_id)


def save_watcher_registration(registration_data):
    document = copy.deepcopy(registration_data)
    document["persisted_at"] = utc_now()
    result = watcher_registrations_collection.insert_one(document)
    return str(result.inserted_id)