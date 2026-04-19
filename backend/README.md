# README Backend

## 1. Mục đích chính của folder `backend`

Folder `backend` là lớp dịch vụ API và lưu trữ dữ liệu của dự án `traffic-density-analysis-system`.

Nếu thư mục `detection/` chịu trách nhiệm:

- đọc video hoặc camera,
- nhận diện phương tiện,
- theo dõi đối tượng,
- xác định sự kiện xe đi qua vùng quan tâm,

thì `backend/` chịu trách nhiệm:

- nhận các sự kiện đó qua HTTP API,
- kiểm tra tính hợp lệ của dữ liệu đầu vào,
- lưu dữ liệu vào cơ sở dữ liệu,
- cung cấp các API để truy xuất dữ liệu thô,
- tạo nền tảng cho các chức năng tổng hợp và dự báo sau này.

Nói ngắn gọn, `backend` là cầu nối giữa phần AI nhận diện giao thông và phần lưu trữ, khai thác dữ liệu.

## 2. Vai trò của backend trong toàn dự án

Toàn bộ dự án hiện có thể hiểu thành 3 lớp lớn:

### 2.1. Lớp phát hiện giao thông

Nằm chủ yếu trong `detection/`, có nhiệm vụ:

- mở video hoặc camera,
- chạy mô hình YOLO,
- tracking phương tiện,
- kiểm tra xe có đi vào vùng đếm hay không,
- tạo event và gửi về backend.

### 2.2. Lớp API và dữ liệu

Nằm trong `backend/`, có nhiệm vụ:

- tạo web service bằng FastAPI,
- ánh xạ dữ liệu sang ORM model bằng SQLAlchemy,
- ghi dữ liệu vào `traffic.db`,
- trả dữ liệu lại cho các client hoặc module khác.

### 2.3. Lớp mô hình/dataset

Nằm ở các thư mục như `yolov9-cus/`, `detection/pro_models/`, video mẫu, notebook... Đây là lớp phục vụ huấn luyện, suy luận và thử nghiệm.

Vì vậy, `backend` không trực tiếp nhận diện hình ảnh. Nó đóng vai trò "trạm trung chuyển dữ liệu có cấu trúc" trong pipeline.

## 3. Cấu trúc hiện tại của folder `backend`

```text
backend/
├─ api/
│  ├─ aggregation_routes.py
│  ├─ detection_routes.py
│  ├─ prediction_routes.py
│  └─ traffic_routes.py
├─ models/
│  ├─ camera.py
│  ├─ traffic_aggregation.py
│  ├─ traffic_prediction.py
│  └─ vehicle_detection.py
├─ schemas/
│  ├─ aggregation_schema.py
│  ├─ detection_schema.py
│  └─ prediction_schema.py
├─ services/
│  ├─ aggregation_service.py
│  └─ db_service.py
├─ database.py
├─ main.py
└─ README.md
```

Ý nghĩa từng nhóm file:

- `main.py`: điểm khởi động FastAPI, nơi đăng ký router và tạo bảng dữ liệu.
- `database.py`: cấu hình kết nối database, session SQLAlchemy và đồng bộ schema tối thiểu.
- `api/`: nơi định nghĩa các endpoint REST API.
- `models/`: mô tả cấu trúc bảng trong database bằng ORM.
- `schemas/`: mô tả dữ liệu đầu vào/đầu ra bằng Pydantic.
- `services/`: chứa logic dùng chung, tách khỏi route để code gọn hơn.

## 4. Phân tích từng file quan trọng

### 4.1. `backend/main.py`

Đây là file entrypoint của backend.

Những việc chính file này đang làm:

1. Tạo ứng dụng FastAPI với tên `Traffic AI Backend`.
2. Import toàn bộ model để SQLAlchemy biết các bảng cần tạo.
3. Gọi `Base.metadata.create_all(bind=engine)` để tự tạo bảng nếu chưa có.
4. Gọi `sync_vehicle_detection_schema()` để bổ sung các cột mới cho bảng `vehicle_detections` nếu database cũ chưa có đủ.
5. Gắn các router API vào app.

