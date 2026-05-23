# KẾ HOẠCH HỢP NHẤT ML PIPELINE: Ý TƯỞNG A, B, C

**Hệ Thống Điều Khiển Tối Ưu Pha Đèn Tín Hiệu Động Cho Nút Giao Tách Luồng**  
*(Isolated Intelligent Junction Phase Controller)*

---

## 1. Mục Tiêu Chiến Lược Của Hệ Thống

Hệ thống chuyển dịch hoàn toàn từ trạng thái giả lập (mock/random data) sang **vận hành dựa trên dữ liệu thực tế** bằng cách kết hợp sức mạnh của Thị giác máy tính thời gian thực và Học máy mẫu bảng dự báo chuỗi thời gian.

### Các Tiêu Chí Chính:

#### 🎯 Tối ưu hóa hạ tầng đô thị
- Không điều khiển đèn ngã tư một cách cào bằng
- Hệ thống phân tách nhu cầu giao thông thành các **Pha giao thông (Traffic Phases)** độc lập
- Tự động phân bổ lại số giây đèn xanh tỷ lệ thuận với áp lực dòng xe dự báo
- Chủ động giải tỏa nút giao từ sớm

#### 💾 Xử lý On-RAM & Tiết kiệm tài nguyên
- Khai thác video stream đầu vào
- Trích xuất số liệu đếm số xe dạng văn bản/JSON cực nhẹ
- Lưu vào MongoDB và giải phóng hình ảnh ngay lập tức
- Triệt tiêu bài toán quá tải dung lượng lưu trữ ổ cứng

#### 🤖 Tự động hóa cấu hình (Data-Driven)
- Thay vì sử dụng các tham số tĩnh do con người tự gán
- Hệ thống áp dụng học máy không giám sát
- Tự phân tích và hiểu rõ năng lực thông hành hình học của từng nhánh rẽ riêng biệt

---

## 2. Đặc Tả Ngữ Cảnh Hạ Tầng & Hình Học Ngã Rẽ

### Cấu hình Góc Camera Thực Tế

Hệ thống sử dụng **1 Camera góc rộng duy nhất** giám sát một nút giao một chiều tuyến tính, phân tách trực diện thành 3 nhánh rẽ độc lập:

1. **Nhánh rẽ trái (`left`)**
   - Luồng di chuyển cua hẹp
   - Tốc độ thoát xe chậm
   - Dễ gây dồn ứ xung đột hàng dài

2. **Nhánh đi thẳng (`straight`)**
   - Trục hành lang chính
   - Hạ tầng rộng
   - Năng lực thoát xe cao
   - Sức chứa (capacity) lớn

3. **Nhánh rẽ phải (`right`)**
   - Luồng đi vào làn đường gom nội bộ
   - Hoặc đường dịch vụ

### Cấu hình Pha Đèn Giao Thông (Signal Phases)

Tổng chu kỳ đèn (Cycle Time) được cố định là **90 giây** và phân chia thành:

- **Pha 1 (Pha Tuyến Chính):** 
  - Cho phép luồng xe **Đi thẳng** và **Rẽ phải** di chuyển song song
  - Cấu hình nền mặc định: **50 giây**

- **Pha 2 (Pha Rẽ Trái):**
  - Cho phép luồng xe **Rẽ trái** di chuyển cắt ngang dòng trục đường bên kia độc lập
  - Cấu hình nền mặc định: **30 giây**

- **10 giây còn lại:** Khóa cứng cho các tham số đèn vàng và đèn đỏ an toàn chuyển mạch giao thoa đô thị

---

## 3. Kiến Trúc Luồng Dữ Liệu Khép Kín (Closed-Loop Data Pipeline)

Luồng vận hành đồng bộ thời gian thực của hệ thống được chia làm các tầng xử lý tuần tự:

```
               [ LUỒNG VIDEO REAL-TIME HOẶC FILE VIDEO ]
                                  │
                                  ▼ (Xử lý trên RAM qua OpenCV)
               
               [ TẦNG 1: COMPUTER VISION (DETECTION) ]
       - YOLOv9 phát hiện phương tiện, ByteTrack bám đuổi theo ID
       - Đếm xe vượt vạch qua 3 vùng ROI độc lập: Làn Thẳng | Làn Trái | Làn Phải
       - Định kỳ mỗi 15 phút, tổng hợp và đẩy Payload JSON về Backend FastAPI
                                  │
                                  ▼ (Lưu trữ văn bản số hóa cực nhẹ)
               
               [ TẦNG 2: CƠ SỞ DỮ LIỆU MONGODB ]
       - Lưu log thô số lượng xe vào collection 'traffic_aggregation'
       - Cơ chế gom nhóm GroupBy theo bộ khóa: camera_id + timestamp_15min + direction
                                  │
                                  ▼ (Orchestrator Layer chạy chu kỳ 5 giây)
               
               [ TẦNG 3: MACHINE LEARNING & ĐIỀU KHIỂN ĐÈN ]
       
       BƯỚC 1 (Ý tưởng A - XGBoost): 
         → Dự báo chính xác số lượng xe sẽ đến của 3 ngả rẽ trong 15 phút kế tiếp (t+1)
         → Dựa vào lịch sử Lag_1, Lag_2 từ MongoDB
       
       BƯỚC 2 (Ý tưởng B - K-Means): 
         → Đối chiếu số thô dự báo với Ma trận ngưỡng thích ứng 
         → Trong collection 'directional_thresholds'
         → Gắn nhãn mật độ (Low/Medium/High/Heavy)
       
       BƯỚC 3 (Ý tưởng C - Optimizer): 
         → Nạp áp lực dự báo vào PhaseLightOptimizer
         → Tính toán số giây bù trừ delta_green cho Pha Thẳng và Pha Trái
         → Dưới ràng buộc an toàn
       
       BƯỚC 4: 
         → Ghi đè trạng thái chu kỳ mới vào file 'integration_system/light_status.json'
                                  │
                                  ▼ (Cập nhật thời gian thực)
               
               [ TẦNG 4: DASHBOARD FRONTEND DISPLAY ]
       - Dashboard React đọc file json
       - Hiển thị đồng hồ đếm ngược pha đèn của AI
       - Vẽ đồ thị dự báo 3 nhánh kèm màu sắc cảnh báo trực quan tương ứng
```

