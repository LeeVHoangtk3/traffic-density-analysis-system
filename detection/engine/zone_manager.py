import cv2
import numpy as np
from collections import OrderedDict

class ZoneManager:
    def __init__(self, zones, max_history=5000):
        self.zones = zones
        # Sử dụng OrderedDict thay vì set() để giới hạn kích thước lưu trữ
        self.counted_ids = OrderedDict()
        self.max_history = max_history

    def check_crossing(self, track_id, cx, cy):
        point = (float(cx), float(cy))

        for zone in self.zones:
            polygon = np.array(zone["points"], np.int32)
            inside = cv2.pointPolygonTest(polygon, point, False)

            if inside >= 0:
                if track_id not in self.counted_ids:
                    # Đánh dấu đã đếm
                    self.counted_ids[track_id] = True
                    
                    # Nếu danh sách vượt quá giới hạn, xóa ID cũ nhất (FIFO)
                    if len(self.counted_ids) > self.max_history:
                        self.counted_ids.popitem(last=False)
                        
                    return True
        return False

    def draw_zone(self, frame):
        for zone in self.zones:
            pts = np.array(zone["points"], np.int32)
            cv2.polylines(
                frame,
                [pts],
                isClosed=True,
                color=(255, 0, 255),
                thickness=3
            )