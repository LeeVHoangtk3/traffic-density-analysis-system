from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.prediction_schema import PredictionResponse
from backend.services.db_service import get_db
from backend.services.prediction_service import predict_next_density

router = APIRouter(tags=["prediction"])


@router.get("/predict-next", response_model=PredictionResponse)
def predict_next(camera_id: str | None = None, db: Session = Depends(get_db)):
    prediction = predict_next_density(db=db, camera_id=camera_id)
    return PredictionResponse(
        camera_id=prediction.camera_id,
        predicted_density=prediction.predicted_density,
        horizon_minutes=prediction.horizon_minutes,
        source=prediction.source,
        timestamp=prediction.timestamp,
    )
