# BÁO CÁO HIỆN TRẠNG DỰ ÁN: TRAFFIC DENSITY ANALYSIS SYSTEM

## 1. Tổng quan dự án

Dự án `Traffic Density Analysis System` được xây dựng với mục tiêu tạo ra một hệ thống phân tích mật độ giao thông dựa trên video. Ý tưởng chính là sử dụng mô hình nhận diện đối tượng để phát hiện các phương tiện giao thông trong từng khung hình, sau đó dùng thuật toán theo dõi đối tượng để gán ID cho từng xe và theo dõi chuyển động của chúng theo thời gian. Khi xe đi vào vùng quan tâm đã được cấu hình trước, hệ thống sẽ ghi nhận sự kiện, đếm xe, ước lượng mật độ giao thông và gửi dữ liệu sang backend để lưu trữ.

Ở thời điểm hiện tại, dự án đã hình thành được một pipeline tương đối hoàn chỉnh cho bài toán demo và nghiên cứu, bao gồm:

- Một khối xử lý video và nhận diện phương tiện.
- Một khối backend để nhận dữ liệu và lưu vào cơ sở dữ liệu.
- Một nhánh dataset và mã nguồn huấn luyện YOLOv9 phục vụ cho việc fine-tune mô hình.
- Một notebook hỗ trợ chạy thử toàn bộ hệ thống trong môi trường phát triển.

Tuy nhiên, nếu đánh giá ở góc độ một hệ thống hoàn chỉnh để triển khai thực tế, dự án vẫn đang ở giai đoạn nguyên mẫu chức năng. Một số phần cốt lõi đã chạy được, nhưng vẫn còn nhiều thành phần mới dừng ở mức mô phỏng, hard-code hoặc chưa tích hợp đầy đủ.

## 2. Lý do chọn đề tài

Trong bối cảnh quá trình đô thị hóa diễn ra ngày càng mạnh mẽ, bài toán giao thông đang trở thành một trong những vấn đề nổi bật tại các thành phố lớn. Tình trạng ùn tắc thường xuyên xuất hiện tại các nút giao thông trọng điểm, đặc biệt vào các khung giờ cao điểm, gây ảnh hưởng đáng kể đến thời gian di chuyển, hiệu quả lưu thông và chất lượng đời sống đô thị. Trước thực tế đó, việc ứng dụng công nghệ để theo dõi, phân tích và hỗ trợ đánh giá tình trạng giao thông là một hướng tiếp cận có giá trị thực tiễn cao. Đây cũng là lý do quan trọng khiến nhóm lựa chọn đề tài xây dựng hệ thống phân tích mật độ giao thông dựa trên video.

Bên cạnh tính ứng dụng thực tế, đề tài còn có ý nghĩa rõ rệt về mặt học thuật và nghiên cứu. Đây là một bài toán tổng hợp, đòi hỏi sự kết hợp giữa nhiều lĩnh vực trong công nghệ thông tin như thị giác máy tính, xử lý ảnh, học sâu, theo dõi đối tượng, phát triển backend và quản lý cơ sở dữ liệu. Thông qua việc triển khai đề tài, nhóm có cơ hội tiếp cận một quy trình xây dựng hệ thống AI tương đối đầy đủ, bắt đầu từ dữ liệu đầu vào, mô hình nhận diện, xử lý luồng suy luận, lưu trữ kết quả cho đến khai thác dữ liệu phục vụ phân tích. Vì vậy, đề tài không chỉ mang tính ứng dụng mà còn phù hợp với định hướng học tập và rèn luyện năng lực xây dựng hệ thống thực tế.

Một lý do khác khiến đề tài này được lựa chọn là tính mở rộng cao. Từ chức năng ban đầu là phát hiện và đếm phương tiện, hệ thống có thể tiếp tục phát triển theo nhiều hướng như thống kê lưu lượng xe theo thời gian, phân tích mức độ ùn tắc tại từng khu vực, xây dựng bảng điều khiển giám sát trực quan hoặc tích hợp mô hình dự báo mật độ giao thông. Chính khả năng mở rộng này giúp đề tài không dừng lại ở một bài toán nhận diện đơn lẻ mà có thể trở thành nền tảng cho các ứng dụng thuộc lĩnh vực giao thông thông minh trong tương lai.

