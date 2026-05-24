# Báo cáo cập nhật Module Backend - Đợt 2

## 1. Mục tiêu phát triển trong đợt 2

Sau đợt 1, backend đã hoàn thành nền tảng cơ bản gồm API nhận sự kiện nhận diện, kiểm tra dữ liệu đầu vào, lưu dữ liệu và xây dựng khung tổng hợp ban đầu. Sang đợt 2, mục tiêu của Module Backend không chỉ dừng lại ở việc tiếp nhận dữ liệu từ Module A, mà mở rộng thành một lớp xử lý trung tâm cho toàn hệ thống phân tích mật độ giao thông.

Các mục tiêu chính trong đợt 2 gồm:

- Mở rộng backend từ chức năng lưu dữ liệu thô sang truy vấn, tổng hợp, dự báo và hỗ trợ tích hợp thời gian thực.
- Hoàn thiện thêm các API phục vụ các module khác như dashboard, tích hợp hệ thống và mô hình dự báo.
- Tăng khả năng lọc, phân trang và truy xuất dữ liệu đã lưu.
- Bổ sung hướng xử lý theo camera, theo khoảng thời gian và theo chiều di chuyển của phương tiện.
- Xây dựng bước đầu luồng dự báo mật độ giao thông dựa trên dữ liệu tổng hợp hoặc dữ liệu phát hiện thực tế.
- Bổ sung API quản lý camera ở mức cơ bản để backend không chỉ lưu event rời rạc mà còn có thông tin nguồn dữ liệu.
- Tăng độ ổn định vận hành thông qua health check, logging request và cơ chế xử lý lỗi chung.

Như vậy, trọng tâm của đợt 2 là chuyển backend từ một API lưu trữ đơn giản thành một dịch vụ dữ liệu có khả năng phục vụ phân tích giao thông.

## 2. Cách triển khai trong đợt 2

### a. Mở rộng giao thức API bằng FastAPI

Backend tiếp tục sử dụng `FastAPI` làm framework chính. So với đợt 1 mới tập trung vào endpoint `POST /detection`, đợt 2 đã mở rộng thêm nhiều nhóm route riêng biệt:

- `POST /detection`: nhận và lưu sự kiện phát hiện phương tiện.
- `GET /raw-data`: truy vấn dữ liệu phát hiện gốc.
- `GET /aggregation`: lấy kết quả tổng hợp nhanh hoặc tổng hợp từ dữ liệu đã lưu.
- `GET /aggregation/history`: xem lịch sử tổng hợp.
- `POST /aggregation/compute`: chốt dữ liệu tổng hợp theo cửa sổ thời gian.
- `GET /predict-next`: dự báo mật độ giao thông trong khoảng thời gian tiếp theo.
- `GET /predictions/history`: xem lịch sử dự báo.
- `GET /cameras` và `POST /cameras`: quản lý danh sách camera.
- `GET /health`: kiểm tra trạng thái backend và database.
- `GET /video`: cung cấp luồng video dạng streaming để phục vụ quan sát thời gian thực.

Các route được tách theo từng file trong thư mục `api/`, giúp cấu trúc backend rõ ràng hơn và dễ mở rộng khi số lượng endpoint tăng lên.

### b. Chuyển hướng lớp lưu trữ sang MongoDB cho dữ liệu vận hành

Trong đợt 1, hệ thống sử dụng `SQLite` kết hợp `SQLAlchemy ORM` để lưu dữ liệu thử nghiệm. Đến đợt 2, backend đã bổ sung `mongo_database.py` và `db_service.py` để kết nối với MongoDB thông qua `pymongo`.

Các collection chính đang được sử dụng gồm:

- `vehicle_detections`
- `traffic_aggregation`
- `traffic_predictions`
- `cameras`

MongoDB phù hợp hơn cho giai đoạn này vì dữ liệu event từ module nhận diện có dạng bản ghi JSON, thay đổi linh hoạt và có thể tăng nhanh theo thời gian. Backend cũng đã tạo index cho các trường quan trọng như `event_id`, `camera_id`, `timestamp` và `direction`. Điều này giúp việc kiểm tra trùng sự kiện, lọc theo camera và truy vấn theo thời gian hiệu quả hơn.

