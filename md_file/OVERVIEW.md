# 📊 Traffic Density Analysis System — Tổng Quan Dự Án

## 1. Giới Thiệu

**Traffic Density Analysis System** là một hệ thống phân tích mật độ giao thông thời gian thực, sử dụng Computer Vision (YOLOv9) để nhận diện và theo dõi phương tiện, kết hợp Machine Learning (XGBoost) để dự báo lưu lượng xe và đề xuất điều chỉnh đèn tín hiệu giao thông. Hệ thống hiện tại bao gồm **5 module chính** giao tiếp với nhau qua REST API.

---

## 2. Kiến Trúc Tổng Thể

```
┌─────────────────┐     HTTP POST /detection     ┌─────────────────┐
│                 │ ──────────────────────────▶  │                 │
│   detection/    │     POST /aggregation/compute│   backend/      │
│  (Module A)     │ ──────────────────────────▶  │  (Module B)     │
│  Detect + Track │                              │  FastAPI + DB   │
└─────────────────┘                              └────────┬────────┘
                                                          │
                        GET /aggregation                  │     GET /raw-data, GET /video
┌─────────────────┐ ◀────────────────────────────         │  ┌─────────────────┐
│ integration_    │     GET /raw-data                     │  │ traffic-frontend│
│ system/         │ ◀────────────────────────────         │  │ (Module E)      │
│ (Module D)      │                              ┌────────┴──┤ React.js Dash   │
│ Tích hợp hệ     │                              │           │                 │
│ thống           │                              │ml_service/└─────────────────┘
└─────────────────┘                              │(Module C) 
                        GET /predict-next        │Dự báo xe &
                    ◀────────────────────────────┤Đèn tín hiệu
                                                 └───────────
```

### Luồng Dữ Liệu Chính

```
Video/Camera ──▶ detection/main.py
                   │
                   ├─▶ Detect (YOLOv9) ──▶ Track (ByteTrack)
                   │
                   ├─▶ Zone crossing? ──▶ EventGenerator (với direction) ──▶ POST /detection ──▶ DB
                   │
                   └─▶ Mỗi 15 phút ──▶ POST /aggregation/compute ──▶ traffic_aggregation (DB)
                                                                          │
                                                                          ▼
                                                          GET /predict-next ──▶ ML Predict (XGBoost)
                                                                          │      (Traffic & Light Delta)
                                                                          ▼
                                                                traffic_predictions (DB)
```

---

## 3. Cây Thư Mục

