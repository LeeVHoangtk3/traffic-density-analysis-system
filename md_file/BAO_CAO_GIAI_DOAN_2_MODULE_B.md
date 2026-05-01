# BÁO CÁO TIẾN ĐỘ THỰC HIỆN GIAI ĐOẠN 2

## 1. Tên giai đoạn

**Giai đoạn 2: Quản lý và Tổng hợp dữ liệu (Data & Orchestration Layer - Module B)**

Giai đoạn này tập trung vào việc xây dựng lớp trung gian giữa khối nhận diện giao thông và khối phân tích dữ liệu. Nói đơn giản, đây là phần giúp hệ thống nhận dữ liệu từ module phát hiện xe, kiểm tra dữ liệu đó có hợp lệ hay không, lưu lại vào cơ sở dữ liệu và chuẩn bị dữ liệu ở dạng phù hợp để phục vụ thống kê hoặc học máy về sau.

## 2. Mục tiêu của giai đoạn

Mục tiêu chính của Giai đoạn 2 là bảo đảm dữ liệu giao thông luôn ở trạng thái sẵn sàng cho việc khai thác. Cụ thể, phần này hướng đến 3 nhiệm vụ quan trọng:

- Xây dựng giao thức truyền tải dữ liệu giữa Module A và backend thông qua RESTful API.
- Thiết kế cơ sở dữ liệu để lưu trữ dữ liệu đếm xe theo cách có tổ chức, dễ truy vấn.
- Tạo nền tảng cho dịch vụ tổng hợp dữ liệu theo các khung thời gian, nhằm giảm nhiễu và chuẩn hóa dữ liệu chuỗi thời gian.

## 3. Nội dung đã thực hiện

### 3.1. Xây dựng giao thức truyền tải bằng FastAPI

Ở bước đầu tiên, hệ thống backend đã được xây dựng bằng `FastAPI`. Đây là framework phù hợp vì có tốc độ xử lý tốt, dễ xây dựng API và rất thuận tiện khi làm việc với dữ liệu JSON.

Hiện tại, backend đã có endpoint:

- `POST /detection`: dùng để nhận dữ liệu sự kiện từ Module A gửi lên.

Luồng hoạt động đang được triển khai như sau:

1. Module A phát hiện phương tiện và tạo event.
2. Event được gửi lên server bằng phương thức `POST`.
3. Backend nhận dữ liệu qua API.
4. Dữ liệu được kiểm tra định dạng trước khi lưu.
5. Sau khi hợp lệ, dữ liệu được ghi vào cơ sở dữ liệu.

Kết quả đạt được ở bước này là hệ thống đã hình thành được kênh giao tiếp ổn định giữa khối nhận diện và khối lưu trữ. Đây là nền tảng rất quan trọng, vì nếu không có bước này thì toàn bộ dữ liệu nhận diện chỉ tồn tại tạm thời trong lúc chạy chương trình mà không thể phục vụ cho các bước phân tích sau.

### 3.2. Kiểm tra và chuẩn hóa dữ liệu đầu vào

Sau khi xây dựng API nhận dữ liệu, phần tiếp theo đã được thực hiện là kiểm tra dữ liệu đầu vào bằng `Pydantic`. Backend hiện đã có schema để xác định các trường quan trọng như:

- `event_id`
- `camera_id`
- `track_id`
- `vehicle_type`
- `density`
- `event_type`
- `confidence`
- `timestamp`

Việc sử dụng schema giúp hệ thống tránh được tình trạng lưu dữ liệu sai định dạng hoặc thiếu trường quan trọng. Nhờ đó, dữ liệu đưa vào cơ sở dữ liệu có tính nhất quán cao hơn và giảm lỗi trong các bước xử lý sau.

Có thể xem đây là bước làm sạch dữ liệu ở mức đầu vào. Dù hiện tại việc kiểm tra vẫn đang ở mức cơ bản, nhưng nó đã tạo được nền tảng tốt để mở rộng thành cơ chế validation chặt chẽ hơn trong tương lai.

### 3.3. Thiết kế cơ sở dữ liệu lưu trữ dữ liệu giao thông

