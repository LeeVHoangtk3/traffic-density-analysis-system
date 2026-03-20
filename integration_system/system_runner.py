import requests
import time

BACKEND_AGG_URL = "http://127.0.0.1:8000/aggregation"
BACKEND_RAW_URL = "http://127.0.0.1:8000/raw-data"


class TrafficSystem:
    def __init__(self):
        print("=== INIT SYSTEM ===")

        from congestion_classifier import CongestionClassifier
        from traffic_light_logic import TrafficLightOptimizer
        from performance_monitor import PerformanceMonitor

        self.classifier = CongestionClassifier()
        print("✔ Loaded CongestionClassifier")

        self.optimizer = TrafficLightOptimizer()
        print("✔ Loaded TrafficLightOptimizer")

        self.monitor = PerformanceMonitor()
        print("✔ Loaded PerformanceMonitor")

    def run_pipeline(self):
        print("\n===== START PIPELINE =====")

        try:
            # ===== STEP 1: GET RAW DATA =====
            print("[1] Calling /raw-data ...")
            raw_res = requests.get(BACKEND_RAW_URL, timeout=2)

            print("    Status:", raw_res.status_code)

            if raw_res.status_code != 200:
                print("✖ ERROR: Cannot get raw data")
                print("    Response:", raw_res.text)
                return

            raw_json = raw_res.json()
            print("    RAW DATA:", raw_json)
            print("    TYPE:", type(raw_json))

            # ===== FIX LIST / DICT =====
            if isinstance(raw_json, list):
                print("✔ Data is LIST")
                vehicle_count = sum(item.get("vehicle_count", 0) for item in raw_json)

            elif isinstance(raw_json, dict):
                print("✔ Data is DICT")
                if "vehicle_count" not in raw_json:
                    print("✖ ERROR: Missing 'vehicle_count'")
                    return
                vehicle_count = raw_json["vehicle_count"]

            else:
                print("✖ ERROR: Unknown data format")
                return

            print("✔ Vehicle count:", vehicle_count)

            # ===== STEP 2: CALL AGGREGATION =====
            print("\n[2] Calling /aggregation ...")
            response = requests.get(
                BACKEND_AGG_URL,
                params={"vehicle_count": vehicle_count},
                timeout=2
            )

            print("    Status:", response.status_code)

            if response.status_code != 200:
                print("✖ ERROR: Aggregation failed")
                print("    Response:", response.text)
                return

            data = response.json()
            print("    DATA:", data)

            if "congestion_level" not in data:
                print("✖ ERROR: Missing 'congestion_level'")
                return

            level = data["congestion_level"]
            print("✔ Congestion level (Backend):", level)

            # ===== STEP 3: LOCAL CLASSIFICATION =====
            print("\n[3] Local classification ...")
            local_level = self.classifier.classify(vehicle_count)
            print("✔ Local result:", local_level)

            # ===== STEP 4: TRAFFIC LIGHT =====
            print("\n[4] Traffic light optimization ...")
            light = self.optimizer.optimize(level)
            print("✔ Light config:", light)

            # ===== STEP 5: PERFORMANCE =====
            print("\n[5] Monitoring ...")
            perf = self.monitor.monitor()
            print("✔ Performance:", perf)

            print("\n✔✔ SYSTEM RUNNING OK ✔✔")

        except requests.exceptions.ConnectionError:
            print("✖ ERROR: Cannot connect to Backend (check server)")
        except requests.exceptions.Timeout:
            print("✖ ERROR: Request timeout")
        except Exception as e:
            print("✖ UNEXPECTED ERROR:", e)


if __name__ == "__main__":
    system = TrafficSystem()

    while True:
        system.run_pipeline()
        time.sleep(5)