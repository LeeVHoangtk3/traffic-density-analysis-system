# Backend Module

`backend/` la lop FastAPI trung tam cua he thong `traffic-density-analysis-system`.
Module nay nhan su kien tu Computer Vision, luu MongoDB, tong hop du lieu 15 phut,
du bao luu luong 3 huong va cung cap API cho dashboard/orchestrator.

## Vai Tro

- Nhan event xe tu `detection/` qua `POST /detection`.
- Luu du lieu van hanh vao MongoDB.
- Truy van raw data theo camera, thoi gian, loai xe va huong di chuyen.
- Tong hop luu luong theo 3 huong `left`, `straight`, `right`.
- Du bao luu luong 15 phut tiep theo bang 3 model trong `ml_service/model/`.
- Tra trang thai den tin hieu tu `light_status.json` cho frontend.
- Cung cap health check, camera API va video stream phuc vu demo.

## Cau Truc

```text
backend/
├── api/
│   ├── aggregation_routes.py
│   ├── camera_routes.py
│   ├── detection_routes.py
│   ├── health_routes.py
│   ├── prediction_routes.py
│   ├── traffic_routes.py
│   └── video.py
├── schemas/
├── services/
├── config.py
├── main.py
├── mongo_database.py
└── seed_data.py
```

## MongoDB Collections

- `vehicle_detections`: event detection thoi gian thuc.
- `traffic_aggregation`: ban ghi tong hop 15 phut, gom `direction_counts`.
- `traffic_predictions`: lich su du bao, gom `predictions` va `phase_timing`.
- `directional_thresholds`: nguong K-Means dong theo camera va huong.
- `cameras`: metadata camera.

## Direction Contract

Backend hien ho tro cac huong moi:

```text
left | straight | right
```

Hai gia tri cu `inbound` va `outbound` van duoc chap nhan de tuong thich du lieu cu,
nhung pipeline moi nen gui `left`, `straight`, hoac `right`.

## Endpoints Chinh

### Health

```text
GET /health
```

Kiem tra FastAPI va MongoDB.

### Detection

```text
POST /detection
```

Payload mau:

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

Backend kiem tra trung `event_id` va tra `409 Conflict` neu event da ton tai.

### Raw Data

```text
GET /raw-data?camera_id=CAM_01&direction=straight&limit=20&offset=0
```

Ho tro filter: `camera_id`, `vehicle_type`, `density`, `direction`, `start_time`, `end_time`.

### Aggregation

```text
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
