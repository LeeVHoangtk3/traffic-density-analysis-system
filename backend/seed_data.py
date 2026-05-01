from datetime import datetime

from sqlalchemy import func

from backend.database import SessionLocal
from backend.models.camera import Camera
from backend.models.traffic_aggregation import TrafficAggregation
from backend.models.vehicle_detection import VehicleDetection
from backend.services.aggregation_service import compute_congestion
from backend.services.prediction_service import predict_next_density


def seed_cameras(db):
    camera_ids = [
        row[0]
        for row in db.query(VehicleDetection.camera_id)
        .filter(VehicleDetection.camera_id.isnot(None))
        .distinct()
        .all()
        if row[0]
    ]

    created = 0
    for camera_id in camera_ids:
        existing = (
            db.query(Camera)
            .filter(Camera.camera_id == camera_id)
            .first()
        )
        if existing:
            continue

        camera = Camera(
            camera_id=camera_id,
            name=f"Camera {camera_id}",
            location="Chua cap nhat",
        )
        db.add(camera)
        created += 1

    if created:
        db.commit()
    return created, camera_ids


def seed_aggregations(db, camera_ids):
    created = 0

    for camera_id in camera_ids:
        existing = (
            db.query(TrafficAggregation)
            .filter(TrafficAggregation.camera_id == camera_id)
            .first()
        )
        if existing:
            continue

        vehicle_count = (
            db.query(func.count(VehicleDetection.id))
            .filter(VehicleDetection.camera_id == camera_id)
            .scalar()
            or 0
        )

        latest_timestamp = (
            db.query(func.max(VehicleDetection.timestamp))
            .filter(VehicleDetection.camera_id == camera_id)
            .scalar()
        ) or datetime.utcnow()

        aggregation = TrafficAggregation(
            camera_id=camera_id,
            vehicle_count=vehicle_count,
            congestion_level=compute_congestion(vehicle_count),
            timestamp=latest_timestamp,
        )
        db.add(aggregation)
        created += 1

    if created:
        db.commit()
    return created


def seed_predictions(db, camera_ids):
    created = 0
    for camera_id in camera_ids:
        try:
            prediction = predict_next_density(db, camera_id=camera_id)
            if prediction:
                created += 1
        except Exception as exc:
            print(f"[WARN] Khong the tao prediction cho {camera_id}: {exc}")
    return created


def main():
    db = SessionLocal()
    try:
        total_detections = db.query(func.count(VehicleDetection.id)).scalar() or 0
        if total_detections == 0:
            print("Khong co du lieu trong bang vehicle_detections.")
            print("Hay chay detection truoc, sau do seed lai.")
            return

        camera_created, camera_ids = seed_cameras(db)
        aggregation_created = seed_aggregations(db, camera_ids)
        prediction_created = seed_predictions(db, camera_ids)

        print("Seed du lieu backend hoan tat.")
        print(f"- Cameras moi: {camera_created}")
        print(f"- Aggregations moi: {aggregation_created}")
        print(f"- Predictions moi: {prediction_created}")
        print(f"- Camera duoc xu ly: {len(camera_ids)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
