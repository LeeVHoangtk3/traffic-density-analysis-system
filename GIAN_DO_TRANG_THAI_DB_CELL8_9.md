# Giản Đồ Trạng Thái Cơ Sở Dữ Liệu & Luồng Hoạt Động Chi Tiết Của Cell 8 & Cell 9

Tài liệu này giải thích chi tiết trạng thái vật lý của cơ sở dữ liệu MongoDB Atlas sau khi chạy **Cell 8 (Dịch chuyển thời gian co giãn)** và luồng xử lý dữ liệu tiếp theo của **Cell 9 (Seed dữ liệu backend)**. Đây là cẩm nang giúp nhà phát triển nắm rõ cấu trúc dữ liệu và sự biến đổi của database qua từng bước chạy.

---

## 1. Trạng Thái Cơ Sở Dữ Liệu (MongoDB Atlas) Sau Khi Chạy Cell 8

Mục đích duy nhất của **Cell 8 (simulate_history_colab.py)** là biến dữ liệu nhận diện thô dồn cục (quay lệch thời gian) của bạn thành một chuỗi thời gian ảo liên tục dài **3 tiếng (180 phút)** được đồng bộ hóa vật lý giữa các camera.

### 1.1. Trước khi chạy Cell 8 (Trạng thái thô từ YOLOv9)
* **Tình trạng:** Khi bạn chạy nhận diện trên notebook, YOLOv9 xử lý video đầu xuôi và đầu ngược tuần tự. Toàn bộ các sự kiện vượt vạch ROI được lưu vào collection `vehicle_detections` với `timestamp` là thời điểm thực tế máy tính chạy code xử lý ( System Time).
* **Vấn đề xảy ra:**
  * Dữ liệu của 8 video ngắn bị dồn cục lại trong khoảng thời gian chạy (chỉ khoảng 13-15 phút xử lý/video).
  * Video đầu xuôi (`cam01`, `cam02`) và đầu ngược (`cam03`) bị lệch múi giờ xa nhau (ví dụ: Cam xuôi nằm ở 02:00 - 02:30, Cam ngược nằm ở 03:00 - 03:15).
  * Trục thời gian không khớp nhau và quá ngắn $\rightarrow$ Không thể vẽ biểu đồ so sánh xuôi/ngược và AI không có dữ liệu lịch sử chu kỳ 15 phút.

---

### 1.2. Sau khi chạy Cell 8 (Trạng thái co giãn tỷ lệ song song & nối tiếp)
Thuật toán co giãn tỷ lệ ($K = 3.33$ lần) tự động phân chia lại toàn bộ trường `timestamp` của tất cả các bản ghi nhận diện trong collection `vehicle_detections` thành một chuỗi thời gian liền mạch dài 3 tiếng chuẩn hóa (từ `T - 180 phút` đến `T` hiện tại).

#### 🔹 Sự biến động của trường `timestamp` trong Collection `vehicle_detections`:

```
Trục thời gian ảo 3 tiếng (Từ 08:00 sáng đến 11:00 trưa hiện tại):

08:00                                                09:53                                      11:00 (T)
+------------------------------------------------------+------------------------------------------+
|  SONG SONG: Cam 1 & Cam 2 (Xuôi)                     |  NỐI TIẾP: Cam 3 (Ngược)                 |
|  (Rải tỷ lệ video 3 -> 8)                            |  (Rải tỷ lệ video 1 -> 2)                |
|  Timestamp ảo: 08:00:00 -> 09:53:20                  |  Timestamp ảo: 09:53:20 -> 11:00:00      |
+------------------------------------------------------+------------------------------------------+
```

1. **Camera Đầu Xuôi (`cam01`, `cam02`):**
   * Gom toàn bộ detections từ các video `traffic3` đến `traffic8` (tổng thời lượng gốc $34 \text{ phút}$).
   * Co giãn đều $3.33$ lần để xếp **song song đè lên nhau** trong khoảng thời gian ảo dài $113.33 \text{ phút}$ đầu tiên.
   * **Mốc timestamp trong DB:** Chạy tăng dần liên tục từ **`08:00:00` đến `09:53:20`**.
   * *Trạng thái vật lý:* Hai camera có mốc thời gian hoàn toàn khớp nhau từng giây $\rightarrow$ Frontend vẽ được đồ thị song song biểu diễn sự tương quan lưu lượng cùng chiều.