Ngoài ra, đề tài còn có ưu điểm là dữ liệu đầu vào trực quan, dễ quan sát và thuận lợi cho việc kiểm chứng kết quả. Kết quả xử lý có thể được thể hiện trực tiếp trên video thông qua bounding box, ID đối tượng, số lượng phương tiện và mức mật độ giao thông. Điều này giúp quá trình đánh giá, so sánh và trình bày kết quả trở nên rõ ràng hơn, đồng thời hỗ trợ tốt cho việc báo cáo, minh họa và bảo vệ đề tài.

Từ những phân tích trên, có thể thấy việc lựa chọn đề tài `Traffic Density Analysis System` xuất phát từ cả nhu cầu thực tiễn lẫn giá trị học thuật. Đây là một đề tài phù hợp để vận dụng kiến thức chuyên môn, phát triển kỹ năng xây dựng hệ thống và hướng tới các ứng dụng có ý nghĩa trong thực tế.

## 3. Dự án đã thực hiện được đến đâu

### 2.1. Phần đã hoàn thiện ở mức chạy được

Dựa trên mã nguồn hiện tại, hệ thống đã làm được các bước quan trọng sau:

- Đọc video đầu vào từ file `traffictrim.mp4` hoặc từ nguồn video được cấu hình qua biến môi trường.
- Tải mô hình YOLOv9 đã huấn luyện để nhận diện 4 lớp phương tiện gồm `bus`, `car`, `motorcycle`, `truck`.
- Thực hiện phát hiện phương tiện trên từng frame sau khi resize ảnh về kích thước phù hợp.
- Áp dụng thuật toán DeepSort để theo dõi đối tượng giữa các frame và gán `track_id`.
- Đếm số lượng phương tiện khi xe đi vào vùng giám sát được xác định trong file cấu hình camera.
- Ước lượng mức độ đông đúc giao thông theo quy tắc ngưỡng đơn giản.
- Tạo sự kiện và gửi sự kiện từ khối detection sang backend bằng HTTP API.
- Backend nhận sự kiện, kiểm tra dữ liệu đầu vào, sau đó lưu vào cơ sở dữ liệu SQLite.
- Cung cấp API để xem dữ liệu thô và một API tổng hợp mức ùn tắc dựa trên số xe truyền vào.
- Có notebook để khởi động backend và detection trong cùng một quy trình demo.

Nói cách khác, phần lõi của dự án, tức là “đọc video -> nhận diện xe -> tracking -> kiểm tra zone -> tạo event -> lưu database”, đã được triển khai và có thể xem là phần đã hoàn thành rõ nhất.

### 2.2. Phần đã làm nhưng mới ở mức cơ bản

Một số thành phần đã có mặt trong dự án nhưng mới chỉ ở mức ban đầu:

- Phần ước lượng mật độ giao thông hiện chỉ dùng luật ngưỡng đơn giản theo số lượng track hiện tại.
- Phần tổng hợp mức ùn tắc ở backend chưa đọc trực tiếp từ dữ liệu database, mà mới nhận tham số `vehicle_count` từ bên ngoài rồi phân loại theo mức `Low`, `Medium`, `High`, `Severe`.
- Phần dự đoán mật độ giao thông tiếp theo đã có endpoint riêng, nhưng hiện tại chỉ trả về giá trị giả lập `0.45`.
- Cơ sở dữ liệu đã có model cho `TrafficAggregation` và `TrafficPrediction`, nhưng thực tế chưa thấy pipeline nào ghi dữ liệu thật vào hai bảng này.
- Dự án có thư mục huấn luyện mô hình và dataset, nhưng chưa thấy một quy trình huấn luyện, đánh giá và triển khai được viết thành tài liệu hoàn chỉnh trong repo.

Vì vậy có thể nói dự án hiện đang mạnh nhất ở phần nhận diện và ghi nhận sự kiện, còn phần phân tích nâng cao và dự báo mới chỉ là khung nền.

## 3. Cấu trúc hiện tại của dự án

Từ mã nguồn, dự án đang được chia thành ba khối lớn:

