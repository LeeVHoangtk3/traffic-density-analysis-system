"""
integration_system/system_runner.py
=====================================
Entry point duy nhat — chay file nay la khoi dong + dieu phoi TOAN BO he thong:
    python integration_system/system_runner.py

He thong gom 4 subprocess:
    [A] Backend   — FastAPI (uvicorn), port 8000
    [B] Detection — YOLO + Tracker, gui event ve Backend
    [C] Frontend  — React (npm start), port 3000
    [D] Pipeline  — Chu ky 5s: aggregation → classify → optimize → monitor

Bien moi truong (tuy chinh):
    TRAFFIC_API_BASE    (mac dinh: http://127.0.0.1:8000)
    TRAFFIC_CAMERA_ID   (mac dinh: cam01)
    PIPELINE_INTERVAL   (mac dinh: 5 giay)
    NO_SUBPROCESS       (neu set = 1, khong tu dong khoi dong backend/detection/frontend)
    SKIP_DETECTION      (neu set = 1, khong khoi dong detection — khi da co du lieu trong DB)
    SKIP_FRONTEND       (neu set = 1, khong khoi dong frontend)
"""

# ===========================================================================
# 0. IMPORTS
# ===========================================================================

import os
import sys
import time
import json
import signal
import subprocess
import datetime
import threading
import traceback

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

try:
    import requests
except ModuleNotFoundError:
    requests = None

# ===========================================================================
# 1. CAU HINH
# ===========================================================================

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_INTEGRATION_DIR = os.path.dirname(os.path.abspath(__file__))
if _INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, _INTEGRATION_DIR)

API_BASE          = os.getenv("TRAFFIC_API_BASE",  "http://127.0.0.1:8000")
CAMERA_ID         = os.getenv("TRAFFIC_CAMERA_ID", "cam01")
PIPELINE_INTERVAL = int(os.getenv("PIPELINE_INTERVAL", "5"))
NO_SUBPROCESS     = os.getenv("NO_SUBPROCESS", "0") == "1"
SKIP_DETECTION    = os.getenv("SKIP_DETECTION", "0") == "1"
SKIP_FRONTEND     = os.getenv("SKIP_FRONTEND", "0") == "1"

BACKEND_AGG_URL = f"{API_BASE}/aggregation"
BACKEND_RAW_URL = f"{API_BASE}/raw-data"
BACKEND_HEALTH  = f"{API_BASE}/health"


# ===========================================================================
# 2. CONGESTION CLASSIFIER (rule-based, local)
# ===========================================================================

class CongestionClassifier:
    """Phan loai muc tac nghen theo so xe."""

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
# 3. PERFORMANCE MONITOR
# ===========================================================================

class PerformanceMonitor:
    """Giam sat CPU + RAM."""

    def monitor(self) -> dict:
        if psutil is None:
            return {"cpu_usage": 0.0, "memory_usage": 0.0, "source": "psutil_unavailable"}
        cpu    = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory().percent
        return {"cpu_usage": cpu, "memory_usage": memory}


# ===========================================================================
# 4. DIRECTION ROUTER
# ===========================================================================

CAMERA_PHASE_MAP: dict[str, dict[str, str]] = {
    "cam01": {
        "phase": "north_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
    },
    "CAM_01": {
        "phase": "north_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
    },
    "cam02": {
        "phase": "south_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
    },
    "CAM_03": {
        "phase": "east_green",
        "controlled_phase": "phase_2",
        "direction": "left",
        "junction": "JCT_A",
    },
    "CAM_04": {
        "phase": "west_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
    },
}


def get_phase(camera_id: str) -> dict[str, str]:
    if camera_id not in CAMERA_PHASE_MAP:
        raise KeyError(
            f"[DirectionRouter] Camera '{camera_id}' not configured. "
            f"Valid: {list(CAMERA_PHASE_MAP.keys())}"
        )
    return CAMERA_PHASE_MAP[camera_id].copy()


def get_phase_name(camera_id: str) -> str:
    return get_phase(camera_id)["phase"]


# ===========================================================================
# 5. DELTA APPLIER
# ===========================================================================

PHASE_BASELINE: dict[str, int] = {
    "phase_1": 50,
    "phase_2": 30,
}

_DELTA_MIN: float = -30.0
_DELTA_MAX: float = +45.0

_light_model = None


def _get_light_model():
    global _light_model
    if _light_model is None:
        try:
            from ml_service.light_delta_model import LightDeltaModel
            _light_model = LightDeltaModel()
        except Exception as e:
            print(f"    [DeltaApplier] Cannot load LightDeltaModel: {e}")
            _light_model = None
    return _light_model


def _controlled_phase_for_camera(camera_id: str) -> str:
    return get_phase(camera_id).get("controlled_phase", "phase_1")


