"""
integration_system/traffic_light_logic.py
==========================================
Bộ điều phối đèn tín hiệu — kết hợp:
  • Phân loại tắc nghẽn (fallback rule-based)
  • Dự đoán delta qua ML (LightDeltaModel, thông qua DeltaApplier)
  • Ánh xạ camera → pha đèn (DirectionRouter)

API công khai
-------------
TrafficLightOptimizer.optimize(congestion_level)
    → dict {"green_time": int}          # Chế độ fallback rule-based (giữ
                                         # tương thích với system_runner.py cũ)

TrafficLightOptimizer.optimize_with_ml(
    camera_id, queue_proxy, inbound_count,
    congestion_level, hour, dow
)
    → dict {
        "camera_id"    : str,
        "phase"        : str,   # pha đèn ("north_green", ...)
        "direction"    : str,   # "inbound" | "outbound"
        "green_time"   : float, # giây, đã áp delta ML
        "baseline"     : int,   # baseline_green của camera
        "delta"        : float, # delta được áp (đã clamp)
        "mode"         : "ml",
      }
"""

from __future__ import annotations

import sys
import os

# ---------------------------------------------------------------------------
# Đảm bảo import được module trong cùng package
# ---------------------------------------------------------------------------
_INTEGRATION_DIR = os.path.dirname(os.path.abspath(__file__))
if _INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, _INTEGRATION_DIR)

