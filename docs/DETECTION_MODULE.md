# 🚗 Detection Module - Nhận Diện & Theo Dõi Xe

**Detection Module** là thành phần cốt lõi của hệ thống, chịu trách nhiệm nhận diện xe từ video camera, theo dõi chúng qua các frame, phát sinh sự kiện khi xe qua vạch, và gửi dữ liệu lên Backend API.

---

## 📋 Tổng Quan Architecture

```
┌─────────────────────────────────────────────────────┐
│              Video Input (MP4 / Webcam)              │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│        FrameProcessor: Resize & Normalize            │
│        (Giảm resolution, enhance contrast)            │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│    Detector: YOLOv9 Inference                        │
│    - Load model từ .pt file                         │
│    - Infer bounding boxes & confidence              │
│    - Per-class confidence threshold                 │
│    Output: [bbox, confidence, class_id, class_name] │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│    Tracker: ByteTrack                               │
│    - Associate detections với track IDs             │
│    - Giữ ID khi xe bị occlusion (buffer: 90 frames) │
│    Output: [track_id, bbox, class_name, confidence] │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│    ZoneManager: Quản lý Zone & Kiểm Tra Giao       │
│    - Định nghĩa region-of-interest (ROI)           │
│    - Kiểm tra xe có qua zone nào không             │
│    - Tính direction (left/straight/right)          │
│    Output: zone_entry events                        │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│    DensityEstimator: Tính Mật Độ                   │
│    - Đếm số track trong rolling window             │
│    - Trả về LOW/MEDIUM/HIGH cho frame skip         │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│    EventGenerator: Tạo Sự Kiện                     │
│    - Tổng hợp tracking info + detection confidence │
│    - Tạo event_id duy nhất                         │
│    Output: VehicleDetection event JSON             │
└──────────────────────┬────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│    EventPublisher: Gửi lên Backend                 │
│    - POST /detection                                │
│    - Retry nếu fail                                │
└──────────────────────────────────────────────────────┘
```

---

## 🏗️ Cấu Trúc Thư Mục

```
detection/
├── main.py                    # Entry point: khởi tạo, vòng lặp chính
├── camera_engine.py           # Wrapper OpenCV: read frame, write video
│
├── engine/
│   ├── __init__.py
│   ├── detector.py            # YOLOv9 inference wrapper
│   ├── tracker.py             # ByteTrack wrapper
│   ├── frame_processor.py     # Resize, normalize frame
│   ├── density_estimator.py   # Tính mật độ từ track count
│   ├── zone_manager.py        # Quản lý zone, tính direction
│   ├── event_generator.py     # Tạo sự kiện detection
│   └── counter.py             # (deprecated) Số lượng xe
│
├── integration/
│   └── publisher.py           # Gửi event lên Backend API
│
├── configs_cameras/           # Zone definitions per camera
│   ├── cam01_zones.json
│   └── ...
│
├── pro_models/
│   └── yolov9_img960_ultimate.pt  # Trọng số YOLOv9 (bắt buộc)
│
├── ultralytics_yolov9/        # YOLOv9 core library
├── Ultralytics/               # Config dir cho YOLO
│
├── data/                      # (symbolic link hoặc thư mục dữ liệu)
├── output/                    # Video output sau khi process
└── README.md
```

---

## 🔧 Chi Tiết Các Thành Phần Chính

### 1. detector.py - YOLOv9 Inference

**Chức năng:** Load mô hình YOLOv9, chạy inference, phân tích bbox và confidence.

**Class: `Detector`**

```python
class Detector:
    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.40,
        img_size: int = 960,          # Target width
    )
```

**Parameters:**
- `model_path`: Đường dẫn file `.pt` (e.g., `pro_models/yolov9_img960_ultimate.pt`)
- `conf_threshold`: Độ tự tin tối thiểu global (0.0 - 1.0). Sẽ được override per-class
- `img_size`: Kích thước input chuẩn hóa (960px × aspect_ratio)

