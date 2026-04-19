from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field


class VehicleType(str, Enum):
    bus = "bus"
    car = "car"
    motorcycle = "motorcycle"
    truck = "truck"


class DensityLevel(str, Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    severe = "SEVERE"


class EventType(str, Enum):
    line_crossing = "line_crossing"
    zone_entry = "zone_entry"
    zone_exit = "zone_exit"


class DetectionCreate(BaseModel):
    event_id: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    track_id: Union[int, str]
    vehicle_type: VehicleType
    density: DensityLevel
    event_type: EventType
    timestamp: datetime
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
