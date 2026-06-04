# Traffic Density Analysis System - Tổng quan & Định hướng chiến lược

Tài liệu này mô tả kiến trúc, công nghệ và định hướng mục tiêu phát triển của hệ thống phân tích mật độ giao thông thông minh thời gian thực `traffic-density-analysis-system`. Hệ thống được thiết kế hướng tới giải pháp thực tế, chuyển dịch từ các mô phỏng tĩnh sang tối ưu hóa đèn tín hiệu giao thông ngã tư dựa trên luồng dữ liệu thời gian thực và mô hình học máy chuỗi thời gian phân tách ngả rẽ.

---

## 1. Định hướng & Mục tiêu Chiến lược Hệ thống

Mục tiêu cốt lõi của dự án là xây dựng một **Hệ Thống Điều Khiển Tối Ưu Pha Đèn Tín Hiệu Động Cho Nút Giao Tách Luồng** (*Isolated Intelligent Junction Phase Controller*). Hệ thống chuyển đổi toàn diện từ trạng thái giả lập (mock/random data) sang vận hành dựa trên dữ liệu thực tế thông qua việc tích hợp luồng xử lý khép kín:

### 🎯 Phân tích lưu lượng giao thông thông minh
Hạ tầng nút giao được giám sát và phân tách nhu cầu giao thông thành các luồng di chuyển độc lập. Hệ thống tự động dự báo áp lực dòng xe, giúp cảnh báo ùn tắc từ sớm và hỗ trợ đưa ra các quyết định điều tiết phù hợp.

### 💾 Xử lý Trên RAM (On-RAM) & Tiết kiệm tài nguyên
Để loại bỏ bài toán quá tải dung lượng lưu trữ ổ cứng khi triển khai diện rộng, hệ thống xử lý trực tiếp dòng video stream thời gian thực trên RAM thông qua OpenCV và các thuật toán Thị giác máy tính. Dữ liệu hình ảnh thô sau khi được trích xuất thành số liệu đếm phương tiện (dạng text/JSON cực nhẹ) sẽ được lưu trữ vào cơ sở dữ liệu MongoDB, còn khung hình video sẽ được giải phóng ngay lập tức.

### 🤖 Cấu hình Tự động Dựa trên Dữ liệu (Data-Driven Calibration)
Hệ thống loại bỏ hoàn toàn các tham số tĩnh do con người gán thủ công một cách cảm tính. Bằng việc áp dụng học máy không giám sát (K-Means Clustering), hệ thống tự phân tích và hiểu rõ năng lực thông hành hình học thực tế của từng nhánh rẽ riêng biệt dựa trên lịch sử lưu thông tích lũy, từ đó tự cập nhật các ngưỡng cảnh báo ùn tắc.

---

## 2. Đặc Tả Ngữ Cảnh Hạ Tầng & Hình Học Ngã Rẽ

### Cấu hình Góc Camera Thực Tế
Hệ thống sử dụng **1 Camera góc rộng cố định (Fixed Wide-Angle Traffic Camera)** giám sát một nút giao một chiều tuyến tính (1-Way Corridor) đóng vai trò gom luồng xe tiến vào ngã rẽ, phân tách trực diện thành 3 nhánh di chuyển độc lập:
1. **Nhánh Rẽ Trái (`left`):** Luồng di chuyển cua hẹp, tốc độ giải tỏa chậm, dễ dồn ứ xung đột cắt làn ngang dòng ngược chiều, sức chứa (capacity) thấp nhất.
2. **Nhánh Đi Thẳng (`straight`):** Trục hành lang chính, hạ tầng rộng, vận tốc tối đa và sức chứa lớn, năng lực xả xe cao nhất.
3. **Nhánh Rẽ Phải (`right`):** Hướng dòng phương tiện tách luồng đi vào làn đường gom nội bộ hoặc đường dịch vụ, dòng chảy tương đối độc lập, ít xung đột trực diện.



## 3. Kiến Trúc Luồng Dữ Liệu Khép Kín (Closed-Loop Data Pipeline)

Luồng vận hành đồng bộ thời gian thực của hệ thống được thực thi thông qua 4 tầng xử lý tuần tự:

```text
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
        
        Ý TƯỞNG A (XGBoost Regressor):
          → Dự báo chính xác lưu lượng xe đổ vào 3 nhánh rẽ ở chu kỳ 15 phút kế tiếp (t+1)
          → Sử dụng đặc trưng lịch sử trễ tự hồi quy (Lag_1, Lag_2, Rolling Mean) từ MongoDB
        
        Ý TƯỞNG B (K-Means Clustering):
          → Đối chiếu lưu lượng xe thực tế/dự báo với ma trận ngưỡng thích ứng động
          → Gắn nhãn trạng thái mật độ ùn tắc (Low/Medium/High/Heavy) riêng biệt cho từng ngả
        

                                  │
                                  ▼ (Cập nhật thời gian thực)
               
               [ TẦNG 4: DASHBOARD FRONTEND DISPLAY ]
        - Vẽ đồ thị so sánh thực tế và dự báo của 3 ngả rẽ kèm màu sắc cảnh báo trực quan tương ứng
```

---

## 4. Chi Tiết Chức Năng 3 Ý Tưởng ML Cốt Lõi

### 📈 Ý Tưởng A: Bộ Dự Báo Lưu Lượng Phân Tách Ngả Rẽ (Multi-Directional Regressor)
- **Chức năng:** Giải quyết bài toán hồi quy chuỗi thời gian ngắn hạn (15 phút). Dự báo độc lập số lượng xe đổ vào 3 làn đường riêng biệt (`straight`, `left`, `right`) trong cửa sổ tiếp theo.
- **Thuật toán:** XGBoost Regressor xuất dưới dạng 3 file trọng số độc lập: `model_straight.pkl`, `model_left.pkl`, `model_right.pkl`.
- **Ma trận Đặc trưng (Feature Matrix):**
  - *Biến tuần hoàn:* `hour_sin`, `hour_cos` mã hóa thời gian liên tục mốc ngày-đêm.
  - *Biến lịch trình:* `day_of_week`, `is_weekend`.
  - *Biến trễ tự hồi quy (Autoregressive Lags):* `lag_1` (15 phút trước), `lag_2` (30 phút trước), `rolling_mean_3` (trung bình trượt 3 bước trước đó).

### 🏷️ Ý Tưởng B: Phân Cấp Mật Độ Động Thích Ứng (Adaptive Directional Clustering)
- **Chức năng:** Sử dụng học máy không giám sát để tự động hóa định nghĩa ngưỡng mật độ ùn tắc dựa trên thực tế phân phối hạ tầng thực tế của từng làn rẽ, thay vì dùng ngưỡng cứng cảm tính.
- **Thuật toán:** K-Means Clustering với số cụm $K=4$, phân cấp ra các mức: `Low`, `Medium`, `High`, `Heavy`.
- **Cơ chế vận hành:** Tác vụ chạy ngầm định kỳ hàng tuần quét toàn bộ lịch sử đếm xe của từng hướng trong MongoDB, tính toán trung điểm giữa các tâm cụm liên tiếp để làm ranh giới bước nhảy trạng thái, sau đó lưu trữ kết quả cấu hình ngưỡng động vào collection `directional_thresholds`.
- **Hiệu năng thực tế:** Làn rẽ trái sức chứa nhỏ chỉ cần $>30 \text{ xe/15 phút}$ đã báo trạng thái `Heavy` (màu Đỏ), trong khi làn đi thẳng rộng rãi phải đạt $>100 \text{ xe}$ mới kích hoạt cảnh báo tương ứng.



## 5. Cấu Trúc Thư Mục Dự Án Thực Tế

