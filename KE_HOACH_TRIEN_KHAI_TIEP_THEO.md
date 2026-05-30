# Kế Hoạch Triển Khai Hệ Thống & Nguyên Lý Co Giãn Dữ Liệu AI

Tài liệu này ghi lại toàn bộ ý tưởng thiết kế kiến trúc hệ thống, nguyên lý co giãn thời gian tỷ lệ thuận phục vụ mô hình học máy (Machine Learning), và lộ trình triển khai chi tiết các bước tiếp theo cho dự án **Hệ Thống Phân Tích & Dự Báo Mật Độ Giao Thông Đường Một Chiều**.

---

## 1. Nguyên Lý Co Giãn Thời Gian Tỷ Lệ Thuận (Proportional Time-Scaling)

### 1.1. Hiện tượng giãn dữ liệu so với thời gian thực
Khi thực hiện kéo giãn **54 phút** video gốc thành **180 phút (3 tiếng)** mô phỏng trong cơ sở dữ liệu MongoDB Atlas, mốc thời gian xuất hiện của các phương tiện giao thông sẽ bị **giãn ra khoảng 3.33 lần** so với thực tế ghi hình.

* **Hệ số co giãn ($K$):**
  $$K = \frac{180 \text{ phút (Mô phỏng lịch sử)}}{54 \text{ phút (Tổng thời lượng 8 video gốc)}} = 3.3333...$$
* **Ví dụ thực tế:** 
  Nếu trong video gốc, cứ $3 \text{ giây}$ có $1 \text{ xe}$ đi qua vạch ROI, thì sau khi co giãn, cơ sở dữ liệu MongoDB sẽ ghi nhận cứ $10 \text{ giây}$ mới có $1 \text{ xe}$ đi qua vạch.

> [!NOTE]
> Mặc dù tần suất xuất hiện của xe bị loãng đi 3.33 lần, nhưng vì đây là **co giãn tỷ lệ thuận đồng đều**, mọi quy luật giao thông quan trọng đều được **bảo toàn nguyên vẹn 100%**:
> * Tỷ lệ phân phối lưu lượng giữa các khung giờ (lúc đông xe, lúc vắng xe).
> * Sự biến động trồi sụt của đồ thị mật độ.
> * Sự chênh lệch lưu lượng giữa các camera.

---

### 1.2. Tại sao bắt buộc phải trải dài thời gian phục vụ mô hình học máy (ML)?
Mô hình AI dự báo mật độ giao thông 15 phút tiếp theo của bạn sử dụng thuật toán **XGBoost Regressor** dựa trên các đặc trưng trễ tự hồi quy (Autoregressive Lags):
* **`lag_1`**: Lưu lượng xe tổng hợp của chu kỳ **15 phút trước**.
* **`lag_2`**: Lưu lượng xe tổng hợp của chu kỳ **30 phút trước**.
* **`rolling_mean_3`**: Trung bình trượt của **3 chu kỳ gần nhất** (45 phút trước).

#### ❌ Nếu không kéo giãn thời gian (Giữ nguyên thời gian thực):
YOLO xử lý video 5 phút và lưu dữ liệu dồn cục trong đúng block 15 phút hiện tại. Khi tổng hợp (Aggregation), MongoDB chỉ sinh ra đúng **1 bản ghi** duy nhất. AI hoàn toàn không có dữ liệu của các chu kỳ trước đó (`lag_1`, `lag_2`, `lag_3` trống rỗng) -> Mô hình AI bị lỗi và phải dùng giá trị mặc định gán cứng `50.0 xe`. Chức năng dự báo trở nên vô dụng.

#### ✅ Khi kéo giãn thời gian ra 3 tiếng:
Thuật toán biến 8 video của bạn thành một chuỗi thời gian liên tục dài 3 tiếng (180 phút). Khi chạy tổng hợp dữ liệu, MongoDB sẽ tạo ra đầy đủ **12 bản ghi tổng hợp liên tục** (180 phút / 15 phút mỗi chu kỳ = 12 chu kỳ lịch sử).
* **Kết quả:** AI có đầy đủ các thông số trễ thực tế để dự báo cực kỳ thông minh và chính xác con số lưu lượng của 15 phút tiếp theo.
* **Giao diện:** Biểu đồ lịch sử trên Frontend hiển thị một đường cong liên tục 12 điểm cực kỳ sinh động và chuyên nghiệp.

---

## 2. Sơ Đồ Đồng Bộ Hóa Vật Lý (Song Song & Nối Tiếp)

