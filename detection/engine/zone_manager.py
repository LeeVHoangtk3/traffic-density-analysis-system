import cv2
import time
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from shapely.geometry import Point, Polygon


class ZoneManager:
    """
    Quản lý 4 vùng ROI đa giác và kiểm soát hướng di chuyển của xe (State Machine - Chiều đi lên/ra xa).
    - Sử dụng thư viện Shapely để kiểm tra quan hệ hình học chính xác (Point in Polygon).
    - Quy trình ĐẢO NGƯỢC: Xe xuất phát chạm vào vùng `zone_trigger` trước (đóng vai trò Start Zone), 
      sau đó di chuyển lên phía xa chạm vào các vùng làn khác (đóng vai trò Exit/End Zones) mới được tính là hợp lệ.
    """

    ZONE_COLORS = [
        (255,   0, 255),   # hồng cánh sen (Làn Trái)
        (  0, 255, 255),   # cyan (Làn Giữa)
        (255, 165,   0),   # cam (Làn Phải)
        (  0, 255,   0),   # xanh lá
    ]

    def __init__(
        self,
        zones: List[Dict[str, Any]],
        max_history: int = 5000,
        cooldown_seconds: float = 30.0,
    ):
        self.max_history      = max_history
        self.cooldown_seconds = cooldown_seconds

        # Tách biệt trigger zone và validator zones từ camera config
        self.validators: List[Tuple[Polygon, str, np.ndarray]] = []
        self.roi_trigger: Optional[Polygon] = None
        self.roi_trigger_pts: Optional[np.ndarray] = None

        for zone in zones:
            pts = np.array(zone["points"], np.int32)
            poly = Polygon(zone["points"])
            
            if zone.get("is_trigger") or zone.get("direction") == "trigger":
                self.roi_trigger = poly
                self.roi_trigger_pts = pts
            else:
                direction = zone.get("direction", "straight")
                self.validators.append((poly, direction, pts))

        # Fallback an toàn nếu cấu hình thiếu trigger zone
        if self.roi_trigger is None:
            print("[ZoneManager] WARNING: Không tìm thấy Trigger Zone trong cấu hình. Sử dụng mặc định.")
            fallback_pts = [[0, 380], [0, 460], [960, 460], [960, 380]]
            self.roi_trigger = Polygon(fallback_pts)
            self.roi_trigger_pts = np.array(fallback_pts, np.int32)

        # Bộ nhớ trạng thái (State Machine): track_id -> dict
        self.memory_traffic: Dict[int, Dict[str, Any]] = {}
        
        # Thống kê hiệu suất
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
        Cập nhật trạng thái của track đang hoạt động trong khung hình.
        Liên tục theo dõi và ghi nhận phân làn quyết định cuối cùng mà phương tiện đi qua.
        """
        point = Point(float(cx), float(cy))

        # Khởi tạo trạng thái mới nếu xe lần đầu xuất hiện
        if track_id not in self.memory_traffic:
            self.memory_traffic[track_id] = {
                "passed_trigger": False,      # Đã đi qua Trigger Zone xuất phát
                "last_zone": None,            # Làn quyết định cuối cùng chạm phải
                "track": track_dict,          # Cache thông tin track để phục vụ đếm khi thoát
                "is_counted": False,          # Trạng thái đã đếm
                "discarded": False,           # Trạng thái bị loại bỏ vì đi vào validator không qua Trigger
                "last_counted": 0.0
            }

        state = self.memory_traffic[track_id]
        
        # Cập nhật thông tin track mới nhất (tọa độ, confidence...)
        state["track"] = track_dict

        # Nếu xe đã đếm hoặc đã bị loại bỏ từ trước, bỏ qua
        if state["is_counted"] or state["discarded"]:
            return

        # BƯỚC 1: Kiểm tra xe chạm vào Trigger Zone cận cảnh trước
        if not state["passed_trigger"]:
            if self.roi_trigger.contains(point):
                state["passed_trigger"] = True
                print(f"[ZoneManager] Track ID {track_id} registered at TRIGGER zone (Start).")
                return

        # BƯỚC 2: Kiểm tra khi xe chạm vào các Validator Lanes tiếp theo (Exit/End Zones)
        for validator_poly, lane_name, _ in self.validators:
            if validator_poly.contains(point):
                # Nếu xe ĐÃ có lịch sử đi qua Trigger hợp lệ
                if state["passed_trigger"]:
                    # Liên tục cập nhật làn cuối cùng chạm phải (không chốt ngay lập tức)
                    if state["last_zone"] != lane_name:
                        state["last_zone"] = lane_name
                        print(f"[ZoneManager] Track ID {track_id} updated active lane to: {lane_name}")
                else:
                    # Xe nhảy thẳng vào Validator Lane mà không có lịch sử qua Trigger -> Loại bỏ!
                    state["discarded"] = True
                    self.discarded_count += 1
                    print(f"[ZoneManager] Track ID {track_id} DISCARDED (Direct entry to lane without passing trigger).")
                    return

    def draw_zone(self, frame: np.ndarray) -> np.ndarray:
        """Vẽ toàn bộ các validator và trigger zone lên frame hình OpenCV."""
        # 1. Vẽ Trigger Zone (Màu đỏ chói để đánh dấu chốt chặn xuất phát)
        if self.roi_trigger_pts is not None:
            cv2.polylines(frame, [self.roi_trigger_pts], isClosed=True, color=(0, 0, 255), thickness=2)
            cv2.putText(
                frame, "TRIGGER ZONE (Xuất phát)", (self.roi_trigger_pts[0][0] + 10, self.roi_trigger_pts[0][1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA
            )

        # 2. Vẽ các Validator Lanes (Màu sắc phân biệt)
        for idx, (poly, name, pts) in enumerate(self.validators):
            color = self.ZONE_COLORS[idx % len(self.ZONE_COLORS)]
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
            
            # Viết label làn để giám sát trực quan
            label = f"DECIDING ZONE: {name}"
            origin = tuple(pts[0])
            cv2.putText(
                frame, label, (origin[0], origin[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA
            )

        return frame

    def cleanup_memory(self, active_track_ids: List[int]) -> List[Tuple[int, str, Dict[str, Any]]]:
        """
        Dọn dẹp bộ nhớ RAM và xác định các xe đã đi ra ngoài khung hình (exit).
        Trả về danh sách các sự kiện đếm xe hợp lệ: (track_id, final_lane_name, cached_track_dict)
        """
        exited_events: List[Tuple[int, str, Dict[str, Any]]] = []
        
        expired_ids = [tid for tid in self.memory_traffic if tid not in active_track_ids]
        for tid in expired_ids:
            state = self.memory_traffic[tid]
            
            # Nếu xe qua Trigger hợp lệ và đã chạm ít nhất 1 làn quyết định trước khi thoát
            if state["passed_trigger"] and state["last_zone"] is not None and not state["is_counted"]:
                state["is_counted"] = True
                exited_events.append((tid, state["last_zone"], state["track"]))
                print(f"[ZoneManager] Track ID {tid} COUNTED ON EXIT! Final direction: {state['last_zone']} (Trigger -> {state['last_zone']})")
                
            # Xóa sạch khỏi bộ nhớ RAM để tránh rò rỉ bộ nhớ
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