import os
import time

import requests

API_BASE = os.getenv("TRAFFIC_API_BASE", "http://127.0.0.1:8000")
CAMERA_ID = os.getenv("TRAFFIC_CAMERA_ID", "CAM_01")
BACKEND_AGG_URL = f"{API_BASE}/aggregation"
BACKEND_RAW_URL = f"{API_BASE}/raw-data"


class TrafficSystem:
    def __init__(self):
        print("=== INIT SYSTEM ===")

        from congestion_classifier import CongestionClassifier
        from traffic_light_logic import TrafficLightOptimizer
        from performance_monitor import PerformanceMonitor

        self.classifier = CongestionClassifier()
        print("[OK] Loaded CongestionClassifier")

        self.optimizer = TrafficLightOptimizer()
        print("[OK] Loaded TrafficLightOptimizer")

        self.monitor = PerformanceMonitor()
        print("[OK] Loaded PerformanceMonitor")

    def run_pipeline(self):
        print("\n===== START PIPELINE =====")

        try:
            print("[1] Calling /raw-data ...")
            raw_res = requests.get(
                BACKEND_RAW_URL,
                params={"camera_id": CAMERA_ID, "limit": 20, "offset": 0},
                timeout=3,
            )

            print("    Status:", raw_res.status_code)
            if raw_res.status_code != 200:
                print("[ERROR] Cannot get raw data")
                print("    Response:", raw_res.text)
                return

            raw_json = raw_res.json()
            items = raw_json.get("items", []) if isinstance(raw_json, dict) else []
            total = raw_json.get("total", len(items)) if isinstance(raw_json, dict) else 0

            print(f"    Total records: {total}")
            print(f"    Returned items: {len(items)}")

            print("\n[2] Calling /aggregation ...")
            response = requests.get(
                BACKEND_AGG_URL,
                params={"camera_id": CAMERA_ID},
                timeout=3,
            )

            print("    Status:", response.status_code)
            if response.status_code != 200:
                print("[ERROR] Aggregation failed")
                print("    Response:", response.text)
                return

            data = response.json()
            if "congestion_level" not in data or "vehicle_count" not in data:
                print("[ERROR] Missing aggregation fields")
                print("    Response:", data)
                return

            vehicle_count = data["vehicle_count"]
            level = data["congestion_level"]
            print("    Aggregated vehicle count:", vehicle_count)
            print("    Congestion level (Backend):", level)

            print("\n[3] Local classification ...")
            local_level = self.classifier.classify(vehicle_count)
            print("    Local result:", local_level)

            print("\n[4] Traffic light optimization ...")
            light = self.optimizer.optimize(level)
            print("    Light config:", light)

            print("\n[5] Monitoring ...")
            perf = self.monitor.monitor()
            print("    Performance:", perf)

            print("\n[OK] SYSTEM RUNNING")

        except requests.exceptions.ConnectionError:
            print("[ERROR] Cannot connect to Backend")
        except requests.exceptions.Timeout:
            print("[ERROR] Request timeout")
        except Exception as exc:
            print("[ERROR] Unexpected error:", exc)


if __name__ == "__main__":
    system = TrafficSystem()

    while True:
        system.run_pipeline()
        time.sleep(5)
