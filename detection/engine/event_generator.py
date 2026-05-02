import uuid
from datetime import datetime, timezone


class EventGenerator:
    """
    Tạo event payload khi xe vượt zone.

    Thay đổi so với bản trước:
    ────────────────────────────────────────────────────────
    Thêm direction vào payload (kế hoạch camera 1 hướng):
    - generate() nhận thêm param direction: str
    - direction lấy từ zone_manager.check_crossing() — đọc
      trực tiếp từ zone config, không hardcode trong detection
    ────────────────────────────────────────────────────────
    """

    def generate(
        self,
        camera_id: str,
        track: dict,
        direction: str,
        density: str = "LOW",
    ) -> dict:
        """
        Args:
            camera_id:  ID camera (e.g. "CAM_01")
            track:      Dict từ Tracker: track_id, class_name, bbox, confidence
            direction:  Hướng xe từ zone config ("inbound" | "outbound")
            density:    Mật độ hiện tại từ DensityEstimator ("LOW"|"MEDIUM"|"HIGH")
        Returns:
            Event dict sẵn sàng gửi lên backend qua EventPublisher
        """
        return {
            "event_id":     str(uuid.uuid4()),
            "camera_id":    camera_id,
            "track_id":     track["track_id"],
            "vehicle_type": track["class_name"],
            "event_type":   "zone_entry",
            "direction":    direction,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "confidence":   round(float(track.get("confidence") or 0.0), 4),
        }