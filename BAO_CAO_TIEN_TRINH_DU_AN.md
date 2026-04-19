# BÁO CÁO TIẾN TRÌNH DỰ ÁN

## 1. Thông tin chung về đề tài

- Tên đề tài: `Hệ thống phân tích mật độ giao thông bằng Computer Vision`
- Định hướng bài toán: phân tích mức độ chiếm dụng mặt đường và tự động cảnh báo ùn tắc, ưu tiên đánh giá tình trạng đông đúc của luồng giao thông thay vì chỉ đếm số lượng phương tiện.
- Phạm vi hiện tại của dự án: xử lý video giao thông, nhận diện và theo dõi phương tiện, ghi nhận sự kiện khi phương tiện đi vào vùng quan sát, lưu dữ liệu vào backend và đánh giá mật độ ở mức nguyên mẫu.

## 2. Mô tả tiến trình chung của dự án

Dự án được triển khai theo hướng chia thành các khối chức năng rõ ràng. Đầu vào của hệ thống là video giao thông. Từ video này, khối xử lý thị giác máy tính sẽ thực hiện nhận diện phương tiện, theo dõi đối tượng giữa các khung hình, sau đó kiểm tra xem phương tiện có đi vào vùng quan sát hay không. Khi phát sinh sự kiện, hệ thống tạo event và gửi sang backend thông qua HTTP API. Backend có nhiệm vụ kiểm tra dữ liệu, lưu vào cơ sở dữ liệu SQLite và cung cấp một số API truy vấn.

Qua đối chiếu với mã nguồn hiện tại, pipeline chính của dự án đã hình thành tương đối đầy đủ:

1. Đọc video đầu vào.
2. Chạy mô hình YOLOv9 để nhận diện các loại phương tiện.
3. Dùng tracker để gán `track_id` cho từng đối tượng.
4. Kiểm tra tâm bounding box của xe có đi vào `zone` hay không.
5. Sinh event giao thông.
6. Gửi event lên backend qua endpoint `POST /detection`.
7. Backend lưu dữ liệu vào bảng `vehicle_detections` trong file `traffic.db`.

Như vậy, dự án đã đi qua giai đoạn ý tưởng và đã có một hệ thống demo có khả năng chạy được từ đầu vào video cho đến lưu trữ sự kiện.

## 3. Dự án đã thực hiện đến đâu

### 3.1. Những phần đã hoàn thành ở mức có thể demo

Căn cứ vào repo hiện tại, nhóm đã thực hiện được những nội dung quan trọng sau:

- Đã xây dựng được khối `detection/` để xử lý video giao thông.
- Đã tích hợp mô hình YOLOv9 cho bài toán nhận diện 4 lớp phương tiện: `bus`, `car`, `motorcycle`, `truck`.
- Đã tích hợp tracker để theo dõi phương tiện giữa các frame và tránh đếm lặp ở mức cơ bản.
- Đã cấu hình `zone` cho camera `CAM_01` để ghi nhận sự kiện khi xe đi vào vùng quan tâm.
- Đã xây dựng `DensityEstimator`, tuy hiện tại mới phân loại mật độ theo số lượng đối tượng đang được track.
- Đã xây dựng backend bằng `FastAPI` để nhận dữ liệu và lưu vào cơ sở dữ liệu.
- Đã có file cơ sở dữ liệu thực tế là `traffic.db`.
- Đã ghi nhận dữ liệu thật vào bảng `vehicle_detections`; trạng thái hiện tại là `80` bản ghi.
- Đã có API xem dữ liệu thô và API tổng hợp ở mức cơ bản.
- Đã có notebook và video mẫu để phục vụ việc demo hệ thống.

Đây là kết quả quan trọng vì chứng tỏ nhóm đã hoàn thành được phần xương sống của hệ thống, không chỉ dừng ở mức mô tả ý tưởng.

### 3.2. Những phần đã làm nhưng mới ở mức cơ bản

Bên cạnh những phần đã chạy được, một số chức năng hiện mới đang ở mức khởi tạo:

- Mật độ giao thông hiện đang được xác định bằng luật ngưỡng đơn giản dựa trên số lượng đối tượng đang track, chưa phải đo lường chiếm dụng mặt đường đúng với tinh thần đề tài.
- API `GET /aggregation` chưa tổng hợp trực tiếp từ dữ liệu trong database mà mới nhận `vehicle_count` rồi trả về mức ùn tắc.
- API `GET /predict-next` mới trả về giá trị giả lập `0.45`, chưa phải mô hình dự báo thật.
- Các bảng `traffic_aggregation`, `traffic_predictions`, `cameras` đã tồn tại ở mức model nhưng chưa được đưa vào pipeline xử lý thực tế.
- Có cấu trúc huấn luyện mô hình và dataset, nhưng tài liệu huấn luyện và đánh giá mô hình vẫn chưa đầy đủ.

### 3.3. Đánh giá mức độ hoàn thành hiện tại

Nếu đánh giá theo mục tiêu của một hệ thống hoàn chỉnh, dự án hiện đang ở giai đoạn:

