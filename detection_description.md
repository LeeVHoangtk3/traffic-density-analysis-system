# Mô tả chi tiết Folder Detection

## Tổng quan
Folder `detection` là module chính của hệ thống phân tích mật độ giao thông, chịu trách nhiệm phát hiện, theo dõi và đếm các phương tiện giao thông từ video camera. Module này sử dụng công nghệ AI tiên tiến (YOLOv9) để phát hiện phương tiện và DeepSort để theo dõi, kết hợp với các tính năng ước tính mật độ và quản lý vùng giám sát.

## Chức năng chính
- **Phát hiện phương tiện**: Sử dụng YOLOv9 để nhận diện xe hơi, xe máy, xe buýt, xe tải
- **Theo dõi phương tiện**: Theo dõi quỹ đạo di chuyển của từng phương tiện qua thời gian
- **Đếm phương tiện**: Đếm số lượng phương tiện qua các vùng giám sát
- **Ước tính mật độ**: Phân loại mật độ giao thông (LOW/MEDIUM/HIGH)
- **Tạo sự kiện**: Phát sinh sự kiện khi phương tiện qua vùng giám sát
- **Xuất bản dữ liệu**: Gửi dữ liệu đến API backend để lưu trữ và phân tích

## Cấu trúc thư mục

```
detection/
├── __init__.py                 # Khởi tạo module
├── main.py                     # Entry point chính
├── camera_engine.py            # Engine xử lý camera/video
├── configs_cameras/            # Cấu hình camera
│   └── cam_01.json
├── engine/                     # Core processing engine
│   ├── __init__.py
│   ├── counter.py              # Đếm phương tiện
│   ├── density_estimator.py    # Ước tính mật độ
│   ├── detector.py             # Phát hiện phương tiện (YOLOv9)
│   ├── event_generator.py      # Tạo sự kiện
│   ├── frame_processor.py      # Xử lý frame
│   ├── tracker.py              # Theo dõi phương tiện (DeepSort)
│   └── zone_manager.py         # Quản lý vùng giám sát
├── integration/                # Tích hợp với hệ thống
│   ├── __init__.py
│   └── publisher.py            # Xuất bản sự kiện
├── pro_models/                 # Models YOLOv9 đã train
│   ├── __init__.py
│   ├── best_final.pt
│   ├── yolov9_img960_ultimate.pt
│   ├── yolov9_ultimate_final.pt
│   └── yolov9c.pt
└── Ultralytics/                # Thư viện Ultralytics tùy chỉnh
    └── ultralytics_yolov9/
        ├── models/
        └── utils/
```

## Các Module và Class

### 1. main.py
**Chức năng**: Entry point chính của module detection
**Cách hoạt động**:
- Khởi tạo tất cả components
- Vòng lặp chính xử lý video frame-by-frame
- Tích hợp pipeline: Camera → Processor → Detector → Tracker → Counter → Publisher

**Các thành phần chính**:
- CameraEngine: Đọc video
- FrameProcessor: Tiền xử lý frame
- Detector: Phát hiện phương tiện
- Tracker: Theo dõi
- VehicleCounter: Đếm
- DensityEstimator: Ước tính mật độ
- EventGenerator: Tạo sự kiện
- EventPublisher: Xuất bản
- ZoneManager: Quản lý vùng

### 2. camera_engine.py
**Class**: CameraEngine
**Chức năng**: Xử lý nguồn video/camera
**Methods**:
- `__init__(source)`: Khởi tạo với đường dẫn video hoặc camera ID
- `read()`: Đọc frame tiếp theo
- `release()`: Giải phóng tài nguyên

**Thư viện**: OpenCV (cv2.VideoCapture)

### 3. engine/frame_processor.py
**Class**: FrameProcessor
**Chức năng**: Tiền xử lý frame video
**Methods**:
- `__init__(target_width=640)`: Khởi tạo với chiều rộng mục tiêu
- `process(frame)`: Resize frame để tối ưu hiệu suất

**Thư viện**: OpenCV

### 4. engine/detector.py
**Class**: Detector
**Chức năng**: Phát hiện phương tiện sử dụng YOLOv9
**Cách hoạt động**:
- Load model YOLOv9 từ file .pt
- Tiền xử lý frame (resize, normalize)
- Inference với model
- Post-processing: NMS, filter theo confidence
- Mapping class ID sang tên phương tiện

**Classes hỗ trợ**:
- bus (0)
- car (1)
- motorcycle (2)
- truck (3)

**Thư viện**: PyTorch, Torchvision, OpenCV, NumPy

### 5. engine/tracker.py
**Class**: Tracker
**Chức năng**: Theo dõi phương tiện qua các frame
**Cách hoạt động**:
- Sử dụng DeepSort algorithm
- Update tracks với detections mới
- Maintain track ID cho từng phương tiện

**Thư viện**: deep-sort-realtime

### 6. engine/counter.py
**Class**: VehicleCounter
**Chức năng**: Đếm số lượng phương tiện
**Methods**:
- `count(class_name)`: Tăng counter cho loại phương tiện
- `get_totals()`: Lấy tổng số theo loại
- `get_per_minute()`: Lấy số lượng theo phút

