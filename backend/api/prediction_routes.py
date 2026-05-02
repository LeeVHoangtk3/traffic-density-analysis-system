from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import settings
from backend.schemas.prediction_schema import (
    PredictionHistoryItem,
    PredictionHistoryResponse,
    PredictionResponse,
)
from backend.services.db_service import get_db
from backend.services.prediction_service import (
    get_recent_aggregations,
    list_predictions,
    predict_next_density,
)

router = APIRouter(tags=["prediction"])


@router.get("/predict-next", response_model=PredictionResponse)
def predict_next(camera_id: str | None = None, db=Depends(get_db)):
    recent_camera_id = camera_id or "CAM_01"
    history = get_recent_aggregations(db, camera_id=recent_camera_id, n=5)

    if history.empty:
        prediction = predict_next_density(db=db, camera_id=camera_id)
        if prediction.predicted_density == 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Chua co du lieu lich su cho camera '{recent_camera_id}' "
                    "de tao du bao."
                ),
            )
    else:
        prediction = predict_next_density(db=db, camera_id=camera_id)

    return PredictionResponse(
        camera_id=prediction.camera_id,
        predicted_density=prediction.predicted_density,
        predicted_congestion_level=getattr(
            prediction,
            "predicted_congestion_level",
            None
        ),
        green_light_time=getattr(
            prediction,
            "green_light_time",
            45
        ),
        horizon_minutes=prediction.horizon_minutes,
        source=prediction.source,
        timestamp=prediction.timestamp,
    )


@router.get("/predictions/history", response_model=PredictionHistoryResponse)
def get_prediction_history(
    camera_id: str | None = None,
    limit: int = Query(default=20, ge=1),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    safe_limit = min(limit, settings.max_page_size)
    total, items = list_predictions(
        db=db,
        camera_id=camera_id,
        limit=safe_limit,
        offset=offset,
    )

    return PredictionHistoryResponse(
        total=total,
        limit=safe_limit,
        offset=offset,
        items=[
            PredictionHistoryItem(
                id=item.id,
                camera_id=item.camera_id,
                predicted_density=item.predicted_density,
                predicted_congestion_level=getattr(
                    item,
                    "predicted_congestion_level",
                    None
                ),
                green_light_time=getattr(
                    item,
                    "green_light_time",
                    45
                ),
                horizon_minutes=item.horizon_minutes,
                source=item.source,
                timestamp=item.timestamp,
            )
            for item in items
        ],
    )