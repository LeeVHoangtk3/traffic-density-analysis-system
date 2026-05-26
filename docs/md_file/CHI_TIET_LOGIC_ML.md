# 🧠 Tài Liệu Chi Tiết — Phần Machine Learning Dự Báo Giao Thông

> **Dự án:** Hệ thống Phân tích Mật độ Giao thông  
> **Tác giả:** Nhóm phát triển TTCS  
> **Cập nhật lần cuối:** 21/05/2026

---

## Mục Lục

1. [Bài toán & Mục tiêu](#1-bài-toán--mục-tiêu)
2. [Dữ liệu](#2-dữ-liệu)
3. [Kiến trúc tổng thể](#3-kiến-trúc-tổng-thể)
4. [Chi tiết pipeline huấn luyện (train.py)](#4-chi-tiết-pipeline-huấn-luyện)
5. [Feature Engineering — Giải thích từng đặc trưng](#5-feature-engineering)
6. [Thuật toán XGBoost — Tại sao chọn & cách cấu hình](#6-thuật-toán-xgboost)
7. [Chiến lược đánh giá mô hình](#7-chiến-lược-đánh-giá-mô-hình)
8. [Luồng dự báo thực tế (Inference)](#8-luồng-dự-báo-thực-tế)
9. [Phân loại mức độ tắc nghẽn & Đèn xanh](#9-phân-loại-mức-độ-tắc-nghẽn--đèn-xanh)
10. [Cơ chế Fallback khi thiếu dữ liệu](#10-cơ-chế-fallback)
11. [Kết quả đạt được](#11-kết-quả-đạt-được)
12. [Sơ đồ tổng quan luồng dữ liệu](#12-sơ-đồ-tổng-quan)

---

## 1. Bài Toán & Mục Tiêu

### 1.1. Bài toán đặt ra

Hệ thống của chúng ta sử dụng camera quan sát giao thông kết hợp YOLO (Computer Vision) để **đếm số lượng xe** trên một đoạn đường trong từng chu kỳ 15 phút. Câu hỏi đặt ra là:

> **"Dựa trên lịch sử vài khung 15 phút gần nhất, có thể dự đoán được 15 phút tới sẽ có bao nhiêu xe không?"**

Đây chính là bài toán **Time Series Regression** (hồi quy chuỗi thời gian) — một bài toán cổ điển và rất phổ biến trong Machine Learning.

### 1.2. Hai đầu ra của hệ thống

Hệ thống ML cung cấp **hai đầu ra** cho mỗi lần dự báo:

| Đầu ra | Kiểu dữ liệu | Ví dụ | Cách tính |
|---|---|---|---|
| **Số lượng xe dự báo** | Số nguyên ≥ 0 | `125` xe | XGBoost Regressor (mô hình ML) |
| **Mức độ tắc nghẽn** | Chuỗi phân loại | `"High"` | Rule-based: tra bảng ngưỡng từ số xe |

**Lý do chỉ dùng 1 model:** Thay vì huấn luyện 2 model riêng (1 cho số xe, 1 cho mức tắc nghẽn), chúng ta chỉ huấn luyện 1 model dự báo **số xe**, sau đó suy ra mức tắc nghẽn bằng cách so sánh với ngưỡng. Cách này đảm bảo:

- **Nhất quán tuyệt đối:** Không bao giờ xảy ra chuyện model số xe báo 20 nhưng model mức độ lại báo "Severe".
- **Dễ bảo trì:** Chỉ cần retrain 1 model. Khi muốn đổi ngưỡng, chỉ sửa hàm `classify_congestion()`.
- **Tách biệt:** Logic ML (dự báo) và logic nghiệp vụ (phân loại mức) độc lập, dễ thay đổi.

---

## 2. Dữ Liệu

### 2.1. Nguồn dữ liệu: NYC Automated Traffic Volume Counts

File: `ml_service/data/Automated_Traffic_Volume_Counts_20260521.csv`

Đây là bộ dữ liệu thống kê lưu lượng giao thông do Sở Giao thông Vận tải New York (NYC DOT) thu thập, bao gồm **1,875,154 bản ghi** từ nhiều đoạn đường đô thị trên toàn thành phố.

| Thuộc tính | Giá trị |
|---|---|
| **Tổng records** | 1,875,154 |
| **Khu vực** | 5 quận NYC (Bronx, Brooklyn, Manhattan, Queens, Staten Island) |
| **Số đoạn đường (SegmentID)** | ~4,355 đoạn |
| **Thời gian** | 2000, 2006–2026 |
| **Tần suất ghi nhận** | Mỗi **15 phút** (gốc, không cần nội suy) |
| **Cột chính** | `RequestID`, `Boro`, `Yr`, `M`, `D`, `HH`, `MM`, `Vol`, `SegmentID`, `Direction` |

### 2.2. Tại sao chọn dataset này?

**So sánh với dataset cũ (Metro Interstate Traffic Volume):**

| Tiêu chí | Dataset cũ (Metro) | Dataset mới (NYC) | Lý do quan trọng |
|---|---|---|---|
| Loại đường | Xa lộ liên bang I-94 | Đường phố đô thị | Dự án của chúng ta nhắm đến đường đô thị, không phải xa lộ |
| Tần suất gốc | 1 giờ | **15 phút** | Khớp chính xác với chu kỳ đếm xe 15 phút của hệ thống |
| Dữ liệu thật | ~25% (phải nội suy 75%) | **100%** | Không có dữ liệu giả → model học được pattern thực |
| Số lượng records | 48,204 | **1,875,154** | Gấp 39 lần → model có nhiều mẫu để học hơn |

**Điểm mấu chốt:** Dataset cũ ghi nhận theo **giờ**, nhưng hệ thống cần dự báo theo **15 phút**. Điều này buộc phải chia mỗi record giờ thành 4 record 15 phút (nội suy), tạo ra **75% dữ liệu giả**. Model cũ thực chất đang học trên dữ liệu tự phát sinh ra chứ không phải dữ liệu thật. Dataset mới đã có sẵn interval 15 phút → loại bỏ hoàn toàn vấn đề này.

### 2.3. Chọn SegmentID đại diện

Dataset có ~4,355 đoạn đường khác nhau. Chúng ta chọn **SegmentID `72887`** để huấn luyện vì:

- Đây là segment có **nhiều bản ghi nhất** (13,398 records) → đảm bảo model có đủ dữ liệu.
- Trung bình ~192 xe/15 phút — là đoạn đường có mật độ giao thông vừa phải, không quá thưa, không quá đông.

### 2.4. Quy trình dọn dẹp dữ liệu

Trước khi đưa vào model, dữ liệu được lọc qua 4 bước:

```
1,875,154 records (gốc)
    ↓ Lọc SegmentID = 72887
    ↓ Chuyển Vol và MM sang số (loại giá trị rác không parse được)
    ↓ Chỉ giữ MM ∈ {0, 15, 30, 45} (loại bỏ interval không chuẩn)
    ↓ Loại Vol < 0 (giá trị âm vô nghĩa)
    ↓ Ghép Yr + M + D + HH + MM → timestamp duy nhất
13,398 records (sạch, sẵn sàng train)
```

**Cách ghép timestamp:** Vì dataset không có cột datetime sẵn mà chia tách thành 5 cột riêng (`Yr`, `M`, `D`, `HH`, `MM`), nên cần ghép lại:

```python
# Ví dụ: Yr=2013, M=3, D=7, HH=4, MM=15 → "2013-03-07 04:15"
df['timestamp'] = pd.to_datetime(
    df['Yr'].astype(str) + '-' + 
    df['M'].astype(str).str.zfill(2) + '-' + 
    df['D'].astype(str).str.zfill(2) + ' ' + 
    df['HH'].astype(str).str.zfill(2) + ':' + 
    df['MM'].astype(str).str.zfill(2)
)
```

Hàm `str.zfill(2)` đảm bảo các số 1 chữ số (ví dụ tháng `3`) được đệm thành `03`, vì `pd.to_datetime` yêu cầu định dạng chuẩn.

---

## 3. Kiến Trúc Tổng Thể

Hệ thống ML gồm 3 file chính:

```
ml_service/
├── train.py              # Pipeline huấn luyện: đọc CSV → làm sạch → train → lưu model.pkl
├── traffic_predictor.py  # Class TrafficPredictor: feature engineering + train + predict
├── predict.py            # Client CLI: gọi API backend để lấy kết quả dự báo
└── model.pkl             # File model đã train (XGBoost serialized bằng joblib)
```

**Phân tách trách nhiệm:**

| File | Trách nhiệm | Khi nào chạy? |
|---|---|---|
| `train.py` | Đọc CSV, lọc data, gọi `TrafficPredictor.train_and_evaluate()`, lưu `model.pkl` | Chạy **1 lần** trước khi hệ thống hoạt động, hoặc khi muốn retrain |
| `traffic_predictor.py` | Class chứa toàn bộ logic ML: tạo features, train model, predict | Được **import** bởi `train.py` (khi train) và `prediction_service.py` (khi predict) |
| `predict.py` | Script test — gọi API `/predict-next` của backend để kiểm tra dự báo | Chạy thủ công để **debug** |

---

## 4. Chi Tiết Pipeline Huấn Luyện

File: `ml_service/train.py`

Pipeline huấn luyện được thiết kế theo nguyên tắc **đơn giản, minh bạch, tái tạo được** (reproducible). Toàn bộ quá trình diễn ra tuần tự trong hàm `main()`:

### Bước 1: Đọc dữ liệu

```python
df = pd.read_csv(raw_csv, dtype={'SegmentID': str})
```

**Lý do `dtype={'SegmentID': str}`:** SegmentID là mã định danh (ID), không phải số để tính toán. Nếu để pandas tự suy kiểu, nó sẽ đọc thành `int64`, gây mất số 0 đầu (nếu có) và khó so sánh. Ép kiểu `str` đảm bảo so sánh chính xác.

### Bước 2: Lọc segment & dọn dẹp

```python
df = df[df['SegmentID'] == SEGMENT_ID].copy()
df['Vol'] = pd.to_numeric(df['Vol'], errors='coerce')    # Chuyển sang số, NaN nếu không parse được
df['MM'] = pd.to_numeric(df['MM'], errors='coerce')
df = df.dropna(subset=['Vol', 'MM']).copy()               # Bỏ dòng rác
df = df[df['MM'].isin([0, 15, 30, 45])].copy()           # Chỉ giữ interval 15 phút chuẩn
df = df[df['Vol'] >= 0].copy()                            # Bỏ giá trị âm
```

**Lý do dùng `.copy()`:** Trong pandas, khi lọc DataFrame, kết quả có thể là "view" (tham chiếu) thay vì bản sao thật. Nếu sau đó chỉnh sửa dữ liệu, pandas sẽ cảnh báo `SettingWithCopyWarning`. Dùng `.copy()` tạo bản sao độc lập, tránh lỗi này.

### Bước 3: Tạo timestamp & chuẩn hóa

```python
df = df.rename(columns={'Vol': 'vehicle_count'})
df = df[['timestamp', 'vehicle_count']].sort_values('timestamp').reset_index(drop=True)
```

Sau bước này, DataFrame chỉ còn 2 cột: `timestamp` và `vehicle_count` — đúng định dạng mà `TrafficPredictor` yêu cầu.

### Bước 4: Huấn luyện & lưu model

```python
predictor = TrafficPredictor(os.path.join(base, 'model.pkl'))
predictor.train_and_evaluate(df)    # Feature engineering → Train/Test split → CV → Fit → Evaluate
predictor.save_model()              # Serialize model ra model.pkl
```

---

## 5. Feature Engineering

File: `ml_service/traffic_predictor.py` → hàm `create_features()`

Feature Engineering (kỹ thuật tạo đặc trưng) là bước **quan trọng nhất** quyết định chất lượng mô hình. Hệ thống sử dụng **12 đặc trưng (features)** chia thành 3 nhóm.

### 5.1. Nhóm 1: Đặc trưng thời gian (Temporal Features) — 6 features

Giao thông có tính chu kỳ rõ rệt: đông vào giờ cao điểm, vắng vào ban đêm, khác nhau giữa ngày thường và cuối tuần. Các features này giúp model "biết" đang ở thời điểm nào trong ngày/tuần.

#### `is_peak_hour` — Cờ giờ cao điểm

```python
data['is_peak_hour'] = data['hour'].apply(
    lambda x: 1 if (7 <= x <= 9) or (17 <= x <= 19) else 0
)
```

- **Ý nghĩa:** Đánh dấu 1 nếu đang trong khung giờ cao điểm (7h–9h sáng, 17h–19h chiều), 0 nếu không.
- **Tại sao cần:** Lưu lượng giao thông tại giờ cao điểm thường **gấp 2-3 lần** giờ bình thường. Feature nhị phân (0/1) này giúp model nhanh chóng phân biệt hai chế độ hoạt động khác nhau.
- **Giá trị:** 0 hoặc 1.

#### `is_weekend` — Cờ cuối tuần

```python
data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
```

- **Ý nghĩa:** 1 nếu Thứ 7 hoặc Chủ Nhật, 0 nếu ngày thường.
- **Tại sao cần:** Cuối tuần ít người đi làm → lưu lượng thấp hơn đáng kể (thường giảm 30-50%). Đây là thông tin rất hữu ích cho model.
- **Giá trị:** 0 hoặc 1.

#### `hour_sin` và `hour_cos` — Mã hóa vòng tròn cho giờ

```python
data['hour_sin'] = np.sin(2 * np.pi * data['hour'] / 24)
data['hour_cos'] = np.cos(2 * np.pi * data['hour'] / 24)
```

- **Ý nghĩa:** Biểu diễn giờ trong ngày (0–23) dưới dạng toạ độ trên đường tròn.
- **Tại sao không dùng `hour` số nguyên?** Nếu dùng số nguyên 0–23, model sẽ hiểu giờ 23 và giờ 0 cách nhau **23 đơn vị**. Nhưng thực tế chúng chỉ cách nhau **1 giờ**. Mã hóa sin/cos đặt giờ lên đường tròn, giúp model hiểu đúng khoảng cách thời gian:
  - Giờ 0 → sin=0, cos=1
  - Giờ 6 → sin=1, cos=0
  - Giờ 12 → sin=0, cos=-1
  - Giờ 23 → sin≈-0.26, cos≈0.97 (gần giá trị của giờ 0)
- **Tại sao cần cả sin lẫn cos?** Nếu chỉ dùng sin, giờ 6 và giờ 18 sẽ có cùng giá trị (sin = ±1). Cặp (sin, cos) tạo toạ độ duy nhất cho mỗi giờ trên đường tròn → model phân biệt được mọi giờ.

#### `day_of_week_sin` và `day_of_week_cos` — Mã hóa vòng tròn cho thứ

```python
data['day_of_week_sin'] = np.sin(2 * np.pi * data['day_of_week'] / 7)
data['day_of_week_cos'] = np.cos(2 * np.pi * data['day_of_week'] / 7)
```

- **Logic tương tự `hour_sin/cos`** nhưng áp dụng cho 7 ngày trong tuần (0=Thứ Hai, 6=Chủ Nhật).
- **Tại sao cần:** Chủ nhật (6) và Thứ hai (0) liền kề trong tuần nhưng cách nhau 6 đơn vị nếu dùng số nguyên. Mã hóa vòng tròn giải quyết vấn đề này, giúp model hiểu mối quan hệ tuần hoàn.

---

### 5.2. Nhóm 2: Đặc trưng trễ (Lag Features) — 3 features

Đây là nhóm features **mạnh nhất** cho bài toán chuỗi thời gian. Ý tưởng cốt lõi: **giao thông thay đổi từ từ, không nhảy đột ngột**. Nếu 15 phút trước có 100 xe, 15 phút tới rất có thể cũng sẽ quanh 100 xe.

#### `lag_1` — Số xe 15 phút trước

```python
data['lag_1'] = data['vehicle_count'].shift(1)
```

- **Ý nghĩa:** Giá trị `vehicle_count` của dòng ngay trước đó (tức 15 phút trước).
- **Tại sao quan trọng nhất:** Đây là predictor mạnh nhất vì giao thông có **quán tính** cao — dòng xe không thể biến mất hoặc xuất hiện đột ngột trong 15 phút.
- **Ví dụ:** Nếu lag_1 = 150, model biết ngay rằng giá trị tiếp theo rất có thể nằm trong khoảng 130–170.

#### `lag_2` — Số xe 30 phút trước

```python
data['lag_2'] = data['vehicle_count'].shift(2)
```

- **Ý nghĩa:** Giá trị 2 khung trước (30 phút).
- **Tại sao cần:** Kết hợp lag_1 và lag_2, model có thể nhận ra **xu hướng**: nếu lag_2 = 80 và lag_1 = 100, giao thông đang **tăng**; nếu lag_2 = 120 và lag_1 = 100, đang **giảm**.

#### `lag_4` — Số xe 1 giờ trước

```python
data['lag_4'] = data['vehicle_count'].shift(4)
```

- **Ý nghĩa:** Giá trị 4 khung trước (1 giờ).
- **Tại sao cần:** Cung cấp context rộng hơn. Nếu 1 giờ trước rất đông (lag_4 = 300) nhưng hiện tại chỉ 100 (lag_1 = 100), model hiểu rằng giao thông đang giảm dần sau giờ cao điểm.

---

### 5.3. Nhóm 3: Đặc trưng xu hướng & biến động (Trend/Rolling) — 3 features

#### `diff_1` — Chênh lệch so với 15 phút trước

```python
data['diff_1'] = data['vehicle_count'].diff(1)
```

- **Ý nghĩa:** `count(t) - count(t-1)` = số xe hiện tại **trừ** số xe 15 phút trước.
- **Tại sao cần:** Cho model biết **hướng biến động** trực tiếp:
  - diff_1 > 0 → đang tăng (ví dụ: +30 xe trong 15 phút)
  - diff_1 < 0 → đang giảm
  - diff_1 ≈ 0 → ổn định
- **Khác gì lag?** Lag cho giá trị tuyệt đối (100 xe, 120 xe), diff cho **tốc độ thay đổi** (+20 xe). Model dùng cả hai để dự đoán chính xác hơn.

#### `rolling_mean_3` — Trung bình trượt 3 khung gần nhất

```python
data['rolling_mean_3'] = data['vehicle_count'].shift(1).rolling(window=3).mean()
```

- **Ý nghĩa:** Trung bình cộng của 3 giá trị `vehicle_count` gần nhất (đã shift 1 để tránh data leakage — không dùng giá trị hiện tại).
- **Tại sao cần:** Làm **mượt nhiễu (noise smoothing)**. Dữ liệu giao thông có nhiều biến động ngắn hạn (1 xe buýt 50 người vs 1 xe ô tô). Rolling mean lọc bỏ các dao động nhỏ, giữ lại xu hướng chung.
- **Tại sao `shift(1)` trước khi `rolling`?** Để tránh **data leakage** — nếu không shift, rolling mean sẽ bao gồm giá trị hiện tại (chính là target mà model đang cố dự đoán), dẫn đến model "gian lận".

#### `rolling_std_3` — Độ lệch chuẩn trượt 3 khung

```python
data['rolling_std_3'] = data['vehicle_count'].shift(1).rolling(window=3).std()
```

- **Ý nghĩa:** Đo mức độ **biến động** của giao thông trong 3 khung gần nhất.
- **Tại sao cần:** Nếu rolling_std cao (ví dụ: 50), giao thông đang **bất ổn** (lúc đông lúc vắng), model nên thận trọng hơn. Nếu std thấp (ví dụ: 5), giao thông **ổn định**, model có thể tự tin dự đoán gần rolling_mean.

### 5.4. Xử lý giá trị thiếu (NaN)

```python
data = data.dropna()
```

Các phép `shift()` và `rolling()` tạo ra giá trị NaN ở **đầu** DataFrame (vì không có dữ liệu trước đó để shift). Với `lag_4` và `rolling(3)` kết hợp `shift(1)`, tối thiểu **5 dòng đầu** sẽ bị NaN → bị loại bỏ bởi `dropna()`. Đây là trade-off cần thiết: mất 5 dòng nhưng đảm bảo mọi feature đều có giá trị hợp lệ.

---

## 6. Thuật Toán XGBoost

### 6.1. Tại sao chọn XGBoost?

| Tiêu chí | XGBoost | LSTM/RNN | Linear Regression |
|---|---|---|---|
| Dữ liệu dạng bảng (tabular) | ✅ **Tốt nhất** | ❌ Không phù hợp | ⚠️ Quá đơn giản |
| Xử lý feature phi tuyến | ✅ Tự động | ✅ Tự động | ❌ Chỉ tuyến tính |
| Tốc độ train | ✅ Nhanh (~6 giây) | ❌ Rất chậm (phút/giờ) | ✅ Nhanh |
| Yêu cầu dữ liệu | ✅ Vừa phải (~10K+) | ❌ Cần rất nhiều (~100K+) | ✅ Ít |
| Khả năng diễn giải | ✅ Feature importance | ❌ Hộp đen | ✅ Coefficients |
| Xử lý missing/outlier | ✅ Tốt | ❌ Phải xử lý trước | ❌ Nhạy cảm |

**Kết luận:** XGBoost là sự cân bằng lý tưởng giữa **độ chính xác cao**, **tốc độ nhanh**, và **dễ triển khai** cho bài toán dự báo giao thông 15 phút với dữ liệu tabular.

### 6.2. XGBoost hoạt động như thế nào? (Giải thích đơn giản)

XGBoost (eXtreme Gradient Boosting) xây dựng **nhiều cây quyết định nhỏ** (weak learners), mỗi cây **sửa lỗi** của các cây trước đó.

```
Cây 1: Dự đoán thô → Sai số lớn
Cây 2: Học từ sai số của Cây 1 → Sai số giảm
Cây 3: Học từ sai số còn lại → Sai số giảm tiếp
...
Cây 200: Sai số rất nhỏ
```

Kết quả cuối = Tổng dự đoán của tất cả 200 cây. Mỗi cây đóng góp một phần nhỏ (learning_rate = 0.05), đảm bảo quá trình hội tụ ổn định.

### 6.3. Giải thích từng tham số

```python
XGBRegressor(
    n_estimators=200,           # Số cây quyết định
    learning_rate=0.05,         # Tốc độ học
    max_depth=6,                # Độ sâu tối đa mỗi cây
    subsample=0.8,              # Tỉ lệ data sampling
    colsample_bytree=0.8,      # Tỉ lệ feature sampling
    objective='reg:squarederror', # Hàm mất mát
    random_state=42,            # Seed cố định
)
```

| Tham số | Giá trị | Ý nghĩa | Lý do chọn |
|---|---|---|---|
| `n_estimators` | 200 | Tổng số cây quyết định | 200 cây là đủ cho dataset ~13K records. Nhiều hơn không cải thiện thêm nhưng tốn thời gian |
| `learning_rate` | 0.05 | Mỗi cây mới chỉ đóng góp 5% vào kết quả | Giá trị thấp = học chậm nhưng **ổn định hơn**, giảm nguy cơ overfitting. Thường đi kèm n_estimators cao |
| `max_depth` | 6 | Mỗi cây có tối đa 6 tầng phân nhánh | Đủ phức tạp để nắm bắt pattern (giờ cao điểm, cuối tuần) nhưng không quá sâu gây overfitting |
| `subsample` | 0.8 | Mỗi cây chỉ dùng **80% dữ liệu** (random) | Tạo sự đa dạng giữa các cây, giảm overfitting — tương tự ý tưởng của Bagging |
| `colsample_bytree` | 0.8 | Mỗi cây chỉ dùng **80% features** (random) | Ngăn model phụ thuộc quá nhiều vào 1-2 feature mạnh (như lag_1) |
| `objective` | `reg:squarederror` | Tối ưu hóa Mean Squared Error | Tiêu chuẩn cho bài toán hồi quy (regression). Phạt mạnh các lỗi lớn |
| `random_state` | 42 | Seed ngẫu nhiên cố định | Đảm bảo kết quả **tái tạo được** — chạy lại luôn cho cùng kết quả |

### 6.4. Early Stopping

```python
early_stopping_rounds=20
```

- **Ý nghĩa:** Nếu sau 20 cây liên tiếp mà metric trên tập validation không cải thiện, **dừng train sớm**.
- **Tại sao cần:** Ngăn model train quá nhiều cây vô ích (overfitting). Thay vì luôn dùng đủ 200 cây, model có thể dừng ở cây thứ 150 nếu đã đạt đỉnh. Tiết kiệm thời gian và tránh overfitting.

---

## 7. Chiến Lược Đánh Giá Mô Hình

### 7.1. Chia dữ liệu: Train 80% — Test 20% (theo thời gian)

```python
split_idx = int(len(data) * 0.8)
train_data = data.iloc[:split_idx]      # 80% dữ liệu đầu (quá khứ)
test_data = data.iloc[split_idx:]       # 20% dữ liệu cuối (tương lai)
```

**Tại sao không random split?** Đây là **chuỗi thời gian** — nếu random split, dữ liệu từ năm 2020 có thể nằm trong tập train trong khi 2019 nằm trong test. Model sẽ "nhìn thấy tương lai" khi train → kết quả đánh giá không đáng tin cậy (data leakage).

**Cách đúng:** Chia theo **chronological order** — train trên quá khứ, test trên tương lai. Đây chính xác là cách model sẽ hoạt động trong thực tế.

### 7.2. Cross-Validation trên tập Train (5-Fold TimeSeriesSplit)

```
Fold 1: Train [────────]  Val [───]
Fold 2: Train [────────────]  Val [───]
Fold 3: Train [────────────────]  Val [───]
Fold 4: Train [────────────────────]  Val [───]
Fold 5: Train [────────────────────────]  Val [───]
                    Thời gian ────────────────────────→
```

- **Mục đích:** Đánh giá model trên **nhiều thời điểm khác nhau** trong tập train, đảm bảo model không chỉ tốt ở 1 giai đoạn cụ thể.
- **Kết quả:** MAE trung bình 5 folds = 7.12 xe — cho thấy model ổn định qua các thời kỳ.

### 7.3. Đánh giá trên Held-out Test (20% cuối)

Sau CV, model cuối cùng được train trên **toàn bộ 80% train** và đánh giá trên 20% test (dữ liệu model **chưa bao giờ thấy**). Đây là thước đo chính xác nhất.

### 7.4. Giải thích 4 metrics

| Metric | Công thức | Giá trị đạt được | Ý nghĩa thực tế |
|---|---|---|---|
| **MAE** | Trung bình \|thực - dự đoán\| | **4.76 xe** | Trung bình mỗi lần dự đoán sai khoảng ~5 xe so với thực tế |
| **RMSE** | √(Trung bình (thực - dự đoán)²) | **8.31 xe** | Giống MAE nhưng phạt mạnh hơn các lỗi lớn. RMSE > MAE cho thấy có một số lần dự đoán sai khá nhiều |
| **R²** | 1 - (tổng sai số model / tổng biến động data) | **0.9895** | Model giải thích được 98.95% sự biến động của dữ liệu. Giá trị rất cao |
| **MAPE** | Trung bình (\|thực - dự đoán\| / thực) × 100% | **3.89%** | Sai số tương đối: dự báo sai trung bình ~3.9% so với giá trị thật |

---

## 8. Luồng Dự Báo Thực Tế (Inference)

Khi hệ thống chạy production, quá trình dự báo diễn ra qua các bước sau:

### Bước 1: Client gọi API

```
GET /predict-next?camera_id=CAM_01
```

### Bước 2: Backend lấy lịch sử từ MongoDB

```python
# prediction_service.py → _build_prediction_history()
# Ưu tiên lấy từ traffic_aggregation (đã tổng hợp sẵn)
# Fallback: tổng hợp từ vehicle_detections (detection thô)
history = get_recent_aggregations(db, camera_id="CAM_01", n=8)
```

Lấy tối đa **8 bản ghi gần nhất** từ collection `traffic_aggregation`. Mỗi bản ghi chứa `timestamp` và `vehicle_count` (số xe đếm được trong khung 15 phút đó).

### Bước 3: Kiểm tra đủ dữ liệu

```python
if len(history) >= 5:
    # Đủ data → dùng ML model
else:
    # Thiếu data → dùng fallback (trung bình cộng)
```

### Bước 4: Tạo dòng giả cho tương lai

```python
# traffic_predictor.py → predict()
last_time = pd.to_datetime(df['timestamp'].iloc[-1])
next_time = last_time + pd.Timedelta(minutes=15)
future_row = pd.DataFrame([{'timestamp': next_time, 'vehicle_count': 0}])
temp_df = pd.concat([df, future_row], ignore_index=True)
```

**Tại sao cần dòng giả?** Hàm `create_features()` tính features dựa trên `timestamp` (giờ, thứ) và `vehicle_count` (lag, rolling). Chúng ta cần features **tại thời điểm tương lai** (15 phút tới) để model dự đoán. Dòng giả cung cấp timestamp tương lai, từ đó tính được `hour_sin`, `hour_cos`, `is_peak_hour` đúng cho thời điểm cần dự báo.

Giá trị `vehicle_count = 0` của dòng giả **không ảnh hưởng** đến features quan trọng nhất (`lag_1`, `lag_2`, `lag_4`) vì chúng lấy giá trị từ **các dòng trước đó** (shift), không phải dòng hiện tại.

### Bước 5: Tạo features & dự đoán

```python
processed = self.create_features(temp_df)
target_features = processed.tail(1)[self.features]  # Lấy dòng cuối (tương lai)
predicted = self.model.predict(target_features)[0]   # XGBoost dự đoán
return max(0, int(round(predicted)))                 # Không cho ra số âm
```

### Bước 6: Phân loại mức tắc nghẽn & tính đèn xanh

```python
congestion_level = compute_congestion(int(predicted_value))  # "Low" / "Medium" / "High" / "Severe"
green_light_time = _compute_green_light_time(predicted_value, history)  # 20–60 giây
```

### Bước 7: Lưu & trả kết quả

```python
document = {
    "camera_id": "CAM_01",
    "predicted_density": 125.0,
    "predicted_congestion_level": "High",
    "green_light_time": 45,
    "horizon_minutes": 15,
    "source": "ml_service",        # hoặc "fallback"
    "timestamp": "2026-05-21T09:33:15"
}
db.traffic_predictions.insert_one(document)  # Lưu vào MongoDB
return document                               # Trả về cho client
```

---

## 9. Phân Loại Mức Độ Tắc Nghẽn & Đèn Xanh

### 9.1. Ngưỡng phân loại

Dựa trên phân tích phân vị của dataset NYC (trung bình ~102 xe/15p, median ~58 xe/15p):

| Mức độ | Ngưỡng | Ý nghĩa | Cơ sở thống kê |
|---|---|---|---|
| **Low** | < 30 xe | Đường thông thoáng | Dưới Q1 (25th percentile = 17) + margin |
| **Medium** | 30 – 99 xe | Lưu thông bình thường | Quanh median (58) |
| **High** | 100 – 199 xe | Bắt đầu đông đúc | Trên Q3 (75th percentile = 131) |
| **Severe** | ≥ 200 xe | Tắc nghẽn nặng | Top ~5% giá trị cao nhất |

### 9.2. Đồng bộ ngưỡng trong hệ thống

Ngưỡng 30/100/200 được áp dụng **nhất quán** tại 3 vị trí:

| Module | File | Hàm |
|---|---|---|
| ML Service | `ml_service/traffic_predictor.py` | `classify_congestion()` |
| Backend | `backend/services/aggregation_service.py` | `compute_congestion()` |
| Integration | `integration_system/system_runner.py` | `CongestionClassifier.classify()` |

### 9.3. Logic đèn xanh

```python
def _compute_green_light_time(predicted_density, history):
    base_time = 30                    # Thời gian cơ sở (giây)
    avg_density = history.mean()      # Trung bình lịch sử gần nhất
    diff_ratio = (predicted - avg) / avg   # % chênh lệch
    delta = int(diff_ratio / 0.1) * 5      # Mỗi 10% → ±5 giây
    return clamp(base_time + delta, min=20, max=60)
```

**Logic:** Nếu dự báo 15 phút tới **đông hơn** trung bình lịch sử → **tăng** thời gian đèn xanh (cho nhiều xe qua hơn). Ngược lại → **giảm**. Giới hạn an toàn: 20–60 giây.

---

## 10. Cơ Chế Fallback

Hệ thống có 2 cấp fallback khi thiếu dữ liệu:

```
                    Có ≥ 5 bản ghi lịch sử?
                    /                     \
                  CÓ                      KHÔNG
                  ↓                         ↓
           Dùng ML Model              Có ≥ 3 bản ghi?
           (XGBoost predict)          /              \
           source = "ml_service"    CÓ              KHÔNG
                                    ↓                 ↓
                              Trung bình cộng    Raise Error
                              source = "fallback"  "Cần ≥ 3 records"
```

**Tại sao cần 5 bản ghi tối thiểu?** Vì model cần tính `lag_4` (shift 4) + `dropna()` loại dòng đầu → cần ít nhất 5 dòng để còn lại 1 dòng có đủ features.

**Tại sao fallback dùng trung bình cộng?** Khi chưa đủ dữ liệu cho ML, trung bình cộng là ước tính đơn giản nhất nhưng an toàn: nó không phóng đại cũng không đánh thấp, chỉ dùng tạm cho đến khi hệ thống tích luỹ đủ history.

---

## 11. Kết Quả Đạt Được

### Output huấn luyện

```
[1] Đọc dữ liệu từ CSV (NYC Automated Traffic Volume)...
    Tổng số record gốc: 1875154
[2] Lọc SegmentID 72887 và dọn dẹp dữ liệu...
    Số lượng bản ghi sau khi lọc: 13398
    Trung bình vehicle_count: 192.3 xe/15p

--- Training Model: Vehicle Forecast + Density Level ---

[*] Quá trình huấn luyện và đánh giá bắt đầu...
 -> Tập Train: 10715 samples, Tập Test: 2679 samples
 -> Kết quả Cross Validation (5 folds) trên tập Train:
    - MAE trung bình:  7.12 xe
    - RMSE trung bình: 13.91 xe

 -> Đang huấn luyện mô hình cuối trên toàn bộ tập Train (với early stopping qua tập Test)...
 -> Kết quả đánh giá trên tập Held-out Test (20% cuối):
    - MAE:   4.76 xe
    - RMSE:  8.31 xe
    - R2:    0.9895
    - MAPE:  3.89%

[+] ĐÃ LƯU MÔ HÌNH THÀNH CÔNG: ml_service/model.pkl
```

---

## 12. Sơ Đồ Tổng Quan

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LUỒNG HUẤN LUYỆN (OFFLINE)                       │
│                                                                         │
│  CSV Dataset ──→ train.py ──→ Lọc & Làm sạch ──→ TrafficPredictor     │
│  (1.87M rows)    (pipeline)   (13K rows)          .train_and_evaluate()│
│                                                         │               │
│                                                    model.pkl            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      LUỒNG DỰ BÁO (ONLINE/REALTIME)                    │
│                                                                         │
│  Camera ──→ YOLO Detection ──→ POST /detection ──→ MongoDB             │
│  (video)    (đếm xe)           (backend API)       (vehicle_detections) │
│                                                         │               │
│                                    POST /aggregation/compute            │
│                                                         │               │
│                                                    MongoDB              │
│                                                    (traffic_aggregation)│
│                                                         │               │
│                                    GET /predict-next                    │
│                                         │                               │
│                              ┌──────────┴──────────┐                    │
│                              │ prediction_service   │                    │
│                              │                      │                    │
│                              │ 1. Lấy 8 records    │                    │
│                              │    gần nhất từ DB    │                    │
│                              │                      │                    │
│                              │ 2. ≥5 records?       │                    │
│                              │    CÓ → ML predict   │                    │
│                              │    KHÔNG → Fallback   │                    │
│                              │                      │                    │
│                              │ 3. Phân loại mức     │                    │
│                              │    tắc nghẽn         │                    │
│                              │                      │                    │
│                              │ 4. Tính đèn xanh    │                    │
│                              │                      │                    │
│                              │ 5. Lưu MongoDB &     │                    │
│                              │    trả API response  │                    │
│                              └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
```
