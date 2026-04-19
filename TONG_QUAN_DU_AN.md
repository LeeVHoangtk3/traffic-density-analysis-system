# 🏢 TỔNG QUAN DỰ ÁN: TRAFFIC DENSITY ANALYSIS SYSTEM

Đây là bản tóm tắt toàn diện về hệ thống phân tích mật độ giao thông, bao gồm chức năng, công nghệ sử dụng, cách thức hoạt động và luồng dữ liệu chi tiết của dự án.

---

## 🎯 1. Chức năng và Mục đích

Hệ thống **Traffic Density Analysis System** là một giải pháp AI hoàn chỉnh, hoạt động theo tời gian thực với các chức năng chính:
- **Phát hiện phương tiện giao thông (Object Detection):** Có khả năng nhận diện nhiều loại xe khác nhau (xe máy, ô tô, xe buýt, xe tải) trên luồng camera, video streaming.
- **Theo dõi phương tiện (Multi-object Tracking):** Gắn và theo dõi `track_id` cho từng phương tiện chạy qua màn hình để tránh đếm trùng.
- **Đếm số lượng theo vùng (Zone-based Counting):** Đếm lưu lượng từng loại phương tiện di chuyển qua một khu vực quan tâm (ROI - Region of Interest).
- **Đánh giá mật độ giao thông (Density Estimation):** Tự động phân loại mức độ tắc đường thành các mức độ: "LOW" (Thấp), "MEDIUM" (Trung bình), "HIGH" (Chật cứng).
- **Lưu trữ và Truy xuất (Data persistence & API):** Cung cấp hệ thống backend với các API RESTful phục vụ lưu trữ sự kiện nhận diện và trích xuất dữ liệu, tổng hợp báo cáo.

---

## 🛠️ 2. Công nghệ sử dụng (Tech Stack)

Hệ thống sử dụng kiến trúc **Microservices**, tách biệt phần xử lý Machine Learning (Detection Engine) và khối Backend Server.

### AI / Computer Vision (Detection Engine)
- **Deep Learning Framework:** `PyTorch`
- **Object Detection:** `YOLOv9` (sử dụng custom trained model `best_final.pt` hoặc model pretrained).
- **Object Tracking:** `DeepSort` (Kết hợp Kalman filter và thuật toán Hungarian để giữ dấu phương tiện theo các frame).
- **Xử lý ảnh (Computer Vision):** `OpenCV` (Xử lý frame, resize, vẽ bounding box, zone), `NumPy`.
- **Định dạng vùng (Geometry):** `Shapely` (Tính toán các đa giác giao cắt).
- **Khác:** `Supervision`, `Loguru` cho logging.

### Backend API & Database (Lưu trữ và Trao đổi dữ liệu)
- **Web Framework:** `FastAPI` (Xây dựng các endpoint REST API hiệu năng cao).
- **ORM & Database:** `SQLAlchemy` để giao tiếp với DB.
- **Data Validation:** `Pydantic` (Xác thực dữ liệu Input/Output từ AI đẩy sang).
- **Database Server:** `SQLite` (Mặc định, lưu tại tập tin `traffic.db`) hoặc có thể scale sang `PostgreSQL`.
- **Server Gateway:** `Uvicorn` (ASGI Server).

---

## ⚙️ 3. Cách thức thực hiện và Luồng dữ liệu (Data Flow)

Luồng hoạt động của hệ thống chia làm 2 giai đoạn (Tiers) hoạt động đồng thời:

### Giai đoạn 1: AI Detection Pipeline (Nhận diễn và tạo Sự Kiện)
1. **CameraEngine:** Đọc video từ file `.mp4`, luồng RTSP camera hoặc Webcam trực tiếp. Nhặt từng frame một cách liên tục.
2. **FrameProcessor:** Xử lý (Resize chuẩn hóa về 640x640, đổi chuẩn màu BGR → RGB, padding) -> Ép kiểu Tensor đẩy sang GPU để YOLO xử lý.
3. **Detector (YOLOv9):** Quét qua Tensor Frame, trả về tập Bounding Boxes chứa (Tọa độ, Tỉ lệ chuẩn xác - Confidence >= 0.4, Loại xe).
4. **Tracker (DeepSort):** Xử lý ma trận dự đoán (Kalman Filter), ánh xạ và gắn một ID đặc trưng cho từng phương tiện duy nhất trải qua các frame.
5. **ZoneManager & Counter:** Kiểm tra tâm của Bounding Box (`cx, cy`) có nằm trong Đa giác thiết lập trước (Polygol point-in-test bằng OpenCV) hay không. Nếu có, tăng biến đếm của class đó lên 1 điểm.
6. **DensityEstimator:** Dựa trên tổng số đang tracking trên đường, đánh giá Level "LOW" / "MEDIUM" / "HIGH".
7. **Event Generator & HTTP Publish:** Đóng gói thông tin (UUID, track_id, timestamp, level, v.v.) vào JSON Event. Bắn thông qua lệnh HTTP POST phi đồng bộ (non-blocking) gửi lên API Backend.

### Giai đoạn 2: Backend API (Lưu trữ và Trả truy vấn)
1. **Lắng nghe Requests:** Uvicorn chạy FastAPI trên cổng 8000 sẽ nhận JSON Event.
2. **Data Validation:** Lớp Pydantic sẽ kiểm tra kiểu dữ liệu của hệ thống, cản rác và phòng chống hack/Injection.
3. **Ghi Database:** FastAPI dùng session của SQLAlchemy (`db.add()`) tạo record mới vào bảng `vehicle_detections`. 
4. **Đáp ứng Client khác:** Hệ thống lưu được phục vụ qua các Endpoint:
   - `GET /raw-data`: Trả về toàn bộ lịch sử detect được (JSON List).
   - `GET /aggregation`: Hàm phân tích, tổng hợp dữ liệu mật độ (VD: Đếm số lượng, trả về mốc kẹt xe đang ở mức Rất Nặng, Trung bình...).

---

## 📁 4. Chi tiết Kiến trúc Thư mục

* **`detection/`**: Trạm phân tích Engine AI chính.
  * `camera_engine.py`, `detector.py`, `tracker.py`... ở trong: Chứa các Model OOP chịu trách nhiệm từng công đoạn Tracking.
  * `integration/publisher.py`: Công cụ bắn API lên backend.
  * `main.py`: Nhạc trưởng thu nhận luồng trên rải xuống các Engine. Điều chỉnh vòng loop frame liên tục.
  * `pro_models/`: Trọng số của YOLOv9 (đuôi `.pt`).
* **`backend/`**: Hệ thống máy chủ API.
  * `api/`: Các luồng Routes endpoint như `detection_routes.py`.
  * `models/`, `schemas/`: Lớp bảo mật kiểu dữ liệu ORM, Pydantic DB.
  * `main.py`: Entry point khởi tạo Server bằng Uvicorn và cài đặt Table SQLite.
* **`yolov9-cus/`**: Thư mục đặc trị dùng cho việc custom training Model YOLOv9 (Dataset, runs, code thuật toán YOLO).

---

## 🚀 5. Hướng dẫn Chạy (Quick Start)

Tiến trình chạy đòi hỏi môi trường tách biệt:
1. **Cài cắm Thư Viện:** 
   ```bash
   pip install -r requirements.txt
   ```
2. **Chạy dịch vụ Backend:** (Mở Terminal 1)
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
   *Hệ thống sẽ tự khởi tạo `traffic.db` nếu chưa có DB.*

3. **Chạy trí tuệ nhân tạo - Detection Engine:** (Mở Terminal 2)
   ```bash
   python detection/main.py
   ```
   *Cửa sổ OpenCV popup sẽ hiện ra video nhận diện xe cộ và thông số.*

4. **Trải nghiệm API:**
   Chạy `http://localhost:8000/raw-data` trên trình duyệt để thấy thành quả dữ liệu đã được tổng hợp, lưu trữ.
