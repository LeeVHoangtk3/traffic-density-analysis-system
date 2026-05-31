# 🔧 Backend Module - FastAPI + MongoDB

**Backend** là lớp trung tâm của hệ thống Traffic Density Analysis. Module này nhận sự kiện từ Detection, lưu trữ vào MongoDB, tổng hợp dữ liệu định kỳ, gọi ML để dự báo và cung cấp API cho dashboard.

---

## 📋 Vai Trò Chính

| Chức năng | Mô tả |
|----------|-------|
| **Nhận Event Detection** | `POST /detection` - Lưu sự kiện xe qua vạch |
| **Lưu Trữ Dữ Liệu** | MongoDB collections: `vehicle_detections`, `traffic_aggregation`, `traffic_predictions` |
| **Tổng Hợp 15 Phút** | `POST /aggregation/compute` - Tính toán số xe theo 3 hướng |
| **Dự Báo Lưu Lượng** | `GET /predict-next` - Gọi ML service để dự báo 15 phút tiếp theo |
| **Truy Vấn Dữ Liệu** | `GET /raw-data`, `GET /aggregation` - Phục vụ dashboard & integration_system |
| **Quản Lý Camera** | `GET /cameras`, `POST /cameras` - Danh sách & cấu hình camera |
| **Health Check** | `GET /health` - Kiểm tra trạng thái API & DB |

---

## 🏗️ Cấu Trúc Thư Mục

```
backend/
├── api/
│   ├── __init__.py
│   ├── aggregation_routes.py      # POST/GET /aggregation
│   ├── camera_routes.py           # GET/POST /cameras
│   ├── detection_routes.py        # POST /detection
│   ├── health_routes.py           # GET /health
│   ├── prediction_routes.py       # GET /predict-next, /predictions/history
│   ├── traffic_routes.py          # GET /raw-data
│   └── video.py                   # Stream video (not used in current phase)
│
├── services/
│   ├── __init__.py
│   ├── aggregation_service.py     # Tính toán tổng hợp 15 phút
│   ├── camera_service.py          # CRUD camera
│   ├── db_service.py              # MongoDB helper functions
│   ├── detection_service.py       # Xử lý event detection
│   ├── prediction_service.py      # Gọi ML, lưu dự báo
│   └── ...
│
├── schemas/
│   ├── __init__.py
│   ├── aggregation_schema.py      # Pydantic model: TrafficAggregation
│   ├── camera_schema.py           # Pydantic model: Camera
│   ├── detection_schema.py        # Pydantic model: VehicleDetection
│   ├── prediction_schema.py       # Pydantic model: TrafficPrediction
│   └── traffic_schema.py          # Pydantic model: RawTrafficData
│
├── config.py                      # Cấu hình DB, API, thông số hệ thống
├── main.py                        # Entry point FastAPI
├── mongo_database.py              # Khởi tạo MongoDB client
├── seed_data.py                   # Script tạo dữ liệu mẫu
├── test_config.py                 # Cấu hình test
└── README.md                      # File này
```

---

## 🗄️ MongoDB Schema

### 1. `vehicle_detections` - Sự kiện xe qua vạch

```javascript
{
  _id: ObjectId,
  event_id: "cam01_straight_001",      // Unique ID để tránh duplicate
  camera_id: "CAM_01",                 // Mã camera
  track_id: 948,                       // ID theo dõi từ ByteTrack
  vehicle_type: "car",                 // bus, car, motorcycle, truck
  density: "LOW",                      // Mật độ tức thời (LOW/MEDIUM/HIGH)
  event_type: "zone_entry",            // zone_entry, zone_exit
  direction: "straight",               // left, straight, right
  timestamp: ISODate("2026-05-23T02:00:15Z"),
  confidence: 0.91,                    // Độ tự tin YOLO
  processed_at: ISODate("2026-05-23T02:00:16Z")
}
```

**Indexes:**
- `event_id` (unique)
- `camera_id + timestamp` (compound)
- `timestamp` (tăng)

---

### 2. `traffic_aggregation` - Tổng hợp 15 phút

