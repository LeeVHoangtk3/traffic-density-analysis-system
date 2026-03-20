import requests
import time
import random

BACKEND_URL = "http://127.0.0.1:8000/aggregation"


def run_pipeline():

    print("=== START PIPELINE TEST ===")

    while True:

        try:
            vehicle_count = random.randint(5, 50)
            print("\n[1] Detection result:", vehicle_count)
            print("[2] Sending data to Backend...")

            response = requests.get(
                BACKEND_URL,
                params={"vehicle_count": vehicle_count}
            )
            if response.status_code == 200:

                data = response.json()

                print("[3] Backend response:", data)

                print(
                    f"[4] Traffic Level → {data['congestion_level']}"
                )

                print("✔ Pipeline OK")

            else:
                print("✖ Backend error:", response.status_code)

        except Exception as e:
            print("✖ Pipeline error:", e)

        time.sleep(5)


if __name__ == "__main__":
    run_pipeline()