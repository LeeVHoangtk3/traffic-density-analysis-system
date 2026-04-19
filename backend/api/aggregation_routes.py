"""
aggregation_routes.py
Hai endpoints:
  GET  /aggregation?vehicle_count=N  — tính mức tắc nghẽn từ số xe (cũ, giữ lại)
  POST /aggregation/compute?camera_id=CAM_01
       — gom dữ liệu từ vehicle_detections của 15 phút vừa qua,
         tính tổng xe, rồi ghi vào bảng traffic_aggregation.
         detection/main.py gọi endpoint này sau mỗi window 15 phút.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.services.aggregation_service import compute_congestion
from backend.services.db_service import get_db
from backend.models.vehicle_detection import VehicleDetection
from backend.models.traffic_aggregation import TrafficAggregation

router = APIRouter()


@router.get("/aggregation")
def get_aggregation(vehicle_count: int):
    """Tính mức tắc nghẽn từ số xe (endpoint cũ, giữ nguyên)."""
    level = compute_congestion(vehicle_count)
    return {"vehicle_count": vehicle_count, "congestion_level": level}


@router.post("/aggregation/compute")
def compute_aggregation(camera_id: str = "CAM_01", db: Session = Depends(get_db)):
    """
    Gom toàn bộ vehicle_detections của 15 phút vừa qua theo camera_id,
    đếm tổng số xe unique (theo track_id), rồi lưu vào traffic_aggregation.

    detection/main.py gọi endpoint này sau mỗi window 15 phút.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=15)

    # Đếm số track_id unique trong 15 phút vừa qua => số xe đã qua
    count_result = (
        db.query(func.count(func.distinct(VehicleDetection.track_id)))
        .filter(
            VehicleDetection.camera_id == camera_id,
            VehicleDetection.timestamp >= window_start,
            VehicleDetection.timestamp <= now,
        )
        .scalar()
    )
    vehicle_count = count_result or 0

    congestion_level = compute_congestion(vehicle_count)

    # Ghi vào traffic_aggregation
    record = TrafficAggregation(
        camera_id=camera_id,
        vehicle_count=vehicle_count,
        congestion_level=congestion_level,
        timestamp=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "camera_id": camera_id,
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "vehicle_count": vehicle_count,
        "congestion_level": congestion_level,
        "aggregation_id": record.id,
    }