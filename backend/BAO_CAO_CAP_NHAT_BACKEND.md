# Báo cáo cập nhật module Backend - Đợt 2

Ngày lập báo cáo: 02/05/2026

Phạm vi báo cáo: báo cáo tập trung vào các công việc đã triển khai trong module `backend` ở đợt 2, bao gồm mục tiêu của đợt 2, cách triển khai kỹ thuật, kết quả đạt được và mức độ cải thiện so với các hạn chế đã nêu trong báo cáo đợt 1 ngày 20/03.

## 1. Bối cảnh từ báo cáo đợt 1

Trong báo cáo đợt 1, nhóm đã xác định một số khó khăn cốt lõi ảnh hưởng trực tiếp đến hiệu quả của hệ thống phân tích mật độ giao thông:

- Mô hình nhận diện phương tiện chưa tối ưu với đặc thù giao thông Việt Nam, đặc biệt là xe máy di chuyển sát nhau thành cụm.
- Dữ liệu đầu vào cho Machine Learning còn phụ thuộc nhiều vào dữ liệu giả lập.
- Việc xử lý video dài bằng Computer Vision tiêu tốn nhiều CPU/GPU, dễ gây quá tải trên thiết bị cá nhân.
- Do chỉ xử lý được video ngắn, lượng dữ liệu lịch sử chưa đủ dày để huấn luyện và đánh giá mô hình dự báo một cách ổn định.
- Nhóm cần có hướng xử lý dữ liệu thực tốt hơn, giảm phụ thuộc vào `generate_dummy_data` và từng bước xây dựng pipeline dữ liệu thực từ detection đến dự báo.

Từ các hạn chế đó, trọng tâm của đợt 2 không phải là tối ưu toàn bộ mô hình nhận diện, mà là xây dựng lại nền backend để có thể tiếp nhận, lưu trữ, tổng hợp và khai thác dữ liệu thật tốt hơn. Backend được xem là lớp trung gian quan trọng giữa module Computer Vision, cơ sở dữ liệu, module Machine Learning và frontend.

## 2. Mục tiêu của đợt 2

Mục tiêu chính của đợt 2 là biến backend từ một API demo đơn giản thành một lớp dữ liệu có khả năng phục vụ luồng xử lý thực tế của hệ thống.

Cụ thể, đợt 2 đặt ra các mục tiêu sau:

1. Chuyển backend sang hướng làm việc với dữ liệu thật thay vì chỉ dựa vào dữ liệu giả lập.
2. Kết nối backend với MongoDB Atlas để lưu trữ dữ liệu detection theo dạng document linh hoạt hơn.
3. Xây dựng API nhận event từ module detection và lưu lại làm dữ liệu lịch sử.
4. Bổ sung khả năng truy vấn dữ liệu thô theo camera, thời gian, loại xe, mật độ và hướng di chuyển.
5. Xây dựng module aggregation để tổng hợp dữ liệu detection thành các chỉ số giao thông có ý nghĩa hơn.
6. Tạo nền dữ liệu cho module prediction bằng cách lấy lịch sử từ database thay vì phụ thuộc hoàn toàn vào `generate_dummy_data`.
7. Tích hợp kết quả dự báo với gợi ý điều chỉnh đèn giao thông thông qua trường `suggested_delta`.
8. Bổ sung các API hỗ trợ vận hành như health check, camera management, prediction history và aggregation history.
9. Cải thiện khả năng quan sát hệ thống thông qua request logging, response lỗi rõ hơn và health check database.
10. Tạo cơ sở để các đợt tiếp theo có thể mở rộng dashboard, test tự động, quản lý dataset và tối ưu mô hình.

Nói ngắn gọn, mục tiêu của đợt 2 là giải quyết phần “nền dữ liệu thật” cho hệ thống: detection có nơi lưu, backend có thể tổng hợp, ML có dữ liệu lịch sử để khai thác, frontend có API để hiển thị.

## 3. Định hướng triển khai đợt 2

Đợt 2 được triển khai theo hướng xây dựng backend thành các lớp rõ ràng:

- API layer: nhận request, validate đầu vào và trả response.
- Schema layer: định nghĩa định dạng dữ liệu bằng Pydantic.
- Service layer: xử lý logic nghiệp vụ như detection, aggregation, prediction và camera.
- Database layer: kết nối MongoDB, tạo index và cung cấp database object cho các route.
- Integration layer: kết nối backend với `ml_service` và module detection/video.

