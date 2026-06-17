from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RawDataQueryParams(BaseModel):
    camera_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    density: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class RawDataSummary(BaseModel):
    total: int
    limit: int
    offset: int





class ThresholdValues(BaseModel):
    low_to_medium: float
    medium_to_high: float
    high_to_heavy: float


class DirectionalThresholdBase(BaseModel):
    thresholds: ThresholdValues
    centroids: list[float] = Field(default_factory=list)


class DirectionalThresholdUpsert(DirectionalThresholdBase):
    pass


class DirectionalThresholdResponse(DirectionalThresholdBase):
    id: Optional[str] = None
    camera_id: Optional[str] = None
    updated_at: datetime


class ThresholdHistoryResponse(BaseModel):
    total: int
    items: list[DirectionalThresholdResponse]


class DatasetExportItem(BaseModel):
    camera_id: Optional[str] = None
    timestamp: datetime
    vehicle_count: int
    congestion_level: Optional[str] = None


class DatasetExportResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[DatasetExportItem]
