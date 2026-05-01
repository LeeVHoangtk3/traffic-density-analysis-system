import cv2


class CameraEngine:
    """
    Wrapper VideoCapture cho video file hoặc camera thật.

    Thay đổi so với bản gốc:
    ────────────────────────────────────────────────────────
    1. Thêm guard kiểm tra VideoCapture mở thành công
       → Raise rõ ràng thay vì crash ngầm ở frame đầu tiên

    2. Thêm reset() method
       → main.py cũ gọi camera.reset() — nay implement đúng
       → Không dùng trực tiếp camera.cap từ bên ngoài

    3. Thêm is_opened() helper
       → Cho phép main.py kiểm tra trạng thái trước khi vào loop
    ────────────────────────────────────────────────────────
    """

    def __init__(self, source):
        self.source = source
        self.cap    = cv2.VideoCapture(source)

        if not self.cap.isOpened():
            raise RuntimeError(f"[CameraEngine] Không mở được source: {source}")

        self._fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0

    def read(self):
        return self.cap.read()

    def get_video_ms(self) -> float:
        """Timestamp hiện tại trong video (milliseconds). Dùng cho per-minute counter."""
        return self.cap.get(cv2.CAP_PROP_POS_MSEC)

    def get_fps(self) -> float:
        return self._fps

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def reset(self):
        """Rewind về frame đầu. Chỉ hoạt động với video file, không hoạt động với camera thật."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def release(self):
        self.cap.release()