Cách triển khai này giúp backend dễ mở rộng hơn so với việc viết toàn bộ logic trực tiếp trong route. Các chức năng như lưu detection, tổng hợp dữ liệu và dự báo đều được tách ra service riêng để dễ kiểm thử và bảo trì.

## 4. Cách triển khai chi tiết trong đợt 2

### 4.1. Kết nối MongoDB Atlas

Backend đã được bổ sung file `backend/mongo_database.py` để quản lý kết nối MongoDB.

Các việc đã triển khai:

- Đọc chuỗi kết nối từ `DB_URL` hoặc `MONGODB_URI`.
- Đọc tên database từ `MONGODB_DB`.
- Tạo `MongoClient` bằng PyMongo.
- Cung cấp biến `db` dùng chung cho các service.
- Thêm hàm `ping_mongo()` để kiểm tra trạng thái database.
- Thêm hàm `init_mongo_indexes()` để tạo index cho các collection quan trọng.

Các collection chính được sử dụng:

- `vehicle_detections`: lưu event detection từ module Computer Vision.
- `traffic_aggregation`: lưu các bản ghi tổng hợp mật độ giao thông.
- `traffic_predictions`: lưu lịch sử dự báo.
- `cameras`: lưu thông tin camera.

Các index đã được tạo:

- Unique index trên `vehicle_detections.event_id` để chống trùng event.
- Index trên `camera_id` để truy vấn theo camera nhanh hơn.
- Index trên `timestamp` để lấy dữ liệu mới nhất hiệu quả hơn.
- Compound index trên `camera_id` và `timestamp` cho lịch sử theo camera.
- Index trên `direction` để phục vụ thống kê luồng xe vào/ra.
- Index tương tự cho `traffic_aggregation` và `traffic_predictions`.

Việc chuyển sang MongoDB giúp backend phù hợp hơn với dữ liệu event có tần suất cao và cấu trúc linh hoạt.

### 4.2. Cập nhật cấu hình backend

File `backend/config.py` đã được mở rộng để đọc các biến môi trường cần thiết:

- `DATABASE_URL`: giữ lại để tương thích với phần SQLAlchemy cũ.
- `DB_URL` hoặc `MONGODB_URI`: chuỗi kết nối MongoDB Atlas.
- `MONGODB_DB`: tên database MongoDB.
- `BACKEND_API_TITLE`: tên FastAPI app.
- `DEFAULT_PAGE_SIZE`: số bản ghi mặc định khi phân trang.
- `MAX_PAGE_SIZE`: giới hạn số bản ghi tối đa cho mỗi request.
- `PREDICTION_HORIZON_MINUTES`: khoảng thời gian dự báo, mặc định 15 phút.

Nhờ đó, backend có thể cấu hình linh hoạt hơn qua file `.env`, phù hợp với cả môi trường local và môi trường demo/deploy.

### 4.3. Điều chỉnh luồng database trong service

File `backend/services/db_service.py` hiện trả về Mongo database object:

```python
from backend.mongo_database import db

def get_db():
    yield db
```

Các route chính không còn phụ thuộc vào SQLAlchemy session như trước. Thay vào đó, route dùng `Depends(get_db)` để lấy Mongo database và thao tác với các collection.

File `backend/database.py` và các model SQLAlchemy vẫn được giữ lại để tương thích với code cũ hoặc phục vụ migrate nếu cần, nhưng luồng chạy chính của backend đợt 2 đã chuyển sang MongoDB.

### 4.4. Hoàn thiện API nhận dữ liệu detection

Endpoint:

```text
POST /detection
```

Trong đợt 2, API detection được triển khai để nhận event từ module Computer Vision và lưu vào MongoDB.

Payload detection được chuẩn hóa qua `backend/schemas/detection_schema.py`, gồm:

- `event_id`: mã event duy nhất.
- `camera_id`: mã camera.
- `track_id`: mã theo dõi phương tiện.
- `vehicle_type`: loại phương tiện.
- `density`: mức mật độ.
- `event_type`: loại sự kiện.
- `timestamp`: thời điểm xảy ra event.
- `confidence`: độ tin cậy.
- `direction`: hướng di chuyển, gồm `inbound` và `outbound`.

Logic xử lý:

- Kiểm tra `event_id` đã tồn tại chưa.
- Nếu đã tồn tại, trả về HTTP 409 để tránh lưu trùng dữ liệu.
- Nếu hợp lệ, lưu document vào collection `vehicle_detections`.
- Trả về `status`, `id` và `event_id`.

