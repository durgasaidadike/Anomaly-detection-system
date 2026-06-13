from pymongo import MongoClient
from datetime import datetime
import copy

client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

db = client["anomaly_detection"]

events_collection = db["events"]
baseline_collection = db["baseline_files"]


def save_event(event_data):

    document = copy.deepcopy(event_data)

    document["timestamp"] = datetime.utcnow()

    result = events_collection.insert_one(document)

    return str(result.inserted_id)


def save_baseline(file_data):

    document = copy.deepcopy(file_data)

    document["scan_timestamp"] = datetime.utcnow()

    result = baseline_collection.insert_one(document)

    return str(result.inserted_id)