**Classes Được Hỗ Trợ:**
```python
VEHICLE_CLASSES = {
    0: "bus",
    1: "car",
    2: "motorcycle",      # Ngưỡng thấp hơn: 0.25
    3: "truck",
}

CLASS_CONF_THRESHOLD = {
    0: 0.40,  # bus
    1: 0.40,  # car
    2: 0.25,  # motorcycle (nhỏ, chiếm 70-80% traffic VN)
    3: 0.40,  # truck
}
```

**Output:**
```python
detections = [
    {
        "bbox": [x1, y1, x2, y2],           # Pixel coordinates
        "confidence": 0.91,                 # 0-1
        "class_id": 1,                      # 0-3
        "class_name": "car"
    },
    ...
]
```

**Công Nghệ:**
- ✅ Per-class confidence threshold (motorcycle được ưu đãi nhỏ hơn)
- ✅ GPU/CUDA support (auto-detect)
- ✅ VRAM auto-clear định kỳ (tránh leak)
- ✅ Flexible input size (chuẩn hóa theo aspect ratio)

---

### 2. tracker.py - ByteTrack

**Chức năng:** Gán track ID cho từng xe, duy trì ID qua occlusion.

**Class: `Tracker`**

```python
class Tracker:
    def __init__(
        self,
        track_activation_threshold: float = 0.35,
        lost_track_buffer: int = 90,         # ~3.6 sec @ 25FPS
        minimum_matching_threshold: float = 0.8,
    )
```

**Parameters:**
- `track_activation_threshold`: Độ tự tin tối thiểu để activate track (không phải ghost)
- `lost_track_buffer`: Số frame giữ ID khi xe bị occlusion. 90 frame ≈ 3.6 giây @ 25FPS → tránh double counting
- `minimum_matching_threshold`: Độ tương đồng tối thiểu để gán lại ID cũ

**Input:**
```python
detections = [
    {
        "bbox": [x1, y1, x2, y2],
        "confidence": 0.91,
        "class_id": 1,
        "class_name": "car"
    },
]
```

**Output:**
```python
tracks = [
    {
        "track_id": 948,                    # Unique ID
        "bbox": [x1, y1, x2, y2],
        "class_name": "car",
        "confidence": 0.91
    },
]
```

---

### 3. zone_manager.py - Quản Lý Zone

**Chức năng:** Định nghĩa region-of-interest (zone), kiểm tra xe có qua zone nào, tính hướng di chuyển.

**Class: `ZoneManager`**

```python
class ZoneManager:
    def __init__(self, zones_config: dict)
    
    def update_tracks(self, tracks: list) -> dict
    # Returns: {track_id: {zone_id, direction, ...}}
```

**Zone Configuration (JSON):**
```json
{
  "zones": [
    {
      "zone_id": "zone_straight",
      "polygon": [[0, 100], [960, 100], [960, 300], [0, 300]],
      "direction": "straight"
    },
    {
      "zone_id": "zone_left",
      "polygon": [[0, 0], [200, 0], [200, 100], [0, 100]],
      "direction": "left"
    }
  ]
}
```

**Algorithm:**
1. Check xe có nằm trong bất kỳ zone nào không (dùng `cv2.pointPolygonTest`)
2. Lưu trạng thái zone của mỗi track
3. Phát hiện zone_entry: track vừa vào zone lần đầu
4. Trả về direction dựa trên zone entry

**Output:**
```python
{
  948: {                # track_id
    "zone_id": "zone_straight",
    "direction": "straight",
    "entry_frame": 1234,
    "entered": True
  }
}
```

---

### 4. density_estimator.py - Tính Mật Độ

**Chức năng:** Ước tính mật độ giao thông từ số lượng xe trong rolling window. Dùng để điều chỉnh frame skip động.

**Class: `DensityEstimator`**

```python
class DensityEstimator:
    def __init__(self, window: int = 30)  # Rolling window
    
    def update(self, tracks: list) -> None
    
    def get_density(self) -> str  # LOW, MEDIUM, HIGH
    
    def get_avg_count(self) -> float
```

