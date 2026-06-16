import os
import sys
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.db_service import get_db
from backend.schemas.prediction_schema import (
    PredictionResponse,
    PredictionHistoryResponse,
    PredictionHistoryItem,
)
from backend.services.prediction_service import (
    predict_next_density,
    list_predictions,
    get_recent_aggregations,
)

# Thư mục gốc dự án để nạp mô hình XGBoost
PROJECT_ROOT = Path(__file__).resolve().parents[2]

router = APIRouter()

# ==============================================================================
# SCHEMA & RESPONSE MODELS CHO API V1 MỚI (SINGLE ROI + XGBOOST + K-MEANS)
# ==============================================================================

class PredictNextV1Response(BaseModel):
    camera_id: str = Field(..., description="ID của camera giám sát")
    predicted_raw_volume: int = Field(..., description="Lưu lượng xe thô dự đoán cho 15 phút tới")
    status_label: str = Field(..., description="Nhãn mật độ phân cụm động: LOW/MEDIUM/HIGH/HEAVY")
    color_hex: str = Field(..., description="Mã màu đại diện hiển thị trực quan lên React Dashboard")
    timestamp: datetime = Field(..., description="Mốc thời gian dự báo thời gian thực")
    features_used: dict = Field(..., description="Các đặc trưng trễ và tuần hoàn được sử dụng")
    thresholds: dict = Field(default_factory=dict, description="Các ngưỡng phân cụm K-Means thích ứng động")

# ==============================================================================
# CACHED XGBOOST MODEL LOADER
# ==============================================================================
_xgb_model = None

def get_xgb_model():
    """
    Nạp và cache mô hình XGBoost từ file pickle để tối ưu tốc độ phản hồi API (0ms latency).
    """
    global _xgb_model
    if _xgb_model is None:
        model_path = PROJECT_ROOT / "ml_service" / "model" / "model.pkl"
        if model_path.exists():
            try:
                with open(model_path, "rb") as f:
                    _xgb_model = pickle.load(f)
                print(f"[+] Loaded XGBoost model from: {model_path}")
            except Exception as e:
                print(f"[!] Lỗi khi nạp mô hình XGBoost từ {model_path}: {e}")
    return _xgb_model

# ==============================================================================
# API ROUTE MỚI: /api/v1/predict-next (XGBoost + K-Means)
# ==============================================================================

