# 📊 Traffic Density Analysis System — Tổng Quan & Tài Liệu Kiến Trúc

Tài liệu này là nguồn chân lý (Source of Truth) kết hợp cung cấp cái nhìn tổng quan về kiến trúc luồng dữ liệu lẫn phân tích chuyên sâu vào chức năng cốt lõi của từng file riêng biệt và thư viện công nghệ trong hệ thống.

---

## 1. Giới Thiệu Tổng Quan

**Traffic Density Analysis System** là một hệ thống phân tích mật độ giao thông thời gian thực (Full-stack AI System), sử dụng Computer Vision (YOLOv9) để nhận diện và theo dõi phương tiện, kết hợp Machine Learning (XGBoost) để dự báo lưu lượng xe và đề xuất điều chỉnh đèn tín hiệu giao thông. Hệ thống hiện tại bao gồm **5 module chính** giao tiếp với nhau qua REST API và sử dụng cơ sở dữ liệu **MongoDB**.

### Công Nghệ Sử Dụng (Tech Stack)
*   **Computer Vision**: `PyTorch`, `OpenCV`, `YOLOv9` (Object Detection), `supervision` (ByteTrack - Tracking, PolygonZone).
*   **Backend & Cơ Sở Dữ Liệu**: `FastAPI`, `Uvicorn`, `Pydantic` (Validation), `MongoDB` (`pymongo` - Lưu trữ NoSQL, aggregation framework).
*   **Machine Learning**: `XGBoost` (Gradient Boosting Trees), `scikit-learn`, `pandas`, `joblib`.
*   **Tích Hợp & Vận Hành**: `psutil` (giám sát tài nguyên), `requests` (giao tiếp HTTP).
*   **Frontend**: `React 19` (JavaScript thuần), `Chart.js`, `react-chartjs-2`.

---

## 2. Kiến Trúc Tổng Thể

```text
┌─────────────────┐     HTTP POST /detection     ┌─────────────────┐
│                 │ ──────────────────────────▶  │                 │
│   detection/    │     POST /aggregation/compute│   backend/      │
│  (Module A)     │ ──────────────────────────▶  │  (Module B)     │
│  Detect + Track │                              │  FastAPI + Mongo│
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

```text
Video/Camera ──▶ detection/main.py
                   │
                   ├─▶ Detect (YOLOv9) ──▶ Track (ByteTrack)
                   │
                   ├─▶ Zone crossing? ──▶ EventGenerator (với direction) ──▶ POST /detection ──▶ MongoDB
                   │
                   └─▶ Mỗi 15 phút ──▶ POST /aggregation/compute ──▶ MongoDB (traffic_aggregation)
                                                                          │
                                                                          ▼
                                                          GET /predict-next ──▶ ML Predict (XGBoost)
                                                                          │      (Traffic & Light Delta)
                                                                          ▼
                                                                MongoDB (traffic_predictions)
