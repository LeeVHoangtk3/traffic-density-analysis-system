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
