import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import settings
from backend.services.db_service import get_db

router = APIRouter(tags=["traffic"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def normalize_document(document):
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return document


def _light_status_candidates() -> list[Path]:
    return [
        PROJECT_ROOT / "integration_system" / "light_status.json",
        PROJECT_ROOT / "light_status.json",
    ]


def _normalize_light_status(raw_status: dict) -> dict:
    phase_timing = raw_status.get("phase_timing") or {}
    phase_1_green = int(
        phase_timing.get("phase_1_green")
        or raw_status.get("phase_1_green")
        or raw_status.get("green_time")
        or 50
    )
    phase_2_green = int(
        phase_timing.get("phase_2_green")
        or raw_status.get("phase_2_green")
        or max(25, 80 - phase_1_green)
    )

    active_phase = raw_status.get("active_phase")
    if not active_phase:
        phase_name = str(raw_status.get("phase", "")).lower()
        active_phase = "phase_2" if "left" in phase_name else "phase_1"

    phases = raw_status.get("phases") or {
        "phase_1": {
            "name": "straight_right",
            "directions": ["straight", "right"],
            "status": "GREEN" if active_phase == "phase_1" else "RED",
            "duration": phase_1_green,
        },
        "phase_2": {
            "name": "left",
            "directions": ["left"],
            "status": "GREEN" if active_phase == "phase_2" else "RED",
            "duration": phase_2_green,
        },
    }

    return {
        "camera_id": raw_status.get("camera_id", "CAM_01"),
        "active_phase": active_phase,
        "cycle_time": int(raw_status.get("cycle_time", 90)),
        "transition_time": int(raw_status.get("transition_time", 10)),
        "phase_timing": {
            "phase_1_green": phase_1_green,
            "phase_2_green": phase_2_green,
            "delta_phase_1": int(
                phase_timing.get("delta_phase_1")
                or raw_status.get("delta_phase_1")
                or phase_1_green - 50
            ),
            "delta_phase_2": int(
                phase_timing.get("delta_phase_2")
                or raw_status.get("delta_phase_2")
                or phase_2_green - 30
            ),
        },
        "phases": phases,
        "mode": raw_status.get("mode", "unknown"),
        "source": raw_status,
        "updated_at": raw_status.get("updated_at") or datetime.utcnow().isoformat(),
    }


@router.get("/traffic-lights/status")
def get_traffic_light_status():
    for path in _light_status_candidates():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as file:
                return _normalize_light_status(json.load(file))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid traffic light status JSON: {path}",
            ) from exc

    raise HTTPException(
        status_code=404,
        detail="Khong tim thay light_status.json.",
    )


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

    safe_limit = limit
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
