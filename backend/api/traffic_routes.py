import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import settings
from backend.schemas.traffic_schema import (
    DatasetExportItem,
    DatasetExportResponse,
    Direction,
    DirectionalThresholdResponse,
    DirectionalThresholdUpsert,
    ThresholdHistoryResponse,
    TrafficLightStatusResponse,
)
from backend.services.db_service import get_db

router = APIRouter(tags=["traffic"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LANE_DIRECTIONS = ("left", "straight", "right")


def normalize_document(document):
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return document


def _normalize_threshold_document(document) -> dict:
    row = normalize_document(document)
    row["updated_at"] = row.get("updated_at") or datetime.utcnow()
    return row


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
        "camera_id": raw_status.get("camera_id", "cam01"),
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
        "updated_at": raw_status.get("updated_at") or datetime.utcnow(),
    }


@router.get("/traffic-lights/status", response_model=TrafficLightStatusResponse)
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


@router.get("/thresholds", response_model=ThresholdHistoryResponse)
def get_directional_thresholds(
    camera_id: str | None = None,
    direction: Direction | None = None,
    db=Depends(get_db),
):
    filters = {}
    if camera_id is not None:
        filters["camera_id"] = camera_id
    if direction is not None:
        filters["direction"] = direction

    rows = list(db.directional_thresholds.find(filters).sort("direction", 1))
    return ThresholdHistoryResponse(
        total=len(rows),
        items=[
            DirectionalThresholdResponse(**_normalize_threshold_document(row))
            for row in rows
        ],
    )


@router.put("/thresholds/{direction}", response_model=DirectionalThresholdResponse)
def upsert_directional_threshold(
    direction: Direction,
    payload: DirectionalThresholdUpsert,
    camera_id: str = "cam01",
    db=Depends(get_db),
):
    values = payload.thresholds
    if not (
        values.low_to_medium < values.medium_to_high < values.high_to_heavy
    ):
        raise HTTPException(
            status_code=422,
            detail="Thresholds must satisfy low_to_medium < medium_to_high < high_to_heavy.",
        )

    now = datetime.utcnow()
    document = {
        "camera_id": camera_id,
        "direction": direction,
        "thresholds": payload.thresholds.model_dump(),
        "centroids": payload.centroids,
        "updated_at": now,
    }
    db.directional_thresholds.update_one(
        {"camera_id": camera_id, "direction": direction},
        {"$set": document},
        upsert=True,
    )
    saved = db.directional_thresholds.find_one(
        {"camera_id": camera_id, "direction": direction}
    )
    return DirectionalThresholdResponse(**_normalize_threshold_document(saved))


@router.get("/dataset/export", response_model=DatasetExportResponse)
def export_training_dataset(
    camera_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=500, ge=1),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    timestamp_filter = {}
    if start_time:
        timestamp_filter["$gte"] = start_time
    if end_time:
        timestamp_filter["$lte"] = end_time
    if timestamp_filter:
        filters["timestamp"] = timestamp_filter

    safe_limit = min(limit, settings.max_page_size)
    total_records = db.traffic_aggregation.count_documents(filters)
    rows = list(
        db.traffic_aggregation.find(filters)
        .sort("timestamp", -1)
        .skip(offset)
        .limit(safe_limit)
    )

    items = []
    for row in rows:
        direction_counts = row.get("direction_counts") or {}
        congestion_levels = row.get("congestion_levels") or {}
        for direction in LANE_DIRECTIONS:
            items.append(
                DatasetExportItem(
                    camera_id=row.get("camera_id"),
                    timestamp=row["timestamp"],
                    direction=direction,
                    vehicle_count=int(direction_counts.get(direction, 0)),
                    congestion_level=congestion_levels.get(direction),
                )
            )

    return DatasetExportResponse(
        total=total_records * len(LANE_DIRECTIONS),
        limit=safe_limit,
        offset=offset,
        items=items,
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


@router.get("/api/traffic/history")
def get_traffic_history(
    camera_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db=Depends(get_db),
):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    # Dynamic Range scanning if start_time or end_time are missing
    if not start_time or not end_time:
        min_doc = db.traffic_aggregation.find_one(filters, sort=[("timestamp", 1)])
        max_doc = db.traffic_aggregation.find_one(filters, sort=[("timestamp", -1)])
        
        if min_doc and not start_time:
            start_time = min_doc["timestamp"]
        if max_doc and not end_time:
            end_time = max_doc["timestamp"]

    if start_time or end_time:
        timestamp_filter = {}
        if start_time:
            timestamp_filter["$gte"] = start_time
        if end_time:
            timestamp_filter["$lte"] = end_time
        filters["timestamp"] = timestamp_filter

    # Sort ASCENDING to draw a nice timeline from past to present
    rows = list(db.traffic_aggregation.find(filters).sort("timestamp", 1))

    return {
        "camera_id": camera_id,
        "start_time": start_time,
        "end_time": end_time,
        "total": len(rows),
        "items": [normalize_document(row) for row in rows],
    }


@router.get("/api/traffic/average")
def get_traffic_average(
    camera_id: str = "cam01",
    db=Depends(get_db),
):
    # Lấy dữ liệu của 3 camera và gom nhóm theo timestamp
    pipeline = [
        {"$match": {"camera_id": {"$in": ["cam01", "cam02", "cam03"]}}},
        {"$group": {
            "_id": "$timestamp",
            "combined_count": {"$sum": "$vehicle_count"},
            "timestamp": {"$first": "$timestamp"}
        }},
        {"$sort": {"timestamp": 1}}
    ]
    rows = list(db.traffic_aggregation.aggregate(pipeline))

    if not rows:
        return {
            "camera_id": "Làn đường đơn",
            "average_vehicle_count": 0.0,
            "peak_hour": "N/A",
            "peak_vehicle_count": 0,
            "total_records": 0,
        }

    total_vehicles = sum(int(row.get("combined_count", 0)) for row in rows)
    avg_vehicles = total_vehicles / len(rows)

    # Find peak record
    peak_record = max(rows, key=lambda row: int(row.get("combined_count", 0)))
    peak_count = int(peak_record.get("combined_count", 0))
    peak_time = peak_record.get("timestamp")

    if isinstance(peak_time, datetime):
        peak_hour_str = f"{peak_time.hour:02d}:00 - {(peak_time.hour + 1) % 24:02d}:00"
    else:
        try:
            dt = datetime.fromisoformat(str(peak_time).replace("Z", "+00:00"))
            peak_hour_str = f"{dt.hour:02d}:00 - {(dt.hour + 1) % 24:02d}:00"
        except:
            peak_hour_str = "N/A"

    return {
        "camera_id": "Làn đường đơn",
        "average_vehicle_count": round(avg_vehicles, 2),
        "peak_hour": peak_hour_str,
        "peak_vehicle_count": peak_count,
        "total_records": len(rows),
    }