```text
traffic-density-analysis-system/
│
├── detection/                          # MODULE A: Nhận diện & theo dõi phương tiện
│   ├── main.py                         # Entry point - vòng lặp xử lý video chính
│   ├── camera_engine.py                # Đọc video/camera bằng OpenCV
│   ├── engine/                         # Core engine xử lý Computer Vision
│   │   ├── detector.py                 # YOLOv9 inference - nhận diện phương tiện
│   │   ├── tracker.py                  # ByteTrack - theo dõi phương tiện qua các frame
│   │   ├── counter.py                  # Đếm phương tiện (tổng + theo phút)
│   │   ├── density_estimator.py        # Ước lượng mật độ giao thông (LOW/MEDIUM/HIGH)
│   │   ├── zone_manager.py             # Quản lý vùng đếm (polygon zone) hỗ trợ direction
│   │   ├── event_generator.py          # Tạo event khi xe vượt zone
│   │   └── frame_processor.py          # Tiền xử lý frame (resize)
│   ├── integration/                    # Gửi event đến backend
│   │   └── publisher.py                # Non-blocking HTTP publisher (queue)
│   ├── configs_cameras/                # Cấu hình camera & vùng đếm
│   │   └── cam_01.json                 # Zone polygon cho camera CAM_01
│   ├── pro_models/                     # Trọng số model YOLOv9
│   └── Ultralytics/, ultralytics_yolov9/ # Code core YOLOv9
│
├── backend/                            # MODULE B: Backend API & Database
│   ├── main.py                         # Entry point FastAPI app
│   ├── config.py                       # Cấu hình (database URL, page size, ...)
│   ├── database.py                     # SQLAlchemy engine, schema migration
│   ├── api/                            # API Routes (controllers)
│   │   ├── detection_routes.py, traffic_routes.py, aggregation_routes.py
│   │   ├── prediction_routes.py, camera_routes.py, health_routes.py
│   │   └── video.py                    # Cung cấp file video đầu ra cho Frontend
│   ├── models/                         # SQLAlchemy ORM models
│   │   └── vehicle_detection.py, traffic_aggregation.py, traffic_prediction.py, camera.py
│   ├── schemas/                        # Pydantic schemas
│   └── services/                       # Business logic layer
│       └── prediction_service.py       # Tích hợp cả Model dự báo xe và đề xuất đèn
│
├── ml_service/                         # MODULE C: Machine Learning - Dự báo
│   ├── traffic_predictor.py            # TrafficPredictor (XGBoost) - Dự báo số lượng xe
│   ├── light_delta_model.py            # LightDeltaModel (XGBoost) - Đề xuất thay đổi đèn (delta)
│   ├── label_generator.py              # Tạo nhãn huấn luyện, áp dụng SCALE_FACTOR
│   ├── train.py                        # Huấn luyện cả 2 model
│   ├── predict.py                      # Script test dự báo qua API
│   ├── model.pkl                       # Trọng số model dự báo xe
│   └── light_model.pkl                 # Trọng số model dự báo đèn
│
├── integration_system/                 # MODULE D: Tích hợp hệ thống
│   ├── system_runner.py                # Entry point - chạy pipeline tích hợp
│   ├── congestion_classifier.py        # Phân loại mức ùn tắc local
│   ├── traffic_light_logic.py          # Tối ưu đèn giao thông
│   ├── performance_monitor.py          # Giám sát CPU/RAM
│   ├── scheduler.py                    # Lập lịch gọi aggregation
│   └── pipeline_test.py                # Test pipeline
│
├── traffic-frontend/                   # MODULE E: Frontend Dashboard (React.js)
│   ├── package.json                    # Dependencies (React, Chart.js)
│   └── src/
│       ├── App.js                      # Giao diện chính hiển thị chart và video live
│       └── App.css                     # Styling
│
├── yolov9-cus/                         # Thử nghiệm YOLOv9 custom
├── video_data/                         # Video đầu vào
├── md_file/                            # Tài liệu báo cáo (chứa OVERVIEW.md này)
├── traffic.db                          # SQLite database
└── requirements.txt                    # Danh sách thư viện Python
```

---

## 4. Chi Tiết Từng Module

### 4.1. Module A — `detection/` (Nhận Diện & Theo Dõi)

Đọc video/camera → nhận diện phương tiện → theo dõi → đếm → gửi event đến backend.

**Điểm mới so với các phiên bản trước:**
- Hỗ trợ **`direction`** trong hệ thống (inbound/outbound) lấy từ cấu hình vùng `cam_01.json`.
- Tối ưu VRAM: Định kỳ giải phóng bộ nhớ `torch.cuda.empty_cache()` trong `detector.py`.

| File / Component | Chức năng |
|------------------|-----------|
| `main.py` | Vòng lặp chính, có Dynamic Frame Skip dựa theo mức độ ùn tắc cục bộ (`LOW`, `MEDIUM`, `HIGH`). |
| `Detector` | Load mô hình YOLOv9, áp dụng ngưỡng độ tin cậy riêng biệt cho từng loại xe (ví dụ: mô tô 0.25, ô tô 0.40). |
| `Tracker` | Sử dụng **ByteTrack** (thông qua library `supervision`), với `lost_track_buffer = 90` khung hình để chống mất dấu xe. |
| `ZoneManager` | Trả về thông tin hướng đi (`direction`) khi một phương tiện đi qua. |
| `EventPublisher` | Gửi dữ liệu vào một Queue trong tiến trình nền (Non-blocking) với kích thước tối đa 200 items. |

---

### 4.2. Module B — `backend/` (Backend API & Database)

Lưu trữ và gom nhóm dữ liệu (aggregation), phục vụ API, cũng như tích hợp các logic từ AI Service.