```text
traffic-density-analysis-system/
│
├── backend/                        # FastAPI Web API Layer
│   ├── main.py                     # Entrypoint khởi chạy backend API
│   ├── config.py                   # Cấu hình biến môi trường và MongoDB
│   ├── mongo_database.py           # Thiết lập kết nối và chỉ mục MongoDB
│   ├── seed_data.py                # Kịch bản nạp dữ liệu mẫu
│   ├── api/                        # Chứa các router chức năng
│   │   ├── aggregation_routes.py   # API tổng hợp dữ liệu (15 phút)
│   │   ├── camera_routes.py        # API quản lý thiết bị camera
│   │   ├── detection_routes.py     # API tiếp nhận sự kiện đếm xe
│   │   ├── health_routes.py        # API kiểm tra trạng thái hoạt động
│   │   ├── prediction_routes.py    # API dự báo lưu lượng tiếp theo
│   │   ├── traffic_routes.py       # API quản lý và tối ưu đèn tín hiệu
│   │   └── video.py                # API tải lên và truyền luồng video
│   ├── schemas/                    # Pydantic schemas xác thực dữ liệu
│   └── services/                   # Business logic xử lý dữ liệu
│
├── detection/                      # Computer Vision Engine
│   ├── main.py                     # Entrypoint xử lý video/camera
│   ├── camera_engine.py            # Quản lý luồng đọc khung hình OpenCV
│   ├── calibrate_zones.py          # Bộ công cụ GUI tương tác hiệu chuẩn vùng ROI bằng chuột
│   ├── configs_cameras/
│   │   └── cam_01.json             # Cấu hình vùng ROI và baseline ngã tư
│   ├── engine/                     # Các module xử lý lõi
│   │   ├── counter.py              # Đếm xe qua vạch ranh giới
│   │   ├── density_estimator.py    # Ước lượng mật độ tức thời
│   │   ├── detector.py             # Bộ phát hiện YOLOv9
│   │   ├── event_generator.py      # Đóng gói và gửi payload JSON lên backend
│   │   ├── frame_processor.py      # Tiền xử lý chuẩn hóa kích thước ảnh
│   │   ├── tracker.py              # ByteTrack bám đuổi hành trình
│   │   └── zone_manager.py         # Quản lý đa giác vùng kiểm soát ROI
│   └── integration/
│       └── publisher.py            # Đẩy tin nhắn qua HTTP
│
├── ml_service/                     # Machine Learning Services
│   ├── traffic_predictor.py        # Bộ dự báo XGBoost
│   ├── light_delta_model.py        # Bộ đề xuất delta thời lượng đèn xanh
│   ├── train.py                    # Script huấn luyện mô hình dự báo
│   ├── predict.py                  # CLI dự đoán nhanh
│   ├── model.pkl                   # File trọng số dự báo (cũ)
│   ├── light_model.pkl             # File trọng số đèn tín hiệu (cũ)
│   └── data/                       # Dữ liệu phục vụ huấn luyện mô hình
│
├── integration_system/             # Orchestration & Coordination Layer
│   ├── system_runner.py            # Vòng lặp điều khiển hệ thống chu kỳ 5 giây
│   ├── congestion_classifier.py    # Phân loại ùn tắc dựa trên ngưỡng
│   ├── performance_monitor.py      # Giám sát tài nguyên hệ thống (RAM/CPU)
│   └── scheduler.py                # Bộ lập lịch gọi API tuần tự
│
├── docs/                           # Tài liệu thiết kế hệ thống
│   ├── OVERVIEW.md                 # Tổng quan & Định hướng mục tiêu (Tài liệu này)
│   ├── camera.md                   # Đặc tả hình học nút giao và ROI zones
│   ├── ke_hoach.md                 # Kế hoạch tích hợp ML 3 Ý tưởng lớn
│   └── plan/                       # Hướng dẫn chi tiết triển khai từng task (Mới)
│
├── traffic-frontend/               # Giao diện Dashboard (React JS)
│   ├── package.json
│   └── src/
│       ├── App.js                  # Điểm dựng giao diện điều khiển chính
│       ├── App.css                 # CSS định hình phong cách hiện đại
│       └── index.js
│
├── video_data/                     # Thư mục lưu trữ video mẫu chạy thử
├── yolov9-cus/                     # Mã nguồn YOLOv9 custom
├── requirements.txt                # Danh sách thư viện Python phụ thuộc
└── yolov9c.pt                      # Trọng số YOLOv9 pre-trained
```

---

## 6. Sơ Đồ Chi Tiết Luồng Chạy API Hệ Thống

Dưới đây là thiết kế luồng API chính của backend kết nối cơ sở dữ liệu MongoDB và hỗ trợ các client gửi nhận dữ liệu:

1. **Gửi sự kiện phát hiện phương tiện (`POST /detection`):**
   - *Client:* `detection/main.py`
   - *Payload:* Chứa `camera_id`, `track_id`, `vehicle_type`, `direction` (left, straight, right), `timestamp`.
   - *Backend:* Kiểm tra trùng lặp `event_id`, lưu trữ trực tiếp vào collection `vehicle_detections`.

