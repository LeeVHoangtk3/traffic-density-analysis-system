from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional

from pymongo import DESCENDING

LANE_DIRECTIONS = ("left", "straight", "right")
LEGACY_INBOUND_DIRECTIONS = ("inbound", "straight", "left", "right")


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
    return "Heavy"


def empty_direction_counts() -> dict[str, int]:
    return {direction: 0 for direction in LANE_DIRECTIONS}


def get_direction_thresholds(db, camera_id: Optional[str], direction: str) -> dict | None:
    filters = {"direction": direction}
    if camera_id:
        filters["camera_id"] = camera_id

    document = db.directional_thresholds.find_one(filters)
    if document:
        return document.get("thresholds")

    if camera_id:
        document = db.directional_thresholds.find_one(
            {"camera_id": None, "direction": direction}
        )
        if document:
            return document.get("thresholds")

    return None


def classify_direction_count(
    db,
    camera_id: Optional[str],
    direction: str,
    vehicle_count: int,
) -> str:
    thresholds = get_direction_thresholds(db, camera_id, direction)
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


def classify_direction_counts(
    db,
    camera_id: Optional[str],
    direction_counts: dict[str, int],
) -> dict[str, str]:
    return {
        direction: classify_direction_count(
            db=db,
            camera_id=camera_id,
            direction=direction,
            vehicle_count=count,
        )
        for direction, count in direction_counts.items()
    }


def compute_overall_congestion(congestion_levels: dict[str, str]) -> str:
    rank = {"Low": 0, "Medium": 1, "High": 2, "Heavy": 3, "Severe": 3}
    if not congestion_levels:
        return "Low"
    return max(congestion_levels.values(), key=lambda level: rank.get(level, 0))


def count_distinct_tracks_by_direction(db, filters: dict) -> dict[str, int]:
    counts = empty_direction_counts()
    for direction in LANE_DIRECTIONS:
        direction_filters = dict(filters)
        direction_filters["direction"] = direction
        counts[direction] = len(
            db.vehicle_detections.distinct("track_id", direction_filters)
        )
    return counts



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
    direction_counts = count_distinct_tracks_by_direction(db, filters)
    vehicle_count = sum(direction_counts.values())
    if vehicle_count == 0:
        vehicle_count = db.vehicle_detections.count_documents(filters)
        direction_counts["straight"] = vehicle_count

    inbound_filters = dict(filters)
    inbound_filters["direction"] = {"$in": LEGACY_INBOUND_DIRECTIONS}
    inbound_track_ids = db.vehicle_detections.distinct("track_id", inbound_filters)
    inbound_count = len(inbound_track_ids)

    previous_inbound = get_previous_inbound_count(
        db=db,
        camera_id=camera_id,
        before_time=end_time,
    )
    queue_proxy = inbound_count - previous_inbound
    congestion_levels = classify_direction_counts(db, camera_id, direction_counts)
    congestion_level = compute_overall_congestion(congestion_levels)

    document = {
        "camera_id": camera_id,
        "vehicle_count": vehicle_count,
        "inbound_count": inbound_count,
        "queue_proxy": queue_proxy,
        "congestion_level": congestion_level,
        "direction_counts": direction_counts,
        "congestion_levels": congestion_levels,
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
    direction_counts = count_distinct_tracks_by_direction(db, filters)
    vehicle_count = sum(direction_counts.values())
    if vehicle_count == 0:
        track_ids = db.vehicle_detections.distinct("track_id", filters)
        vehicle_count = len(track_ids)
        direction_counts["straight"] = vehicle_count

    inbound_filters = dict(filters)
    inbound_filters["direction"] = {"$in": LEGACY_INBOUND_DIRECTIONS}
    inbound_track_ids = db.vehicle_detections.distinct("track_id", inbound_filters)
    inbound_count = len(inbound_track_ids)

    previous_inbound = get_previous_inbound_count(
        db=db,
        camera_id=camera_id,
        before_time=now,
    )
    queue_proxy = inbound_count - previous_inbound

    congestion_levels = classify_direction_counts(db, camera_id, direction_counts)
    document = {
        "camera_id": camera_id,
        "vehicle_count": vehicle_count,
        "inbound_count": inbound_count,
        "queue_proxy": queue_proxy,
        "congestion_level": compute_overall_congestion(congestion_levels),
        "direction_counts": direction_counts,
        "congestion_levels": congestion_levels,
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
