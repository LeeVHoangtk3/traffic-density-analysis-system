"""
integration_system/delta_applier.py
====================================
Áp dụng delta dự đoán từ LightDeltaModel vào baseline_green của camera
để tính thời gian đèn xanh cuối cùng (giây).

Workflow:
    1. Nhận: camera_id, queue_proxy, inbound_count,
             congestion_level, hour, dow (day_of_week)
    2. Tra baseline_green của camera từ CAMERA_BASELINE
    3. Gọi LightDeltaModel.predict_delta()  (clamp đã thực hiện bên trong model)
    4. Clamp thêm một lần ở lớp này: delta = max(-30, min(+45, delta))
    5. Tính: green_time = baseline_green + delta
    6. Trả về: green_time (giây, float)
"""

import sys
import os

# ---------------------------------------------------------------------------
# Đảm bảo có thể import ml_service từ bất kỳ thư mục làm việc nào
# ---------------------------------------------------------------------------
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ml_service.light_delta_model import LightDeltaModel  # noqa: E402

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------

# Thời gian đèn xanh baseline (giây) cho từng camera
# → Chỉnh theo cấu hình thực tế của hệ thống
CAMERA_BASELINE: dict[str, int] = {
    "CAM_01": 30,
    "CAM_02": 25,
    "CAM_03": 35,
    "CAM_04": 40,
}

# Giới hạn clamp delta (giây)
_DELTA_MIN: float = -30.0
_DELTA_MAX: float = +45.0

# ---------------------------------------------------------------------------
# Singleton model — chỉ load model .pkl một lần trong suốt vòng đời process
# ---------------------------------------------------------------------------
_model_instance: LightDeltaModel | None = None


def _get_model() -> LightDeltaModel:
    """Trả về LightDeltaModel singleton (lazy-load)."""
    global _model_instance
    if _model_instance is None:
        _model_instance = LightDeltaModel()
    return _model_instance


# ---------------------------------------------------------------------------
# API chính
# ---------------------------------------------------------------------------

def apply_delta(
    camera_id: str,
    queue_proxy: float,
    inbound_count: int,
    congestion_level: str,
    hour: int,
    dow: int,
) -> float:
    """
    Tính thời gian đèn xanh cuối cùng bằng cách cộng delta dự đoán vào baseline.

    Tham số
    -------
    camera_id       : ID camera (ví dụ: "CAM_01")
    queue_proxy     : Ước tính chiều dài hàng đợi (xe)
    inbound_count   : Số xe vào giao lộ trong chu kỳ
    congestion_level: Mức tắc nghẽn ('low' | 'medium' | 'high')
    hour            : Giờ trong ngày (0–23)
    dow             : Day-of-week (0=Thứ Hai … 6=Chủ Nhật)

    Trả về
    ------
    float
        Thời gian đèn xanh cuối cùng (giây). Không âm (min = 0).

    Raises
    ------
    KeyError
        Nếu camera_id không có trong bảng CAMERA_BASELINE.
    """
    # 1. Lấy baseline theo camera_id
    if camera_id not in CAMERA_BASELINE:
        raise KeyError(
            f"[DeltaApplier] Camera '{camera_id}' not found in CAMERA_BASELINE. "
            f"Valid cameras: {list(CAMERA_BASELINE.keys())}"
        )
    baseline_green: int = CAMERA_BASELINE[camera_id]

    # 2. Gọi model dự đoán delta
    feature_dict = {
        "queue_proxy":      queue_proxy,
        "inbound_count":    inbound_count,
        "congestion_level": congestion_level,
        "baseline_green":   baseline_green,
        "hour":             hour,
        "day_of_week":      dow,
    }
    raw_delta: float = _get_model().predict_delta(feature_dict)

    # 3. Clamp delta (lop applier - bao ve kep)
    delta: float = max(_DELTA_MIN, min(_DELTA_MAX, raw_delta))

    # 4. Tinh green_time cuoi cung (khong de am)
    green_time: float = max(0.0, baseline_green + delta)

    print(
        f"[DeltaApplier] {camera_id} | baseline={baseline_green}s "
        f"delta={delta:+.2f}s -> green_time={green_time:.1f}s"
    )
    return green_time


# ---------------------------------------------------------------------------
# Chạy thử nhanh: python -m integration_system.delta_applier
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        ("CAM_01", 18.0, 60, "high",   8, 1),
        ("CAM_02",  2.0, 10, "low",   14, 5),
        ("CAM_03", -5.0, 20, "medium",22, 6),
        ("CAM_04", 25.0, 80, "high",   7, 0),
    ]

    print("=" * 55)
    print("  DeltaApplier --- Demo")
    print("=" * 55)
    for args in test_cases:
        cam_id, qp, ic, cl, hr, dw = args
        try:
            gt = apply_delta(cam_id, qp, ic, cl, hr, dw)
            print(f"  -> green_time = {gt:.1f}s\n")
        except Exception as exc:
            print(f"  [ERROR] {exc}\n")
    print("=" * 55)
