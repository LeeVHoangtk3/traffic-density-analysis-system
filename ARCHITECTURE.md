# 🏗️ TRAFFIC DENSITY ANALYSIS SYSTEM - KIẾN TRÚC TOÀN HỆ THỐNG

## 📋 Mục lục
1. [Tổng quan](#tổng-quan)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Các module chính](#các-module-chính)
4. [Luồng dữ liệu](#luồng-dữ-liệu)
5. [Công nghệ sử dụng](#công-nghệ-sử-dụng)
6. [Cách chạy hệ thống](#cách-chạy-hệ-thống)

---

## 🎯 Tổng quan

**Tên**: Traffic Density Analysis System  
**Loại**: Hệ thống phân tích giao thông thời gian thực  
**Mục đích**: Phát hiện, theo dõi phương tiện và phân tích mật độ giao thông bằng AI  
**Kiến trúc**: Microservices (Detection Engine + Backend API)  

### Các tính năng chính:
- ✅ Phát hiện phương tiện thời gian thực (Real-time detection)
- ✅ Theo dõi đối tượng đa frame (Multi-object tracking)
- ✅ Đếm phương tiện qua vùng quan sát (Zone-based counting)
- ✅ Phân loại mật độ giao thông (Traffic density classification)
- ✅ Lưu trữ và query dữ liệu (Data persistence)
- ✅ API REST để tích hợp (REST API integration)

---

## 🔧 Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│              TRAFFIC DENSITY ANALYSIS SYSTEM                │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  TIER 1: INPUT LAYER                                         │
│  ├─ Video Files (.mp4, .avi)                                │
│  ├─ Live Camera (USB, RTSP)                                 │
│  └─ Webcam (ID: 0, 1, 2...)                                │
└────────────────┬─────────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────────────────────┐
│  TIER 2: DETECTION ENGINE (Python + PyTorch)                │
│  ├─ CameraEngine: Đọc video streams                         │
│  ├─ FrameProcessor: Xử lý frame (resize, normalize)         │
│  ├─ Detector (YOLOv9): Phát hiện phương tiện                │
│  ├─ Tracker (DeepSort): Gắn track_id cho mỗi xe            │
│  ├─ ZoneManager: Kiểm tra xe qua từng vùng ROI             │
│  ├─ Counter: Đếm lượng phương tiện                         │
│  ├─ DensityEstimator: Tính mức độ tắc đông                 │
│  └─ EventGenerator: Tạo event (uuid, timestamp, density)    │
└────────────────┬─────────────────────────────────────────────┘
                 ↓
         [HTTP POST /detection]
                 ↓
┌──────────────────────────────────────────────────────────────┐
│  TIER 3: BACKEND API (FastAPI)                              │
│  ├─ main.py: FastAPI app initialization                    │
│  ├─ Routes:                                                 │
│  │  ├─ POST /detection: Lưu detection events               │
│  │  ├─ GET /raw-data: Lấy tất cả detection                 │
│  │  ├─ GET /aggregation: Tính mức tắc đông                 │
│  │  └─ GET /prediction: Dự báo mật độ giao thông           │
│  └─ Services: Business logic (aggregation, prediction)      │
└────────────────┬─────────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────────────────────┐
│  TIER 4: DATA LAYER (SQLAlchemy ORM)                        │
│  ├─ vehicle_detections: Lưu detection events               │
│  ├─ traffic_aggregation: Tổng hợp dữ liệu mật độ           │
│  ├─ traffic_predictions: Dự báo giao thông                 │
│  └─ cameras: Cấu hình camera                                │
└────────────────┬─────────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────────────────────┐
│  TIER 5: DATABASE (SQLite / PostgreSQL)                     │
│  └─ traffic.db (SQLite) hoặc PostgreSQL instance           │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎮 Các module chính

### 1. **DETECTION ENGINE** (`detection/`)
**Mục đích**: Xử lý video, phát hiện xe, theo dõi, đếm, tính mật độ

**Thành phần**:

#### a) `camera_engine.py`
```
- Lớp: CameraEngine
- Chức năng:
  * Mở video file hoặc camera input
  * Đọc frame theo từng frame
  * Handle video properties (FPS, resolution)
- Input: Video source (file path, camera ID, RTSP URL)
- Output: Frame array (H × W × 3)
```

#### b) `detector.py`
```
- Lớp: Detector
- Chức năng:
  * Load YOLOv9 model (best_final.pt hoặc yolov9c.pt)
  * Chạy inference trên mỗi frame
  * Xử lý output, filter confidence
- Input: Frame (640×640 after resize)
- Output: [{bbox, confidence, class_name}, ...]
- Model classes: bus(0), car(1), motorcycle(2), truck(3)
```

#### c) `frame_processor.py`
```
- Lớp: FrameProcessor
- Chức năng:
  * Resize frame theo chiều rộng cố định (default 640px)
  * Maintain aspect ratio
  * Chuẩn bị frame cho YOLO model
- Input: Original frame
- Output: Resized frame
```

#### d) `tracker.py`
```
- Lớp: Tracker
- Chức năng:
  * Sử dụng DeepSort để tracking
  * Gắn track_id cho mỗi detection qua các frame
  * Duy trì trạng thái của mỗi object
- Input: Detections từ YOLO + raw frame
- Output: [{track_id, bbox, class_name}, ...]
- Config: max_age=30 (giữ track max 30 frame)
```

#### e) `counter.py`
```
- Lớp: VehicleCounter
- Chức năng:
  * Đếm tổng số phương tiện theo từng loại (class_name)
  * Đếm phương tiện trong khoảng thời gian 1 phút
  * Tự động reset counter mỗi phút
- Attributes:
  * total_counts: {class_name → int} (toàn thời gian)
  * minute_counts: {class_name → int} (mỗi phút)
  * start_time: timestamp bắt đầu phút hiện tại
- Output: Dict với count cho mỗi vehicle class
```

#### f) `density_estimator.py`
```
- Lớp: DensityEstimator
- Chức năng:
  * Tính mức độ tắc đông dựa vào số lượng tracking objects
  * Phân loại thành 3 level: LOW, MEDIUM, HIGH
- Logic:
  * current_count < 5     → "LOW"
  * 5 ≤ current_count < 15 → "MEDIUM"
  * current_count ≥ 15     → "HIGH"
- Input: Tracked objects list
- Output: Density level (string)
```

#### g) `zone_manager.py`
```
- Lớp: ZoneManager
- Chức năng:
  * Quản lý các vùng quan sát (ROI - Regions of Interest)
  * Kiểm tra xe có qua vùng không (polygon test)
  * Tính toán có/không crossing zone
  * Vẽ zone lên video preview
- Logic:
  * Load zones từ camera config (JSON)
  * Mỗi zone là một polygon (danh sách điểm)
  * Kiểm tra center point của xe có nằm trong polygon
  * Dùng cv2.pointPolygonTest() để kiểm tra
- Input: Track objects + zones config
- Output: Boolean (crossing or not)
```

#### h) `event_generator.py`
```
- Lớp: EventGenerator
- Chức năng:
  * Tạo event object khi xe qua vùng
  * Thêm uuid, timestamp, density level
- Output format:
  {
    "event_id": "uuid4-string",
    "camera_id": "CAM_01",
    "track_id": 123,
    "vehicle_type": "car",
    "density": "MEDIUM",
    "event_type": "line_crossing",
    "timestamp": 1716120564.123
  }
```

#### i) `main.py` (Detection Entry Point)
```
- Chức năng:
  * Orchestrate toàn bộ detection pipeline
  * Đọc video → xử lý frame → detect → track → count → publish
  * Vẽ visualization lên video
- Flow:
  1. Load camera config (zones)
  2. Initialize tất cả components
  3. Open video source
  4. Vòng lặp xử lý frame (main loop):
     - Read frame từ camera
     - Resize frame
     - Detect objects
     - Track objects
     - Check zone crossing
     - Generate event
     - Publish event to API
     - Optional: Draw visualization
  5. Cleanup resources
```

---

### 2. **BACKEND API** (`backend/`)
**Mục đích**: Nhận event từ Detection Engine, lưu vào DB, cung cấp API để query

**Thành phần**:

#### a) `main.py` (FastAPI Application)
```
- Framework: FastAPI
- Chức năng:
  * Khởi tạo FastAPI app
  * Tạo tất cả database tables
  * Include routers cho các endpoints
- Routers bao gồm:
  * detection_routes: /detection (POST)
  * traffic_routes: /raw-data (GET)
  * aggregation_routes: /aggregation (GET)
  * prediction_routes: (chưa xong)
```

#### b) `database.py`
```
- Chức năng:
  * Cấu hình SQLAlchemy engine
  * Kết nối database (SQLite mặc định)
  * Tạo session factory
  * Sync schema (add columns nếu cần)
- Database: sqlite:///./traffic.db
- ORM: SQLAlchemy declarative base
```

#### c) **Models** (`models/`)
```
vehicle_detection.py:
  - Table: vehicle_detections
  - Columns: event_id, camera_id, track_id, vehicle_type, 
             density, event_type, confidence, timestamp
             
traffic_aggregation.py:
  - Table: traffic_aggregation
  - Columns: camera_id, vehicle_count, congestion_level, timestamp
  
traffic_prediction.py:
  - Table: traffic_predictions
  - Columns: predicted_density, timestamp
  
camera.py:
  - Table: cameras
  - Columns: name, location
```

#### d) **Schemas** (`schemas/`)
```
detection_schema.py:
  - Pydantic model: DetectionCreate
  - Validate input từ Detection Engine
  - Fields: event_id, camera_id, track_id, vehicle_type, 
           density, event_type, timestamp, confidence

aggregation_schema.py, prediction_schema.py, traffic_schema.py:
  - Định nghĩa data format cho các API
```

#### e) **API Routes** (`api/`)
```
detection_routes.py:
  POST /detection
  - Body: DetectionCreate (event object)
  - Response: {status: "saved", id: <db_id>}
  - Function: create_detection()
  
traffic_routes.py:
  GET /raw-data
  - Response: [VehicleDetection, ...]
  - Function: get_raw_data()
  
aggregation_routes.py:
  GET /aggregation?vehicle_count=<int>
  - Response: {vehicle_count, congestion_level}
  - Function: get_aggregation()
  - Logic: Tính mức tắc đông từ số lượng xe
  
prediction_routes.py:
  - (Chưa xong)
```

#### f) **Services** (`services/`)
```
db_service.py:
  - Hàm: get_db()
  - Dependency: FastAPI dependency injection
  - Return: Database session cho mỗi request
  
aggregation_service.py:
  - Hàm: compute_congestion(vehicle_count)
  - Logic:
    * count < 10     → "Low"
    * 10 ≤ count < 30 → "Medium"
    * 30 ≤ count < 60 → "High"
    * count ≥ 60     → "Severe"
```

---

### 3. **INTEGRATION** (`detection/integration/`)
```
publisher.py:
  - Lớp: EventPublisher
  - Chức năng:
    * Gửi event qua HTTP POST đến Backend API
    * Timeout 1 giây (non-blocking)
    * Error handling (log failure, không crash)
  - Endpoint: http://127.0.0.1:8000/detection
```

---

### 4. **MODELS** (`detection/pro_models/`)
```
best_final.pt:
  - Custom trained YOLOv9 model
  - Classes: bus, car, motorcycle, truck
  - Được train trên dataset giao thông tùy chỉnh
  
yolov9c.pt:
  - Pre-trained YOLOv9-compact
  - COCO classes (80 classes)
```

---

### 5. **TRAINING** (`yolov9-cus/`)
```
dataset/:
  - train/, val/, test/ folders
  - Chứa ảnh và labels cho training
  - data.yaml: Dataset configuration
  
runs/detect/:
  - Output results từ detection/inference
  - test_results/: Visualization
  
yolov9/:
  - Custom YOLOv9 implementation
  - train.py, val.py, detect.py
```

---

## 📊 Luồng dữ liệu (Data Flow)

### A. **Detection Flow** (Detection Engine):
```
Video File/Camera
    ↓ [CameraEngine.read()]
Raw Frame (H×W×3)
    ↓ [FrameProcessor.process()]
Resized Frame (640×?, 3)
    ↓ [Detector.detect()]
Detections: [{bbox, conf, class}, ...]
    ↓ [Tracker.update()]
Tracked: [{track_id, bbox, class}, ...]
    ↓ [ZoneManager.check_crossing()]
Crossing: Boolean
    ↓ [Nếu crossing] [Counter.count()]
Updated counts: {class → count}
    ↓ [DensityEstimator.update()]
current_count = len(tracks)
    ↓ [DensityEstimator.get_density()]
Density: "LOW" | "MEDIUM" | "HIGH"
    ↓ [EventGenerator.generate()]
Event: {event_id, camera_id, track_id, density, ...}
    ↓ [EventPublisher.publish()]
HTTP POST /detection
```

### B. **Backend Flow** (FastAPI):
```
HTTP POST /detection
    ↓ [Pydantic validation]
Valid DetectionCreate
    ↓ [detection_routes.create_detection()]
VehicleDetection ORM object
    ↓ [db.add() + db.commit()]
SQLite Insert
    ↓
Response: {status: "saved", id: <unique_id>}
```

### C. **Query Flow**:
```
Client Request
    ↓
GET /raw-data
    ↓ [traffic_routes.get_raw_data()]
Query: SELECT * FROM vehicle_detections
    ↓
Response: [VehicleDetection, ...]
```

---

## 🔧 Công nghệ sử dụng

### **AI/ML Stack**:
```
- YOLOv9: Object Detection model
- DeepSort: Multi-object tracking
- PyTorch: Deep Learning framework
- OpenCV: Computer vision operations
- NumPy: Numerical computing
```

### **Backend Stack**:
```
- FastAPI: REST API framework
- SQLAlchemy: ORM (Object-Relational Mapping)
- Pydantic: Data validation
- Uvicorn: ASGI server
```

### **Database**:
```
- SQLite: Lightweight, file-based (development)
- PostgreSQL: Production-ready (optional)
```

### **Utilities**:
```
- Shapely: Geometric operations
- Supervision: Detection utilities
- Deep-sort-realtime: Tracking library
- Requests: HTTP client
- Loguru: Logging
```

---

## 🚀 Cách chạy hệ thống

### **1. Installation**:
```bash
pip install -r requirements.txt
```

### **2. Setup Database**:
```bash
# SQLite sẽ tự tạo traffic.db khi chạy
# PostgreSQL (optional): tạo database trước
```

### **3. Run Backend API**:
```bash
cd /path/to/project
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### **4. Run Detection Engine** (New Terminal):
```bash
cd /path/to/project
python detection/main.py
```

### **5. Monitor Data**:
```bash
# Truy suất data via API
http://localhost:8000/raw-data
http://localhost:8000/aggregation?vehicle_count=20
```

---

## 📋 Environment Variables

```env
# Detection Engine
TRAFFIC_VIDEO_SOURCE = "./traffictrim.mp4"  # hoặc 0 (webcam)
TRAFFIC_MODEL_PATH = "./detection/pro_models/best_final.pt"
TRAFFIC_API_URL = "http://127.0.0.1:8000/detection"

# Backend
DATABASE_URL = "sqlite:///./traffic.db"

# Performance
FRAME_SKIP = 3              # Skip frames để tăng tốc
TARGET_WIDTH = 640          # Resize width
CONF_THRESHOLD = 0.5        # Confidence threshold
```

---

## 📈 Performance Metrics

| Metric | Value | Ghi chú |
|--------|-------|--------|
| FPS (baseline) | ~0.5 FPS | Tùy máy, model, resolution |
| FPS (FRAME_SKIP=3) | ~1.5 FPS | 3x tăng tốc |
| Model size | ~50-100MB | best_final.pt hoặc yolov9c.pt |
| Memory | ~2-4GB GPU | CUDA preferred |
| Latency/frame | ~2 giây | Detect + Track + Publish |

---

## 🔐 Security Considerations

- [ ] API authentication/authorization
- [ ] Input validation (Pydantic handles this)
- [ ] Rate limiting
- [ ] HTTPS for production
- [ ] Database credentials management
- [ ] Model access control

---

## 📝 Lưu ý quan trọng

1. **GPU Requirements**: Hệ thống chạy tốt nhất với CUDA GPU
2. **Video Quality**: Input resolution ảnh hưởng đến detection accuracy
3. **Zone Config**: Phải match video resolution (points in pixel coordinates)
4. **Timeout**: Publisher timeout 1s → event có thể miss nếu API slow
5. **Database**: SQLite OK cho testing, PostgreSQL recommended for production

---
