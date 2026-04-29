from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.traffic_aggregation import TrafficAggregation
from backend.models.traffic_prediction import TrafficPrediction
from backend.models.vehicle_detection import VehicleDetection

# --- HÀM HỖ TRỢ LẤY DỮ LIỆU ---

def get_recent_aggregations(
    db: Session,
    camera_id: str,
    n: int = 5,
) -> pd.DataFrame:
    rows = (
        db.query(TrafficAggregation)
        .filter(TrafficAggregation.camera_id == camera_id)
        .order_by(TrafficAggregation.timestamp.desc())
        .limit(n)
        .all()
    )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    df = pd.DataFrame(
        [{"timestamp": row.timestamp, "vehicle_count": row.vehicle_count} for row in rows]
    )
    return df.sort_values("timestamp").reset_index(drop=True)


# --- HÀM LOAD CÁC BỘ NÃO AI ---

def _load_predictors():
    """Load cả TrafficPredictor (Model 1) và LightDeltaModel (Model 2)"""
    ml_service_dir = Path(__file__).resolve().parents[2] / "ml_service"
    if not ml_service_dir.exists():
        return None, None

    ml_service_path = str(ml_service_dir)
    if ml_service_path not in sys.path:
        sys.path.insert(0, ml_service_path)

    try:
        from traffic_predictor import TrafficPredictor
        from light_delta_model import LightDeltaModel # Import Model 2 mới
    except Exception:
        return None, None

    # Load Model 1 (Dự báo xe)
    model1_path = ml_service_dir / "model.pkl"
    predictor = TrafficPredictor(model_path=str(model1_path))
    if not predictor.load_model():
        predictor = None

    # Load Model 2 (Điều khiển đèn)
    model2_path = ml_service_dir / "light_model.pkl"
    light_model = LightDeltaModel(model_path=str(model2_path))
    # Lưu ý: Class LightDeltaModel cần có hàm load_model hoặc logic tương tự
    # Nếu trong file light_delta_model.py chưa có load_model, bạn có thể bổ sung sau
    
    return predictor, light_model


def _build_prediction_history(
    db: Session,
    camera_id: Optional[str],
    periods: int = 8,
) -> pd.DataFrame:
    if camera_id:
        aggregation_history = get_recent_aggregations(db, camera_id=camera_id, n=periods)
        if len(aggregation_history) >= 3:
            return aggregation_history

    bucket = "%Y-%m-%d %H:%M:00"
    query = (
        db.query(
            func.strftime(bucket, VehicleDetection.timestamp).label("bucket_time"),
            func.count(VehicleDetection.id).label("vehicle_count"),
        )
        .group_by("bucket_time")
        .order_by("bucket_time desc")
        .limit(periods)
    )

    if camera_id:
        query = query.filter(VehicleDetection.camera_id == camera_id)

    rows = list(reversed(query.all()))
    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    return pd.DataFrame(
        [
            {
                "timestamp": pd.to_datetime(row.bucket_time),
                "vehicle_count": int(row.vehicle_count),
            }
            for row in rows
        ]
    )


# --- HÀM DỰ BÁO CHÍNH (TÍCH HỢP 2 MODEL) ---

def predict_next_density(
    db: Session,
    camera_id: Optional[str] = None,
) -> TrafficPrediction:
    history = _build_prediction_history(db, camera_id)
    predictor, light_model = _load_predictors()

    suggested_delta = 0.0 # Giá trị mặc định

    if predictor is not None and len(history) >= 3:
        # 1. Dự báo số lượng xe (Model 1)
        predicted_value = float(predictor.predict(history))
        source = "ml_service"

        # 2. Dự báo Delta Đèn (Model 2)
        if light_model is not None and len(history) >= 2:
            try:
                # Lấy 2 mốc gần nhất để tính Queue Proxy
                last_row = history.iloc[-1]
                prev_row = history.iloc[-2]
                
                # Chuẩn bị input cho Model 2
                current_features = pd.DataFrame([{
                    'hour': last_row['timestamp'].hour,
                    'day_of_week': last_row['timestamp'].dayofweek,
                    'is_peak_hour': 1 if (7 <= last_row['timestamp'].hour <= 9 or 17 <= last_row['timestamp'].hour <= 19) else 0,
                    'inbound_count': int(last_row['vehicle_count']),
                    'queue_proxy': int(last_row['vehicle_count'] - prev_row['vehicle_count'])
                }])
                
                # Gọi Model 2 dự báo số giây delta
                suggested_delta = float(light_model.predict_delta(current_features))
            except Exception as e:
                print(f"Error predicting light delta: {e}")
                suggested_delta = 0.0
    else:
        # Fallback khi không đủ dữ liệu hoặc thiếu model
        predicted_value = float(history["vehicle_count"].mean()) if not history.empty else 0.0
        source = "fallback"

    # Tạo object kết quả
    # Chú ý: Nếu bảng traffic_predictions của bạn chưa có cột suggested_delta, 
    # bạn cần thêm nó vào model SQLAlchemy TrafficPrediction trước.
    prediction = TrafficPrediction(
        camera_id=camera_id,
        predicted_density=predicted_value,
        horizon_minutes=settings.prediction_horizon_minutes,
        source=source,
        # suggested_delta=suggested_delta  # Bỏ comment dòng này sau khi đã cập nhật DB model
    )
    
    # Gán tạm vào object để API có thể trả về (dù có lưu DB hay không)
    prediction.suggested_delta = suggested_delta 

    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def list_predictions(
    db: Session,
    camera_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[TrafficPrediction]]:
    query = db.query(TrafficPrediction)
    if camera_id:
        query = query.filter(TrafficPrediction.camera_id == camera_id)

    total = query.count()
    items = (
        query.order_by(TrafficPrediction.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, items