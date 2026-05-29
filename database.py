from pymongo import MongoClient
from datetime import datetime
import copy

client = MongoClient("mongodb://localhost:27017/")

db = client["anomaly_detection"]

events_collection = db["events"]


def save_event(event_data):
    document = copy.deepcopy(event_data)
    document["timestamp"] = datetime.now()
    result = events_collection.insert_one(document)
    return str(result.inserted_id)