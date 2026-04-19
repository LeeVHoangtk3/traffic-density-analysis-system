from typing import Optional

from pydantic import BaseModel


class CameraBase(BaseModel):
    name: str
    location: Optional[str] = None


class CameraCreate(CameraBase):
    camera_id: Optional[str] = None


class CameraResponse(CameraBase):
    id: int
    camera_id: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True
