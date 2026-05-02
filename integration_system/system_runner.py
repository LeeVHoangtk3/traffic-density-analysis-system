"""
integration_system/system_runner.py
=====================================
Entry point duy nhat — chay file nay la chay toan bo he thong:
    python integration_system/system_runner.py

Cac buoc trong mot chu ky pipeline:
    [1] Goi /raw-data          -> lay ban ghi tho tu Backend
    [2] Goi /aggregation       -> lay vehicle_count + congestion_level
    [3] Phan loai tac nghen    -> CongestionClassifier (rule-based, local)
    [4] Toi uu den tin hieu    -> TrafficLightOptimizer (ML hoac rule-based)
         [4a] DeltaApplier     -> predict delta tu LightDeltaModel
         [4b] DirectionRouter  -> anh xa camera_id -> pha den
    [5] Giam sat hieu nang     -> PerformanceMonitor (CPU / RAM)

Bien moi truong:
    TRAFFIC_API_BASE    (mac dinh: http://127.0.0.1:8000)
    TRAFFIC_CAMERA_ID   (mac dinh: CAM_01)
    PIPELINE_INTERVAL   (mac dinh: 5 giay)
    NO_SUBPROCESS       (neu set = 1, khong tu dong khoi dong backend/detection)
"""

# ===========================================================================
# 0. IMPORTS CHUAN
# ===========================================================================

import os
import sys
import time
import signal
import subprocess
import datetime

import psutil        # performance monitor
import requests      # goi Backend API

# ===========================================================================
# 1. CAU HINH TOAN CUC
# ===========================================================================

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_INTEGRATION_DIR = os.path.dirname(os.path.abspath(__file__))
if _INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, _INTEGRATION_DIR)

API_BASE         = os.getenv("TRAFFIC_API_BASE",  "http://127.0.0.1:8000")
CAMERA_ID        = os.getenv("TRAFFIC_CAMERA_ID", "CAM_01")
PIPELINE_INTERVAL = int(os.getenv("PIPELINE_INTERVAL", "5"))   # giay
NO_SUBPROCESS    = os.getenv("NO_SUBPROCESS", "0") == "1"

BACKEND_AGG_URL  = f"{API_BASE}/aggregation"
BACKEND_RAW_URL  = f"{API_BASE}/raw-data"

# ===========================================================================
# 2. CONGESTION CLASSIFIER  (noi tuyen tu congestion_classifier.py)
# ===========================================================================

class CongestionClassifier:
    """Phan loai muc tac nghen theo so xe (rule-based, chay local)."""

    def classify(self, vehicle_count: int) -> str:
        if vehicle_count < 15:
            return "Low"
        elif vehicle_count < 30:
            return "Medium"
        elif vehicle_count < 50:
            return "High"
        else:
            return "Severe"


# ===========================================================================
# 3. PERFORMANCE MONITOR  (noi tuyen tu performance_monitor.py)
# ===========================================================================

class PerformanceMonitor:
    """Giam sat tai nguyen he thong (CPU + RAM)."""

    def monitor(self) -> dict:
        cpu    = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        return {"cpu_usage": cpu, "memory_usage": memory}


# ===========================================================================
# 4. DIRECTION ROUTER  (noi tuyen tu direction_router.py)
# ===========================================================================

# Anh xa camera_id -> thong tin pha den va huong luong xe.
# Chinh bang nay theo so do vat ly cua he thong thuc te.
CAMERA_PHASE_MAP: dict[str, dict[str, str]] = {
    "CAM_01": {"phase": "north_green", "direction": "inbound",  "junction": "JCT_A"},
    "CAM_02": {"phase": "south_green", "direction": "inbound",  "junction": "JCT_A"},
    "CAM_03": {"phase": "east_green",  "direction": "inbound",  "junction": "JCT_A"},
    "CAM_04": {"phase": "west_green",  "direction": "outbound", "junction": "JCT_A"},
}


def get_phase(camera_id: str) -> dict[str, str]:
    """Tra ve thong tin pha den cua camera_id."""
    if camera_id not in CAMERA_PHASE_MAP:
        raise KeyError(
            f"[DirectionRouter] Camera '{camera_id}' not configured. "
            f"Valid: {list(CAMERA_PHASE_MAP.keys())}"
        )
    return CAMERA_PHASE_MAP[camera_id].copy()


