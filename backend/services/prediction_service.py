from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pandas as pd
from pymongo import DESCENDING

from backend.config import settings


def to_object(document):
    if not document:
        return None
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return SimpleNamespace(**document)


def get_recent_aggregations(db, camera_id: str, n: int = 5) -> pd.DataFrame:
    rows = list(
        db.traffic_aggregation.find({"camera_id": camera_id})
        .sort("timestamp", DESCENDING)
        .limit(n)
    )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    df = pd.DataFrame([
        {
            "timestamp": row["timestamp"],
            "vehicle_count": int(row.get("vehicle_count", 0)),
        }
        for row in rows
    ])

    return df.sort_values("timestamp").reset_index(drop=True)


def _load_predictors():
    ml_service_dir = Path(__file__).resolve().parents[2] / "ml_service"
    if not ml_service_dir.exists():
        return None

    if str(ml_service_dir) not in sys.path:
        sys.path.insert(0, str(ml_service_dir))

    try:
        from traffic_predictor import TrafficPredictor
    except Exception:
        return None

    model_path = ml_service_dir / "model.pkl"
    predictor = TrafficPredictor(model_path=str(model_path))

    if not predictor.load_model():
        return None

    return predictor


def _build_history_from_detections(db, camera_id: Optional[str], periods: int):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    rows = list(
        db.vehicle_detections.find(filters, {"timestamp": 1})
        .sort("timestamp", DESCENDING)
        .limit(max(periods * 50, 100))
    )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    df = pd.DataFrame([{"timestamp": row["timestamp"]} for row in rows])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    history = (
        df.groupby(df["timestamp"].dt.floor("min"))
        .size()
        .reset_index(name="vehicle_count")
        .sort_values("timestamp")
        .tail(periods)
        .reset_index(drop=True)
    )

    return history


def _build_prediction_history(db, camera_id: Optional[str], periods: int = 8):
    if camera_id:
        agg = get_recent_aggregations(db, camera_id=camera_id, n=periods)
        if len(agg) >= 3:
            return agg

    return _build_history_from_detections(db, camera_id, periods)


# ❌ KHÔNG lưu DB ở đây
def predict_next_density(db, camera_id: Optional[str] = None):
    history = _build_prediction_history(db, camera_id)
    predictor = _load_predictors()

    avg_density = (
        float(history["vehicle_count"].mean()) if not history.empty else 100.0
    )

    if predictor is not None and len(history) >= 5:
        predicted_value = float(predictor.predict(history))
        source = "ml_service"

        try:
            from backend.services.aggregation_service import compute_congestion
            congestion_level = compute_congestion(int(predicted_value))
        except:
            congestion_level = None
    else:
        predicted_value = avg_density
        source = "fallback"
        congestion_level = None

    return SimpleNamespace(
        camera_id=camera_id,
        predicted_density=predicted_value,
        predicted_congestion_level=congestion_level,
        horizon_minutes=settings.prediction_horizon_minutes,
        source=source,
        timestamp=datetime.utcnow(),
        avg_density=avg_density  # 👈 rất quan trọng
    )


# ✅ CHỈ lưu khi POST từ FE
def save_prediction(db, data):
    document = {
        "camera_id": data.camera_id,
        "predicted_density": data.predicted_density,
        "predicted_congestion_level": data.predicted_congestion_level,
        "horizon_minutes": data.horizon_minutes,
        "source": data.source,
        "timestamp": data.timestamp or datetime.utcnow(),
        "time_green_light": data.time_green_light,
    }

    result = db.traffic_predictions.insert_one(document)
    document["_id"] = result.inserted_id

    return to_object(document)


def list_predictions(db, camera_id=None, limit=20, offset=0):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    total = db.traffic_predictions.count_documents(filters)

    docs = (
        db.traffic_predictions.find(filters)
        .sort("timestamp", DESCENDING)
        .skip(offset)
        .limit(limit)
    )

    return total, [to_object(doc) for doc in docs]