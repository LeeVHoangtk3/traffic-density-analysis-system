# 🤖 ML Service – Dự báo Lưu lượng & Mật độ Giao thông

Thư mục này chứa toàn bộ logic Machine Learning của hệ thống phân tích mật độ giao thông. Hệ thống sử dụng **một mô hình XGBoost duy nhất** để dự báo số lượng xe cho khung 15 phút tiếp theo, sau đó tự động suy ra **mức độ mật độ** (Low / Medium / High / Severe) dựa trên ngưỡng đã hiệu chỉnh cho thực tế đô thị Việt Nam.

---

## 📁 Cấu trúc thư mục

```
ml_service/
├── data/
│   └── Metro_Interstate_Traffic_Volume.csv   # Dataset gốc (48,204 bản ghi theo giờ)
│
├── traffic_predictor.py   # Model XGBoost: dự báo số xe + phân loại mật độ
├── train.py               # Script huấn luyện: biến đổi dữ liệu + train + xuất model.pkl
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
| **Số lượng xe dự báo** | Số nguyên | `491` xe |
| **Mức độ mật độ dự báo** | Phân loại | `HIGH` |

### 1.2. Tại sao chỉ dùng 1 model?

Thay vì train 2 model riêng biệt (1 cho số xe, 1 cho mật độ), hệ thống sử dụng **kiến trúc 1 model + tra ngưỡng**:

```
Lịch sử MongoDB (5 khung 15 phút gần nhất)
        ↓
TrafficPredictor.predict()  →  predicted_count = 491
        ↓
classify_congestion(491)    →  "HIGH"
        ↓
API Response: { predicted_density: 491, predicted_congestion_level: "HIGH" }
```

**Lý do:**
- **Đơn giản hơn:** Chỉ cần bảo trì và retrain 1 model duy nhất.
- **Nhất quán:** Mức mật độ luôn khớp 100% với số xe dự báo (không bao giờ xảy ra tình trạng model số xe trả 200 nhưng model mật độ lại trả "SEVERE").
- **Dễ hiệu chỉnh:** Khi cần thay đổi ngưỡng, chỉ cần sửa hàm `classify_congestion()` mà không cần train lại.

### 1.3. Ngưỡng phân loại mật độ

Các ngưỡng dưới đây được hiệu chỉnh dựa trên lưu lượng thực tế trên các tuyến đường đô thị Việt Nam (~400–500 xe/15 phút):

| Mức độ | Điều kiện | Ý nghĩa thực tế |
|---|---|---|
| **LOW** | < 200 xe | Đường thông thoáng (giờ khuya, nghỉ lễ) |
| **MEDIUM** | 200 – 349 xe | Lưu thông bình thường |
| **HIGH** | 350 – 499 xe | Bắt đầu đông, có thể chậm |
| **SEVERE** | ≥ 500 xe | Tắc nghẽn, giờ cao điểm nặng |

### 1.4. Tại sao chọn XGBoost?

| Tiêu chí | XGBoost | LSTM/RNN | Linear Regression |
|---|---|---|---|
| Dữ liệu dạng bảng (tabular) | ✅ Tốt nhất | ❌ Không phù hợp | ⚠️ Quá đơn giản |
| Xử lý feature phi tuyến tính | ✅ Tự động | ✅ Tự động | ❌ Chỉ tuyến tính |
| Tốc độ train | ✅ Nhanh (~6 giây) | ❌ Rất chậm | ✅ Nhanh |
| Yêu cầu dữ liệu | ✅ Vừa phải | ❌ Cần rất nhiều | ✅ Ít |
| Khả năng diễn giải (feature importance) | ✅ Có | ❌ Hộp đen | ✅ Có |

→ XGBoost là sự cân bằng lý tưởng giữa **độ chính xác cao** và **tốc độ triển khai nhanh** cho bài toán dự báo giao thông 15 phút.

---

## 2. Cách triển khai

### 2.1. Dữ liệu đầu vào – Metro Interstate Traffic Volume

**Nguồn:** [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/492/metro+interstate+traffic+volume)

| Thông tin | Giá trị |
|---|---|
| Tổng số bản ghi | 48,204 |
| Khoảng thời gian | 2012 – 2018 |
| Đơn vị gốc | **1 bản ghi = 1 giờ** |
| Trung bình | ~3,260 xe/giờ |
| Loại đường | Xa lộ liên bang I-94 (Minnesota, Mỹ) |

**Vấn đề:** Đây là dữ liệu xa lộ Mỹ, khác biệt về cả **đơn vị thời gian** (giờ vs 15 phút) lẫn **quy mô xe** (3,260 vs 400–500 xe) so với thực tế đường đô thị Việt Nam.

### 2.2. Pipeline biến đổi dữ liệu trong `train.py`

```
CSV gốc (48K records, hourly, ~3,260 xe/h)
    ↓ Bước 1: Parse datetime, loại bỏ timestamp trùng lặp
    ↓ Bước 2: Resample 1 giờ → 4 khung 15 phút (÷4 + interpolate)
    ↓ Bước 3: Scale Factor ×0.55 (kéo từ 815 xe/15p → 450 xe/15p)
    ↓
