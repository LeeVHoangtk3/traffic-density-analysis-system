from collections import defaultdict


class VehicleCounter:
    def __init__(self):
        self.total_counts = defaultdict(int)
        self.minute_counts = defaultdict(int)
        # Đổi từ time.time() sang video timestamp (ms) để đúng với video file
        # start_time cũ bị sai khi máy xử lý nhanh/chậm hơn thực tế
        self._start_ms = None

    def count(self, class_name: str) -> None:
        self.total_counts[class_name] += 1
        self.minute_counts[class_name] += 1

    def get_totals(self) -> dict:
        return dict(self.total_counts)

    def get_per_minute(self, video_ms: float) -> dict | None:
        """
        Đếm theo thời gian trong video, không phải thời gian thực.
        video_ms: lấy từ camera.get_video_ms() (CAP_PROP_POS_MSEC)
        Return dict nếu đủ 60 giây video, None nếu chưa đủ.
        """
        # Lần đầu gọi: khởi tạo mốc
        if self._start_ms is None:
            self._start_ms = video_ms
            return None

        if video_ms - self._start_ms >= 60_000:
            data = dict(self.minute_counts)
            self.minute_counts.clear()
            self._start_ms = video_ms  # reset mốc
            return data

        return None