Kết quả của phần này là backend đã có điểm nhận dữ liệu thật từ detection, thay vì chỉ hoạt động với dữ liệu mô phỏng hoặc dữ liệu tĩnh.

### 4.5. Bổ sung API truy vấn dữ liệu thô

Endpoint:

```text
GET /raw-data
```

API này được dùng để xem lại dữ liệu detection đã lưu.

Các khả năng đã triển khai:

- Lọc theo `camera_id`.
- Lọc theo `vehicle_type`.
- Lọc theo `density`.
- Lọc theo `direction`.
- Lọc theo `start_time` và `end_time`.
- Hỗ trợ `limit` và `offset`.
- Giới hạn `limit` theo `MAX_PAGE_SIZE`.
- Sắp xếp dữ liệu mới nhất trước.
- Chuẩn hóa `_id` của MongoDB thành `id` trong response.

API raw data giúp nhóm kiểm tra dữ liệu thật từ detection, phục vụ debug, phân tích và làm nền cho dashboard.

### 4.6. Xây dựng module aggregation

Đợt 2 đã mở rộng aggregation từ mức tính đơn giản sang tổng hợp từ dữ liệu thật trong database.

Các chỉ số hiện có:

- `vehicle_count`: số lượng xe/event trong khoảng thời gian.
- `inbound_count`: số lượng xe đi vào khu vực theo dõi.
- `queue_proxy`: chỉ số xấp xỉ biến động hàng đợi.
- `congestion_level`: mức ùn tắc gồm `Low`, `Medium`, `High`, `Severe`.

Các endpoint aggregation:

```text
GET /aggregation
GET /aggregation/history
POST /aggregation/compute
```

Cách triển khai:

- `GET /aggregation` có thể tính nhanh từ `vehicle_count` hoặc tự truy vấn detection từ database.
- `GET /aggregation/history` trả về lịch sử các bản ghi tổng hợp.
- `POST /aggregation/compute` chốt aggregation theo cửa sổ thời gian, mặc định 15 phút.
- Khi compute theo cửa sổ thời gian, backend dùng `distinct("track_id")` để giảm nguy cơ đếm lặp cùng một xe.
- Kết quả aggregation được lưu vào collection `traffic_aggregation`.

Phần này giúp dữ liệu detection rời rạc được chuyển thành dữ liệu tổng hợp có thể dùng cho dashboard và prediction.

### 4.7. Nâng cấp module prediction

Trước đợt 2, prediction còn ở mức demo, có thể chỉ trả về giá trị cố định như:

```json
{
  "predicted_density": 0.45
}
```

Trong đợt 2, prediction đã được nâng cấp theo hướng lấy dữ liệu lịch sử từ database.

Endpoint:

```text
GET /predict-next
GET /predictions/history
```

Cách triển khai:

- Backend lấy lịch sử aggregation gần nhất theo `camera_id`.
- Nếu aggregation chưa đủ, backend fallback sang build history từ `vehicle_detections`.
- Nếu có model trong `ml_service`, backend cố gắng load `TrafficPredictor`.
- Nếu không load được model hoặc chưa đủ dữ liệu, backend fallback về trung bình lịch sử.
- Mỗi lần dự báo đều được lưu vào collection `traffic_predictions`.
- API `/predictions/history` cho phép xem lại lịch sử dự báo.

Như vậy, prediction đã bắt đầu sử dụng dữ liệu thực tế từ database, thay vì phụ thuộc hoàn toàn vào dữ liệu giả lập.

### 4.8. Tích hợp gợi ý điều chỉnh đèn giao thông

Đợt 2 bổ sung trường `suggested_delta` vào prediction.

Ý nghĩa:

- `suggested_delta` là gợi ý điều chỉnh thời gian đèn giao thông dựa trên tình trạng lưu lượng.
- Trường này giúp kết nối kết quả dự báo với bài toán điều khiển đèn.

Cách triển khai:

- Backend cố gắng load `LightDeltaModel` từ `ml_service/light_model.pkl`.
- Tạo feature từ dữ liệu gần nhất:
  - `hour`
  - `day_of_week`
  - `is_peak_hour`
  - `inbound_count`
  - `queue_proxy`
- Gọi model để dự đoán `suggested_delta`.
- Nếu model lỗi hoặc chưa sẵn sàng, backend fallback về `0.0`.

Các file liên quan đã được cập nhật:

