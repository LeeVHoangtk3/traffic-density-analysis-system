# integration/scheduler.py

import time
import requests

class Scheduler:

    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.ml_url = "http://localhost:8001"

    def run(self):

        while True:

            try:

                # gọi aggregation
                response = requests.get(
                    f"{self.backend_url}/aggregation"
                )

                data = response.json()

                # gọi ML prediction
                pred = requests.get(
                    f"{self.ml_url}/predict-next"
                )

                prediction = pred.json()

                print("Aggregation:", data)
                print("Prediction:", prediction)

            except Exception as e:
                print("Scheduler error:", e)

            time.sleep(60)