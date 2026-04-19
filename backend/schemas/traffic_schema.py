from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