```javascript
{
  _id: ObjectId,
  camera_id: "CAM_01",
  aggregation_period: ISODate("2026-05-23T02:00:00Z"),  // Mốc 15 phút
  direction_counts: {
    left: 12,                          // Số xe rẽ trái
    straight: 45,                      // Số xe thẳng
    right: 8                           // Số xe rẽ phải
  },
  vehicle_type_counts: {
    bus: 5,
    car: 40,
    motorcycle: 15,
    truck: 5
  },
  total_vehicles: 65,
  congestion_level: "MEDIUM",          // LOW, MEDIUM, HIGH dựa K-Means threshold
  computed_at: ISODate("2026-05-23T02:15:05Z")
}
```

**Indexes:**
- `camera_id + aggregation_period` (compound, unique)

---

### 3. `traffic_predictions` - Dự báo 15 phút

```javascript
{
  _id: ObjectId,
  camera_id: "CAM_01",
  prediction_period: ISODate("2026-05-23T02:15:00Z"),  // Mốc dự báo
  predictions: {
    straight: 48,                      // Dự báo số xe thẳng
    left: 14,
    right: 9
  },
  phase_timing: {
    phase_1_green: 52,                 // Giây xanh pha 1 (thẳng + phải)
    phase_2_green: 28,                 // Giây xanh pha 2 (rẽ trái)
    delta_straight: 5,                 // Điều chỉnh so với baseline
    delta_left: 0,
    delta_right: 0
  },
  model_accuracy: {
    mae_straight: 3.2,
    mae_left: 1.5,
    mae_right: 0.8
  },
  predicted_at: ISODate("2026-05-23T02:15:00Z")
}
```

**Indexes:**
- `camera_id + prediction_period` (compound, unique)

---

### 4. `directional_thresholds` - Ngưỡng K-Means (tự thích ứng)

```javascript
{
  _id: ObjectId,
  camera_id: "CAM_01",
  direction: "straight",
  threshold_low: 20,                   // Ngưỡng LOW/MEDIUM
  threshold_high: 50,                  // Ngưỡng MEDIUM/HIGH
  updated_at: ISODate("2026-05-23T00:00:00Z")
}
```

---

### 5. `cameras` - Metadata camera

```javascript
{
  _id: ObjectId,
  camera_id: "CAM_01",
  location: "Ngã ba Phố Huế - Lý Tự Trọng",
  latitude: 21.0285,
  longitude: 105.8541,
  video_source: "data/video/cam01-traffic3.mp4",
  zones: [
    {zone_id: "zone_1", name: "Entry Zone", coordinates: [[0,0], [100,100], ...]},
    {zone_id: "zone_2", name: "Straight Lane", ...},
    {zone_id: "zone_3", name: "Left Lane", ...},
    {zone_id: "zone_4", name: "Right Lane", ...}
  ],
  status: "active",
  created_at: ISODate("2026-05-01T00:00:00Z")
}
```

---

## 🔌 API Endpoints

### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "api": "Running",
  "mongodb": "Connected",
  "timestamp": "2026-05-31T10:30:00Z"
}
```

---

### Detection Events
```
POST /detection
```

**Request Body:**
```json
{
  "event_id": "cam01_straight_001",
  "camera_id": "CAM_01",
  "track_id": 948,
  "vehicle_type": "car",
  "density": "LOW",
  "event_type": "zone_entry",
  "direction": "straight",
  "timestamp": "2026-05-23T02:00:15Z",
  "confidence": 0.91
}
```

**Response:** `200 OK` hoặc `409 Conflict` (nếu event_id tồn tại)

---

### Raw Traffic Data
```
GET /raw-data?camera_id=CAM_01&direction=straight&limit=20&offset=0
```

**Query Parameters:**
- `camera_id` (required)
- `direction` (optional): left, straight, right
- `vehicle_type` (optional): bus, car, motorcycle, truck
- `density` (optional): LOW, MEDIUM, HIGH
- `start_time` (optional): ISO 8601
- `end_time` (optional): ISO 8601
- `limit` (default: 100)
- `offset` (default: 0)

**Response:**
```json
{
  "data": [
    {
      "event_id": "cam01_straight_001",
      "camera_id": "CAM_01",
      "vehicle_type": "car",
      "direction": "straight",
      "timestamp": "2026-05-23T02:00:15Z",
      "confidence": 0.91
    }
  ],
  "total": 2456,
  "limit": 20,
  "offset": 0
}
```

---

### Traffic Aggregation
```
GET /aggregation?camera_id=CAM_01&limit=10
```

**Response:**
```json
{
  "data": [
    {
      "camera_id": "CAM_01",
      "aggregation_period": "2026-05-23T02:00:00Z",
      "direction_counts": {"left": 12, "straight": 45, "right": 8},
      "total_vehicles": 65,
      "congestion_level": "MEDIUM",
      "computed_at": "2026-05-23T02:15:05Z"
    }
  ],
  "total": 1023
}
```

---

### Compute Aggregation (được gọi từ detection mỗi 15 phút)
```
POST /aggregation/compute
```

**Request Body:**
```json
{
  "camera_id": "CAM_01",
  "start_time": "2026-05-23T02:00:00Z",
  "end_time": "2026-05-23T02:15:00Z"
}
```

**Logic:**
1. Đếm sự kiện detection theo `direction` trong khoảng 15 phút
2. Tính `total_vehicles`
3. Sử dụng K-Means threshold để xác định `congestion_level`
4. Lưu vào `traffic_aggregation`

---

### Predict Next Period
```
GET /predict-next?camera_id=CAM_01
```

**Response:**
```json
{
  "camera_id": "CAM_01",
  "prediction_period": "2026-05-23T02:15:00Z",
  "predictions": {
    "straight": 48,
    "left": 14,
    "right": 9
  },
  "phase_timing": {
    "phase_1_green": 52,
    "phase_2_green": 28,
    "delta_straight": 5
  },
  "confidence": 0.87,
  "predicted_at": "2026-05-23T02:15:00Z"
}
```

**Logic:**
1. Lấy 24 mốc aggregation gần nhất (6 giờ lịch sử)
2. Trích đặc trưng (hour, day_of_week, etc.)
3. Gọi 3 mô hình XGBoost từ `ml_service/model/`
4. Tính pha đèn tối ưu
5. Lưu vào `traffic_predictions`

---

### Cameras Management
```
GET /cameras
POST /cameras
GET /cameras/{camera_id}
PUT /cameras/{camera_id}
DELETE /cameras/{camera_id}
```

---

## ⚙️ Cấu Hình (config.py)

```python
# MongoDB
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "traffic_db"

# API
API_TITLE = "Traffic Density Analysis System"
API_VERSION = "1.0.0"
ALLOWED_HOSTS = ["*"]

# Hệ thống
AGGREGATION_INTERVAL_MINUTES = 15
CONFIDENCE_THRESHOLD = 0.40

# K-Means threshold (tự thích ứng)
KMEANS_N_CLUSTERS = 3
KMEANS_RANDOM_STATE = 42

# Pha đèn
TOTAL_GREEN_SECONDS = 80  # Total green seconds per cycle
PHASE_1_MIN_GREEN = 10    # min sec for phase 1 (straight + right)
PHASE_2_MIN_GREEN = 10    # min sec for phase 2 (left)
```

---

## 🚀 Chạy Backend

```bash
# Cách 1: Development
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Cách 2: Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# Cách 3: Với gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
```

Truy cập API docs: `http://localhost:8000/docs`

---

## 🧪 Testing

```bash
# Run tests
pytest backend/

# Với coverage
pytest --cov=backend backend/
```

---

## 📊 Luồng Dữ Liệu

```
Detection Event
    ↓
POST /detection
    ↓
vehicle_detections (MongoDB)
    ↓
[Mỗi 15 phút]
    ↓
POST /aggregation/compute
    ↓
traffic_aggregation (MongoDB)
    ↓
[Integration System gọi]
    ↓
GET /predict-next
    ↓
[Backend gọi ML Service]
    ↓
traffic_predictions (MongoDB)
    ↓
Dashboard GET /aggregation
```

---

## 🔒 Bảo Mật

- ✅ Input validation với Pydantic
- ✅ CORS middleware cho dashboard
- ✅ MongoDB connection pooling
- ✅ Error handling & logging

---

## 📝 Ghi Chú

- Backend hiện tại chạy **hoàn toàn in-memory** cho ML inference (không gọi external API)
- Tất cả sự kiện detection được **xác thực unique bằng event_id** trước khi lưu
- Aggregation tự động được trigger mỗi 15 phút từ detection module

