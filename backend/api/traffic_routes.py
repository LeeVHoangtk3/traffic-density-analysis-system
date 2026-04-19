from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.vehicle_detection import VehicleDetection
from backend.services.db_service import get_db

router = APIRouter(tags=["traffic"])


@router.get("/raw-data")
def get_raw_data(
    camera_id: str | None = None,
    vehicle_type: str | None = None,
    density: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(VehicleDetection)

    if camera_id:
        query = query.filter(VehicleDetection.camera_id == camera_id)
    if vehicle_type:
        query = query.filter(VehicleDetection.vehicle_type == vehicle_type)
    if density:
        query = query.filter(VehicleDetection.density == density.upper())
    if start_time:
        query = query.filter(VehicleDetection.timestamp >= start_time)
    if end_time:
        query = query.filter(VehicleDetection.timestamp <= end_time)

    total = query.count()
    rows = (
        query.order_by(VehicleDetection.timestamp.desc())
        .offset(offset)
        .limit(min(limit, settings.max_page_size))
        .all()
    )

    return {
        "total": total,
        "limit": min(limit, settings.max_page_size),
        "offset": offset,
        "items": rows,
    }
