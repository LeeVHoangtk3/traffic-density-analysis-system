# TỔNG QUAN LỘ TRÌNH TRIỂN KHAI & PHÂN CHIA NHÂN SỰ TOÀN HỆ THỐNG
**Mục tiêu:** Tài liệu này cung cấp cái nhìn toàn cảnh về kiến trúc hệ thống, phân loại module nghiệp vụ, trạng thái hoàn thành thực tế của các nhiệm vụ trong mã nguồn và giải pháp phân phối công việc khoa học cho nhóm 3 lập trình viên đối với **các phần việc còn lại**.

---

## 1. Bản Đồ Module Hệ Thống (System Architecture Map)
Hệ thống Phân tích Mật độ Giao thông Thông minh (Traffic Density Analysis System) được chia thành **4 module cốt lõi** hoạt động tuần hoàn khép kín:

```
┌────────────────────────────────────────────────────────┐
│             [MODULE 1: COMPUTER VISION]                │
│ 📹 OpenCV + YOLOv9 + ByteTrack -> Multi-ROI Counting   │
└───────────────────────────┬────────────────────────────┘
                            │ (Events HTTP POST /detection)
                            ▼
┌────────────────────────────────────────────────────────┐
│               [MODULE 2: WEB BACKEND]                  │
│ ⚡ FastAPI + MongoDB -> Log, Aggregation & REST APIs   │
└───────────────────────────┬────────────────────────────┘
                            │ (Autoregressive Lags History)
                            ▼
┌────────────────────────────────────────────────────────┐
│             [MODULE 3: MACHINE LEARNING]               │
│ 🤖 XGBoost Predictors + K-Means + PhaseLightOptimizer  │
└───────────────────────────┬────────────────────────────┘
                            │ (light_status.json sync)
                            ▼
┌────────────────────────────────────────────────────────┐
│               [MODULE 4: WEB FRONTEND]                 │
│ 💻 React JS Dashboard -> Real-time Visualizer         │
└────────────────────────────────────────────────────────┘
```

---

## 2. Bản Đồ Nghiệm Thu Nhiệm Vụ (Completed vs. Remaining Tasks)
Dựa trên việc kiểm tra toàn bộ mã nguồn hiện tại, chúng ta phân loại rõ rệt các phần việc **Đã Hoàn Thành** (tài sản ML Core có sẵn) và các phần việc **Còn Lại Cần Thực Hiện** (tích hợp hệ thống và giao diện):

### A. 🎯 Các Nhiệm Vụ Đã Hoàn Thành (ML Core Assets)
Các nhiệm vụ này đã được lập trình xuất sắc, tối ưu hóa và kiểm thử đầy đủ trong mã nguồn hiện tại của dự án:
* **`TASK_ML_01` (Tiền xử lý & Xoay trục đa nút giao):** Đã hoàn thiện trong tệp `ml_service/preprocess.py` để xử lý, làm sạch và xoay trục đồng thời cho cả 3 SegmentID (138, 72887, 83624) tạo ra tệp dữ liệu hợp nhất `junction_pivot_clean.csv`.
* **`TASK_ML_02` (Kỹ nghệ đặc trưng & Lớp dự báo AI):** Đã hoàn thiện lớp `TrafficPredictor` trong `ml_service/traffic_predictor.py` (trích xuất lags, peaks, circular sin/cos) và tích hợp API endpoint `/predict-next` tại `backend/api/prediction_routes.py`.
* **`TASK_ML_03` (Huấn luyện 3 mô hình XGBoost hợp nhất):** Đã hoàn thiện trong tệp `ml_service/train.py` thực hiện huấn luyện chronological 80/20 train/test và đóng gói 3 mô hình `.pkl` thành công vào thư mục `ml_service/model/`.

---

### B. 🛠️ Các Nhiệm Vụ Còn Lại Cần Triển Khai (Integration & UI)
Đây là các nhiệm vụ còn khuyết hoặc đang dùng hàm sinh số ngẫu nhiên (mock/random) cần được thực thi để đóng vòng hệ thống:

| Mã Task | Tên Nhiệm Vụ Còn Lại | Module Nghiệp Vụ | Thư Mục / File Mã Nguồn Tác Động |
| :--- | :--- | :---: | :--- |
| **`TASK_ML_04`** | K-Means phân cụm ngưỡng ùn tắc động | **ML / Database** | `ml_service/density_cluster.py`<br>MongoDB: `directional_thresholds` |
| **`TASK_ML_05`** | Thuật toán tối ưu hóa 2 pha đèn động | **Control Logic** | `ml_service/phase_optimizer.py`<br>`ml_service/test_phase_optimizer.py` |
| **`TASK_ML_06`** | Adapter LightDeltaModel cầu nối hệ thống | **Integration** | `ml_service/light_delta_model.py`<br>`integration_system/system_runner.py` |
| **`TASK_CV_07`** | Cấu hình 3 đa giác ROI phân tách hướng CV | **CV Engine** | `detection/configs_cameras/cam_01.json`<br>`detection/engine/zone_manager.py` |
| **`TASK_FE_08`** | Đồng bộ Dashboard React thời gian thực | **Frontend** | `frontend/src/App.js`<br>`frontend/src/App.css` |
| **`TASK_ML_09`** | Đánh giá học thuật & Báo cáo chất lượng | **ML Evaluation** | `ml_service/evaluate.py`<br>`ml_service/data/training_metrics.json` |

---

## 3. Phân Chia Nhân Sự Đối Với Các Nhiệm Vụ Còn Lại
Để tối ưu hóa song song luồng công việc còn lại, chúng ta phân bổ cho **3 vị trí lập trình viên chuyên biệt** (chi tiết xem tại tệp cấu hình phân bổ [remaining_tasks_assignment.md](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/docs/plan/remaining_tasks_assignment.md)):

* **👤 LẬP TRÌNH VIÊN A (ML Specialist):**
  * Đảm nhận: **Task 4** (Phân cụm K-Means ngưỡng ùn tắc động) và **Task 9** (Đánh giá học thuật MAE/RMSE/MAPE và vẽ ảnh đồ thị png phục vụ quyển báo cáo tốt nghiệp).
  * Mục tiêu: Đảm bảo độ chính xác của ngưỡng mật độ và chuẩn hóa học thuật báo cáo.
* **👤 LẬP TRÌNH VIÊN B (Backend & Control Engineer):**
  * Đảm nhận: **Task 5** (Lập trình bộ toán học tối ưu pha `PhaseLightOptimizer`) và **Task 6** (Viết lớp adapter `LightDeltaModel` kết nối mô hình ML với `system_runner.py` để sửa lỗi import).
  * Mục tiêu: Điều phối đèn tín hiệu thông minh và tích hợp hệ thống khép kín.
* **👤 LẬP TRÌNH VIÊN C (CV & React Specialist):**
  * Đảm nhận: **Task 7** (Căn chỉnh 3 đa giác ROI trên OpenCV, tích hợp ByteTrack đếm xe phân hướng bắn payload POST) và **Task 8** (Đồng bộ dashboard React hiển thị đồng hồ giây AI và đồ thị so sánh Chart.js thực tế).
  * Mục tiêu: Trích xuất trực quan đầu vào thời gian thực và hiển thị UI quản trị cao cấp.

---

## 4. Các Cột Mốc Tích Hợp Cộng Tác (Collaborative Milestones)
Trong 2 tuần làm việc trên các nhiệm vụ còn lại, 3 nhà phát triển sẽ cùng phối hợp tại 2 cột mốc kiểm thử liên thông quan trọng:

> [!IMPORTANT]
> **Cột mốc 1 (Ngày 3) - Tích hợp Dữ liệu Đếm Phân Làn:**
> * Lập trình viên C hoàn thành hiệu chuẩn 3 ROI và ByteTrack đếm xe phân làn rẽ. Chạy test video đếm xe và bắn API.
> * Lập trình viên A xác nhận MongoDB collection `vehicle_detections` lưu đúng cấu trúc chứa trường `direction` (`straight`, `left`, `right`).

> [!IMPORTANT]
> **Cột mốc 2 (Ngày 6) - Nghiệm thu Vận hành Đóng vòng (Closed-loop Testing):**
> * Lập trình viên B tích hợp `LightDeltaModel` và `PhaseLightOptimizer` vào `system_runner.py` chạy thật bằng ML.
> * Lập trình viên C khởi chạy React App, kiểm duyệt đồng hồ giây AI đếm ngược và đồ thị so sánh Actual vs Predicted hiển thị mượt mà đồng bộ 100% thời gian thực.