---

## 4. Chi Tiết Chức Năng 3 Ý Tưởng ML Cốt Lõi

### Ý Tưởng A: Bộ Dự Báo Lưu Lượng Phân Tách Ngả Rẽ
*(Multi-Directional Junction Regressor)*

**Chức năng:** Giải quyết bài toán hồi quy chuỗi thời gian ngắn hạn (15 phút). Dự báo độc lập số lượng xe tải trọng đổ vào 3 làn đường riêng biệt trong cửa sổ tiếp theo.

**Thuật toán:** XGBoost Regressor xuất dưới dạng 3 file trọng số nhỏ gọn:
- `model_straight.pkl`
- `model_left.pkl`
- `model_right.pkl`

Các file này được nhúng trực tiếp vào RAM nhằm đảm bảo tốc độ đáp ứng thời gian thực.

**Ma trận Đặc trưng:**
- **Biến tuần hoàn:** `hour_sin`, `hour_cos` mã hóa sóng thời gian liên tục mốc giao ngày (sát mốc 23:45 và 00:00)
- **Biến lịch trình:** `day_of_week`, `is_weekend`
- **Biến trễ tự hồi quy (Autoregressive Lags):** 
  - `lag_1` (15 phút trước)
  - `lag_2` (30 phút trước)
  - `rolling_mean_3` (trung bình trượt 3 bước)
  - Được tính toán độc lập cho riêng ngả đó từ dữ liệu thật

---

### Ý Tưởng B: Phân Cấp Mật Độ Động Thích Ứng
*(Adaptive Directional Clustering)*

**Chức năng:** Sử dụng học máy không giám sát để tự động hóa định nghĩa nhãn ùn tắc dựa trên thực tế phân phối hạ tầng, thay vì áp dụng ngưỡng cứng cảm tính.

**Thuật toán:** K-Means Clustering với số cụm $K=4$

**Cơ chế vận hành:** 
- Một tác vụ chạy ngầm định kỳ hàng tuần quét toàn bộ lịch sử đếm xe của từng hướng trong MongoDB
- Tính toán trung điểm giữa các tâm cụm liên tiếp để làm ranh giới bước nhảy trạng thái
- Xuất ra ma trận ngưỡng tối ưu lưu trữ tại collection `directional_thresholds`

**Hiệu quả:** Nhận diện thông minh hình học nút giao
- Ví dụ: Làn rẽ trái cua hẹp sức chứa nhỏ chỉ cần $>30 \text{ xe/15 phút}$ đã báo trạng thái Heavy (màu Đỏ)
- Trong khi làn đi thẳng rộng rãi phải đạt $>100 \text{ xe}$ mới kích hoạt trạng thái báo động

---

### Ý Tưởng C: Bộ Tối Ưu Hóa Chu Kỳ Pha Đèn Tín Hiệu Động
*(Dynamic Traffic Phase Timing Predictor)*

**Chức năng:** Đóng vòng điều khiển logic (Closed-loop control), chuyển dịch kết quả phân tích số liệu của AI thành hành động thay đổi cấu hình đèn hạ tầng thực tế.

**Thuật toán:** Tối ưu hóa phân bổ toán học tỷ lệ thuận theo chỉ số áp lực dòng xe (Flow Ratio Pressure) kết hợp bộ lọc điều kiện biên an toàn giao thông đô thị (Hard Constraints).

**Ràng buộc giới hạn kỹ thuật:**
- Giờ đèn xanh tối thiểu của mỗi pha: $\ge 15$ giây
- Giờ đèn xanh tối đa của mỗi pha: $\le 55$ giây
- Tránh triệt tiêu hoàn toàn quyền ưu tiên hoặc kéo dài pha gây kiệt quệ nút giao xung quanh

**Luồng thực thi:**
- Ghi đè trực tiếp kết quả số giây tối ưu vào file trạng thái `light_status.json` sau mỗi chu kỳ lặp
- Frontend đồng bộ hiển thị
- Luồng OpenCV cập nhật đèn tín hiệu trực quan trên màn hình

