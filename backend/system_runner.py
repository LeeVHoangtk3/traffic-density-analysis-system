"""
integration_system/system_runner.py
=====================================
Entry point duy nhat — chay file nay la chay toan bo he thong:
    python integration_system/system_runner.py

Cac buoc trong mot chu ky pipeline:
    [1] Goi /raw-data          -> lay ban ghi tho tu Backend
    [2] Goi /aggregation       -> lay vehicle_count + congestion_level
    [3] Phan loai tac nghen    -> CongestionClassifier (rule-based, local)
    [4] Giam sat hieu nang     -> PerformanceMonitor (CPU / RAM)

Bien moi truong:
    TRAFFIC_API_BASE    (mac dinh: http://127.0.0.1:8000)
    TRAFFIC_CAMERA_ID   (mac dinh: CAM_01)
    PIPELINE_INTERVAL   (mac dinh: 5 giay)
    NO_SUBPROCESS       (neu set = 1, khong tu dong khoi dong backend/detection/frontend)
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

try:
    import psutil        # performance monitor
except ModuleNotFoundError:
    psutil = None

try:
    import requests      # goi Backend API
except ModuleNotFoundError:
    requests = None

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
CAMERA_ID        = os.getenv("TRAFFIC_CAMERA_ID", "cam01")
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
            return "low"
        elif vehicle_count < 30:
            return "medium"
        elif vehicle_count < 50:
            return "high"
        else:
            return "severe"


# ===========================================================================
# 3. PERFORMANCE MONITOR  (noi tuyen tu performance_monitor.py)
# ===========================================================================

class PerformanceMonitor:
    """Giam sat tai nguyen he thong (CPU + RAM)."""

    def monitor(self) -> dict:
        if psutil is None:
            return {"cpu_usage": 0.0, "memory_usage": 0.0, "source": "psutil_unavailable"}
        cpu    = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        return {"cpu_usage": cpu, "memory_usage": memory}




# ===========================================================================
# 7. TRAFFIC SYSTEM — KHOI DONG + PIPELINE
# ===========================================================================

class TrafficSystem:
    """He thong quan ly giao thong toan dien."""

    def __init__(self):
        print("=" * 60)
        print("  TRAFFIC DENSITY ANALYSIS SYSTEM — STARTING")
        print("=" * 60)

        # --- Khoi dong Backend & Detection & Frontend (subprocess) ---
        if not NO_SUBPROCESS:
            self._start_subprocess_services()
        else:
            print("[INFO] NO_SUBPROCESS=1 -> Skip launching backend/detection/frontend")

        # --- Khoi tao cac component noi tuyen ---
        self.classifier = CongestionClassifier()
        print("[OK] CongestionClassifier ready")

        self.monitor = PerformanceMonitor()
        print("[OK] PerformanceMonitor ready")

        print(f"[OK] API base: {API_BASE} | Camera: {CAMERA_ID}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Subprocess: Backend + Detection + Frontend
    # ------------------------------------------------------------------

    def _start_subprocess_services(self):
        project_root = os.path.abspath(os.path.join(_INTEGRATION_DIR, ".."))

        print("[1/3] Starting Backend (uvicorn)...")
        backend_cmd = [
            "uvicorn", "backend.main:app",
            "--reload", "--host", "127.0.0.1", "--port", "8000"
        ]
        self.backend_process = subprocess.Popen(
            backend_cmd, cwd=project_root
        )
        time.sleep(5)
        print("      Backend started (PID={})".format(self.backend_process.pid))

        print("[2/3] Starting Detection Engine...")
        detection_cmd = [sys.executable, "-m", "detection.main"]
        self.detection_process = subprocess.Popen(
            detection_cmd, cwd=project_root
        )
        time.sleep(5)
        print("      Detection started (PID={})".format(self.detection_process.pid))

        print("[3/3] Starting Frontend (npm start)...")
        frontend_dir = os.path.join(project_root, "frontend")
        frontend_cmd = ["npm.cmd", "start"] if os.name == 'nt' else ["npm", "start"]
        self.frontend_process = subprocess.Popen(
            frontend_cmd, cwd=frontend_dir
        )
        time.sleep(5)
        print("      Frontend started (PID={})".format(self.frontend_process.pid))

    # ------------------------------------------------------------------
    # Dung he thong
    # ------------------------------------------------------------------

    def stop_system(self):
        print("\n[SHUTDOWN] Stopping system...")
        for attr in ("backend_process", "detection_process", "frontend_process"):
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
            if requests is None:
                print("[ERROR] requests package is not installed")
                return

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

            # -------------------------------------------------------
            # BUOC 4: Giam sat hieu nang
            # -------------------------------------------------------
            print("\n[4] Performance monitoring ...")
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