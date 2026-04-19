# BÁO CÁO TỔNG QUAN MODULE B: DATA PIPELINE & API SERVICE

## 1. Giới thiệu chung

Module B trong dự án `Traffic Density Analysis System` đóng vai trò là lớp trung gian giữa khối nhận diện giao thông và lớp lưu trữ, khai thác dữ liệu. Nếu khối `detection` chịu trách nhiệm đọc video, nhận diện phương tiện và tạo sự kiện, thì Module B có nhiệm vụ tiếp nhận các sự kiện đó, kiểm tra tính hợp lệ của dữ liệu, lưu xuống cơ sở dữ liệu và cung cấp API để truy vấn hoặc tổng hợp kết quả.

Nói cách khác, đây là phần đảm nhiệm bài toán `data pipeline + API service` của toàn hệ thống. Trong phạm vi mã nguồn hiện tại, backend đã được triển khai bằng `FastAPI`, kết nối cơ sở dữ liệu thông qua `SQLAlchemy` và đang sử dụng `SQLite` với file dữ liệu thực tế là `traffic.db`.

## 2. Mục tiêu của Module B

Theo yêu cầu được giao, Module B hướng đến các mục tiêu chính sau:

- Thiết kế cơ sở dữ liệu phục vụ lưu trữ dữ liệu phát hiện giao thông.
- Xây dựng REST API để nhận và cung cấp dữ liệu.
- Kiểm tra dữ liệu đầu vào bằng Pydantic.
- Thực hiện tổng hợp dữ liệu giao thông theo mốc thời gian.
- Bổ sung logging và xử lý lỗi để hệ thống ổn định hơn.

Trong hiện trạng dự án, một phần các mục tiêu này đã được thực hiện, một phần mới ở mức khởi tạo cấu trúc, và một số phần vẫn chưa hoàn thành đầy đủ.

## 3. Cấu trúc backend hiện tại

Khối backend hiện được tổ chức trong thư mục `backend/` với các thành phần chính sau:

- `backend/main.py`: điểm khởi động của FastAPI.
- `backend/database.py`: cấu hình kết nối database và khai báo `Base`, `engine`, `SessionLocal`.
- `backend/models/`: định nghĩa các bảng dữ liệu bằng SQLAlchemy ORM.
- `backend/schemas/`: định nghĩa schema Pydantic cho dữ liệu vào và dữ liệu ra.
- `backend/api/`: định nghĩa các route REST API.
- `backend/services/`: chứa các service xử lý logic phụ trợ.

Về mặt tổ chức mã nguồn, phần backend đã được tách lớp tương đối rõ ràng. Điều này giúp dễ mở rộng về sau và phù hợp với cách thiết kế dịch vụ backend thông thường.

## 4. Các thành phần đã thực hiện được

### 4.1. Thiết kế cơ sở dữ liệu

Hiện tại hệ thống đang dùng `SQLite` với file dữ liệu nằm ở thư mục gốc dự án:

- `traffic.db`

Kết nối database được định nghĩa trong `backend/database.py`:

- `DATABASE_URL = "sqlite:///./traffic.db"`

Các bảng hiện có trong cơ sở dữ liệu gồm:

- `vehicle_detections`
- `traffic_aggregation`
- `traffic_predictions`
- `cameras`

Qua kiểm tra dữ liệu thực tế trong file `traffic.db`, trạng thái hiện tại là:

- `vehicle_detections`: đã có `80` bản ghi.
- `traffic_aggregation`: chưa có dữ liệu.
- `traffic_predictions`: chưa có dữ liệu.
- `cameras`: chưa có dữ liệu.

Điều này cho thấy backend đã thực sự lưu được dữ liệu từ khối detection, nhưng mới tập trung ở bảng sự kiện gốc là `vehicle_detections`.

### 4.2. Schema và model dữ liệu

Model quan trọng nhất hiện nay là `VehicleDetection`, dùng để lưu sự kiện mà module detection gửi lên. Bảng này hiện đang lưu các trường:

- `id`
- `event_id`
- `camera_id`
- `track_id`
- `vehicle_type`
- `density`
- `event_type`
- `confidence`
- `timestamp`

Ngoài ra backend còn có các model:

- `TrafficAggregation`
- `TrafficPrediction`
- `Camera`

Tuy nhiên ba model này hiện mới chỉ tồn tại ở mức cấu trúc ORM, chưa có luồng xử lý đầy đủ để đổ dữ liệu thật vào.