_ROOT = os.path.abspath(os.path.join(_INTEGRATION_DIR, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Import có điều kiện — tránh crash nếu ml_service chưa cài
try:
    from delta_applier import apply_delta, CAMERA_BASELINE      # noqa: E402
    from direction_router import get_phase                       # noqa: E402
    _ML_AVAILABLE = True
except Exception as _ml_err:                                    # noqa: BLE001
    _ML_AVAILABLE = False
    _ml_err_msg = str(_ml_err)


# ---------------------------------------------------------------------------
# Hằng số rule-based (fallback)
# ---------------------------------------------------------------------------
_RULE_MAP: dict[str, int] = {
    "low":    20,
    "medium": 40,
    "high":   60,
}
_RULE_DEFAULT: int = 90   # "severe" hoặc không rõ


# ---------------------------------------------------------------------------
# Lớp chính
# ---------------------------------------------------------------------------

class TrafficLightOptimizer:
    """
    Điều phối thời gian đèn xanh cho giao lộ thông minh.

    Có hai chế độ vận hành:
    1. **Rule-based** (optimize): tương thích ngược với code cũ.
    2. **ML-based** (optimize_with_ml): dùng LightDeltaModel + DeltaApplier.
    """

    # ------------------------------------------------------------------
    # Chế độ 1 — Rule-based (giữ nguyên hành vi cũ)
    # ------------------------------------------------------------------

    def optimize(self, congestion_level: str) -> dict:
        """
        Trả về green_time theo rule cứng dựa trên mức tắc nghẽn.

        Tương thích ngược với system_runner.py và các consumer hiện tại.

        Tham số
        -------
        congestion_level : str  ('low' | 'medium' | 'high' | 'severe')

        Trả về
        ------
        dict  {"green_time": int, "mode": "rule"}
        """
        normalized = str(congestion_level).strip().lower()
        green_time = _RULE_MAP.get(normalized, _RULE_DEFAULT)
        return {"green_time": green_time, "mode": "rule"}

    # ------------------------------------------------------------------
    # Chế độ 2 — ML-based (mới)
    # ------------------------------------------------------------------

    def optimize_with_ml(
        self,
        camera_id: str,
        queue_proxy: float,
        inbound_count: int,
        congestion_level: str,
        hour: int,
        dow: int,
    ) -> dict:
        """
        Tính green_time bằng ML delta model kết hợp với direction router.

        Tham số
        -------
        camera_id        : ID camera (ví dụ "CAM_01")
        queue_proxy      : Ước tính chiều dài hàng đợi (xe)
        inbound_count    : Số xe vào giao lộ trong chu kỳ
        congestion_level : 'low' | 'medium' | 'high'
        hour             : Giờ trong ngày (0–23)
        dow              : Day-of-week (0=Thứ Hai … 6=Chủ Nhật)

        Trả về
        ------
        dict
            {
              "camera_id"  : str,
              "phase"      : str,    # pha đèn (e.g. "north_green")
              "direction"  : str,    # "inbound" | "outbound"
              "green_time" : float,  # thời gian đèn xanh cuối (giây)
              "baseline"   : int,    # baseline_green của camera
              "delta"      : float,  # delta thực sự đã áp
              "mode"       : "ml" | "rule_fallback",
            }

        Notes
        -----
        Nếu ML không khả dụng (import lỗi), tự động fallback về rule-based
        và ghi cảnh báo vào stdout.
        """
        if not _ML_AVAILABLE:
            print(
                f"[TrafficLightOptimizer] ⚠ ML không khả dụng ({_ml_err_msg}). "
                "Chuyển về rule-based."
            )
            rule_result = self.optimize(congestion_level)
            return {
                "camera_id":  camera_id,
                "phase":      "unknown",
                "direction":  "unknown",
                "green_time": float(rule_result["green_time"]),
                "baseline":   rule_result["green_time"],
                "delta":      0.0,
                "mode":       "rule_fallback",
            }

        try:
            # 1. Lấy thông tin pha từ direction router
            phase_info = get_phase(camera_id)
            phase      = phase_info["phase"]
            direction  = phase_info["direction"]

            # 2. Lấy baseline để tính delta ngược
            baseline = CAMERA_BASELINE.get(camera_id, 30)

            # 3. Gọi delta applier — xử lý predict + clamp + tính green_time
            green_time = apply_delta(
                camera_id=camera_id,
                queue_proxy=queue_proxy,
                inbound_count=inbound_count,
                congestion_level=congestion_level,
                hour=hour,
                dow=dow,
            )

            delta = round(green_time - baseline, 2)

            return {
                "camera_id":  camera_id,
                "phase":      phase,
                "direction":  direction,
                "green_time": round(green_time, 2),
                "baseline":   baseline,
                "delta":      delta,
                "mode":       "ml",
            }

        except Exception as exc:                                # noqa: BLE001
            print(f"[TrafficLightOptimizer] ⚠ Lỗi ML ({exc}). Fallback rule-based.")
            rule_result = self.optimize(congestion_level)
            return {
                "camera_id":  camera_id,
                "phase":      "unknown",
                "direction":  "unknown",
                "green_time": float(rule_result["green_time"]),
                "baseline":   rule_result["green_time"],
                "delta":      0.0,
                "mode":       "rule_fallback",
            }


# ---------------------------------------------------------------------------
# Chạy thử nhanh: python -m integration_system.traffic_light_logic
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    optimizer = TrafficLightOptimizer()

    print("=" * 60)
    print("  TrafficLightOptimizer — Demo")
    print("=" * 60)

    # --- Chế độ rule-based (tương thích ngược) ---
    print("\n[Rule-based]")
    for level in ("low", "medium", "high", "severe"):
        result = optimizer.optimize(level)
        print(f"  congestion='{level}' → {result}")

    # --- Chế độ ML-based ---
    print("\n[ML-based]")
    ml_cases = [
        ("CAM_01", 18.0, 60, "high",    8, 1),
        ("CAM_02",  2.0, 10, "low",    14, 5),
        ("CAM_03", -5.0, 20, "medium", 22, 6),
    ]
    for cam, qp, ic, cl, hr, dw in ml_cases:
        res = optimizer.optimize_with_ml(cam, qp, ic, cl, hr, dw)
        print(
            f"  {cam} | phase='{res['phase']}' | dir='{res['direction']}' "
            f"| green={res['green_time']}s | delta={res['delta']:+.2f}s "
            f"| mode='{res['mode']}'"
        )

    print("=" * 60)
