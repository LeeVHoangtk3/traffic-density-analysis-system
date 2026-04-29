# Kế Hoạch Triển Khai — Traffic Density Analysis System
> Cập nhật: 28/04/2026  
> Ràng buộc: **Camera 1 hướng duy nhất (inbound only)**  
> Trạng thái: Module A hoàn thành — đang chuyển sang Module B

---

## Ràng Buộc Cốt Lõi

Camera chỉ nhìn **1 hướng** (inbound). Không có outbound, không có multi-direction.  
Hệ quả trực tiếp:

- `direction` trong mọi event luôn là `"inbound"` — lấy từ zone config, không tính toán
- `queue_proxy = inbound_count[t] - inbound_count[t-1]` — chênh lệch xe vào giữa 2 chu kỳ 15 phút
- `queue_proxy > 0` → xe đang tích lũy → tăng đèn xanh
- `queue_proxy < 0` → xe giảm → giảm hoặc giữ nguyên đèn xanh
- `direction_router.py` không cần multi-camera logic phức tạp — chỉ map `CAM_01 → phase_id`

---

## Tổng Quan Luồng Dữ Liệu (Sau Khi Cập Nhật)

```
Video → YOLOv9 + ByteTrack → zone_crossing (inbound)
                                    │
                                    ▼
                        event { camera_id, vehicle_type,
                                direction="inbound", timestamp, ... }
                                    │
                              POST /detection
                                    │
                                    ▼
                         vehicle_detections (DB)
                                    │
                         mỗi 15 phút (wall clock)
                                    │
                                    ▼
                    aggregation_service.compute()
                    ├── vehicle_count  (tổng xe)
                    ├── inbound_count  (xe direction=inbound)
                    ├── queue_proxy    (inbound[t] - inbound[t-1])
                    └── congestion_level (Low/Medium/High/Severe)
                                    │
                                    ▼
                      traffic_aggregation (DB)
                          │                  │
                          ▼                  ▼
               XGBoost #1              XGBoost #2
           traffic_predictor       light_delta_model
           (dự báo xe 15')        (đề xuất delta giây đèn)
                          │                  │
                          ▼                  ▼
                  predicted_density      delta_green
                                              │
                                    green_time = baseline + clamp(delta, -30, +45)
```

---

## Module A — `detection/` ✅ HOÀN THÀNH

**Ràng buộc camera 1 hướng đã được tích hợp.**

### Files đã hoàn thành

| File | Trạng thái | Thay đổi chính |
|------|-----------|----------------|
| `engine/detector.py` | ✅ Xong | bbox scale đúng tỷ lệ, per-class confidence, GPU memory fix |
| `engine/tracker.py` | ✅ Xong | lost_track_buffer=90, track_activation_threshold=0.35 |
| `engine/zone_manager.py` | ✅ Xong | check_crossing() trả về direction thay vì bool, cooldown LRU |
| `engine/event_generator.py` | ✅ Xong | thêm direction, bỏ density, đổi event_type="zone_crossing" |
| `engine/density_estimator.py` | ✅ Xong | window=30 frame, thêm get_last_count() |
| `camera_engine.py` | ✅ Xong | thêm reset(), is_opened(), guard khi mở thất bại |
| `main.py` | ✅ Xong | wall clock aggregation, spike detection, TARGET_WIDTH=960 cố định |
| `configs_cameras/cam_01.json` | ✅ Xong | thêm direction="inbound", baseline_green=30 |

### Quy tắc quan trọng (không thay đổi nữa)

- `direction` luôn = `"inbound"` — đọc từ zone config, không hardcode trong code
- `density` (LOW/MEDIUM/HIGH) chỉ dùng nội bộ để điều khiển frame skip, **không gửi lên backend**
- `check_crossing()` trả về `str | None` — `None` = không crossing hoặc cooldown
- Frame skip: CPU = 10/6/2, GPU = 5/3/1 theo LOW/MEDIUM/HIGH

---

## Module B — `backend/` 🔄 CẦN SỬA

**Thứ tự bắt buộc: DB schema trước, rồi mới sửa các service.**

### Bước B1 — DB Schema (làm trước tiên)

**`models/vehicle_detection.py`** — thêm column:
```python
direction = Column(String, default="inbound")  # "inbound" | "outbound"
```

**`models/traffic_aggregation.py`** — thêm columns:
```python
inbound_count = Column(Integer, default=0)   # chỉ đếm event direction=inbound
queue_proxy   = Column(Integer, default=0)   # inbound[t] - inbound[t-1]
```

**`models/camera.py`** — thêm columns:
```python
baseline_green      = Column(Integer, default=30)      # giây đèn xanh mặc định
monitored_direction = Column(String,  default="inbound")
```