### 4.3. REST API

Backend hiện đã có các API đúng với phần lớn yêu cầu được giao:

- `POST /detection`
- `GET /aggregation`
- `GET /raw-data`

Ý nghĩa từng API như sau:

- `POST /detection`: nhận dữ liệu sự kiện từ khối detection và lưu vào database.
- `GET /raw-data`: trả về toàn bộ dữ liệu thô từ bảng `vehicle_detections`.
- `GET /aggregation`: nhận tham số `vehicle_count` và trả về mức độ ùn tắc theo quy tắc đã định sẵn.

Ngoài ra còn có thêm:

- `GET /predict-next`

API này cho thấy định hướng mở rộng sang bài toán dự báo, nhưng hiện vẫn chỉ là endpoint mẫu.

### 4.4. Data validation

Phần kiểm tra dữ liệu đầu vào đã được triển khai thông qua Pydantic trong `backend/schemas/detection_schema.py`.

Schema `DetectionCreate` hiện kiểm tra:

- `event_id: str`
- `camera_id: str`
- `track_id: Union[int, str]`
- `vehicle_type: str`
- `density: str`
- `event_type: str`
- `timestamp: datetime`
- `confidence: Optional[float]`

Nhờ đó, backend đã đảm bảo được việc:

- kiểm tra kiểu dữ liệu đầu vào,
- chặn các request sai định dạng cơ bản,
- ép dữ liệu vào đúng cấu trúc trước khi lưu xuống database.

Tuy nhiên phần validation hiện vẫn mới ở mức cơ bản, chưa có ràng buộc mạnh hơn như:

- kiểm tra chuỗi rỗng,
- kiểm tra giá trị hợp lệ của `vehicle_type`,
- kiểm tra giá trị hợp lệ của `density`,
- kiểm tra `confidence` nằm trong khoảng hợp lệ.

### 4.5. Aggregation service

Phần tổng hợp hiện được triển khai ở mức đơn giản trong `backend/services/aggregation_service.py`.

Logic hiện tại:

- `< 10` xe: `Low`
- `< 30` xe: `Medium`
- `< 60` xe: `High`
- `>= 60` xe: `Severe`

Như vậy backend đã có khối `aggregation service`, nhưng mới dừng ở mức hàm quy tắc, chưa thực hiện tổng hợp dữ liệu trực tiếp từ database theo mốc thời gian 1 phút hoặc 5 phút như yêu cầu ban đầu.

### 4.6. Kết nối giữa các phần

Luồng kết nối hiện tại của Module B với toàn hệ thống được triển khai như sau:

1. Khối `detection` đọc video và nhận diện phương tiện.
2. Khi xe đi vào vùng quan tâm, `EventGenerator` tạo một event.
3. `EventPublisher` gửi event bằng HTTP `POST` đến endpoint `/detection`.
4. Backend nhận request qua `detection_routes.py`.
5. Dữ liệu được kiểm tra bằng schema Pydantic `DetectionCreate`.
6. Sau khi hợp lệ, dữ liệu được ánh xạ sang model `VehicleDetection`.
7. SQLAlchemy dùng session từ `SessionLocal` để ghi dữ liệu vào `traffic.db`.
8. Dữ liệu đã lưu có thể được đọc lại bằng `GET /raw-data`.

Đây là phần kết nối đã chạy thực tế và là luồng hoàn chỉnh nhất của Module B ở thời điểm hiện tại.

## 5. Module B đã thực hiện đến đâu so với yêu cầu

Nếu đối chiếu với yêu cầu công việc ban đầu, có thể đánh giá như sau:

### 5.1. B1. Thiết kế Database

Đã làm được:

- Đã có các bảng dữ liệu chính bằng SQLAlchemy ORM.
- Đã có cơ chế tự tạo bảng khi backend khởi động.
- Đã có schema cho dữ liệu detection.
- Đã có file database thực tế và dữ liệu thực trong bảng `vehicle_detections`.

Chưa hoàn thành:

- Chưa chuẩn hóa quan hệ khóa ngoại giữa các bảng.
- Chưa thiết kế index rõ ràng cho các cột quan trọng như `timestamp`, `camera_id`, `vehicle_type`.
- Bảng `cameras`, `traffic_aggregation`, `traffic_predictions` chưa được dùng thực tế trong pipeline.

### 5.2. B2. Xây dựng REST API

Đã làm được:

