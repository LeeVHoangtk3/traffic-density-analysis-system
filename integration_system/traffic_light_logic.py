"""
integration_system/traffic_light_logic.py
==========================================
Bộ điều phối đèn tín hiệu — kết hợp:
  • Phân loại tắc nghẽn (fallback rule-based)
  • Dự đoán delta qua ML (LightDeltaModel, thông qua DeltaApplier)
  • Ánh xạ camera → pha đèn (DirectionRouter)
"""

import sys
import os

# Ensure we can import from the root
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_INTEGRATION_DIR = os.path.dirname(os.path.abspath(__file__))
if _INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, _INTEGRATION_DIR)

from delta_applier import apply, CAMERA_BASELINE
from direction_router import get_phase

# Hardcoded mapping as fallback (requested by user)
_FALLBACK_MAP = {
    "low": 20,
    "medium": 40,
    "high": 60,
    "severe": 90
}

class TrafficLightOptimizer:
    """
    Điều phối thời gian đèn xanh cho giao lộ thông minh.
    Sử dụng ML model (DeltaApplier) và fallback về rule-based nếu model lỗi/không tồn tại.
    """

    def optimize(self, congestion_level: str) -> dict:
        """
        Rule-based fallback (giữ tương thích ngược).
        Sử dụng map cứng: Low=20s, Medium=40s, High=60s, Severe=90s.
        """
        lvl = str(congestion_level).lower()
        green_time = _FALLBACK_MAP.get(lvl, 90)
        return {"green_time": green_time, "mode": "rule"}

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
        """
        try:
            # 1. Lấy thông tin pha
            phase_info = get_phase(camera_id)
            
            # 2. Gọi delta applier
            green_time = apply(
                camera_id=camera_id,
                queue_proxy=queue_proxy,
                inbound_count=inbound_count,
                congestion_level=congestion_level,
                hour=hour,
                dow=dow
            )

            # 3. Tính delta so với baseline để report
            baseline = CAMERA_BASELINE.get(camera_id, 30)
            delta = round(green_time - baseline, 2)

            return {
                "camera_id": camera_id,
                "phase": phase_info["phase"],
                "direction": phase_info["direction"],
                "green_time": round(green_time, 2),
                "baseline": baseline,
                "delta": delta,
                "mode": "ml"
            }

        except Exception as e:
            print(f"[TrafficLightOptimizer] Fallback to rules due to error: {e}")
            fallback = self.optimize(congestion_level)
            return {
                "camera_id": camera_id,
                "phase": "unknown",
                "direction": "unknown",
                "green_time": float(fallback["green_time"]),
                "baseline": fallback["green_time"],
                "delta": 0.0,
                "mode": "rule_fallback"
            }

if __name__ == "__main__":
    opt = TrafficLightOptimizer()
    print(opt.optimize_with_ml("CAM_01", 15.0, 40, "high", 8, 1))