Vì bạn có **Cam 1 & Cam 2 cùng hướng xuôi**, còn **Cam 3 hướng ngược** tại cùng một địa điểm một chiều, thuật toán mô phỏng (Cell 8) sẽ phối hợp phân bổ thời gian ảo một cách logic nhất:

```
Trục thời gian mô phỏng (3 tiếng liên tục trong MongoDB):
08:00                                                09:53                                      11:00 (Hiện tại)
+------------------------------------------------------+------------------------------------------+
|  SONG SONG: Cam 1 & Cam 2 (Xuôi)                     |  NỐI TIẾP: Cam 3 (Ngược)                 |
|  (Rải tỷ lệ video 3 -> 8)                            |  (Rải tỷ lệ video 1 -> 2)                |
|  Độ dài: 113.33 phút (34p gốc x 3.33)                |  Độ dài: 66.67 phút (20p gốc x 3.33)     |
+------------------------------------------------------+------------------------------------------+
```

* **Cam 1 & Cam 2 (Xuôi - Song song):** Gồm 6 video (`traffic3` đến `traffic8` với tổng $34 \text{ phút}$ gốc). Được co giãn và xếp **song song chồng lên nhau** từ phút thứ `0` đến `113.33`. Điều này đảm bảo tính đồng bộ: khi người dùng xem biểu đồ hướng xuôi, cả Cam 1 và Cam 2 đều hiển thị dữ liệu đồng thời!
* **Cam 3 (Ngược - Nối tiếp):** Gồm 2 video (`traffic1` và `traffic2` với tổng $20 \text{ phút}$ gốc). Được co giãn và xếp **nối tiếp ngay sau đầu xuôi**, chạy từ phút thứ `113.33` đến `180` (Hiện tại) để tạo dòng chảy thời gian liền mạch chạm đến mốc thời gian thực tại của hệ thống.

---

## 3. Kế Hoạch Triển Khai Lập Trình Chi Tiết

Để hoàn thành ý tưởng đột phá này, lộ trình triển khai chi tiết sẽ gồm các bước sau:

### Bước 1: Nâng cấp Cell 8 (Time-Shifting) trong Notebook
* **Nhiệm vụ:** Viết lại file script giả lập `simulate_history_colab.py` trong Cell 8 của notebook `colab_run.ipynb` và `run_system.ipynb`.
* **Logic:** 
  1. Quét MongoDB để lấy toàn bộ danh sách `vehicle_detections` của từng camera.
  2. Gom nhóm các bản ghi theo tên video nguồn (dựa trên thứ tự timestamp gốc tăng dần).
  3. Áp dụng hệ số co giãn $K = 3.33$ để tính toán lại chính xác mốc thời gian ảo cho từng bản ghi theo sơ đồ song song/nối tiếp ở trên.
  4. Ghi đè cập nhật vào MongoDB.

### Bước 2: Xây dựng Backend API Phục Vụ Dữ Liệu Tích Lũy
* **Nhiệm vụ:** Thiết lập các endpoint API trong FastAPI phục vụ Frontend:
  * `GET /api/traffic/history?camera_id=xxx`: Tự động co giãn động trục thời gian dựa trên mốc dữ liệu nhỏ nhất và lớn nhất đang có trong MongoDB (Dynamic Range), trả về chuỗi dữ liệu lịch sử liên tục để vẽ biểu đồ.
  * `GET /api/traffic/average?camera_id=xxx`: Tính toán lưu lượng xe trung bình của camera đó dựa trên toàn bộ lịch sử tích lũy hiện có.
  * `GET /api/prediction/next?camera_id=xxx`: Gọi mô hình XGBoost dự báo lưu lượng 15 phút tiếp theo dựa trên 3 chu kỳ lịch sử gần nhất của camera đó.

### Bước 3: Phát Triển React Frontend Hoàn Chỉnh
* **Nhiệm vụ:** Thiết kế giao diện Dashboard phân tích thông minh:
  * **Trang chủ Dashboard:** Chứa 3 khối KPI hiển thị: *Lưu lượng trung bình*, *Giờ cao điểm nhất* và *Kết quả dự đoán 15 phút tới của AI*.
  * **Biểu Đồ Xu Hướng Động (Line Chart):** Tự động co giãn trục X theo lượng dữ liệu thực tế đang có trong DB (từ 0.5 tiếng đến 3 tiếng tùy thuộc dữ liệu nạp vào).
  * **Bảng Phát Video Phân Tích:** Hiển thị song song các khung phát video kết quả đã qua xử lý AI (`_output.mp4`) kèm nhãn phân loại mật độ thời gian thực tương ứng (**Low / Medium / High / Heavy**).
