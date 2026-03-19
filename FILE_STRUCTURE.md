# 📁 FILE STRUCTURE & DEPENDENCIES

## Tổng quan cây file

```
traffic-density-analysis-system/
│
├── 📄 README.md                          # Tài liệu dự án
├── 📄 requirements.txt                   # Dependencies (53 packages)
├── 📄 TODO.md                            # Hướng dẫn chạy
├── 📄 ARCHITECTURE.md                    # Kiến trúc hệ thống (NEW)
├── 📄 MODULES_DETAILED.md                # Chi tiết modules (NEW)
│
├── 📓 traffic_density_git_project.ipynb  # Jupyter notebook
├── 🤖 yolov9c.pt                         # Pre-trained YOLOv9 model
│
│
├── 📂 backend/                           # ✨ BACKEND API MODULE
│   ├── 📄 main.py                        # FastAPI application entry
│   │   │   Imports:
│   │   │   ├─ FastAPI, Base, models
│   │   │   ├─ database.py → engine, Base
│   │   │   └─ api routes
│   │   │   Khởi tạo: FastAPI app, DB tables, routers
│   │   │
│   │   └─ Endpoints:
│   │       ├─ POST /detection
│   │       ├─ GET /raw-data
│   │       ├─ GET /aggregation
│   │       └─ GET /prediction
│   │
│   ├── 📄 database.py                    # SQLAlchemy setup
│   │   │   Exports: engine, SessionLocal, Base
│   │   │   DatabaseURL: sqlite:///./traffic.db
│   │   │   Function: sync_vehicle_detection_schema()
│   │   │
│   │   └─ Used by:
│   │       ├─ main.py (create tables)
│   │       ├─ services/db_service.py
│   │       └─ models/* (inherit Base)
│   │
│   │
│   ├── 📂 models/                        # ORM Models (SQLAlchemy)
│   │   ├── 📄 camera.py
│   │   │   │   Inherits: Base
│   │   │   │   Table: cameras
│   │   │   │   Columns: id, name, location
│   │   │   │
│   │   │   ├── 📄 vehicle_detection.py
│   │   │   │   │   Inherits: Base
│   │   │   │   │   Table: vehicle_detections
│   │   │   │   │   Columns: id, event_id, camera_id, track_id,
│   │   │   │   │            vehicle_type, density, event_type,
│   │   │   │   │            confidence, timestamp
│   │   │   │   │
│   │   │   │   ├── 📄 traffic_aggregation.py
│   │   │   │   │   │   Inherits: Base
│   │   │   │   │   │   Table: traffic_aggregation
│   │   │   │   │   │   Columns: id, camera_id, vehicle_count,
│   │   │   │   │   │            congestion_level, timestamp
│   │   │   │   │   │
│   │   │   │   └── 📄 traffic_prediction.py
│   │   │           │   Inherits: Base
│   │   │           │   Table: traffic_predictions
│   │   │           │   Columns: id, predicted_density, timestamp
│   │   │           │
│   │   │           └─ Used by:
│   │   │               └─ main.py (create_all)
│   │   │
│   │
│   ├── 📂 schemas/                       # Pydantic Models (Validation)
│   │   ├── 📄 detection_schema.py
│   │   │   │   Pydantic: DetectionCreate
│   │   │   │   Fields: event_id, camera_id, track_id, vehicle_type,
│   │   │   │           density, event_type, timestamp, confidence
│   │   │   │
│   │   │   ├── 📄 aggregation_schema.py  # (Optional)
│   │   │   ├── 📄 prediction_schema.py   # (Optional)
│   │   │   └── 📄 traffic_schema.py      # (Optional)
│   │   │
│   │   └─ Used by:
│   │       └─ api/detection_routes.py (validate input)
│   │
│   │
│   ├── 📂 api/                           # FastAPI Routers
│   │   ├── 📄 detection_routes.py
│   │   │   │   Router prefix: (root)
│   │   │   │   Endpoint: POST /detection
│   │   │   │   Function: create_detection(data: DetectionCreate, db: Session)
│   │   │   │   Logic: Create VehicleDetection ORM → save to DB
│   │   │   │
│   │   │   ├── 📄 traffic_routes.py
│   │   │   │   │   Router prefix: (root)
│   │   │   │   │   Endpoint: GET /raw-data
│   │   │   │   │   Function: get_raw_data(db: Session)
│   │   │   │   │   Logic: Query all VehicleDetections
│   │   │   │   │
│   │   │   ├── 📄 aggregation_routes.py
│   │   │   │   │   Router prefix: (root)
│   │   │   │   │   Endpoint: GET /aggregation?vehicle_count=<int>
│   │   │   │   │   Function: get_aggregation(vehicle_count: int)
│   │   │   │   │   Logic: Call aggregation_service.compute_congestion()
│   │   │   │   │
│   │   │   └── 📄 prediction_routes.py
│   │   │       │   (Not fully implemented)
│   │   │       │   Placeholder for prediction endpoint
│   │   │       │
│   │   │       └─ Used by:
│   │   │           └─ main.py (include_router)
│   │   │
│   │
│   ├── 📂 services/                      # Business Logic
│   │   ├── 📄 db_service.py
│   │   │   │   Function: get_db() → Generator[Session]
│   │   │   │   Purpose: FastAPI dependency for DB session
│   │   │   │
│   │   │   ├── 📄 aggregation_service.py
│   │   │   │   │   Function: compute_congestion(vehicle_count: int) → str
│   │   │   │   │   Logic: Map vehicle_count ranges to congestion levels
│   │   │   │   │
│   │   │   │   └─ Used by:
│   │   │   │       └─ api/aggregation_routes.py
│   │   │   │
│   │   │   └─ Used by:
│   │   │       ├─ api/detection_routes.py (get_db dependency)
│   │   │       ├─ api/traffic_routes.py
│   │   │       └─ api/aggregation_routes.py
│   │   │
│   │
│   └── 📂 __pycache__/                   # Compiled Python bytecode
│
│
├── 📂 detection/                         # ✨ DETECTION ENGINE MODULE
│   ├── 📄 main.py                        # Entry point (detection pipeline)
│   │   │   Orchestrates all components
│   │   │   Flow:
│   │   │   ├─ Load config (camera, model paths)
│   │   │   ├─ Initialize components
│   │   │   ├─ Main loop:
│   │   │   │  ├─ Read frame
│   │   │   │  ├─ Detect objects
│   │   │   │  ├─ Track objects
│   │   │   │  ├─ Check zone crossing
│   │   │   │  ├─ Publish event
│   │   │   │  └─ Visualize (optional)
│   │   │   └─ Cleanup
│   │   │
│   │   │   Imports:
│   │   │   ├─ CameraEngine (camera_engine.py)
│   │   │   ├─ FrameProcessor (engine/frame_processor.py)
│   │   │   ├─ Detector (engine/detector.py)
│   │   │   ├─ Tracker (engine/tracker.py)
│   │   │   ├─ VehicleCounter (engine/counter.py)
│   │   │   ├─ DensityEstimator (engine/density_estimator.py)
│   │   │   ├─ ZoneManager (engine/zone_manager.py)
│   │   │   ├─ EventGenerator (engine/event_generator.py)
│   │   │   ├─ EventPublisher (integration/publisher.py)
│   │   │   └─ json (load config)
│   │   │
│   │
│   ├── 📄 camera_engine.py               # 🎥 Video Input
│   │   │   Class: CameraEngine
│   │   │   Methods:
│   │   │   ├─ __init__(source)
│   │   │   ├─ read() → (bool, np.ndarray)
│   │   │   └─ release()
│   │   │   Wrapper around cv2.VideoCapture
│   │   │
│   │   └─ Used by:
│   │       └─ main.py
│   │
│   │
│   ├── 📂 engine/                        # 🧠 Detection & Tracking Core
│   │   ├── 📄 frame_processor.py
│   │   │   │   Class: FrameProcessor
│   │   │   │   Purpose: Resize frame maintaining aspect ratio
│   │   │   │   Method: process(frame) → resized_frame
│   │   │   │
│   │   │   ├── 📄 detector.py
│   │   │   │   │   Class: Detector
│   │   │   │   │   Purpose: YOLOv9 object detection
│   │   │   │   │   Methods:
│   │   │   │   │   ├─ __init__(model_path, conf_threshold)
│   │   │   │   │   └─ detect(frame) → [detection, ...]
│   │   │   │   │   Detection format:
│   │   │   │   │   {bbox, confidence, class_name}
│   │   │   │   │
│   │   │   ├── 📄 tracker.py
│   │   │   │   │   Class: Tracker
│   │   │   │   │   Purpose: Multi-object tracking (DeepSort)
│   │   │   │   │   Methods:
│   │   │   │   │   ├─ __init__()
│   │   │   │   │   └─ update(detections, frame) → [track, ...]
│   │   │   │   │   Track format:
│   │   │   │   │   {track_id, bbox, class_name}
│   │   │   │   │
│   │   │   ├── 📄 counter.py
│   │   │   │   │   Class: VehicleCounter
│   │   │   │   │   Purpose: Count vehicles by class & per-minute stats
│   │   │   │   │   Methods:
│   │   │   │   │   ├─ count(class_name)
│   │   │   │   │   ├─ get_totals() → dict
│   │   │   │   │   └─ get_per_minute() → Optional[dict]
│   │   │   │   │
│   │   │   ├── 📄 density_estimator.py
│   │   │   │   │   Class: DensityEstimator
│   │   │   │   │   Purpose: Calculate traffic density level
│   │   │   │   │   Methods:
│   │   │   │   │   ├─ update(tracks)
│   │   │   │   │   └─ get_density() → "LOW"|"MEDIUM"|"HIGH"
│   │   │   │   │
│   │   │   ├── 📄 zone_manager.py
│   │   │   │   │   Class: ZoneManager
│   │   │   │   │   Purpose: Manage detection zones (ROI)
│   │   │   │   │   Methods:
│   │   │   │   │   ├─ __init__(zones)
│   │   │   │   │   ├─ check_crossing(track_id, cx, cy) → bool
│   │   │   │   │   └─ draw_zone(frame)
│   │   │   │   │   Polygon-based zone detection
│   │   │   │   │
│   │   │   ├── 📄 event_generator.py
│   │   │   │   │   Class: EventGenerator
│   │   │   │   │   Purpose: Create event objects
│   │   │   │   │   Method:
│   │   │   │   │   └─ generate(camera_id, track, density) → event_dict
│   │   │   │   │   Event format:
│   │   │   │   │   {event_id, camera_id, track_id, vehicle_type,
│   │   │   │   │    density, event_type, timestamp}
│   │   │   │   │
│   │   │   └── 📂 __pycache__/
│   │   │
│   │
│   ├── 📂 integration/                   # 📡 Backend Integration
│   │   ├── 📄 publisher.py
│   │   │   │   Class: EventPublisher
│   │   │   │   Purpose: Send events to backend API (HTTP)
│   │   │   │   Methods:
│   │   │   │   ├─ __init__(api_url)
│   │   │   │   └─ publish(event) → None (non-blocking)
│   │   │   │   Timeout: 1 second
│   │   │   │
│   │   │   └─ Used by:
│   │   │       └─ main.py
│   │   │
│   │   └── 📂 __pycache__/
│   │
│   │
│   ├── 📂 configs_cameras/               # 📋 Camera Configuration
│   │   └── 📄 cam_01.json
│   │       │   JSON format:
│   │       │   {
│   │       │     "camera_id": "CAM_01",
│   │       │     "zones": [
│   │       │       {
│   │       │         "id": "zone_name",
│   │       │         "points": [[x1,y1], [x2,y2], ...]
│   │       │       }
│   │       │     ]
│   │       │   }
│   │       │
│   │       └─ Used by:
│   │           └─ main.py (ZoneManager initialization)
│   │
│   │
│   ├── 📂 pro_models/                    # 🤖 Pre-trained Models
│   │   ├── 📄 best_final.pt              # Custom trained YOLOv9
│   │   │   │   Classes: bus, car, motorcycle, truck
│   │   │   │   Size: ~50MB
│   │   │   │
│   │   │   ├── 📄 yolov9c.pt             # Pre-trained YOLOv9-compact
│   │   │   │   Classes: COCO 80 classes
│   │   │   │   Size: ~50MB
│   │   │   │
│   │   │   └─ Used by:
│   │           └─ engine/detector.py (model loading)
│   │
│   │
│   ├── 📂 ultralytics_yolov9/            # 🎯 YOLOv9 Implementation
│   │   ├── 📂 models/
│   │   │   ├── yolo.py                   # YOLO model class
│   │   │   ├── common.py                 # Common components
│   │   │   ├── experimental.py           # Experimental models
│   │   │   ├─ ... (detect, segment, panoptic subdirs)
│   │   │   └── 📂 __pycache__/
│   │   │
│   │   ├── 📂 utils/
│   │   │   ├── general.py                # General utilities
│   │   │   ├── activations.py            # Activation functions
│   │   │   ├── augmentations.py          # Data augmentation
│   │   │   ├── autoanchor.py             # Auto anchor calculation
│   │   │   ├── loss.py                   # Loss functions
│   │   │   ├── metrics.py                # Evaluation metrics
│   │   │   ├── callbacks.py              # Training callbacks
│   │   │   └── ... (other utils)
│   │   │
│   │   └─ Used by:
│   │       └─ engine/detector.py (YOLO core functionality)
│   │
│   │
│   └── 📂 __pycache__/
│
│
├── 📂 intergration/                      # (Typo: "intergration" instead of "integration")
│   │   Appears to be empty or placeholder
│
│
├── 📂 yolov9-cus/                        # 🏋️ Training & Inference
│   ├── 📄 test_model.py
│   │   │   Script: Test custom-trained models
│   │   │   Usage: Run detection on test images
│   │   │
│   │
│   ├── 📂 dataset/
│   │   ├── 📄 data.yaml                  # Dataset configuration
│   │   │   │   path: dataset paths
│   │   │   │   train: ./train/images
│   │   │   │   val: ./val/images
│   │   │   │   test: ./test/images
│   │   │   │   nc: 4 (number of classes)
│   │   │   │   names: [bus, car, motorcycle, truck]
│   │   │   │
│   │   │
│   │   ├── 📂 train/
│   │   │   ├── 📂 images/                # Training images
│   │   │   └── 📂 labels/                # YOLO format labels
│   │   │
│   │   ├── 📂 val/
│   │   │   ├── 📂 images/                # Validation images
│   │   │   └── 📂 labels/                # Validation labels
│   │   │
│   │   └── 📂 test/
│   │       ├── 📂 images/                # Test images
│   │       └── 📂 labels/                # Test labels
│   │
│   │
│   ├── 📂 runs/
│   │   └── 📂 detect/
│   │       └── 📂 test_results/          # Detection results
│   │           └── Visualization images
│   │
│   │
│   ├── 📂 weights/
│   │   │   (Directory for trained weights)
│   │   │
│   │
│   ├── 📂 yolov9/
│   │   ├── 📄 train.py                   # Training script
│   │   ├── 📄 val.py                     # Validation script
│   │   ├── 📄 detect.py                  # Detection script
│   │   ├── 📄 export.py                  # Model export
│   │   ├── 📄 train_dual.py              # Dual training
│   │   ├── 📄 train_triple.py            # Triple training
│   │   ├── 📄 val_dual.py
│   │   ├── 📄 val_triple.py
│   │   ├── 📄 detect_dual.py
│   │   ├── 📄 hubconf.py                 # Hub configuration
│   │   ├── 📄 benchmarks.py              # Benchmarking
│   │   ├── 📄 requirements.txt           # YOLOv9 dependencies
│   │   ├── 📄 LICENSE.md
│   │   ├── 📄 README.md
│   │   │
│   │   ├── 📂 models/                    # Model architectures
│   │   ├── 📂 segment/                   # Segmentation models
│   │   ├── 📂 panoptic/                  # Panoptic models
│   │   ├── 📂 classify/                  # Classification
│   │   ├── 📂 utils/                     # Utilities
│   │   ├── 📂 tools/                     # Tools
│   │   └── 📂 scripts/                   # Scripts
│
│
└── 📂 (root __pycache__)
```

