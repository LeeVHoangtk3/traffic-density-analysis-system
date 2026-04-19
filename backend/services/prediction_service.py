"""
prediction_service.py
Đọc dữ liệu lịch sử xe từ bảng traffic_aggregation trong traffic.db,
rồi trả về DataFrame để TrafficPredictor.predict() có thể sử dụng ngay.
"""

import pandas as pd
from sqlalchemy.orm import Session
from backend.models.traffic_aggregation import TrafficAggregation


def get_recent_aggregations(db: Session, camera_id: str, n: int = 5) -> pd.DataFrame:
    """
    Truy vấn n bản ghi mới nhất trong bảng traffic_aggregation theo camera_id.

    Returns:
        DataFrame với 2 cột: timestamp (datetime), vehicle_count (int)
        Trả về DataFrame rỗng nếu không có dữ liệu.
    """
    rows = (
        db.query(TrafficAggregation)
        .filter(TrafficAggregation.camera_id == camera_id)
        .order_by(TrafficAggregation.timestamp.desc())
        .limit(n)
        .all()
    )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "vehicle_count"])

    # Sắp xếp lại theo thứ tự thời gian tăng dần (cũ → mới) để lag hoạt động đúng
    df = pd.DataFrame(
        [{"timestamp": r.timestamp, "vehicle_count": r.vehicle_count} for r in rows]
    )
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