Dữ liệu sạch (210K records, 15-min, ~424 xe/15p)
    ↓ Bước 4: Feature Engineering → Train XGBoost → Lưu model.pkl
```

#### Bước 2 – Tại sao chia ÷4 rồi interpolate?

Dữ liệu gốc ghi nhận **tổng số xe qua trạm trong 1 giờ**. Khi chia đều cho 4, mỗi khung 15 phút sẽ nhận được ~1/4 lưu lượng. Sau đó dùng `interpolate(method='time')` để **nội suy mượt** giữa các điểm, tránh hiện tượng "bậc thang" (tất cả 4 khung đều có giá trị bằng nhau).

```python
# Kết quả: 48,204 records → 210,201 records (x4.36)
df['traffic_volume_15min'] = df['traffic_volume'] / 4
series = df['traffic_volume_15min'].groupby(df.index).mean()
         .resample('15min').asfreq().interpolate(method='time')
```

#### Bước 3 – Scale Factor: 0.55

| Nguồn | Trung bình / 15 phút |
|---|---|
| Metro Dataset (sau ÷4) | ~815 xe |
| Thực tế Việt Nam | ~400–500 xe |

**Scale Factor = 450 / 815 ≈ 0.55**

Sử dụng `450` làm baseline (trung vị của 400–500). Sau khi nhân toàn bộ dữ liệu với hệ số này, phân phối trung bình dịch chuyển về đúng vùng thực tế (~424 xe/15p), giúp mô hình học được các pattern ở đúng quy mô mà nó sẽ gặp khi dự báo.

### 2.3. Feature Engineering trong `traffic_predictor.py`

Mô hình sử dụng **10 đặc trưng** được chia thành 3 nhóm:

#### Nhóm 1: Đặc trưng thời gian (Temporal Features)

| Feature | Cách tính | Lý do |
|---|---|---|
| `hour` | Giờ trong ngày (0–23) | Giao thông có pattern rõ theo giờ (đỉnh 7–9h, 17–19h) |
| `day_of_week` | Thứ trong tuần (0=T2, 6=CN) | Ngày thường ≠ cuối tuần |
| `is_peak_hour` | 1 nếu 7–9h hoặc 17–19h | Đánh dấu rõ ràng giờ cao điểm Việt Nam |
| `is_weekend` | 1 nếu Thứ 7 hoặc Chủ nhật | Cuối tuần lưu lượng thấp hơn đáng kể |
| `hour_sin` | sin(2π × hour / 24) | Mã hóa vòng tròn: giờ 23 gần giờ 0 (liên tục, không gián đoạn) |
| `hour_cos` | cos(2π × hour / 24) | Cặp sin/cos cho phép XGBoost nắm bắt tính chu kỳ 24 giờ |

**Tại sao cần hour_sin/hour_cos?** Với mã hóa số nguyên thông thường (0–23), mô hình hiểu giờ `23` và giờ `0` cách nhau 23 đơn vị. Nhưng thực tế chúng chỉ cách nhau 1 giờ. Mã hóa vòng tròn bằng sin/cos giải quyết vấn đề này, giúp mô hình học đúng khoảng cách thời gian.

#### Nhóm 2: Đặc trưng trễ (Lag Features)

| Feature | Cách tính | Lý do |
|---|---|---|
| `lag_1` | Số xe 15 phút trước (shift 1) | Quán tính ngắn hạn: giao thông thay đổi từ từ |
| `lag_2` | Số xe 30 phút trước (shift 2) | Xu hướng trung hạn: phát hiện tăng/giảm dần |
| `lag_4` | Số xe 1 giờ trước (shift 4) | Chu kỳ 1 giờ + đây là điểm dữ liệu gốc thật (không phải nội suy) |

**Tại sao dùng lag_4 thay vì lag_3?** Dataset Metro gốc là dữ liệu **theo giờ**. Khi nội suy về 15 phút, các giá trị `lag_1`, `lag_2`, `lag_3` là dữ liệu nội suy (ước tính). Riêng `lag_4` (= 1 giờ) tương ứng với điểm dữ liệu gốc thật, nên có **độ tin cậy cao hơn** và giúp mô hình học chính xác hơn.

#### Nhóm 3: Đặc trưng thống kê trượt (Rolling Feature)

| Feature | Cách tính | Lý do |
|---|---|---|
| `rolling_mean_3` | Trung bình 3 khung 15 phút gần nhất | Làm mượt nhiễu (noise), bắt được xu hướng chung thay vì bị ảnh hưởng bởi 1 giá trị bất thường |

### 2.4. Huấn luyện – Time Series Cross-Validation

Đây là **bài toán chuỗi thời gian**, nên không thể dùng random train/test split thông thường vì sẽ rò rỉ dữ liệu tương lai vào tập train (data leakage).

Hệ thống sử dụng **TimeSeriesSplit (5 folds)** từ scikit-learn, đảm bảo:
- Tập train luôn nằm **trước** tập test theo thời gian.
- Mỗi fold, tập train mở rộng thêm trong khi tập test dịch về phía tương lai.

```
Fold 1: Train [────────]  Test [───]
Fold 2: Train [────────────]  Test [───]
Fold 3: Train [────────────────]  Test [───]
Fold 4: Train [────────────────────]  Test [───]
Fold 5: Train [────────────────────────]  Test [───]
                    Thời gian ────────────────────────→
