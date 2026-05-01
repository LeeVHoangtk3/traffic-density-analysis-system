# ⚙️ Integration System (Hệ Thống Tích Hợp)

## 1. Tổng Quan Module

**`integration_system`** (Module D) đóng vai trò như một nhạc trưởng (orchestrator) và công cụ giám sát vòng ngoài của toàn bộ hệ thống Traffic Density Analysis. 

Thay vì can thiệp trực tiếp vào Computer Vision hay cấu trúc Database, module này chịu trách nhiệm:
- Khởi chạy và quản lý vòng đời các process (tiến trình) của Backend và Detection một cách tự động.
- Liên tục lấy mẫu (polling) qua REST API để kiểm tra sức khoẻ và theo dõi luồng dữ liệu.
- Tính toán logic đèn giao thông cơ sở (Rule-based) nhằm đối chiếu với Machine Learning.
- Phân loại mức độ ùn tắc độc lập.
- Giám sát tài nguyên phần cứng (CPU, RAM) để đảm bảo tính ổn định.

---

## 2. Chi Tiết Các File và Chức Năng

### 2.1. `system_runner.py` (Entry Point Chính)
Đây là script trung tâm khởi động toàn bộ hệ thống và chạy vòng lặp giám sát.
- **Khởi chạy tiến trình:** Dùng `subprocess.Popen` để tự động chạy Backend (`uvicorn backend.main:app`) và Detection Engine (`python detection/main.py`), giúp vận hành viên chỉ cần chạy 1 tệp tin duy nhất.
- **Graceful Shutdown:** Lắng nghe và xử lý tín hiệu hệ thống (`SIGINT`, `SIGTERM`) để dọn dẹp, tắt các process con an toàn khi người dùng nhấn Ctrl+C.
- **Vòng lặp Pipeline (chạy mỗi 5 giây):**
  1. Yêu cầu dữ liệu từ `/raw-data` API (kiểm tra dòng xe thời gian thực).
  2. Yêu cầu dữ liệu từ `/aggregation` API (kiểm tra chỉ số tổng hợp).
  3. Truyền số đếm vào `CongestionClassifier` để đánh giá lại cục bộ.
  4. Đưa mức độ ùn tắc qua `TrafficLightOptimizer` để tính pha đèn.
  5. Gọi `PerformanceMonitor` lấy thông số CPU/RAM và xuất ra bảng Log trên Terminal.

### 2.2. `traffic_light_logic.py` (Tối Ưu Đèn Giao Thông Cơ Sở)
Chứa class `TrafficLightOptimizer`. Đây là module Rule-based trực tiếp gán thời gian lý tưởng của đèn xanh theo mật độ:
- `low` (Thấp): **20 giây**
- `medium` (Trung bình): **40 giây**
- `high` (Cao): **60 giây**
- `severe` / khác (Rất nghiêm trọng): **90 giây**

*(Ghi chú: Logic này hoạt động như một fallback hệ thống chạy song song và đối chiếu với chỉ số `suggested_delta` được Machine Learning XGBoost dự đoán trả về từ ML Service).*

### 2.3. `congestion_classifier.py` (Phân Loại Ùn Tắc Cục Bộ)
Chứa class `CongestionClassifier`, áp dụng ngưỡng tĩnh (static threshold) cho mức độ kẹt xe dựa trên tổng số xe (vehicle count):
- `< 15` xe: **Low**
- `< 30` xe: **Medium**
- `< 50` xe: **High**
- `>= 50` xe: **Severe**

### 2.4. `performance_monitor.py` (Giám Sát Tài Nguyên)
Sử dụng thư viện `psutil` để thu thập các chỉ số về tài nguyên đang tiêu thụ:
- `cpu_usage`: Lấy `%` CPU đang sử dụng trong 1 khoảng ngắn.
- `memory_usage`: Lấy `%` RAM hệ thống đang sử dụng.
Dữ liệu này rất quan trọng để chẩn đoán xem YOLOv9 hay quá trình ghi API có đang vắt kiệt thiết bị hay không.

### 2.5. `scheduler.py` (Lên Lịch Các Tác Vụ Định Kỳ)
Đóng vai trò là một cronjob nhẹ (Vòng lặp delay 60 giây), có nhiệm vụ kích hoạt hệ thống lưu trữ:
1. Gửi request `GET /aggregation` để backend đóng gói các khung dữ liệu trong quá khứ thành một khối thống kê cố định.
2. Gửi request `GET /predict-next` tới AI Service để tính toán xu hướng kẹt xe và đưa ra đề xuất điều tiết đèn.
Việc tách bạch scheduler với system_runner giúp giảm tải và làm rõ vai trò xử lý tuần tự (batch processing).

### 2.6. `pipeline_test.py` (Kiểm Thử Giả Lập)
Một script độc lập dùng để **mock (giả lập)** dữ liệu. 
Thay vì phải dùng camera để nhận diện, script này tạo ra các bộ số ngẫu nhiên (`random.randint(5, 50)`) và đẩy tới Backend mỗi 5 giây. Mục tiêu để kiểm thử sự chịu tải (load test), phản hồi HTTP và hệ phân loại lưu lượng của Backend có hoạt động mượt mà không mà không cần mở YOLOv9.

---

## 3. Sơ Đồ Hoạt Động (Flow)

```text
[Khởi động system_runner.py]
         │
         ├──▶ [Subprocess 1] Khởi chạy Backend (FastAPI, Port 8000)
         │
         ├──▶ [Subprocess 2] Khởi chạy Detection Engine (Computer Vision)
         │
         └──▶ Vòng lặp quản lý (Mỗi 5 giây):
                    │
                    ├── 1. Kéo API: /raw-data, /aggregation
                    │
                    ├── 2. Tính toán: Phân loại ùn tắc & Đề xuất đèn cơ sở
                    │
                    ├── 3. Lấy Health Metrics: psutil (CPU, Memory)
                    │
                    └── 4. Hiển thị Log (Console Output) để theo dõi
```

---

## 4. Hướng Dẫn Sử Dụng

**1. Khởi động toàn bộ cụm hệ thống thông qua System Runner (được khuyên dùng):**
```bash
python integration_system/system_runner.py
```
> Khi đóng terminal hoặc nhấn `Ctrl+C`, runner sẽ dọn dẹp và dừng cả các tiến trình Backend/Detection ngầm một cách an toàn.

**2. Chạy thử nghiệm giả lập (Không cần Camera/Video):**
```bash
# Lưu ý: Cần khởi động backend.main ở 1 terminal trước
python integration_system/pipeline_test.py
```

**3. Chạy quá trình gom dữ liệu và dự báo thủ công:**
```bash
python integration_system/scheduler.py
```