2. **Camera Đầu Ngược (`cam03`):**
   * Gom toàn bộ detections từ các video `traffic1` đến `traffic2` (tổng thời lượng gốc $20 \text{ phút}$).
   * Co giãn đều $3.33$ lần để xếp **nối tiếp ngay sau đầu xuôi** trong khoảng thời gian ảo dài $66.67 \text{ phút}$ tiếp theo.
   * **Mốc timestamp trong DB:** Chạy tăng dần liên tục từ **`09:53:20` đến `11:00:00`** (mốc thời gian hiện tại `T`).
   * *Trạng thái vật lý:* Dữ liệu của Cam 3 nối tiếp mượt mà ngay sau điểm kết thúc của Cam xuôi, tạo thành dòng chảy thời gian 3 tiếng liên tục chạm đến hiện tại.

#### 🔹 Cấu trúc tài liệu mẫu trong Collection `vehicle_detections` sau Cell 8:
```json
{
  "_id": "6657a9f8f812ab572cf93b22",
  "event_id": "e8d7a85c-4f99-470b-bd09-17d4526d1101",
  "camera_id": "cam02",         // ID camera thô
  "track_id": "42",
  "vehicle_type": "car",
  "density": "MEDIUM",
  "direction": "straight",
  "event_type": "zone_entry",
  "confidence": 0.8954,
  "timestamp": "2026-05-30T09:15:30.000Z"  // <-- Đã được Cell 8 cập nhật thành mốc giờ ảo lượng hóa
}
```

---

## 2. Chi Tiết Hoạt Động & Sự Biến Đổi Dữ Liệu Ở Cell 9 (seed_data.py)

Khi bạn bấm nút chạy **Cell 9**, lệnh `python -m backend.seed_data` được gọi. Cell này không thay đổi dữ liệu thô `vehicle_detections` nữa, mà nó đóng vai trò là **"Nhà máy chế biến"** thực hiện 3 công đoạn tuần tự để sinh ra các thông số phân tích cấp cao:

```
[MÃ NGUỒN CELL 9: backend/seed_data.py]
         |
         +---> Công đoạn 1: seed_cameras() ------> Tạo/cấu hình Camera trong collection 'cameras'
         |
         +---> Công đoạn 2: seed_aggregations() --> Gom nhóm 15p, tính mật độ thích ứng K-Means
         |                                          lưu vào 'traffic_aggregation'
         |
         +---> Công đoạn 3: seed_predictions() ---> Lấy 3 lag gần nhất, nạp XGBoost model.predict
                                                    lưu kết quả vào 'traffic_predictions'
```

---

### Công Đoạn 9.1: Khởi Tạo Đăng Ký Cấu Hình Camera (`seed_cameras`)
* **Chức năng:** Tự động nhận diện các `camera_id` đang có dữ liệu trong database và đăng ký cấu hình cho chúng vào bảng `cameras`.
* **Đầu vào (Inputs):** Danh sách các `camera_id` duy nhất được quét từ collection `vehicle_detections` (sử dụng hàm `distinct("camera_id")`).
* **Đầu ra (Outputs):** Tạo mới các bản ghi cấu hình camera tương ứng trong collection `cameras`.
* **Cấu trúc tài liệu sinh ra trong Collection `cameras`:**
  ```json
  {
    "_id": "6657aa50f812ab572cf93d01",
    "camera_id": "cam02",
    "name": "Camera cam02",
    "location": "Chua cap nhat",
    "baseline_green": 30,
    "monitored_direction": "straight"
  }
  ```

---

### Công Đoạn 9.2: Tổng Hợp Chu Kỳ Lịch Sử 15 Phút (`seed_aggregations`)
* **Chức năng:** Lấy toàn bộ hàng ngàn bản ghi nhận diện xe thô trong `vehicle_detections` (đã được Cell 8 rải đều 3 tiếng), gom nhóm chúng theo các block thời gian 15 phút, tính toán tổng lượng xe rẽ các hướng, đối chiếu với các ngưỡng K-Means thích ứng để phân loại mật độ tương ứng.
* **Đầu vào (Inputs):** 
  * Toàn bộ dữ liệu thô trong `vehicle_detections`.
  * Collection `directional_thresholds` (cung cấp các ngưỡng $T_1, T_2, T_3$ thích ứng thu được từ thuật toán K-Means).
