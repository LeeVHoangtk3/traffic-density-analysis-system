from pymongo import ASCENDING, DESCENDING, MongoClient

from backend.config import settings


if not settings.db_url:
    raise RuntimeError("Missing DB_URL or MONGODB_URI in .env for MongoDB Atlas.")

client = MongoClient(settings.db_url, serverSelectionTimeoutMS=5000)
db = client[settings.mongodb_db]


def init_mongo_indexes() -> None:
    db.vehicle_detections.create_index([("event_id", ASCENDING)], unique=True)
    db.vehicle_detections.create_index([("camera_id", ASCENDING)])
    db.vehicle_detections.create_index([("timestamp", DESCENDING)])
    db.vehicle_detections.create_index(
        [("camera_id", ASCENDING), ("timestamp", DESCENDING)]
    )
    db.vehicle_detections.create_index([("direction", ASCENDING)])

    db.traffic_aggregation.create_index(
        [("camera_id", ASCENDING), ("timestamp", DESCENDING)]
    )
    db.traffic_predictions.create_index(
        [("camera_id", ASCENDING), ("timestamp", DESCENDING)]
    )
    db.cameras.create_index([("camera_id", ASCENDING)], unique=True, sparse=True)


def ping_mongo() -> bool:
    client.admin.command("ping")
    return True