- `backend/models/traffic_prediction.py`
- `backend/schemas/prediction_schema.py`
- `backend/services/prediction_service.py`
- `backend/api/prediction_routes.py`
- `backend/database.py`

### 4.9. Bổ sung quản lý camera

Endpoint:

```text
GET /cameras
POST /cameras
```

Backend đã có API tối thiểu để quản lý camera:

- Lấy danh sách camera.
- Tạo camera mới.
- Lưu `camera_id`, `name`, `location`, `baseline_green`, `monitored_direction`.

Thông tin camera giúp hệ thống không chỉ xử lý các event rời rạc mà còn có metadata để phục vụ dashboard và các logic điều khiển về sau.

### 4.10. Bổ sung health check, logging và xử lý lỗi

Endpoint:

```text
GET /health
```

Health check hiện trả về:

- Trạng thái API.
- Trạng thái MongoDB.
- Thời điểm kiểm tra.

Ngoài ra, `backend/main.py` đã được bổ sung:

- Middleware log request, gồm method, path, status code và thời gian xử lý.
- Exception handler chung để trả về response 500 có cấu trúc rõ ràng hơn.
- Gọi `init_mongo_indexes()` khi app được load.

Các thay đổi này giúp backend dễ theo dõi hơn trong quá trình chạy thử và demo.

### 4.11. Bổ sung video stream

Endpoint:

```text
GET /video
```

Backend đã có route để stream frame mới nhất từ `detection.main.latest_frame`.

Chức năng:

- Đọc frame mới nhất từ module detection.
- Nếu chưa có frame thì chờ ngắn.
- Trả về `StreamingResponse` với media type `multipart/x-mixed-replace`.

Tính năng này phục vụ nhu cầu quan sát kết quả detection gần thời gian thực trên client hoặc giao diện demo.

### 4.12. Bổ sung seed dữ liệu

File `backend/seed_data.py` được dùng để tạo dữ liệu phụ từ detection đã có.

Script thực hiện:

- Khởi tạo index MongoDB.
- Kiểm tra dữ liệu trong `vehicle_detections`.
- Lấy danh sách camera từ detection.
- Tạo hoặc cập nhật camera.
- Tạo aggregation ban đầu cho mỗi camera nếu chưa có.
- Tạo prediction cho mỗi camera.

Seed script giúp nhóm nhanh chóng tạo dữ liệu nền cho dashboard, aggregation và prediction sau khi đã có một lượng detection nhất định.

## 5. Kết quả đạt được trong đợt 2

Sau đợt 2, module backend đã đạt được các kết quả chính sau:

1. Backend đã kết nối được MongoDB Atlas thông qua `.env`.
2. Dữ liệu detection có thể được lưu vào collection `vehicle_detections`.
3. Backend có cơ chế chống trùng event thông qua `event_id`.
4. Dữ liệu thô có thể được truy vấn lại theo camera, loại xe, mật độ, hướng và khoảng thời gian.
5. Backend có thể tổng hợp dữ liệu detection thành các bản ghi aggregation.
6. Aggregation đã có thêm `inbound_count` và `queue_proxy`, phục vụ bài toán điều khiển đèn.
7. Backend có thể chốt aggregation theo cửa sổ thời gian bằng `POST /aggregation/compute`.
8. Prediction đã có thể lấy dữ liệu lịch sử từ database thay vì chỉ dựa vào mock data.
9. Kết quả prediction được lưu vào collection `traffic_predictions`.
10. Prediction response đã có `suggested_delta`.
11. Backend có API xem lịch sử aggregation và prediction.
12. Backend có API quản lý camera ở mức tối thiểu.
13. Backend có health check kiểm tra cả API và MongoDB.
14. Backend có request logging và exception handler chung.
15. Backend có endpoint stream video phục vụ demo.
16. Backend có script seed dữ liệu để hỗ trợ tạo dữ liệu nền.

## 6. So sánh kết quả đợt 2 với hạn chế của đợt 1

### 6.1. Về vấn đề dữ liệu giả lập trong Machine Learning

Hạn chế đợt 1:

- Module dự báo lưu lượng còn phụ thuộc vào dữ liệu mô phỏng từ `generate_dummy_data`.
- Dữ liệu chưa phản ánh đầy đủ tình hình giao thông thực tế.

Kết quả đợt 2:

- Backend đã có khả năng lưu detection thật vào MongoDB.
- Prediction đã có thể lấy lịch sử từ `traffic_aggregation` hoặc `vehicle_detections`.
- Mỗi kết quả dự báo được lưu lại để tạo lịch sử prediction.
- Dữ liệu giả lập không còn là nguồn duy nhất cho prediction.

Mức độ cải thiện:

- Đợt 2 đã giải quyết được một phần quan trọng của vấn đề phụ thuộc dữ liệu giả lập.
- Tuy nhiên, nếu dữ liệu thật chưa đủ hoặc model chưa load được, backend vẫn cần fallback về trung bình lịch sử.
- Vì vậy, hệ thống đã chuyển từ “phụ thuộc hoàn toàn vào dữ liệu giả lập” sang “ưu tiên dữ liệu thật, có fallback khi thiếu dữ liệu hoặc thiếu model”.

### 6.2. Về vấn đề thiếu dữ liệu lịch sử

Hạn chế đợt 1:

- Nhóm chỉ xử lý được video ngắn, dẫn đến dataset mỏng.
- Dữ liệu không đủ dày để huấn luyện mô hình Machine Learning hiệu quả.

Kết quả đợt 2:

- Backend đã lưu lại từng event detection vào MongoDB.
- Có API raw data để xem lại dữ liệu đã thu thập.
- Có aggregation history để tạo chuỗi dữ liệu theo thời gian.
- Có prediction history để theo dõi kết quả dự báo.
- Có seed script để tạo dữ liệu phụ từ dữ liệu detection đã có.

Mức độ cải thiện:

- Backend đã tạo được nền tảng tích lũy dữ liệu lâu dài.
- Thay vì chỉ có các video ngắn rời rạc, hệ thống đã có nơi lưu dữ liệu event và dữ liệu tổng hợp theo thời gian.
- Tuy nhiên, chất lượng và độ dày dataset vẫn phụ thuộc vào thời gian chạy detection và số lượng camera/video thực tế.

### 6.3. Về đặc thù giao thông Việt Nam và xe máy đi thành cụm

Hạn chế đợt 1:

- YOLOv9 tiền huấn luyện chưa tối ưu với dòng phương tiện hỗn hợp.
- Xe máy đi sát nhau làm giảm độ chính xác nhận diện riêng lẻ.

Kết quả đợt 2:

- Backend chưa trực tiếp cải thiện độ chính xác của YOLOv9.
- Tuy nhiên, backend đã bổ sung các trường như `track_id`, `vehicle_type`, `direction`, `confidence`, `timestamp`.
- Aggregation compute dùng `distinct("track_id")` để giảm nguy cơ đếm lặp cùng một xe trong cửa sổ thời gian.
- Dữ liệu detection được lưu lại, tạo điều kiện để phân tích lỗi nhận diện về sau.

Mức độ cải thiện:

- Đợt 2 chưa giải quyết tận gốc bài toán nhận diện xe máy.
- Nhưng backend đã tạo nền dữ liệu để nhóm có thể kiểm tra, thống kê và đánh giá lỗi detection theo thời gian.
- Đây là bước chuẩn bị cần thiết cho việc cải thiện model detection ở các đợt tiếp theo.

### 6.4. Về rào cản tài nguyên khi xử lý video

Hạn chế đợt 1:

- Xử lý video dài tiêu tốn CPU/GPU.
- Thiết bị cá nhân dễ bị quá tải.
- Nhóm chỉ thử nghiệm được video ngắn.

Kết quả đợt 2:

- Backend không xử lý YOLO trực tiếp, nhưng đã đảm nhiệm việc lưu và khai thác kết quả detection.
- Video stream `/video` chỉ stream frame mới nhất phục vụ quan sát, không thay thế pipeline xử lý video.
- Dữ liệu detection sau khi được sinh ra có thể được lưu lại, giảm việc phải xử lý lại cùng một video nhiều lần.

Mức độ cải thiện:

- Backend không làm giảm trực tiếp chi phí GPU/CPU của Computer Vision.
- Nhưng backend giúp tận dụng tốt hơn kết quả đã xử lý bằng cách lưu lại event và aggregation.
- Điều này gián tiếp giảm nhu cầu chạy lại video nhiều lần chỉ để lấy lại dữ liệu.

### 6.5. Về chiến lược xử lý dữ liệu

Hạn chế đợt 1:

- Nhóm mới đề xuất chia nhỏ video và kết hợp dữ liệu thật với dữ liệu giả lập.
- Chưa có pipeline backend rõ ràng để lưu, tổng hợp và khai thác dữ liệu thật.

