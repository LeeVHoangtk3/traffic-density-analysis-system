# 📦 CHI TIẾT CÁC MODULE VÀ FILE

## Mục lục
1. [Detection Engine Modules](#detection-engine-modules)
2. [Backend Modules](#backend-modules)
3. [Supporting Components](#supporting-components)

---

## 🎥 DETECTION ENGINE MODULES

### **detection/camera_engine.py**

#### Mục đích
Lớp wrapper để mở và đọc video từ nhiều nguồn (file video, camera USB, webcam, RTSP stream)

#### Cấu trúc
```python
class CameraEngine:
    def __init__(self, source: Union[str, int])
        # source: 
        #   - File path: "./video.mp4"
        #   - Webcam ID: 0, 1, 2, ...
        #   - RTSP URL: "rtsp://camera_ip/stream"
    
    def read() → Tuple[bool, np.ndarray]
        # Return: success flag, frame (H×W×3)
    
    def release()
        # Clean up resources
```

#### Cách hoạt động
1. Khởi tạo: `cv2.VideoCapture(source)`
2. Mỗi lần gọi `read()`: lấy frame tiếp theo
3. Return 2 giá trị: success (True/False), frame array
4. Frame format: BGR (OpenCV format), shape (H, W, 3)

#### Mã nguồn
```python
import cv2

class CameraEngine:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        print("Video opened:", self.cap.isOpened())

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()
```

#### Ví dụ sử dụng
```python
camera = CameraEngine("./video.mp4")
while True:
    success, frame = camera.read()
    if not success:
        break
    # Xử lý frame
camera.release()
```

---

### **detection/engine/frame_processor.py**

#### Mục đích
Tiền xử lý frame trước khi đưa vào YOLO: resize, normalize, giữ aspect ratio

#### Cấu trúc
```python
class FrameProcessor:
    def __init__(self, target_width: int = 1280)
        # target_width: chiều rộng khi resize
    
    def process(self, frame: np.ndarray) → np.ndarray
        # Input: original frame
        # Output: resized frame (target_width × ?, 3)
```

#### Cách hoạt động
1. Tính tỷ lệ resize: `scale = target_width / original_width`
2. Tính chiều cao mới: `new_height = original_height * scale`
3. Resize frame: `cv2.resize(frame, (target_width, new_height))`
4. Giữ aspect ratio → không distortion

#### Mã nguồn
```python
import cv2

class FrameProcessor:
    def __init__(self, target_width=1280):
        self.target_width = target_width

    def process(self, frame):
        h, w = frame.shape[:2]
        scale = self.target_width / w
        frame = cv2.resize(frame, (self.target_width, int(h * scale)))
        return frame
```

#### Ví dụ sử dụng
```python
processor = FrameProcessor(target_width=640)
frame_resized = processor.process(frame_original)
# frame_resized shape: (?, 640, 3)
```

---

### **detection/engine/detector.py**

#### Mục đích
Chương trình chính để chạy YOLOv9 inference và phát hiện phương tiện

#### Cấu trúc
```python
class Detector:
    def __init__(self, model_path: str, conf_threshold: float = 0.4)
        # model_path: đường dẫn đến .pt model file
        # conf_threshold: confidence threshold (0.0 - 1.0)
    
    def detect(self, frame: np.ndarray) → List[Dict]
        # Input: frame (H×W×3)
        # Output: [{bbox, confidence, class_name}, ...]
```

#### Cách hoạt động
1. **Model Loading**:
   - Load checkpoint từ file .pt
   - Move to GPU (CUDA) hoặc CPU
   - Set to eval mode

2. **Preprocessing**:
   - Resize frame thành 640×640
   - Transpose từ (H,W,3) → (3,H,W)
   - Normalize: chia cho 255
   - Convert to torch tensor
   - Add batch dimension

3. **Inference**:
   - Forward pass: `model(img)`
   - Get output từ model
   - Handle nested outputs (list/tuple)

4. **Postprocessing**:
   - NMS (Non-Maximum Suppression)
   - Filter by confidence threshold
   - Format bbox, confidence, class

#### Classes (Custom Model)
```python
VEHICLE_CLASSES = {
    0: "bus",
    1: "car",
    2: "motorcycle",
    3: "truck"
}
```

#### Output Format
```python
[
    {
        "bbox": [x1, y1, x2, y2],      # Top-left, bottom-right
        "confidence": 0.95,             # 0.0 - 1.0
        "class_name": "car"
    },
    ...
]
```

---

### **detection/engine/tracker.py**

#### Mục đích
Theo dõi đối tượng qua các frame, gắn track_id cho mỗi phương tiện để duy trì identity

#### Cấu trúc
```python
class Tracker:
    def __init__(self)
        # Khởi tạo DeepSort tracker
    
    def update(self, detections: List[Dict], frame: np.ndarray) → List[Dict]
        # Input: detections từ YOLO, raw frame
        # Output: tracked objects với track_id
```

#### Cách hoạt động
1. **Input Preparation**:
   - Convert bbox từ YOLO format → DeepSort format
   - Create raw_detections: `[[x1, y1, w, h], conf, class_name]`

2. **Tracking**:
   - Call `tracker.update_tracks(raw_detections, frame=frame)`
   - DeepSort dùng Deep feature extraction + Hungarian algorithm
   - Khớp detection với previous tracks

3. **Output Filtering**:
   - Chỉ return confirmed tracks (không ghost tracks)
   - Extract bbox, track_id, class_name

#### Configuration
```python
max_age = 30  # Keep track for max 30 frames nếu không có detection
```

#### Output Format
```python
[
    {
        "track_id": 1,                  # Unique ID (persistent)
        "bbox": [x1, y1, x2, y2],      # Current bbox
        "class_name": "car"             # Vehicle class
    },
    ...
]
```

#### Ví dụ sử dụng
```python
tracker = Tracker()
detections = detector.detect(frame)
tracked = tracker.update(detections, frame)
# tracked: [
#   {track_id: 1, bbox: [...], class_name: "car"},
#   {track_id: 2, bbox: [...], class_name: "truck"},
# ]
```

---

### **detection/engine/counter.py**

#### Mục đích
Đếm tổng số phương tiện theo loại, và đếm theo từng phút (phục vụ thống kê giao thông)

#### Cấu trúc
```python
class VehicleCounter:
    def __init__(self)
        # total_counts: {class_name → count}
        # minute_counts: {class_name → count}
        # start_time: timestamp bắt đầu phút
    
    def count(self, class_name: str)
        # Tăng counter cho class_name này
        # Cập nhật cả total_counts và minute_counts
    
    def get_totals() → Dict[str, int]
        # Return snapshot hiện tại của total_counts
    
    def get_per_minute() → Optional[Dict[str, int]]
        # Nếu ≥60s đã trôi qua: return minute_counts, reset
        # Nếu <60s: return None
```

#### Cách hoạt động
```
Timeline:
t=0s: Init, start_time = now
t=10s: count("car") → total={car:1}, minute={car:1}
t=20s: count("car") → total={car:2}, minute={car:2}
t=55s: count("truck") → total={car:2, truck:1}, minute={car:2, truck:1}
t=60s: get_per_minute() → minute={car:2, truck:1}
       → RESET: start_time=now, minute_counts={}
t=70s: count("car") → total={car:3}, minute={car:1}
```

#### Mã nguồn
```python
import time
from collections import defaultdict

class VehicleCounter:
    def __init__(self):
        self.total_counts = defaultdict(int)
        self.minute_counts = defaultdict(int)
        self.start_time = time.time()

    def count(self, class_name):
        self.total_counts[class_name] += 1
        self.minute_counts[class_name] += 1

    def get_totals(self):
        return dict(self.total_counts)

    def get_per_minute(self):
        if time.time() - self.start_time >= 60:
            data = dict(self.minute_counts)
            self.minute_counts.clear()
            self.start_time = time.time()
            return data
        return None
```

#### Ví dụ sử dụng
```python
counter = VehicleCounter()
counter.count("car")
counter.count("car")
counter.count("truck")
print(counter.get_totals())  # {car: 2, truck: 1}
```

---

### **detection/engine/density_estimator.py**

#### Mục đích
Tính toán mức độ tắc đông giao thông dựa vào số lượng phương tiện hiện tại

#### Cấu trúc
```python
class DensityEstimator:
    def __init__(self)
        # current_count: số lượng tracked objects hiện tại
    
    def update(self, tracks: List[Dict])
        # Cập nhật current_count từ danh sách tracked objects
    
    def get_density() → str
        # Return "LOW", "MEDIUM", hoặc "HIGH"
```

#### Cách hoạt động
```python
Logic:
if current_count < 5:
    density = "LOW"       # Ít xe
elif current_count < 15:
    density = "MEDIUM"    # Mức bình thường
else:
    density = "HIGH"      # Tắc đông
```

#### Mã nguồn
```python
class DensityEstimator:
    def __init__(self):
        self.current_count = 0

    def update(self, tracks):
        self.current_count = len(tracks)

    def get_density(self):
        if self.current_count < 5:
            return "LOW"
        elif self.current_count < 15:
            return "MEDIUM"
        return "HIGH"
```

---

### **detection/engine/zone_manager.py**

#### Mục đích
Quản lý các vùng quan sát (ROI) để đếm phương tiện qua từng vùng cụ thể

#### Cấu trúc
```python
class ZoneManager:
    def __init__(self, zones: List[Dict])
        # zones: danh sách vùng từ camera config
    
    def check_crossing(self, track_id: int, cx: float, cy: float) → bool
        # Kiểm tra nếu xe (track_id) qua vùng
        # cx, cy: tọa độ trung tâm xe
        # Return: True nếu qua vùng (và chưa counted), False otherwise
    
    def draw_zone(self, frame: np.ndarray)
        # Vẽ polygon vùng lên frame (visualization)
```

#### Cách hoạt động
```python
Flow:
1. Load zones từ config (mỗi zone là polygon)
2. Lấy center point của xe: cx = (x1+x2)/2, cy = (y1+y2)/2
3. Với mỗi zone:
   - Convert points thành numpy array
   - Dùng cv2.pointPolygonTest(polygon, (cx, cy), False)
   - Nếu inside >= 0 (inside polygon):
     * Kiểm tra track_id chưa trong counted_ids
     * Nếu chưa count: thêm vào counted_ids, return True
4. Return False nếu không crossing hoặc đã count trước
```

#### Zone Config Format (JSON)
```json
{
  "camera_id": "CAM_01",
  "zones": [
    {
      "id": "main_detection_zone",
      "points": [
        [0, 240],
        [640, 240],
        [640, 360],
        [0, 360]
      ]
    }
  ]
}
```

#### Mã nguồn
```python
import cv2
import numpy as np

class ZoneManager:
    def __init__(self, zones):
        self.zones = zones
        self.counted_ids = set()

    def check_crossing(self, track_id, cx, cy):
        point = (cx, cy)
        for zone in self.zones:
            polygon = np.array(zone["points"], np.int32)
            inside = cv2.pointPolygonTest(polygon, point, False)
            if inside >= 0:
                if track_id not in self.counted_ids:
                    self.counted_ids.add(track_id)
                    return True
        return False

    def draw_zone(self, frame):
        for zone in self.zones:
            pts = np.array(zone["points"], np.int32)
            cv2.polylines(frame, [pts], True, (255,0,255), 3)
```

---

### **detection/engine/event_generator.py**

#### Mục đích
Tạo event object khi xe qua vùng, chứa tất cả metadata cho backend

#### Cấu trúc
```python
class EventGenerator:
    def generate(self, camera_id: str, track: Dict, density: str) → Dict
        # camera_id: ID camera (e.g., "CAM_01")
        # track: tracked object từ tracker
        # density: mức độ tắc đông từ estimator
        # Return: event dict
```

#### Output Format
```python
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID4
    "camera_id": "CAM_01",
    "track_id": 1,
    "vehicle_type": "car",           # từ track["class_name"]
    "density": "MEDIUM",             # từ density_estimator
    "event_type": "line_crossing",
    "timestamp": 1711900223.456      # Unix timestamp
}
```

#### Mã nguồn
```python
import uuid
import time

class EventGenerator:
    def generate(self, camera_id, track, density):
        return {
            "event_id": str(uuid.uuid4()),
            "camera_id": camera_id,
            "track_id": track["track_id"],
            "vehicle_type": track["class_name"],
            "density": density,
            "event_type": "line_crossing",
            "timestamp": time.time()
        }
```

---

### **detection/integration/publisher.py**

#### Mục đích
Gửi event qua HTTP POST tới Backend API (non-blocking, với timeout)

#### Cấu trúc
```python
class EventPublisher:
    def __init__(self, api_url: str)
        # api_url: endpoint của backend (e.g., "http://127.0.0.1:8000/detection")
    
    def publish(self, event: Dict)
        # Gửi event qua HTTP POST
        # Không block main thread (timeout 1s)
```

#### Cách hoạt động
```python
1. Tạo HTTP POST request
2. Headers: Content-Type: application/json
3. Body: event dict (serialized thành JSON)
4. Timeout: 1 second (nếu quá lâu → discard)
5. Error handling: Log, không raise exception
```

#### Mã nguồn
```python
import requests

class EventPublisher:
    def __init__(self, api_url):
        self.api_url = api_url

    def publish(self, event):
        try:
            requests.post(self.api_url, json=event, timeout=1)
        except Exception as e:
            print("Publish failed:", e)
```

---

### **detection/main.py**

#### Mục đích
Entry point chính, orchestrate toàn bộ detection pipeline

#### Cấu trúc
```python
def main():
    # 1. Load config
    # 2. Load model
    # 3. Initialize components
    # 4. Main processing loop
    # 5. Cleanup
```

#### Cách hoạt động

**Phase 1: Initialization**
```python
- Load camera config từ JSON
- Initialize CameraEngine
- Initialize Detector (load YOLOv9 model)
- Initialize Tracker, Counter, DensityEstimator
- Initialize ZoneManager
- Initialize EventPublisher
```

**Phase 2: Main Loop**
```
Vòng lặp vô hạn:
  1. camera.read() → frame
  2. frameprocessor.process(frame)
  3. detector.detect(frame) → detections
  4. tracker.update(detections, frame) → tracks
  5. DensityEstimator.update(tracks)
  6. Đối với mỗi track:
     - ZoneManager.check_crossing(track_id, cx, cy)
     - Nếu crossing:
       * Counter.count(track["class_name"])
       * EventGenerator.generate(...)
       * EventPublisher.publish(event)
  7. (Optional) Vẽ visualization
  8. (Optional) Hiển thị video
```

**Phase 3: Cleanup**
```python
- camera.release()
- cv2.destroyAllWindows()
```

---

## 🔌 BACKEND MODULES

### **backend/main.py**

#### Mục đích
FastAPI application entry point, khởi tạo server và endpoints

#### Cấu trúc
```python
from fastapi import FastAPI
from backend.database import engine, Base

app = FastAPI(title="Traffic AI Backend")

# Create tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(detection_routes.router)
app.include_router(traffic_routes.router)
app.include_router(aggregation_routes.router)
app.include_router(prediction_routes.router)
```

#### Cách hoạt động
1. FastAPI app initialization
2. Database tables creation (từ ORM models)
3. Router registration
4. Uvicorn server nhận requests

#### Endpoints được include
```
POST   /detection           (detection_routes)
GET    /raw-data           (traffic_routes)
GET    /aggregation        (aggregation_routes)
```

---

### **backend/database.py**

#### Mục đích
Cấu hình SQLAlchemy ORM, database connection, schema management

#### Cấu trúc
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./traffic.db"
engine = create_engine(DATABASE_URL, connect_args={...})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def sync_vehicle_detection_schema():
    # Thêm columns nếu cần
```

#### Cách hoạt động
1. **Engine**: Kết nối đến database
2. **SessionLocal**: Factory để tạo session (per request)
3. **Base**: Declarative base cho tất cả ORM models
4. **sync_vehicle_detection_schema()**: Dynamically add columns nếu không tồn tại

---

### **backend/models/vehicle_detection.py**

#### Mục đích
SQLAlchemy ORM model cho table `vehicle_detections`

#### Schema
```python
class VehicleDetection(Base):
    __tablename__ = "vehicle_detections"
    
    id              Integer (PK)
    event_id        String
    camera_id       String
    track_id        String
    vehicle_type    String
    density         String
    event_type      String
    confidence      Float
    timestamp       DateTime (default: utcnow)
```

#### Cách hoạt động
- SQLAlchemy map Python class → SQL table
- Mỗi instance → row trong table
- Automatic type conversion

---

### **backend/models/traffic_aggregation.py**

#### Mục đích
SQLAlchemy ORM model cho table `traffic_aggregation` (aggregated data)

#### Schema
```python
class TrafficAggregation(Base):
    __tablename__ = "traffic_aggregation"
    
    id               Integer (PK)
    camera_id        String
    vehicle_count    Integer
    congestion_level String
    timestamp        DateTime
```

---

### **backend/models/traffic_prediction.py**

#### Mục đích
SQLAlchemy ORM model cho table `traffic_predictions` (ML predictions)

#### Schema
```python
class TrafficPrediction(Base):
    __tablename__ = "traffic_predictions"
    
    id                Integer (PK)
    predicted_density Float
    timestamp         DateTime
```

---

### **backend/schemas/detection_schema.py**

#### Mục đích
Pydantic model để validate input từ Detection Engine

#### Cấu trúc
```python
from pydantic import BaseModel

class DetectionCreate(BaseModel):
    event_id: str
    camera_id: str
    track_id: Union[int, str]
    vehicle_type: str
    density: str
    event_type: str
    timestamp: datetime
    confidence: Optional[float] = None
```

#### Cách hoạt động
1. Detection Engine gửi HTTP POST với JSON body
2. FastAPI endpoint receive
3. Pydantic validate JSON against DetectionCreate schema
4. Automatic type conversion + validation
5. Raise validation error nếu invalid

---

### **backend/api/detection_routes.py**

#### Mục đích
FastAPI router cho `/detection` endpoint (nhận events từ Detection Engine)

#### Endpoint
```python
@router.post("/detection")
def create_detection(data: DetectionCreate, db: Session = Depends(get_db)):
    # 1. Pydantic validates data
    # 2. Create VehicleDetection ORM object
    # 3. db.add() + db.commit()
    # 4. Return {status: "saved", id: detection.id}
```

#### Cách hoạt động
```
HTTP POST /detection
  Body: {event_id, camera_id, track_id, ...}
    ↓ [Pydantic validation]
  DetectionCreate instance
    ↓ [create_detection() called]
  VehicleDetection(
    event_id=data.event_id,
    camera_id=data.camera_id,
    track_id=str(data.track_id),
    ...
  )
    ↓ [db.add() + db.commit()]
  INSERT into vehicle_detections table
    ↓
  Response: {"status": "saved", "id": 123}
```

---

### **backend/api/traffic_routes.py**

#### Mục đích
Query raw detection data

#### Endpoint
```python
@router.get("/raw-data")
def get_raw_data(db: Session = Depends(get_db)):
    data = db.query(VehicleDetection).all()
    return data
```

#### Output
```python
[
    {
        "id": 1,
        "event_id": "...",
        "camera_id": "CAM_01",
        "track_id": "1",
        "vehicle_type": "car",
        "density": "MEDIUM",
        ...
    },
    ...
]
```

---

### **backend/api/aggregation_routes.py**

#### Mục đích
Tính toán mức tắc đông từ số lượng phương tiện

#### Endpoint
```python
@router.get("/aggregation")
def get_aggregation(vehicle_count: int):
    level = compute_congestion(vehicle_count)
    return {
        "vehicle_count": vehicle_count,
        "congestion_level": level
    }
```

#### Cách hoạt động
```
Vehicle Count → Congestion Level:
< 10         → "Low"
10-29        → "Medium"
30-59        → "High"
≥ 60         → "Severe"
```

---

### **backend/services/aggregation_service.py**

#### Mục đích
Business logic cho aggregation

#### Function
```python
def compute_congestion(vehicle_count):
    if vehicle_count < 10:
        return "Low"
    elif vehicle_count < 30:
        return "Medium"
    elif vehicle_count < 60:
        return "High"
    else:
        return "Severe"
```

---

### **backend/services/db_service.py**

#### Mục đích
Database dependency injection cho FastAPI

#### Function
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Cách hoạt động
- FastAPI dependency: `Depends(get_db)`
- Mỗi request: tạo session mới
- Sau xử lý: close session

---

## 📺 CONFIG FILES

### **detection/configs_cameras/cam_01.json**

#### Mục đích
Cấu hình camera specific: zones (ROI)

#### Format
```json
{
  "camera_id": "CAM_01",
  "zones": [
    {
      "id": "zone_name",
      "points": [
        [x1, y1],
        [x2, y2],
        [x3, y3],
        [x4, y4]
      ]
    }
  ]
}
```

#### Ví dụ
```json
{
  "camera_id": "CAM_01",
  "zones": [
    {
      "id": "main_detection_zone",
      "points": [[0, 240], [640, 240], [640, 360], [0, 360]]
    },
    {
      "id": "entry_zone",
      "points": [[0, 200], [200, 200], [200, 300], [0, 300]]
    }
  ]
}
```

---

## 🐍 UTILITY SCRIPTS

### **detection/ultralytics_yolov9/**
Custom YOLOv9 implementation (models, utils, inference code)

### **yolov9-cus/**
Training codebase (dataset, training scripts, model weights)

---

## 📊 DATABASE SCHEMA DIAGRAM

```
vehicle_detections
├── id (PK)
├── event_id (unique identifier từ Detection Engine)
├── camera_id (e.g., "CAM_01")
├── track_id (persistent ID từ DeepSort)
├── vehicle_type (bus, car, motorcycle, truck)
├── density (LOW, MEDIUM, HIGH)
├── event_type (line_crossing)
├── confidence (0.0-1.0)
└── timestamp

traffic_aggregation
├── id (PK)
├── camera_id
├── vehicle_count
├── congestion_level
└── timestamp

traffic_predictions
├── id (PK)
├── predicted_density
└── timestamp

cameras
├── id (PK)
├── name
└── location
```

---
