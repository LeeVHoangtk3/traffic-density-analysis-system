import uuid
from datetime import datetime, timezone


class EventGenerator:
    """
    Tạo event payload khi xe vượt qua vùng ROI.
    - Hủy bỏ hoàn toàn tham số 'direction' bên ngoài do hệ thống đã đơn giản hóa sang một chiều đơn ROI.
    - Trường 'direction' bên trong JSON vẫn được thiết lập cố định là 'straight' để tương thích ngược 
      hoàn toàn với database index và các API tổng hợp cũ của Backend.
    """

    def generate(
        self,
        camera_id: str,
        track: dict,
        density: str = "LOW",
    ) -> dict:
        """
        Args:
            camera_id:  ID camera (e.g. "cam01")
            track:      Dict từ Tracker chứa: track_id, class_name, bbox, confidence
            density:    Mật độ giao thông hiện tại
        Returns:
            Event dict gửi lên Backend
        """
        return {
            "event_id":     str(uuid.uuid4()),
            "camera_id":    camera_id,
            "track_id":     track["track_id"],
            "vehicle_type": track["class_name"],
            "event_type":   "zone_entry",
            "direction":    "straight",  # Cố định luôn là straight để duy trì tính tương thích với DB
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "confidence":   round(float(track.get("confidence") or 0.0), 4),
        }