**`database.py`** — thêm vào schema migration tự động (ALTER TABLE):
```python
# Các column mới cần được thêm vào _migrations list
"vehicle_detections.direction",
"traffic_aggregation.inbound_count",
"traffic_aggregation.queue_proxy",
"cameras.baseline_green",
"cameras.monitored_direction",
```

### Bước B2 — Pydantic Schema

**`schemas/detection_schema.py`** — thêm field:
```python
class DetectionCreate(BaseModel):
    ...
    direction: str = "inbound"   # nhận từ event_generator
```

### Bước B3 — Aggregation Service

**`services/aggregation_service.py`** — thêm logic:
```python
# Tách riêng inbound_count
inbound_count = COUNT(events WHERE direction='inbound' AND window=15min)

# Lấy inbound_count của chu kỳ trước (cùng camera)
prev_inbound = SELECT inbound_count FROM traffic_aggregation
               WHERE camera_id = ? ORDER BY timestamp DESC LIMIT 1 OFFSET 1

# Tính queue_proxy
queue_proxy = inbound_count - (prev_inbound or 0)

# Lưu vào DB
aggregation.inbound_count = inbound_count
aggregation.queue_proxy   = queue_proxy
```

### Bước B4 — Seed Data

**`seed_data.py`** — thêm baseline cho CAM_01:
```python
CAM_01: baseline_green=30, monitored_direction="inbound"
```

### Checklist Module B

- [ ] B1: Thêm columns vào 3 model files
- [ ] B1: Thêm ALTER TABLE migration vào database.py  
- [ ] B2: Thêm direction vào DetectionCreate schema
- [ ] B3: Tách inbound_count + tính queue_proxy trong aggregation_service
- [ ] B4: Seed baseline_green cho CAM_01

---

## Module C — `ml_service/` 🆕 CẦN THÊM MỚI

**Giữ nguyên traffic_predictor.py. Thêm 2 file mới.**

### Giữ nguyên

**`traffic_predictor.py`** — XGBoost #1, dự báo vehicle_count 15 phút tới. Không thay đổi.

### Thêm mới: `label_generator.py`

Script sinh training label cho model delta — chạy **1 lần** sau khi có đủ data từ DB.

```python
# Rule mapping queue_proxy → delta_green
queue_proxy > 15   → delta = +30
queue_proxy > 5    → delta = +15
-5 ≤ queue_proxy ≤ 5  → delta =   0
queue_proxy < -5   → delta = -15
queue_proxy < -15  → delta = -30

# Input:  traffic_aggregation table (hoặc CSV export)
# Output: training_data_delta.csv
#         Columns: queue_proxy, inbound_count, congestion_level,
#                  baseline_green, hour, day_of_week, delta_green
```

Thêm flag review thủ công cho ~20 record bất thường (queue_proxy outlier).

### Thêm mới: `light_delta_model.py`

XGBoost #2 — train độc lập, đề xuất delta giây đèn xanh.

```python
class LightDeltaModel:
    # Features:
    # queue_proxy, inbound_count, congestion_level (encoded),
    # baseline_green, hour, day_of_week

    # Target: delta_green (float, giây — âm hoặc dương)

    def train_delta(csv_path) → lưu light_model.pkl
    def predict_delta(feature_dict) → float (giây delta)
```

**Lưu ý quan trọng với camera 1 hướng:**  
`camera_direction` không cần đưa vào feature vector vì luôn = `"inbound"` — thêm vào chỉ làm tăng chiều dữ liệu vô ích.

### Checklist Module C

- [ ] Viết label_generator.py
- [ ] Chạy label_generator, export training_data_delta.csv
- [ ] Review thủ công ~20 record bất thường
- [ ] Viết light_delta_model.py
- [ ] Train model, lưu light_model.pkl

---

## Module D — `integration_system/` 🔄 CẦN SỬA + THÊM

### Giữ nguyên

| File | Lý do |
|------|-------|
| `congestion_classifier.py` | Phân loại local đúng, không cần sửa |
| `performance_monitor.py` | CPU/RAM monitor ổn |
| `scheduler.py` | Lập lịch ổn |

### Sửa: `traffic_light_logic.py`

Bỏ map cứng `density → green_time`, thay bằng gọi `delta_applier`:

```python
# Bỏ:
GREEN_TIME_MAP = {"Low": 20, "Medium": 40, "High": 60, "Severe": 90}

# Thay bằng:
def get_green_time(camera_id, aggregation_data):
    try:
        return delta_applier.apply(camera_id, aggregation_data)
    except Exception:
        # Fallback nếu light_model.pkl chưa có
        return GREEN_TIME_MAP[aggregation_data["congestion_level"]]
```

### Thêm mới: `delta_applier.py`