def get_phase_name(camera_id: str) -> str:
    """Tra ve ten pha den (vd: 'north_green')."""
    return get_phase(camera_id)["phase"]


def register_camera(camera_id: str, phase: str,
                    direction: str = "inbound",
                    junction: str = "JCT_DEFAULT") -> None:
    """Dang ky camera moi tai runtime."""
    CAMERA_PHASE_MAP[camera_id] = {
        "phase": phase, "direction": direction, "junction": junction
    }
    print(f"[DirectionRouter] Registered: {camera_id} -> phase='{phase}', "
          f"direction='{direction}', junction='{junction}'")


# ===========================================================================
# 5. DELTA APPLIER  (noi tuyen tu delta_applier.py)
# ===========================================================================

# Thoi gian den xanh baseline (giay) cho tung camera.
CAMERA_BASELINE: dict[str, int] = {
    "CAM_01": 30,
    "CAM_02": 25,
    "CAM_03": 35,
    "CAM_04": 40,
}

_DELTA_MIN: float = -30.0
_DELTA_MAX: float = +45.0

# Singleton LightDeltaModel — chi load pkl mot lan
_light_model = None


def _get_light_model():
    """Lazy-load LightDeltaModel singleton."""
    global _light_model
    if _light_model is None:
        from ml_service.light_delta_model import LightDeltaModel
        _light_model = LightDeltaModel()
    return _light_model


def apply(
    camera_id: str,
    queue_proxy: float,
    inbound_count: int,
    congestion_level: str,
    hour: int,
    dow: int,
) -> float:
    """
    Tinh green_time bang cach cong delta du doan vao baseline cua camera.
    Tra ve: green_time (giay, float, >= 0)
    """
    if camera_id not in CAMERA_BASELINE:
        baseline_green = 30
    else:
        baseline_green = CAMERA_BASELINE[camera_id]

    try:
        feature_dict = {
            "queue_proxy":      queue_proxy,
            "inbound_count":    inbound_count,
            "congestion_level": congestion_level.lower(),
            "baseline_green":   baseline_green,
            "hour":             hour,
            "day_of_week":      dow,
        }
        raw_delta: float = _get_light_model().predict_delta(feature_dict)
        delta: float = max(_DELTA_MIN, min(_DELTA_MAX, raw_delta))
        green_time: float = max(0.0, baseline_green + delta)
        return green_time
    except Exception as e:
        print(f"    [DeltaApplier] Error: {e}. Using baseline.")
        return float(baseline_green)


# ===========================================================================
# 6. TRAFFIC LIGHT OPTIMIZER  (noi tuyen tu traffic_light_logic.py)
# ===========================================================================

_RULE_MAP: dict[str, int] = {
    "low":    20,
    "medium": 40,
    "high":   60,
    "severe": 90,
}