Ý nghĩa:
- đây là nơi "ghép" toàn bộ backend thành một dịch vụ chạy được,
- mỗi lần backend khởi động, nó cố gắng bảo đảm database ở trạng thái phù hợp với mã nguồn hiện tại.

### 4.2. `backend/database.py`

File này là nền tảng dữ liệu của backend.

Các thành phần chính:

- `DATABASE_URL = "sqlite:///./traffic.db"`: dùng SQLite với file `traffic.db` ở thư mục gốc dự án.
- `engine`: đối tượng kết nối DB.
- `SessionLocal`: factory tạo session để truy vấn/ghi dữ liệu.
- `Base = declarative_base()`: lớp cha cho tất cả model SQLAlchemy.

#### Hàm `sync_vehicle_detection_schema()`

Đây là điểm khá quan trọng trong kiến trúc hiện tại.

Hàm này:

- kiểm tra bảng `vehicle_detections` có tồn tại không,
- đọc danh sách cột hiện có,
- nếu thiếu các cột như `event_id`, `track_id`, `density`, `event_type`, `confidence`, `timestamp` thì tự `ALTER TABLE` để thêm vào.

Điều này cho thấy:

- schema của bảng detection đã thay đổi trong quá trình phát triển,
- dự án hiện chưa dùng migration chuẩn như Alembic,
- nhóm đang chọn cách đồng bộ tối thiểu bằng code để tránh lỗi khi database cũ chưa cập nhật.

Đây là giải pháp nhanh, phù hợp với đồ án/prototype, nhưng về lâu dài nên chuyển sang migration có kiểm soát.

### 4.3. `backend/services/db_service.py`

File này cung cấp dependency `get_db()` cho FastAPI.

Logic:

- mở một session DB,
- `yield` session đó cho route dùng,
- sau khi request xong thì đóng session.

Ý nghĩa:

- tránh việc route tự tạo và tự đóng kết nối,
- chuẩn hóa cách dùng database trong toàn backend.

### 4.4. `backend/models/vehicle_detection.py`

Đây là model quan trọng nhất của backend hiện tại.

Nó ánh xạ vào bảng `vehicle_detections` với các cột:

- `id`: khóa chính tự tăng.
- `event_id`: mã sự kiện duy nhất.
- `camera_id`: mã camera.
- `track_id`: mã đối tượng được tracker gán.
- `vehicle_type`: loại xe.
- `density`: mức mật độ giao thông tại thời điểm đó.
- `event_type`: loại event, hiện tại là `line_crossing`.
- `confidence`: độ tin cậy của detection.
- `timestamp`: thời gian phát sinh event.

Đây là bảng dữ liệu gốc của toàn hệ thống. Hầu hết giá trị phân tích sau này đều nên được sinh ra từ bảng này.

### 4.5. `backend/models/traffic_aggregation.py`

Model này định nghĩa bảng `traffic_aggregation`.

Mục đích dự kiến:

- lưu kết quả tổng hợp như số xe theo camera,
- mức ùn tắc theo khoảng thời gian,
- dữ liệu đã xử lý thay vì event thô.

Hiện trạng:

- bảng đã được định nghĩa,
- nhưng chưa có luồng nào ghi dữ liệu thực vào đây.

### 4.6. `backend/models/traffic_prediction.py`

Model này định nghĩa bảng `traffic_predictions`.

Mục tiêu tương lai:

- lưu các giá trị dự báo mật độ giao thông,
- phục vụ dashboard hoặc phân tích dự đoán.

Hiện trạng:

- mới chỉ là khung cấu trúc dữ liệu,
- chưa có mô hình dự báo thật và chưa có logic ghi dữ liệu.

### 4.7. `backend/models/camera.py`

Model này định nghĩa bảng `cameras` với:

- `id`,
- `name`,
- `location`.

Mục tiêu:

- quản lý danh sách camera trong hệ thống,
- chuẩn hóa thông tin camera thay vì chỉ dùng chuỗi `camera_id`.