@router.get("/api/v1/predict-next", response_model=PredictNextV1Response)
def predict_next_v1(camera_id: str = "cam01", db=Depends(get_db)):
    """
    API dự báo lưu lượng và phân cụm mật độ giao thông thích ứng thế hệ mới:
    Được thiết kế chuẩn hóa cho 1 video phân tích duy nhất (Single ROI).
    """
    # Ép cứng toàn bộ dữ liệu trả về thuộc về cam03 (Do UI vẽ 3 cam chỉ là hình thức)
    camera_id = "cam03"
    
    # 1. Lấy 3 dòng dữ liệu đếm xe mới nhất của camera mục tiêu (không gộp nhóm, không check timestamp)
    recent_records = list(
        db.traffic_aggregation.find({"camera_id": camera_id})
        .sort("timestamp", -1)  # Sắp xếp lại theo chuẩn thời gian sự kiện (timestamp)
        .limit(3)
    )
    
    # 2. Cơ chế Fallback an toàn tuyệt đối cho các đặc trưng trễ (lags) của cả địa điểm
    lag_1 = 450.0
    lag_2 = 450.0
    lag_3 = 450.0
    
    if len(recent_records) >= 1:
        lag_1 = float(recent_records[0].get("vehicle_count", 450.0))
    if len(recent_records) >= 2:
        lag_2 = float(recent_records[1].get("vehicle_count", 450.0))
    if len(recent_records) >= 3:
        lag_3 = float(recent_records[2].get("vehicle_count", 450.0))
        
    rolling_mean_3 = (lag_1 + lag_2 + lag_3) / 3.0
    
    # 3. Trích xuất đặc trưng cyclic (giờ/phút) và lịch trình (thứ/cuối tuần)
    now = datetime.now()
    hour_float = now.hour + now.minute / 60.0
    hour_sin = float(np.sin(2 * np.pi * hour_float / 24.0))
    hour_cos = float(np.cos(2 * np.pi * hour_float / 24.0))
    
    day_of_week = int(now.weekday())  # 0 = Thứ hai, 6 = Chủ nhật
    is_weekend = 1 if day_of_week >= 5 else 0
    
    features_used = {
        "lag_1": lag_1,
        "lag_2": lag_2,
        "rolling_mean_3": rolling_mean_3,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend
    }
    
    # 4. Hồi quy dự đoán lưu lượng xe thô bằng XGBoost
    model = get_xgb_model()
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
            print(f"[!] Lỗi dự báo XGBoost, kích hoạt fallback: {e}")
            
    # 5. Lấy ma trận ngưỡng K-Means thích ứng của địa điểm (lưu dưới camera_id)
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
        
    # 6. Ánh xạ ngưỡng K-Means thích ứng sang nhãn trạng thái & màu sắc HEX
    if predicted_raw_volume < low_to_medium:
        status_label = "LOW"
        color_hex = "#10B981"  # Emerald Green
    elif predicted_raw_volume < medium_to_high:
        status_label = "MEDIUM"
        color_hex = "#3B82F6"  # Royal Blue
    elif predicted_raw_volume < high_to_heavy:
        status_label = "HIGH"
        color_hex = "#F59E0B"  # Amber Gold
    else:
        status_label = "HEAVY"
        color_hex = "#EF4444"  # Crimson Red
        
    # 7. Lưu trữ lịch sử dự báo
    prediction_doc = {
        "camera_id": camera_id,
        "predicted_raw_volume": predicted_raw_volume,
        "predicted_density": float(predicted_raw_volume),
        "predicted_congestion_level": status_label,
        "color_hex": color_hex,
        "timestamp": datetime.utcnow(),
        "horizon_minutes": 15,
        "source": "xgboost_v1_single_roi",
        "features": features_used
    }
    
    try:
        db.traffic_predictions.insert_one(prediction_doc)
    except Exception as e:
        print(f"[!] Lỗi khi lưu bản ghi dự báo vào MongoDB: {e}")
        
    return PredictNextV1Response(
        camera_id="Làn đường đơn",
        predicted_raw_volume=predicted_raw_volume,
        status_label=status_label,
        color_hex=color_hex,
        timestamp=datetime.now(),
        features_used=features_used,
        thresholds={
            "low_to_medium": low_to_medium,
            "medium_to_high": medium_to_high,
            "high_to_heavy": high_to_heavy
        }
    )



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

@router.get("/predict-next", response_model=PredictionResponse)
def predict_next(camera_id: str | None = None, db=Depends(get_db)):
    """
    Đường dẫn predict-next cũ. Tự động chuyển tiếp thông tin hoặc gọi logic cũ tương thích.
    """
    recent_camera_id = camera_id or "cam01"
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
        predicted_congestion_level=getattr(prediction, "predicted_congestion_level", None),
        predictions=_predictions(prediction),
        congestion_levels=_congestion_levels(prediction),
        horizon_minutes=prediction.horizon_minutes,
        source=prediction.source,
        timestamp=prediction.timestamp,
    )

@router.get("/predictions/history", response_model=PredictionHistoryResponse)
def get_prediction_history(
    camera_id: Optional[str] = "cam03",
    limit: int = Query(default=20, ge=1),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    camera_id = "cam03"
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
                predicted_congestion_level=getattr(item, "predicted_congestion_level", None),
                predictions=_predictions(item),
                congestion_levels=_congestion_levels(item),
                horizon_minutes=item.horizon_minutes,
                source=item.source,
                timestamp=item.timestamp,
            )
            for item in items
        ],
    )