Kết quả đợt 2:

- Backend đã hình thành pipeline dữ liệu:

```text
Detection engine
    -> POST /detection
    -> vehicle_detections
    -> raw-data / aggregation
    -> traffic_aggregation
    -> prediction
    -> traffic_predictions
    -> frontend / integration system
```

- Có dữ liệu thô.
- Có dữ liệu tổng hợp.
- Có dữ liệu dự báo.
- Có lịch sử theo camera.

Mức độ cải thiện:

- Đợt 2 đã chuyển chiến lược xử lý dữ liệu từ mức đề xuất sang mức có triển khai cụ thể trong backend.
- Đây là cải thiện quan trọng nhất so với đợt 1.

## 7. Những hạn chế còn tồn tại sau đợt 2

Mặc dù module backend đã cải thiện rõ rệt, vẫn còn một số hạn chế cần tiếp tục xử lý:

1. Backend vẫn phụ thuộc vào chất lượng dữ liệu từ module detection. Nếu detection nhận diện sai hoặc bỏ sót xe, backend vẫn lưu và xử lý trên dữ liệu đó.
2. Chưa có cơ chế làm sạch dữ liệu nâng cao, ví dụ phát hiện timestamp bất thường, track bị lỗi, camera gửi dữ liệu quá dày hoặc quá thưa.
3. Ngưỡng `Low`, `Medium`, `High`, `Severe` còn cố định, chưa cá nhân hóa theo từng tuyến đường hoặc từng camera.
4. `queue_proxy` mới là chỉ số xấp xỉ, chưa phản ánh chính xác chiều dài hàng chờ thực tế.
5. Prediction vẫn có fallback khi thiếu dữ liệu hoặc không load được model.
6. Chưa có pipeline quản lý dataset đầy đủ cho Machine Learning, ví dụ version dataset, export dataset, đánh dấu dữ liệu thật/seed/mô phỏng.
7. Chưa có test tự động cho các API quan trọng.
8. Chưa có authentication/authorization cho các endpoint ghi dữ liệu.
9. Video stream có thể gây tải nếu nhiều client cùng truy cập.
10. `backend/README.md` cũ vẫn cần được cập nhật lại để khớp với trạng thái MongoDB hiện tại.

## 8. Định hướng công việc tiếp theo

Sau đợt 2, các công việc nên ưu tiên ở giai đoạn tiếp theo gồm:

1. Bổ sung test tự động cho detection, raw data, aggregation, prediction và health check.
2. Cập nhật lại `backend/README.md` để phản ánh đúng kiến trúc MongoDB hiện tại.
3. Bổ sung bước kiểm tra và làm sạch dữ liệu trước khi aggregation/prediction.
4. Xây dựng endpoint xuất dataset phục vụ huấn luyện ML.
5. Phân biệt rõ dữ liệu thật, dữ liệu seed và dữ liệu mô phỏng.
6. Tối ưu logic congestion theo từng camera hoặc từng tuyến đường.
7. Làm rõ đơn vị và ý nghĩa nghiệp vụ của `suggested_delta`.
8. Thêm cơ chế retry hoặc buffer nếu MongoDB tạm thời mất kết nối.
9. Bổ sung xác thực API cho các endpoint ghi dữ liệu.
10. Kiểm soát tài nguyên cho video stream nếu triển khai nhiều client.

## 9. Kết luận

Đợt 2 đã giúp module backend tiến một bước quan trọng từ mức demo sang mức có khả năng vận hành với dữ liệu thật. Nếu ở đợt 1 hệ thống còn gặp hạn chế lớn do thiếu dữ liệu, phụ thuộc vào dữ liệu giả lập và chưa có pipeline lưu trữ rõ ràng, thì sau đợt 2 backend đã có thể tiếp nhận detection event, lưu vào MongoDB, truy vấn dữ liệu thô, tổng hợp thành aggregation, tạo prediction và trả về gợi ý điều chỉnh đèn giao thông.

So với đợt 1, kết quả nổi bật nhất là backend đã trở thành trung tâm dữ liệu của hệ thống. Dữ liệu không còn chỉ tồn tại tạm thời trong quá trình chạy detection mà đã được lưu lại, tổng hợp và tái sử dụng cho dự báo. Điều này tạo nền tảng cần thiết để nhóm tiếp tục cải thiện mô hình Machine Learning, dashboard và các chức năng điều khiển giao thông trong các giai đoạn sau.