```

---

## 3. Cây Thư Mục Toàn Dữ Án

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
│   ├── pro_models/                     # Trọng số model YOLOv9
│   └── Ultralytics/, ultralytics_yolov9/ # Code core YOLOv9
│
├── backend/                            # MODULE B: Backend API & MongoDB
│   ├── main.py                         # Entry point FastAPI app
│   ├── config.py                       # Cấu hình (MongoDB URL, page size, ...)
│   ├── mongo_database.py               # Kết nối PyMongo, quản lý schema index
│   ├── seed_data.py                    # Khởi tạo dữ liệu mẫu cho hệ thống
│   ├── api/                            # API Routes (controllers)
│   │   ├── detection_routes.py, traffic_routes.py, aggregation_routes.py
│   │   ├── prediction_routes.py, camera_routes.py, health_routes.py
│   │   └── video.py                    # Cung cấp file video đầu ra cho Frontend
│   ├── schemas/                        # Pydantic schemas validation
│   └── services/                       # Business logic layer
│
├── ml_service/                         # MODULE C: Machine Learning - Dự báo
│   ├── traffic_predictor.py            # TrafficPredictor (XGBoost) - Dự báo số lượng xe
│   ├── light_delta_model.py            # LightDeltaModel (XGBoost) - Đề xuất thay đổi đèn (delta)
│   ├── train.py                        # Huấn luyện cả 2 model
│   ├── predict.py                      # Script test dự báo qua API
│   ├── model.pkl                       # Trọng số model dự báo xe
│   └── light_model.pkl                 # Trọng số model dự báo đèn
│
├── integration_system/                 # MODULE D: Tích hợp hệ thống
│   ├── system_runner.py                # Entry point - chạy pipeline tích hợp
│   ├── congestion_classifier.py        # Phân loại mức ùn tắc local
│   ├── traffic_light_logic.py          # Tối ưu đèn giao thông
│   ├── delta_applier.py                # Áp dụng delta từ ML Model vào baseline_green của camera
│   ├── direction_router.py             # Ánh xạ camera_id tới pha đèn tín hiệu (phase)
│   ├── performance_monitor.py          # Giám sát CPU/RAM
│   └── scheduler.py                    # Lập lịch gọi aggregation định kỳ
│
├── traffic-frontend/                   # MODULE E: Frontend Dashboard (React.js - Pure JavaScript)
│   ├── package.json                    # Dependencies (React, Chart.js)
│   └── src/
│       ├── App.js                      # Giao diện chính hiển thị chart và video live (JS)
│       └── App.css                     # Styling
│
├── video_data/                         # Video đầu vào
└── md_file/                            # Tài liệu báo cáo (chứa OVERVIEW.md này)
```

---

## 4. Phân Tích Chuyên Sâu Từng Module & Các File Chính

### 4.1. MODULE A: `detection/` (Computer Vision Engine)
Chịu trách nhiệm trực tiếp giao tiếp với dữ liệu hình ảnh, tracking và tính toán logic không gian.

*   **`main.py`**: **Entry point**. Khởi tạo `CameraEngine`, vòng lặp while đọc video liên tục. Có chứa logic **Dynamic Frame Skip**: Khi `density` (mật độ) là `HIGH`, hệ thống chủ động skip một số frame để giảm tải CPU/GPU, khi `LOW` thì xử lý mọi frame.
*   **`camera_engine.py`**: Sử dụng `cv2.VideoCapture` để đọc luồng hình ảnh đầu vào.
*   **`engine/detector.py`**: Khởi tạo model `YOLOv9`. Quản lý `torch.cuda.empty_cache()` để tối ưu VRAM. Cho phép cấu hình confidence threshold khác nhau cho từng loại xe (VD: Ô tô `0.40`, Xe máy `0.25`).
*   **`engine/tracker.py`**: Khởi chạy `supervision.ByteTrack`. Quản lý ID phương tiện xuyên suốt các khung hình với `lost_track_buffer=90`, giúp duy trì ID ngay cả khi phương tiện bị che khuất tạm thời.
*   **`engine/zone_manager.py`**: Khai báo vùng đếm (PolygonZone). Dựa trên toạ độ xe khi giao cắt vùng, nó có khả năng **xác định hướng** (direction: `inbound` / `outbound`).
*   **`engine/density_estimator.py`**: Cung cấp hàm ước lượng `LOW`, `MEDIUM`, `HIGH` theo tổng số lượng bounding box xuất hiện trong một khung hình.
*   **`engine/event_generator.py`**: Lấy thông tin từ sự kiện tracking (xe, ID, camera_id, direction) và đóng gói thành một Event có ý nghĩa để Backend tiếp nhận.
*   **`integration/publisher.py`**: Khởi tạo luồng nền (Background Thread) và một cấu trúc dữ liệu Queue. Nó gộp (batching) và đẩy HTTP `POST /detection` không đồng bộ, giúp luồng phân tích hình ảnh chính **không bị lag (block)** khi gặp vấn đề về mạng.

### 4.2. MODULE B: `backend/` (FastAPI & MongoDB)
Trung tâm lưu trữ và cầu nối API. Sử dụng kiến trúc routing RESTful chuẩn với schema validate bởi Pydantic.