---

## 🔗 Dependencies & Imports Map

### **Main Flow: Detection Engine**

```
detection/main.py
│
├─→ camera_engine.py
│   └─ cv2.VideoCapture()
│
├─→ engine/frame_processor.py
│   └─ cv2.resize()
│
├─→ engine/detector.py
│   ├─ torch (model loading)
│   ├─ cv2 (preprocessing)
│   ├─ numpy
│   ├─ ultralytics_yolov9/ (YOLOv9 core)
│   └─ torchvision
│
├─→ engine/tracker.py
│   └─ deep_sort_realtime.DeepSort()
│
├─→ engine/counter.py
│   └─ collections.defaultdict
│
├─→ engine/density_estimator.py
│   (No external imports)
│
├─→ engine/zone_manager.py
│   ├─ cv2.pointPolygonTest()
│   └─ numpy
│
├─→ engine/event_generator.py
│   ├─ uuid.uuid4()
│   └─ time.time()
│
└─→ integration/publisher.py
    └─ requests.post()
```

### **Main Flow: Backend API**

```
backend/main.py
│
├─→ FastAPI()
│   └─ fastapi.FastAPI
│
├─→ database.py
│   ├─ sqlalchemy.create_engine()
│   └─ sqlalchemy.orm.sessionmaker()
│
├─→ models/*
│   └─ SQLAlchemy declarative_base()
│
├─→ api/detection_routes.py
│   ├─ schemas.detection_schema.DetectionCreate
│   ├─ models.vehicle_detection.VehicleDetection
│   └─ services.db_service.get_db()
│
├─→ api/traffic_routes.py
│   └─ services.db_service.get_db()
│
├─→ api/aggregation_routes.py
│   ├─ services.db_service.get_db()
│   └─ services.aggregation_service.compute_congestion()
│
└─→ api/prediction_routes.py
    (TBD)
```

