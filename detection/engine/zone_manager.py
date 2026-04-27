import cv2
import time
import numpy as np
from collections import OrderedDict


class ZoneManager:
    """
    Quản lý polygon zone và đếm xe vượt zone.

    Thay đổi so với bản gốc:
    ─────────────────────────────────────────────────────────────────
    1. counted_ids lưu timestamp thay vì True
       → Biết chính xác xe vào zone lúc nào (phục vụ cooldown, debug)

    2. Thêm cooldown_seconds (mặc định 30s)
       → Nếu cùng track_id xuất hiện lại trong zone sau < 30s → KHÔNG đếm
       → Xử lý trường hợp xe dừng trong zone (đèn đỏ), ByteTrack
         re-assign ID cũ, tránh đếm trùng

    3. Eviction theo LRU (Least Recently Used) thay vì FIFO
       → Xóa track_id lâu nhất KHÔNG hoạt động, không phải cũ nhất về thời gian vào
       → Xe đang đứng yên trong zone sẽ không bị xóa sớm

    4. Thêm drop_count để theo dõi số lần eviction → debug memory pressure

    5. draw_zone() giữ nguyên interface, thêm tùy chọn màu theo zone index
    ─────────────────────────────────────────────────────────────────
    """

    # Màu phân biệt khi có nhiều zone
    ZONE_COLORS = [
        (255,   0, 255),   # magenta
        (  0, 255, 255),   # cyan
        (255, 165,   0),   # orange
        (  0, 255,   0),   # green
    ]

    def __init__(
        self,
        zones,
        max_history: int = 5000,
        cooldown_seconds: float = 30.0,
    ):
        """
        Args:
            zones:             List zone dicts, mỗi zone có key "points" (list of [x,y])
            max_history:       Số track_id tối đa lưu trong bộ nhớ
            cooldown_seconds:  Thời gian tối thiểu (giây) giữa 2 lần đếm cùng track_id
        """
        self.zones = zones
        self.max_history = max_history
        self.cooldown_seconds = cooldown_seconds

        # key: track_id  |  value: timestamp lần cuối được đếm (time.monotonic)
        self._last_counted: OrderedDict[int, float] = OrderedDict()

        # Thống kê
        self.drop_count = 0   # số lần evict do vượt max_history
        self.cooldown_blocked = 0  # số lần bị chặn do cooldown

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def check_crossing(self, track_id: int, cx: float, cy: float) -> bool:
        """
        Trả về True nếu xe (track_id) vượt zone VÀ đủ điều kiện được đếm.

        Điều kiện được đếm:
          - centroid (cx, cy) nằm trong ít nhất 1 polygon zone
          - track_id chưa được đếm, HOẶC đã quá cooldown_seconds kể từ lần đếm trước
        """
        point = (float(cx), float(cy))

        for zone in self.zones:
            polygon = np.array(zone["points"], np.int32)
            inside = cv2.pointPolygonTest(polygon, point, False)

            if inside >= 0:
                now = time.monotonic()
                last_ts = self._last_counted.get(track_id)

                # --- Cooldown check ---
                if last_ts is not None:
                    elapsed = now - last_ts
                    if elapsed < self.cooldown_seconds:
                        self.cooldown_blocked += 1
                        return False
                    # Hết cooldown: cho phép đếm lại (xe mới đi qua)
                    # Cập nhật vị trí trong OrderedDict (move_to_end = LRU update)
                    self._last_counted.move_to_end(track_id)
                    self._last_counted[track_id] = now
                    return True

                # --- Lần đầu tiên track_id này vào zone ---
                self._last_counted[track_id] = now
                self._evict_if_needed()
                return True

        return False

    def draw_zone(self, frame: np.ndarray) -> np.ndarray:
        """Vẽ tất cả polygon zones lên frame. Trả về frame đã vẽ."""
        for idx, zone in enumerate(self.zones):
            color = self.ZONE_COLORS[idx % len(self.ZONE_COLORS)]
            pts = np.array(zone["points"], np.int32)
            cv2.polylines(
                frame,
                [pts],
                isClosed=True,
                color=color,
                thickness=3,
            )
            # Label tên zone nếu có
            if "name" in zone:
                origin = tuple(pts[0])
                cv2.putText(
                    frame,
                    zone["name"],
                    origin,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                    cv2.LINE_AA,
                )
        return frame

    def stats(self) -> dict:
        """Trả về thống kê nội bộ để debug / monitor."""
        return {
            "tracked_ids_in_memory": len(self._last_counted),
            "max_history":           self.max_history,
            "cooldown_seconds":      self.cooldown_seconds,
            "evictions":             self.drop_count,
            "cooldown_blocked":      self.cooldown_blocked,
        }

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _evict_if_needed(self):
        """
        Xóa entry LRU (ít được dùng gần nhất) khi vượt max_history.
        OrderedDict giữ thứ tự insertion; move_to_end() dùng khi update
        → phần tử đầu tiên luôn là LRU.
        """
        while len(self._last_counted) > self.max_history:
            self._last_counted.popitem(last=False)  # xóa LRU
            self.drop_count += 1