from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AggregationResponse(BaseModel):
    camera_id: Optional[str] = None
    vehicle_count: int
    inbound_count: int = 0
    queue_proxy: int = 0
    congestion_level: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    generated_at: datetime


class AggregationHistoryItem(BaseModel):
    id: str
    camera_id: Optional[str] = None
    vehicle_count: int
    inbound_count: int = 0
    queue_proxy: int = 0
    congestion_level: str
    timestamp: datetime


class AggregationHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AggregationHistoryItem]


class AggregationComputeResponse(BaseModel):
    aggregation_id: str
    camera_id: str
    window_start: datetime
    window_end: datetime
    vehicle_count: int
    inbound_count: int
    queue_proxy: int
    congestion_level: str