- Đã dùng `FastAPI`.
- Đã có đầy đủ các route cơ bản theo yêu cầu: `POST /detection`, `GET /aggregation`, `GET /raw-data`.

Chưa hoàn thành:

- API `aggregation` chưa lấy dữ liệu thật từ DB.
- Chưa có API lọc theo khoảng thời gian.
- Chưa có API thống kê theo camera hoặc theo loại xe.

### 5.3. B3. Data Validation

Đã làm được:

- Đã dùng Pydantic schema.
- Đã kiểm tra kiểu dữ liệu cơ bản.
- Đã hỗ trợ parse `timestamp` theo kiểu thời gian.

Chưa hoàn thành:

- Chưa kiểm tra null hoặc chuỗi rỗng một cách chặt chẽ.
- Chưa kiểm tra tính hợp lệ nghiệp vụ của từng trường.
- Chưa có custom validator cho các trường quan trọng.

### 5.4. B4. Aggregation Service

Đã làm được:

- Đã có service tính `congestion_level` theo số xe.

Chưa hoàn thành:

- Chưa tổng hợp theo mốc 1 phút.
- Chưa tổng hợp theo mốc 5 phút.
- Chưa ghi kết quả tổng hợp vào bảng `traffic_aggregation`.
- Chưa dùng dữ liệu thực từ `vehicle_detections` để sinh thống kê.

### 5.5. B5. Logging & Error Handling

Đã làm được:

- Có xử lý lỗi cơ bản ở phía detection khi gửi dữ liệu thất bại.

Chưa hoàn thành:

- Chưa có log file riêng cho backend.
- Chưa có middleware hoặc exception handler chuẩn của FastAPI.
- Chưa có logging mức `info`, `warning`, `error` rõ ràng cho từng route.
- Chưa có cơ chế truy vết lỗi và giám sát hệ thống ở mức đầy đủ.

## 6. Dữ liệu hiện đang lưu ở đâu

Dữ liệu hiện tại đang được lưu trong file:

- `traffic.db`

Đây là cơ sở dữ liệu `SQLite`, phù hợp cho giai đoạn phát triển, demo và kiểm thử cục bộ. Trong đó:

- Dữ liệu phát hiện thực tế đang nằm chủ yếu trong bảng `vehicle_detections`.
- Các bảng `traffic_aggregation`, `traffic_predictions`, `cameras` hiện chưa có dữ liệu.

Điều này cho thấy hệ thống đã có dữ liệu thật, nhưng mới tập trung vào lớp dữ liệu gốc, chưa phát triển đầy đủ phần dữ liệu tổng hợp và dữ liệu phục vụ phân tích nâng cao.

## 7. Tiến trình thực hiện Module B

Để xây dựng được Module B ở trạng thái hiện tại, quá trình thực hiện có thể được mô tả theo từng bước như sau:

### Bước 1. Xác định vai trò của backend trong toàn hệ thống

Trước tiên, cần xác định rõ backend không phải là nơi xử lý nhận diện hình ảnh, mà là nơi tiếp nhận dữ liệu từ khối detection, kiểm tra dữ liệu, lưu trữ dữ liệu và cung cấp API cho việc truy vấn, thống kê hoặc mở rộng về sau. Việc xác định đúng vai trò này giúp tách biệt rõ trách nhiệm giữa hai khối:

- Khối `detection`: xử lý video và sinh event.
- Khối `backend`: tiếp nhận event và quản lý dữ liệu.

Đây là bước quan trọng vì nó quyết định cấu trúc tổng thể của module và cách tổ chức mã nguồn.

### Bước 2. Lựa chọn công nghệ triển khai

Sau khi xác định vai trò của backend, bước tiếp theo là chọn công nghệ phù hợp. Trong dự án này, nhóm sử dụng:

- `FastAPI` để xây dựng REST API.
- `SQLAlchemy` để quản lý truy cập cơ sở dữ liệu theo kiểu ORM.
- `SQLite` để lưu trữ dữ liệu ở giai đoạn phát triển.
- `Pydantic` để kiểm tra dữ liệu đầu vào.

Việc lựa chọn bộ công nghệ này là hợp lý vì:

- dễ triển khai,
- phù hợp với dự án học thuật,
- hỗ trợ tốt cho việc xây dựng API nhanh,
- dễ kết nối với Python và pipeline AI hiện có.

### Bước 3. Tạo cấu trúc thư mục backend

