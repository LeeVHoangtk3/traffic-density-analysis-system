from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.traffic_prediction import TrafficPrediction
from backend.models.vehicle_detection import VehicleDetection


def _load_predictor():
    ml_service_dir = Path(__file__).resolve().parents[2] / "ml_service"
    if not ml_service_dir.exists():
        return None

    ml_service_path = str(ml_service_dir)
    if ml_service_path not in sys.path:
        sys.path.insert(0, ml_service_path)

    try:
        from traffic_predictor import TrafficPredictor
    except Exception:
        return None

    model_path = ml_service_dir / "model.pkl"
    predictor = TrafficPredictor(model_path=str(model_path))
    if not predictor.load_model():
        return None
    return predictor


def _build_prediction_history(
    db: Session, camera_id: Optional[str], periods: int = 8
) -> pd.DataFrame:
    bucket = "%Y-%m-%d %H:%M:00"
    query = (
        db.query(
            func.strftime(bucket, VehicleDetection.timestamp).label("bucket_time"),
            func.count(VehicleDetection.id).label("vehicle_count"),
        )
        .group_by("bucket_time")
        .order_by("bucket_time.desc()")
        .limit(periods)
    )

    if camera_id:
        query = query.filter(VehicleDetection.camera_id == camera_id)

    rows = list(reversed(query.all()))
    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    history = pd.DataFrame(
        [
            {
                "timestamp": pd.to_datetime(row.bucket_time),
                "vehicle_count": int(row.vehicle_count),
            }
            for row in rows
        ]
    )
    return history


def predict_next_density(
    db: Session, camera_id: Optional[str] = None
) -> TrafficPrediction:
    history = _build_prediction_history(db, camera_id)
    predictor = _load_predictor()

    if predictor is not None and len(history) >= 3:
        predicted_value = float(predictor.predict(history))
    else:
        predicted_value = float(history["vehicle_count"].mean()) if not history.empty else 0.0

    prediction = TrafficPrediction(
        camera_id=camera_id,
        predicted_density=predicted_value,
        horizon_minutes=settings.prediction_horizon_minutes,
        source="ml_service" if predictor is not None and len(history) >= 3 else "fallback",
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
