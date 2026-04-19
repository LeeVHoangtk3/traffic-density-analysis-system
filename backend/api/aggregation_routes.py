from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.aggregation_schema import AggregationResponse
from backend.services.aggregation_service import (
    aggregate_from_detections,
    compute_congestion,
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