**Cập nhật cấu trúc DB (`traffic_predictions`):**
Bổ sung `suggested_delta` để lưu trữ kết quả đề xuất thay đổi thời gian tín hiệu đèn xanh.

| Endpoint (API) | Chức năng |
|----------------|-----------|
| `POST /detection` | Lưu dữ liệu đếm xe vào `vehicle_detections`. |
| `POST /aggregation/compute` | Gom nhóm dữ liệu 15 phút, tính số lượng và mức độ tắc nghẽn, lưu vào `traffic_aggregation`. |
| `GET /predict-next` | Lấy 5 lần tổng hợp gần nhất, gọi đồng thời **Model 1** (Dự đoán lưu lượng) và **Model 2** (Đề xuất tín hiệu đèn). Trả về lưu lượng và `suggested_delta`. |
| `GET /video/{filename}`| Trả file video MP4 phục vụ tính năng xem trực tiếp trên Frontend. |

---

### 4.3. Module C — `ml_service/` (Machine Learning)

Thay vì 1 mô hình như trước, hệ thống nay bao gồm 2 mô hình XGBoost.

- **`TrafficPredictor`**: Dự đoán tổng số xe cho 15 phút tới.
- **`LightDeltaModel`**: Dựa vào `inbound_count` hiện tại và `queue_proxy` (độ chênh lệch lượng xe so với khung thời gian trước) để đưa ra chỉ số `suggested_delta` (-30s đến +45s) để thay đổi thời lượng đèn xanh.
- **`label_generator.py`**: Áp dụng cơ chế **SCALE_FACTOR** (~2.21) trên file CSV để khớp dữ liệu huấn luyện mẫu với phân phối thực tế được ghi nhận ở Backend, giúp dự báo sát với luồng dữ liệu thật.

---

### 4.4. Module D — `integration_system/` (Tích Hợp Hệ Thống)

Chạy ngầm liên tục với vòng lặp 5 giây, kiểm tra tình trạng kết nối tới backend.
Dùng `CongestionClassifier` để đánh giá cục bộ dữ liệu `vehicle_count` trả về từ `/aggregation`, và sử dụng `TrafficLightOptimizer` để in ra các cấu hình điều tiết cơ sở. Đồng thời theo dõi RAM/CPU qua `PerformanceMonitor`.

---

### 4.5. Module E — `traffic-frontend/` (React Dashboard)

Giao diện quan sát thời gian thực.
- Kéo liên tục thông tin từ `GET /raw-data`.
- Hiển thị tổng số lượng phương tiện theo loại.
- Hiển thị biểu đồ (Line chart bằng Chart.js) so sánh dữ liệu thực tế và AI Prediction.
- Tích hợp thẻ `<video>` gọi nguồn API tới `/video/output.mp4` để chiếu song song quá trình Detection.

---

## 5. Công Nghệ & Thư Viện

| Thành phần | Công nghệ chính |
|------------|-----------------|
| **AI / Computer Vision** | PyTorch, OpenCV, YOLOv9, Supervision (ByteTrack) |
| **Backend & DB** | FastAPI, Uvicorn, SQLAlchemy, SQLite (hoặc PostgreSQL), Pydantic |
| **Machine Learning** | XGBoost, Scikit-learn, Pandas, Joblib |
| **Frontend** | React 19, Chart.js, React-Chartjs-2 |
| **Tích hợp/Hệ thống** | psutil, requests |

---

## 6. Sơ Đồ Database (Cập nhật)

**Bảng `traffic_predictions` hiện tại:**
- `id` (INTEGER, PK)
- `camera_id` (TEXT)
- `predicted_density` (FLOAT) - Số xe dự đoán
- `suggested_delta` (FLOAT) - Số giây đề xuất cộng/trừ vào đèn xanh
- `horizon_minutes` (INTEGER) - Mặc định 15
- `source` (TEXT) - `ml_service` hoặc `fallback`
- `timestamp` (DATETIME)

---

## 7. Hướng Dẫn Chạy Toàn Hệ Thống

Bạn cần mở nhiều Terminal/Command Prompt.

