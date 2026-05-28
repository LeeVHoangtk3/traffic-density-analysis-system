import os
import sys

# Khắc phục lỗi mã hóa Unicode hiển thị tiếng Việt trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Đảm bảo PYTHONPATH đúng để import backend
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.main import app

def main():
    print("[*] Đang khởi động TestClient cho FastAPI app...")
    client = TestClient(app)
    
    print("[*] Đang gửi yêu cầu GET tới `/api/v1/predict-next?camera_id=cam01`...")
    try:
        response = client.get("/api/v1/predict-next?camera_id=cam01")
        print("\n" + "="*50)
        print(f"Trạng thái HTTP: {response.status_code}")
        print("Nội dung Payload JSON nhận về:")
        import json
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))
        print("="*50)
    except Exception as e:
        print(f"[!] Lỗi khi gửi request: {e}")

if __name__ == '__main__':
    main()
