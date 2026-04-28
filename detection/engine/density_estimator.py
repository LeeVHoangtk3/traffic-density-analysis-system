from collections import deque


class DensityEstimator:
    def __init__(self, window: int = 10):
        # Rolling window: trung bình 10 lần update gần nhất
        # Với FRAME_SKIP=3 → tương đương ~30 frame thật (~1 giây ở 30fps)
        self._window = deque(maxlen=window)

    def update(self, tracks: list) -> None:
        self._window.append(len(tracks))

    def get_density(self) -> str:
        if not self._window:
            return "LOW"
        avg = sum(self._window) / len(self._window)
        if avg < 5:
            return "LOW"
        elif avg < 15:
            return "MEDIUM"
        return "HIGH"