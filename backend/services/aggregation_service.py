from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.traffic_aggregation import TrafficAggregation
from backend.models.vehicle_detection import VehicleDetection


def compute_congestion(vehicle_count: int) -> str:
    if vehicle_count < 10:
        return "Low"
    if vehicle_count < 30:
        return "Medium"
    if vehicle_count < 60:
        return "High"
    return "Severe"


def aggregate_from_detections(
    db: Session,
    camera_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> TrafficAggregation:
    end_time = end_time or datetime.utcnow()
    start_time = start_time or (end_time - timedelta(minutes=15))

    query = db.query(VehicleDetection).filter(
        VehicleDetection.timestamp >= start_time,
        VehicleDetection.timestamp <= end_time,
    )

    if camera_id:
        query = query.filter(VehicleDetection.camera_id == camera_id)

    vehicle_count = query.count()
    congestion_level = compute_congestion(vehicle_count)

    aggregation = TrafficAggregation(
        camera_id=camera_id,
        vehicle_count=vehicle_count,
        congestion_level=congestion_level,
        timestamp=end_time,
    )
    db.add(aggregation)
    db.commit()
    db.refresh(aggregation)
    return aggregation


def compute_window_aggregation(
    db: Session,
    camera_id: str,
    window_minutes: int = 15,
) -> tuple[TrafficAggregation, datetime]:
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    vehicle_count = (
        db.query(func.count(func.distinct(VehicleDetection.track_id)))
        .filter(
            VehicleDetection.camera_id == camera_id,
            VehicleDetection.timestamp >= window_start,
            VehicleDetection.timestamp <= now,
        )
        .scalar()
        or 0
    )

    aggregation = TrafficAggregation(
        camera_id=camera_id,
        vehicle_count=vehicle_count,
        congestion_level=compute_congestion(vehicle_count),
        timestamp=now,
    )
    db.add(aggregation)
    db.commit()
    db.refresh(aggregation)
    return aggregation, window_start


def list_aggregations(
    db: Session,
    camera_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[TrafficAggregation]]:
    query = db.query(TrafficAggregation)
    if camera_id:
        query = query.filter(TrafficAggregation.camera_id == camera_id)

    total = query.count()
    items = (
        query.order_by(TrafficAggregation.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, items