---

## 📊 Data Flow Between Modules

### **End-to-End Data Flow**

```
┌─────────────────────────────┐
│ Video File / Camera Stream  │
└──────────────┬──────────────┘
               │
               ↓
    detection/camera_engine.py
    ├─ CameraEngine.read()
    └─ Output: Frame (H×W×3)
               │
               ↓
    detection/engine/frame_processor.py
    ├─ FrameProcessor.process()
    └─ Output: Resized frame (H'×W'×3)
               │
               ↓
    detection/engine/detector.py
    ├─ Detector.detect()
    └─ Output: [detection, ...] with bbox, conf, class
               │
               ↓
    detection/engine/tracker.py
    ├─ Tracker.update()
    └─ Output: [track, ...] with track_id, bbox, class
               │
               ↓
    detection/engine/zone_manager.py
    ├─ ZoneManager.check_crossing()
    └─ Output: Boolean (crossing?)
               │
         ┌─────┴─────────────┐
         │ If crossing=True  │
         └─────┬─────────────┘
               ↓
    detection/engine/counter.py
    ├─ VehicleCounter.count()
    └─ Updates: total_counts, minute_counts
               │
    detection/engine/density_estimator.py
    ├─ DensityEstimator.update()
    ├─ DensityEstimator.get_density()
    └─ Output: "LOW" | "MEDIUM" | "HIGH"
               │
               ↓
    detection/engine/event_generator.py
    ├─ EventGenerator.generate()
    └─ Output: Event dict with uuid, timestamp, density
               │
               ↓
    detection/integration/publisher.py
    ├─ EventPublisher.publish()
    └─ HTTP POST /detection
               │
               ↓
┌──────────────────────────┐
│ Backend: FastAPI Server  │
│ backend/main.py          │
└──────────────┬───────────┘
               │
               ↓
    backend/api/detection_routes.py
    ├─ Validate: DetectionCreate (Pydantic)
    └─ Create VehicleDetection ORM object
               │
               ↓
    backend/services/db_service.py
    ├─ get_db() → SQLAlchemy Session
    └─ db.add() + db.commit()
               │
               ↓
    backend/database.py
    ├─ SQLAlchemy engine
    └─ INSERT into vehicle_detections
               │
               ↓
    SQLite/PostgreSQL Database
    └─ Persistent storage
```