*   **`main.py`**: Khởi tạo FastAPI, cấu hình CORS middleware cho React. Có Global Exception Handler và Logger để đo đạc `duration_ms` của mỗi request.
*   **`mongo_database.py`**: Quản lý connection pooling thông qua `pymongo.MongoClient`. Quản lý logic tạo Indexes tối ưu trên các Collection (như `timestamp` và `camera_id` trên data tracking).
*   **`api/detection_routes.py`**: API `POST /detection`. Map dữ liệu payload với `DetectionSchema` và lưu bản ghi sự kiện xe vào collection `vehicle_detections`.
*   **`api/aggregation_routes.py`**: API `POST /aggregation/compute`. Cốt lõi gom nhóm dữ liệu. Sử dụng **MongoDB Aggregation Pipeline** (`$match` các sự kiện trong 15 phút qua -> `$group`) đếm `inbound_count`, `total_vehicles`, tính ùn tắc trung bình, sau đó lưu một Record duy nhất vào `traffic_aggregation`.
*   **`api/prediction_routes.py`**: `GET /predict-next`. API phục vụ ML Pipeline. Gọi trực tiếp mô hình AI để đưa ra kết quả phân tích đèn và số lượng xe tương lai, sau đó cập nhật collection `traffic_predictions`.
*   **`api/video.py`**: Chứa endpoint `/video/{filename}` trả về luồng video dạng byte (HTTP 206 Partial Content) để Frontend sử dụng thẻ HTML5 `<video>` trơn tru.

### 4.3. MODULE C: `ml_service/` (AI & Machine Learning)
Module cung cấp sức mạnh dự báo với **2 mô hình XGBoost** vận hành song song:

*   **`traffic_predictor.py`**: Load model `model.pkl`. Nhận lịch sử khung thời gian gần nhất và xuất ra `predicted_density` (Dự báo mật độ xe 15 phút kế).
*   **`light_delta_model.py`**: Load model `light_model.pkl`. Mô hình điều hướng thiết thực: dựa trên số xe lưu thông vào (inbound) và hàng đợi (queue), đề xuất `suggested_delta` linh hoạt (trong khoảng `-30s` đến `+45s`) để cấu hình tín hiệu đèn giao thông thực tế.
*   **`train.py`**: Lệnh huấn luyện lại hai mô hình (sử dụng thư viện `xgboost`, `scikit-learn` xử lý pipeline tách train/test và các độ đo MAE/RMSE).

### 4.4. MODULE D: `integration_system/` (System Orchestrator)
Đóng vai trò điều phối tổng và ra quyết định, vận hành như một dịch vụ chạy ngầm.

*   **`system_runner.py`**: Vòng lặp Orchestrator gốc kiểm tra luồng API đều đặn định kỳ mỗi 5 giây.
*   **`scheduler.py`**: Hệ thống lập lịch nhận biết các mốc chẵn thời gian (Ví dụ 12:00, 12:15, 12:30) để tự động gọi endpoint Aggregation.
*   **`delta_applier.py`**: Liên kết Module ML và thế giới thực bằng cách tính toán thời gian `green_time` cụ thể dựa trên thông số `CAMERA_BASELINE` và `delta` tiên đoán.
*   **`direction_router.py`**: Bảng điều hướng logic, map `camera_id` với các pha đèn tín hiệu vật lý tại ngã tư (như `north_green`, `west_green`).
*   **`traffic_light_logic.py`**: Xử lý logic hiển thị hoặc tương tác tín hiệu đèn với bên thứ ba sau khi quá trình phân tích hoàn tất.
*   **`performance_monitor.py`**: Theo dõi chỉ số RAM và CPU server thông qua `psutil` để phòng chống nguy cơ sập phần cứng.

### 4.5. MODULE E: `traffic-frontend/` (React Dashboard)
Hiển thị giao diện người dùng trực quan. Code base đã được chuyển sang **JavaScript thuần (.js)**.

*   **`src/App.js`**: React component chính. Liên tục Poll API lấy về số lượng xe thực tế, kết hợp thư viện `Chart.js` để render các biểu đồ tương quan với dự báo. Nhúng luồng `<video>` thời gian thực được đẩy từ module backend.
*   **`src/index.js`**: Trình khởi động App gắn vào React DOM.

