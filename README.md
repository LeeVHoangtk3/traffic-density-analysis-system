# Cách chạy dự án chuẩn thực tế (15 phút/lần)

🖥️ Terminal 1: Bật Server Backend
source .venv/bin/activate
uvicorn backend.main:app --reload

📷 Terminal 2: Bật Camera Phân tích
source .venv/bin/activate
python -m detection.main
(Hệ thống sẽ tự động chốt số xe mỗi 15 phút một lần)

🔮 Terminal 3: Dự báo kết quả
source .venv/bin/activate
python -m ml_service.predict
(Chạy sau khi Terminal 2 đã báo chốt số ít nhất 3 lần - khoảng 45 phút)
