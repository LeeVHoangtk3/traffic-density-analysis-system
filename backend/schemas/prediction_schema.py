from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None
    horizon_minutes: int
    source: str
    timestamp: datetime
    time_green_light: Optional[int] = None


class PredictionHistoryItem(BaseModel):
    id: str
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None
    horizon_minutes: int
    source: str
    timestamp: datetime
    time_green_light: Optional[int] = None


class PredictionHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PredictionHistoryItem]


class GreenLightRequest(BaseModel):
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None  # ✅ FIX
    horizon_minutes: int                              # ✅ FIX
    source: str                                       # ✅ FIX
    time_green_light: int
    timestamp: Optional[datetime] = None