Hiện trạng:

- chưa được kết nối thật sự với bảng `vehicle_detections`,
- chưa có foreign key,
- chưa có API quản lý camera.

### 4.8. `backend/schemas/detection_schema.py`

Schema `DetectionCreate` dùng để kiểm tra dữ liệu gửi vào endpoint `POST /detection`.

Các trường hiện tại:

- `event_id: str`
- `camera_id: str`
- `track_id: Union[int, str]`
- `vehicle_type: str`
- `density: str`
- `event_type: str`
- `timestamp: datetime`
- `confidence: Optional[float]`

Ý nghĩa:

- xác định format chuẩn của event mà backend mong đợi,
- tự động parse `timestamp`,
- từ chối request sai kiểu dữ liệu trước khi ghi DB.

Điểm đáng chú ý:

- `track_id` cho phép cả `int` và `str`, sau đó route sẽ ép về `str`,
- điều này giúp backend linh hoạt hơn khi module detection thay đổi kiểu dữ liệu của tracker.

### 4.9. `backend/schemas/aggregation_schema.py`

Schema phản hồi cho aggregation:

- `vehicle_count`
- `congestion_level`

Hiện tại schema này mới phản ánh kết quả đơn giản từ service tính mức ùn tắc.

### 4.10. `backend/schemas/prediction_schema.py`

Schema phản hồi cho prediction:

- `predicted_density`

Đây cũng mới là một khung sẵn sàng cho chức năng mở rộng.

### 4.11. `backend/api/detection_routes.py`

Đây là route quan trọng nhất của backend.

Endpoint:

- `POST /detection`

Luồng xử lý:

1. Nhận JSON request và ép kiểu qua `DetectionCreate`.
2. Tạo đối tượng `VehicleDetection`.
3. Ghi dữ liệu vào database.
4. `commit` transaction.
5. `refresh` để lấy lại bản ghi đã lưu.
6. Trả về JSON gồm `status` và `id`.

Tại sao route này quan trọng:

- toàn bộ pipeline giữa detection và backend đang phụ thuộc vào endpoint này,
- nếu route này lỗi, hệ thống vẫn detect được xe nhưng không lưu được dữ liệu.

### 4.12. `backend/api/traffic_routes.py`

Endpoint:

- `GET /raw-data`

Chức năng:

- đọc toàn bộ bản ghi trong bảng `vehicle_detections`,
- trả dữ liệu thô phục vụ kiểm tra, debug hoặc tích hợp giao diện.

Ý nghĩa:

- đây là endpoint đọc dữ liệu cơ bản nhất,
- giúp xác minh backend đang lưu dữ liệu đúng hay không.

Điểm cần lưu ý:

- route hiện trả toàn bộ dữ liệu không phân trang,
- nếu số bản ghi tăng lớn, endpoint này sẽ chậm và nặng.

### 4.13. `backend/api/aggregation_routes.py`

Endpoint:

- `GET /aggregation?vehicle_count=...`

Route này chưa đọc database.

Nó chỉ:

1. nhận `vehicle_count` từ query parameter,
2. gọi `compute_congestion(vehicle_count)`,
3. trả về mức độ ùn tắc tương ứng.

Đây là route minh họa logic nghiệp vụ, chưa phải aggregation đúng nghĩa từ dữ liệu thực.

### 4.14. `backend/api/prediction_routes.py`

Endpoint:

- `GET /predict-next`

Hiện tại endpoint này trả cứng:

- `predicted_density: 0.45`

Điều đó cho thấy phần prediction mới chỉ là placeholder kiến trúc.

### 4.15. `backend/services/aggregation_service.py`

Hàm `compute_congestion(vehicle_count)` phân loại mức ùn tắc theo số lượng xe:

- dưới 10: `Low`
- từ 10 đến dưới 30: `Medium`
- từ 30 đến dưới 60: `High`
- từ 60 trở lên: `Severe`

Đây là logic nghiệp vụ đơn giản, dùng để:

