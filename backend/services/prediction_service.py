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
        from traffic_predictor import TrafficPredictor
        from light_delta_model import LightDeltaModel
    except Exception:
        return None, None

    model1_path = ml_service_dir / "model.pkl"
    predictor = TrafficPredictor(model_path=str(model1_path))
    if not predictor.load_model():
        predictor = None

    model2_path = ml_service_dir / "light_model.pkl"
    light_model = LightDeltaModel(model_path=str(model2_path))
    return predictor, light_model


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


def predict_next_density(
    db,
    camera_id: Optional[str] = None,
):
    history = _build_prediction_history(db, camera_id)
    predictor, light_model = _load_predictors()

    suggested_delta = 0.0

    if predictor is not None and len(history) >= 3:
        predicted_value = float(predictor.predict(history))
        source = "ml_service"

        if light_model is not None and len(history) >= 2:
            try:
                last_row = history.iloc[-1]
                prev_row = history.iloc[-2]
                current_features = pd.DataFrame(
                    [
                        {
                            "hour": last_row["timestamp"].hour,
                            "day_of_week": last_row["timestamp"].dayofweek,
                            "is_peak_hour": 1
                            if (
                                7 <= last_row["timestamp"].hour <= 9
                                or 17 <= last_row["timestamp"].hour <= 19
                            )
                            else 0,
                            "inbound_count": int(last_row["vehicle_count"]),
                            "queue_proxy": int(
                                last_row["vehicle_count"] - prev_row["vehicle_count"]
                            ),
                        }
                    ]
                )
                suggested_delta = float(light_model.predict_delta(current_features))
            except Exception as exc:
                print(f"Error predicting light delta: {exc}")
                suggested_delta = 0.0
    else:
        predicted_value = (
            float(history["vehicle_count"].mean()) if not history.empty else 0.0
        )
        source = "fallback"

    document = {
        "camera_id": camera_id,
        "predicted_density": predicted_value,
        "horizon_minutes": settings.prediction_horizon_minutes,
        "source": source,
        "suggested_delta": suggested_delta,
        "timestamp": datetime.utcnow(),
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