---

## 🔐 File Permissions & Access

### **Read-Write Files**

```
database/
└─ traffic.db          (R/W) SQLite database

detection/configs_cameras/
└─ cam_01.json         (R)   Camera configuration

detection/pro_models/
├─ best_final.pt       (R)   Custom model
└─ yolov9c.pt          (R)   Pre-trained model

yolov9-cus/dataset/
├─ train/, val/, test/ (R)   Training data

yolov9-cus/runs/       (R/W) Inference results
```

### **Python Source Files** (Read-only / Modified during dev)

```
detection/
├─ main.py             (R/W) Can be modified
├─ camera_engine.py    (R)   Core functionality
├─ engine/*.py         (R)   Core components
└─ integration/*.py    (R)   Integration layer

backend/
├─ main.py             (R/W) Can be modified
├─ database.py         (R/W) DB config
├─ models/*.py         (R)   ORM models
├─ schemas/*.py        (R)   Validation schemas
├─ api/*.py            (R)   API endpoints
└─ services/*.py       (R)   Business logic
```

---

## 📦 External Dependencies

### **AI/ML Stack**
- ultralytics (YOLOv9)
- torch, torchvision
- opencv-python
- deep-sort-realtime
- numpy, scipy, shapely
- supervision

### **Backend Stack**
- fastapi, uvicorn
- sqlalchemy
- pydantic

