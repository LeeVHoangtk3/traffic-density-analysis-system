import uuid
from datetime import datetime, timezone


class EventGenerator:
    """
    Tạo event payload khi xe vượt zone.

    Thay đổi so với bản gốc:
    ────────────────────────────────────────────────────────
    1. Bỏ density khỏi param và payload
    2. confidence có fallback 0.0, round 4 chữ số
    3. event_type đổi "line_crossing" → "zone_crossing"
    ────────────────────────────────────────────────────────
    """

    def generate(self, camera_id: str, track: dict) -> dict:
        return {
            "event_id":     str(uuid.uuid4()),
            "camera_id":    camera_id,
            "track_id":     track["track_id"],
            "vehicle_type": track["class_name"],
            "event_type":   "zone_crossing",
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "confidence":   round(float(track.get("confidence") or 0.0), 4),
        }
