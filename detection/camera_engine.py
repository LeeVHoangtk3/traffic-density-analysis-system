import cv2


class CameraEngine:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        # Cache FPS khi khởi tạo, fallback về 30 nếu không đọc được
        self._fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0

    def read(self):
        ret, frame = self.cap.read()
        return ret, frame

    def get_video_ms(self) -> float:
        """
        Trả về timestamp hiện tại trong video (milliseconds).
        Dùng cho counter.get_per_minute() và aggregation trigger
        để đồng bộ theo thời gian video thay vì thời gian thực.
        """
        return self.cap.get(cv2.CAP_PROP_POS_MSEC)

    def get_fps(self) -> float:
        """FPS gốc của video, dùng để tính display_delay trong main.py"""
        return self._fps

    def release(self):
        self.cap.release()