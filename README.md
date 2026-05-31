# 🚦 Hệ Thống Phân Tích Mật Độ Giao Thông & Điều Phối Pha Đèn Tín Hiệu Động

## 📋 Tổng Quan Dự Án

**Traffic Density Analysis System** là một hệ thống AI toàn diện được thiết kế để:
- ✅ **Nhận diện & theo dõi xe** từ camera video sử dụng YOLOv9
- ✅ **Tổng hợp dữ liệu lưu lượng** theo hướng di chuyển (thẳng, rẽ trái, rẽ phải) trong khoảng 15 phút
- ✅ **Dự báo lưu lượng** cho 15 phút tiếp theo bằng mô hình XGBoost
- ✅ **Tối ưu hóa phân bổ thời gian xanh** cho đèn tín hiệu dựa trên dự báo lưu lượng
- ✅ **Cung cấp dashboard thời gian thực** hiển thị trạng thái giao thông và kiến nghị pha đèn

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Dashboard (React)                   │
│           Hiển thị mật độ, dự báo, trạng thái đèn              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/WebSocket
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│          Backend API (FastAPI + MongoDB)                         │
│  - POST /detection       (nhận event từ detection)              │
│  - POST /aggregation/compute  (tổng hợp 15 phút)              │
│  - GET /predict-next     (gọi dự báo ML)                       │
│  - GET /aggregation      (lấy dữ liệu tổng hợp)                │
│  - GET /raw-data         (lấy dữ liệu thô)                     │
└────┬──────────────────────────────────────────────────────────┬─┘
     │                                                             │
     ↓ nhận event                                            lấy dự báo ↓
┌─────────────────────────────────────┐       ┌────────────────────────────┐
│  Detection Module                   │       │  ML Service                │
│  (YOLOv9 + ByteTrack)              │       │  (XGBoost Regressor)       │
│  - detect.py (YOLO inference)      │       │  - train.py                │
│  - tracker.py (ByteTrack)          │       │  - traffic_predictor.py    │
│  - density_estimator.py            │       │  - phase_optimizer.py      │
│  - event_generator.py              │       │  - light_delta_model.py    │
│  - zone_manager.py                 │       │                            │
│  Output: vehicle_detections        │       │  Output: traffic_predictions│
└──────────────────────────────────────┘     └────────────────────────────┘
```

---

## 🚀 Hướng Dẫn Chạy Dự Án

### Chuẩn Bị Môi Trường

```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (Linux/Mac)
source .venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 1️⃣ Chạy Backend API

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Endpoints chính:**
- `GET /health` - Kiểm tra trạng thái API & MongoDB
- `POST /detection` - Nhận sự kiện nhận diện từ detection module
- `GET /raw-data` - Truy vấn dữ liệu thô xe qua vạch (filter: camera_id, direction, time range)
- `GET /aggregation` - Lấy mật độ/lưu lượng 15 phút gần nhất
- `POST /aggregation/compute` - Tính toán tổng hợp (gọi từ detection)
- `GET /predict-next` - Lấy dự báo 15 phút tiếp theo
- `GET /cameras` - Danh sách camera
- `POST /cameras` - Thêm camera mới

### 2️⃣ Chạy Detection Module

```bash
# Chế độ đơn giản (hiển thị cửa sổ)
python -m detection.main

# Chế độ async (video mượt mà hơn)
SYNC_MODE=false python -m detection.main

# Chế độ headless (không hiển thị)
NO_DISPLAY=true python -m detection.main

# Với file log cảnh báo mật độ cao
ALERT_LOG=alerts.csv python -m detection.main
```

**Quy trình:**
1. Đọc video từ `data/video/` hoặc webcam
2. Nhận diện xe bằng YOLOv9 (4 class: bus, car, motorcycle, truck)
3. Theo dõi xe với ByteTrack
4. Tạo sự kiện khi xe qua vạch (gửi `POST /detection`)
5. Tự động gọi `POST /aggregation/compute` mỗi 15 phút
6. Xuất video đầu ra có vẽ bbox và HUD giám sát

### 3️⃣ Huấn Luyện Mô Hình ML

```bash
# Bước 1: Tiền xử lý dữ liệu
python ml_service/preprocess.py

# Bước 2: Huấn luyện 3 mô hình XGBoost (thẳng, trái, phải)
python ml_service/train.py

# Bước 3: Đánh giá mô hình (MAE, RMSE, MAPE)
python ml_service/evaluate.py
```

**Đầu vào:** `data/ml/Automated_Traffic_Volume_Counts_20260521.csv`  
**Đầu ra:** 3 mô hình `ml_service/model/model_*.pkl` + báo cáo lỗi

### 4️⃣ Khởi Chạy Tích Hợp Toàn Bộ Hệ Thống (Một-cho-Tất-cả)

```bash
python backend/system_runner.py
```

**Chức năng:**
- Tự động khởi chạy và quản lý đồng thời cả 3 thành phần: *Backend (FastAPI)*, *Detection (YOLO)*, và *Frontend (React)*.
- Giúp vận hành nhanh chóng toàn bộ dự án bằng 1 lệnh duy nhất.

### 5️⃣ Khởi Tạo Dữ Liệu

```bash
# Tạo dữ liệu mẫu cho cameras, aggregation, predictions
python -m backend.seed_data
```

---

## 📁 Cấu Trúc Thư Mục

