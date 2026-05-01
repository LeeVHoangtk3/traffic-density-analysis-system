from typing import Optional

from pydantic import BaseModel


class CameraBase(BaseModel):
    name: str
    location: Optional[str] = None
    baseline_green: int = 30
    monitored_direction: str = "inbound"


class CameraCreate(CameraBase):
    camera_id: Optional[str] = None


class CameraResponse(CameraBase):
    id: str
    camera_id: Optional[str] = None

    model_config = {"from_attributes": True}
