# 📖 Documentation Summary & Quick Links

Hệ thống Traffic Density Analysis được tài liệu hóa chi tiết qua các file MD sau:

---

## 📚 Tài Liệu Chính

### 🏠 Project Root

**[README.md](../README.md)** - **Bắt đầu ở đây**
- Tổng quan dự án (2-3 phút đọc)
- Kiến trúc hệ thống & sơ đồ data flow
- Hướng dẫn chạy nhanh (4 component)
- Troubleshooting cơ bản

---

### 🎬 Detection Module

**[docs/DETECTION_MODULE.md](DETECTION_MODULE.md)** - **Để hiểu Detection**
- ✅ Kiến trúc chi tiết (YOLOv9 + ByteTrack)
- ✅ Chi tiết từng component:
  - `detector.py` - YOLOv9 inference
  - `tracker.py` - ByteTrack tracking
  - `zone_manager.py` - Zone & direction detection
  - `event_generator.py` - Event creation
  - `publisher.py` - HTTP POST to Backend
- ✅ Biến môi trường & configuration
- ✅ Vòng lặp chính (main loop)
- ✅ Lệnh chạy 5 mode khác nhau
- ✅ Performance tips & troubleshooting

**Khi nào đọc:**
- Muốn hiểu cách detection hoạt động
- Debug vấn đề nhận diện hoặc theo dõi xe
- Tối ưu performance của detection

---

### 🤖 ML Service Module

**[docs/ML_SERVICE_MODULE.md](ML_SERVICE_MODULE.md)** - **Để hiểu ML & Dự Báo**
- ✅ Pipeline ML hoàn chỉnh:
  - Task 1: Tiền xử lý dữ liệu (preprocess.py)
  - Task 2: Kỹ nghệ đặc trưng (traffic_predictor.py)
  - Task 3: Huấn luyện (train.py)
  - Task 5: Tối ưu pha đèn (phase_optimizer.py)
  - Task 6: Bridge model (light_delta_model.py)
  - Task 9: Đánh giá (evaluate.py)
- ✅ Chi tiết từng file:
  - Input/output schema
  - Parameters & hyperparameters
  - Công thức toán học
  - Metrics (MAE, RMSE, MAPE, R²)
- ✅ 4 lệnh chạy (preprocess → train → evaluate → test)
- ✅ Performance tuning & troubleshooting

**Khi nào đọc:**
- Muốn hiểu dự báo lưu lượng
- Debug sai số cao (MAPE)
- Tune hyperparameters
- Tối ưu pha đèn (pha sáng bao lâu)

---

### 🔧 Backend API

**[backend/README.md](../backend/README.md)** - **Để hiểu API & Database**
- ✅ Vai trò Backend
- ✅ Cấu trúc folder
- ✅ MongoDB schema chi tiết:
  - `vehicle_detections`
  - `traffic_aggregation`
  - `traffic_predictions`
  - `directional_thresholds`
  - `cameras`
- ✅ Endpoints chính (GET/POST):
  - `/health`
  - `/detection`
  - `/raw-data`
  - `/aggregation`
  - `/predict-next`
  - `/cameras`
- ✅ Configuration & Biến môi trường
- ✅ Cách chạy (3 cách)

**Khi nào đọc:**
- Muốn gọi API từ frontend/script
- Debug database issues
- Thay đổi schema hoặc endpoints

---

### 🎨 Frontend Dashboard

**[frontend/README.md](../frontend/README.md)** - **Để hiểu UI/UX**
- ✅ Chức năng dashboard
- ✅ Công nghệ (React 18, Recharts, Tailwind)
- ✅ Cấu trúc folder & components
- ✅ Biến môi trường (.env)
- ✅ Cách gọi Backend API từ React
- ✅ Code examples (components, hooks)
- ✅ CORS configuration
- ✅ Docker deployment

**Khi nào đọc:**
- Muốn phát triển UI/Dashboard
- Debug CORS hoặc API errors
- Deploy frontend (Netlify, Vercel, Docker)

---

### 📋 ML Service README

**[ml_service/README.md](../ml_service/README.md)** - **Độc lập, chi tiết hơn**
- ✅ Tương tự `docs/ML_SERVICE_MODULE.md`
- ✅ Nhưng có thêm:
  - Cây thư mục đầy đủ
  - Từng file chi tiết (preprocess, train, helpers)
  - Direct reference đến code

**Khi nào đọc:**
- Để so sánh thêm từ ML module docs
- Cần reference code cụ thể

---

### 📊 Overview & System Architecture

**[docs/OVERVIEW.md](OVERVIEW.md)** - **Tổng quan chiến lược**
- ✅ Định hướng mục tiêu (strategy)
- ✅ Đặc tả hạ tầng (2 pha đèn)
- ✅ Data pipeline khép kín (4 tầng)
- ⚠️ Ghi chú: File này có vẻ là phiên bản cũ Tiếng Việt

