"""
ml_service/predict.py
Thay vì dùng dữ liệu hard-code, script này gọi API backend thực
để lấy kết quả dự báo dựa trên dữ liệu đếm xe thực từ video.

Yêu cầu: backend đang chạy tại TRAFFIC_API_URL (mặc định localhost:8000)
Chạy: python -m ml_service.predict
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
    print(f"[*] Đang gọi API dự báo: {url}")
    print(f"    Camera ID : {CAMERA_ID}")
    print("-" * 40)

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.ConnectionError:
        print(
            "❌ Lỗi kết nối: Không thể kết nối tới backend.\n"
            f"   Hãy chắc chắn backend đang chạy tại {API_BASE}\n"
            "   Lệnh khởi động: uvicorn backend.main:app --reload"
        )
        sys.exit(1)

    if response.status_code == 422:
        detail = response.json().get("detail", "")
        print(f"⚠️  Chưa đủ dữ liệu thực để dự báo:\n   {detail}")
        print("\n   → Hãy chạy detection trước để tích lũy dữ liệu:")
        print("     python -m detection.main")
        sys.exit(1)

    if response.status_code != 200:
        print(f"❌ Lỗi API (HTTP {response.status_code}): {response.text}")
        sys.exit(1)

    data = response.json()
    print(f"📷 Camera        : {data['camera_id']}")
    print(f"🔮 Dự báo 15p tới: {data['predicted_count']} xe")
    print(f"🕐 Thời điểm dự báo: {data['predicted_at']}")
    print("-" * 40)


if __name__ == "__main__":
    main()