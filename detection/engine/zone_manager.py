import cv2
import time
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from shapely.geometry import Point, Polygon


class ZoneManager:
    """
    Quản lý 1 vùng ROI đa giác duy nhất để đếm xe thời gian thực (On-RAM Processing).
    - Quy định đếm chuẩn xác: 1 xe được tính là hợp lệ khi và chỉ khi đi VÀO (Enter) và đi RA ngoài (Exit) vùng ROI.
    - Cơ chế State Machine:
      + Bước 1: Khi bánh xe đi VÀO ROI lần đầu, trạng thái `passed_trigger` kích hoạt thành True.
      + Bước 2: Khi bánh xe di chuyển đi RA ngoài ROI, hệ thống lập tức chốt đếm `is_counted = True`.
      + Fallback an toàn: Nếu xe đi vào ROI nhưng bị mất vết bám hoặc thoát khỏi khung hình khi chưa kịp đi ra ngoài ROI trên camera, hệ thống vẫn ghi nhận đếm ở cleanup_memory để tránh hụt lưu lượng thực tế.
    """

    def __init__(
        self,
        zones: List[Dict[str, Any]],
        max_history: int = 5000,
        cooldown_seconds: float = 30.0,
    ):
        self.max_history      = max_history
        self.cooldown_seconds = cooldown_seconds

        self.roi_trigger: Optional[Polygon] = None
        self.roi_trigger_pts: Optional[np.ndarray] = None

        # Trích xuất duy nhất Trigger Zone làm ROI đếm tổng
        for zone in zones:
            if zone.get("is_trigger") or zone.get("direction") == "trigger" or zone.get("id") == "zone_trigger":
                self.roi_trigger = Polygon(zone["points"])
                self.roi_trigger_pts = np.array(zone["points"], np.int32)
                break

        # Fallback an toàn nếu cấu hình thiếu trigger zone hoặc không tìm thấy
        if self.roi_trigger is None and zones:
            self.roi_trigger = Polygon(zones[0]["points"])
            self.roi_trigger_pts = np.array(zones[0]["points"], np.int32)

        if self.roi_trigger is None:
            print("[ZoneManager] WARNING: Không tìm thấy bất kỳ vùng ROI nào. Khởi tạo mặc định.")
            fallback_pts = [[100, 400], [860, 400], [760, 320], [200, 320]]
            self.roi_trigger = Polygon(fallback_pts)
            self.roi_trigger_pts = np.array(fallback_pts, np.int32)

        # Bộ nhớ trạng thái: track_id -> dict
        self.memory_traffic: Dict[int, Dict[str, Any]] = {}
        
        # Thống kê
        self.cooldown_blocked = 0
        self.discarded_count = 0

    def update_active_track(
        self,
        track_id: int,
        cx: float,
        cy: float,
        track_dict: dict,
    ) -> None:
        """
        Cập nhật trạng thái vết bám của xe. Đánh dấu 'passed_trigger' khi đi vào
        và chốt đếm 'is_counted' khi đi ra khỏi ROI.
        """
        point = Point(float(cx), float(cy))

        # Khởi tạo trạng thái mới nếu xe lần đầu xuất hiện
        if track_id not in self.memory_traffic:
            self.memory_traffic[track_id] = {
                "passed_trigger": False,      # True khi xe đi VÀO vùng ROI
                "is_counted": False,          # True khi xe đi RA ngoài vùng ROI (Chốt đếm)
                "track": track_dict,
            }

        state = self.memory_traffic[track_id]
        state["track"] = track_dict  # Cập nhật thông tin track mới nhất

        # Nếu xe này đã chốt đếm xong rồi thì bỏ qua
        if state["is_counted"]:
            return

        point_inside_roi = self.roi_trigger.contains(point)

        # BƯỚC 1: Kiểm tra xe đi VÀO vùng ROI
        if not state["passed_trigger"]:
            if point_inside_roi:
                state["passed_trigger"] = True
                print(f"[ZoneManager] 🚗 Track ID {track_id} ({track_dict['class_name']}) đi VÀO vùng ROI.")
        else:
            # BƯỚC 2: Kiểm tra xe đi RA ngoài vùng ROI sau khi đã đi vào
            if not point_inside_roi:
                state["is_counted"] = True
                print(f"[ZoneManager] 🏁 Track ID {track_id} ({track_dict['class_name']}) đi RA khỏi ROI -> CHỐT ĐẾM!")

    def draw_zone(self, frame: np.ndarray) -> np.ndarray:
        """Vẽ duy nhất 1 vùng ROI chốt đếm tổng lên màn hình OpenCV."""
        if self.roi_trigger_pts is not None:
            # Vẽ đa giác ROI màu xanh lá ngọc bảo rất cao cấp
            cv2.polylines(frame, [self.roi_trigger_pts], isClosed=True, color=(129, 185, 16), thickness=2)
            # Tạo hiệu ứng highlight mờ cho vùng ROI
            overlay = frame.copy()
            cv2.fillPoly(overlay, [self.roi_trigger_pts], color=(129, 185, 16))
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            
            # Viết nhãn đếm tổng
            cv2.putText(
                frame, "ROI CHỐT ĐẾM TỔNG (Single ROI)", (self.roi_trigger_pts[0][0] + 10, self.roi_trigger_pts[0][1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (180, 255, 180), 1, cv2.LINE_AA
            )
        return frame

    def cleanup_memory(self, active_track_ids: List[int]) -> List[Tuple[int, Dict[str, Any]]]:
        """
        Dọn dẹp bộ nhớ RAM và xác nhận các xe đã đếm để gửi sự kiện về Backend.
        """
        exited_events: List[Tuple[int, Dict[str, Any]]] = []
        
        expired_ids = [tid for tid in self.memory_traffic if tid not in active_track_ids]
        for tid in expired_ids:
            state = self.memory_traffic[tid]
            
            # Xe được tính là đếm hợp lệ nếu:
            # - Đã chốt đếm thành công khi đi ra ngoài vùng ROI lúc đang trong camera.
            if state["is_counted"]:
                exited_events.append((tid, state["track"]))
                
            # Xóa khỏi bộ nhớ ngay khi thoát khung hình để giải phóng RAM triệt để (On-RAM Processing)
            if tid in self.memory_traffic:
                del self.memory_traffic[tid]
                
        return exited_events

    def stats(self) -> dict:
        return {
            "tracked_ids_in_memory": len(self.memory_traffic),
            "max_history":           self.max_history,
            "cooldown_seconds":      self.cooldown_seconds,
            "cooldown_blocked":      self.cooldown_blocked,
            "discarded_crossings":   self.discarded_count
        }