```
.
├── backend/                    # FastAPI + MongoDB
│   ├── api/                    # Các routes (detection, aggregation, prediction...)
│   ├── services/               # Logic nghiệp vụ
│   ├── schemas/                # Pydantic schemas
│   ├── config.py              # Cấu hình DB, API
│   ├── main.py                # Entry point FastAPI
│   └── README.md              # Tài liệu backend chi tiết
│
├── detection/                  # Module A: Nhận diện & theo dõi
│   ├── main.py                # Entry point
│   ├── engine/
│   │   ├── detector.py        # YOLOv9 inference
│   │   ├── tracker.py         # ByteTrack
│   │   ├── density_estimator.py
│   │   ├── event_generator.py
│   │   ├── zone_manager.py
│   │   └── ...
│   ├── pro_models/            # Trọng số YOLOv9 (.pt)
│   ├── ultralytics_yolov9/    # YOLOv9 core code
│   └── configs_cameras/       # Cấu hình zone/camera
│
├── ml_service/                # Module B: Dự báo & tối ưu
│   ├── train.py              # Huấn luyện XGBoost
│   ├── preprocess.py         # Tiền xử lý dữ liệu
│   ├── traffic_predictor.py  # Kỹ nghệ đặc trưng
│   ├── phase_optimizer.py    # Tối ưu pha đèn
│   ├── light_delta_model.py  # Bridge dự báo ↔ điều phối
│   ├── evaluate.py           # Đánh giá mô hình
│   ├── model/                # Trọng số pkl
│   ├── data/                 # Dữ liệu training/validation
│   └── README.md             # Tài liệu ML chi tiết
│
├── backend/                  # FastAPI Backend & Orchestrator
│   ├── system_runner.py      # Trình điều phối chạy tích hợp hệ thống (Một-cho-Tất-cả)
│   ├── api/                  # Các routes API phục vụ frontend
│   └── ...
│
├── frontend/                  # React Dashboard
│   ├── src/
│   ├── public/
│   └── package.json
│
├── data/
│   ├── ml/                   # Dữ liệu training
│   ├── video/                # Video test
│   └── output/               # Kết quả detection
│
├── docs/                      # Tài liệu kỹ thuật
│   ├── DETECTION_MODULE.md   # Chi tiết module detection
│   ├── ML_SERVICE_MODULE.md  # Chi tiết module ML
│   └── OVERVIEW.md
│
├── requirements.txt           # Dependencies Python
├── README.md                  # File này
└── colab_run.ipynb           # Notebook Google Colab
```

---

## 🔄 Luồng Dữ Liệu Toàn Hệ Thống

```
Video Input (MP4/Webcam)
         ↓
  [Detection.main]
  - YOLOv9 detect
  - ByteTrack
  - Event generate
         ↓
  POST /detection → Backend
         ↓
  [MongoDB] vehicle_detections
         ↓
  POST /aggregation/compute (tự động mỗi 15 phút)
         ↓
  [MongoDB] traffic_aggregation
         ↓
  GET /predict-next (gọi từ integration_system)
         ↓
  [ML Service]
  - Load features
  - Run 3 XGBoost models
  - Optimize phase timing
         ↓
  [MongoDB] traffic_predictions
         ↓
  [Integration System]
  - Apply traffic light logic
  - Generate delta adjustment
         ↓
  light_status.json
         ↓
  Frontend Dashboard
```

---

## 📚 Tài Liệu Chi Tiết

- **[docs/DETECTION_MODULE.md](docs/DETECTION_MODULE.md)** - Kiến trúc, algorithm, tham số detection
- **[docs/ML_SERVICE_MODULE.md](docs/ML_SERVICE_MODULE.md)** - Tiền xử lý, training, dự báo
- **[backend/README.md](backend/README.md)** - API spec, MongoDB schema, endpoints
- **[ml_service/README.md](ml_service/README.md)** - Chi tiết hàm, đầu vào/ra, hyperparameter
- **[frontend/README.md](frontend/README.md)** - React components, build/deploy

---

## ⚙️ Biến Môi Trường

Tạo file `.env` trong thư mục gốc:

```env
# Backend
MONGO_URI=mongodb://localhost:27017
DB_NAME=traffic_db
TRAFFIC_API_URL=http://127.0.0.1:8000

# Detection
TRAFFIC_VIDEO_SOURCE=data/video/cam01-traffic3.mp4
TRAFFIC_MODEL_PATH=detection/pro_models/yolov9_img960_ultimate.pt
CONF_THRESHOLD=0.40
SYNC_MODE=false

# ML Service
ML_MODEL_DIR=ml_service/model
```

---

## 🐛 Troubleshooting

| Lỗi | Giải pháp |
|-----|---------|
| `CUDA out of memory` | Giảm `TARGET_WIDTH` hoặc bật `SYNC_MODE=true` |
| `MongoDB connection failed` | Kiểm tra MongoDB service chạy: `mongod` |
| `Model file not found` | Đảm bảo file `.pt` tồn tại ở `pro_models/` |
| `Import error: ultralytics` | Cài: `pip install ultralytics supervision` |

---

## 👨‍💼 Thông Tin Liên Hệ & Đóng Góp

Nếu có câu hỏi hoặc muốn đóng góp, vui lòng tạo Issue hoặc Pull Request.

**Cập nhật lần cuối:** 2026-05-31