- Đã hoàn thành tương đối tốt phần nhận diện, tracking, zone-based event, kết nối backend và lưu trữ dữ liệu.
- Đang ở mức nguyên mẫu đối với phần phân tích mật độ giao thông.
- Chưa hoàn thiện ở phần đo lường mức độ chiếm dụng mặt đường, cảnh báo ùn tắc tự động theo ngưỡng nghiệp vụ, thống kê theo thời gian và dự báo.

Có thể nói ngắn gọn rằng dự án đã hoàn thành nền tảng kỹ thuật, nhưng chưa đạt đến mức một “hệ thống phân tích mật độ chiếm dụng mặt đường” theo nghĩa đầy đủ.

## 4. Điểm mạnh của những gì đã làm được

Những kết quả hiện tại cho thấy dự án có một số điểm mạnh rõ ràng:

- Pipeline được tách thành các module khá rõ: detection, tracking, zone, event, publisher, backend.
- Hệ thống đã chạy với dữ liệu video thực tế thay vì chỉ mô phỏng.
- Backend đã có luồng nhận và lưu sự kiện thật.
- Có khả năng mở rộng tiếp vì cấu trúc mã nguồn đã được tách theo module.
- Đề tài có tính liên ngành, kết hợp được thị giác máy tính, xử lý video, backend và cơ sở dữ liệu.

## 5. Cần thực hiện tiếp như thế nào

Để đưa dự án từ mức demo lên mức báo cáo hoàn chỉnh hơn, nhóm nên tiếp tục theo các hướng sau.

### 5.1. Hoàn thiện đúng trọng tâm đề tài

Đây là việc quan trọng nhất, vì mô tả đề tài nhấn mạnh “mật độ chiếm dụng mặt đường” thay vì “đếm số lượng phương tiện”. Do đó, nhóm nên:

- Xác định lại chỉ số đánh giá mật độ giao thông theo hướng chiếm dụng mặt đường.
- Tính toán tỷ lệ diện tích mặt đường bị phương tiện chiếm trong vùng quan sát theo từng frame hoặc theo cửa sổ thời gian.
- Tách rõ hai khái niệm: `vehicle count` và `road occupancy`.
- Đặt ngưỡng cảnh báo ùn tắc dựa trên occupancy, thay vì chỉ dựa trên số lượng xe đang có.

Nếu chưa kịp xây dựng occupancy ở mức thật chuẩn, nhóm vẫn có thể trình bày rõ lộ trình nâng cấp từ hệ thống đang đếm và theo dõi xe sang hệ thống đánh giá chiếm dụng mặt đường.

### 5.2. Bổ sung lớp tổng hợp và cảnh báo

Sau khi đã có dữ liệu sự kiện gốc, nhóm nên triển khai tiếp:

- Tổng hợp dữ liệu theo mốc `1 phút`, `5 phút`, `15 phút`.
- Tính thống kê theo camera, theo loại xe, theo khung giờ.
- Lưu kết quả tổng hợp vào bảng `traffic_aggregation`.
- Xây dựng logic cảnh báo ùn tắc khi occupancy hoặc mật độ vượt ngưỡng trong một khoảng thời gian liên tiếp.
- Bổ sung API trả về thống kê và mức cảnh báo theo thời gian thực.

### 5.3. Hoàn thiện backend

Khối backend hiện đã có nền tảng, nhưng cần làm tiếp:

- Cho API tổng hợp đọc trực tiếp từ database thay vì nhận tham số thủ công.
- Bổ sung bộ lọc theo `camera_id`, `timestamp`, `vehicle_type`.
- Chuẩn hóa validation dữ liệu đầu vào.
- Thêm logging, xử lý lỗi và cơ chế retry khi gửi event thất bại.
- Cân nhắc dùng migration thay vì đồng bộ schema thủ công.

### 5.4. Hoàn thiện phần báo cáo và minh chứng

Để báo cáo có sức thuyết phục hơn, nhóm nên bổ sung:

- Sơ đồ kiến trúc tổng thể của hệ thống.
- Ảnh minh họa video đầu vào và kết quả detect/tracking.
- Số liệu về database và số lượng event đã thu được.
- Đánh giá ưu, nhược điểm của cách tiếp cận hiện tại.
- Nếu có thể, bổ sung bảng so sánh giữa “đếm xe” và “ước lượng occupancy” để làm nổi bật điểm mới của đề tài.

## 6. Những khó khăn khi làm dự án

Trong quá trình thực hiện đề tài này, nhóm có thể gặp và thực tế đã gặp một số khó khăn tiêu biểu sau:

### 6.1. Khó khăn trong việc chuyển từ bài toán đếm xe sang bài toán occupancy

Đây là khó khăn lớn nhất về mặt học thuật. Đếm số lượng phương tiện là một bài toán dễ hình dung và dễ triển khai hơn. Trong khi đó, “mật độ chiếm dụng mặt đường” đòi hỏi phải xác định rõ vùng mặt đường được quan sát, cách ước lượng phần diện tích bị chiếm và cách quy đổi thành các mức cảnh báo. Vì vậy, rất dễ rơi vào tình trạng hệ thống hiện đang mạnh về phát hiện và tracking, nhưng phần occupancy lại chưa được mô hình hóa đầy đủ.

