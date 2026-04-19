from typing import Optional

from sqlalchemy.orm import Session

from backend.models.vehicle_detection import VehicleDetection
from backend.schemas.detection_schema import DetectionCreate


def get_detection_by_event_id(
    db: Session, event_id: str
) -> Optional[VehicleDetection]:
    return (
        db.query(VehicleDetection)
        .filter(VehicleDetection.event_id == event_id)
        .first()
    )


def create_detection(db: Session, data: DetectionCreate) -> VehicleDetection:
    detection = VehicleDetection(
        event_id=data.event_id,
        camera_id=data.camera_id,
        track_id=str(data.track_id),
        vehicle_type=data.vehicle_type,
        density=data.density,
        event_type=data.event_type,
        confidence=data.confidence,
        timestamp=data.timestamp,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection
