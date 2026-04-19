# 🚀 QUICK START & USAGE EXAMPLES

## Tổng quan

| Yếu tố | Chi tiết |
|--------|---------|
| Ngôn ngữ | Python 3.8+ |
| Framework chính | FastAPI + YOLOv9 + DeepSort |
| Database | SQLite (default) / PostgreSQL (production) |
| Thời gian thực | ~0.5-1.5 FPS tùy hệ thống |
| Model | best_final.pt (custom) hoặc yolov9c.pt (pre-trained) |

---

## ⚙️ Cài đặt & Setup

### 1. Prerequisites
```bash
# Python 3.8+
python --version

# CUDA (recommended for GPU)
nvidia-smi
```

### 2. Clone repository
```bash
cd d:/GIT\ REPO/trafffic-density-analysis-system
```

### 3. Cài đặt dependencies
```bash
# Tạo virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Cài dependencies
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
# Kiểm tra PyTorch
python -c "import torch; print(torch.cuda.is_available())"

# Kiểm tra FastAPI
python -c "import fastapi; print(fastapi.__version__)"

# Kiểm tra YOLO
python -c "from ultralytics import YOLO; print('YOLOv8 loaded')"
```

---

## 🎯 Cách chạy hệ thống (Step-by-step)

### **Option 1: Full System (Recommended)**

#### Terminal 1: Backend API
```bash
# Chạy FastAPI server
cd traffic-density-analysis-system
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Kiểm tra**: http://localhost:8000/docs (Swagger UI)

#### Terminal 2: Detection Engine
```bash
# Chạy detection pipeline
python detection/main.py
```

**Output:**
```
Video opened: True
Load model successfully from: ./detection/pro_models/best_final.pt
Processing frame 1/xyz...
Detected 5 vehicles
Event published: {event_id, timestamp, density}
...
```

### **Option 2: Backend Only (Testing)**

```bash
# Chỉ chạy API server
uvicorn backend.main:app --reload --port 8000

# Test endpoints (in another terminal)
curl http://localhost:8000/raw-data
# Response: []  (empty, no detections yet)

curl "http://localhost:8000/aggregation?vehicle_count=20"
# Response: {"vehicle_count": 20, "congestion_level": "Medium"}
```

### **Option 3: Detection Only (Without Backend)**

```bash
# Comment out publisher code in detection/main.py
# hoặc modify EventPublisher to skip publish

python detection/main.py
# Sẽ chạy detection pipeline nhưng không gửi event
```

---

## 📡 API Usage Examples

### **1. POST /detection** (Detection Engine → Backend)

```python
import requests
import json

event = {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "camera_id": "CAM_01",
    "track_id": 1,
    "vehicle_type": "car",
    "density": "MEDIUM",
    "event_type": "line_crossing",
    "timestamp": 1711900223.456,
    "confidence": 0.95
}

response = requests.post(
    "http://localhost:8000/detection",
    json=event
)

print(response.json())
# Output: {"status": "saved", "id": 1}
```

### **2. GET /raw-data** (Query all detections)

```python
import requests

response = requests.get("http://localhost:8000/raw-data")
data = response.json()

print(f"Total detections: {len(data)}")
for item in data:
    print(f"{item['camera_id']}: {item['vehicle_type']} @ {item['density']}")
```

### **3. GET /aggregation** (Calculate congestion)

```python
import requests

# Query for different vehicle counts
for count in [5, 15, 50]:
    response = requests.get(f"http://localhost:8000/aggregation?vehicle_count={count}")
    result = response.json()
    print(f"Count {count} → {result['congestion_level']}")

# Output:
# Count 5 → Low
# Count 15 → Medium
# Count 50 → High
```

---

## 🎮 Configuration Examples

### **1. Camera Config (cam_01.json)**

```json
{
  "camera_id": "CAM_01",
  "zones": [
    {
      "id": "entry_zone",
      "points": [
        [100, 200],
        [300, 200],
        [300, 400],
        [100, 400]
      ]
    },
    {
      "id": "exit_zone",
      "points": [
        [500, 200],
        [640, 200],
        [640, 400],
        [500, 400]
      ]
    }
  ]
}
```

**Thêm camera mới**:
1. Tạo file `detection/configs_cameras/cam_02.json`
2. Định nghĩa zones với pixel coordinates
3. Update `detection/main.py`: CAMERA_ID = "CAM_02"

### **2. Environment Variables (.env)**

```env
# Detection Engine
TRAFFIC_VIDEO_SOURCE=./video.mp4
TRAFFIC_MODEL_PATH=./detection/pro_models/best_final.pt
TRAFFIC_API_URL=http://127.0.0.1:8000/detection

# Backend
DATABASE_URL=sqlite:///./traffic.db

# Performance
FRAME_SKIP=3
TARGET_WIDTH=640
CONF_THRESHOLD=0.5
```

**Load từ code**:
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_url = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000/detection")
```

### **3. Performance Tuning**

```python
# In detection/main.py

# Tăng tốc độ
FRAME_SKIP = 3              # Skip 2/3 frames
TARGET_WIDTH = 480          # Resize nhỏ hơn (default 640)
CONF_THRESHOLD = 0.6        # Filter threshold cao hơn
SHOW_VIDEO = False          # Tắt visualization

# Tăng độ chính xác
FRAME_SKIP = 1              # Process every frame
TARGET_WIDTH = 1280         # Keep high resolution
CONF_THRESHOLD = 0.3        # Lower threshold
SHOW_VIDEO = True           # Enable debugging

# Balanced
FRAME_SKIP = 2              # ~2 FPS
TARGET_WIDTH = 640
CONF_THRESHOLD = 0.5
SHOW_VIDEO = True
```

---

## 📊 Database Queries (SQL)

### **Setup PostgreSQL** (Production)

```bash
# Cài PostgreSQL
# Tạo database
createdb traffic_db

# Update backend/database.py
DATABASE_URL = "postgresql://user:password@localhost/traffic_db"
```

### **Common Queries**

```sql
-- Reset database
DROP TABLE IF EXISTS vehicle_detections;

-- Get detections in last hour
SELECT * FROM vehicle_detections 
WHERE timestamp > datetime('now', '-1 hour');

-- Count by vehicle type
SELECT vehicle_type, COUNT(*) 
FROM vehicle_detections 
GROUP BY vehicle_type;

-- Density distribution
SELECT density, COUNT(*) 
FROM vehicle_detections 
GROUP BY density;

-- Events per camera
SELECT camera_id, COUNT(*) 
FROM vehicle_detections 
GROUP BY camera_id;

-- Export to CSV
SELECT * FROM vehicle_detections 
INTO OUTFILE 'export.csv' 
DELIMITER ',';
```

### **Python SQLAlchemy Queries**

```python
from sqlalchemy import func
from backend.database import SessionLocal
from backend.models.vehicle_detection import VehicleDetection

db = SessionLocal()

# Get all detections
all_detections = db.query(VehicleDetection).all()

# Filter by camera
cam_detections = db.query(VehicleDetection)\
    .filter(VehicleDetection.camera_id == "CAM_01")\
    .all()

# Count by type
type_counts = db.query(
    VehicleDetection.vehicle_type,
    func.count(VehicleDetection.id)
).group_by(VehicleDetection.vehicle_type).all()

# Latest detection
latest = db.query(VehicleDetection)\
    .order_by(VehicleDetection.timestamp.desc())\
    .first()

# Delete old records (older than 7 days)
from datetime import datetime, timedelta
cutoff = datetime.utcnow() - timedelta(days=7)
db.query(VehicleDetection)\
    .filter(VehicleDetection.timestamp < cutoff)\
    .delete()
db.commit()
```

---

## 🔧 Debugging & Troubleshooting

### **Problem: Model không load**

```python
# Error: FileNotFoundError: model not found

# Solution 1: Check path
import os
model_path = "./detection/pro_models/best_final.pt"
print(os.path.exists(model_path))

# Solution 2: Download model
# Download từ: https://github.com/WongKinYiu/yolov9/releases
# Place vào: detection/pro_models/best_final.pt
```

### **Problem: GPU memory exhausted**

```python
# Solution: Reduce model size hoặc batch size

# Option 1: Use smaller model
MODEL_PATH = "./detection/pro_models/yolov9s.pt"  # small instead of conv

# Option 2: Clear cache
import torch
torch.cuda.empty_cache()

# Option 3: Use CPU
detector = Detector(MODEL_PATH, device='cpu')
```

### **Problem: API connection failed**

```python
# Error: requests.exceptions.ConnectionError

# Check 1: Backend running?
curl http://localhost:8000/docs

# Check 2: Firewall blocking?
# Update TRAFFIC_API_URL to your machine IP
TRAFFIC_API_URL = "http://192.168.1.100:8000/detection"

# Check 3: Port in use?
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac
```

### **Problem: Zone coordinates wrong**

```python
# Issue: Vehicles not counted in zone

# Solution: Print frame + draw rectangles for debugging

import cv2

fig = camera.read()
success, frame = fig

# Draw zones
zone_manager.draw_zone(frame)

# Display
cv2.imshow("Debug", frame)
cv2.waitKey(0)

# Then adjust cam_01.json coordinates
```

### **Problem: Track ID jumping (not persistent)**

```python
# Issue: Same vehicle has different track_id each frame

# Reason: Tracker max_age too low, or detections missing

# Solution: Adjust tracker in engine/tracker.py
self.tracker = DeepSort(
    max_age=60,    # Increase from 30
    n_init=5,      # Require more detections to confirm
)
```

---

## 📈 Monitoring & Analytics

### **Real-time Dashboard Script**

```python
# dashboard.py
import time
from backend.database import SessionLocal
from backend.models.vehicle_detection import VehicleDetection

def print_stats():
    db = SessionLocal()
    
    while True:
        # Count current
        total = db.query(VehicleDetection).count()
        
        # Density distribution
        densities = db.query(VehicleDetection.density, 
                            func.count()).group_by(VehicleDetection.density).all()
        
        # Vehicle types
        types = db.query(VehicleDetection.vehicle_type,
                        func.count()).group_by(VehicleDetection.vehicle_type).all()
        
        print(f"\n=== STATS at {time.time()} ===")
        print(f"Total events: {total}")
        print(f"Densities: {dict(densities)}")
        print(f"Vehicle types: {dict(types)}")
        
        time.sleep(5)

if __name__ == "__main__":
    print_stats()
```

**Run**:
```bash
python dashboard.py
```

### **Export Data Script**

```python
# export_data.py
import pandas as pd
from backend.database import SessionLocal
from backend.models.vehicle_detection import VehicleDetection

db = SessionLocal()
detections = db.query(VehicleDetection).all()

# Create DataFrame
df = pd.DataFrame([{
    'event_id': d.event_id,
    'camera_id': d.camera_id,
    'vehicle_type': d.vehicle_type,
    'density': d.density,
    'confidence': d.confidence,
    'timestamp': d.timestamp
} for d in detections])

# Export
df.to_csv('detections_export.csv', index=False)
df.to_json('detections_export.json')

print(f"Exported {len(df)} records")
```

---

## 🧪 Testing

### **Unit Test Example**

```python
# test_detector.py
import cv2
import numpy as np
from detection.engine.detector import Detector

def test_detector_loads():
    detector = Detector("./detection/pro_models/best_final.pt")
    assert detector.model is not None
    print("✓ Model loaded successfully")

def test_detector_inference():
    detector = Detector("./detection/pro_models/best_final.pt")
    
    # Create dummy frame
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    # Run inference
    detections = detector.detect(frame)
    
    # Should return list
    assert isinstance(detections, list)
    print(f"✓ Inference returned {len(detections)} detections")

if __name__ == "__main__":
    test_detector_loads()
    test_detector_inference()
```

**Run**:
```bash
python test_detector.py
```

---

## 🔄 Production Deployment Checklist

- [ ] Database: Switch to PostgreSQL
- [ ] API: Enable authentication/authorization
- [ ] API: Add rate limiting
- [ ] API: Enable HTTPS (SSL certificate)
- [ ] Logging: Setup logging to file
- [ ] Monitoring: Setup health checks
- [ ] Error Handling: Setup error alerts
- [ ] Performance: Optimize model loading
- [ ] Scaling: Multi-process detection
- [ ] Documentation: Update deployment guide

---

## 📚 Useful Resources

### **YOLOv9**
- GitHub: https://github.com/WongKinYiu/yolov9
- Paper: https://arxiv.org/abs/2402.13616
- Docs: https://docs.ultralytics.com/

### **FastAPI**
- Official Docs: https://fastapi.tiangolo.com/
- Interactive Docs: http://localhost:8000/docs (when running)

### **Deep-SORT**
- GitHub: https://github.com/mikel-brostrom/yolov8_tracking
- Paper: https://arxiv.org/abs/1703.07402

### **OpenCV**
- Docs: https://docs.opencv.org/
- Tutorials: https://docs.opencv.org/4.x/d9/df8/tutorial_root.html

---

## 🎓 Learning Path

1. **Understand the architecture first**
   - Read ARCHITECTURE.md
   - Read FILE_STRUCTURE.md

2. **Run the system**
   - Start backend: `uvicorn backend.main:app --reload`
   - Start detection: `python detection/main.py`
   - Monitor data: `curl http://localhost:8000/raw-data`

3. **Experiment with configs**
   - Modify detection/configs_cameras/cam_01.json
   - Change zones to different image areas
   - Adjust FRAME_SKIP, TARGET_WIDTH, CONF_THRESHOLD

4. **Train custom model** (Advanced)
   - Prepare dataset in yolov9-cus/dataset/
   - Run training: `python yolov9-cus/yolov9/train.py`
   - Use new model: Update TRAFFIC_MODEL_PATH

5. **Optimize for production**
   - Benchmark performance
   - Setup PostgreSQL
   - Deploy on Docker/Kubernetes
   - Setup CI/CD pipeline

---

## ❓ FAQ

**Q: Làm sao để thêm camera mới?**  
A: Tạo file `cam_02.json` trong `configs_cameras/`, định nghĩa zones, sau đó update `CAMERA_ID` trong `detection/main.py`

**Q: Làm sao để tăng tốc độ xử lý?**  
A: Tăng `FRAME_SKIP`, giảm `TARGET_WIDTH`, sử dụng GPU (CUDA), hoặc dùng model nhỏ hơn

**Q: Dữ liệu được lưu ở đâu?**  
A: SQLite: `./traffic.db` (default), hoặc PostgreSQL (production config)

**Q: Làm sao để reset database?**  
A: Xóa file `traffic.db` hoặc chạy SQL: `DELETE FROM vehicle_detections;`

**Q: Model nào tốt nhất?**  
A: `best_final.pt` (custom trained, recommended) hoặc `yolov9c.pt` (pre-trained, general)

---