**Parameters:**
- `window`: 30 frame (với FRAME_SKIP=3 → ~90 frame thật ≈ 3-4 giây)

**Thresholds:**
```python
_THRESHOLDS = {
    "LOW": 5,          # < 5 xe trung bình
    "MEDIUM": 15,      # 5-15 xe
    "HIGH": >= 15      # >= 15 xe (tắc)
}
```

**Dùng cho:**
- ⚡ **Dynamic Frame Skip**: HIGH density → skip ít frame (mượt hơn), LOW → skip nhiều frame (tiết kiệm CPU)
- 📊 **Spike Detection**: So sánh `get_avg_count()` với baseline để phát hiện đột biến

**Output:**
```python
density = "MEDIUM"  # hay LOW, HIGH
avg_count = 12.5    # xe trung bình
```

---

### 5. event_generator.py - Tạo Sự Kiện

**Chức năng:** Kết hợp thông tin từ detector, tracker, zone_manager để tạo sự kiện VehicleDetection.

**Class: `EventGenerator`**

```python
class EventGenerator:
    def __init__(self, camera_id: str)
    
    def generate_event(
        self,
        track_id: int,
        bbox: list,
        class_name: str,
        confidence: float,
        direction: str,
        zone_id: str,
        timestamp: datetime,
        density: str
    ) -> dict
```

**Output Event:**
```json
{
  "event_id": "cam01_straight_001",        # Unique, hash-based
  "camera_id": "CAM_01",
  "track_id": 948,
  "vehicle_type": "car",
  "density": "MEDIUM",
  "event_type": "zone_entry",
  "direction": "straight",
  "timestamp": "2026-05-23T02:00:15Z",    # ISO 8601
  "confidence": 0.91
}
```

**Event ID Generation:**
```python
event_id = hashlib.sha256(
    f"{camera_id}_{track_id}_{zone_id}_{timestamp.isoformat()}".encode()
).hexdigest()[:16]
```

---

### 6. publisher.py - Gửi Sự Kiện

**Chức năng:** Gửi event lên Backend API via HTTP POST, handle retry & error.

**Class: `EventPublisher`**

```python
class EventPublisher:
    def __init__(self, api_url: str, timeout: int = 5)
    
    def publish(self, event: dict) -> bool
    # Returns: True nếu success (200-299), False nếu fail
```

**Logic:**
1. POST event đến `API_URL/detection`
2. Check response status:
   - ✅ 200-299: Success, log "Event sent"
   - ⚠️ 409 Conflict: Event tồn tại rồi, bỏ qua (không retry)
   - ❌ Khác: Retry 3 lần với exponential backoff (1s, 2s, 4s)

**Error Handling:**
```python
try:
    response = requests.post(
        f"{self.api_url}",
        json=event,
        timeout=self.timeout
    )
    if response.status_code == 409:
        logging.info("Event already exists (duplicate)")
        return True  # Treat as success
    return response.status_code < 300
except requests.exceptions.RequestException as e:
    logging.error(f"Network error: {e}")
    return False
```

---

## ⚙️ Cấu Hình Hệ Thống (main.py)

### Environment Variables

```bash
# Video & Model
TRAFFIC_VIDEO_SOURCE=data/video/cam01-traffic3.mp4  # hoặc 0 cho webcam
TRAFFIC_MODEL_PATH=detection/pro_models/yolov9_img960_ultimate.pt
TRAFFIC_API_URL=http://127.0.0.1:8000/detection
CONF_THRESHOLD=0.40

# Chế độ chạy
SYNC_MODE=false              # true=hiển thị cửa sổ, false=async (video mượt)
NO_DISPLAY=true              # Không render video
PLAYBACK_SPEED=1.0           # 0.5 = chậm 2x

# Log & Output
ALERT_LOG=alerts.csv         # Log cảnh báo mật độ cao
OUTPUT_VIDEO=output_v5.mp4   # Video output

# Nâng cao
DRY_RUN=false                # Không gửi HTTP, chỉ test
FRAME_SKIP=3                 # Skip 2 frame, chạy 1 frame
```

