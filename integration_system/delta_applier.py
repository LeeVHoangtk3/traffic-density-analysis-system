"""
integration_system/delta_applier.py
====================================
Áp dụng delta dự đoán từ LightDeltaModel vào baseline_green của camera
để tính thời gian đèn xanh cuối cùng (giây).
"""

import sys
import os

# Ensure we can import from the root
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ml_service.light_delta_model import LightDeltaModel

# Baseline green times for cameras
CAMERA_BASELINE: dict[str, int] = {
    "CAM_01": 30,
    "CAM_02": 25,
    "CAM_03": 35,
    "CAM_04": 40,
}

_DELTA_MIN: float = -30.0
_DELTA_MAX: float = +45.0

_model_instance: LightDeltaModel | None = None

def _get_model() -> LightDeltaModel | None:
    """Returns the LightDeltaModel singleton. Returns None if loading fails."""
    global _model_instance
    if _model_instance is None:
        try:
            _model_instance = LightDeltaModel()
            # Try to force load to check if file exists
            _model_instance._load()
        except Exception as e:
            print(f"[DeltaApplier] Warning: Could not load ML model: {e}")
            _model_instance = None
    return _model_instance

def apply(
    camera_id: str,
    queue_proxy: float,
    inbound_count: int,
    congestion_level: str,
    hour: int,
    dow: int,
) -> float:
    """
    Predicts green_time by applying a delta to the baseline.
    Returns baseline if model is missing or error occurs.
    """
    if camera_id not in CAMERA_BASELINE:
        print(f"[DeltaApplier] Warning: Camera {camera_id} not in baseline map. Using 30s.")
        baseline_green = 30
    else:
        baseline_green = CAMERA_BASELINE[camera_id]

    model = _get_model()
    if model is None:
        return float(baseline_green)

    try:
        feature_dict = {
            "queue_proxy":      queue_proxy,
            "inbound_count":    inbound_count,
            "congestion_level": congestion_level.lower(),
            "baseline_green":   baseline_green,
            "hour":             hour,
            "day_of_week":      dow,
        }
        delta: float = model.predict_delta(feature_dict)
        
        # Clamp as requested
        delta = max(_DELTA_MIN, min(_DELTA_MAX, delta))
        
        green_time = max(0.0, baseline_green + delta)
        return float(green_time)
    except Exception as e:
        print(f"[DeltaApplier] Error during prediction: {e}. Falling back to baseline.")
        return float(baseline_green)

if __name__ == "__main__":
    # Quick test
    res = apply("CAM_01", 10.0, 50, "high", 12, 0)
    print(f"Result: {res}s")
