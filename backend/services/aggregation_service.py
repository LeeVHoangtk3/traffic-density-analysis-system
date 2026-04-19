from datetime import datetime, timedelta
from typing import Optional

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
