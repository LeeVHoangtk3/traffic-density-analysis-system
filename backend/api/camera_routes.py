from fastapi import APIRouter, Depends, status

from backend.schemas.camera_schema import CameraCreate, CameraResponse
from backend.services.camera_service import create_camera, list_cameras
from backend.services.db_service import get_db

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraResponse])
def get_cameras(db=Depends(get_db)):
    return list_cameras(db)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def add_camera(data: CameraCreate, db=Depends(get_db)):
    return create_camera(db, data)
