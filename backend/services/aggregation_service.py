from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional

# pyrefly: ignore [missing-import]
from pymongo import DESCENDING


def to_object(document):
    if not document:
        return None
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return SimpleNamespace(**document)


def compute_congestion(vehicle_count: int) -> str:
    """
    Phân loại mức độ mật độ giao thông.
    Ngưỡng được hiệu chỉnh cho dataset đô thị NYC (~50-100 xe/15p).
    """
    if vehicle_count < 30:
        return "Low"
    if vehicle_count < 100:
        return "Medium"
    if vehicle_count < 200:
        return "High"
    return "Heavy"


def get_thresholds(db, camera_id: Optional[str]) -> dict | None:
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    document = db.directional_thresholds.find_one(filters)
    if document:
        return document.get("thresholds")

    if camera_id:
        document = db.directional_thresholds.find_one({"camera_id": None})
        if document:
            return document.get("thresholds")

    return None


def classify_count(
    db,
    camera_id: Optional[str],
    vehicle_count: int,
) -> str:
    thresholds = get_thresholds(db, camera_id)
    if thresholds:
        low_to_medium = float(thresholds.get("low_to_medium", 0))
        medium_to_high = float(thresholds.get("medium_to_high", 0))
        high_to_heavy = float(thresholds.get("high_to_heavy", 0))
        if vehicle_count < low_to_medium:
            return "Low"
        if vehicle_count < medium_to_high:
            return "Medium"
        if vehicle_count < high_to_heavy:
            return "High"
        return "Heavy"

    return compute_congestion(vehicle_count)




def get_previous_inbound_count(
    db,
    camera_id: Optional[str],
    before_time: datetime,
) -> int:
    filters = {"timestamp": {"$lt": before_time}}
    if camera_id:
        filters["camera_id"] = camera_id
    else:
        filters["camera_id"] = None

    previous = db.traffic_aggregation.find_one(
        filters,
        sort=[("timestamp", DESCENDING)],
    )
    return int(previous.get("inbound_count", 0)) if previous else 0


def _detection_window_filter(
    camera_id: Optional[str],
    start_time: datetime,
    end_time: datetime,
) -> dict:
    filters = {
        "timestamp": {
            "$gte": start_time,
            "$lte": end_time,
        }
    }
    if camera_id:
        filters["camera_id"] = camera_id
    return filters


def aggregate_from_detections(
    db,
    camera_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    end_time = end_time or datetime.utcnow()
    start_time = start_time or (end_time - timedelta(minutes=15))

    filters = _detection_window_filter(camera_id, start_time, end_time)
    
    vehicle_count = len(db.vehicle_detections.distinct("track_id", filters))
    if vehicle_count == 0:
        vehicle_count = db.vehicle_detections.count_documents(filters)

    inbound_count = vehicle_count

    previous_inbound = get_previous_inbound_count(
        db=db,
        camera_id=camera_id,
        before_time=end_time,
    )
    queue_proxy = inbound_count - previous_inbound
    congestion_level = classify_count(db, camera_id, vehicle_count)

    document = {
        "camera_id": camera_id,
        "vehicle_count": vehicle_count,
        "inbound_count": inbound_count,
        "queue_proxy": queue_proxy,
        "congestion_level": congestion_level,
        "timestamp": end_time,
    }
    # GET /aggregation chỉ đọc dữ liệu trực quan thời gian thực, tuyệt đối không INSERT vào database
    # để tránh gây rác dữ liệu (đặc biệt khi polling 5s/lần)
    document["_id"] = "live_aggregation"
    return to_object(document)


def compute_window_aggregation(
    db,
    camera_id: str,
    window_minutes: int = 15,
):
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    filters = _detection_window_filter(camera_id, window_start, now)
    
    vehicle_count = len(db.vehicle_detections.distinct("track_id", filters))
    if vehicle_count == 0:
        vehicle_count = db.vehicle_detections.count_documents(filters)

    inbound_count = vehicle_count

    previous_inbound = get_previous_inbound_count(
        db=db,
        camera_id=camera_id,
        before_time=now,
    )
    queue_proxy = inbound_count - previous_inbound

    congestion_level = classify_count(db, camera_id, vehicle_count)
    document = {
        "camera_id": camera_id,
        "vehicle_count": vehicle_count,
        "inbound_count": inbound_count,
        "queue_proxy": queue_proxy,
        "congestion_level": congestion_level,
        "timestamp": now,
    }
    # Chỉ lưu lịch sử (insert_one) vào database khi phần detection đang thực sự chạy và có xe (vehicle_count > 0)
    # tránh khởi tạo hàng loạt giá trị 0 gây rác lịch sử khi khởi động hệ thống chưa chạy video/detection.
    if vehicle_count > 0:
        result = db.traffic_aggregation.insert_one(document)
        document["_id"] = result.inserted_id
    else:
        document["_id"] = "temp_aggregation"
        
    return to_object(document), window_start


def list_aggregations(
    db,
    camera_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    filters = {}
    if camera_id:
        filters["camera_id"] = camera_id

    total = db.traffic_aggregation.count_documents(filters)
    documents = (
        db.traffic_aggregation.find(filters)
        .sort("timestamp", DESCENDING)
        .skip(offset)
        .limit(limit)
    )
    return total, [to_object(document) for document in documents]
