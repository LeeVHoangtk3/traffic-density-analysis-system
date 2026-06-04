# 🤖 ML Service – Dự Báo Lưu Lượng
Tài liệu này đặc tả toàn bộ kiến trúc học máy (Machine Learning) cốt lõi của **Hệ Thống Phân Tích Mật Độ Giao Thông**. 

Hệ thống kết hợp sức mạnh của **Học máy giám sát (XGBoost Regressor)** để dự báo lưu lượng, **Học máy không giám sát (K-Means Clustering)** để tự thích ứng ngưỡng ùn tắc động.

---

## 📁 1. Cây Thư Mục Chi Tiết (Directory Tree)
Cơ cấu thư mục được sắp xếp khoa học, tinh giản tối đa ở thư mục gốc để tránh xung đột đường dẫn import nội bộ:

```
ml_service/
├── data/
│   └── junction_pivot_clean.csv        # [Đầu ra Task 1] Dữ liệu 3 ngã rẽ đã sạch & xoay trục ngang
├── model/
│   ├── model.pkl                       # Trọng số mô hình cũ (Single-direction)
│   ├── model_straight.pkl              # [Đầu ra Task 3] Mô hình XGBoost dự báo đi thẳng
│   ├── model_left.pkl                  # [Đầu ra Task 3] Mô hình XGBoost dự báo rẽ trái
│   └── model_right.pkl                 # [Đầu ra Task 3] Mô hình XGBoost dự báo rẽ phải
├── helpers/                            # Thư mục lưu trữ các tệp thử nghiệm & phụ trợ
│   ├── predict.py                      # CLI test nhanh gọi API dự báo của backend
│   ├── synthesize_data.py              # Script sinh dữ liệu giả lập (mock data) đô thị VN
│   ├── augment_data.py                 # Script tăng cường đặc trưng dữ liệu (data augmentation)
│   ├── preprocess_multi_junction.py    # Bản sao lưu tiền xử lý cũ
│   └── data_evaluation.ipynb           # Jupyter Notebook phân tích & đánh giá chất lượng dữ liệu
├── preprocess.py                       # [Active Task 1] Tiền xử lý volume thô đa ngã rẽ (138, 72887, 83624)
├── traffic_predictor.py                # [Active Task 2] Định nghĩa lớp đặc trưng & dự báo AI TrafficPredictor
├── train.py                            # [Active Task 3] Huấn luyện 3 mô hình XGBoost hợp nhất đa nút giao
├── evaluate.py                         # [Active Task 9] Script đánh giá sai số học thuật (MAE/RMSE/MAPE) & vẽ đồ thị
└── README.md                           # Tài liệu đặc tả kỹ thuật này
```

---

## 📝 2. Đặc Tả Chi Tiết Các Tệp Tin (File Specifications)

### 2.1. Nhóm Tiền Xử Lý & Dữ Liệu
#### 🚀 [preprocess.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/preprocess.py)
* **Chức năng:** Tải tệp dữ liệu thô lớn `Automated_Traffic_Volume_Counts_20260521.csv` (286MB), tiến hành ép kiểu số lượng, làm tròn mốc 15 phút, giải quyết trùng lặp logic, lọc trích xuất 3 mã `SegmentID` điểm (138, 72887, 83624), ánh xạ các hướng di chuyển thô sang làn chuẩn (`vol_straight`, `vol_left`, `vol_right`) và xuất ra bảng ngang hợp nhất.
* **Đầu vào:** `data/ml/Automated_Traffic_Volume_Counts_20260521.csv`.
* **Đầu ra:** `ml_service/data/junction_pivot_clean.csv`.

---

### 2.2. Nhóm Học Máy Dự Báo (ML Core Predictors)
#### 🚀 [traffic_predictor.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/traffic_predictor.py)
* **Chức năng:** Định nghĩa lớp `TrafficPredictor` chịu trách nhiệm thiết lập ma trận đặc trưng đầu vào và chạy dự báo. Lớp này hỗ trợ phân tách đặc trưng chuỗi thời gian độc lập cho từng `segment_id` (tránh rò rỉ dữ liệu).
* **Đầu vào:** DataFrame chứa cột thời gian `timestamp` và `vehicle_count`.
* **Đầu ra:** DataFrame đã được kỹ nghệ đặc trưng hoàn chỉnh, sẵn sàng truyền vào XGBoost.

