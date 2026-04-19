"""
ml_service/predict.py
Goi API backend de lay ket qua du bao dua tren du lieu thuc da duoc luu.

Yeu cau: backend dang chay tai TRAFFIC_API_URL (mac dinh localhost:8000)
Chay: python -m ml_service.predict
"""

import os
import sys

import requests

API_BASE = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000")
CAMERA_ID = os.getenv("TRAFFIC_CAMERA_ID", "CAM_01")


def main():
    url = f"{API_BASE}/predict-next"
    params = {"camera_id": CAMERA_ID}

    print("-" * 40)
    print(f"[*] Dang goi API du bao: {url}")
    print(f"    Camera ID : {CAMERA_ID}")
    print("-" * 40)

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.ConnectionError:
        print(
            "Khong the ket noi toi backend.\n"
            f"Hãy chac chan backend dang chay tai {API_BASE}\n"
            "Lenh khoi dong: uvicorn backend.main:app --reload"
        )
        sys.exit(1)

    if response.status_code == 422:
        detail = response.json().get("detail", "")
        print(f"Chua du du lieu thuc de du bao:\n  {detail}")
        print("\nHay chay detection truoc de tich luy du lieu:")
        print("  python -m detection.main")
        sys.exit(1)

    if response.status_code != 200:
        print(f"Loi API (HTTP {response.status_code}): {response.text}")
        sys.exit(1)

    data = response.json()
    print(f"Camera             : {data['camera_id']}")
    print(f"Gia tri du bao     : {data['predicted_density']}")
    print(f"Khung du bao       : {data['horizon_minutes']} phut")
    print(f"Nguon du bao       : {data['source']}")
    print(f"Thoi diem du bao   : {data['timestamp']}")
    print("-" * 40)


if __name__ == "__main__":
    main()
