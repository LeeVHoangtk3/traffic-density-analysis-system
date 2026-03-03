import cv2

class ZoneManager:
    def __init__(self, line_y, x_start, x_end, offset=5):
        self.line_y = line_y
        self.x_start = x_start
        self.x_end = x_end
        self.offset = offset
        self.crossed_ids = set()

    def check_crossing(self, track_id, cx, cy):
        # Kiểm tra trong phạm vi ngang trước
        if not (self.x_start <= cx <= self.x_end):
            return False

        if abs(cy - self.line_y) < self.offset and track_id not in self.crossed_ids:
            self.crossed_ids.add(track_id)
            return True

        return False

    def draw_zone(self, frame):
        cv2.line(frame,
                 (self.x_start, self.line_y),
                 (self.x_end, self.line_y),
                 (0, 0, 255),
                 3)