---

## 5. Lộ Trình Triển Khai Chi Tiết Trong 20 Ngày

Kế hoạch hành động được phân chia khoa học nhằm tận dụng tối đa các công cụ AI:
- **Gemini 3.5 Flash:** Phân tích dữ liệu lớn
- **Claude Sonnet 4.6:** Refactor mã nguồn thuật toán chuyên sâu
- **GPT 5.5:** Tích hợp hệ thống tổng thể

### Giai Đoạn 1: Tiền Xử Lý Dữ Liệu Thực Tế & Huấn Luyện XGBoost (Ngày 1 → Ngày 7)

#### Ngày 1 - Ngày 2: Data Engineering
- **File:** `ml_service/preprocess.py`
- Đọc tệp dữ liệu thực tế lớn `Automated_Traffic_Volume_Counts_20260521.csv`
- Loại bỏ dấu phẩy hàng nghìn
- Làm sạch target `Vol`
- Đồng bộ mốc phút không chuẩn về bin 15 phút

#### Ngày 3 - Ngày 4: Pivot & Lọc
- Lập trình thuật toán tìm kiếm mã `SegmentID` tối ưu nhất có đầy đủ các hướng di chuyển độc lập
- Đại diện cho nút giao
- Thực hiện lệnh `pivot_table` xoay trục hướng đi thành 3 cột song song: `vol_straight`, `vol_left`, `vol_right`
- Xuất file sạch ra: `ml_service/data/junction_pivot_clean.csv`

#### Ngày 5 - Ngày 7: Model Training (Ý tưởng A)
- **File:** `ml_service/train.py`
- Xây dựng ma trận tính năng đặc trưng trễ: `lag_1`, `lag_2`, `rolling_mean_3`
- Xây dựng đặc trưng tuần hoàn
- Chia tập dữ liệu dựa trên thời gian: Train $\le 2024$, Test $\ge 2025$
- Huấn luyện độc lập 3 mô hình XGBoost
- Lưu file đóng gói `.pkl` vào thư mục hệ thống

---

### Giai Đoạn 2: Xây Dựng Tầng Phân Cụm Ngưỡng & Logic Điều Khiển Pha Đèn (Ngày 8 → Ngày 14)

#### Ngày 8 - Ngày 10: Adaptive Clustering (Ý tưởng B)
- **File:** `ml_service/density_cluster.py`
- Viết hàm kết nối MongoDB
- Thực hiện thuật toán K-Means ($K=4$)
- Tự sinh ma trận ranh giới ngưỡng động cho riêng ngả: Trái, Thẳng, Phải
- Lưu cấu hình vào collection `directional_thresholds`

#### Ngày 11 - Ngày 14: Phase Controller (Ý tưởng C)
- **File:** `ml_service/light_delta_model.py`
- Phân bổ giây đèn xanh động của 2 Pha tỷ lệ thuận theo áp lực dòng xe dự báo từ Giai đoạn 1
- **Refactor Layer Orchestrator:** `integration_system/system_runner.py`
- Tự động hóa việc gọi chuỗi pipeline ML
- Ghi đè payload JSON đồng bộ thời gian thực ra file `light_status.json`

---

### Giai Đoạn 3: Kiểm Thử Toàn Diện, Trích Xuất Metric & Đóng Gói Quyển Báo Cáo (Ngày 15 → Ngày 20)

#### Ngày 15 - Ngày 17: System Integration Test
- Chạy kiểm thử tích hợp đóng vòng
- Cấu hình 3 vùng ROI đếm xe trong module `detection/` tương ứng với 3 nhãn ngả rẽ mới
- Giả lập luồng dữ liệu chạy ở chế độ Headless: `NO_DISPLAY=true`
- Kiểm tra tính ổn định
- Đồng bộ hiển thị đồng hồ đếm lùi pha đèn trên Dashboard React

#### Ngày 18 - Ngày 20: Metrics & Documentation
- Trích xuất các chỉ số đo lường hiệu năng khoa học bắt buộc:
  - **MAE** (Mean Absolute Error)
  - **RMSE** (Root Mean Square Error)
  - **MAPE** (Mean Absolute Percentage Error)
  - Trên tập Test của 3 mô hình hướng đi
  - Đưa vào chương thực nghiệm
- Tổng hợp lý thuyết giải thuật nút giao tách luồng hình học đô thị
- Phân bổ pha để hoàn thiện quyển báo cáo tốt nghiệp
- Bàn giao đúng hạn Deadline

---

## Kết Luận

File Markdown đặc tả toàn bộ kế hoạch chiến lược, kiến trúc luồng dữ liệu phối hợp và lộ trình thực thi 20 ngày cho module Machine Learning (Ý tưởng A, B, C) đã được hoàn thành.

Hệ thống sẽ vận hành dựa trên dữ liệu thực tế, tối ưu hóa hạ tầng đô thị thông qua các pha đèn tín hiệu động, và triệu hồi sự kết hợp giữa Thị giác máy tính thời gian thực và Học máy dự báo chuỗi thời gian.