2. **Chốt tổng hợp dữ liệu chu kỳ (`POST /aggregation/compute`):**
   - *Client:* Tự động kích hoạt định kỳ mỗi 15 phút.
   - *Payload:* `camera_id`, `window_minutes` (mặc định 15).
   - *Backend:* Truy vấn tất cả detection trong khoảng thời gian vừa qua, thực hiện `distinct(track_id)` phân nhóm theo 3 hướng `left`, `straight`, `right`, lưu kết quả tổng hợp (ví dụ: `vehicle_count`) vào collection `traffic_aggregation`.

3. **Truy vấn dự báo tiếp theo (`GET /predict-next`):**
   - *Client:* `integration_system/system_runner.py` hoặc `ml_service/predict.py`.
   - *Backend:* Lấy dữ liệu trễ (`lag_1`, `lag_2`, `rolling_mean_3`) từ `traffic_aggregation` cho từng hướng rẽ, truyền qua 3 mô hình XGBoost tương ứng, trả về dự báo lưu lượng tiếp theo `predicted_count` cho 3 ngả và lưu vào collection `traffic_predictions`.

4. **Tải lên & Phát trực tuyến video (`POST /video/upload` & `GET /video/{filename}`):**
   - *Client:* Quản trị hệ thống và frontend dashboard.
   - *Backend:* Nhận và lưu trữ video mẫu dạng chunk trong thư mục `videos/`, hỗ trợ truyền tải video dạng phân mảnh (chunked-streaming) hiển thị trên giao diện dashboard của camera tương ứng.

---

## 7. Hướng Dẫn Vận Hành & Khởi Chạy

### 1. Cài đặt môi trường Python
```bash
pip install -r requirements.txt
```

### 2. Thiết lập cấu hình `.env` tại thư mục gốc
Tạo file `.env` với chuỗi kết nối MongoDB của bạn:
```env
DB_URL=mongodb://localhost:27017/
MONGODB_DB=traffic_density
```

### 3. Khởi động Backend API Layer
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Kiểm tra sức khỏe hệ thống:
```bash
curl http://127.0.0.1:8000/health
```

### 4. Khởi chạy luồng phân tích Computer Vision (Headless hoặc Display)
```bash
# Chạy hiển thị khung hình thực tế
python -m detection.main

# Chạy ở chế độ chạy ngầm (tiết kiệm tài nguyên, chỉ đẩy dữ liệu)
$env:NO_DISPLAY="true"
python -m detection.main
```

### 5. Chạy Orchestrator và ML pipeline
```bash
$env:NO_SUBPROCESS="1"
python integration_system/system_runner.py
```

### 6. Khởi động giao diện Dashboard React
```bash
cd traffic-frontend
npm install
npm start
```
Frontend hoạt động tại địa chỉ: `http://localhost:3000`.

---

## 8. Lộ Trình Triển Khai Tiếp Theo (Roadmap)

Dự án hiện đang chuyển từ trạng thái xây dựng khung cơ sở sang tích hợp sâu các thuật toán học máy nâng cao. Chi tiết lộ trình hành động 20 ngày được mô tả thông qua các nhiệm vụ cụ thể được số hóa chi tiết tại thư mục **`docs/plan/`**:

1. **Giai đoạn 1 (Ngày 1 - 7):** Kỹ nghệ dữ liệu lưu lượng lớn, tìm kiếm ngã rẽ tối ưu (`SegmentID`) và huấn luyện độc lập 3 mô hình hồi quy XGBoost (`task_1`, `task_2`, `task_3`).
2. **Giai đoạn 2 (Ngày 8 - 14):** Áp dụng K-Means tìm ngưỡng mật độ ùn tắc tự thích ứng động và lập trình bộ điều khiển tối ưu phân bổ thời lượng xanh động cho 2 pha đèn (`task_4`, `task_5`, `task_6`).
3. **Giai đoạn 3 (Ngày 15 - 20):** Đồng bộ hóa các vùng đếm ROI trên luồng Computer Vision, hiển thị đồng hồ đếm lùi pha đèn AI lên giao diện React Dashboard và hoàn thành quyển báo cáo tốt nghiệp khoa học (`task_7`, `task_8`, `task_9`).

*Cập nhật tài liệu: 23/05/2026 bởi Antigravity Agent.*
