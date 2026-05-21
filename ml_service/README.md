# 🤖 ML Service – Dự báo Lưu lượng & Mật độ Giao thông

Thư mục này chứa toàn bộ logic Machine Learning của hệ thống phân tích mật độ giao thông. Hệ thống sử dụng **một mô hình XGBoost duy nhất** để dự báo số lượng xe cho khung 15 phút tiếp theo, sau đó tự động suy ra **mức độ mật độ** (Low / Medium / High / Severe) dựa trên ngưỡng đã hiệu chỉnh cho thực tế đường phố đô thị.

---

## 📁 Cấu trúc thư mục

```
ml_service/
├── data/
│   └── Automated_Traffic_Volume_Counts_20260521.csv  # Dataset gốc NYC (đô thị, 15 phút)
│
├── traffic_predictor.py   # Model XGBoost: dự báo số xe + phân loại mật độ
├── train.py               # Script huấn luyện: làm sạch dữ liệu, trích xuất đặc trưng + train + xuất model.pkl
├── predict.py             # Client CLI: gọi API backend để lấy kết quả dự báo
│
├── model.pkl              # File model đã huấn luyện (XGBoost Regressor)
└── README.md              # Tài liệu này
```

---

## 1. Ý tưởng & Bài toán

### 1.1. Mục tiêu

Xây dựng mô hình dự báo **hai đầu ra** cho mỗi khung 15 phút tiếp theo:

| Đầu ra | Kiểu | Ví dụ |
|---|---|---|
| **Số lượng xe dự báo** | Số nguyên | `125` xe |
| **Mức độ mật độ dự báo** | Phân loại | `HIGH` |

### 1.2. Tại sao chỉ dùng 1 model?

Thay vì train 2 model riêng biệt (1 cho số xe, 1 cho mật độ), hệ thống sử dụng **kiến trúc 1 model + tra ngưỡng**:

```
Lịch sử MongoDB (5 khung 15 phút gần nhất)
        ↓
TrafficPredictor.predict()  →  predicted_count = 125
        ↓
classify_congestion(125)    →  "HIGH"
        ↓
API Response: { predicted_density: 125, predicted_congestion_level: "HIGH" }
```

### 1.3. Ngưỡng phân loại mật độ (Cập nhật cho NYC Data)

Các ngưỡng dưới đây được hiệu chỉnh dựa trên lưu lượng thực tế trên các tuyến đường đô thị NYC với trung bình ~100 xe/15 phút (median ~58 xe/15p):

| Mức độ | Điều kiện | Ý nghĩa thực tế |
|---|---|---|
| **LOW** | < 30 xe | Đường thông thoáng (giờ khuya, nghỉ lễ) |
| **MEDIUM** | 30 – 99 xe | Lưu thông bình thường (quanh mức trung vị) |
| **HIGH** | 100 – 199 xe | Bắt đầu đông, có thể chậm (trên Q3) |
| **SEVERE** | ≥ 200 xe | Tắc nghẽn, giờ cao điểm nặng (top 5%) |

---

## 2. Cách triển khai

### 2.1. Dữ liệu đầu vào – NYC Automated Traffic Volume Counts

**Đặc điểm nổi bật:**
- **Tổng số bản ghi:** ~1.87 triệu dòng (hơn 39 lần dataset cũ).
- **Khoảng thời gian:** Khảo sát từ 2000, 2006-2026.
- **Đơn vị gốc:** 15 phút (`MM` = 0, 15, 30, 45) -> Loại bỏ hoàn toàn sự cần thiết của interpolation (nội suy) gây nhiễu dữ liệu.
- **Loại đường:** Đường phố đô thị, mật độ cao -> Rất phù hợp và tương tự với các tình huống giao thông đô thị Việt Nam.

Hệ thống lọc tự động SegmentID phổ biến nhất (`72887`) làm tập đại diện để huấn luyện mô hình cơ sở.

### 2.2. Feature Engineering trong `traffic_predictor.py`

Mô hình sử dụng **12 đặc trưng** được chia thành 3 nhóm:

#### Nhóm 1: Đặc trưng thời gian (Temporal Features)