**Thư viện**: collections.defaultdict, time

### 7. engine/density_estimator.py
**Class**: DensityEstimator
**Chức năng**: Ước tính mật độ giao thông
**Logic**:
- < 5 phương tiện: LOW
- 5-15 phương tiện: MEDIUM
- > 15 phương tiện: HIGH

### 8. engine/zone_manager.py
**Class**: ZoneManager
**Chức năng**: Quản lý vùng giám sát (zones)
**Methods**:
- `check_crossing(track_id, cx, cy)`: Kiểm tra phương tiện có qua zone không
- `draw_zone(frame)`: Vẽ vùng giám sát lên frame

**Thư viện**: OpenCV, NumPy

### 9. engine/event_generator.py
**Class**: EventGenerator
**Chức năng**: Tạo sự kiện khi phương tiện qua zone
**Event structure**:
```json
{
  "event_id": "uuid",
  "camera_id": "CAM_01",
  "track_id": 123,
  "vehicle_type": "car",
  "density": "MEDIUM",
  "event_type": "line_crossing",
  "timestamp": 1640995200.0
}
```

**Thư viện**: uuid, time

### 10. integration/publisher.py
**Class**: EventPublisher
**Chức năng**: Gửi sự kiện đến API backend
**Methods**:
- `publish(event)`: POST event qua HTTP

**Thư viện**: requests

## Cách hoạt động tổng thể

### Pipeline xử lý:
1. **Đọc frame**: CameraEngine đọc frame từ video
2. **Tiền xử lý**: FrameProcessor resize frame
3. **Phát hiện**: Detector sử dụng YOLOv9 để tìm phương tiện
4. **Theo dõi**: Tracker cập nhật quỹ đạo phương tiện
5. **Ước tính mật độ**: DensityEstimator tính mật độ dựa trên số track
6. **Kiểm tra zone**: ZoneManager kiểm tra phương tiện có qua vùng không
7. **Đếm**: VehicleCounter tăng counter nếu qua zone
8. **Tạo sự kiện**: EventGenerator tạo event
9. **Xuất bản**: Publisher gửi event đến API

### Tối ưu hiệu suất:
- **Frame skip**: Chỉ xử lý mỗi N frame (FRAME_SKIP=3)
- **Resize**: Giảm resolution xuống 640px width
- **Confidence threshold**: Lọc detections yếu (CONF_THRESHOLD=0.5)
- **NMS**: Loại bỏ overlapping boxes

## Thư viện và Công nghệ

### Core AI:
- **PyTorch**: Framework deep learning
- **Torchvision**: Computer vision utilities
- **Ultralytics YOLOv9**: Model phát hiện object
- **DeepSort**: Algorithm tracking
- **OpenCV**: Computer vision processing
- **NumPy**: Numerical computing

### Utilities:
- **Requests**: HTTP client
- **UUID**: Generate unique IDs
- **Time**: Timestamp handling
- **Collections**: Data structures
- **JSON**: Configuration parsing

### Models:
- YOLOv9 custom trained models (.pt files)
- Support COCO classes và custom classes

## Cấu hình

### Environment Variables:
- `TRAFFIC_API_URL`: URL API backend (default: http://127.0.0.1:8000/detection)
- `TRAFFIC_VIDEO_SOURCE`: Đường dẫn video source
- `TRAFFIC_MODEL_PATH`: Đường dẫn model YOLOv9

### Camera Config (JSON):
```json
{
  "camera_id": "CAM_01",
  "zones": [
    {
      "id": "main_detection_zone",
      "points": [[x1,y1], [x2,y2], ...]
    }
  ]
}
```

## Hiệu suất và Tối ưu

### Thông số kỹ thuật:
- **Frame rate**: ~10-30 FPS (tùy config)
- **Accuracy**: >90% detection accuracy
- **Memory**: ~2-4GB GPU memory
- **CPU/GPU**: Support cả CPU và GPU inference

### Tối ưu:
- Multi-threading không sử dụng (đơn giản hóa)
- Batch processing không áp dụng
- Memory efficient với frame skip
- Real-time processing với low latency

## Tích hợp với hệ thống

### API Integration:
- POST events đến `/detection` endpoint
- Timeout 1s cho mỗi request
- Error handling với try/catch

### Data Flow:
Detection Module → Backend API → Database → ML Service → Integration System

### Monitoring:
- Console logging cho events
- Visual feedback với OpenCV imshow
- Density display trên video
- Vehicle count display

## Phát triển và Bảo trì

### Dependencies:
- Python 3.8+
- CUDA (tùy chọn cho GPU)
- Compatible với Windows/Linux/macOS

### Testing:
- Unit tests cho từng class
- Integration tests với video samples
- Performance benchmarks

### Deployment:
- Standalone execution
- Docker containerization
- Cloud deployment (Azure/AWS)

---

*Module này được thiết kế để có thể mở rộng dễ dàng với nhiều camera, nhiều zone, và tích hợp với các hệ thống lớn hơn.*