- `detection/`: xử lý video, nhận diện phương tiện, tracking, kiểm tra zone, sinh event.
- `backend/`: xây dựng API bằng FastAPI, lưu dữ liệu bằng SQLAlchemy và SQLite.
- `yolov9-cus/`: chứa source YOLOv9, dataset train/val/test và cấu hình huấn luyện.

Ngoài ra còn có:

- `traffic.db`: file cơ sở dữ liệu SQLite.
- `traffictrim.mp4`: video đầu vào để thử nghiệm.
- `traffic_density_git_project.ipynb`: notebook hỗ trợ chạy hệ thống.
- `requirements.txt`: danh sách thư viện.

Nhìn chung, cách chia tách thư mục là hợp lý và đủ rõ ràng cho một đề tài môn học hoặc đồ án giai đoạn đầu. Các vai trò của từng phần đã được phân chia tương đối đúng hướng.

## 4. Mô tả chi tiết hiện trạng từng phần

### 4.1. Khối detection

Đây là phần hoàn thiện nhất trong dự án hiện nay.

File `detection/main.py` là nơi điều phối toàn bộ quy trình. Chương trình thực hiện lần lượt các bước:

1. Đọc cấu hình đường dẫn video, model và địa chỉ API backend từ biến môi trường.
2. Đọc file cấu hình zone của camera `CAM_01`.
3. Khởi tạo các module xử lý gồm `CameraEngine`, `FrameProcessor`, `Detector`, `Tracker`, `VehicleCounter`, `DensityEstimator`, `EventGenerator`, `EventPublisher`, `ZoneManager`.
4. Đọc từng frame từ video.
5. Bỏ qua bớt frame để tăng tốc độ xử lý.
6. Resize frame.
7. Chạy nhận diện đối tượng bằng YOLOv9.
8. Chạy tracking bằng DeepSort.
9. Cập nhật mật độ giao thông theo số lượng đối tượng đang được theo dõi.
10. Với mỗi track, tính tâm của bounding box để kiểm tra có đi vào vùng quan tâm hay không.
11. Nếu xe đi vào zone lần đầu, tăng bộ đếm và sinh event.
12. Gửi event lên backend.
13. Vẽ thông tin lên frame nếu bật hiển thị video.

Phần detection có thể xem là đã hoàn thiện tương đối tốt ở mức prototype vì có phân tách module rõ ràng, có thể chạy độc lập, có đầy đủ chuỗi xử lý cơ bản, có tối ưu sơ bộ bằng `FRAME_SKIP` và resize, đồng thời có cơ chế tránh đếm lặp bằng `track_id`.

Tuy nhiên phần này vẫn còn nhiều điểm chưa hoàn chỉnh:

- `event_type` hiện đang gán cố định là `line_crossing`, trong khi logic thực tế là kiểm tra xe đi vào vùng polygon. Phần này chưa đồng nhất về mặt nghiệp vụ.
- `ZoneManager` chỉ đánh dấu một `track_id` đã được đếm hay chưa, nhưng chưa phân biệt xe đi vào zone nào. Nếu sau này cần thống kê theo từng làn hoặc từng vùng, cấu trúc hiện tại chưa đủ.
- `VehicleCounter` có hàm `get_per_minute()`, nhưng hiện chưa được sử dụng trong pipeline chính.
- `DensityEstimator` hiện chỉ dựa vào số lượng track tức thời, chưa xét đến diện tích vùng quan sát, lưu lượng theo thời gian, tốc độ di chuyển hoặc ngữ cảnh giao thông.
- Chưa có bước đánh giá độ chính xác của detection và tracking trên video thực tế trong chính dự án.
- `EventPublisher` mới chỉ in lỗi khi gửi thất bại, chưa có retry, log file, queue tạm hoặc cơ chế gửi lại.
- Chưa thấy xử lý riêng cho trường hợp nguồn video là nhiều camera đồng thời.
- Chưa có hệ thống cấu hình tổng quát hơn cho nhiều camera, nhiều model hoặc nhiều profile chạy khác nhau.

### 4.2. Khối backend

Phần backend đã được dựng khá gọn và rõ, dùng FastAPI cùng SQLAlchemy. Khi khởi động, backend sẽ tạo bảng nếu chưa tồn tại, sau đó nạp các router API.

