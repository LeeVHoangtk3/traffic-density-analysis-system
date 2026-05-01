from fastapi import APIRouter, Depends, HTTPException, status

from backend.schemas.detection_schema import DetectionCreate
from backend.services.db_service import get_db
from backend.services.detection_service import (
    create_detection,
    get_detection_by_event_id,
)

router = APIRouter(tags=["detection"])


@router.post("/detection", status_code=status.HTTP_201_CREATED)
def create_detection_route(
    data: DetectionCreate, db=Depends(get_db)
):
    existing = get_detection_by_event_id(db, data.event_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"event_id '{data.event_id}' already exists",
        )

    detection = create_detection(db, data)
    return {"status": "saved", "id": detection["id"], "event_id": detection["event_id"]}
