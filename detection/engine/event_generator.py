import uuid
from datetime import datetime, timezone


class EventGenerator:
    def generate(self, camera_id, track, density):
        return {
            "event_id": str(uuid.uuid4()),
            "camera_id": camera_id,
            "track_id": track["track_id"],
            "vehicle_type": track["class_name"],
            "density": density,
            "event_type": "line_crossing",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": round(float(track.get("confidence") or 0.0), 4),
        }
