# Danh Sách Các Vấn Đề Hiện Tại & Khoảng Trống Mã Nguồn (Pending Tasks & Gaps)

Tài liệu này ghi nhận chi tiết hiện trạng mã nguồn thực tế của dự án so với bản thiết kế mới của chúng ta. Nó chỉ rõ những điểm chưa được sửa đổi, các lỗi cấu trúc hiện tại và lộ trình các việc cần làm ngay để đưa hệ thống hoạt động đúng theo kế hoạch.

---

## 1. Hiện Trạng Mã Nguồn Thực Tế vs. Bản Thiết Kế Mới

Hiện tại, **mã nguồn thực tế của dự án vẫn đang chạy theo kiến trúc cũ**. Bản thiết kế mới về co giãn tỷ lệ và đồng bộ hóa camera mới chỉ dừng lại ở mức tài liệu định hướng (`KE_HOACH_TRIEN_KHAI_TIEP_THEO.md`).

Dưới đây là chi tiết các tệp tin chưa được cập nhật và các vấn đề tồn tại:

### 1.1. Vấn đề 1: Thuật toán Cell 8 (Time-Shifting) vẫn chạy theo logic cũ
* **Tệp tin liên quan:** 
  * [scratch/update_notebook.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/update_notebook.py) (Phần định nghĩa Cell 8)
  * [colab_run.ipynb](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/colab_run.ipynb) và [run_system.ipynb](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/run_system.ipynb)
* **Hiện trạng cũ:** 
  * Thuật toán cũ chỉ đơn giản là lấy toàn bộ detections của một camera và rải đều chúng từ `T - 180 phút` đến `T` một cách độc lập.
  * Chưa hề có logic nhận diện video xuôi (`traffic3` $\rightarrow$ `8`) và video ngược (`traffic1` $\rightarrow$ `2`).
  * Chưa có hệ số co giãn $K = 3.33$ dựa trên thời lượng thực tế của từng video nguồn.
  * Chưa đồng bộ song song dữ liệu của `cam01` & `cam02` (Đầu xuôi) và nối tiếp dữ liệu của `cam03` (Đầu ngược).

---

### 1.2. Vấn đề 2: Cơ sở dữ liệu MongoDB chưa có chuỗi thời gian đồng bộ
* **Hiện trạng cũ:** 
  * Dữ liệu nhận diện thô trong `vehicle_detections` sau khi chạy YOLO vẫn bị lệch múi giờ xa nhau do quá trình xử lý tuần tự trên Colab.
  * Chưa được cấu trúc lại theo mốc giờ ảo song song/nối tiếp $\rightarrow$ Nếu mở biểu đồ Frontend lúc này, đường đồ thị của các camera sẽ nằm ở các ngày/giờ lệch nhau hoàn toàn, không thể đối chiếu so sánh trực quan.

---

### 1.3. Vấn đề 3: Các API Backend chưa hỗ trợ thu thập dữ liệu lịch sử tích lũy
* **Tệp tin liên quan:** Các file định nghĩa route trong thư mục `backend/api/` và `backend/services/`.
* **Hiện trạng cũ:**
  * Chưa có API `GET /api/traffic/history` hỗ trợ tự co giãn động trục thời gian dựa trên mốc dữ liệu nhỏ nhất và lớn nhất có trong DB (Dynamic Range).
  * Chưa có API `GET /api/traffic/average` để tính toán thông minh lượng xe trung bình và tìm kiếm giờ cao điểm tự động từ dữ liệu tích lũy phục vụ Frontend Widgets.

---

### 1.4. Vấn đề 4: React Frontend UI đang sử dụng dữ liệu tĩnh/mockup cũ
* **Tệp tin liên quan:** Thư mục [frontend/src/](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/frontend/src)
* **Hiện trạng cũ:**
  * Giao diện React Frontend hiện nay vẫn đang hiển thị các thẻ KPI và biểu đồ dựa trên cấu trúc cũ (không hiển thị dữ liệu lịch sử trải dài động).
  * Chưa có Playlist động kết nối 8 video nguồn (`traffic1` $\rightarrow$ `8`).
  * Các widget hiển thị *Lưu lượng xe trung bình*, *Giờ cao điểm* và *AI prediction card* chưa được lập trình để kết nối trực tiếp với các API tích lũy của Backend.

---

## 2. Danh Sách Hành Động Cần Triển Khai (Action Items)

Để lấp đầy các khoảng trống kỹ thuật trên, chúng ta cần triển khai code theo trình tự ưu tiên sau:

```
[LỘ TRÌNH SỬA CODE THỰC TẾ]
       |
       +---> ƯU TIÊN 1: Nâng cấp Cell 8 trong 'scratch/update_notebook.py'
       |                và chạy tái tạo (regenerate) 2 file notebook.
       |
       +---> ƯU TIÊN 2: Viết các API Backend hỗ trợ Dynamic Range History
       |                và tính toán xe trung bình tích lũy.
       |
       +---> ƯU TIÊN 3: Lập trình giao diện React Frontend hoàn chỉnh
                        (Line Chart động, Analytics Widgets, Video Playlist).
```

### 📋 Nhiệm vụ chi tiết của Ưu tiên 1 (Lập trình Cell 8 mới):
Chúng ta sẽ thay thế đoạn script Python tạo file `simulate_history_colab.py` trong `scratch/update_notebook.py` bằng một thuật toán thông minh mới:
1. **Lấy danh sách bản ghi:** Truy vấn toàn bộ `vehicle_detections` từ MongoDB.
2. **Phân tích nguồn:** Tự động phát hiện tên video nguồn (qua logic phân nhóm hoặc timestamp thô tăng dần).
3. **Phân chia mốc thời gian ảo:**
   * Gán mốc song song cho Cam 1 & 2 (08:00 - 09:53) co giãn theo tỷ lệ video 3 $\rightarrow$ 8.
   * Gán mốc nối tiếp cho Cam 3 (09:53 - 11:00) co giãn theo tỷ lệ video 1 $\rightarrow$ 2.
4. **Cập nhật MongoDB:** Ghi đè timestamp mới thành công.
