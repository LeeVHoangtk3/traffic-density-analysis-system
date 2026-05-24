from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DirectionPredictions(BaseModel):
    left: int = 0
    straight: int = 0
    right: int = 0


class DirectionCongestionLevels(BaseModel):
    left: Optional[str] = None
    straight: Optional[str] = None
    right: Optional[str] = None


class PhaseTiming(BaseModel):
    phase_1_green: int = 50
    phase_2_green: int = 30
    delta_phase_1: int = 0
    delta_phase_2: int = 0


class PredictionResponse(BaseModel):
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None
    green_light_time: int = 45
    predictions: DirectionPredictions = Field(default_factory=DirectionPredictions)
    congestion_levels: DirectionCongestionLevels = Field(
        default_factory=DirectionCongestionLevels
    )
    phase_timing: PhaseTiming = Field(default_factory=PhaseTiming)
    horizon_minutes: int
    source: str
    timestamp: datetime


class PredictionHistoryItem(BaseModel):
    id: str
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None
    green_light_time: int = 45
    predictions: DirectionPredictions = Field(default_factory=DirectionPredictions)
    congestion_levels: DirectionCongestionLevels = Field(
        default_factory=DirectionCongestionLevels
    )
    phase_timing: PhaseTiming = Field(default_factory=PhaseTiming)
    horizon_minutes: int
    source: str
    timestamp: datetime


class PredictionHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PredictionHistoryItem]
