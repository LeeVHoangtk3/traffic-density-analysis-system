from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AggregationResponse(BaseModel):
    camera_id: Optional[str] = None
    vehicle_count: int
    congestion_level: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    generated_at: datetime


class AggregationHistoryItem(BaseModel):
    id: int
    camera_id: Optional[str] = None
    vehicle_count: int
    congestion_level: str
    timestamp: datetime


class AggregationHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AggregationHistoryItem]


class AggregationComputeResponse(BaseModel):
    aggregation_id: int
    camera_id: str
    window_start: datetime
    window_end: datetime
    vehicle_count: int
    congestion_level: str