Sau khi chốt công nghệ, module backend được tổ chức thành các thành phần riêng:

- `api/` để chứa các route.
- `models/` để chứa các bảng dữ liệu.
- `schemas/` để chứa các Pydantic schema.
- `services/` để chứa logic phụ trợ.
- `database.py` để cấu hình kết nối dữ liệu.
- `main.py` để khởi động ứng dụng FastAPI.

Việc tách như vậy giúp mã nguồn rõ ràng hơn, dễ đọc hơn và thuận lợi cho việc phát triển tiếp về sau.

### Bước 4. Thiết kế cơ sở dữ liệu ban đầu

Sau khi có cấu trúc thư mục, bước tiếp theo là thiết kế dữ liệu cần lưu. Vì đầu vào của backend là các event sinh ra từ detection, nhóm trước tiên xây dựng bảng `vehicle_detections` để lưu dữ liệu phát hiện.

Các trường chính được lưu bao gồm:

- mã sự kiện,
- mã camera,
- mã track,
- loại phương tiện,
- mức mật độ,
- loại sự kiện,
- độ tin cậy,
- thời gian ghi nhận.

Ngoài bảng chính này, hệ thống còn tạo thêm các model:

- `TrafficAggregation`
- `TrafficPrediction`
- `Camera`

Việc tạo trước các model này cho thấy định hướng mở rộng ngay từ đầu, dù ở thời điểm hiện tại các bảng này chưa được sử dụng đầy đủ.

### Bước 5. Cấu hình kết nối database và session làm việc

Tiếp theo, trong `backend/database.py`, hệ thống cấu hình:

- `engine`
- `SessionLocal`
- `Base`

Mục đích của bước này là tạo nền tảng chung để toàn bộ backend có thể dùng chung kết nối database. Đồng thời, một hàm đồng bộ schema cũng được bổ sung để hỗ trợ thêm cột mới cho bảng `vehicle_detections` nếu cấu trúc bảng thay đổi trong quá trình phát triển.

Điều này phản ánh quá trình thực hiện thực tế: schema dữ liệu không phải ngay từ đầu đã cố định hoàn toàn, mà có sự điều chỉnh dần khi pipeline detection rõ hơn.

### Bước 6. Xây dựng model ORM

Sau khi có cấu hình database, các bảng được ánh xạ thành model SQLAlchemy trong thư mục `models/`. Trong đó:

- `VehicleDetection` là model quan trọng nhất và đang được dùng thực tế.
- `TrafficAggregation` và `TrafficPrediction` mới dừng ở mức khai báo cấu trúc.
- `Camera` được tạo ra để phục vụ khả năng mở rộng nhiều camera.

Bước này giúp backend làm việc với dữ liệu ở mức đối tượng thay vì viết truy vấn SQL thủ công ngay từ đầu.

### Bước 7. Xây dựng schema kiểm tra dữ liệu đầu vào

Khi đã có model lưu trữ, bước tiếp theo là tạo schema nhận dữ liệu từ phía detection. Trong `backend/schemas/detection_schema.py`, schema `DetectionCreate` được xây dựng để xác định các trường bắt buộc và kiểu dữ liệu tương ứng.

Mục tiêu của bước này là:

- đảm bảo dữ liệu gửi sang backend đúng định dạng,
- tránh ghi dữ liệu sai cấu trúc vào database,
- chuẩn hóa dữ liệu đầu vào trước khi xử lý.

Đây là bước rất quan trọng vì backend nhận dữ liệu từ một module khác, nên nếu không có validation thì rất dễ phát sinh lỗi khó kiểm soát.

### Bước 8. Xây dựng API nhận dữ liệu từ detection

Sau khi có model và schema, backend triển khai route `POST /detection`. Đây là API cốt lõi của Module B.

Quy trình của API này gồm:

1. Nhận request JSON từ detection.
2. Dùng Pydantic để kiểm tra dữ liệu đầu vào.
3. Tạo đối tượng `VehicleDetection`.
4. Thêm bản ghi vào session.
5. Commit xuống database.
6. Trả lại phản hồi xác nhận đã lưu thành công.

Đây là bước đánh dấu việc backend bắt đầu kết nối thực sự với module detection.

### Bước 9. Kết nối detection với backend qua HTTP

Sau khi API nhận dữ liệu đã sẵn sàng, phía detection được cấu hình để gửi event về backend qua địa chỉ:

- `http://127.0.0.1:8000/detection`