**Khi nào đọc:**
- Lần đầu hiểu mục tiêu dự án
- Nếu muốn hiểu chiến lược pha đèn

---

## 🚀 Lộ Trình Đọc Tài Liệu (Suggested Reading Order)

### 👶 Beginners (Đây là lần đầu)

1. **[README.md](../README.md)** (5 phút)
   - Tổng quan + quick start
   
2. **[docs/DETECTION_MODULE.md](DETECTION_MODULE.md)** (20 phút)
   - Hiểu flow chính: Video → YOLOv9 → Track → Event
   
3. **[docs/ML_SERVICE_MODULE.md](ML_SERVICE_MODULE.md)** (20 phút)
   - Hiểu dự báo: Data → Features → Model → Predictions
   
4. **[backend/README.md](../backend/README.md)** (15 phút)
   - Hiểu API & Database
   
5. **[frontend/README.md](../frontend/README.md)** (10 phút)
   - Hiểu UI

**Tổng cộng: ~70 phút → Full picture của hệ thống**

---

### 🔧 Developers (Làm việc trên code)

1. **README.md** (nhanh)
2. **Tài liệu module bạn đang làm việc:**
   - Detection? → [DETECTION_MODULE.md](DETECTION_MODULE.md)
   - ML? → [ML_SERVICE_MODULE.md](ML_SERVICE_MODULE.md)
   - Backend? → [backend/README.md](../backend/README.md)
   - Frontend? → [frontend/README.md](../frontend/README.md)
3. **Code & inline comments**

---

### 🎯 DevOps / Deployment (Deploy hệ thống)

1. **README.md** (quick start)
2. **Relevant module docs** (Docker sections)
3. **Configuration files** (.env, config.py)

---

## 📌 Quick Reference

### Commands Chính

```bash
# Detection
python -m detection.main
SYNC_MODE=false python -m detection.main  # Async mode

# ML
python ml_service/preprocess.py
python ml_service/train.py
python ml_service/evaluate.py

# Backend
uvicorn backend.main:app --reload --port 8000

# Frontend
npm install && npm start

# Integration System
python integration_system/system_runner.py
```

---

### Key Files & Paths

```
Video → detection/main.py
       ↓
API endpoint: backend/api/detection_routes.py
       ↓
Store: backend/mongo_database.py (vehicle_detections)
       ↓
Aggregate: backend/services/aggregation_service.py (15-min)
       ↓
Predict: ml_service/light_delta_model.py
       ↓
Dashboard: frontend/src/pages/HomePage.jsx
```

---

### Environment Variables

```env
# Detection
TRAFFIC_VIDEO_SOURCE=data/video/cam01-traffic3.mp4
TRAFFIC_MODEL_PATH=detection/pro_models/yolov9_img960_ultimate.pt
TRAFFIC_API_URL=http://127.0.0.1:8000/detection
SYNC_MODE=false

# Backend
MONGO_URI=mongodb://localhost:27017
DB_NAME=traffic_db

# ML
ML_MODEL_DIR=ml_service/model

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

---

## 🆘 Troubleshooting Flowchart

```
❓ Problem?
│
├─ Detection issues?
│  └─ → [DETECTION_MODULE.md](DETECTION_MODULE.md) Troubleshooting section
│
├─ ML/Prediction issues?
│  └─ → [ML_SERVICE_MODULE.md](ML_SERVICE_MODULE.md) Troubleshooting section
│
├─ Backend API errors?
│  └─ → [backend/README.md](../backend/README.md) API section
│
├─ Frontend not loading?
│  └─ → [frontend/README.md](../frontend/README.md) Troubleshooting section
│
└─ General setup issues?
   └─ → [README.md](../README.md) Troubleshooting section
```

---

## 📖 Related Resources

- **YOLOv9:** [GitHub](https://github.com/WongKinYiu/yolov9)
- **ByteTrack:** [Paper & GitHub](https://github.com/ifzhang/ByteTrack)
- **XGBoost:** [Documentation](https://xgboost.readthedocs.io/)
- **FastAPI:** [Documentation](https://fastapi.tiangolo.com/)
- **React:** [Documentation](https://react.dev)
- **MongoDB:** [Documentation](https://docs.mongodb.com/)

---

## ✅ Documentation Checklist

- ✅ README.md - Project overview
- ✅ docs/DETECTION_MODULE.md - Detection deep dive
- ✅ docs/ML_SERVICE_MODULE.md - ML pipeline deep dive
- ✅ backend/README.md - Backend API & DB
- ✅ frontend/README.md - Frontend guide
- ✅ ml_service/README.md - ML module spec
- ✅ docs/OVERVIEW.md - System overview (older version)
- ✅ docs/INDEX.md - This file

---

**Last Updated:** 2026-05-31  
**Maintained By:** Development Team  
**Status:** Complete ✅