- minh họa cách backend xử lý dữ liệu,
- làm nền để thay thế bằng thuật toán tổng hợp thực sau này.

## 5. Luồng hoạt động thực tế của backend trong dự án

Đây là luồng quan trọng nhất để hiểu folder `backend`.

### Bước 1. Hệ thống detection chạy video

File liên quan:

- `detection/main.py`
- `detection/camera_engine.py`
- `detection/engine/frame_processor.py`
- `detection/engine/detector.py`
- `detection/engine/tracker.py`

Ý nghĩa:

- mở nguồn video,
- tiền xử lý frame,
- nhận diện xe,
- tracking đối tượng giữa các frame.

### Bước 2. Hệ thống xác định mật độ và vùng đếm

File liên quan:

- `detection/engine/density_estimator.py`
- `detection/engine/zone_manager.py`
- `detection/configs_cameras/cam_01.json`

Ý nghĩa:

- đếm số track đang tồn tại để ước lượng mật độ `LOW/MEDIUM/HIGH`,
- kiểm tra tâm bbox của xe có đi vào polygon quan tâm không,
- tránh đếm lặp bằng `counted_ids`.

### Bước 3. Hệ thống sinh event chuẩn hóa

File liên quan:

- `detection/engine/event_generator.py`

Khi có xe đi qua vùng đếm, file này tạo event có cấu trúc:

- `event_id`
- `camera_id`
- `track_id`
- `vehicle_type`
- `density`
- `event_type`
- `timestamp`
- `confidence`

Đây chính là format mà backend đang nhận ở `DetectionCreate`.

### Bước 4. Event được gửi từ detection sang backend

File liên quan:

- `detection/integration/publisher.py`

Publisher dùng:

- `requests.post(api_url, json=event, timeout=3)`

Mặc định URL là:

- `http://127.0.0.1:8000/detection`

Điều này nối trực tiếp `detection` với route `POST /detection` của backend.

### Bước 5. Backend nhận event và validate

File liên quan:

- `backend/api/detection_routes.py`
- `backend/schemas/detection_schema.py`

Backend:

- nhận event JSON,
- parse qua Pydantic,
- bảo đảm dữ liệu có đúng cấu trúc trước khi lưu.

### Bước 6. Backend ghi dữ liệu vào database

File liên quan:

- `backend/models/vehicle_detection.py`
- `backend/services/db_service.py`
- `backend/database.py`

Sau khi hợp lệ:

- route tạo `VehicleDetection`,
- dùng session DB,
- `add -> commit -> refresh`,
- lưu xuống `traffic.db`.

### Bước 7. Dữ liệu được truy xuất lại qua API

File liên quan:

- `backend/api/traffic_routes.py`

Lúc này:

- `GET /raw-data` có thể trả về toàn bộ dữ liệu đã lưu,
- các phần tổng hợp/dự báo có thể tiếp tục dùng dữ liệu từ bảng gốc này.

## 6. Mối liên kết giữa backend và các file khác trong dự án

### 6.1. Liên kết với `traffic.db`

Backend đang dùng trực tiếp file database ở thư mục gốc:

- `traffic.db`

Tại thời điểm kiểm tra hiện tại:

- `vehicle_detections`: 80 bản ghi
- `traffic_aggregation`: 0 bản ghi
- `traffic_predictions`: 0 bản ghi
- `cameras`: 0 bản ghi

Điều này cho thấy luồng lưu dữ liệu detection đã hoạt động, còn các bảng mở rộng chưa được dùng thực tế.

### 6.2. Liên kết với `requirements.txt`

Các thư viện backend dùng chủ yếu là:

- `fastapi`
- `uvicorn`
- `pydantic`
- `sqlalchemy`
- `requests`

Ngoài ra dự án còn chuẩn bị sẵn:

- `psycopg2-binary`

Điều này gợi ý backend có thể được nâng cấp từ SQLite lên PostgreSQL trong tương lai.

### 6.3. Liên kết với `detection/main.py`

`detection/main.py` có biến:

- `API_URL = os.getenv("TRAFFIC_API_URL", "http://127.0.0.1:8000/detection")`

Nghĩa là detection sẽ gửi event sang backend theo URL này nếu không cấu hình khác.

### 6.4. Liên kết với `detection/configs_cameras/cam_01.json`

File này định nghĩa các polygon vùng đếm. Khi phương tiện đi vào vùng đó:

- detection sinh event,
- backend lưu event như một bản ghi trong `vehicle_detections`.

Nói cách khác, backend không biết hình ảnh hay tọa độ zone. Backend chỉ nhận kết quả cuối của bước phát hiện.

## 7. Logic thiết kế của backend theo từng lớp

Kiến trúc hiện tại đang đi theo hướng phân tầng đơn giản:

### 7.1. Route layer

Nằm trong `backend/api/`.

Vai trò:

- nhận request,
- gọi service hoặc thao tác DB,
- trả response.

### 7.2. Schema layer

Nằm trong `backend/schemas/`.

Vai trò:

- validate dữ liệu,
- chuẩn hóa kiểu đầu vào/đầu ra.

### 7.3. Model layer

Nằm trong `backend/models/`.

Vai trò:

- mô tả bảng dữ liệu,
- làm cầu nối giữa Python object và database record.

### 7.4. Service layer

Nằm trong `backend/services/`.

Vai trò:

- chứa logic dùng lại,
- giúp route không bị nhồi quá nhiều xử lý.

### 7.5. Database layer

Nằm trong `backend/database.py`.

Vai trò:

- quản lý engine, session, base,
- là nền móng cho toàn bộ phần ORM.

Đây là cách tổ chức tốt cho một backend nhỏ đến trung bình vì:

- dễ đọc,
- dễ tách logic,
- dễ mở rộng thêm endpoint và service.

## 8. Các bước triển khai backend theo đúng tinh thần mã nguồn hiện tại

Nếu mô tả "các bước làm" của folder `backend` theo tiến trình phát triển, có thể hiểu như sau:

### Bước 1. Xác định backend là nơi nhận event chứ không xử lý ảnh

Đây là bước tư duy quan trọng nhất.

Nhóm đã tách rõ:

- `detection` lo video và AI,
- `backend` lo API và database.

Nhờ đó cấu trúc dự án rõ trách nhiệm ngay từ đầu.

### Bước 2. Chọn FastAPI + SQLAlchemy + SQLite

Đây là bộ công nghệ hợp lý cho đồ án:

- dựng API nhanh,
- code Python đồng nhất với phần AI,
- dễ chạy local,
- không cần hạ tầng DB phức tạp ngay.

### Bước 3. Tạo model dữ liệu gốc trước

Model `VehicleDetection` được xem là trung tâm.

Lý do:

- detection sinh ra event,
- event cần được lưu nguyên dạng càng sớm càng tốt,
- mọi thống kê về sau đều có thể tái tạo từ dữ liệu thô này.

### Bước 4. Tạo schema xác thực đầu vào

Đây là lớp chặn lỗi giữa detection và database.

Nếu không có schema:

- request sai định dạng vẫn có thể đi sâu vào hệ thống,
- database dễ bị bẩn dữ liệu,
- lỗi khó debug hơn nhiều.

### Bước 5. Xây route ghi dữ liệu cốt lõi

Route `POST /detection` là bước hoàn thiện quan trọng nhất.

Khi route này chạy được, pipeline:

- detect xe,
- sinh event,
- gửi event,
- lưu event

đã trở thành một chuỗi khép kín.

### Bước 6. Bổ sung route đọc dữ liệu

`GET /raw-data` giúp:

- kiểm tra dữ liệu có được lưu không,
- phục vụ demo,
- mở đường cho frontend hoặc dashboard đọc dữ liệu.

### Bước 7. Chuẩn bị cấu trúc cho aggregation và prediction

Nhóm đã tạo sẵn:

- model,
- schema,
- route,
- service nền

cho aggregation và prediction, dù logic thật chưa hoàn thiện.