### Global Parameters

```python
API_URL = "http://127.0.0.1:8000/detection"
VIDEO_SOURCE = "data/video/cam01-traffic3.mp4"
MODEL_PATH = "detection/pro_models/yolov9_img960_ultimate.pt"
OUTPUT_VIDEO = "output_v5.mp4"
ALERT_LOG = ""
CONF_THRESHOLD = 0.40
TARGET_WIDTH = 960                # Chuẩn hóa độ rộng frame
FRAME_SKIP = 3                    # Dynamic skip (1/3 frame được process)
```

---

## 🎬 Vòng Lặp Chính (main.py)

```python
while True:
    # 1. Đọc frame từ video
    ret, frame = cap.read()
    if not ret:
        break

    # 2. Tiền xử lý: resize & normalize
    frame_proc = frame_processor.process(frame)

    # 3. Nhận diện (skip frame động)
    if frame_count % FRAME_SKIP == 0:
        detections = detector.detect(frame_proc)
    
    # 4. Theo dõi
    tracks = tracker.update(detections)
    
    # 5. Cập nhật zone & direction
    zones_info = zone_manager.update_tracks(tracks)
    
    # 6. Tính mật độ
    density_estimator.update(tracks)
    density = density_estimator.get_density()
    
    # 7. Phát sinh sự kiện & gửi lên API
    for track in tracks:
        if zones_info[track['track_id']]['entered']:
            event = event_generator.generate_event(...)
            publisher.publish(event)
    
    # 8. Render (nếu không NO_DISPLAY)
    if not NO_DISPLAY:
        draw_results(frame, tracks, zones, density)
        cv2.imshow('Detection', frame)
    
    # 9. Ghi video (nếu OUTPUT_VIDEO)
    video_writer.write(frame_with_annotations)
    
    # 10. Tự động tính toán aggregation mỗi 15 phút
    if time_since_last_compute > 900:  # 900s = 15 min
        requests.post(
            f"{API_URL}/aggregation/compute",
            json={"camera_id": camera_id, ...}
        )

    frame_count += 1
    
    # Handle keyboard interrupt
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

---

## 📊 Luồng Dữ Liệu Chi Tiết

```
Frame 1
  ├─ Resize 1920×1080 → 960×540
  ├─ YOLOv9: Detect 8 objects
  │   └─ Filter: 5 cars (conf > 0.40), 2 motorcycles (conf > 0.25), 1 motorcycle rejected
  ├─ ByteTrack: Associate với tracks cũ
  │   └─ Output: [ID:1, ID:2, ID:3, ID:5] (ID:4 đã mất 20 frame)
  ├─ ZoneManager: Check zones
  │   ├─ ID:1 nằm trong zone_straight → direction="straight"
  │   └─ ID:2 vừa vào zone_straight (entry_frame=1, entered=True)
  ├─ DensityEstimator: avg_count=4 → "LOW"
  ├─ EventGenerator:
  │   ├─ ID:2 zone_entry → event_id="abc123def456"
  │   └─ Event: {camera: CAM_01, direction: straight, confidence: 0.91, ...}
  ├─ EventPublisher:
  │   └─ POST /detection → 200 OK
  └─ Render + Save video frame

Frame 2 (skip vì FRAME_SKIP=3)
  └─ Chỉ update tracks từ frame 1, không detect lại

Frame 3 (skip)
  └─ Chỉ update tracks từ frame 1, không detect lại

Frame 4
  ├─ Detect lại (mỗi 3 frame)
  ├─ Update tracks & zones
  └─ ...
