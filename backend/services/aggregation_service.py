from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional

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
    Ngưỡng hiệu chỉnh cho thực tế đường đô thị Việt Nam (~400–500 xe/15 phút).
    """
    if vehicle_count < 200:
        return "Low"
    if vehicle_count < 350:
        return "Medium"
    if vehicle_count < 500:
        return "High"
    return "Severe"



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
    vehicle_count = db.vehicle_detections.count_documents(filters)

    inbound_filters = dict(filters)
    inbound_filters["direction"] = "inbound"
    inbound_count = db.vehicle_detections.count_documents(inbound_filters)

    previous_inbound = get_previous_inbound_count(
        db=db,
        camera_id=camera_id,
        before_time=end_time,
    )
    queue_proxy = inbound_count - previous_inbound
    congestion_level = compute_congestion(vehicle_count)

    document = {
        "camera_id": camera_id,
        "vehicle_count": vehicle_count,
        "inbound_count": inbound_count,
        "queue_proxy": queue_proxy,
        "congestion_level": congestion_level,
        "timestamp": end_time,
    }
    result = db.traffic_aggregation.insert_one(document)
    document["_id"] = result.inserted_id
    return to_object(document)


def compute_window_aggregation(
    db,
    camera_id: str,
    window_minutes: int = 15,
):
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    filters = _detection_window_filter(camera_id, window_start, now)
    track_ids = db.vehicle_detections.distinct("track_id", filters)
    vehicle_count = len(track_ids)

    inbound_filters = dict(filters)
    inbound_filters["direction"] = "inbound"
    inbound_track_ids = db.vehicle_detections.distinct("track_id", inbound_filters)
    inbound_count = len(inbound_track_ids)

    previous_inbound = get_previous_inbound_count(
        db=db,
        camera_id=camera_id,
        before_time=now,
    )
    queue_proxy = inbound_count - previous_inbound

    document = {
        "camera_id": camera_id,
        "vehicle_count": vehicle_count,
        "inbound_count": inbound_count,
        "queue_proxy": queue_proxy,
        "congestion_level": compute_congestion(vehicle_count),
        "timestamp": now,
    }
    result = db.traffic_aggregation.insert_one(document)
    document["_id"] = result.inserted_id
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
