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


def get_recent_aggregations(
    db,
    camera_id: str,
    n: int = 5,
) -> pd.DataFrame:
    rows = list(
        db.traffic_aggregation.find({"camera_id": camera_id})
        .sort("timestamp", DESCENDING)
        .limit(n)
    )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    df = pd.DataFrame(
        [
            {
                "timestamp": row["timestamp"],
                "vehicle_count": int(row.get("vehicle_count", 0)),
            }
            for row in rows
        ]
    )
    return df.sort_values("timestamp").reset_index(drop=True)


def _load_predictors():
    ml_service_dir = Path(__file__).resolve().parents[2] / "ml_service"
    if not ml_service_dir.exists():
        return None, None

    ml_service_path = str(ml_service_dir)
    if ml_service_path not in sys.path:
        sys.path.insert(0, ml_service_path)

    try:
        from traffic_predictor import TrafficPredictor, classify_congestion
    except Exception:
        return None

    model1_path = ml_service_dir / "model.pkl"
    predictor = TrafficPredictor(model_path=str(model1_path))
    if not predictor.load_model():
        predictor = None

    return predictor


def _build_history_from_detections(
    db,
    camera_id: Optional[str],
    periods: int,
) -> pd.DataFrame:
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
        .rename(columns={"timestamp": "timestamp"})
        .sort_values("timestamp")
        .tail(periods)
        .reset_index(drop=True)
    )
    return history


def _build_prediction_history(
    db,
    camera_id: Optional[str],
    periods: int = 8,
) -> pd.DataFrame:
    if camera_id:
        aggregation_history = get_recent_aggregations(db, camera_id=camera_id, n=periods)
        if len(aggregation_history) >= 3:
            return aggregation_history

    return _build_history_from_detections(db, camera_id, periods)


# =========================================================
# ✅ GREEN LIGHT TIME (MỚI THEO YÊU CẦU CỦA BẠN)
# =========================================================
def _compute_green_light_time(predicted_density: float, history: pd.DataFrame) -> int:
    base_time = 45

    if history.empty or predicted_density <= 0:
        return base_time

    avg_density = float(history["vehicle_count"].mean())

    if avg_density == 0:
        return base_time

    # % chênh lệch so với avg
    diff_ratio = (predicted_density - avg_density) / avg_density

    # mỗi 10% -> 5s
    steps = int(diff_ratio / 0.1)
    delta = steps * 5

    green_time = base_time + delta

    # clamp: không nhỏ hơn 30, không lớn hơn 45
    green_time = max(30, min(45, green_time))

    return int(green_time)


def predict_next_density(
    db,
    camera_id: Optional[str] = None,
):
    history = _build_prediction_history(db, camera_id)
    predictor = _load_predictors()

    if predictor is not None and len(history) >= 5:
        predicted_value = float(predictor.predict(history))
        source = "ml_service"
        try:
            from backend.services.aggregation_service import compute_congestion
            congestion_level = compute_congestion(int(predicted_value))
        except Exception as e:
            print(f"Error computing congestion: {e}")
            congestion_level = None

    else:
        predicted_value = (
            float(history["vehicle_count"].mean()) if not history.empty else 0.0
        )
        source = "fallback"
        congestion_level = None

    green_light_time = _compute_green_light_time(predicted_value, history)

    document = {
        "camera_id": camera_id,
        "predicted_density": predicted_value,
        "predicted_congestion_level": congestion_level,
        "horizon_minutes": settings.prediction_horizon_minutes,
        "source": source,
        "timestamp": datetime.utcnow(),
        "green_light_time": green_light_time,
    }

    result = db.traffic_predictions.insert_one(document)
    document["_id"] = result.inserted_id
    return to_object(document)


def list_predictions(
    db,
    camera_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    total = db.traffic_predictions.count_documents(filters)
    documents = (
        db.traffic_predictions.find(filters)
        .sort("timestamp", DESCENDING)
        .skip(offset)
        .limit(limit)
    )
    return total, [to_object(document) for document in documents]