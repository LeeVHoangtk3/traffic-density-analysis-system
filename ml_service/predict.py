"""
ml_service/predict.py
Goi API backend de lay ket qua du bao dua tren du lieu thuc da duoc luu.

Yeu cau: backend dang chay tai TRAFFIC_API_URL (mac dinh localhost:8000)
Chay: python -m ml_service.predict
"""

import os
import sys
from datetime import datetime

import requests

API_BASE = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000")
CAMERA_ID = os.getenv("TRAFFIC_CAMERA_ID", "CAM_01")


def calculate_green_light_time(predicted_density: float, avg_density: float) -> int:
    base_time = 45

    # tránh chia cho 0
    if avg_density <= 0:
        avg_density = predicted_density if predicted_density > 0 else 1

    delta = ((predicted_density - avg_density) / avg_density) * 100

    print(f">>> avg={avg_density}, predicted={predicted_density}, delta={delta}")

    if delta < 0:
        adjustment = max(((delta // 10) * 5), -15)
    else:
        adjustment = min(((delta // 10) * 5), 45)

    return int(base_time + adjustment)


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

    # 👉 LẤY AVG TỪ BACKEND (nếu có)
    avg_density = data.get("avg_density")

    # fallback nếu backend chưa trả
    if avg_density is None:
        print("[!] Backend chưa trả avg_density → fallback tạm = predicted")
        avg_density = data["predicted_density"]

    # tính đèn xanh
    green_light_time = calculate_green_light_time(
        data['predicted_density'],
        avg_density
    )

    print(f"Camera             : {data['camera_id']}")
    print(f"Gia tri du bao     : {data['predicted_density']}")
    print(f"Muc do mat do      : {data.get('predicted_congestion_level', 'N/A')}")
    print(f"Khung du bao       : {data['horizon_minutes']} phut")
    print(f"Nguon du bao       : {data['source']}")
    print(f"Thoi gian den xanh : {green_light_time} giay")
    print(f"Thoi diem du bao   : {data['timestamp']}")
    print("-" * 40)

    # POST lên backend
    try:
        post_url = f"{API_BASE}/predictions/history"

        timestamp = data.get("timestamp")
        try:
            timestamp = datetime.fromisoformat(timestamp).isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()

        post_data = {
            "camera_id": data.get('camera_id', CAMERA_ID),
            "predicted_density": float(data['predicted_density']),
            "predicted_congestion_level": data.get('predicted_congestion_level'),
            "horizon_minutes": int(data.get('horizon_minutes', 15)),
            "source": data.get('source', 'ml_service'),
            "time_green_light": int(green_light_time),
            "timestamp": timestamp
        }

        print(f"\n[*] Đang gửi POST lên: {post_url}")
        print(f"    Dữ liệu: {post_data}")

        post_response = requests.post(post_url, json=post_data, timeout=5)

        print(f"    Response Status: {post_response.status_code}")

        if post_response.status_code in [200, 201]:
            print("[+] Thời gian đèn xanh đã được lưu lên backend")
            print(f"    Chi tiết: {post_response.json()}")
        else:
            print(f"[!] Không thể lưu thời gian đèn xanh (HTTP {post_response.status_code})")
            print(f"    Response: {post_response.text}")

    except requests.RequestException as e:
        print(f"[!] Lỗi khi gửi thời gian đèn xanh: {e}")


if __name__ == "__main__":
    main()