Các endpoint hiện tại gồm:

- `POST /detection`: nhận event từ detection và lưu vào bảng `vehicle_detections`.
- `GET /raw-data`: trả về toàn bộ dữ liệu phát hiện đã lưu.
- `GET /aggregation`: nhận `vehicle_count` từ query và suy ra mức ùn tắc.
- `GET /predict-next`: trả về giá trị dự đoán mẫu.

Backend đã hoàn thành được phần tiếp nhận dữ liệu và lưu trữ cơ bản:

- Có mô hình dữ liệu cho detection.
- Có schema Pydantic để kiểm tra dữ liệu đầu vào.
- Có session database riêng.
- Có khả năng tạo bảng tự động.
- Có API đọc dữ liệu thô để phục vụ debug hoặc demo.

Tuy nhiên phần backend hiện vẫn còn khá sơ khai nếu so với mục tiêu một hệ thống phân tích giao thông hoàn chỉnh:

- API `aggregation` chưa thực hiện tổng hợp từ dữ liệu thật trong database.
- API `predict-next` chưa dùng mô hình dự báo thật.
- Hai bảng `traffic_aggregation` và `traffic_predictions` mới chỉ tồn tại ở mức model, chưa thấy luồng xử lý nào ghi dữ liệu vào.
- Chưa có API lọc dữ liệu theo thời gian, theo camera, theo loại phương tiện hoặc theo zone.
- Chưa có API thống kê số lượng xe theo phút, theo giờ hoặc theo ngày.
- Chưa có xử lý phân trang hoặc giới hạn dữ liệu khi bảng lớn dần.
- Chưa có authentication, validation nâng cao, logging backend hoặc chuẩn hóa response.
- Chưa có migration chuyên nghiệp, hiện mới dùng cách thêm cột thủ công qua `ALTER TABLE`.

Điều này cho thấy backend hiện phù hợp cho việc minh họa pipeline hơn là phục vụ phân tích dữ liệu ở mức hoàn chỉnh.

### 4.3. Phần huấn luyện mô hình

Repo có chứa đầy đủ dấu hiệu cho thấy dự án đã chuẩn bị dữ liệu và môi trường để huấn luyện mô hình nhận diện riêng cho bài toán giao thông:

- Có thư mục dataset gồm `train`, `val`, `test`.
- Có file `data.yaml` định nghĩa 4 lớp xe.
- Có source YOLOv9 để phục vụ huấn luyện.
- Có trọng số mô hình được dùng cho suy luận.

Theo README dataset, bộ dữ liệu có 2012 ảnh và được gán nhãn theo định dạng YOLOv9.

Có thể kết luận rằng phần dữ liệu và nền tảng huấn luyện đã được chuẩn bị. Mô hình dùng trong phần detection nhiều khả năng là mô hình đã fine-tune từ dữ liệu tùy biến này.

Tuy nhiên, repo hiện vẫn còn thiếu các thành phần quan trọng để phần huấn luyện được xem là hoàn thiện:

- Chưa có báo cáo kết quả huấn luyện như `mAP`, `precision`, `recall`.
- Chưa có tài liệu mô tả cách train, epoch, batch size, learning rate, thời gian huấn luyện.
- Chưa có quy trình rõ ràng từ dataset đến file model cuối cùng.
- Chưa có phần so sánh giữa model gốc và model fine-tune.
- Chưa có đánh giá xem mô hình chạy tốt nhất trong điều kiện nào và sai ở các trường hợp nào.

Nói ngắn gọn, phần huấn luyện hiện đang có dấu vết triển khai, nhưng hồ sơ kỹ thuật của nó chưa đầy đủ để trình bày thành một quy trình chuẩn.

## 5. Những phần còn thiếu so với mục tiêu của một hệ thống hoàn chỉnh

Nếu nhìn theo mục tiêu ban đầu của một hệ thống phân tích mật độ giao thông, dự án vẫn còn thiếu các khối sau:

### 5.1. Thiếu phần tổng hợp dữ liệu thực sự

Hiện tại dự án mới dừng ở việc lưu từng event riêng lẻ. Chưa có logic tổng hợp dữ liệu để trả lời các câu hỏi như:

- Trong 1 phút có bao nhiêu xe đi qua?
- Từng loại xe xuất hiện bao nhiêu?
- Camera nào có mật độ cao nhất?
- Làn đường nào đông nhất?
- Khung giờ nào thường bị ùn tắc?

Đây là phần rất quan trọng nếu muốn gọi dự án là hệ thống phân tích, thay vì chỉ là hệ thống nhận diện và ghi log.

### 5.2. Thiếu phần dự báo giao thông thật

Endpoint dự báo hiện chỉ mang tính minh họa. Nếu muốn hoàn thiện, dự án cần thêm:

- Dữ liệu lịch sử đã được tổng hợp theo chuỗi thời gian.
- Một mô hình dự báo như hồi quy, ARIMA, LSTM hoặc mô hình học máy phù hợp.
- Pipeline huấn luyện, đánh giá và triển khai mô hình dự báo.

### 5.3. Thiếu phần giao diện trực quan

Hiện chưa có dashboard hoặc giao diện web để:

- xem video kèm kết quả nhận diện,
- xem thống kê theo thời gian,
- xem biểu đồ mật độ,
- xem dữ liệu theo camera hoặc theo làn.

Nếu bổ sung dashboard, giá trị trình bày của đề tài sẽ tăng lên rất nhiều.

### 5.4. Thiếu kiểm thử và đánh giá hệ thống

Dự án hiện chưa thấy:

- unit test,
- integration test,
- test API,
- đánh giá độ chính xác tracking,
- benchmark tốc độ xử lý.

Thiếu phần này khiến việc chứng minh chất lượng hệ thống còn yếu.

## 6. Những chỗ cần cập nhật hoặc chỉnh sửa

Dựa trên hiện trạng code, có một số nội dung nên chỉnh sửa để dự án đồng bộ và chặt chẽ hơn.

### 6.1. Chỉnh sửa về mặt nghiệp vụ

- Đổi `event_type` từ `line_crossing` sang tên phản ánh đúng logic hơn như `zone_entry` hoặc `zone_crossing`.
- Lưu thêm `zone_id` vào event và database để biết xe đã được ghi nhận ở vùng nào.
- Làm rõ khái niệm “mật độ giao thông” trong báo cáo: hiện tại đây mới là mức phân loại theo số track đang có, chưa phải mật độ theo nghĩa giao thông học đầy đủ.

### 6.2. Chỉnh sửa về cấu trúc dữ liệu

- Nên đổi trường `density` trong bảng detection từ kiểu chuỗi sang cấu trúc rõ ràng hơn, ví dụ có thể tách thành `density_level` và `active_vehicle_count`.
- Cân nhắc lưu thêm `zone_id`, `bbox`, hoặc `frame_index` nếu muốn phục vụ truy vết sau này.
- Nếu đã có model `TrafficAggregation` và `TrafficPrediction`, nên triển khai luôn luồng ghi dữ liệu thật hoặc tạm thời bỏ chúng khỏi báo cáo để tránh cảm giác có nhưng chưa dùng.

### 6.3. Chỉnh sửa tài liệu

- README hiện quá ngắn, chưa mô tả cách cài đặt và cách chạy.
- Cần bổ sung tài liệu mô tả cấu trúc dự án, ý nghĩa từng module và các lệnh chạy chính.
- Nên ghi rõ model nào đang được sử dụng thật sự, vì trong code có dấu vết của nhiều đường dẫn model khác nhau.
- Cần ghi rõ workflow train model, workflow chạy detection và workflow backend.

### 6.4. Chỉnh sửa về kỹ thuật backend

- Nên thay cách đồng bộ schema thủ công bằng công cụ migration như Alembic nếu dự án tiếp tục phát triển.
- Bổ sung response model cho API để dữ liệu trả về ổn định hơn.
- Bổ sung route thống kê theo thời gian và theo camera.
- Tách logic nghiệp vụ ra service rõ hơn thay vì để router xử lý trực tiếp.

## 7. Những điểm cần tối ưu

Ngoài việc hoàn thiện tính năng, dự án còn cần tối ưu ở một số mặt quan trọng.

### 7.1. Tối ưu hiệu năng xử lý video