* **Đầu ra (Outputs):** **12 bản ghi tổng hợp chu kỳ** (tương ứng 3 tiếng lịch sử) được chèn vào collection `traffic_aggregation`.
* **Cấu trúc tài liệu sinh ra trong Collection `traffic_aggregation`:**
  ```json
  {
    "_id": "6657ab1cf812ab572cf93e11",
    "camera_id": "cam02",
    "vehicle_count": 145,         // Tổng số xe đi qua ROI trong block 15 phút này
    "inbound_count": 145,
    "queue_proxy": 145,
    "congestion_level": "High",   // Phân loại mật độ thích ứng dựa trên K-Means
    "direction_counts": { "left": 0, "straight": 145, "right": 0 },
    "congestion_levels": { "left": "Low", "straight": "High", "right": "Low" },
    "timestamp": "2026-05-30T09:30:00.000Z" // Mốc thời gian kết thúc chu kỳ tổng hợp
  }
  ```

---

### Công Đoạn 9.3: Dự Báo AI Cho Chu Kỳ Kế Tiếp (`seed_predictions`)
* **Chức năng:** Sử dụng mô hình AI **XGBoost Regressor** để dự báo chính xác số lượng xe và mật độ giao thông của **15 phút tiếp theo** cho từng camera.
* **Đầu vào (Inputs):**
  * Collection `traffic_aggregation`: Lấy **3 bản ghi tổng hợp mới nhất** của camera đó làm các đặc trưng trễ (`lag_1` / $Y_{t-1}$, `lag_2` / $Y_{t-2}$, `rolling_mean_3`).
  * Tệp mô hình `ml_service/model/model.pkl`: Cung cấp các trọng số của thuật toán cây tăng cường XGBoost đã huấn luyện.
* **Đầu ra (Outputs):** Các bản ghi dự báo tương ứng được lưu trữ trong collection `traffic_predictions`.
* **Cấu trúc tài liệu sinh ra trong Collection `traffic_predictions`:**
  ```json
  {
    "_id": "6657ab2af812ab572cf93f99",
    "camera_id": "cam02",
    "predicted_volume": 185,            // AI dự đoán 15 phút tới sẽ có 185 xe
    "predicted_congestion": "High",     // Mật độ dự kiến tương lai
    "confidence_score": 0.924,
    "features_used": {
      "lag_1": 145.0,
      "lag_2": 110.0,
      "rolling_mean_3": 115.0
    },
    "timestamp": "2026-05-30T11:00:00.000Z" // Thời điểm thực hiện dự báo (Hiện tại)
  }
  ```

---

## 3. Bảng So Sánh Chi Tiết Luồng Hoạt Động Giữa Cell 8 & Cell 9

| Tiêu Chí So Sánh | BƯỚC 8: Cell Dịch Chuyển Thời Gian (simulate_history) | BƯỚC 9: Cell Seed Dữ Liệu Backend (seed_data) |
| :--- | :--- | :--- |
| **Mục đích chính** | Chuẩn bị nguyên liệu: Giả lập co giãn dòng thời gian 3 tiếng lịch sử đồng bộ. | Chế biến nguyên liệu: Tổng hợp dữ liệu chu kỳ 15 phút và kích hoạt AI dự báo. |
| **Tập tin thực thi** | `simulate_history_colab.py` (Chạy độc lập trên Colab/Local). | `backend/seed_data.py` (Chạy thông qua module backend). |
| **Tác động lên MongoDB** | **Cập nhật ghi đè (Update)** lên collection `vehicle_detections`. | **Chèn mới (Insert)** vào các collection: `cameras`, `traffic_aggregation`, `traffic_predictions`. |
| **Đầu vào (Inputs)** | Các bản ghi nhận diện thô trong `vehicle_detections` có timestamp thực tế khi chạy YOLO. | * Dữ liệu thô đã rải đều trong `vehicle_detections`. <br> * Các ngưỡng K-Means thích ứng. <br> * Tệp mô hình `model.pkl`. |
| **Đầu ra (Outputs)** | Toàn bộ detections được gán lại mốc `timestamp` ảo song song (Cam 1/2) và nối tiếp (Cam 3) kéo dài 3 tiếng. | * Đăng ký camera thành công. <br> * 12 bản ghi tổng hợp 15p hoàn chỉnh. <br> * Kết quả dự báo 15p tiếp theo từ XGBoost. |
| **Cơ chế Fallback** | Giữ nguyên timestamp thô của hệ thống nếu database hoàn toàn trống rỗng không có bản ghi nào. | Nếu thiếu lịch sử aggregation, tự động gán giá trị mặc định an toàn `lag = 50.0` để AI dự báo không bị crash. |
| **Giá trị hiển thị** | Giúp đồng bộ hóa múi giờ giữa đầu xuôi/ngược để vẽ biểu đồ Frontend. | Cung cấp toàn bộ số liệu trực quan (nhãn mật độ, con số dự báo 15p tới, các KPI trung bình) lên màn hình Dashboard. |