Bên cạnh đó, các model SQLAlchemy và phần `database.py` vẫn được giữ lại để duy trì cấu trúc tham chiếu và khả năng tương thích với phiên bản trước. Đây là bước chuyển tiếp hợp lý từ môi trường thử nghiệm SQLite sang môi trường lưu trữ linh hoạt hơn.

### c. Chuẩn hóa dữ liệu đầu vào chi tiết hơn

Phần schema bằng `Pydantic` tiếp tục được sử dụng và đã được mở rộng rõ hơn. Schema `DetectionCreate` hiện kiểm soát các trường:

- `event_id`
- `camera_id`
- `track_id`
- `vehicle_type`
- `density`
- `event_type`
- `timestamp`
- `confidence`
- `direction`

So với đợt 1, dữ liệu đầu vào đã được chuẩn hóa chặt hơn ở một số điểm. Trường `vehicle_type`, `density` và `event_type` được giới hạn bằng `Enum`, giúp tránh việc lưu các giá trị tự do không thống nhất. Trường `confidence` được ràng buộc trong khoảng từ `0` đến `1`. Trường `direction` được bổ sung để phân biệt chiều `inbound` và `outbound`, làm cơ sở cho các bước tính toán hàng đợi và điều chỉnh tín hiệu giao thông.

Ngoài ra, endpoint `POST /detection` đã có kiểm tra trùng `event_id`. Nếu một event đã tồn tại, backend trả về lỗi `409 Conflict` thay vì lưu trùng dữ liệu. Đây là cải tiến quan trọng so với giai đoạn chỉ kiểm tra định dạng cơ bản.

### d. Bổ sung API truy vấn dữ liệu thô

Đợt 2 đã bổ sung endpoint `GET /raw-data` để truy xuất lại dữ liệu phát hiện đã lưu trong `vehicle_detections`.

Endpoint này hỗ trợ các điều kiện lọc:

- `camera_id`
- `vehicle_type`
- `density`
- `direction`
- `start_time`
- `end_time`
- `limit`
- `offset`

Việc có API truy vấn dữ liệu thô giúp backend phục vụ tốt hơn cho dashboard, kiểm thử dữ liệu và các module phân tích sau này. Nếu ở đợt 1 dữ liệu chủ yếu chỉ được ghi vào database, thì ở đợt 2 dữ liệu đã có thể được khai thác lại theo nhiều tiêu chí khác nhau.

### e. Nâng cấp dịch vụ tổng hợp dữ liệu giao thông

Trong đợt 1, phần tổng hợp mới dừng ở việc nhận `vehicle_count` và phân loại mức ùn tắc theo các mức `Low`, `Medium`, `High`, `Severe`.

Ở đợt 2, `aggregation_service.py` đã được mở rộng đáng kể. Backend có thể tổng hợp trực tiếp từ dữ liệu detection đã lưu thay vì chỉ phụ thuộc vào số lượng xe truyền từ bên ngoài.

Các thông tin tổng hợp hiện gồm:

- `vehicle_count`: số lượng phương tiện trong khoảng thời gian.
- `inbound_count`: số lượng phương tiện theo chiều đi vào.
- `queue_proxy`: chỉ số ước lượng biến động hàng đợi dựa trên chênh lệch inbound so với lần tổng hợp trước.
- `congestion_level`: mức độ ùn tắc.
- `timestamp`: thời điểm tạo bản ghi tổng hợp.

Endpoint `POST /aggregation/compute` cho phép chốt kết quả tổng hợp theo `window_minutes`, mặc định là 15 phút. Khi tính toán, backend dùng `track_id` phân biệt để hạn chế đếm trùng phương tiện trong cùng một cửa sổ thời gian.

Đây là bước nâng cấp quan trọng vì backend bắt đầu chuyển từ lưu trữ dữ liệu sang tạo dữ liệu phân tích có ý nghĩa.