**Terminal 1: Khởi động Backend**
```bash
# Bắt buộc chạy đầu tiên
uvicorn backend.main:app --reload
```

**Terminal 2: Khởi động hệ thống Detection**
```bash
python -m detection.main
```
> *Sẽ đọc file video đầu vào, xử lý, và liên tục đẩy event vào Backend.*

**Terminal 3: Khởi động Frontend Dashboard**
```bash
cd traffic-frontend
npm install
npm start
```

**Terminal 4: Khởi động Integration System**
```bash
python integration_system/system_runner.py
```
> *Hệ thống sẽ chạy chu kỳ và gọi các hàm tính toán, dự đoán AI, in ra console kết quả phân tích.*

**Tùy chọn: Đào tạo lại Model AI**
```bash
python -m ml_service.train
```

## 8. Chi Tiết Các File / Class Chính

### 8.1. `detection/engine/` (Core Computer Vision)
*   **`detector.py (YOLOv9Detector)`**: Khởi tạo model YOLOv9 từ trọng số `pro_models/yolov9-c.pt` (hoặc `e.pt`). Hỗ trợ cấu hình thiết bị (`mps`/`cuda`/`cpu`). Hàm `detect()` nhận frame ảnh, trả về bounding boxes, confidences, và class IDs với ngưỡng tin cậy riêng biệt (vd: `{"motorcycle": 0.25, "car": 0.40, "bus": 0.45, "truck": 0.45}`).
*   **`tracker.py (VehicleTracker)`**: Dùng `supervision.ByteTrack`. Hàm `update()` nhận detection results và gán/duy trì ID cho từng phương tiện. `lost_track_buffer=90` giúp giữ tracking kể cả khi xe bị che khuất trong vài chục frame.
*   **`zone_manager.py (ZoneManager)`**: Xử lý vùng đếm (PolygonZone), hỗ trợ xác định `direction` (hướng xe). Khi xe giao cắt với polygon, `ZoneManager` xác định hướng đi dựa trên toạ độ y1, y2, trả về `inbound` hoặc `outbound`.
*   **`density_estimator.py (DensityEstimator)`**: Đoán mức độ ùn tắc cục bộ (`LOW`, `MEDIUM`, `HIGH`) dựa trên số lượng bounding box hiện diện trên một frame.
*   **`event_generator.py (EventGenerator)`**: Chuyển đổi dữ liệu tracking thành một data object `DetectionEvent` chuẩn hóa (class xe, camera_id, timestamp, direction).
*   **`counter.py` & `frame_processor.py`**: Quản lý bộ đếm tổng/chi tiết, tính FPS và tiền xử lý (resize, padding khung hình).

### 8.2. `backend/models/` (SQLAlchemy Models)
*   **`camera.py (Camera)`**: Thông tin camera (ID, location, status, rtsp_url).
*   **`vehicle_detection.py (VehicleDetection)`**: Bảng `vehicle_detections` lưu trữ log phát hiện từng phương tiện (`vehicle_type`, `direction`, `speed`, `timestamp`).
*   **`traffic_aggregation.py (TrafficAggregation)`**: Bảng `traffic_aggregation`, chứa dữ liệu đã được gom nhóm (thường là 15 phút) (`period_start`, `period_end`, `total_vehicles`, `congestion_level`, `avg_speed`, `inbound_count`, `outbound_count`).
*   **`traffic_prediction.py (TrafficPrediction)`**: Bảng `traffic_predictions`, lưu trữ kết quả dự báo từ ML (`predicted_density`, `suggested_delta`, `horizon_minutes`).

### 8.3. `backend/api/` (API Routes)
*   **`detection_routes.py`**: `POST /detection`, nhận payload từ Module Detection. Có thể hỗ trợ batch insert để tối ưu lưu lượng database khi lượng xe đông.
*   **`aggregation_routes.py`**: `POST /aggregation/compute`, tính toán dữ liệu từ `vehicle_detections` và lưu thành 1 dòng trong `traffic_aggregation`. Thường được gọi bởi module `scheduler`.
*   **`prediction_routes.py`**: `GET /predict-next` load 2 mô hình XGBoost (`model.pkl`, `light_model.pkl`) và tính toán nội suy. Trả về JSON với `predicted_density`, `suggested_delta_seconds`.
*   **`video.py`**: Endpoint `/video/output.mp4` stream file trực tiếp bằng `StreamingResponse` với tính năng hỗ trợ byte-ranges (`206 Partial Content`), phục vụ thẻ `<video>` HTML5 của React Dashboard.

