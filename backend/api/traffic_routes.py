from datetime import datetime

from fastapi import APIRouter, Depends, Query

from backend.config import settings
from backend.services.db_service import get_db

router = APIRouter(tags=["traffic"])


def normalize_document(document):
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return document


@router.get("/raw-data")
def get_raw_data(
    camera_id: str | None = None,
    vehicle_type: str | None = None,
    density: str | None = None,
    direction: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=settings.default_page_size, ge=1),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id
    if vehicle_type:
        filters["vehicle_type"] = vehicle_type
    if density:
        filters["density"] = density.upper()
    if direction:
        filters["direction"] = direction.lower()

    timestamp_filter = {}
    if start_time:
        timestamp_filter["$gte"] = start_time
    if end_time:
        timestamp_filter["$lte"] = end_time
    if timestamp_filter:
        filters["timestamp"] = timestamp_filter

    safe_limit = min(limit, settings.max_page_size)
    total = db.vehicle_detections.count_documents(filters)
    rows = list(
        db.vehicle_detections.find(filters)
        .sort("timestamp", -1)
        .skip(offset)
        .limit(safe_limit)
    )

    return {
        "total": total,
        "limit": safe_limit,
        "offset": offset,
        "items": [normalize_document(row) for row in rows],
    }
