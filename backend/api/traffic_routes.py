import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import settings
from backend.schemas.traffic_schema import (
    DatasetExportItem,
    DatasetExportResponse,
    DirectionalThresholdResponse,
    DirectionalThresholdUpsert,
    ThresholdHistoryResponse,
)
from backend.services.db_service import get_db

router = APIRouter(tags=["traffic"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def normalize_document(document):
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return document


def _normalize_threshold_document(document) -> dict:
    row = normalize_document(document)
    row["updated_at"] = row.get("updated_at") or datetime.utcnow()
    return row





@router.get("/thresholds", response_model=ThresholdHistoryResponse)
def get_directional_thresholds(
    camera_id: str | None = None,
    db=Depends(get_db),
):
    filters = {}
    if camera_id is not None:
        filters["camera_id"] = camera_id

    rows = list(db.directional_thresholds.find(filters))
    return ThresholdHistoryResponse(
        total=len(rows),
        items=[
            DirectionalThresholdResponse(**_normalize_threshold_document(row))
            for row in rows
        ],
    )


@router.put("/thresholds", response_model=DirectionalThresholdResponse)
def upsert_directional_threshold(
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
        "thresholds": payload.thresholds.model_dump(),
        "centroids": payload.centroids,
        "updated_at": now,
    }
    db.directional_thresholds.update_one(
        {"camera_id": camera_id},
        {"$set": document},
        upsert=True,
    )
    saved = db.directional_thresholds.find_one(
        {"camera_id": camera_id}
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
        items.append(
            DatasetExportItem(
                camera_id=row.get("camera_id"),
                timestamp=row["timestamp"],
                vehicle_count=row.get("vehicle_count", 0),
                congestion_level=row.get("congestion_level"),
            )
        )

    return DatasetExportResponse(
        total=total_records,
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
    # Lấy dữ liệu đếm xe của camera mục tiêu
    pipeline = [
        {"$match": {"camera_id": camera_id}},
        {"$project": {
            "_id": 0,
            "combined_count": "$vehicle_count",
            "timestamp": 1
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