def _baseline_for_camera(camera_id: str) -> int:
    controlled_phase = _controlled_phase_for_camera(camera_id)
    return PHASE_BASELINE.get(controlled_phase, PHASE_BASELINE["phase_1"])


def apply(
    camera_id: str,
    queue_proxy: float,
    inbound_count: int,
    congestion_level: str,
    hour: int,
    dow: int,
) -> float:
    phase_info = get_phase(camera_id)
    controlled_phase = phase_info.get("controlled_phase", "phase_1")
    baseline_green = PHASE_BASELINE.get(controlled_phase, PHASE_BASELINE["phase_1"])

    model = _get_light_model()
    if model is None:
        return float(baseline_green)

    try:
        feature_dict = {
            "camera_id":        camera_id,
            "controlled_phase": controlled_phase,
            "queue_proxy":      queue_proxy,
            "inbound_count":    inbound_count,
            "congestion_level": congestion_level.lower(),
            "baseline_green":   baseline_green,
            "hour":             hour,
            "day_of_week":      dow,
        }
        raw_delta: float = model.predict_delta(feature_dict)
        delta: float = max(_DELTA_MIN, min(_DELTA_MAX, raw_delta))
        green_time: float = max(0.0, baseline_green + delta)
        return green_time
    except Exception as e:
        print(f"    [DeltaApplier] Error: {e}. Using baseline.")
        return float(baseline_green)


# ===========================================================================
# 6. TRAFFIC LIGHT OPTIMIZER
# ===========================================================================

_RULE_MAP: dict[str, int] = {
    "low":    20,
    "medium": 40,
    "high":   60,
    "severe": 90,
}