Trong quá trình chạy hệ thống:

- detection sinh event,
- `EventPublisher` gửi request POST,
- backend tiếp nhận và lưu dữ liệu.

Việc kết nối này là bước xác nhận backend không còn là phần độc lập, mà đã trở thành một thành phần hoạt động trong pipeline chung của toàn dự án.

### Bước 10. Bổ sung API truy vấn dữ liệu thô

Sau khi lưu được dữ liệu, bước tiếp theo là xây dựng API `GET /raw-data` để đọc lại các bản ghi đã có trong bảng `vehicle_detections`.

Mục tiêu của bước này là:

- kiểm tra xem dữ liệu đã thực sự được lưu chưa,
- hỗ trợ debug hệ thống,
- phục vụ trình bày kết quả và khai thác dữ liệu bước đầu.

Đây là API đơn giản nhưng cần thiết, vì nếu không có nó thì rất khó xác minh backend đã hoạt động đúng hay chưa.

### Bước 11. Xây dựng service tổng hợp mức ùn tắc cơ bản

Sau khi có lớp dữ liệu thô, nhóm tiếp tục xây dựng một service tổng hợp đơn giản trong `aggregation_service.py`. Service này chưa đọc từ database, mà nhận trực tiếp một giá trị `vehicle_count` rồi phân loại mức ùn tắc.

Từ đó route `GET /aggregation` được xây dựng để minh họa khả năng xử lý nghiệp vụ ở backend.

Bước này cho thấy backend đã bắt đầu chuyển từ vai trò “chỉ lưu dữ liệu” sang “có xử lý dữ liệu”, dù hiện tại mức xử lý vẫn còn đơn giản.

### Bước 12. Chuẩn bị khung cho phần dự báo

Tiếp theo, backend được mở rộng thêm:

- model `TrafficPrediction`,
- schema `PredictionResponse`,
- route `GET /predict-next`

Tuy phần này hiện vẫn chỉ trả về giá trị mẫu, nhưng đây là bước chuẩn bị kiến trúc cho khả năng mở rộng sang dự báo mật độ giao thông trong tương lai.

### Bước 13. Kiểm tra dữ liệu thực tế trong database

Sau khi hoàn thành các thành phần chính, hệ thống đã được chạy thử cùng với module detection. Kết quả là file `traffic.db` đã có dữ liệu thực trong bảng `vehicle_detections`.

Ở thời điểm kiểm tra hiện tại:

- bảng `vehicle_detections` đã có 80 bản ghi,
- các bảng tổng hợp và dự báo vẫn chưa có dữ liệu.

Điều này cho thấy tiến trình thực hiện Module B đã đi được đến giai đoạn “nhận được dữ liệu thật và lưu được dữ liệu thật”.

### Bước 14. Đánh giá và nhận diện phần còn thiếu

Sau khi có một backend hoạt động được, bước tiếp theo là đánh giá những phần còn thiếu so với yêu cầu ban đầu. Qua đối chiếu với mục tiêu Module B, nhóm nhận ra một số phần vẫn chưa hoàn thiện:

- chưa có aggregation theo 1 phút và 5 phút,
- chưa có index và khóa ngoại rõ ràng,
- chưa có logging file và exception handling chuẩn,
- chưa có validation nâng cao,
- chưa có dữ liệu thật cho bảng aggregation và prediction.

Đây là bước cần thiết để xác định phần nào đã hoàn thành, phần nào mới dừng ở mức nền tảng và phần nào cần tiếp tục phát triển.

## 8. Khó khăn trong quá trình thực hiện Module B

Trong quá trình xây dựng Module B, có thể nhận thấy một số khó khăn chính như sau:

### 7.1. Đồng bộ giữa detection và backend

Khó khăn lớn nhất là đảm bảo dữ liệu từ khối detection gửi sang đúng định dạng mà backend mong đợi. Khi pipeline detection thay đổi trường dữ liệu, backend cũng phải cập nhật schema và model tương ứng. Nếu không đồng bộ, request rất dễ lỗi hoặc dữ liệu lưu xuống sẽ không chính xác.

### 7.2. Thiết kế schema ngay từ đầu chưa thật sự ổn định

Hiện tại có dấu hiệu cho thấy bảng `vehicle_detections` đã được bổ sung thêm cột bằng cách đồng bộ thủ công trong `sync_vehicle_detection_schema()`. Điều này cho thấy thiết kế ban đầu có thay đổi trong quá trình phát triển. Khi schema thay đổi liên tục, việc quản lý database sẽ khó hơn, đặc biệt nếu sau này chuyển sang hệ thống lớn hơn.

