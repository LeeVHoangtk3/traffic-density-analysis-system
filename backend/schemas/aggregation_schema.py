from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DirectionCounts(BaseModel):
    left: int = 0
    straight: int = 0
    right: int = 0


class DirectionCongestionLevels(BaseModel):
    left: str = "Low"
    straight: str = "Low"
    right: str = "Low"


class AggregationResponse(BaseModel):
    camera_id: Optional[str] = None
    vehicle_count: int
    inbound_count: int = 0
    queue_proxy: int = 0
    congestion_level: str
    direction_counts: DirectionCounts = Field(default_factory=DirectionCounts)
    congestion_levels: DirectionCongestionLevels = Field(
        default_factory=DirectionCongestionLevels
    )
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
    direction_counts: DirectionCounts = Field(default_factory=DirectionCounts)
    congestion_levels: DirectionCongestionLevels = Field(
        default_factory=DirectionCongestionLevels
    )
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
    direction_counts: DirectionCounts
    congestion_levels: DirectionCongestionLevels