class TrafficLightOptimizer:

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
        try:
            phase_info = get_phase(camera_id)
            baseline = _baseline_for_camera(camera_id)

            green_time = apply(
                camera_id=camera_id,
                queue_proxy=queue_proxy,
                inbound_count=inbound_count,
                congestion_level=congestion_level,
                hour=hour,
                dow=dow,
            )
            delta = round(green_time - baseline, 2)
            model = _get_light_model()

            result = {
                "camera_id":  camera_id,
                "phase":      phase_info["phase"],
                "controlled_phase": phase_info.get("controlled_phase", "phase_1"),
                "direction":  phase_info["direction"],
                "green_time": round(green_time, 2),
                "baseline":   baseline,
                "delta":      delta,
                "mode":       "ml" if model else "rule_fallback",
            }
            if model and hasattr(model, 'prediction_source'):
                result["prediction_source"] = model.prediction_source()
            if model and hasattr(model, 'fallback_reason') and model.fallback_reason:
                result["fallback_reason"] = model.fallback_reason
            return result

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
        self.processes: dict[str, subprocess.Popen] = {}
        self._stopping = False
        self._cycle = 0

        self._banner()

        # --- Khoi dong subprocess ---
        if not NO_SUBPROCESS:
            self._start_all_services()
        else:
            print("[INFO] NO_SUBPROCESS=1 → Khong khoi dong subprocess")

        # --- Component noi tuyen ---
        self.classifier = CongestionClassifier()
        self.optimizer  = TrafficLightOptimizer()
        self.monitor    = PerformanceMonitor()

        print()
        self._log("OK", "CongestionClassifier ready")
        self._log("OK", "TrafficLightOptimizer ready (ML + rule fallback)")
        self._log("OK", "PerformanceMonitor ready")
        self._log("OK", f"DirectionRouter ready | cameras: {list(CAMERA_PHASE_MAP.keys())}")
        self._log("OK", f"DeltaApplier ready    | phase baselines: {PHASE_BASELINE}")
        self._log("OK", f"API base: {API_BASE} | Camera: {CAMERA_ID}")
        print("=" * 64)
        print()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _banner():
        print()
        print("╔" + "═" * 62 + "╗")
        print("║" + "TRAFFIC DENSITY ANALYSIS SYSTEM".center(62) + "║")
        print("║" + "All-in-One Launcher".center(62) + "║")
        print("╚" + "═" * 62 + "╝")
        print()

    @staticmethod
    def _log(level: str, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = {
            "OK":    "✅",
            "INFO":  "ℹ️ ",
            "WARN":  "⚠️ ",
            "ERROR": "❌",
            "STEP":  "🔹",
        }.get(level, "  ")
        print(f"  {prefix} [{ts}] {msg}")

    # ------------------------------------------------------------------
    # SUBPROCESS MANAGEMENT
    # ------------------------------------------------------------------

    def _wait_for_backend(self, timeout: int = 30) -> bool:
        """Doi backend san sang (health check OK)."""
        self._log("INFO", f"Doi Backend san sang (max {timeout}s)...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                if requests:
                    r = requests.get(BACKEND_HEALTH, timeout=2)
                    if r.status_code == 200:
                        d = r.json()
                        if d.get("status") == "ok":
                            self._log("OK", f"Backend san sang! (database: {d.get('database', '?')})")
                            return True
            except Exception:
                pass
            time.sleep(1)
        self._log("WARN", "Backend chua san sang sau timeout — tiep tuc...")
        return False

    def _start_all_services(self):
        """Khoi dong Backend → doi san sang → Detection → Frontend."""
        project_root = _ROOT

        # ──────────────── [A] BACKEND ────────────────
        self._log("INFO", "[1/3] Khoi dong Backend (uvicorn)...")
        backend_cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--reload",
        ]
        self.processes["backend"] = subprocess.Popen(
            backend_cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._log("OK", f"Backend PID={self.processes['backend'].pid}")

        # Doi backend san sang truoc khi khoi dong detection
        self._wait_for_backend(timeout=30)

        # ──────────────── [B] DETECTION ────────────────
        if not SKIP_DETECTION:
            self._log("INFO", "[2/3] Khoi dong Detection Engine...")
            detection_env = os.environ.copy()
            # Detection gui event ve backend, KHONG chay dry-run
            detection_env["DRY_RUN"]          = "false"
            detection_env["NO_DISPLAY"]       = "true"
            detection_env["SYNC_MODE"]        = "true"
            detection_env["TRAFFIC_API_URL"]  = f"{API_BASE}/detection"

            detection_cmd = [sys.executable, "-m", "detection.main"]
            self.processes["detection"] = subprocess.Popen(
                detection_cmd,
                cwd=project_root,
                env=detection_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._log("OK", f"Detection PID={self.processes['detection'].pid}")
        else:
            self._log("INFO", "[2/3] SKIP_DETECTION=1 → Bo qua detection")

        # ──────────────── [C] FRONTEND ────────────────
        if not SKIP_FRONTEND:
            self._log("INFO", "[3/3] Khoi dong Frontend (React)...")
            frontend_dir = os.path.join(project_root, "frontend")
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

            frontend_env = os.environ.copy()
            frontend_env["BROWSER"] = "none"  # Khong tu dong mo browser

            self.processes["frontend"] = subprocess.Popen(
                [npm_cmd, "start"],
                cwd=frontend_dir,
                env=frontend_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._log("OK", f"Frontend PID={self.processes['frontend'].pid}")
        else:
            self._log("INFO", "[3/3] SKIP_FRONTEND=1 → Bo qua frontend")

        # ──────────────── LOG STREAM ────────────────
        # Chay thread doc stdout cua cac subprocess (tranh block)
        for name, proc in self.processes.items():
            if proc.stdout:
                t = threading.Thread(
                    target=self._stream_output,
                    args=(name, proc),
                    daemon=True,
                )
                t.start()

        time.sleep(2)
        print()
        self._log("OK", "=== TAT CA SERVICES DA KHOI DONG ===")
        print()

    def _stream_output(self, name: str, proc: subprocess.Popen):
        """Doc stdout cua subprocess va in ra voi prefix."""
        tag = f"[{name.upper():>9s}]"
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    print(f"  {tag} {line}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # DUNG HE THONG
    # ------------------------------------------------------------------

    def stop_system(self):
        if self._stopping:
            return
        self._stopping = True

        print()
        print("=" * 64)
        print("  🛑 DANG TAT HE THONG...")
        print("=" * 64)

        for name in ("frontend", "detection", "backend"):
            proc = self.processes.get(name)
            if proc is None:
                continue

            try:
                if proc.poll() is None:
                    self._log("INFO", f"Dung {name} (PID={proc.pid})...")
                    if os.name == "nt":
                        # Windows: kill process tree
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            capture_output=True,
                        )
                    else:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                    self._log("OK", f"{name} da dung")
                else:
                    self._log("INFO", f"{name} da thoat (code={proc.returncode})")
            except Exception as e:
                self._log("WARN", f"Loi khi dung {name}: {e}")

        print()
        print("  ✅ HE THONG DA TAT HOAN TOAN")
        print("=" * 64)

    # ------------------------------------------------------------------
    # PIPELINE CHINH
    # ------------------------------------------------------------------

    def run_pipeline(self):
        self._cycle += 1
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        print()
        print(f"  ┌{'─' * 56}┐")
        print(f"  │  PIPELINE #{self._cycle:04d}  @  {ts}{'':>30s}│")
        print(f"  └{'─' * 56}┘")

        try:
            if requests is None:
                self._log("ERROR", "'requests' package chua cai dat!")
                return

            # ── BUOC 1: Kiem tra backend con song ────────────────────
            self._log("STEP", "[1/5] Kiem tra Backend health...")
            try:
                health = requests.get(BACKEND_HEALTH, timeout=3).json()
                db_status = health.get("database", "?")
                self._log("OK", f"Backend OK | database={db_status}")
            except Exception as e:
                self._log("ERROR", f"Backend khong phan hoi: {e}")
                return

            # ── BUOC 2: Lay raw-data ─────────────────────────────────
            self._log("STEP", "[2/5] GET /raw-data ...")
            raw_res = requests.get(
                BACKEND_RAW_URL,
                params={"limit": 20, "offset": 0},
                timeout=5,
            )
            if raw_res.status_code != 200:
                self._log("ERROR", f"raw-data HTTP {raw_res.status_code}")
                return

            raw_json = raw_res.json()
            items = raw_json.get("items", []) if isinstance(raw_json, dict) else []
            total = raw_json.get("total", len(items)) if isinstance(raw_json, dict) else 0
            self._log("OK", f"Records: {total} total / {len(items)} returned")

            # ── BUOC 3: Lay aggregation ──────────────────────────────
            self._log("STEP", "[3/5] GET /aggregation ...")
            agg_res = requests.get(BACKEND_AGG_URL, timeout=5)
            if agg_res.status_code != 200:
                self._log("ERROR", f"aggregation HTTP {agg_res.status_code}")
                return

            data = agg_res.json()
            vehicle_count = data.get("vehicle_count", 0)
            backend_level = data.get("congestion_level", "low")
            self._log("OK", f"vehicle_count={vehicle_count} | congestion={backend_level}")

            # Phan loai local
            local_level = self.classifier.classify(vehicle_count)
            if local_level != backend_level.lower():
                self._log("INFO", f"Local classify: {local_level} (API: {backend_level})")

            # ── BUOC 4: Toi uu den tin hieu ──────────────────────────
            self._log("STEP", "[4/5] Traffic light optimization ...")

            queue_proxy   = float(data.get("queue_proxy",   0.0))
            inbound_count = int(data.get("inbound_count",   vehicle_count))
            now           = datetime.datetime.now()
            hour          = int(data.get("hour",            now.hour))
            dow           = int(data.get("day_of_week",     now.weekday()))

            try:
                light = self.optimizer.optimize_with_ml(
                    camera_id=CAMERA_ID,
                    queue_proxy=queue_proxy,
                    inbound_count=inbound_count,
                    congestion_level=backend_level,
                    hour=hour,
                    dow=dow,
                )
            except Exception:
                light = self.optimizer.optimize(local_level)

            gt = light.get("green_time", "?")
            mode = light.get("mode", "?")
            delta = light.get("delta", 0)
            self._log("OK", f"green_time={gt}s | delta={delta:+.1f}s | mode={mode}")

            # Ghi trang thai den ra file cho detection/main.py doc
            light_file = os.path.join(_ROOT, "light_status.json")
            try:
                with open(light_file, "w") as f:
                    json.dump(light, f)
            except Exception:
                pass

            # ── BUOC 5: Hieu nang he thong ───────────────────────────
            self._log("STEP", "[5/5] Performance monitoring ...")
            perf = self.monitor.monitor()
            self._log("OK", f"CPU={perf['cpu_usage']:.1f}% | RAM={perf['memory_usage']:.1f}%")

            # Kiem tra subprocess con song
            for name, proc in self.processes.items():
                if proc.poll() is not None:
                    self._log("WARN", f"⚠ {name} da thoat (code={proc.returncode})")

            self._log("OK", f"Pipeline #{self._cycle} hoan thanh")

        except requests.exceptions.ConnectionError:
            self._log("ERROR", "Khong the ket noi Backend — chua chay?")
        except requests.exceptions.Timeout:
            self._log("ERROR", "Request timeout")
        except Exception as exc:
            self._log("ERROR", f"Unexpected: {exc}")
            traceback.print_exc()


# ===========================================================================
# 8. ENTRY POINT
# ===========================================================================

def main():
    system = TrafficSystem()

    def _signal_handler(sig, frame):
        system.stop_system()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print()
    system._log("INFO", f"Pipeline chay moi {PIPELINE_INTERVAL}s. Nhan Ctrl+C de dung.")
    print()
    system._log("INFO", f"Frontend:  http://localhost:3000")
    system._log("INFO", f"Backend:   {API_BASE}")
    system._log("INFO", f"API Docs:  {API_BASE}/docs")
    print()

    try:
        while True:
            system.run_pipeline()
            time.sleep(PIPELINE_INTERVAL)
    except KeyboardInterrupt:
        system.stop_system()


if __name__ == "__main__":
    main()