Về mặt lưu trữ, hệ thống đã sử dụng `SQLite` làm cơ sở dữ liệu ở giai đoạn hiện tại. Đây là lựa chọn phù hợp cho quá trình phát triển và thử nghiệm vì dễ triển khai, không yêu cầu cấu hình phức tạp và có thể tích hợp trực tiếp vào dự án.

Phần backend đã xây dựng cấu trúc cơ sở dữ liệu thông qua `SQLAlchemy ORM`. Một số bảng đã được khai báo gồm:

- `vehicle_detections`
- `traffic_aggregation`
- `traffic_predictions`
- `cameras`

Trong đó, bảng đang được sử dụng thực tế rõ nhất là `vehicle_detections`. Đây là nơi lưu các bản ghi gốc do Module A gửi lên. Việc có bảng dữ liệu thô riêng là rất cần thiết vì nó đóng vai trò là nguồn dữ liệu đầu vào cho các bước tổng hợp sau này.

Ngoài ra, hệ thống cũng đã có cơ chế tự tạo bảng khi backend khởi động. Điều này giúp giảm thao tác thủ công trong quá trình phát triển và bảo đảm backend có thể chạy nhanh trong môi trường demo.

### 3.4. Tổ chức lớp truy cập dữ liệu

Một điểm tích cực trong tiến trình thực hiện là phần backend không chỉ dừng ở việc có database, mà còn đã tách các thành phần khá rõ ràng:

- `models/` để định nghĩa bảng dữ liệu
- `schemas/` để định nghĩa cấu trúc dữ liệu vào/ra
- `api/` để xây dựng các route
- `services/` để đặt các xử lý nghiệp vụ hỗ trợ
- `database.py` để cấu hình kết nối và session

Cách tổ chức này cho thấy Giai đoạn 2 đã được triển khai theo hướng có cấu trúc, không làm theo kiểu gom toàn bộ logic vào một file duy nhất. Đây là lợi thế lớn cho việc mở rộng về sau, đặc biệt khi cần bổ sung thống kê theo thời gian, theo camera hoặc tích hợp mô hình dự báo.

### 3.5. Xây dựng nền tảng cho dịch vụ tổng hợp dữ liệu

Đối với yêu cầu tổng hợp dữ liệu, hệ thống hiện đã có phần khung ban đầu thông qua `aggregation_service.py` và route:

- `GET /aggregation`

Chức năng hiện tại của phần này là nhận số lượng xe và phân loại mức độ ùn tắc theo các mức:

- `Low`
- `Medium`
- `High`
- `Severe`

Mặc dù đây mới chỉ là bước tổng hợp ở mức đơn giản, nhưng nó thể hiện rằng hệ thống đã bắt đầu chuyển từ giai đoạn "chỉ lưu dữ liệu" sang giai đoạn "xử lý và diễn giải dữ liệu". Đây là bước chuyển quan trọng về mặt kiến trúc, vì mục tiêu cuối cùng của Module B không chỉ là nhận dữ liệu, mà còn phải biến dữ liệu thô thành dữ liệu có ý nghĩa phân tích.

## 4. Tiến độ thực hiện theo từng hạng mục

Nếu đối chiếu với mục tiêu ban đầu của Giai đoạn 2, tiến độ hiện tại có thể mô tả như sau:

### 4.1. Hạng mục giao thức truyền tải

Đã hoàn thành ở mức tốt.

- Đã xây dựng backend bằng `FastAPI`.
- Đã có API nhận dữ liệu từ Module A bằng phương thức `POST`.
- Đã hình thành luồng truyền dữ liệu từ khối detection sang server.

### 4.2. Hạng mục lưu trữ dữ liệu

Đã hoàn thành phần nền tảng.

- Đã cấu hình cơ sở dữ liệu `SQLite`.
- Đã xây dựng model ORM cho các bảng chính.
- Đã lưu được dữ liệu thực vào bảng `vehicle_detections`.
- Đã có cấu trúc để mở rộng sang bảng tổng hợp và bảng dự báo.

Tuy nhiên, phần tối ưu hóa truy vấn theo `timestamp` hiện mới dừng ở định hướng thiết kế. Hệ thống đã nhận thức rõ vai trò của dữ liệu thời gian, nhưng chưa triển khai đầy đủ cơ chế index rõ ràng cho truy vấn lịch sử ở quy mô lớn.