class TrafficLightOptimizer:
    """
    Dieu phoi thoi gian den xanh.
    - optimize()          : rule-based fallback
    - optimize_with_ml()  : ML delta + direction router
    """

    def optimize(self, congestion_level: str) -> dict:
        """Rule-based fallback."""
        lvl = str(congestion_level).lower()
        green_time = _RULE_MAP.get(lvl, 90)
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
        Tinh green_time bang ML delta model ket hop direction router.
        """
        try:
            phase_info = get_phase(camera_id)
            baseline   = CAMERA_BASELINE.get(camera_id, 30)

            green_time = apply(
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
                "phase":      phase_info["phase"],
                "direction":  phase_info["direction"],
                "green_time": round(green_time, 2),
                "baseline":   baseline,
                "delta":      delta,
                "mode":       "ml",
            }

        except Exception as exc:
            print(f"    [TrafficLightOptimizer] WARNING: {exc}. Fallback to rule.")
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


# ===========================================================================
# 7. TRAFFIC SYSTEM — KHOI DONG + PIPELINE
# ===========================================================================

class TrafficSystem:
    """He thong quan ly giao thong toan dien."""

    def __init__(self):
        print("=" * 60)
        print("  TRAFFIC DENSITY ANALYSIS SYSTEM — STARTING")
        print("=" * 60)

<<<<<<< HEAD
        # Start backend
        print("Starting Backend...")
        backend_cmd = ["uvicorn", "backend.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"]
        self.backend_process = subprocess.Popen(backend_cmd, cwd=os.path.join(os.path.dirname(__file__), ".."))

        # Wait for backend to start
        time.sleep(5)

        # Start detection
        print("Starting Detection Engine...")
        detection_cmd = ["python", "detection/main.py"]
        self.detection_process = subprocess.Popen(detection_cmd, cwd=os.path.join(os.path.dirname(__file__), ".."))

        # Wait for detection to start
        time.sleep(5)

        from congestion_classifier import CongestionClassifier

        from performance_monitor import PerformanceMonitor
=======
        # --- Khoi dong Backend & Detection (subprocess) ---
        if not NO_SUBPROCESS:
            self._start_subprocess_services()
        else:
            print("[INFO] NO_SUBPROCESS=1 -> Skip launching backend/detection")
>>>>>>> origin/hao

        # --- Khoi tao cac component noi tuyen ---
        self.classifier = CongestionClassifier()
        print("[OK] CongestionClassifier ready")

<<<<<<< HEAD
=======
        self.optimizer = TrafficLightOptimizer()
        print("[OK] TrafficLightOptimizer ready (ML + rule fallback)")
>>>>>>> origin/hao

        self.monitor = PerformanceMonitor()
        print("[OK] PerformanceMonitor ready")

        print(f"[OK] DirectionRouter ready | cameras: {list(CAMERA_PHASE_MAP.keys())}")
        print(f"[OK] DeltaApplier ready    | baselines: {CAMERA_BASELINE}")
        print(f"[OK] API base: {API_BASE} | Camera: {CAMERA_ID}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Subprocess: Backend + Detection
    # ------------------------------------------------------------------

    def _start_subprocess_services(self):
        project_root = os.path.abspath(os.path.join(_INTEGRATION_DIR, ".."))

        print("[1/2] Starting Backend (uvicorn)...")
        backend_cmd = [
            "uvicorn", "backend.main:app",
            "--reload", "--host", "127.0.0.1", "--port", "8000"
        ]
        self.backend_process = subprocess.Popen(
            backend_cmd, cwd=project_root
        )
        time.sleep(5)
        print("      Backend started (PID={})".format(self.backend_process.pid))

        print("[2/2] Starting Detection Engine...")
        detection_cmd = ["python", "detection/main.py"]
        self.detection_process = subprocess.Popen(
            detection_cmd, cwd=project_root
        )
        time.sleep(5)
        print("      Detection started (PID={})".format(self.detection_process.pid))

    # ------------------------------------------------------------------
    # Dung he thong
    # ------------------------------------------------------------------

    def stop_system(self):
        print("\n[SHUTDOWN] Stopping system...")
        for attr in ("backend_process", "detection_process"):
            proc = getattr(self, attr, None)
            if proc is not None:
                proc.terminate()
                proc.wait()
        print("[SHUTDOWN] System stopped.")

    # ------------------------------------------------------------------
    # Pipeline chinh
    # ------------------------------------------------------------------

    def run_pipeline(self):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*60}")
        print(f"  PIPELINE @ {ts}")
        print(f"{'='*60}")

        try:
            # -------------------------------------------------------
            # BUOC 1: Lay ban ghi tho
            # -------------------------------------------------------
            print("[1] GET /raw-data ...")
            raw_res = requests.get(
                BACKEND_RAW_URL,
                params={"camera_id": CAMERA_ID, "limit": 20, "offset": 0},
                timeout=3,
            )
            print(f"    Status : {raw_res.status_code}")
            if raw_res.status_code != 200:
                print(f"    ERROR  : {raw_res.text}")
                return

            raw_json = raw_res.json()
            items    = raw_json.get("items", []) if isinstance(raw_json, dict) else []
            total    = raw_json.get("total",  len(items)) if isinstance(raw_json, dict) else 0
            print(f"    Records: {total} total / {len(items)} returned")

            # -------------------------------------------------------
            # BUOC 2: Lay aggregation
            # -------------------------------------------------------
            print("\n[2] GET /aggregation ...")
            agg_res = requests.get(
                BACKEND_AGG_URL,
                params={"camera_id": CAMERA_ID},
                timeout=3,
            )
            print(f"    Status : {agg_res.status_code}")
            if agg_res.status_code != 200:
                print(f"    ERROR  : {agg_res.text}")
                return

            data = agg_res.json()
            if "congestion_level" not in data or "vehicle_count" not in data:
                print(f"    ERROR  : Missing required fields | Response: {data}")
                return

            vehicle_count = data["vehicle_count"]
            backend_level = data["congestion_level"]
            print(f"    Vehicle count    : {vehicle_count}")
            print(f"    Congestion (API) : {backend_level}")

            # -------------------------------------------------------
            # BUOC 3: Phan loai local
            # -------------------------------------------------------
            print("\n[3] Local congestion classification ...")
            local_level = self.classifier.classify(vehicle_count)
            print(f"    Local result     : {local_level}")

<<<<<<< HEAD
=======
            # -------------------------------------------------------
            # BUOC 4: Toi uu den tin hieu (ML > rule fallback)
            # -------------------------------------------------------
            print("\n[4] Traffic light optimization ...")
>>>>>>> origin/hao

            # Lay them cac truong ML neu API tra ve
            queue_proxy   = float(data.get("queue_proxy",   0.0))
            inbound_count = int(data.get("inbound_count",   vehicle_count))
            now           = datetime.datetime.now()
            hour          = int(data.get("hour",            now.hour))
            dow           = int(data.get("day_of_week",     now.weekday()))

            ml_fields_available = all(
                k in data for k in ("queue_proxy", "inbound_count", "hour", "day_of_week")
            )

            if ml_fields_available:
                light = self.optimizer.optimize_with_ml(
                    camera_id=CAMERA_ID,
                    queue_proxy=queue_proxy,
                    inbound_count=inbound_count,
                    congestion_level=backend_level,
                    hour=hour,
                    dow=dow,
                )
            else:
                # Fallback rule-based (API khong du truong ML)
                print("    (ML fields not in API response -> using rule-based fallback)")
                # Van co the su dung local classification + apply_delta
                try:
                    light = self.optimizer.optimize_with_ml(
                        camera_id=CAMERA_ID,
                        queue_proxy=queue_proxy,
                        inbound_count=vehicle_count,
                        congestion_level=local_level,
                        hour=now.hour,
                        dow=now.weekday(),
                    )
                except Exception:
                    light = self.optimizer.optimize(local_level)

            # Hien thi ket qua den tin hieu
            try:
                phase_info = get_phase(CAMERA_ID)
                print(f"    Phase applied    : {phase_info['phase']} "
                      f"({phase_info['direction']}, {phase_info['junction']})")
            except KeyError:
                pass

            if "green_time" in light:
                print(f"    GREEN TIME       : {light['green_time']}s")
            if "delta" in light:
                print(f"    Delta applied    : {light.get('delta', 0):+.2f}s")
            if "baseline" in light:
                print(f"    Baseline         : {light.get('baseline')}s")
            print(f"    Mode             : {light.get('mode', '?')}")
            print(f"    Full config      : {light}")

            # Ghi trang thai den ra file cho detection/main.py doc
            import json
            light_file = os.path.join(_ROOT, "light_status.json")
            try:
                with open(light_file, "w") as f:
                    json.dump(light, f)
            except Exception as e:
                pass

            # -------------------------------------------------------
            # BUOC 5: Giam sat hieu nang
            # -------------------------------------------------------
            print("\n[5] Performance monitoring ...")
            perf = self.monitor.monitor()
            print(f"    CPU usage    : {perf['cpu_usage']}%")
            print(f"    Memory usage : {perf['memory_usage']}%")

            print(f"\n[OK] PIPELINE COMPLETE @ {ts}")

        except requests.exceptions.ConnectionError:
            print("[ERROR] Cannot connect to Backend — is it running?")
        except requests.exceptions.Timeout:
            print("[ERROR] Request timeout")
        except Exception as exc:
            import traceback
            print(f"[ERROR] Unexpected: {exc}")
            traceback.print_exc()


# ===========================================================================
# 8. ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    system = TrafficSystem()

    def _signal_handler(sig, frame):
        system.stop_system()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"\n[INFO] Running pipeline every {PIPELINE_INTERVAL}s. Press Ctrl+C to stop.\n")

    try:
        while True:
            system.run_pipeline()
            time.sleep(PIPELINE_INTERVAL)
    except KeyboardInterrupt:
        system.stop_system()
