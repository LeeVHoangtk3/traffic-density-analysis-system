# Backend Module

## Mục đích

Thư mục `backend/` là lớp API và dữ liệu của dự án `traffic-density-analysis-system`.

Nhiệm vụ chính:
- Nhận event giao thông từ `detection/` qua HTTP.
- Validate dữ liệu đầu vào bằng Pydantic.
- Lưu dữ liệu vào database thông qua SQLAlchemy.
- Cung cấp API để truy vấn, tổng hợp và dự báo.
- Làm nguồn dữ liệu cho `integration_system/`.

Nói ngắn gọn: `backend/` là cầu nối giữa AI detection, database và business logic giao thông.

## Cấu trúc hiện tại

```text
backend/
├── api/
│   ├── aggregation_routes.py
│   ├── camera_routes.py
│   ├── detection_routes.py
│   ├── health_routes.py
│   ├── prediction_routes.py
│   └── traffic_routes.py
├── models/
│   ├── __init__.py
│   ├── camera.py
│   ├── traffic_aggregation.py
│   ├── traffic_prediction.py
│   └── vehicle_detection.py
├── schemas/
│   ├── aggregation_schema.py
│   ├── camera_schema.py
│   ├── detection_schema.py
│   ├── prediction_schema.py
│   └── traffic_schema.py
├── services/
│   ├── aggregation_service.py
│   ├── camera_service.py
│   ├── db_service.py
│   ├── detection_service.py
│   └── prediction_service.py
├── config.py
├── database.py
├── main.py
└── README.md
```

## Kiến trúc theo lớp

### 1. API layer

Nằm trong `backend/api/`.

Vai trò:
- nhận request
- gọi service
- trả response

Không nên viết business logic phức tạp trong route.

### 2. Schema layer

Nằm trong `backend/schemas/`.

Vai trò:
- validate dữ liệu đầu vào
- chuẩn hóa response
- định nghĩa format giao tiếp giữa client và backend

### 3. Model layer

Nằm trong `backend/models/`.

Vai trò:
- mô tả bảng dữ liệu
- ánh xạ object Python sang database record

### 4. Service layer

Nằm trong `backend/services/`.

Vai trò:
- chứa business logic
- xử lý detection, aggregation, prediction, camera
- giúp route gọn và dễ test

### 5. Database layer

Nằm trong `backend/database.py`.

Vai trò:
- tạo engine
- tạo session
- quản lý `Base`
- đồng bộ schema tối thiểu cho các bảng cũ

## Các file quan trọng

### `main.py`

Entry point của FastAPI app.

Chức năng:
- tạo `FastAPI`
- import models để SQLAlchemy biết schema
- `create_all()` tạo bảng nếu chưa có
- gọi `sync_vehicle_detection_schema()`
- mount toàn bộ routers

### `config.py`

Chứa cấu hình backend qua environment variables.

Hiện có:
- `DATABASE_URL`
- `BACKEND_API_TITLE`
- `DEFAULT_PAGE_SIZE`
- `MAX_PAGE_SIZE`
- `PREDICTION_HORIZON_MINUTES`

### `database.py`

Chứa engine, `SessionLocal`, `Base`.

Ngoài ra còn có `sync_vehicle_detection_schema()` để bổ sung các cột cần thiết vào database cũ mà không cần xóa file `traffic.db`.

### `models/vehicle_detection.py`

Bảng dữ liệu gốc quan trọng nhất.

Lưu:
- `event_id`
- `camera_id`
- `track_id`
- `vehicle_type`
- `density`
- `event_type`
- `confidence`
- `timestamp`

Đây là bảng nguồn cho truy vấn, thống kê và dự báo.

### `models/traffic_aggregation.py`

Lưu snapshot tổng hợp:
- `camera_id`
- `vehicle_count`
- `congestion_level`
- `timestamp`

### `models/traffic_prediction.py`

Lưu kết quả dự báo:
- `camera_id`
- `predicted_density`
- `horizon_minutes`
- `source`
- `timestamp`

### `models/camera.py`

Lưu thông tin camera:
- `camera_id`
- `name`
- `location`

### `services/detection_service.py`

Chứa logic:
- tìm detection theo `event_id`
- tạo detection mới

### `services/aggregation_service.py`

Chứa logic:
- `compute_congestion(vehicle_count)`
- `aggregate_from_detections(...)`

Route aggregation có thể:
- tính nhanh từ `vehicle_count`
- hoặc query trực tiếp từ `vehicle_detections`

### `services/prediction_service.py`

