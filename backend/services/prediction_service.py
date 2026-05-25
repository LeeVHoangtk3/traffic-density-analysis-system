from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pandas as pd
from pymongo import DESCENDING  # type: ignore

from backend.config import settings
from backend.services.aggregation_service import (
    LANE_DIRECTIONS,
    classify_direction_counts,
    compute_overall_congestion,
)


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


def _load_single_predictor(model_path: Path):
    ml_service_dir = Path(__file__).resolve().parents[2] / "ml_service"
    if not ml_service_dir.exists():
        return None

    if str(ml_service_dir) not in sys.path:
        sys.path.insert(0, str(ml_service_dir))

    try:
        from traffic_predictor import TrafficPredictor  # type: ignore
    except Exception:
        return None

    predictor = TrafficPredictor(model_path=str(model_path))
    if not predictor.load_model():
        return None

    return predictor


def _load_direction_predictors() -> dict[str, object]:
    model_dir = Path(__file__).resolve().parents[2] / "ml_service" / "model"
    predictors = {}
    for direction in LANE_DIRECTIONS:
        predictor = _load_single_predictor(model_dir / f"model_{direction}.pkl")
        if predictor is not None:
            predictors[direction] = predictor
    return predictors


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
        .sort_values("timestamp")
        .tail(periods)
        .reset_index(drop=True)
    )

    return history


def _build_direction_history_from_aggregations(
    db,
    camera_id: str,
    direction: str,
    periods: int,
) -> pd.DataFrame:
    rows = list(
        db.traffic_aggregation.find({"camera_id": camera_id})
        .sort("timestamp", DESCENDING)
        .limit(periods)
    )
    data = []
    for row in rows:
        direction_counts = row.get("direction_counts") or {}
        data.append(
            {
                "timestamp": row["timestamp"],
                "vehicle_count": int(direction_counts.get(direction, 0)),
            }
        )

    if not data:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    return (
        pd.DataFrame(data)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def _build_direction_history_from_detections(
    db,
    camera_id: Optional[str],
    direction: str,
    periods: int,
) -> pd.DataFrame:
    filters = {"direction": direction}
    if camera_id:
        filters["camera_id"] = camera_id

    rows = list(
        db.vehicle_detections.find(filters, {"timestamp": 1, "track_id": 1})
        .sort("timestamp", DESCENDING)
        .limit(max(periods * 50, 100))
    )
    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    df = pd.DataFrame(
        [
            {
                "timestamp": row["timestamp"],
                "track_id": str(row.get("track_id", "")),
            }
            for row in rows
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    history = (
        df.groupby(df["timestamp"].dt.floor("15min"))["track_id"]
        .nunique()
        .reset_index(name="vehicle_count")
        .sort_values("timestamp")
        .tail(periods)
        .reset_index(drop=True)
    )
    return history


def _build_direction_history(
    db,
    camera_id: Optional[str],
    direction: str,
    periods: int = 8,
) -> pd.DataFrame:
    if camera_id:
        history = _build_direction_history_from_aggregations(
            db, camera_id, direction, periods
        )
        if len(history) >= 5 and history["vehicle_count"].sum() > 0:
            return history

    return _build_direction_history_from_detections(
        db, camera_id, direction, periods
    )


def _build_prediction_history(
    db,
    camera_id: Optional[str],
    periods: int = 8,
) -> pd.DataFrame:
    if camera_id:
        agg = get_recent_aggregations(db, camera_id=camera_id, n=periods)
        if len(agg) >= 3:
            return agg

    return _build_history_from_detections(db, camera_id, periods)


def _optimize_phase_timing(predictions: dict[str, int]) -> dict[str, int]:
    p1 = float(predictions.get("straight", 0)) + 0.3 * float(
        predictions.get("right", 0)
    )
    p2 = 1.5 * float(predictions.get("left", 0))

    if p1 + p2 <= 0:
        phase_1_green = 50
    else:
        raw_phase_1 = round((p1 / (p1 + p2)) * 80)
        phase_1_green = max(25, min(55, int(raw_phase_1)))

    phase_2_green = 80 - phase_1_green
    return {
        "phase_1_green": phase_1_green,
        "phase_2_green": phase_2_green,
        "delta_phase_1": phase_1_green - 50,
        "delta_phase_2": phase_2_green - 30,
    }


def predict_next_density(
    db,
    camera_id: Optional[str] = None,
):
    predictors = _load_direction_predictors()
    predictions: dict[str, int] = {}
    source_parts = []

    for direction in LANE_DIRECTIONS:
        history = _build_direction_history(db, camera_id, direction)
        predictor = predictors.get(direction)
        if predictor is not None and len(history) >= 5:
            try:
                predictions[direction] = int(predictor.predict(history))
                source_parts.append(f"{direction}:ml_service")
                continue
            except Exception as exc:
                print(f"Error predicting {direction}: {exc}")

        predictions[direction] = int(
            round(float(history["vehicle_count"].mean()))
        ) if not history.empty else 0
        source_parts.append(f"{direction}:fallback")

    if sum(predictions.values()) == 0:
        legacy_history = _build_prediction_history(db, camera_id)
        if not legacy_history.empty:
            predictions["straight"] = int(
                round(float(legacy_history["vehicle_count"].mean()))
            )
            source_parts.append("legacy:fallback")

    predicted_value = float(sum(predictions.values()))
    congestion_levels = classify_direction_counts(db, camera_id, predictions)
    congestion_level = compute_overall_congestion(congestion_levels)
    phase_timing = _optimize_phase_timing(predictions)
    green_light_time = phase_timing["phase_1_green"]
    source = ",".join(source_parts)

    document = {
        "camera_id": camera_id,
        "predicted_density": predicted_value,
        "predicted_congestion_level": congestion_level,
        "horizon_minutes": settings.prediction_horizon_minutes,
        "source": source,
        "timestamp": datetime.utcnow(),
        "green_light_time": green_light_time,
        "predictions": predictions,
        "congestion_levels": congestion_levels,
        "phase_timing": phase_timing,
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
<<<<<<< HEAD
    return total, [to_object(document) for document in docs]
=======
    return total, [to_object(document) for document in documents]
>>>>>>> origin/cuong