```python
def apply(camera_id, aggregation_data) → green_time (giây):
    # 1. Lấy feature từ aggregation_data
    feature = {
        "queue_proxy":      aggregation_data["queue_proxy"],
        "inbound_count":    aggregation_data["inbound_count"],
        "congestion_level": encode(aggregation_data["congestion_level"]),
        "baseline_green":   get_baseline(camera_id),   # từ cameras table
        "hour":             now.hour,
        "day_of_week":      now.weekday(),
    }
    # 2. Predict delta
    delta = LightDeltaModel.predict_delta(feature)

    # 3. Clamp: không giảm quá 30s, không tăng quá 45s
    delta = max(-30, min(+45, delta))

    # 4. Tính green_time
    return get_baseline(camera_id) + delta
```

### Thêm mới: `direction_router.py`

Với camera 1 hướng, file này đơn giản — chỉ map camera → pha đèn:

```python
# Không cần multi-direction logic
CAMERA_PHASE_MAP = {
    "CAM_01": {
        "phase":     "north_green",   # pha đèn tương ứng ở giao lộ
        "direction": "inbound",
    }
}

def get_phase(camera_id: str) -> str:
    return CAMERA_PHASE_MAP[camera_id]["phase"]
```

Nếu sau này có thêm camera — chỉ cần thêm entry vào dict, không đổi logic.

### Checklist Module D

- [ ] Sửa traffic_light_logic.py (thêm fallback, gọi delta_applier)
- [ ] Viết delta_applier.py
- [ ] Viết direction_router.py (đơn giản, 1 camera)

---

## Module E — `web_demo/` 🆕 HOÀN TOÀN MỚI

Giao diện demo cho hội đồng. Có thể chạy offline bằng mock data.

### Các thành phần cần làm

**1. Layout chính (`index.html` hoặc `App.jsx`)**
- 4 metric cards: tổng xe hôm nay, congestion_level, dự báo 15', delta đèn gần nhất
- Toggle Live / Demo mode (fetch API thật hoặc load mock_data.json)

**2. Camera panel**
- Vẽ zone detection trên khung hình giả lập (CSS/Canvas)
- Hiển thị: camera_id, direction="inbound", xe trong zone, density level

**3. Biểu đồ mật độ xe**
- Line chart: actual (aggregation) vs predicted (ML forecast)
- Trục X = thời gian 15 phút/điểm, trục Y = vehicle_count

**4. Bảng đèn giao thông**
- Mỗi camera: baseline_green, delta, green_time
- Đèn giao thông SVG animated đếm ngược
- Màu theo congestion: LOW=xanh, MEDIUM=vàng, HIGH=cam, SEVERE=đỏ

**5. Log sự kiện**
- Danh sách event gần nhất từ `GET /raw-data`
- Mỗi row: timestamp, camera_id, vehicle_type, direction
- Auto-refresh 5 giây

### Checklist Module E

- [ ] Setup project (HTML thuần hoặc React)
- [ ] Mock data JSON cho demo offline
- [ ] 4 metric cards
- [ ] Camera panel với zone animation
- [ ] Line chart actual vs predicted
- [ ] Bảng đèn + SVG animated
- [ ] Log sự kiện + auto-refresh

---

## Thứ Tự Implement

```
B1 (DB schema)
    │
    ▼
B2 (Pydantic schema) + B3 (aggregation service) + B4 (seed data)
    │
    ▼
C1 (label_generator) → export CSV → review thủ công
    │
    ▼
C2 (light_delta_model) → train → light_model.pkl
    │
    ▼
D1 (delta_applier) → D2 (direction_router) → D3 (traffic_light_logic)
    │
    ▼
E (web_demo)
```

---

## Bảng Tổng Hợp

| Module | Trạng thái | Files giữ | Files sửa | Files thêm |
|--------|-----------|-----------|-----------|------------|
| A — detection | ✅ Xong | — | 8 files | — |
| B — backend | 🔄 Đang làm | detection_routes, prediction_routes, camera_routes, health_routes | vehicle_detection.py, traffic_aggregation.py, camera.py, database.py, detection_schema.py, aggregation_service.py, seed_data.py | — |
| C — ml_service | ⏳ Chưa bắt đầu | traffic_predictor.py, train.py | — | label_generator.py, light_delta_model.py |
| D — integration | ⏳ Chưa bắt đầu | congestion_classifier.py, performance_monitor.py, scheduler.py | traffic_light_logic.py | delta_applier.py, direction_router.py |
| E — web_demo | ⏳ Chưa bắt đầu | — | — | Toàn bộ frontend |

---

> **Ghi chú**: `direction_router.py` được giữ đơn giản vì hệ thống chỉ có 1 camera 1 hướng.  
> Nếu mở rộng thêm camera sau này — chỉ cần thêm entry vào `CAMERA_PHASE_MAP`, không cần refactor logic.

