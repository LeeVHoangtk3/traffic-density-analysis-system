from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.services.db_service import get_db
from backend.models.vehicle_detection import VehicleDetection

router = APIRouter()

@router.get("/raw-data")
def get_raw_data(db: Session = Depends(get_db)):

    data = db.query(VehicleDetection).all()

    return data