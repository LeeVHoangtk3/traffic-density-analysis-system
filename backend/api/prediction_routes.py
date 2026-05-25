<<<<<<< HEAD
from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
=======
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import settings
from backend.schemas.prediction_schema import (
    PredictionHistoryItem,
    PredictionHistoryResponse,
    PredictionResponse,
>>>>>>> origin/cuong
)

from backend.services.db_service import get_db
from backend.config import settings

from backend.services.prediction_service import (
    predict_next_density,
    list_predictions,
    get_recent_aggregations,
)

from backend.schemas.prediction_schema import (
    PredictionResponse,
    PredictionHistoryResponse,
    PredictionHistoryItem,
)

router = APIRouter()

def _predictions(item) -> dict:
    return getattr(item, "predictions", None) or {
        "left": 0,
        "straight": int(getattr(item, "predicted_density", 0) or 0),
        "right": 0,
    }


def _congestion_levels(item) -> dict:
    return getattr(item, "congestion_levels", None) or {
        "left": None,
        "straight": getattr(item, "predicted_congestion_level", None),
        "right": None,
    }


def _phase_timing(item) -> dict:
    return getattr(item, "phase_timing", None) or {
        "phase_1_green": getattr(item, "green_light_time", 45),
        "phase_2_green": 30,
        "delta_phase_1": getattr(item, "green_light_time", 45) - 50,
        "delta_phase_2": 0,
    }


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
        predictions=_predictions(prediction),
        congestion_levels=_congestion_levels(prediction),
        phase_timing=_phase_timing(prediction),
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
                predictions=_predictions(item),
                congestion_levels=_congestion_levels(item),
                phase_timing=_phase_timing(item),
                horizon_minutes=item.horizon_minutes,
                source=item.source,
                timestamp=item.timestamp,
            )
            for item in items
        ],
    )
