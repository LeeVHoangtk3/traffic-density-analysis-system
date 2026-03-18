from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.detection_schema import DetectionCreate
from backend.models.vehicle_detection import VehicleDetection
from backend.services.db_service import get_db

router = APIRouter()

@router.post("/detection")
def create_detection(data: DetectionCreate, db: Session = Depends(get_db)):

    detection = VehicleDetection(
        event_id=data.event_id,
        camera_id=data.camera_id,
        track_id=str(data.track_id),
        vehicle_type=data.vehicle_type,
        density=data.density,
        event_type=data.event_type,
        confidence=data.confidence,
        timestamp=data.timestamp
    )

    db.add(detection)
    db.commit()
    db.refresh(detection)

    return {
        "status": "saved",
        "id": detection.id
    }