### f. Bổ sung chức năng dự báo mật độ giao thông

Đợt 2 đã xây dựng thêm nhóm chức năng dự báo thông qua `prediction_service.py` và `prediction_routes.py`.

Endpoint `GET /predict-next` lấy dữ liệu lịch sử từ `traffic_aggregation` hoặc từ `vehicle_detections`, sau đó tạo kết quả dự báo mật độ giao thông trong khoảng thời gian tiếp theo. Khoảng dự báo được cấu hình qua `PREDICTION_HORIZON_MINUTES`, mặc định là 15 phút.

Luồng dự báo hiện có hai chế độ:

- Nếu có mô hình trong `ml_service`, backend cố gắng tải `TrafficPredictor` và sử dụng mô hình đã huấn luyện.
- Nếu chưa có đủ điều kiện dùng mô hình, backend dùng cơ chế fallback bằng giá trị trung bình từ dữ liệu lịch sử.

Ngoài `predicted_density`, backend còn bổ sung `suggested_delta`. Trường này phục vụ định hướng điều chỉnh thời lượng đèn giao thông dựa trên mô hình phụ `LightDeltaModel` nếu có đủ dữ liệu và mô hình tương ứng.

Kết quả dự báo được lưu vào `traffic_predictions`, đồng thời có endpoint `GET /predictions/history` để xem lại lịch sử. So với đợt 1, đây là phần mở rộng rõ nhất về mặt mục tiêu xử lý dữ liệu.

### g. Bổ sung quản lý camera

Backend đã có thêm `camera_service.py`, `camera_schema.py` và route `/cameras`.

Thông tin camera hiện gồm:

- `camera_id`
- `name`
- `location`
- `baseline_green`
- `monitored_direction`

Việc bổ sung camera giúp dữ liệu detection và aggregation có ngữ cảnh rõ hơn. Thay vì chỉ lưu các event độc lập, backend bắt đầu quản lý nguồn phát sinh dữ liệu. Các trường `baseline_green` và `monitored_direction` cũng tạo nền tảng cho bài toán điều phối đèn giao thông ở các bước sau.

### h. Bổ sung health check, logging và xử lý lỗi chung

Đợt 2 đã cải thiện khả năng theo dõi trạng thái backend:

- `GET /health` kiểm tra trạng thái API và kết nối MongoDB.
- Middleware trong `main.py` ghi log method, path, status code và thời gian xử lý request.
- Exception handler chung trả về lỗi `500` có cấu trúc rõ ràng khi xảy ra lỗi chưa được xử lý.

Các phần này không trực tiếp tạo ra kết quả phân tích giao thông, nhưng rất cần thiết để backend ổn định hơn trong quá trình chạy demo và tích hợp với các module khác.

### i. Bổ sung luồng video thời gian thực

Backend đã có route `GET /video` sử dụng `StreamingResponse` để phát frame mới nhất từ module detection. Luồng này sử dụng định dạng `multipart/x-mixed-replace`, phù hợp để hiển thị video MJPEG trên client hoặc dashboard.

Chức năng này giúp backend không chỉ cung cấp dữ liệu dạng JSON mà còn có khả năng phục vụ quan sát trực tiếp kết quả nhận diện.

## 3. Kết quả đạt được so với đợt 1

So với đợt 1, Module Backend đã có những thay đổi đáng kể:

| Nội dung | Đợt 1 | Đợt 2 |
|---|---|---|
| Giao thức API | Chủ yếu có `POST /detection` và khung `GET /aggregation` | Mở rộng thành nhiều nhóm API: raw data, aggregation history, compute aggregation, prediction, camera, health, video |
| Lưu trữ dữ liệu | SQLite/SQLAlchemy phục vụ phát triển và thử nghiệm | Bổ sung MongoDB cho dữ liệu vận hành dạng JSON, có index phục vụ truy vấn |
| Kiểm tra dữ liệu | Schema Pydantic ở mức cơ bản | Enum, ràng buộc confidence, direction, kiểm tra trùng `event_id` |
| Truy vấn dữ liệu | Chưa nhấn mạnh truy xuất dữ liệu thô | Có `GET /raw-data` với filter theo camera, loại xe, mật độ, hướng, thời gian và phân trang |
| Tổng hợp dữ liệu | Phân loại ùn tắc từ `vehicle_count` | Tổng hợp trực tiếp từ database, có `inbound_count`, `queue_proxy`, lịch sử và compute theo cửa sổ thời gian |
| Dự báo | Chưa có hoặc mới ở mức định hướng | Có API dự báo, lưu lịch sử dự báo, fallback khi thiếu model, hỗ trợ `suggested_delta` |
| Quản lý camera | Có bảng camera ở mức khai báo | Có API thêm và lấy danh sách camera, bổ sung thông tin hướng giám sát và đèn nền |
| Theo dõi hệ thống | Chưa nổi bật | Có health check, request logging và exception handler chung |
| Tích hợp thời gian thực | Chủ yếu nhận event JSON | Có thêm endpoint streaming video từ module detection |

Kết quả quan trọng nhất của đợt 2 là backend đã hình thành đầy đủ hơn vai trò của Module B trong hệ thống. Backend hiện không chỉ nhận dữ liệu từ Module A mà còn có thể lưu trữ linh hoạt, truy vấn, tổng hợp, dự báo và cung cấp dữ liệu cho các thành phần hiển thị hoặc điều khiển tiếp theo.

## 4. Đánh giá mức độ hoàn thiện

Các phần đã đạt được ở đợt 2:

- API backend được mở rộng rõ ràng và chia theo từng nhóm chức năng.
- Dữ liệu detection có kiểm tra trùng và chuẩn hóa tốt hơn.
- MongoDB được đưa vào làm cơ sở lưu trữ chính cho dữ liệu vận hành.
- Dữ liệu thô có thể truy vấn lại bằng nhiều bộ lọc.
- Aggregation đã có khả năng tính từ dữ liệu thực tế trong database.
- Prediction đã có luồng xử lý riêng, có fallback và có lưu lịch sử.
- Camera đã có API quản lý cơ bản.
- Backend có health check, logging và xử lý lỗi chung.
- Có bước đầu hỗ trợ streaming video phục vụ quan sát thời gian thực.

Một số điểm còn có thể tiếp tục nâng cấp:

- Hoàn thiện cơ chế migration rõ ràng nếu tiếp tục duy trì song song SQLAlchemy và MongoDB.
- Bổ sung authentication và phân quyền cho các API quan trọng.
- Chuẩn hóa response model cho toàn bộ endpoint.
- Bổ sung test tự động cho detection, aggregation và prediction.
- Tối ưu thuật toán `queue_proxy` bằng dữ liệu giao thông thực tế hơn.
- Hoàn thiện mô hình dự báo trong `ml_service` để giảm phụ thuộc vào cơ chế fallback.
- Bổ sung API tổng hợp dashboard theo nhiều camera và nhiều khung thời gian.

## 5. Kết luận

Trong đợt 1, backend đã hoàn thành nhiệm vụ nền tảng là nhận dữ liệu từ module nhận diện, kiểm tra định dạng và lưu vào cơ sở dữ liệu. Đến đợt 2, backend đã được mở rộng thành một lớp dịch vụ dữ liệu hoàn chỉnh hơn, có khả năng truy vấn, tổng hợp, dự báo và hỗ trợ tích hợp thời gian thực.

Sự thay đổi lớn nhất là backend đã bắt đầu đảm nhiệm vai trò xử lý nghiệp vụ của hệ thống giao thông, không chỉ là nơi lưu dữ liệu thô. Các chức năng như tổng hợp theo cửa sổ thời gian, dự báo mật độ, quản lý camera và streaming video tạo nền tảng để các module tiếp theo phát triển dashboard giám sát, phân tích ùn tắc và đề xuất điều chỉnh tín hiệu giao thông.
