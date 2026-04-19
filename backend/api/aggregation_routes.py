from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.config import settings
from backend.schemas.aggregation_schema import (
    AggregationComputeResponse,
    AggregationHistoryItem,
    AggregationHistoryResponse,
    AggregationResponse,
)
from backend.services.aggregation_service import (
    aggregate_from_detections,
    compute_congestion,
    compute_window_aggregation,
    list_aggregations,
)
from backend.services.db_service import get_db

router = APIRouter(tags=["aggregation"])


@router.get("/aggregation", response_model=AggregationResponse)
def get_aggregation(
    vehicle_count: int | None = None,
    camera_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: Session = Depends(get_db),
):
    generated_at = datetime.utcnow()

    if vehicle_count is not None:
        level = compute_congestion(vehicle_count)
        return AggregationResponse(
            camera_id=camera_id,
            vehicle_count=vehicle_count,
            congestion_level=level,
            start_time=start_time,
            end_time=end_time,
            generated_at=generated_at,
        )

    aggregation = aggregate_from_detections(
        db=db,
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
    )
    return AggregationResponse(
        camera_id=aggregation.camera_id,
        vehicle_count=aggregation.vehicle_count,
        congestion_level=aggregation.congestion_level,
        start_time=start_time,
        end_time=aggregation.timestamp,
        generated_at=generated_at,
    )


@router.get("/aggregation/history", response_model=AggregationHistoryResponse)
def get_aggregation_history(
    camera_id: str | None = None,
    limit: int = Query(default=20, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    safe_limit = min(limit, settings.max_page_size)
    total, items = list_aggregations(
        db=db,
        camera_id=camera_id,
        limit=safe_limit,
        offset=offset,
    )
    return AggregationHistoryResponse(
        total=total,
        limit=safe_limit,
        offset=offset,
        items=[
            AggregationHistoryItem(
                id=item.id,
                camera_id=item.camera_id,
                vehicle_count=item.vehicle_count,
                congestion_level=item.congestion_level,
                timestamp=item.timestamp,
            )
            for item in items
        ],
    )


@router.post("/aggregation/compute", response_model=AggregationComputeResponse)
def compute_aggregation(
    camera_id: str = "CAM_01",
    window_minutes: int = Query(default=15, ge=1, le=1440),
    db: Session = Depends(get_db),
):
    record, window_start = compute_window_aggregation(
        db=db,
        camera_id=camera_id,
        window_minutes=window_minutes,
    )
    return AggregationComputeResponse(
        aggregation_id=record.id,
        camera_id=camera_id,
        window_start=window_start,
        window_end=record.timestamp,
        vehicle_count=record.vehicle_count,
        congestion_level=record.congestion_level,
    )
