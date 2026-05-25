from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


Direction = Literal["left", "straight", "right"]


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


class PhaseTiming(BaseModel):
    phase_1_green: int = 50
    phase_2_green: int = 30
    delta_phase_1: int = 0
    delta_phase_2: int = 0


class TrafficLightPhase(BaseModel):
    name: str
    directions: list[Direction]
    status: Literal["GREEN", "RED", "YELLOW"] = "RED"
    duration: int = Field(ge=0)


class TrafficLightStatusResponse(BaseModel):
    camera_id: str
    active_phase: Literal["phase_1", "phase_2"]
    cycle_time: int = 90
    transition_time: int = 10
    phase_timing: PhaseTiming
    phases: dict[str, TrafficLightPhase]
    mode: str = "unknown"
    source: dict
    updated_at: datetime


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
    direction: Direction
    updated_at: datetime


class ThresholdHistoryResponse(BaseModel):
    total: int
    items: list[DirectionalThresholdResponse]


class DatasetExportItem(BaseModel):
    camera_id: Optional[str] = None
    timestamp: datetime
    direction: Direction
    vehicle_count: int
    congestion_level: Optional[str] = None


class DatasetExportResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[DatasetExportItem]
