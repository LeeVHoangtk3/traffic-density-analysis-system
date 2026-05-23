# BẢNG PHÂN CHIA CHI TIẾT CÁC NHIỆM VỤ CÒN LẠI (REMAINING TASKS ASSIGNMENT)
**Ngữ cảnh:** Hệ thống đã hoàn thành 100% nền tảng ML Core ở Giai đoạn 1 (Task 1, Task 2, và Task 3 đã được lập trình sẵn trong mã nguồn). Tài liệu này chỉ tập trung phân bổ các nhiệm vụ còn lại (Tasks 4, 5, 6, 7, 8, 9) cho nhóm 3 lập trình viên nhằm hoàn thiện hệ thống khép kín.

---

## 📊 Trạng Thái Triển Khai Toàn Hệ Thống

* **ĐÃ HOÀN THÀNH (ML Core Foundation):**
  * `TASK_ML_01` (Tiền xử lý volume & Xoay trục đa nút giao - Đã có `preprocess.py`).
  * `TASK_ML_02` (Đặc trưng chuỗi thời gian & Tích hợp `TrafficPredictor` vào backend).
  * `TASK_ML_03` (Huấn luyện XGBoost xuất ra 3 file pkl lưu tại `ml_service/model/`).
* **CÒN LẠI CẦN THỰC HIỆN (Integration & Control):**
  * **`TASK_ML_04`** (Phân cụm K-Means tự thích ứng ngưỡng mật độ).
  * **`TASK_ML_05`** (Thuật toán tối ưu hóa 2 pha đèn động).
  * **`TASK_ML_06`** (Xây dựng lớp cầu nối `LightDeltaModel` và refactor `system_runner.py`).
  * **`TASK_CV_07`** (Hiệu chuẩn 3 đa giác ROI & ByteTrack phân tách hướng CV).
  * **`TASK_FE_08`** (Đồng bộ Dashboard React thời gian thực & vẽ Chart.js).
  * **`TASK_ML_09`** (Đánh giá học thuật xuất báo cáo tốt nghiệp).

---

## 👥 Phân Chia Các Nhiệm Vụ Còn Lại Cho 3 Nhân Sự

```
           ┌──────────────────────────────────────────────┐
           │        BẢNG PHÂN BỔ NHIỆM VỤ CÒN LẠI         │
           └──────────────────────┬───────────────────────┘
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
 ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
 │ DEVELOPER A  │         │ DEVELOPER B  │         │ DEVELOPER C  │
 │ (ML Core /   │         │ (Backend &   │         │ (CV & React  │
 │  Clustering) │         │  Control)    │         │  Dashboard)  │
 └──────────────┘         └──────────────┘         └──────────────┘
  - Task 4 (K-Means)       - Task 5 (Pha Opt)       - Task 7 (CV ROI Zones)
  - Task 9 (Evaluation)    - Task 6 (Delta Bridge)  - Task 8 (React Dashboard)
```

---

### 👤 Lập Trình Viên A: Kỹ Sư Học Máy & Phân Tích (ML Core & Clustering Specialist)
* **Trọng tâm công việc:** Tập trung hoàn thiện logic học máy không giám sát trên MongoDB và viết mã nguồn đánh giá, xuất biểu đồ nghiên cứu học thuật phục vụ quyển báo cáo tốt nghiệp.
* **Nhiệm vụ phân bổ:**

#### 1. [TASK_ML_04] K-Means Dynamic Congestion Thresholds
- **Mô tả:** Lập trình tệp `ml_service/density_cluster.py` lấy dữ liệu lịch sử từ MongoDB/CSV, chạy K-Means ($K=4$) cho từng hướng rẽ, tính toán 3 ranh giới động (`low_to_medium`, `medium_to_high`, `high_to_heavy`) và ghi đè vào collection `directional_thresholds` của MongoDB.
- **Sản phẩm bàn giao:** File `ml_service/density_cluster.py` hoạt động ổn định và collection `directional_thresholds` được cập nhật.

#### 2. [TASK_ML_09] Academic Evaluation & Metrics Report
- **Mô tả:** Lập trình tệp `ml_service/evaluate.py` nạp 3 mô hình XGBoost pkl đã huấn luyện, chạy dự báo trên tập Test độc lập (từ ngày 2025-01-01 trở đi), tính toán các chỉ số MAE, RMSE, MAPE cho từng hướng. Xuất ra tệp `training_metrics.json` và vẽ 3 đồ thị so sánh Actual vs Predicted dưới dạng ảnh `.png` chất lượng cao.
- **Sản phẩm bàn giao:** File `ml_service/evaluate.py`, tệp JSON kết quả và 3 hình ảnh đồ thị trong thư mục `ml_service/data/`.

---

### 👤 Lập Trình Viên B: Kỹ Sư Backend & Thuật Toán Điều Khiển (Backend & Control Engineer)
* **Trọng tâm công việc:** Tập trung xây dựng thuật toán phân bổ giây xanh tối ưu, lập trình lớp cầu nối tích hợp ML để loại bỏ hoàn toàn lỗi import trong `system_runner.py` và khép kín vòng điều phối hệ thống.
* **Nhiệm vụ phân bổ:**

#### 1. [TASK_ML_05] Phase Light Optimization & Safety Constraints
- **Mô tả:** Xây dựng thuật toán phân bổ thời lượng đèn xanh động cho 2 Pha chính (P1: thẳng + phải, P2: rẽ trái) tỷ lệ thuận với áp lực dòng xe dự báo, đảm bảo các ràng buộc biên cứng an toàn đô thị ($15s \le g_i \le 55s$, tổng $80s$ trên chu kỳ $90s$). Cài đặt lớp `PhaseLightOptimizer` tại `ml_service/phase_optimizer.py`.
- **Sản phẩm bàn giao:** File `ml_service/phase_optimizer.py` và bộ Unit Tests `ml_service/test_phase_optimizer.py`.

#### 2. [TASK_ML_06] LightDeltaModel Bridge & System Runner Refactor
- **Mô tả:** Giải quyết lỗi import và cảnh báo hệ thống bằng cách lập trình lớp cầu nối `LightDeltaModel` tại tệp `ml_service/light_delta_model.py`. Lớp này sẽ lazy-load 3 mô hình XGBoost, tiếp nhận cấu trúc đầu vào từ `system_runner.py`, chạy predict và truyền qua `PhaseLightOptimizer` để tính toán delta trả về. Đồng thời refactor `system_runner.py` để đóng vòng điều phối.
- **Sản phẩm bàn giao:** Tệp `ml_service/light_delta_model.py` và file `system_runner.py` refactor hoàn thiện.

---

### 👤 Lập Trình Viên C: Kỹ Sư Thị Giác Máy Tính & Giao Diện (CV & React Specialist)
* **Trọng tâm công việc:** Tập trung hiệu chuẩn 3 vùng đa giác kiểm soát trên khung hình OpenCV, tích hợp ByteTrack phân tách luồng đếm xe thời gian thực gửi backend và xây dựng giao diện Dashboard React hiển thị đồng bộ.
* **Nhiệm vụ phân bổ:**

#### 1. [TASK_CV_07] Multi-Zone ROI & Direction-Aware CV
- **Mô tả:** Thiết lập tọa độ 3 đa giác ROI (`left`, `straight`, `right`) tương ứng với 3 làn xe thực tế vào file `detection/configs_cameras/cam_01.json`. Cập nhật `zone_manager.py` và `main.py` để sử dụng bottom-center tiếp đất của bounding box, kiểm tra sự giao cắt với từng đa giác qua ByteTrack và gửi HTTP POST chứa `direction` chuẩn xác lên Backend endpoint `/detection`.
- **Sản phẩm bàn giao:** File cấu hình JSON và module CV đếm xe phân hướng hoạt động thời gian thực.

#### 2. [TASK_FE_08] React Dashboard Real-time Sync & Chart.js
- **Mô tả:** Loại bỏ hoàn toàn mock data trong `frontend/src/App.js` và kết nối với các API thực: `/traffic-lights/status` để hiển thị đồng hồ giây xanh/đỏ đếm ngược của AI, các API lịch sử `/predictions/history` và `/aggregation/history` để vẽ đồ thị so sánh Actual vs Predicted bằng Chart.js. Cập nhật CSS để đổi màu sắc thẻ cảnh báo ùn tắc nhấp nháy động dựa trên ngưỡng phân loại thích ứng của K-Means.
- **Sản phẩm bàn giao:** Giao diện Dashboard React (`frontend/src/App.js` và `App.css`) hoàn chỉnh, đồng bộ 100% thời gian thực.

---

## 📅 Lịch Trình Tích Hợp Chi Tiết (Integration Timeline)

* **Ngày 1 - Ngày 3:**
  * **Dev A:** Viết code `density_cluster.py` (K-Means).
  * **Dev B:** Thiết lập `PhaseLightOptimizer` (Task 5).
  * **Dev C:** Căn chỉnh 3 đa giác ROI trên video `traffic1.mp4` và lập trình ByteTrack đếm phân làn (Task 7).
  * *👉 Cột mốc 1: Dev C hoàn thành gửi sự kiện phân hướng lên Backend; Dev A xác nhận DB lưu đúng.*
* **Ngày 4 - Ngày 6:**
  * **Dev B:** Lập trình lớp cầu nối `LightDeltaModel` và refactor `system_runner.py` chạy thật bằng ML (Task 6).
  * **Dev C:** Viết code React app gọi các API thật và vẽ biểu đồ Chart.js (Task 8).
  * **Dev A:** Lập trình script `evaluate.py` đánh giá sai số tốt nghiệp (Task 9).
  * *👉 Cột mốc 2: Nghiệm thu toàn hệ thống. Dashboard hiển thị đồng bộ con số giây của AI và đồ thị thật.*