```

### 2.5. Cấu hình XGBoost Regressor

```python
XGBRegressor(
    n_estimators=200,        # 200 cây quyết định (tăng từ 100 để cải thiện độ chính xác)
    learning_rate=0.05,      # Tốc độ học thấp hơn → học chậm nhưng ổn định hơn
    max_depth=6,             # Mỗi cây sâu tối đa 6 tầng (đủ phức tạp mà không overfit)
    subsample=0.8,           # Mỗi cây chỉ dùng 80% dữ liệu → giảm overfitting
    colsample_bytree=0.8,    # Mỗi cây chỉ dùng 80% features → tăng tính đa dạng
    objective='reg:squarederror',  # Bài toán hồi quy, tối ưu sai số bình phương
    random_state=42,
)
```

### 2.6. Luồng dự báo thực tế (Inference)

```
1. Client gọi API:  GET /predict-next?camera_id=CAM_01
2. Backend lấy 8 khung 15 phút gần nhất từ MongoDB Atlas
   (Collection: traffic_aggregation hoặc vehicle_detections)
3. Nếu có ≥ 5 khung → Gọi TrafficPredictor.predict(history)
   Nếu < 5 khung    → Fallback: dùng trung bình cộng
4. Phân loại mật độ:  compute_congestion(predicted_count)
5. Lưu kết quả vào MongoDB (Collection: traffic_predictions)
6. Trả về API response cho client
```

**Yêu cầu tối thiểu:** Hệ thống cần tích lũy **5 khung 15 phút** (~75 phút) dữ liệu detection trước khi mô hình ML được kích hoạt. Trong thời gian chưa đủ, hệ thống tự động chuyển sang chế độ dự phòng (fallback) sử dụng trung bình cộng.

---

## 3. Kết quả đạt được

### 3.1. Training Output

```
[1] Đọc dữ liệu từ CSV...
    Tổng số record gốc (hourly): 48,204
[2] Chuyển đổi dữ liệu từ 1 giờ → 15 phút (÷4 + interpolate)...
    Tổng số record sau chuyển đổi (15-min): 210,201
[3] Áp dụng Scale Factor (0.552) về thực tế Việt Nam...
    Trung bình vehicle_count sau scale: 424.0 xe/15p

--- Training Model: Vehicle Forecast + Density Level ---

[*] Quá trình huấn luyện và đánh giá bắt đầu...
 -> Kết quả đánh giá bằng Cross Validation (5 folds):
    - MAE trung bình:  6.69 xe
    - RMSE trung bình: 9.80 xe
 -> Đang cập nhật mô hình với toàn bộ dữ liệu...

[+] ĐÃ LƯU MÔ HÌNH THÀNH CÔNG: ml_service/model.pkl
```

### 3.2. Chỉ số đánh giá (Metrics)

| Chỉ số | Giá trị | Ý nghĩa |
|---|---|---|
| **MAE** | **6.69 xe** | Trung bình mỗi dự báo lệch ~7 xe so với thực tế |
| **RMSE** | **9.80 xe** | Phạt mạnh hơn các lỗi lớn; cho thấy dự báo khá ổn định |
| **Sai số tương đối** | **~1.6%** | MAE / Trung bình (6.69 / 424) = 1.6% – rất chính xác |

### 3.3. Prediction Output mẫu

```
----------------------------------------
[*] Dang goi API du bao: http://127.0.0.1:8000/predict-next
    Camera ID : CAM_01
----------------------------------------
Camera             : CAM_01
Gia tri du bao     : 491.0
Muc do mat do      : High
Khung du bao       : 15 phut
Nguon du bao       : ml_service
Thoi diem du bao   : 2026-05-02T03:44:42
----------------------------------------
```

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

### 3. Điều chỉnh Scale Factor

Nếu dữ liệu thực tế của bạn có lưu lượng khác 400–500 xe/15p, điều chỉnh `SCALE_FACTOR` trong `train.py`:

```python
# train.py – dòng 6
SCALE_FACTOR = 450.0 / 815.0   # Thay 450 bằng trung bình thực tế của bạn
```

Sau đó chạy lại `python -m ml_service.train` để retrain model.

---

## 📦 Thư viện phụ thuộc

| Thư viện | Mục đích |
|---|---|
| `xgboost` | Thuật toán Gradient Boosting – core model |
| `scikit-learn` | TimeSeriesSplit, MAE/RMSE metrics |
| `pandas` | Xử lý dữ liệu dạng bảng, resample, interpolate |
| `numpy` | Tính toán mảng số học, mã hóa sin/cos |
| `joblib` | Serialize/deserialize model ra file `.pkl` |
| `requests` | Client HTTP cho `predict.py` gọi backend API |
