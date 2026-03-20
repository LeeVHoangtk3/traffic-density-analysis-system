import requests
import time

BACKEND_AGG_URL = "http://127.0.0.1:8000/aggregation"
BACKEND_RAW_URL = "http://127.0.0.1:8000/raw-data"


class TrafficSystem:
    def __init__(self):
        from congestion_classifier import CongestionClassifier
        from traffic_light_logic import TrafficLightOptimizer
        from performance_monitor import PerformanceMonitor

        self.classifier = CongestionClassifier()
        self.optimizer = TrafficLightOptimizer()
        self.monitor = PerformanceMonitor()

    def run_pipeline(self):
        try:
            raw_res = requests.get(BACKEND_RAW_URL)

            if raw_res.status_code != 200:
                print(" Cannot get raw data")
                return

            vehicle_count = raw_res.json()["vehicle_count"]
            print("\n[1] Vehicle count (from backend):", vehicle_count)

            response = requests.get(
                BACKEND_AGG_URL,
                params={"vehicle_count": vehicle_count}
            )

            if response.status_code != 200:
                print(" Backend aggregation error:", response.status_code)
                return

            data = response.json()
            level = data["congestion_level"]

            print("[2] Congestion level (Backend):", level)

            local_level = self.classifier.classify(vehicle_count)
            print("[3] Local classification:", local_level)

            light = self.optimizer.optimize(level)
            print("[4] Traffic light:", light)

            perf = self.monitor.monitor()
            print("[5] Performance:", perf)

            print(" System running OK")

        except Exception as e:
            print(" Pipeline error:", e)


if __name__ == "__main__":
    system = TrafficSystem()

    while True:
        system.run_pipeline()
        time.sleep(5)