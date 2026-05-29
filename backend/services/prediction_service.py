from __future__ import annotations

import os
import sys
import pickle
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pandas as pd
from pymongo import DESCENDING

from backend.config import settings

# Thư mục gốc dự án để nạp mô hình XGBoost
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Biến toàn cục để cache mô hình XGBoost
_xgb_model_cached = None

def get_cached_model():
    """
    Nạp và cache mô hình XGBoost từ file model.pkl.
    """
    global _xgb_model_cached
    if _xgb_model_cached is None:
        model_paths = [
            PROJECT_ROOT / "ml_service" / "model.pkl",
            PROJECT_ROOT / "ml_service" / "model" / "model.pkl"
        ]
        for path in model_paths:
            if path.exists():
                try:
                    with open(path, "rb") as f:
                        _xgb_model_cached = pickle.load(f)
                    break
                except Exception as e:
                    print(f"[PredictionService] Lỗi khi nạp mô hình XGBoost từ {path}: {e}")
    return _xgb_model_cached


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


def _optimize_phase_timing(predicted_volume: int) -> dict[str, int]:
    """
    Tối ưu hóa nhịp đèn tín hiệu an toàn dựa trên tổng lưu lượng đếm đơn ROI:
    - Phase 1 (Đoạn đường chính): Tăng thời gian đèn xanh nếu lưu lượng đông, giảm nếu vắng.
    - Tổng chu kỳ đèn xanh là 80 giây.
    """
    # Ngưỡng trung bình để chia tỉ lệ nhịp đèn
    if predicted_volume <= 0:
        phase_1_green = 50
    else:
        # Tỉ lệ đèn xanh tăng dần theo mức độ đông đúc (Min 25 giây, Max 55 giây cho Phase 1)
        raw_phase_1 = 25 + (min(predicted_volume, 600) / 600.0) * 30
        phase_1_green = max(25, min(55, int(round(raw_phase_1))))

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
    """
    Dự báo lưu lượng xe và phân cụm mật độ thế hệ mới, loại bỏ hoàn toàn hướng đi.
    Hoàn toàn tương thích ngược cho cả route cũ và route mới.
    """
    camera_id = camera_id or "cam01"
    
    # 1. Lấy dữ liệu thực đo từ MongoDB
    recent_records = list(
        db.traffic_aggregation.find({"camera_id": camera_id})
        .sort("timestamp", -1)
        .limit(3)
    )
    
    # 2. Xử lý đặc trưng trễ với fallback cực kỳ an toàn
    lag_1 = 50.0
    lag_2 = 50.0
    lag_3 = 50.0
    
    if len(recent_records) >= 1:
        lag_1 = float(recent_records[0].get("vehicle_count", 50.0))
    if len(recent_records) >= 2:
        lag_2 = float(recent_records[1].get("vehicle_count", 50.0))
    if len(recent_records) >= 3:
        lag_3 = float(recent_records[2].get("vehicle_count", 50.0))
        
    rolling_mean_3 = (lag_1 + lag_2 + lag_3) / 3.0
    
    # 3. Tính toán đặc trưng thời gian thực
    now = datetime.now()
    hour_float = now.hour + now.minute / 60.0
    hour_sin = float(np.sin(2 * np.pi * hour_float / 24.0))
    hour_cos = float(np.cos(2 * np.pi * hour_float / 24.0))
    
    day_of_week = int(now.weekday())
    is_weekend = 1 if day_of_week >= 5 else 0
    
    # 4. Thực hiện dự báo bằng XGBoost
    model = get_cached_model()
    if model is None:
        predicted_raw_volume = int(round(rolling_mean_3))
    else:
        try:
            X_pred = pd.DataFrame([[
                lag_1, lag_2, rolling_mean_3, hour_sin, hour_cos, day_of_week, is_weekend
            ]], columns=['lag_1', 'lag_2', 'rolling_mean_3', 'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend'])
            
            raw_pred = model.predict(X_pred)[0]
            predicted_raw_volume = int(round(max(0.0, float(raw_pred))))
        except Exception as e:
            predicted_raw_volume = int(round(rolling_mean_3))
            print(f"[PredictionService] Lỗi dự báo XGBoost: {e}")
            
    # 5. Lấy ngưỡng thích ứng phân cụm từ MongoDB
    low_to_medium = 467.58
    medium_to_high = 495.34
    high_to_heavy = 522.67
    
    threshold_doc = db.density_thresholds.find_one({"camera_id": camera_id})
    if not threshold_doc:
        threshold_doc = db.directional_thresholds.find_one({"camera_id": camera_id, "direction": "total"})
        
    if threshold_doc and "thresholds" in threshold_doc:
        thresholds = threshold_doc["thresholds"]
        low_to_medium = float(thresholds.get("low_to_medium", low_to_medium))
        medium_to_high = float(thresholds.get("medium_to_high", medium_to_high))
        high_to_heavy = float(thresholds.get("high_to_heavy", high_to_heavy))
        
    # Phân loại mật độ giao thông tổng thể
    if predicted_raw_volume < low_to_medium:
        congestion_level = "LOW"
    elif predicted_raw_volume < medium_to_high:
        congestion_level = "MEDIUM"
    elif predicted_raw_volume < high_to_heavy:
        congestion_level = "HIGH"
    else:
        congestion_level = "HEAVY"
        
    # 6. Tối ưu hóa nhịp đèn tín hiệu giao thông
    phase_timing = _optimize_phase_timing(predicted_raw_volume)
    green_light_time = phase_timing["phase_1_green"]
    
    # 7. Xây dựng cấu trúc dữ liệu tương thích ngược cho cả left, straight, right
    # (Để 'straight' đại diện cho toàn bộ lưu lượng đếm đơn ROI, left/right = 0)
    predictions_dict = {
        "left": 0,
        "straight": predicted_raw_volume,
        "right": 0
    }
    congestion_levels_dict = {
        "left": "LOW",
        "straight": congestion_level,
        "right": "LOW"
    }

    document = {
        "camera_id": camera_id,
        "predicted_density": float(predicted_raw_volume),
        "predicted_congestion_level": congestion_level,
        "horizon_minutes": settings.prediction_horizon_minutes,
        "source": "xgb_single_roi_directionless",
        "timestamp": datetime.utcnow(),
        "green_light_time": green_light_time,
        "predictions": predictions_dict,
        "congestion_levels": congestion_levels_dict,
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
    return total, [to_object(document) for document in docs]
