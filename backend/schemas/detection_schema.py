from pydantic import BaseModel
from datetime import datetime

class DetectionCreate(BaseModel):

    camera_id: str
    vehicle_type: str
    confidence: float
    timestamp: datetime