### **Database**
- sqlite3 (built-in)
- psycopg2-binary (PostgreSQL optional)

### **Utilities**
- requests, python-dotenv, loguru, tqdm
- pandas, scikit-learn
- matplotlib, seaborn (visualization)

---

## 🎯 Call Graph

```
detection/main.py (entry point)
├─ Initialize()
│   ├─ CameraEngine(source)
│   ├─ FrameProcessor(target_width)
│   ├─ Detector(model_path)
│   │   └─ Load YOLOv9 from ultralytics_yolov9
│   ├─ Tracker()
│   │   └─ DeepSort(max_age=30)
│   ├─ VehicleCounter()
│   ├─ DensityEstimator()
│   ├─ ZoneManager(zones)
│   ├─ EventGenerator()
│   └─ EventPublisher(api_url)
│
└─ MainLoop()
    └─ For each frame:
        ├─ camera.read()
        ├─ processor.process()
        ├─ detector.detect()
        ├─ tracker.update()
        ├─ density.update()
        ├─ For each track:
        │   ├─ zone.check_crossing()
        │   └─ If crossing:
        │       ├─ counter.count()
        │       ├─ event = event_gen.generate()
        │       └─ publisher.publish(event)
        │           └─ HTTP POST to backend
        └─ Display/render

backend/main.py (API server)
└─ FastAPI App
    ├─ Startup: create_all(tables)
    └─ Endpoints:
        ├─ POST /detection
        │   ├─ Pydantic validate
        │   ├─ Create VehicleDetection ORM
        │   └─ db.add() + db.commit()
        ├─ GET /raw-data
        │   └─ Query all VehicleDetections
        ├─ GET /aggregation
        │   └─ compute_congestion(vehicle_count)
        └─ GET /prediction
            (TBD)
```

---

## 📝 Key Observations

1. **Clear Separation of Concerns**
   - Detection Engine: Pure detection/tracking logic
   - Backend API: Data persistence & serving
   - Integration: Async communication via HTTP

2. **Scalability**
   - Multiple cameras → multiple config files (cam_01.json, cam_02.json, ...)
   - Database abstraction → can switch SQLite → PostgreSQL
   - HTTP-based integration → microservices ready

3. **Model Flexibility**
   - Can switch between best_final.pt ↔ yolov9c.pt
   - Easy to add new models
   - YOLOv9 implementation self-contained

4. **Error Handling**
   - EventPublisher: timeout + exception handling (non-blocking)
   - Zone checking: Safe polygon test
   - Database: ORM auto-handles transactions

5. **Performance Tuning**
   - FRAME_SKIP: Reduce frame processing (3x speedup)
   - TARGET_WIDTH: Resize for faster inference
   - CONF_THRESHOLD: Filter low-confidence detections
   - DeepSort max_age: Control tracking memory

---