Đây là cách làm có định hướng mở rộng: dựng sẵn khung hệ thống trước, sau đó dần lấp logic.

### Bước 8. Xử lý bài toán lệch schema database

Việc thêm `sync_vehicle_detection_schema()` cho thấy một vấn đề thực tế:

- database đã tồn tại trước,
- model mới có thêm cột,
- cần cách cập nhật nhanh để không phải xóa DB cũ.

Đây là một hướng giải quyết thực dụng trong giai đoạn phát triển nội bộ.

## 9. Hướng giải quyết hiện tại của backend

Folder `backend` đang giải quyết bài toán theo hướng "đơn giản nhưng chạy được thật":

### 9.1. Dùng event-driven kiểu nhẹ qua HTTP

Thay vì queue phức tạp, detection gửi event trực tiếp sang backend bằng `POST`.

Ưu điểm:

- dễ làm,
- dễ debug,
- dễ quan sát bằng log hoặc test API.

Nhược điểm:

- nếu backend tắt hoặc chậm, detection có thể gửi lỗi,
- chưa có cơ chế retry/buffer mạnh.

### 9.2. Lưu dữ liệu gốc trước, tổng hợp sau

Backend ưu tiên lưu từng event vào `vehicle_detections`.

Ưu điểm:

- không mất dữ liệu thô,
- có thể tổng hợp lại nhiều kiểu khác nhau sau này,
- dễ kiểm tra pipeline.

### 9.3. Mở rộng dần thay vì làm đầy đủ ngay từ đầu

Ta thấy rõ điều này qua:

- có bảng aggregation nhưng chưa ghi dữ liệu,
- có bảng prediction nhưng chưa dùng,
- có schema response nhưng chưa có logic sâu tương ứng.

Đây là cách đi thường gặp ở prototype: dựng backbone trước, tối ưu sau.

## 10. Những gì backend đã làm được

Dựa trên mã nguồn hiện tại, backend đã làm được:

- khởi tạo API service bằng FastAPI,
- tự tạo bảng dữ liệu nếu chưa có,
- lưu event từ detection vào SQLite,
- validate đầu vào bằng Pydantic,
- có route đọc dữ liệu thô,
- có service phân loại mức ùn tắc đơn giản,
- có khung mở rộng cho aggregation, prediction và camera.

Đây là một nền tảng backend hoạt động được thật, không chỉ là cấu trúc lý thuyết.

## 11. Những điểm còn thiếu hoặc chưa hoàn chỉnh

Đây là phần rất quan trọng nếu muốn hiểu đúng hiện trạng folder `backend`.

### 11.1. Aggregation chưa dùng dữ liệu thật

Hiện `GET /aggregation` chỉ nhận `vehicle_count` từ query, chưa đọc từ `vehicle_detections`.

Nghĩa là:

- chưa có tổng hợp theo 1 phút,
- chưa có tổng hợp theo 5 phút,
- chưa ghi kết quả vào bảng `traffic_aggregation`.

### 11.2. Prediction mới là placeholder

`GET /predict-next` đang trả giá trị cứng `0.45`.

Chưa có:

- mô hình học máy,
- logic dự báo,
- dữ liệu lịch sử dùng cho huấn luyện/suy luận.

### 11.3. Chưa có quản lý camera đúng nghĩa

Bảng `cameras` đã có nhưng:

- chưa có dữ liệu,
- chưa có API CRUD,
- chưa liên kết khóa ngoại với detection event.

### 11.4. Chưa có migration chuẩn

Hiện tại dùng `sync_vehicle_detection_schema()` thay vì Alembic.

Điều này ổn cho prototype nhưng sẽ khó kiểm soát khi schema phức tạp dần.

### 11.5. Chưa có logging và error handling đầy đủ

Hiện chưa thấy:

- middleware log request,
- exception handler chung,
- log file riêng cho backend,
- phân loại lỗi DB/validation/business logic.

### 11.6. API đọc dữ liệu còn đơn giản

`GET /raw-data` hiện:

