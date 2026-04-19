from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    camera_id: Optional[str] = None
    predicted_density: float
    horizon_minutes: int
    source: str
    timestamp: datetime
