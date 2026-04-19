from sqlalchemy.orm import Session

from backend.models.camera import Camera
from backend.schemas.camera_schema import CameraCreate


def list_cameras(db: Session) -> list[Camera]:
    return db.query(Camera).order_by(Camera.id.asc()).all()


def create_camera(db: Session, data: CameraCreate) -> Camera:
    camera = Camera(
        camera_id=data.camera_id,
        name=data.name,
        location=data.location,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera
