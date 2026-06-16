# 🚗 Mô-đun Phát hiện & Bám vết Phương tiện (Vehicle Detection & Tracking Module)

Mô-đun `detection` là thành phần xử lý thị giác máy tính tại biên (Edge CV Processing) trong **Hệ thống phân tích mật độ giao thông thông minh**. Mô-đun này chịu trách nhiệm thu nhận luồng video, phát hiện phương tiện bằng mô hình YOLOv9 tùy chỉnh, bám vết đa đối tượng bằng thuật toán ByteTrack, đếm xe qua vùng quan tâm (ROI), và đẩy dữ liệu sự kiện bất đồng bộ về Backend API.

---

## 📂 Cấu trúc thư mục chi tiết (Directory Structure)

Dưới đây là cấu trúc chi tiết của mô-đun `detection`:

```
detection/
├── configs_cameras/               # Chứa các file cấu hình đa giác ROI cho từng camera
│   ├── cam01.json
│   ├── cam02.json
│   └── cam03.json
├── engine/                        # Lõi xử lý thị giác máy tính và lô-gích đếm xe
│   ├── __init__.py
│   ├── counter.py                 # Bộ tích lũy đếm số lượng xe cục bộ theo lớp
│   ├── density_estimator.py       # Ước lượng mật độ để điều khiển Frame Skip động
│   ├── detector.py                # Wrapper tích hợp mô hình YOLOv9 và tiền/hậu xử lý
│   ├── event_generator.py         # Trích xuất và định dạng dữ liệu sự kiện xe vượt vạch
│   ├── frame_processor.py         # Chuẩn hóa kích thước khung hình giữ nguyên aspect ratio
│   ├── tracker.py                 # Wrapper thuật toán bám vết đa đối tượng ByteTrack
│   └── zone_manager.py            # Quản lý vùng đa giác ROI và State Machine đếm xe
├── integration/                   # Giao tiếp với các thành phần khác ngoài biên
│   ├── __init__.py
│   └── publisher.py               # Hàng đợi đẩy sự kiện HTTP bất đồng bộ (Thread-safe)
├── pro_models/                    # Thư mục chứa trọng số mô hình YOLOv9 đã huấn luyện (.pt)
│   └── yolov9_img960_ultimate.pt
├── ultralytics_yolov9/            # Thư viện lõi YOLOv9 (kiến trúc GELAN & cơ chế PGI)
├── __init__.py
├── calibrate_zones.py             # Công cụ đồ họa OpenCV hỗ trợ vẽ đa giác ROI trực quan
├── camera_engine.py               # Trích xuất luồng video hoặc camera thời gian thực
└── main.py                        # Điểm khởi chạy chính của toàn bộ Pipeline biên
```

---

## 📄 Chi tiết chức năng từng tệp tin (File Functions)

### 1. File điều phối chính
* **[main.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/main.py)**: Điểm khởi chạy toàn bộ luồng xử lý. File này chịu trách nhiệm nạp các cấu hình hệ thống từ biến môi trường, khởi tạo các thực thể xử lý, duy trì vòng lặp đọc khung hình và điều phối hoạt động giữa các mô-đun từ thu nhận, nhận dạng, bám vết, quản lý vùng đến đẩy sự kiện.

### 2. Thư mục `engine/` (Lõi xử lý CV)
* **[detector.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/detector.py)**: 
  * Nạp trọng số PyTorch của mô hình YOLOv9 tùy chỉnh.
  * Thực hiện tiền xử lý (Resize về 960x960, chuẩn hóa thang đo $[0, 1]$, chuyển đổi kênh màu BGR $\rightarrow$ RGB).
  * Chạy suy luận (Inference), áp dụng cơ chế lọc tin cậy riêng biệt (Per-class threshold: `motorcycle = 0.25` và các xe khác = `0.40`).
  * Thực hiện NMS (Non-Maximum Suppression) để loại bỏ các bounding box trùng nhau.
  * Tách biệt tỷ lệ co giãn trục X và Y độc lập để trả tọa độ về khung hình gốc mà không bị lệch.
  * Giải phóng bộ nhớ VRAM đồ họa định kỳ (`empty_cache`).
* **[tracker.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/tracker.py)**: 
  * Đóng vai trò wrapper cho thuật toán **ByteTrack** thông qua thư viện `supervision`.
  * Nhận các bounding box từ detector, sử dụng bộ lọc Kalman Filter để ước lượng trạng thái chuyển động vật lý và Hungarian Algorithm để liên kết quỹ đạo qua từng frame.
  * Sử dụng thuộc tính `lost_track_buffer = 90` để duy trì ID xe khi bị khuất tạm thời.
* **[zone_manager.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/zone_manager.py)**: 
  * Đọc các điểm đa giác từ camera cấu hình và tạo đối tượng đa giác thông qua thư viện `shapely.geometry.Polygon`.
  * Xác định vị trí xe so với đa giác bằng điểm neo đáy bánh xe và kiểm tra tính thuộc vùng đa giác (Ray Casting).
  * Quản lý State Machine đếm xe: `Outside` $\rightarrow$ `Inside` (passed_trigger=True) $\rightarrow$ `Exit` (is_counted=True).
  * Giải phóng bộ nhớ vết bám của các xe đã rời khung hình camera.
* **[density_estimator.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/density_estimator.py)**: 
  * Sử dụng hàng đợi trượt `collections.deque` với kích thước `30` để lưu vết số lượng xe hiện diện tức thời trong 30 frame gần nhất.
  * Tính toán giá trị trung bình để xác định mức độ mật độ hiện tại (`LOW`, `MEDIUM`, `HIGH`) phục vụ cơ chế bỏ qua khung hình động.
* **[counter.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/counter.py)**: 
  * Tích lũy số lượng xe theo từng lớp đối tượng (`car`, `motorcycle`, `bus`, `truck`) trong phiên chạy hiện tại.
* **[frame_processor.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/frame_processor.py)**: 
  * Chuẩn hóa kích thước khung hình về bề rộng `960px` dùng OpenCV, tính toán tỷ lệ co giãn để bảo toàn hình dạng tự nhiên.
* **[event_generator.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/engine/event_generator.py)**: 
  * Tạo chuỗi JSON sự kiện chuẩn chứa mã UUID duy nhất, mã camera, mã track, phân loại xe, độ tin cậy và mốc thời gian dạng ISO 8601.

### 3. Thư mục `integration/` & Tệp tiện ích bổ trợ
* **[publisher.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/integration/publisher.py)**:
  * Triển khai mô hình Producer-Consumer sử dụng một luồng phụ chạy ngầm (Daemon Thread) độc lập và hàng đợi `queue.Queue`.
  * Luồng chính (Producer) đẩy sự kiện vào hàng đợi bất đồng bộ mà không cần đợi phản hồi HTTP.
  * Luồng phụ (Consumer) lấy sự kiện ra và gửi tuần tự đến Backend API bằng phương thức HTTP POST, có cơ chế kiểm soát lỗi kết nối và tự động loại bỏ sự kiện cũ khi hàng đợi bị tràn (>200 events).
* **[camera_engine.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/camera_engine.py)**:
  * Trình điều khiển camera sử dụng OpenCV, xử lý đọc luồng khung hình, tính toán thời gian trễ của tệp video và quản lý giải phóng camera khi tắt hệ thống.
* **[calibrate_zones.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/detection/calibrate_zones.py)**:
  * Công cụ GUI cho phép người dùng click chuột vẽ đa giác ROI trực quan trên màn hình. Tọa độ các đỉnh sẽ tự động được ghi lại và cập nhật thẳng vào tệp cấu hình JSON tương ứng trong thư mục `configs_cameras/`.

---

## 🔄 Quy trình hoạt động chi tiết (Execution Flow & Workflows)

Hoạt động của luồng xử lý biên được chia thành 4 giai đoạn cụ thể:

```
[ Giai đoạn 1: Khởi tạo ]
       │
       ▼ (Nạp cấu hình, camera, mô hình YOLOv9)
[ Giai đoạn 2: Vòng lặp chính ] ◄─────────────────────────────────┐
       │                                                          │
       ▼ (Đọc khung hình & Kiểm tra Frame Skip thích ứng)         │
[ Trích xuất Frame ] ───► [ Bỏ qua? ] ───► Có ────────────────────┤
       │ Không                                                    │
       ▼                                                          │
[ Khớp đặc trưng mô hình YOLOv9 ]                                 │
       │                                                          │
       ▼ (Lọc hộp giới hạn & NMS)                                 │
[ Bám vết ByteTrack (Kalman Filter) ]                             │
       │                                                          │
       ▼                                                          │
[ Kiểm tra đa giác ROI (Ray Casting) ]                            │
       │                                                          │
       ├─► [ Đi vào ROI ] ──► Kích hoạt passed_trigger = True     │
       │                                                          │
       └─► [ Đi ra khỏi ROI ] ──► Chốt đếm is_counted = True      │
             │                                                    │
             ▼                                                    │
      [ Giai đoạn 3: Sinh & Gửi Event ]                           │
             │                                                    │
             ▼ (Đẩy vào Queue)                                    │
      [ Background Thread gửi HTTP ] ──► FastAPI Backend          │
             │                                                    │
             └────────────────────────────────────────────────────┘
```

### 1. Giai đoạn Khởi tạo (Startup Phase)
* Hệ thống phân tích đối số CLI hoặc biến môi trường để xác định `camera_id` (ví dụ `cam01`).
* Đọc tệp cấu hình đa giác ROI tại `configs_cameras/cam01.json`.
* Khởi tạo `CameraEngine` để kết nối tới tệp video hoặc camera stream.
* Tải mô hình YOLOv9 lên thiết bị phần cứng (ưu tiên GPU CUDA, fallback về CPU).
* Khởi chạy luồng chạy ngầm của `EventPublisher` để sẵn sàng nhận hàng đợi sự kiện.

### 2. Giai đoạn Vòng lặp chính (Main Processing Loop)
* **Bước 1: Điều phối Frame Skip**: Luồng chính đọc khung hình tiếp theo từ `CameraEngine`. Nếu chế độ bất đồng bộ kích hoạt, hệ thống sẽ tham chiếu mức độ mật độ gần nhất để quyết định xem có bỏ qua (skip) suy luận AI trên khung hình này hay không.
* **Bước 2: Phát hiện đối tượng (Detection)**: Khung hình được đưa qua `FrameProcessor` để resize về 960x960. `Detector` chạy suy luận trên GPU để tìm ra tọa độ bounding box phương tiện, sau đó áp dụng thuật toán NMS để lọc bớt các hộp trùng nhau và tính toán tọa độ gốc chính xác.
* **Bước 3: Bám vết chuyển động (Tracking)**: Các tọa độ nhận dạng được gửi vào `Tracker`. Thuật toán ByteTrack sẽ cập nhật trạng thái ước lượng Kalman Filter, giải thuật Hungarian thực hiện khớp nối ID liên tục qua các khung hình.
* **Bước 4: Đánh giá Vùng đa giác & State Machine**:
  * Các xe đang hoạt động được cập nhật tọa độ điểm neo bánh xe vào `ZoneManager`.
  * Nếu điểm neo đi vào bên trong đa giác ROI $\rightarrow$ Đánh dấu trạng thái xe là `passed_trigger = True`.
  * Nếu điểm neo đi ra ngoài đa giác $\rightarrow$ Chốt đếm trạng thái xe là `is_counted = True`.
  * Khi xe bị mất dấu (thoát hẳn khỏi khung hình), `cleanup_memory` sẽ tìm các xe đã có trạng thái `is_counted = True` để kích hoạt sự kiện đếm.

### 3. Giai đoạn Sinh và Gửi sự kiện (Event Publishing Phase)
* Đối với mỗi xe đủ điều kiện đếm, `EventGenerator` sinh ra gói tin JSON sự kiện.
* Gói tin được chuyển đến `EventPublisher.publish()`. Luồng chính thực hiện thao tác đẩy bất đồng bộ vào `queue.Queue` trong vòng dưới `0.1 ms` và lập tức quay lại xử lý khung hình tiếp theo.
* Ở chế độ nền, Background Thread liên tục lấy sự kiện từ hàng đợi ra, gọi lệnh `requests.post()` để gửi tuần tự về API `/detection` của FastAPI Backend.

### 4. Giai đoạn Dọn dẹp & Giải phóng (Shutdown Phase)
* Khi luồng video kết thúc hoặc người dùng nhấn phím `Q`, hệ thống thoát khỏi vòng lặp chính.
* Giải phóng đối tượng Camera, lưu và đóng luồng ghi video đầu ra.
* Đóng các file log CSV cảnh báo (`AlertLogger`).
* Luồng ngầm gửi sự kiện tự động kết thúc nhờ thuộc tính `daemon=True`.

---

## 📐 Chi tiết giải thuật & Công thức toán học (Algorithms Deep-Dive)

### 1. Giải thuật Point-in-Polygon (Ray Casting)
Để kiểm tra một điểm bánh xe $P(x_0, y_0)$ có nằm trong vùng đa giác ROI $\mathcal{P}$ hay không, hệ thống sử dụng thuật toán bắn tia (Ray Casting). 
* Vẽ một tia nằm ngang xuất phát từ $P$ hướng sang phía bên phải ($x \rightarrow +\infty$).
* Đếm số lần tia này cắt các cạnh của đa giác. Theo định lý đường cong Jordan:
  * Nếu số giao điểm là **số lẻ**: Điểm nằm **bên trong** đa giác.
  * Nếu số giao điểm là **số chẵn**: Điểm nằm **bên ngoài** đa giác.

Công thức xác định tia nằm ngang từ $P(x_0, y_0)$ cắt cạnh đa giác nối giữa hai đỉnh liên tiếp $V_i(x_i, y_i)$ và $V_{i+1}(x_{i+1}, y_{i+1})$:
1. Tung độ $y_0$ phải nằm trong khoảng giữa hai đỉnh của cạnh:
$$(y_i > y_0) \neq (y_{i+1} > y_0)$$
2. Hoành độ giao điểm của cạnh với đường thẳng $y = y_0$ phải nằm bên phải điểm $x_0$:
$$x_0 < x_i + \frac{(y_0 - y_i) \cdot (x_{i+1} - x_i)}{y_{i+1} - y_i}$$

---

### 2. Ước lượng trạng thái (Kalman Filter) & Khớp quỹ đạo (Hungarian Algorithm)
ByteTrack sử dụng bộ lọc Kalman Filter tuyến tính để dự đoán tọa độ chuyển động của hộp giới hạn.
Vector trạng thái 8 chiều tại thời điểm $t$:
$$x_t = [x_c, y_c, a, h, v_{xc}, v_{yc}, v_a, v_h]^T$$
Trong đó $(x_c, y_c)$ là tâm hộp, $a = w/h$ là tỷ lệ khung hình, $h$ là chiều cao, và các biến $v$ là vận tốc tương ứng.

* **Bước 1 (Prediction)**:
$$\hat{x}_{t|t-1} = F \hat{x}_{t-1|t-1}$$
$$P_{t|t-1} = F P_{t-1|t-1} F^T + Q$$
* **Bước 2 (Association)**:
Tính toán khoảng cách IoU (Intersection over Union) giữa các bounding box phát hiện và các vết bám dự đoán từ Kalman Filter. Ma trận chi phí liên kết $C$:
$$C_{ij} = 1 - \text{IoU}(D_i, T_j)$$
Giải thuật Hungarian tối ưu hóa ma trận phân bổ nhị phân $X$ để cực tiểu hóa tổng chi phí:
$$\min \sum_{i} \sum_{j} C_{ij} X_{ij}$$

---

### 3. Giải thuật Dynamic Frame Skip thích ứng
Được điều khiển động dựa trên giá trị mật độ xe trung bình tức thời $D_{avg}$ trong cửa sổ trượt $W$:
$$D_{avg} = \frac{1}{|W|} \sum_{i \in W} N_{tracks}^{(i)}$$

Quy tắc chuyển đổi số khung hình bỏ qua suy luận $S_{skip}$:
$$S_{skip} = \begin{cases} 
5 & \text{nếu } D_{avg} < 5 \text{ (LOW)} \\
3 & \text{nếu } 5 \le D_{avg} < 15 \text{ (MEDIUM)} \\
1 & \text{nếu } D_{avg} \ge 15 \text{ (HIGH)}
\end{cases}$$

Khi phát hiện **Spike** (đột biến số lượng xe máy đi vào đột ngột):
$$\text{Spike} = \text{True} \quad \text{nếu} \quad N_{tracks}^{(t)} \ge 1.5 \cdot D_{avg} \quad \text{và} \quad N_{tracks}^{(t)} \ge 5$$
Lúc này, hệ thống ép buộc $S_{skip} = 0$ ngay lập tức để chuyển sang quét toàn bộ khung hình, đảm bảo tính ổn định tối đa của quỹ đạo.