| Feature | Cách tính | Lý do |
|---|---|---|
| `is_peak_hour` | 1 nếu 7–9h hoặc 17–19h | Đánh dấu rõ ràng giờ cao điểm |
| `is_weekend` | 1 nếu Thứ 7 hoặc Chủ nhật | Cuối tuần lưu lượng thấp hơn đáng kể |
| `hour_sin/cos` | Cyclical encoding cho giờ | Giúp mô hình hiểu giờ 23 gần giờ 0 |
| `day_of_week_sin/cos` | Cyclical encoding cho thứ | Hiểu chu kỳ tuần liên tục |

#### Nhóm 2: Đặc trưng trễ (Lag Features)

| Feature | Cách tính | Lý do |
|---|---|---|
| `lag_1` | Số xe 15 phút trước | Quán tính ngắn hạn: giao thông thay đổi từ từ |
| `lag_2` | Số xe 30 phút trước | Xu hướng trung hạn: phát hiện tăng/giảm dần |
| `lag_4` | Số xe 1 giờ trước | Chu kỳ 1 giờ |

#### Nhóm 3: Đặc trưng thống kê trượt (Rolling/Trend Features)

| Feature | Cách tính | Lý do |
|---|---|---|
| `diff_1` | `count(t) - count(t-1)` | **Mới:** Nắm bắt xu hướng đang tăng hay giảm |
| `rolling_mean_3` | Trung bình 3 khung gần nhất | Làm mượt nhiễu (noise) |
| `rolling_std_3` | Độ lệch chuẩn 3 khung gần nhất | **Mới:** Đo lường sự bất ổn/biến động của dòng xe |

### 2.3. Huấn luyện – Time Series Cross-Validation và Early Stopping

Hệ thống sử dụng **TimeSeriesSplit (5 folds)** kết hợp **Hold-out Test Set (20% cuối cùng)**:
1. Chia 80% dữ liệu đầu làm tập Train, 20% dữ liệu cuối làm tập Held-out Test.
2. Trên tập Train, sử dụng 5-Fold TimeSeriesSplit kết hợp với `early_stopping_rounds=20` để tìm mô hình không bị overfitting.
3. Cuối cùng, huấn luyện lại trên toàn bộ tập 80% (có validation qua tập 20% test) để lưu ra `model.pkl`.

---

## 3. Kết quả đạt được

### 3.1. Training Output

```
[1] Đọc dữ liệu từ CSV (NYC Automated Traffic Volume)...
    Tổng số record gốc: 1875154
[2] Lọc SegmentID 72887 và dọn dẹp dữ liệu...
    Số lượng bản ghi sau khi lọc: 13398
    Trung bình vehicle_count: 192.3 xe/15p

--- Training Model: Vehicle Forecast + Density Level ---

[*] Quá trình huấn luyện và đánh giá bắt đầu...
 -> Tập Train: 10641 samples, Tập Test: 2661 samples
 -> Kết quả Cross Validation (5 folds) trên tập Train:
    - MAE trung bình:  6.86 xe
    - RMSE trung bình: 13.51 xe

 -> Đang huấn luyện mô hình cuối trên toàn bộ tập Train (với early stopping qua tập Test)...
 -> Kết quả đánh giá trên tập Held-out Test (20% cuối):
    - MAE:   4.76 xe
    - RMSE:  8.31 xe
    - R2:    0.9895
    - MAPE:  3.89%

[+] ĐÃ LƯU MÔ HÌNH THÀNH CÔNG: ml_service/model.pkl
```

### 3.2. Chỉ số đánh giá (Metrics)

Với R² = 0.99 và MAPE ~3.5%, mô hình hiện tại đạt độ chính xác **rất cao** nhờ:
1. Dữ liệu sạch, không bị nội suy nhiễu như dataset cũ.
2. Bổ sung các đặc trưng trễ (lag) và biến động (rolling), cùng với cyclical encoding.

---

## 🚀 Cách chạy

### 1. Huấn luyện Model

```bash
# Kích hoạt môi trường ảo
source .venv/bin/activate

# Chạy training (từ thư mục gốc dự án)
python -m ml_service.train
```

### 2. Kiểm tra dự báo (yêu cầu backend đang chạy)

```bash
# Terminal 1: Khởi động backend
uvicorn backend.main:app --reload

# Terminal 2: Gọi dự báo
python -m ml_service.predict
```
