# Hướng dẫn chạy dự án
source .venv/bin/activate
## 1. Chạy backend

```bash
uvicorn backend.main:app --reload
```

Backend hiện cung cấp các API chính:
- `POST /detection`
- `GET /raw-data`
- `GET /aggregation`
- `GET /aggregation/history`
- `POST /aggregation/compute`
- `GET /predict-next`
- `GET /predictions/history`
- `GET /cameras`
- `POST /cameras`
- `GET /health`

## 2. Chạy detection

```bash
python -m detection.main
```

Detection sẽ:
- đọc video
- nhận diện và theo dõi xe
- gửi event vào `POST /detection`
- tự gọi `POST /aggregation/compute` theo chu kỳ 15 phút

## 3. Chạy dự báo

```bash
python -m ml_service.predict
```

Script này gọi `GET /predict-next` và hiển thị kết quả dự báo hiện tại từ backend.

## 4. Chạy integration system

```bash
python integration_system/system_runner.py
```

`integration_system` hiện đọc:
- `GET /raw-data` để kiểm tra dữ liệu đầu vào
- `GET /aggregation?camera_id=CAM_01` để lấy mức ùn tắc từ backend

## 5. Seed dữ liệu phụ trợ

Nếu `traffic.db` mới chỉ có dữ liệu trong `vehicle_detections`, bạn có thể tạo dữ liệu cho
`cameras`, `traffic_aggregation`, `traffic_predictions` bằng:

```bash
python -m backend.seed_data
```

## 6. Luồng dữ liệu hiện tại

```text
detection/main.py
    -> POST /detection
    -> vehicle_detections
    -> POST /aggregation/compute
    -> traffic_aggregation
    -> GET /predict-next
    -> traffic_predictions
```

## 7. Ghi chú

- Backend hiện đã khớp với `detection/`, `ml_service/` và `integration_system/` ở mức API.
- `backend/README.md` là tài liệu chi tiết nhất cho phần backend.
- Nếu cần tài liệu báo cáo, xem thêm `BAO_CAO_DU_AN.md` và `BAO_CAO_MODULE_B_BACKEND.md`.