**Cập nhật lần cuối:** 2026-05-31
GET /aggregation
GET /aggregation/history
POST /aggregation/compute?camera_id=CAM_01&window_minutes=15
```

Response co them thong tin 3 huong:

```json
{
  "vehicle_count": 42,
  "direction_counts": {
    "left": 8,
    "straight": 28,
    "right": 6
  },
  "congestion_levels": {
    "left": "Low",
    "straight": "Medium",
    "right": "Low"
  }
}
```

Neu collection `directional_thresholds` co du lieu, backend dung nguong dong theo huong.
Neu chua co, backend fallback ve nguong mac dinh.

### Dynamic Thresholds

```text
GET /thresholds?camera_id=CAM_01
PUT /thresholds/{direction}?camera_id=CAM_01
```

`PUT /thresholds/{direction}` dung de cap nhat nguong K-Means dong cho tung huong.
Payload mau:

```json
{
  "thresholds": {
    "low_to_medium": 32.5,
    "medium_to_high": 68.0,
    "high_to_heavy": 105.3
  },
  "centroids": [12.0, 53.0, 83.0, 127.6]
}
```

### Prediction

```text
GET /predict-next?camera_id=CAM_01
GET /predictions/history?camera_id=CAM_01&limit=10
```

Backend uu tien load 3 model:

```text
ml_service/model/model_straight.pkl
ml_service/model/model_left.pkl
ml_service/model/model_right.pkl
```

Neu thieu model hoac thieu lich su, backend fallback bang trung binh du lieu gan nhat.

Response co dang:

```json
{
  "camera_id": "CAM_01",
  "predicted_density": 74,
  "predictions": {
    "left": 14,
    "straight": 52,
    "right": 8
  },
  "congestion_levels": {
    "left": "Low",
    "straight": "Medium",
    "right": "Low"
  },
  "phase_timing": {
    "phase_1_green": 55,
    "phase_2_green": 25,
    "delta_phase_1": 5,
    "delta_phase_2": -5
  },
  "horizon_minutes": 15,
  "source": "straight:ml_service,left:fallback,right:ml_service"
}
```

### Traffic Light Status

```text
GET /traffic-lights/status
```

Backend doc `integration_system/light_status.json` neu co, neu khong se doc `light_status.json`
o thu muc goc. Response duoc chuan hoa thanh 2 pha:

- `phase_1`: `straight` + `right`
- `phase_2`: `left`

### Dataset Export

```text
GET /dataset/export?camera_id=CAM_01&limit=100
```

Xuat du lieu aggregation dang phang theo tung huong de phuc vu training/evaluation ML.
Moi item gom `camera_id`, `timestamp`, `direction`, `vehicle_count`,
`congestion_level`.

### Cameras

```text
GET /cameras
POST /cameras
```

Camera co cac truong: `camera_id`, `name`, `location`, `baseline_green`,
`monitored_direction`.

### Video

```text
GET /video
```

Stream frame moi nhat tu module detection theo dang MJPEG.

## Chay Backend

```powershell
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

File `.env` toi thieu:

```env
DB_URL=mongodb://localhost:27017/
MONGODB_DB=traffic_density
BACKEND_API_TITLE=Traffic AI Backend
DEFAULT_PAGE_SIZE=100
MAX_PAGE_SIZE=500
PREDICTION_HORIZON_MINUTES=15
```

## Seed Du Lieu

```powershell
python -m backend.seed_data
```

Script nay tao/cap nhat camera, aggregation va prediction tu du lieu co san trong
`vehicle_detections`.

## Trang Thai Hoan Thien

Da hoan thien:

- MongoDB la storage chinh.
- Detection nhan `left`, `straight`, `right`.
- Aggregation tinh `direction_counts` va `congestion_levels`.
- Prediction tra du bao 3 huong va `phase_timing`.
- API `/traffic-lights/status` cho frontend.
- Index MongoDB cho `directional_thresholds`.
- API `/thresholds` de quan tri nguong dong.
- API `/dataset/export` de xuat du lieu huan luyen.

Can tiep tuc neu co thoi gian:

- Them authentication/rate limit cho endpoint ghi du lieu.
- Viet test tu dong cho detection, aggregation, prediction va light status.
- Hoan thien script K-Means cap nhat `directional_thresholds`.