Chứa logic:
- lấy lịch sử từ database
- cố gắng load model trong `ml_service/model.pkl`
- fallback về trung bình nếu chưa đủ điều kiện predict
- lưu kết quả vào `traffic_predictions`

### `services/camera_service.py`

Chứa logic:
- lấy danh sách camera
- tạo camera mới

## Các endpoint hiện có

### Health

- `GET /health`

Dùng để check backend còn sống hay không.

### Detection

- `POST /detection`

Nhận event từ detection engine.

Backend sẽ:
- validate payload
- check trùng `event_id`
- lưu vào `vehicle_detections`

### Raw data

- `GET /raw-data`

Hỗ trợ:
- `camera_id`
- `vehicle_type`
- `density`
- `start_time`
- `end_time`
- `limit`
- `offset`

Dùng để lấy dữ liệu detection đã lưu.

### Aggregation

- `GET /aggregation`

Có 2 cách dùng:
- Truyền `vehicle_count` để tính nhanh mức ùn tắc
- Không truyền `vehicle_count` để backend tự query DB và tạo snapshot aggregation

Tham số hỗ trợ:
- `camera_id`
- `start_time`
- `end_time`

### Prediction

- `GET /predict-next`

Tham số hỗ trợ:
- `camera_id`

Nếu có đủ lịch sử và model trong `ml_service/`, backend sẽ predict.
Nếu không, backend dùng chế độ fallback.

### Camera

- `GET /cameras`
- `POST /cameras`

Dùng để quản lý danh sách camera ở mức tối thiểu.

## Luồng dữ liệu thực tế

```text
Detection Engine
    -> tạo event
    -> POST /detection
    -> backend validate
    -> save vào vehicle_detections
    -> client/integration query /raw-data, /aggregation, /predict-next
```

## Cách chạy

### 1. Cài dependency

```bash
pip install -r requirements.txt
```

### 2. Chạy backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Kiểm tra nhanh

```bash
curl http://127.0.0.1:8000/health
```

### 4. Seed dữ liệu cho 3 bảng còn lại

Nếu `traffic.db` mới chỉ có dữ liệu trong `vehicle_detections`, bạn có thể sinh dữ liệu cho:
- `cameras`
- `traffic_aggregation`
- `traffic_predictions`

bằng lệnh:

```bash
python -m backend.seed_data
```

Script này sẽ:
- đọc các `camera_id` đã có trong `vehicle_detections`
- tạo camera nếu bảng `cameras` còn thiếu
- tạo một bản ghi tổng hợp cho mỗi camera trong `traffic_aggregation`
- tạo một bản ghi dự báo cho mỗi camera trong `traffic_predictions`

## Ví dụ request

### Tạo detection

```json
POST /detection
{
  "event_id": "evt-001",
  "camera_id": "CAM_01",
  "track_id": 12,
  "vehicle_type": "car",
  "density": "LOW",
  "event_type": "line_crossing",
  "timestamp": "2026-04-19T10:15:00",
  "confidence": 0.91
}
```

### Lấy dữ liệu raw

```text
GET /raw-data?camera_id=CAM_01&limit=20&offset=0
```

### Tính aggregation từ DB

```text
GET /aggregation?camera_id=CAM_01
```

### Predict tiếp theo

```text
GET /predict-next?camera_id=CAM_01
```

## Environment variables

```env
DATABASE_URL=sqlite:///./traffic.db
BACKEND_API_TITLE=Traffic AI Backend
DEFAULT_PAGE_SIZE=100
MAX_PAGE_SIZE=500
PREDICTION_HORIZON_MINUTES=15
```

## Trạng thái hiện tại

Phần đã hoàn thiện ở mức dùng được:
- nhận detection event
- lưu database
- truy vấn raw data có filter cơ bản
- aggregation từ DB
- prediction có fallback
- health check
- camera API tối thiểu

Phần còn có thể nâng cấp tiếp:
- auth và rate limit
- logging và exception handler chung
- migration chuẩn bằng Alembic
- pagination/response model chặt chẽ hơn
- dashboard endpoint tổng hợp
- prediction nâng cao hơn từ dữ liệu thật

## Ghi chú

- SQLite phù hợp để dev và demo.
- Nếu đưa lên production, nên chuyển sang PostgreSQL.
- `prediction_service.py` có phụ thuộc vào `ml_service/` và các package ML liên quan.
- Nếu thiếu package như `fastapi`, `sqlalchemy`, `xgboost`, backend sẽ không chạy đủ.
