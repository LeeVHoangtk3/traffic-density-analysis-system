from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Union

class DetectionCreate(BaseModel):

    event_id: str
    camera_id: str
    track_id: Union[int, str]
    vehicle_type: str
    density: str
    event_type: str
    timestamp: datetime
    confidence: Optional[float] = None
