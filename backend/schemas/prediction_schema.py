from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None
    green_light_time: int = 45 
    horizon_minutes: int
    source: str
    timestamp: datetime


class PredictionHistoryItem(BaseModel):
    id: str
    camera_id: Optional[str] = None
    predicted_density: float
    predicted_congestion_level: Optional[str] = None
    green_light_time: int = 45  # 👈 thêm
    horizon_minutes: int
    source: str
    timestamp: datetime


class PredictionHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PredictionHistoryItem]