- không phân trang,
- không lọc theo thời gian,
- không lọc theo camera,
- không lọc theo loại xe.

Khi dữ liệu lớn lên, đây sẽ là nút thắt.

## 12. Hướng phát triển và giải quyết tiếp theo

Nếu muốn hoàn thiện `backend` theo hướng bài bản hơn, nên đi theo thứ tự sau:

### 12.1. Hoàn thiện aggregation thật sự

Nên bổ sung logic:

- đọc dữ liệu từ `vehicle_detections`,
- nhóm theo `camera_id`,
- nhóm theo cửa sổ thời gian 1 phút, 5 phút,
- đếm số phương tiện,
- tính mức ùn tắc,
- lưu kết quả vào `traffic_aggregation`.

Đây là bước quan trọng nhất vì nó biến backend từ nơi lưu data thành nơi tạo tri thức tổng hợp.

### 12.2. Chuẩn hóa camera

Nên:

- thêm dữ liệu camera vào bảng `cameras`,
- dùng `camera_id` nhất quán,
- nếu có thể, thêm foreign key hoặc mapping logic.

### 12.3. Tăng độ chặt cho validation

Ví dụ:

- `vehicle_type` chỉ cho phép tập giá trị hợp lệ,
- `density` nên chuyển thành enum,
- `confidence` nên bị chặn trong khoảng `0 -> 1`,
- không cho chuỗi rỗng ở các trường bắt buộc.

### 12.4. Thêm logging và xử lý lỗi

Nên bổ sung:

- log request thành công/thất bại,
- log lỗi DB,
- log lỗi validation,
- response lỗi rõ ràng hơn cho client.

### 12.5. Thêm API truy vấn thực tế hơn

Ví dụ:

- lấy dữ liệu theo ngày/giờ,
- lọc theo camera,
- lọc theo loại xe,
- trả thống kê tổng hợp thay vì chỉ dữ liệu thô.

### 12.6. Chuyển sang migration chuẩn

Nên dùng Alembic khi:

- schema bắt đầu ổn định hơn,
- cần quản lý thay đổi DB theo version,
- muốn triển khai trên nhiều môi trường.

### 12.7. Cân nhắc nâng cấp database

SQLite phù hợp để demo và phát triển local.

Nếu hệ thống lớn hơn:

- nên cân nhắc PostgreSQL,
- tận dụng `psycopg2-binary` đã có trong `requirements.txt`.

## 13. Tóm tắt ngắn gọn để dễ nhớ

Nếu cần hiểu nhanh folder `backend`, có thể ghi nhớ như sau:

- `backend` là nơi nhận event giao thông từ `detection`.
- Event được kiểm tra bằng Pydantic.
- Dữ liệu được lưu bằng SQLAlchemy vào `traffic.db`.
- `vehicle_detections` là bảng quan trọng nhất hiện tại.
- `aggregation` và `prediction` mới ở mức khung.
- Kiến trúc đã đúng hướng, nhưng phần xử lý nghiệp vụ sâu vẫn còn cần hoàn thiện.

## 14. Kết luận

Folder `backend` hiện là xương sống dữ liệu của dự án.

Nó đã giải quyết được bài toán cốt lõi nhất:

- nhận dữ liệu từ hệ thống nhận diện,
- chuẩn hóa dữ liệu,
- lưu vào database,
- cung cấp API cơ bản để truy xuất.

Điểm mạnh của thiết kế hiện tại là:

- tách lớp rõ ràng,
- dễ hiểu,
- phù hợp với đồ án và giai đoạn prototype,
- đã chạy được với dữ liệu thực.

Điểm còn thiếu là:

- aggregation thật từ database,
- prediction thật,
- logging,
- migration chuẩn,
- truy vấn dữ liệu nâng cao.

Nếu tiếp tục phát triển, `backend` hoàn toàn có thể trở thành một service trung tâm đủ mạnh để phục vụ dashboard, phân tích giao thông theo thời gian thực và dự báo mật độ trong các bước sau của dự án.