### 4.3. Hạng mục dịch vụ tổng hợp dữ liệu

Đã hoàn thành ở mức khởi tạo.

- Đã có service tổng hợp cơ bản.
- Đã có logic phân loại mức ùn tắc theo số lượng xe.
- Đã có route riêng để phục vụ chức năng tổng hợp.

Tuy vậy, phần tổng hợp theo cửa sổ thời gian như `15 phút`, `5 phút` hoặc `1 phút` vẫn đang ở giai đoạn chuẩn bị. Điều này có nghĩa là hệ thống đã có khung xử lý, nhưng chưa hoàn thiện bước group by dữ liệu thực từ database để tạo chuỗi thời gian chuẩn cho Machine Learning.

## 5. Đánh giá tiến trình thực hiện

Nhìn chung, Giai đoạn 2 đã hoàn thành được phần quan trọng nhất là tạo ra một pipeline backend có thể hoạt động thật. Thay vì chỉ dừng ở ý tưởng, hệ thống hiện đã:

- Nhận được dữ liệu từ module phát hiện xe
- Kiểm tra được dữ liệu đầu vào
- Lưu được dữ liệu vào cơ sở dữ liệu
- Có nền tảng để tổng hợp và mở rộng thống kê

Điểm mạnh của tiến trình hiện tại là nhóm đã đi đúng thứ tự kỹ thuật. Trước hết là làm cho luồng dữ liệu chạy được, sau đó mới mở rộng dần sang tối ưu hóa và tổng hợp. Cách triển khai này hợp lý vì giúp hệ thống có nền móng rõ ràng trước khi phát triển thêm các chức năng phức tạp hơn.

Ngoài ra, cấu trúc mã nguồn backend cũng đã thể hiện tư duy tổ chức tốt. Điều này giúp cho Giai đoạn 2 không chỉ giải quyết nhu cầu trước mắt là lưu dữ liệu, mà còn tạo ra nền tảng tương đối thuận lợi cho các giai đoạn tiếp theo như thống kê theo thời gian, dự báo lưu lượng và xây dựng dashboard.

## 6. Những phần đang tiếp tục hoàn thiện

Mặc dù đã đạt được nhiều kết quả tích cực, Giai đoạn 2 hiện vẫn còn một số nội dung cần triển khai tiếp để đạt đúng mục tiêu đầy đủ:

- Bổ sung index theo cột `timestamp` để tăng tốc độ truy vấn dữ liệu lịch sử.
- Hoàn thiện dịch vụ tổng hợp dữ liệu trực tiếp từ bảng `vehicle_detections`.
- Thực hiện gom nhóm dữ liệu theo các khung thời gian như `1 phút`, `5 phút`, `15 phút`.
- Lưu kết quả tổng hợp vào bảng `traffic_aggregation`.
- Chuẩn hóa đầu ra theo dạng time series để phục vụ tốt hơn cho các mô hình học máy hoặc dự báo.

Như vậy, có thể nói phần "Data Management" đã đi được khá vững, còn phần "Aggregation" đang ở giai đoạn từ nền tảng chuyển sang hoàn thiện nghiệp vụ.

## 7. Kết luận

Giai đoạn 2 của dự án đã đạt được tiến triển rõ ràng và có giá trị thực tế. Nhóm đã xây dựng được backend bằng `FastAPI`, thiết lập được luồng nhận dữ liệu từ Module A, tổ chức lưu trữ bằng cơ sở dữ liệu và đặt nền móng cho dịch vụ tổng hợp dữ liệu. Đây là bước rất quan trọng vì nó biến dữ liệu phát hiện xe từ dạng rời rạc thành tài nguyên có thể quản lý và khai thác.

Tại thời điểm hiện tại, có thể đánh giá rằng Giai đoạn 2 đã hoàn thành tốt phần hạ tầng dữ liệu và đang chuyển sang giai đoạn hoàn thiện phần tổng hợp theo thời gian. Nếu tiếp tục bổ sung cơ chế index, group by theo khung thời gian và lưu dữ liệu tổng hợp đúng chuẩn, Module B sẽ trở thành lớp dữ liệu trung tâm đủ mạnh để phục vụ cho phân tích và dự báo giao thông trong các bước tiếp theo của dự án.