Hiện tại dự án đã có các tối ưu đơn giản như bỏ qua frame và resize ảnh. Tuy nhiên vẫn có thể cải thiện thêm:

- Cho phép cấu hình động `FRAME_SKIP` tùy theo hiệu năng máy.
- Dùng batch processing hoặc pipeline bất đồng bộ nếu muốn tăng tốc.
- Tối ưu phần load model và suy luận trên GPU ổn định hơn.
- Giảm số lần vẽ lên frame nếu chỉ chạy chế độ backend.

### 7.2. Tối ưu độ chính xác đếm xe

Phần đếm xe hiện phụ thuộc vào tâm bounding box rơi vào polygon. Cách này đơn giản nhưng có thể gây sai số khi:

- bounding box không ổn định,
- track bị mất rồi sinh lại ID mới,
- xe đi sát ranh giới zone,
- hai xe che khuất nhau.

Do đó có thể tối ưu bằng cách:

- dùng line crossing rõ ràng hơn nếu mục tiêu là đếm xe qua vạch,
- thêm logic hướng di chuyển,
- lưu lịch sử vị trí của track trong nhiều frame,
- cải thiện tham số của DeepSort,
- đánh giá lại chất lượng model trên đúng video bài toán.

### 7.3. Tối ưu độ ổn định khi gửi dữ liệu

Hiện tại nếu backend lỗi, event sẽ bị mất. Nên tối ưu bằng cách:

- thêm retry,
- thêm hàng đợi tạm trong bộ nhớ hoặc file,
- ghi log lỗi đầy đủ,
- có cơ chế gửi bù khi backend hoạt động trở lại.

### 7.4. Tối ưu cơ sở dữ liệu và truy vấn

Với SQLite, hệ thống chạy demo là phù hợp. Nhưng nếu dữ liệu tăng:

- truy vấn có thể chậm,
- khó mở rộng đồng thời,
- khó triển khai nhiều nguồn ghi.

Sau này nên cân nhắc:

- chuyển sang PostgreSQL,
- thêm index theo `timestamp`, `camera_id`, `vehicle_type`,
- chuẩn hóa bảng dữ liệu để thuận tiện tổng hợp.

## 8. Đánh giá tổng thể hiện trạng dự án

Nếu đánh giá một cách thẳng thắn, dự án hiện đã hoàn thành tốt phần xương sống của hệ thống:

- Có mô hình nhận diện phương tiện.
- Có tracking để tránh đếm lặp.
- Có zone để ghi nhận sự kiện.
- Có backend để lưu dữ liệu.
- Có dữ liệu và môi trường huấn luyện.

Nhưng dự án vẫn chưa hoàn thiện ở phần khai thác giá trị từ dữ liệu:

- Chưa có thống kê nâng cao.
- Chưa có dashboard.
- Chưa có mô hình dự báo thật.
- Chưa có kiểm thử và đánh giá định lượng rõ ràng.

Vì vậy, có thể mô tả đúng nhất rằng:

> Dự án đã hoàn thành phần nền tảng xử lý nhận diện và lưu trữ dữ liệu, nhưng các phần phân tích sâu, dự báo, tối ưu độ ổn định và hoàn thiện sản phẩm vẫn còn đang ở giai đoạn phát triển tiếp.

## 9. Kết luận

`Traffic Density Analysis System` là một dự án có định hướng đúng và có nền tảng kỹ thuật tương đối rõ ràng. Điểm mạnh lớn nhất của dự án là đã xây dựng được pipeline chạy thực từ video đầu vào cho đến khi sinh sự kiện và lưu vào cơ sở dữ liệu. Đây là phần quan trọng nhất và cũng là phần đã được thực hiện rõ ràng nhất.

Tuy nhiên, để dự án trở thành một hệ thống phân tích mật độ giao thông hoàn chỉnh hơn, cần tiếp tục bổ sung các phần còn thiếu như tổng hợp dữ liệu theo thời gian, dự báo giao thông thật, dashboard trực quan, đánh giá mô hình, tối ưu hiệu năng và nâng cấp độ ổn định khi vận hành. Nếu hoàn thiện được các điểm này, dự án sẽ chuyển từ mức demo kỹ thuật sang mức ứng dụng thực tiễn cao hơn.
