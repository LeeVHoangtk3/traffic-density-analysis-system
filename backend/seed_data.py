from datetime import datetime

from backend.mongo_database import db, init_mongo_indexes
from backend.services.aggregation_service import compute_congestion
from backend.services.prediction_service import predict_next_density


def seed_cameras(database):
    camera_ids = sorted(
        camera_id
        for camera_id in database.vehicle_detections.distinct("camera_id")
        if camera_id
    )

    created = 0
    updated = 0
    for camera_id in camera_ids:
        result = database.cameras.update_one(
            {"camera_id": camera_id},
            {
                "$setOnInsert": {
                    "camera_id": camera_id,
                    "name": f"Camera {camera_id}",
                    "location": "Chua cap nhat",
                },
                "$set": {
                    "baseline_green": 30,
                    "monitored_direction": "inbound",
                },
            },
            upsert=True,
        )
        if result.upserted_id:
            created += 1
        elif result.modified_count:
            updated += 1

    return created, updated, camera_ids


def seed_aggregations(database, camera_ids):
    created = 0

    for camera_id in camera_ids:
        existing = database.traffic_aggregation.find_one({"camera_id": camera_id})
        if existing:
            continue

        vehicle_count = database.vehicle_detections.count_documents(
            {"camera_id": camera_id}
        )
        inbound_count = database.vehicle_detections.count_documents(
            {"camera_id": camera_id, "direction": "inbound"}
        )

        latest = database.vehicle_detections.find_one(
            {"camera_id": camera_id},
            sort=[("timestamp", -1)],
        )
        latest_timestamp = latest["timestamp"] if latest else datetime.utcnow()

        database.traffic_aggregation.insert_one(
            {
                "camera_id": camera_id,
                "vehicle_count": vehicle_count,
                "inbound_count": inbound_count,
                "queue_proxy": inbound_count,
                "congestion_level": compute_congestion(vehicle_count),
                "timestamp": latest_timestamp,
            }
        )
        created += 1

    return created


def seed_predictions(database, camera_ids):
    created = 0
    for camera_id in camera_ids:
        try:
            prediction = predict_next_density(database, camera_id=camera_id)
            if prediction:
                created += 1
        except Exception as exc:
            print(f"[WARN] Khong the tao prediction cho {camera_id}: {exc}")
    return created


def main():
    init_mongo_indexes()
    total_detections = db.vehicle_detections.count_documents({})
    if total_detections == 0:
        print("Khong co du lieu trong collection vehicle_detections.")
        print("Hay chay detection truoc, sau do seed lai.")
        return

    camera_created, camera_updated, camera_ids = seed_cameras(db)
    aggregation_created = seed_aggregations(db, camera_ids)
    prediction_created = seed_predictions(db, camera_ids)

    print("Seed du lieu backend hoan tat.")
    print(f"- Cameras moi: {camera_created}")
    print(f"- Cameras cap nhat: {camera_updated}")
    print(f"- Aggregations moi: {aggregation_created}")
    print(f"- Predictions moi: {prediction_created}")
    print(f"- Camera duoc xu ly: {len(camera_ids)}")


if __name__ == "__main__":
    main()
