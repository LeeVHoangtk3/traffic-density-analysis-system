# CHƯƠNG 6: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

---

## 6.1. Tổng kết kết quả đạt được

Nghiên cứu đã hoàn thành mục tiêu xây dựng **Hệ thống phân tích mật độ giao thông thông minh thời gian thực** (*Traffic Density Analysis System*) — tích hợp đầy đủ từ khâu nhận diện phương tiện, dự báo lưu lượng bằng học máy, đến hiển thị kết quả trực quan trên dashboard giám sát. Toàn bộ kết quả phân tích được trình bày trực tiếp trên giao diện web, cho phép người dùng theo dõi và đánh giá tình trạng giao thông một cách trực quan.

### 6.1.1. Kết quả hiển thị trên Dashboard

Giao diện dashboard hiển thị các thông tin chính sau:

- **Lưu lượng dự báo 15 phút tới (XGBoost):** Hiển thị số phương tiện dự kiến trong chu kỳ 15 phút kế tiếp, kèm mức mật độ được phân loại tự động qua 4 cấp — **Low** (Đường vắng), **Medium** (Thông thoáng), **High** (Bắt đầu đông), **Heavy** (Ùn tắc) — với mã màu trực quan tương ứng (Xanh → Vàng → Cam → Đỏ).

- **Thang phân cụm thích ứng (K-Means):** Thanh đo tiến trình hiển thị vị trí lưu lượng dự báo trên thang ngưỡng K-Means, cho thấy trực quan khoảng cách đến các mức ùn tắc. Các ngưỡng phân cụm được tính toán tự động từ dữ liệu lịch sử, không cần thiết lập thủ công.

- **Giám sát đặc trưng trực tiếp (Online Features):** Hiển thị realtime các giá trị đặc trưng đầu vào mà mô hình XGBoost sử dụng để dự báo (`lag_1`, `lag_2`, `rolling_mean_3`), giúp người dùng hiểu cơ sở dự đoán.

- **Biểu đồ lịch sử lưu lượng:** Trình bày đồ thị chuỗi thời gian tổng hợp lưu lượng phương tiện, kết hợp với thống kê trung bình, hỗ trợ nhận diện xu hướng giao thông theo thời gian.

- **Video phát hiện phương tiện:** Phát trực tiếp video đã xử lý với bounding box nhận diện phương tiện theo thời gian thực, đồng bộ với dữ liệu thống kê trên dashboard.

### 6.1.2. Kết quả đánh giá mô hình

- Mô hình **XGBoost** đạt **MAPE < 10%** và **R² > 0.85** trên tập kiểm tra, vượt trội hơn ~40–45% so với baseline Linear Regression.
- Mô hình **YOLOv9 + ByteTrack** nhận diện và theo dõi thành công 4 loại phương tiện phổ biến trong giao thông Việt Nam.
- Toàn bộ pipeline dự báo có thời gian inference **< 10ms**, không yêu cầu GPU, phù hợp triển khai nhẹ.

---

## 6.2. Đóng góp của nghiên cứu

### 6.2.1. Đóng góp khoa học

- **Chuyển đổi bài toán chuỗi thời gian thành hồi quy bảng** thông qua Feature Engineering có chủ đích, cho phép XGBoost xử lý hiệu quả dữ liệu chuỗi thời gian mà không cần kiến trúc recurrent.
- **Phân ngưỡng mật độ tự thích ứng bằng K-Means**, thay thế ngưỡng cứng thủ công, tự động điều chỉnh theo đặc điểm hạ tầng thực tế.
- **Thiết kế đặc trưng bù đắp kiến trúc (Algorithm-Aware Feature Design)**, mỗi đặc trưng được lập luận rõ vai trò trong việc khắc phục điểm yếu cố hữu của mô hình.

### 6.2.2. Đóng góp thực tiễn

- **Xử lý trực tiếp trên RAM**, không lưu khung hình gốc, giải quyết bài toán quá tải lưu trữ khi triển khai diện rộng.
- **Kiến trúc module hóa** với 4 thành phần độc lập giao tiếp qua REST API, dễ dàng mở rộng và thay thế.
- **Pipeline huấn luyện đôi chế độ (Offline/Online)** với cơ chế fallback tự động, đảm bảo tính khả dụng cao.

---

## 6.3. Hạn chế

- **Mô hình XGBoost không ngoại suy được** — dự báo bị bão hòa khi lưu lượng vượt kỷ lục lịch sử.
- **Chỉ dự báo 1 bước (15 phút tới)**, chưa hỗ trợ dự báo đa bước cho tầm nhìn dài hơn.
- **Chưa tích hợp đặc trưng ngoại sinh** như thời tiết, sự kiện, tai nạn.
- **Chưa có cơ chế tái huấn luyện tự động** — mô hình có thể lỗi thời khi hạ tầng thay đổi.
- **Detection phụ thuộc góc camera cố định** và hiệu năng giảm trong điều kiện thời tiết xấu.
- **Chưa kiểm thử trên môi trường thực tế** với camera trực tuyến (live streaming).

---

## 6.4. Hướng phát triển tương lai

### 6.4.1. Nâng cao mô hình dự báo

- Tích hợp **đặc trưng ngoại sinh** (thời tiết, sự kiện, lịch ngày lễ) để cải thiện độ chính xác.
- Mở rộng sang **dự báo đa bước** (multi-step forecasting) cho tầm nhìn 1–2 giờ.
- Áp dụng **Ensemble Stacking** kết hợp XGBoost với mô hình tuyến tính để xử lý vùng ngoại suy.
- Xây dựng **pipeline tái huấn luyện tự động** khi phát hiện suy giảm hiệu năng.

### 6.4.2. Nâng cấp module Detection

- Hỗ trợ **đa camera** và kỹ thuật re-identification (ReID) theo dõi xe xuyên camera.
- Tăng cường nhận diện trong **điều kiện thời tiết khó** (mưa, sương mù, ban đêm).
- Triển khai trên **thiết bị biên** (Edge Deployment) bằng kỹ thuật quantization và pruning.

### 6.4.3. Mở rộng quy mô hệ thống

- **Điều phối mạng lưới nút giao** và tối ưu "sóng xanh" giữa các nút giao liên tiếp.
- Ứng dụng **Reinforcement Learning** cho bài toán tối ưu pha đèn tín hiệu.
- Tích hợp **IoT và V2X** (Vehicle-to-Everything) để bổ sung nguồn dữ liệu ngoài camera.

### 6.4.4. Cải thiện trải nghiệm người dùng

- Phát triển **ứng dụng di động** cung cấp thông tin mật độ và gợi ý lộ trình tránh ùn tắc.
- Tích hợp **bản đồ GIS** với heatmap overlay và báo cáo xu hướng giao thông phục vụ quy hoạch.

---

## Tổng kết

Nghiên cứu đã hoàn thành việc xây dựng một hệ thống phân tích mật độ giao thông thông minh hoàn chỉnh, từ nhận diện phương tiện (YOLOv9, ByteTrack) đến dự báo lưu lượng (XGBoost, K-Means) và hiển thị trực quan trên dashboard. Hệ thống đạt **độ chính xác dự báo trên 90%**, **thời gian inference dưới 10ms**, và được thiết kế theo kiến trúc module hóa sẵn sàng mở rộng. Các hạn chế đã nhận diện và hướng phát triển được đề xuất mở ra nhiều cơ hội nghiên cứu tiếp theo, hướng tới mục tiêu xây dựng hệ thống giao thông thông minh toàn diện cho đô thị Việt Nam.

---

**Cập nhật lần cuối:** 2026-06-14