### 7.3. Khó khăn trong việc xây dựng aggregation đúng nghĩa

Phần tổng hợp dữ liệu theo thời gian không chỉ là đếm số bản ghi, mà cần xác định rõ đơn vị tổng hợp, mốc thời gian, cách xử lý trùng lặp, cách phân loại mức ùn tắc và cấu trúc dữ liệu đầu ra. Đây là phần khó hơn so với việc chỉ lưu từng event riêng lẻ.

### 7.4. Logging và xử lý lỗi chưa được ưu tiên ngay từ đầu

Trong giai đoạn đầu, nhóm tập trung nhiều vào việc làm cho pipeline chạy được từ detection đến database, nên logging và error handling mới dừng ở mức cơ bản. Đây là điều thường gặp trong giai đoạn prototype, nhưng sẽ trở thành hạn chế nếu tiếp tục mở rộng hệ thống.

## 9. Có hướng giải quyết nào tối ưu hơn không

Có. Nếu tiếp tục phát triển Module B, có thể tối ưu theo các hướng sau:

### 8.1. Tối ưu thiết kế database

- Chuẩn hóa lại schema theo hướng rõ quan hệ hơn.
- Thêm khóa ngoại, ví dụ liên kết `vehicle_detections.camera_id` với bảng `cameras`.
- Thêm index cho các cột truy vấn nhiều như `timestamp`, `camera_id`, `vehicle_type`.
- Tách dữ liệu gốc và dữ liệu tổng hợp thành hai lớp rõ ràng.

### 8.2. Tối ưu aggregation service

- Viết service tổng hợp trực tiếp từ bảng `vehicle_detections`.
- Tạo thống kê theo từng cửa sổ thời gian 1 phút và 5 phút.
- Lưu kết quả tổng hợp vào bảng `traffic_aggregation`.
- Dùng `Pandas` hoặc truy vấn SQLAlchemy nhóm theo mốc thời gian để tính toán linh hoạt hơn.

### 8.3. Tối ưu validation

- Bổ sung validator cho `vehicle_type`, `density`, `confidence`.
- Kiểm tra chuỗi rỗng và dữ liệu bất thường.
- Chuẩn hóa enum cho các trường mang tính phân loại.

### 8.4. Tối ưu logging và error handling

- Dùng module `logging` hoặc `loguru` để ghi log file riêng.
- Tạo exception handler chung cho FastAPI.
- Log cả request vào, response lỗi và thời gian xử lý.
- Phân loại lỗi database, lỗi validation, lỗi nghiệp vụ để dễ debug.

### 8.5. Tối ưu kiến trúc triển khai

- Với giai đoạn học tập, tiếp tục dùng SQLite là hợp lý.
- Nếu muốn mở rộng thật, nên chuyển sang PostgreSQL.
- Có thể tách backend thành các lớp rõ hơn: `router -> service -> repository`.
- Nếu dữ liệu từ detection nhiều hơn, có thể dùng message queue thay cho gửi trực tiếp bằng HTTP để tránh mất dữ liệu khi backend tạm thời không sẵn sàng.

## 10. Đánh giá tổng kết

Module B hiện đã hoàn thành được phần quan trọng nhất là tiếp nhận dữ liệu từ khối detection, kiểm tra dữ liệu đầu vào, lưu dữ liệu vào database và cung cấp API truy vấn cơ bản. Đây là nền tảng quan trọng để toàn bộ hệ thống có thể hoạt động xuyên suốt từ video đầu vào cho đến lưu trữ dữ liệu.

Tuy nhiên, nếu so với yêu cầu đầy đủ của một `Data Pipeline & API Service`, phần backend hiện vẫn đang ở mức nền tảng ban đầu. Những phần như chuẩn hóa schema sâu hơn, thiết kế index, khóa ngoại, aggregation theo 1 phút và 5 phút, logging file, exception handling chuẩn và khai thác dữ liệu tổng hợp vẫn chưa hoàn thiện.

Có thể kết luận rằng Module B đã hoàn thành tốt phần lưu trữ dữ liệu gốc và API cơ bản, nhưng vẫn cần phát triển thêm để đạt đúng mục tiêu của một dịch vụ backend hoàn chỉnh cho hệ thống phân tích giao thông.