---

## 5. Sơ Đồ Cơ Sở Dữ Liệu (MongoDB)

Cơ sở dữ liệu dạng Document-Oriented tối ưu cho Real-time Write-heavy:
1. **`cameras`**: Collection thiết lập dữ liệu vật lý của camera. Có Unique Index trên `camera_id`.
2. **`vehicle_detections`**: Collection ghi lại lịch sử phương tiện được đếm. Rất nhiều sự kiện nhỏ liên tục. Được đánh Index trên `[camera_id, timestamp]` để tăng tốc tính toán Aggregation. Dữ liệu gồm: `event_id`, `camera_id`, `vehicle_type`, `direction`, `timestamp`.
3. **`traffic_aggregation`**: Lưu trữ block dữ liệu đã nén sau mỗi 15 phút: `total_vehicles`, `inbound_count`, `congestion_level`, `avg_speed`, `period_start`, `period_end`.
4. **`traffic_predictions`**: Lưu trữ log dự báo của Model: `predicted_density`, `suggested_delta`, `timestamp`.

---

## 6. Luồng Hoạt Động (Flows) Cụ Thể

### Flow 1: Nhận Diện & Tracking (Real-time Video)
1. **CameraEngine** đọc frame từ camera (ví dụ 30 FPS).
2. Tùy thuộc `congestion_level`, **Dynamic Frame Skip** có thể cắt bớt số frame xử lý nếu tài nguyên quá tải.
3. Frame đi qua `YOLOv9Detector` → Tạo các Bounding Box.
4. Bounding Box đẩy vào `VehicleTracker` (ByteTrack) → Gán ID cho xe.
5. `ZoneManager` kiểm tra nếu xe giao cắt vùng đếm (polygon), tạo ra trạng thái `inbound` (đi vào) hoặc `outbound` (rời đi).
6. `EventPublisher` gói lại sự kiện thành một JSON rồi đưa vào hàng đợi `Queue`. Dữ liệu sẽ được đẩy bằng HTTP tới REST API `/detection` qua một luồng chạy nền không làm đứng ứng dụng chính.

### Flow 2: Tổng Hợp Dữ Liệu & ML Prediction (Mỗi 15 Phút)
1. Tiến trình `scheduler.py` trong Integration module bắt được khoảnh khắc đến mốc 15 phút.
2. Gọi API `POST /aggregation/compute`.
3. Backend gọi MongoDB aggregation, tự động tính tổng số `inbound`, `outbound` trong 15 phút đó để xuất ra document mới lưu vào collection `traffic_aggregation`.
4. Tiếp tục gọi `GET /predict-next`. Hệ thống ML nạp dữ liệu quá khứ, chạy XGBoost để trả về số lượng dự báo tương lai và đặc biệt là số giây cần bù trừ đèn xanh (`suggested_delta`).

---

## 7. Hướng Dẫn Chạy Toàn Hệ Thống

Bạn cần mở **4 Terminal/Command Prompt** độc lập để kích hoạt toàn bộ luồng kiến trúc:

**Terminal 1: Khởi động Backend (FastAPI + MongoDB)**
```bash
uvicorn backend.main:app --reload
```

**Terminal 2: Khởi động hệ thống Detection (Computer Vision)**
```bash
python -m detection.main
```
> *Hệ thống sẽ bật cửa sổ OpenCV, đọc file video đầu vào và đẩy dữ liệu HTTP sang backend.*

**Terminal 3: Khởi động Frontend Dashboard**
```bash
cd traffic-frontend
npm install
npm start
```
> *Dashboard tại `http://localhost:3000` sẽ liên tục load hình ảnh video stream và đồ thị phân tích thực.*

**Terminal 4: Khởi động Integration System (Orchestrator)**
```bash
python integration_system/system_runner.py
```
> *Hệ thống ngầm sẽ chạy, thu thập tài nguyên hệ thống, định kỳ tính toán AI và in thông số đèn thực tế lên terminal.*

**Tùy chọn: Huấn luyện lại Model AI (ML Service)**
```bash
python -m ml_service.train
```

> Cập nhật lần cuối: Tháng 05/2026.
