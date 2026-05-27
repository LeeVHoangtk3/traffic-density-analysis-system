from datetime import datetime

from fastapi import APIRouter, Depends, Query

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
    classify_direction_counts,
    empty_direction_counts,
    compute_window_aggregation,
    list_aggregations,
)
from backend.services.db_service import get_db

router = APIRouter(tags=["aggregation"])


def _direction_counts(item) -> dict:
    value = getattr(item, "direction_counts", None)
    return value if value else empty_direction_counts()


def _congestion_levels(db, camera_id: str | None, item) -> dict:
    value = getattr(item, "congestion_levels", None)
    if value:
        return value
    return classify_direction_counts(db, camera_id, _direction_counts(item))


@router.get("/aggregation", response_model=AggregationResponse)
def get_aggregation(
    vehicle_count: int | None = None,
    camera_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db=Depends(get_db),
):
    generated_at = datetime.utcnow()

    if vehicle_count is not None:
        level = compute_congestion(vehicle_count)
        direction_counts = empty_direction_counts()
        direction_counts["straight"] = vehicle_count
        congestion_levels = classify_direction_counts(
            db, camera_id, direction_counts
        )
        return AggregationResponse(
            camera_id=camera_id,
            vehicle_count=vehicle_count,
            inbound_count=vehicle_count,
            queue_proxy=0,
            congestion_level=level,
            direction_counts=direction_counts,
            congestion_levels=congestion_levels,
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
        inbound_count=aggregation.inbound_count or 0,
        queue_proxy=aggregation.queue_proxy or 0,
        congestion_level=aggregation.congestion_level,
        direction_counts=_direction_counts(aggregation),
        congestion_levels=_congestion_levels(db, aggregation.camera_id, aggregation),
        start_time=start_time,
        end_time=aggregation.timestamp,
        generated_at=generated_at,
    )


@router.get("/aggregation/history", response_model=AggregationHistoryResponse)
def get_aggregation_history(
    camera_id: str | None = None,
    limit: int = Query(default=20, ge=1),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
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
                inbound_count=item.inbound_count or 0,
                queue_proxy=item.queue_proxy or 0,
                congestion_level=item.congestion_level,
                direction_counts=_direction_counts(item),
                congestion_levels=_congestion_levels(db, item.camera_id, item),
                timestamp=item.timestamp,
            )
            for item in items
        ],
    )


@router.post("/aggregation/compute", response_model=AggregationComputeResponse)
def compute_aggregation(
    camera_id: str = "cam01",
    window_minutes: int = Query(default=15, ge=1, le=1440),
    db=Depends(get_db),
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
        inbound_count=record.inbound_count or 0,
        queue_proxy=record.queue_proxy or 0,
        congestion_level=record.congestion_level,
        direction_counts=_direction_counts(record),
        congestion_levels=_congestion_levels(db, record.camera_id, record),
    )