```

---

## 🚀 Lệnh Chạy

### Mode 1: Đơn Giản (Hiển Thị Cửa Sổ)

```bash
python -m detection.main
```

- Video chậm do xử lý real-time
- Hiển thị live preview
- Tiết kiệm CPU

### Mode 2: Async (Video Mượt)

```bash
SYNC_MODE=false python -m detection.main
```

- Video mượt hơn (không chờ render)
- Xử lý nhanh hơn
- Khuyên dùng cho production

### Mode 3: Headless (Không Hiển Thị)

```bash
NO_DISPLAY=true python -m detection.main
```

- Chạy trên server không có display
- Tốc độ nhanh nhất

### Mode 4: Chậm 2x (Debug)

```bash
PLAYBACK_SPEED=0.5 SYNC_MODE=false python -m detection.main
```

- Phát lại video chậm để debug
- Dùng khi muốn xem chi tiết tracking

### Mode 5: Với Log Cảnh Báo

```bash
ALERT_LOG=alerts.csv python -m detection.main
```

- Ghi mỗi sự kiện mật độ cao (HIGH) hoặc spike vào CSV
- Format: `timestamp,camera_id,density,count,alert_type`

---

## 📈 Performance Tips

| Tình Huống | Giải Pháp |
|-----------|---------|
| CUDA out of memory | Giảm `TARGET_WIDTH` từ 960 → 640, hoặc bật `SYNC_MODE=true` |
| Video quá chậm | Bật `SYNC_MODE=false`, tăng `FRAME_SKIP` từ 3 → 5 |
| Bỏ sót xe nhỏ | Giảm `CONF_THRESHOLD` hoặc xem chắc motorcycle có conf 0.25 |
| API timeout | Tăng `timeout` trong `publisher.py` hoặc kiểm tra Backend network |

---

## 🧪 Testing

### Test Detector

```python
from detection.engine.detector import Detector
import cv2

detector = Detector("detection/pro_models/yolov9_img960_ultimate.pt")
frame = cv2.imread("test_frame.jpg")
detections = detector.detect(frame)
print(detections)
```

### Test Tracker

```python
from detection.engine.tracker import Tracker

tracker = Tracker()
detections = [{"bbox": [100, 100, 200, 200], "class_id": 1, "class_name": "car", "confidence": 0.9}]
tracks = tracker.update(detections)
print(tracks)
```

### Test Zone Manager

```python
import json
from detection.engine.zone_manager import ZoneManager

with open("detection/configs_cameras/cam01_zones.json") as f:
    zones_config = json.load(f)

zone_mgr = ZoneManager(zones_config)
tracks = [{"track_id": 1, "bbox": [100, 150, 200, 250]}]
zones_info = zone_mgr.update_tracks(tracks)
print(zones_info)
```

---

## 🐛 Troubleshooting

| Lỗi | Nguyên Nhân | Giải Pháp |
|-----|-----------|---------|
| `Model not found` | File `.pt` không tồn tại | Kiểm tra `TRAFFIC_MODEL_PATH` |
| `CUDA out of memory` | Model quá lớn cho GPU | Giảm `TARGET_WIDTH` hoặc dùng CPU |
| `No detections` | Confidence threshold quá cao | Giảm `CONF_THRESHOLD` |
| `Double counting` | Track_id bị reset sau occlusion | Tăng `lost_track_buffer` (90 là reasonable) |
| `API 409 Conflict` | Event_id bị trùng | Bình thường, publisher sẽ bỏ qua |

---

## 📝 Ghi Chú

- ✅ **YOLOv9 đã train** với 4 class: bus, car, motorcycle, truck
- ✅ **Per-class confidence**: motorcycle (0.25) vs other (0.40) để minimize bỏ sót
- ✅ **ByteTrack buffer**: 90 frame ≈ 3.6 giây @ 25FPS → tránh double counting
- ✅ **Zone entry detection**: Chỉ phát sinh event lần đầu xe qua vạch
- ✅ **Automatic aggregation**: Mỗi 15 phút detection tự gọi `/aggregation/compute`

---

## 📚 Tham Khảo

- [YOLOv9 Repository](https://github.com/WongKinYiu/yolov9)
- [ByteTrack Paper](https://arxiv.org/abs/2110.06864)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Supervision Library](https://supervision.roboflow.com/)

**Cập nhật lần cuối:** 2026-05-31