### 6.2. Khó khăn về độ chính xác của nhận diện và tracking

Kết quả phân tích phụ thuộc rất lớn vào chất lượng detect và tracking. Khi video có góc quay khó, ánh sáng thay đổi, xe che khuất nhau hoặc khung hình động, hệ thống có thể:

- Bỏ sót xe.
- Nhận sai loại xe.
- Mất track.
- Tạo lại ID mới cho cùng một xe.

Những lỗi này làm ảnh hưởng trực tiếp đến chất lượng thống kê và cảnh báo.

### 6.3. Khó khăn trong việc định nghĩa nghiệp vụ

Ngay cả khi detect tốt, nhóm vẫn phải trả lời những câu hỏi nghiệp vụ không dễ:

- Thế nào được gọi là đông?
- Thế nào được gọi là ùn tắc?
- Cần đánh giá theo frame, theo giây hay theo phút?
- Với mỗi camera, ngưỡng cảnh báo có giống nhau không?

Nếu không chốt được các quy tắc này sớm, phần backend và phần phân tích sẽ rất dễ bị làm theo kiểu tạm thời.

### 6.4. Khó khăn trong đồng bộ giữa các module

Dự án gồm nhiều phần: mô hình nhận diện, tracker, logic zone, event, backend, database. Mỗi khi một phần thay đổi cấu trúc dữ liệu, các phần còn lại đều phải cập nhật theo. Đây là lý do dự án đã có dấu hiệu đồng bộ schema thủ công trong database, cho thấy quá trình phát triển vẫn còn thay đổi nhiều.

### 6.5. Khó khăn về tài nguyên và môi trường chạy

Xử lý video với mô hình deep learning tốn tài nguyên tính toán khá lớn. Khi chạy trên máy có cấu hình vừa phải, nhóm phải dùng các cách tối ưu tạm thời như bỏ qua frame, resize khung hình, tắt hiển thị video. Điều này giúp hệ thống chạy được, nhưng đồng thời cũng ảnh hưởng đến độ mượt và độ chính xác.

### 6.6. Khó khăn trong việc nâng cấp từ prototype lên hệ thống hoàn chỉnh

Prototype có thể chạy được với một video và một camera, nhưng để trở thành hệ thống hoàn chỉnh cần nhiều thành phần hơn:

- Thống kê theo thời gian.
- Dashboard.
- Cảnh báo tự động.
- Logging đầy đủ.
- Kiểm thử.
- Đánh giá định lượng.
- Khả năng mở rộng nhiều camera.

Khoảng cách giữa “chạy được” và “hoàn chỉnh” là khá lớn, nên đây là khó khăn rất thường gặp ở các đề tài AI ứng dụng.

## 7. Định hướng đề xuất cho giai đoạn tiếp theo

Nếu nhóm cần một lộ trình thực hiện tiếp theo rõ ràng, có thể chia thành 3 bước:

### Giai đoạn 1: Chốt đúng bài toán

- Chốt lại định nghĩa `road occupancy`.
- Chốt công thức và ngưỡng cảnh báo ùn tắc.
- Chốt các chỉ số sẽ đưa vào báo cáo.

### Giai đoạn 2: Hoàn thiện kỹ thuật

- Thêm module tính occupancy trong vùng mặt đường.
- Tổng hợp dữ liệu theo thời gian và lưu vào `traffic_aggregation`.
- Thêm API thống kê và cảnh báo.
- Cải thiện logging, validation và retry.

### Giai đoạn 3: Hoàn thiện báo cáo và demo

- Chuẩn bị hình ảnh, số liệu, bảng biểu minh họa.
- Viết rõ phần đã làm được, phần chưa làm được và hướng mở rộng.
- Nếu chưa kịp làm dự báo, cần trình bày trung thực rằng đây là hướng phát triển tiếp theo.

## 8. Kết luận

Tính đến thời điểm hiện tại, dự án `Traffic Density Analysis System` đã hoàn thành được phần nền tảng quan trọng nhất: nhận video, nhận diện và theo dõi phương tiện, xác định sự kiện trong vùng quan sát, gửi dữ liệu sang backend và lưu vào cơ sở dữ liệu. Đây là minh chứng cho thấy nhóm đã xây dựng được một pipeline thực sự hoạt động.

Tuy nhiên, nếu đối chiếu với mục tiêu ban đầu là phân tích mức độ chiếm dụng mặt đường và tự động cảnh báo ùn tắc, hệ thống hiện tại mới đạt đến mức nguyên mẫu ban đầu. Phần mạnh nhất của dự án hiện vẫn là detect, tracking và ghi nhận sự kiện; trong khi phần occupancy, tổng hợp theo thời gian, cảnh báo ùn tắc và dự báo vẫn cần được hoàn thiện tiếp.

Vì vậy, có thể đánh giá tổng quát rằng dự án đã đi đúng hướng, đã có thành quả kỹ thuật rõ ràng, nhưng vẫn cần thêm một giai đoạn hoàn thiện nữa để bám sát hơn với mục tiêu học thuật và ứng dụng thực tế của đề tài.
