from collections import deque


class DensityEstimator:
    """
    Ước tính mật độ giao thông từ số track trong rolling window.

    Vai trò duy nhất: cung cấp tín hiệu real-time cho Dynamic Frame Skip
    trong main.py. KHÔNG dùng để gửi lên backend hay phục vụ ML.

    Tại sao GIỮ ở detection (không chuyển sang integration_system):
    ─────────────────────────────────────────────────────────────────
    - Frame skip phải phản ứng ngay trong vòng lặp detect (~ms latency)
    - Nếu gọi API integration để lấy density → latency 50-200ms
      → frame skip mất tính adaptive, đặc biệt nguy hiểm lúc spike

    Tại sao KHÔNG đưa density vào event payload gửi backend:
    ─────────────────────────────────────────────────────────────────
    - Density ở đây = snapshot local 1 camera, window ngắn (~1 giây)
    - Backend/aggregation_service tính congestion_level từ vehicle_count
      tổng hợp 15 phút → chính xác và ổn định hơn nhiều
    - Tránh 2 nguồn density khác nhau gây nhầm lẫn trong DB

    Thay đổi so với bản gốc:
    ─────────────────────────────────────────────────────────────────
    - window: 10 → 30 frame
      Với FRAME_SKIP=3, window=30 → trung bình ~90 frame thật (~3 giây)
      Đủ mượt để không giật HIGH↔LOW khi detector miss vài frame liên tiếp,
      nhưng vẫn đủ nhanh để phản ứng với thay đổi mật độ thực sự
    - Thêm get_raw_count() để main.py dùng cho spike detection
      thay vì phải tự đếm len(tracks) riêng
    """

    # Ngưỡng density — chỉ dùng nội bộ cho frame skip, không liên quan backend
    _THRESHOLDS = {
        "LOW":    5,
        "MEDIUM": 15,
    }

    def __init__(self, window: int = 30):
        self._window = deque(maxlen=window)

    def update(self, tracks: list) -> None:
        self._window.append(len(tracks))

    def get_density(self) -> str:
        """Trả về LOW / MEDIUM / HIGH dùng cho frame skip."""
        if not self._window:
            return "LOW"
        avg = sum(self._window) / len(self._window)
        if avg < self._THRESHOLDS["LOW"]:
            return "LOW"
        elif avg < self._THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        return "HIGH"

    def get_avg_count(self) -> float:
        """Số xe trung bình trong window — dùng cho spike detection ở main.py."""
        if not self._window:
            return 0.0
        return sum(self._window) / len(self._window)

    def get_last_count(self) -> int:
        """Số xe ở frame gần nhất — dùng để so sánh spike."""
        return self._window[-1] if self._window else 0