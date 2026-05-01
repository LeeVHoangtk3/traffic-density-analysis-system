import cv2
import time
import numpy as np
from collections import OrderedDict


class ZoneManager:
    """
    Quản lý polygon zone và đếm xe vượt zone.

    Thay đổi so với bản trước:
    ─────────────────────────────────────────────────────────────────
    Thêm direction support (kế hoạch camera 1 hướng):
    - check_crossing() trả về Optional[str] thay vì bool
      → None  = không crossing (hoặc bị cooldown chặn)
      → "inbound" / "outbound" = crossing hợp lệ, kèm direction của zone đó
    - draw_zone() hiển thị label direction trên frame để debug
    - Zone config cần có field "direction": "inbound" | "outbound"
    ─────────────────────────────────────────────────────────────────
    """

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
        self.zones            = zones
        self.max_history      = max_history
        self.cooldown_seconds = cooldown_seconds

        self._last_counted: OrderedDict[int, float] = OrderedDict()

        self.drop_count       = 0
        self.cooldown_blocked = 0

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def check_crossing(
        self,
        track_id: int,
        cx: float,
        cy: float,
    ) -> str | None:
        """
        Kiểm tra xe có vượt zone không.

        Returns:
            str  — direction của zone ("inbound" | "outbound") nếu crossing hợp lệ
            None — nếu không trong zone, hoặc bị cooldown chặn

        Cách dùng trong main.py:
            direction = zone_manager.check_crossing(track_id, cx, cy_bottom)
            if direction:
                event = event_generator.generate(..., direction=direction)
        """
        point = (float(cx), float(cy))

        for zone in self.zones:
            polygon = np.array(zone["points"], np.int32)
            inside  = cv2.pointPolygonTest(polygon, point, False)

            if inside >= 0:
                now     = time.monotonic()
                last_ts = self._last_counted.get(track_id)

                if last_ts is not None:
                    if now - last_ts < self.cooldown_seconds:
                        self.cooldown_blocked += 1
                        return None
                    self._last_counted.move_to_end(track_id)

                self._last_counted[track_id] = now
                self._evict_if_needed()

                # Trả về direction của zone — fallback "inbound" nếu không có field
                return zone.get("direction", "inbound")

        return None

    def draw_zone(self, frame: np.ndarray) -> np.ndarray:
        """Vẽ polygon zones lên frame, hiển thị direction label để debug."""
        for idx, zone in enumerate(self.zones):
            color = self.ZONE_COLORS[idx % len(self.ZONE_COLORS)]
            pts   = np.array(zone["points"], np.int32)

            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3)

            # Label: ưu tiên "direction", fallback sang "name", fallback sang index
            label  = zone.get("direction") or zone.get("name") or f"zone_{idx}"
            origin = tuple(pts[0])
            cv2.putText(
                frame, label, origin,
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA,
            )

        return frame

    def stats(self) -> dict:
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
        while len(self._last_counted) > self.max_history:
            self._last_counted.popitem(last=False)
            self.drop_count += 1