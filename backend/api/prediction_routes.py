"""
prediction_routes.py
GET /predict-next?camera_id=CAM_01
  - Đọc dữ liệu lịch sử thực từ traffic_aggregation (thay vì hard-code 0.45)
  - Gọi TrafficPredictor.predict() để cho ra số xe dự báo 15 phút tới
  - Lưu kết quả vào bảng traffic_predictions
  - Trả về JSON { camera_id, predicted_count, predicted_at }
"""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.db_service import get_db
from backend.services.prediction_service import get_recent_aggregations
from backend.models.traffic_prediction import TrafficPrediction

# Import TrafficPredictor từ ml_service
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ml_service.traffic_predictor import TrafficPredictor

router = APIRouter()

# Khởi tạo predictor một lần duy nhất (load model.pkl)
_MODEL_PATH = os.path.join(_ROOT, "ml_service", "model.pkl")
_predictor = TrafficPredictor(model_path=_MODEL_PATH)
_predictor.load_model()


@router.get("/predict-next")
def predict_next(camera_id: str = "CAM_01", db: Session = Depends(get_db)):
    """
    Dự báo số lượng xe cho 15 phút tiếp theo dựa trên dữ liệu thực trong DB.
    """
    # 1. Lấy dữ liệu lịch sử thực từ traffic_aggregation
    history_df = get_recent_aggregations(db, camera_id=camera_id, n=5)

    if len(history_df) < 3:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Không đủ dữ liệu lịch sử cho camera '{camera_id}'. "
                f"Cần ít nhất 3 bản ghi trong traffic_aggregation, "
                f"hiện chỉ có {len(history_df)}. "
                "Hãy chạy detection/ trước để tích lũy dữ liệu."
            ),
        )

    # 2. Gọi TrafficPredictor để dự báo
    predicted_count = _predictor.predict(history_df)

    # 3. Lưu kết quả vào bảng traffic_predictions
    record = TrafficPrediction(
        predicted_density=float(predicted_count),
        timestamp=datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    return {
        "camera_id": camera_id,
        "predicted_count": predicted_count,
        "predicted_at": record.timestamp.isoformat(),
    }