### 8.4. `integration_system/` (Background Workers)
*   **`system_runner.py`**: Chạy dưới dạng Daemon, loop định kỳ (ví dụ mỗi 5s).
*   **`scheduler.py`**: Tự động nhận diện mốc thời gian (XX:00, XX:15, XX:30, XX:45) để kích hoạt API Aggregation.
*   **`traffic_light_logic.py (TrafficLightOptimizer)`**: Dựa trên input `suggested_delta` từ Prediction API để ra quyết định điều chỉnh pha đèn xanh/đỏ cụ thể.

---

## 9. Luồng Hoạt Động (Flows) Cụ Thể

### Flow 1: Nhận Diện & Tracking (Real-time Video)
1. **CameraEngine** đọc frame từ Video/Camera (ví dụ với tốc độ 30 FPS).
2. Tại `main.py` của module detection, dựa vào `congestion_level` (LOW/MEDIUM/HIGH), hệ thống áp dụng cơ chế **Dynamic Frame Skip** (Ví dụ nếu HIGH thì bỏ qua 2/3 số frame để tránh quá tải CPU/GPU).
3. Frame đi qua `YOLOv9Detector` → Bounding Boxes.
4. Bounding Boxes đi qua `VehicleTracker` (ByteTrack) → Tracker IDs (vd: `#125`).
5. Nếu Tracker `#125` cắt qua vạch khai báo trong `cam_01.json`, `ZoneManager` kích hoạt sự kiện đếm, đính kèm thông tin `direction` (inbound/outbound).
6. `EventGenerator` gói sự kiện, truyền cho `EventPublisher`.
7. `EventPublisher` lưu event vào một `Queue` cục bộ. Một luồng chạy ngầm sẽ pop dữ liệu ra và bắn HTTP Request (`POST /detection`) (Non-blocking I/O).

### Flow 2: Tổng Hợp Dữ Liệu & Machine Learning (15 phút/lần)
1. `scheduler.py` phát hiện thời điểm tròn mốc 15 phút và gọi `POST /aggregation/compute?minutes=15`.
2. Backend (FastAPI) thực hiện `SELECT COUNT`, `SUM`, gom dữ liệu theo hướng từ `vehicle_detections` (với `timestamp` trong 15 phút vừa qua).
3. Record được lưu vào `traffic_aggregation`.
4. Sau đó `GET /predict-next` được gọi.
5. Service Backend sẽ kéo 5 khoảng thời gian gần nhất (lag=5) đưa cho 2 model XGBoost:
   - **XGBoost 1**: Tính toán luồng giao thông 15 phút tiếp theo → `predicted_density`.
   - **XGBoost 2**: Tính toán pha đèn cần bù trừ → `suggested_delta`.
6. Kết quả ghi vào `traffic_predictions` và trả về JSON cho Frontend.

### Flow 3: Frontend Hiển Thị (Real-time Dashboard)
1. Ứng dụng **React.js** liên tục poll dữ liệu qua các API `GET /raw-data` và `GET /prediction`.
2. Biểu đồ **Chart.js** vẽ đường cong thực tế và dự báo lên màn hình, so sánh độ chênh lệch.
3. Thẻ `<video>` stream trực tiếp từ `GET /video/output.mp4` duy trì hình ảnh thực tế với bounding box được vẽ chồng (overlay) từ backend, giúp người vận hành có góc nhìn tổng thể nhất.

---

> **Ghi chú**: OVERVIEW này được đồng bộ với trạng thái chi tiết nhất của mã nguồn bao gồm việc làm rõ module, class chính, luồng chạy tracking, ML, API và kiến trúc Frontend mới nhất. Cập nhật lần cuối: 01/05/2026.