#### 🚀 [train.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/train.py)
* **Chức năng:** Tiến hành tải dữ liệu xoay trục, lặp qua 3 làn di chuyển (`straight`, `left`, `right`), phân tách tập Train/Test theo mốc thời gian cứng (Chronological Split: 80% thời gian đầu làm Train, 20% thời gian sau làm Test), thực thi huấn luyện song song 3 mô hình XGBoost Regressor độc lập, in báo cáo sai số và đóng gói tệp tin trọng số.
* **Đầu vào:** `ml_service/data/junction_pivot_clean.csv`.
* **Đầu ra:** 3 tệp mô hình `model_straight.pkl`, `model_left.pkl`, `model_right.pkl` lưu tại `ml_service/model/`.

---


#### 🚀 [evaluate.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/evaluate.py) *(Thiết kế mới Task 9)*
* **Chức năng:** Chạy đánh giá khoa học chuyên sâu độc lập trên tập Test (từ ngày 2025-01-01 trở đi), tính toán các chỉ số thống kê MAE, RMSE, MAPE. Đồng thời sử dụng `matplotlib` trích xuất 100 bước thời gian liên tục vẽ đồ thị trực quan so sánh **Thực tế (Actual) vs Dự báo (Predicted)**.
* **Đầu vào:** `junction_pivot_clean.csv` và 3 tệp mô hình pkl.
* **Đầu ra:** Tệp chỉ số `training_metrics.json` và 3 hình ảnh biểu đồ chuỗi thời gian `.png` lưu tại `ml_service/data/`.

---

### 2.5. Nhóm Công Cụ Phụ Trợ & Thử Nghiệm (`ml_service/helpers/`)
Các tệp tin trong thư mục này phục vụ việc phát sinh dữ liệu thử nghiệm, kiểm thử nhanh các dịch vụ APIs và thực hiện phân tích khám phá dữ liệu (EDA):

#### 🚀 [predict.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/helpers/predict.py)
* **Chức năng:** Tệp tin kịch bản CLI độc lập dùng để kiểm thử nhanh tính hoạt động của REST APIs Backend. Tiến trình sẽ trực tiếp gửi HTTP GET request đến endpoint `/predict-next` của FastAPI kèm tham số `camera_id`.
* **Đầu vào:** Biến môi trường cấu hình `TRAFFIC_API_URL` và `TRAFFIC_CAMERA_ID`.
* **Đầu ra:** Bản ghi thông số trạng thái lưu lượng in ra console.

#### 🚀 [synthesize_data.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/helpers/synthesize_data.py)
* **Chức năng:** Script tạo dữ liệu lưu lượng giao thông giả lập chất lượng cao cực kỳ sinh động. Thuật toán áp dụng hệ số lưu thông đô thị Việt Nam thực tế theo giờ (đỉnh điểm sáng 7-9h, chiều 17-19h, thấp điểm ban đêm 23-5h), thiết lập công suất đỉnh và tỷ lệ làn đường riêng biệt cho từng ngã ba/ngã tư, đồng thời tích hợp 5% xác suất sự cố giao thông ngẫu nhiên hoặc thời tiết mưa bão làm giảm volume để nâng cao tính đa dạng của dữ liệu.
* **Đầu vào:** Mốc thời gian bắt đầu và kết thúc cấu hình sinh.
* **Đầu ra:** Tệp dữ liệu giả lập xoay trục ngang `junction_pivot_clean.csv`.

#### 🚀 [augment_data.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/helpers/augment_data.py)
* **Chức năng:** Thực hiện kỹ thuật Tăng Cường Dữ Liệu (Data Augmentation) cho dữ liệu chuỗi thời gian dạng bảng. Script áp dụng phép thêm nhiễu trắng ngẫu nhiên (Gaussian Noise) và dịch chuyển thời gian để làm đa dạng mẫu huấn luyện, tăng độ bền bỉ (robustness) và hạn chế tối đa hiện tượng Overfitting khi huấn luyện mô hình XGBoost.
* **Đầu vào:** Bảng dữ liệu giao thông ngang gốc.
* **Đầu ra:** Tập dữ liệu mở rộng đã được nhân bản và tăng cường đặc trưng nhiễu.

#### 🚀 [preprocess_multi_junction.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/helpers/preprocess_multi_junction.py)
* **Chức năng:** Phiên bản tiền xử lý đa ngã rẽ nâng cấp dự phòng. Cung cấp các giải thuật làm đầy dữ liệu khuyết nâng cao (Bổ khuyết thời gian liên tục dùng `pd.date_range()` và nội suy mượt tuyến tính `interpolate('time')`) để xử lý các phân khúc dữ liệu camera bị mất kết nối hoặc rỗng bản ghi trong quá khứ.
* **Đầu vào:** Dữ liệu thô `Automated_Traffic_Volume_Counts_20260521.csv`.
* **Đầu ra:** File dữ liệu xoay trục ngang hoàn chỉnh.

#### 🚀 [data_evaluation.ipynb](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/helpers/data_evaluation.ipynb)
* **Chức năng:** Tệp tin Jupyter Notebook dùng cho việc Phân tích khám phá dữ liệu chuyên sâu (Exploratory Data Analysis - EDA). Notebook trực quan hóa phân phối phân khúc xe, biểu đồ tương quan thời gian, và kiểm định chất lượng nội suy chia bin dữ liệu của xa lộ Mỹ Interstate 94 trước khi nhân hệ số scale factor Việt Nam đô thị.
* **Đầu vào:** File dữ liệu gốc hourly Metro Interstate.
* **Đầu ra:** Biểu đồ xu hướng, biểu đồ hộp (Boxplot) và các thống kê phân phối trực quan.

---


## 🧮 3. Các Công Thức Toán Học Nền Tảng (Mathematical Formulation)

### 3.1. Kỹ Nghệ Đặc Trưng Chuỗi Thời Gian
Để mã hóa mốc thời gian ngày đêm một cách liên tục (tránh khoảng đứt gãy giữa 23:45 của ngày hôm trước và 00:00 của ngày hôm sau), hệ thống áp dụng phép biến đổi lượng giác vòng tròn:
$$\text{hour\_sin} = \sin\left(\frac{2\pi \times \text{hour}}{24}\right)$$
$$\text{hour\_cos} = \cos\left(\frac{2\pi \times \text{hour}}{24}\right)$$
*(Với `hour` là số thực đại diện cho mốc 24 tiếng, ví dụ mốc 14h15 được quy đổi thành 14.25)*.

---

### 3.2. Phân Cụm Ngưỡng Mật Độ Động (K-Means Clustering)
Áp dụng phân cụm một chiều trên dữ liệu xe lịch sử $V = [v_1, v_2, ..., v_N]^T$ với số cụm $K=4$ để tìm ra 4 tâm cụm (centroids) đại diện cho 4 mức độ:
$$C_0 < C_1 < C_2 < C_3 \quad (\text{tương ứng với Low, Medium, High, Heavy})$$

Ranh giới quyết định (Decision Boundaries) giữa các mức độ được xác định bằng trung điểm giữa hai tâm cụm liên tiếp:
* **Ngưỡng từ Thấp lên Trung bình:** $T_1 = \frac{C_0 + C_1}{2}$
* **Ngưỡng từ Trung bình lên Cao:** $T_2 = \frac{C_1 + C_2}{2}$
* **Ngưỡng từ Cao lên Ùn tắc nghiêm trọng:** $T_3 = \frac{C_2 + C_3}{2}$

---


* **Mean Absolute Error (MAE):** Đo lệch trung bình tuyệt đối số lượng xe vật lý:
  $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$$
* **Root Mean Square Error (RMSE):** Phạt nặng các sai số lệch lớn đột biến để đo độ ổn định:
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$$
* **Mean Absolute Percentage Error (MAPE):** Sai số phần trăm tương đối (loại bỏ các mốc thực tế $y_i = 0$):
  $$\text{MAPE} = \frac{100\%}{N} \sum_{i=1}^N \left| \frac{y_i - \hat{y}_i}{y_i} \right|$$

---

## 🛠️ 4. Thư Viện Yêu Cầu & Cài Đặt (Dependencies)

Để chạy trọn vẹn ML service, môi trường Python yêu cầu các thư viện chính sau:
- **Học máy & Toán học:** `xgboost`, `scikit-learn`, `pandas`, `numpy`, `joblib`
- **Cơ sở dữ liệu:** `pymongo`
- **Vẽ đồ thị:** `matplotlib`, `seaborn`

Cài đặt nhanh toàn bộ thư viện bằng pip:
```powershell
pip install xgboost scikit-learn pandas numpy joblib pymongo matplotlib seaborn
```

---

## 🚀 5. Quy Trình Vận Hành & Khởi Chạy ML Pipeline

Nhóm phát triển thực thi quy trình theo các bước tuần tự sau:

1. **Bước 1: Tiền xử lý dữ liệu thô và xoay trục đa nút giao:**
   ```powershell
   python -m ml_service.preprocess
   ```
2. **Bước 2: Huấn luyện hệ thống 3 mô hình XGBoost:**
   ```powershell
   python -m ml_service.train
   ```
3. **Bước 3: Chạy phân cụm K-Means cập nhật ngưỡng mật độ vào MongoDB:**
   ```powershell
   python -m ml_service.density_cluster
   ```
4. **Bước 4: Chạy đánh giá học thuật và xuất đồ thị thực nghiệm tốt nghiệp:**
   ```powershell
   python -m ml_service.evaluate
   ```
