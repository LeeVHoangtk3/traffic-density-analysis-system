# 🔍 Đánh Giá Chuyên Sâu — Phần Machine Learning Dự Báo

> **Dự án:** Traffic Density Analysis System  
> **Phạm vi đánh giá:** `ml_service/` (TrafficPredictor + LightDeltaModel) và các module tích hợp liên quan  
> **Thời gian:** 2026-05-21

---

## 📋 Tổng Quan Hệ Thống ML

Hệ thống bao gồm **2 mô hình ML** độc lập:

| Mô hình | File | Chức năng | Thuật toán |
|---|---|---|---|
| **TrafficPredictor** | [traffic_predictor.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/traffic_predictor.py) | Dự báo số xe trong 15 phút tiếp theo | XGBoost Regressor |
| **LightDeltaModel** | [light_delta_model.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/light_delta_model.py) | Đề xuất điều chỉnh thời gian đèn xanh (delta giây) | XGBoost Regressor |

Pipeline huấn luyện: [train.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/train.py) | Inference API: [prediction_service.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/backend/services/prediction_service.py)

---

## 1. Đánh Giá Dataset

### 1.1. TrafficPredictor — Metro Interstate Traffic Volume

| Tiêu chí | Đánh giá | Chi tiết |
|---|---|---|
| **Nguồn** | ⚠️ Chấp nhận được | UCI ML Repository — dataset nổi tiếng, có peer review |
| **Kích thước** | ✅ Đủ lớn | 48,204 bản ghi gốc → ~210K sau resample |
| **Tính đại diện** | ❌ **Yếu** | Xa lộ liên bang I-94 (Mỹ) ≠ đường đô thị Việt Nam |
| **Thời gian** | ⚠️ Cũ | 2012–2018, không phản ánh xu hướng giao thông hiện tại |
| **Đa dạng** | ❌ **Thiếu** | Chỉ 1 tuyến đường, 1 hướng, không có đa camera |

> [!CAUTION]
> **Vấn đề nghiêm trọng nhất:** Dataset xa lộ Mỹ (trung bình 3,260 xe/giờ, chủ yếu ô tô) hoàn toàn khác biệt với giao thông đô thị Việt Nam (xe máy chiếm 70-80%, mật độ nén cao, nhiều giao lộ). Việc dùng **Scale Factor cố định ×0.55** chỉ thay đổi **biên độ** chứ **không thay đổi pattern** giao thông. Mô hình sẽ học pattern giờ cao điểm Mỹ (7–9h sáng, 4–6h chiều rush hour), holiday Mỹ (Thanksgiving, Christmas...), chứ không phải Việt Nam.

### 1.2. Các Feature Thời Tiết Bị Lãng Phí

Dataset Metro gốc có các cột rất giá trị: `temp`, `rain_1h`, `snow_1h`, `clouds_all`, `weather_main`, `holiday` — nhưng **tất cả đều bị bỏ qua** trong [train.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/train.py). Nghiên cứu cho thấy thời tiết ảnh hưởng 10-20% đến lưu lượng giao thông (mưa giảm tốc độ, tăng thời gian di chuyển).

### 1.3. File `urban_traffic.csv` — Không Được Sử Dụng

Trong thư mục `data/` có file [urban_traffic.csv](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/data/urban_traffic.csv) (200 bản ghi, interval 15 phút, có `Vehicle_Speed`, `Congestion_Level`, `Peak_Off_Peak`) nhưng **không có bất kỳ file nào import hay sử dụng nó**. Đây là lãng phí — dù nhỏ nhưng dữ liệu này có format phù hợp hơn cho bài toán.

### 1.4. LightDeltaModel — Không Có Dataset Thực

> [!WARNING]
> `LightDeltaModel` **hoàn toàn không có dữ liệu huấn luyện thực**. Demo trong `__main__` sử dụng 500 mẫu **dữ liệu ngẫu nhiên** với nhãn heuristic (if-else đơn giản). Kết quả MAE = 0.83s rất tốt — nhưng chỉ vì model đang học lại một bộ rule đơn giản, **không có giá trị dự báo thực tế**.

---

## 2. Đánh Giá Thuật Toán

### 2.1. Lựa Chọn XGBoost

| Tiêu chí | Đánh giá |
|---|---|
| Phù hợp với dữ liệu dạng bảng | ✅ Rất tốt |
| Tốc độ huấn luyện | ✅ Nhanh |
| Khả năng diễn giải | ✅ Feature importance |
| Xử lý chuỗi thời gian | ⚠️ Trung bình — XGBoost không có memory/state như LSTM |

**Nhận xét:** XGBoost là lựa chọn hợp lý cho dự án TTCS. Tuy nhiên, với dữ liệu chuỗi thời gian 15 phút, các lựa chọn đáng cân nhắc bổ sung:
- **LightGBM**: Nhanh hơn XGBoost 2-3x, kết quả tương đương
- **Prophet (Facebook)**: Tốt cho chuỗi thời gian với tính mùa vụ rõ ràng
- Nếu có GPU: **LSTM/GRU** đơn giản có thể bắt pattern dài hạn tốt hơn

### 2.2. Hyperparameters — Chưa Được Tuning

```python
# traffic_predictor.py — Cấu hình hiện tại
XGBRegressor(
    n_estimators=200,      # ✅ Hợp lý
    learning_rate=0.05,    # ✅ Hợp lý
    max_depth=6,           # ⚠️ Có thể quá sâu cho 10 features
    subsample=0.8,         # ✅ Hợp lý
    colsample_bytree=0.8,  # ✅ Hợp lý
)
```

> [!IMPORTANT]
> **Không có bước Hyperparameter Tuning.** Các tham số được chọn thủ công (hardcode). Thiếu `GridSearchCV`, `RandomizedSearchCV`, hoặc `Optuna` để tìm bộ tham số tối ưu. Với ~210K mẫu, `max_depth=6` và `n_estimators=200` có nguy cơ **overfitting** mà không có early stopping.

**Thiếu `early_stopping_rounds`:** XGBoost hỗ trợ early stopping để tự dừng khi validation loss không cải thiện, giúp tránh overfitting và tiết kiệm thời gian. Hiện tại model luôn chạy hết 200 trees.

---

## 3. Đánh Giá Feature Engineering

### 3.1. TrafficPredictor — 10 Features

| Feature | Đánh giá | Ghi chú |
|---|---|---|
| `hour` | ✅ Cần thiết | Nhưng đã có `hour_sin`/`hour_cos` → **dư thừa** (XGBoost có thể xử lý cả 3, nhưng `hour` integer là redundant khi đã encode sin/cos) |
| `day_of_week` | ✅ Cần thiết | Nên thêm sin/cos encoding tương tự `hour` |
| `is_peak_hour` | ✅ Tốt | Giờ cao điểm VN 7-9h, 17-19h — đúng |
| `is_weekend` | ✅ Tốt | |
| `hour_sin`, `hour_cos` | ✅ Xuất sắc | Cyclical encoding đúng chuẩn |
| `lag_1`, `lag_2`, `lag_4` | ✅ Tốt | Lag quan trọng nhất cho time series |
| `rolling_mean_3` | ✅ Tốt | Smoothing hợp lý |

**Các Feature THIẾU đáng chú ý:**

| Feature nên thêm | Lý do | Mức ưu tiên |
|---|---|---|
| `lag_96` (1 ngày trước) | Tính chu kỳ ngày rất mạnh trong giao thông | 🔴 Cao |
| `lag_672` (1 tuần trước) | Tính chu kỳ tuần (Thứ 2 rush hour ≠ Chủ nhật) | 🔴 Cao |
| `rolling_std_3` | Đo mức biến động — phát hiện đột biến | 🟡 Trung bình |
| `diff_1` (first difference) | Xu hướng tăng/giảm ngắn hạn | 🟡 Trung bình |
| `month` hoặc `month_sin/cos` | Tính mùa vụ (Tết, mùa hè, khai giảng...) | 🟡 Trung bình |
| `is_holiday` | Dataset gốc có sẵn cột `holiday`! | 🔴 Cao |
| `temp`, `rain_1h` | Ảnh hưởng mạnh đến giao thông | 🟡 Trung bình |

### 3.2. Vấn Đề Data Leakage Tiềm Ẩn

> [!CAUTION]
> **`rolling_mean_3` sử dụng `shift(1)` đúng** — tốt, tránh được look-ahead bias. Tuy nhiên, trong hàm [create_features](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/traffic_predictor.py#L53-L83), target variable `vehicle_count` được dùng trực tiếp để tạo lag features trên CÙNG DataFrame. Khi train toàn bộ dữ liệu (dòng 117: `self.model.fit(X, y)`), lag features đã "nhìn thấy" giá trị thực của các điểm lân cận → **metric bị inflate**. MAE = 6.69 xe (~1.6%) có thể **quá lạc quan** so với real-world performance.

### 3.3. LightDeltaModel — Chỉ Dùng 3-Fold CV Thường

Mô hình đèn xanh sử dụng `cross_val_score` (3-fold) — đây là **shuffle k-fold**, không phải `TimeSeriesSplit`. Nếu dữ liệu có yếu tố thời gian (hour, day_of_week), điều này tạo data leakage vì fold train có thể chứa dữ liệu "tương lai" so với fold test.

---

## 4. Đánh Giá Phương Pháp Đánh Giá (Evaluation)

### 4.1. TrafficPredictor

| Tiêu chí | Đánh giá | Chi tiết |
|---|---|---|
| TimeSeriesSplit (5-fold) | ✅ Đúng | Tránh data leakage thời gian |
| Metrics: MAE, RMSE | ✅ Phù hợp | |
| R², MAPE | ❌ Thiếu | Nên bổ sung để đánh giá toàn diện hơn |
| Out-of-sample test | ❌ **Thiếu** | Không hold-out test set cuối cùng |
| Visualization | ❌ **Thiếu** | Không có biểu đồ actual vs predicted |
| Residual analysis | ❌ **Thiếu** | Không kiểm tra phân phối sai số |

> [!WARNING]
> **Vấn đề lớn:** Sau khi cross-validation, model được **fit lại trên toàn bộ dữ liệu** (dòng 117) mà không giữ lại test set nào. Điều này có nghĩa:
> 1. Không có cách kiểm chứng model cuối cùng (model production ≠ model trong CV folds)
> 2. Kết quả MAE 6.69 xe là từ CV, nhưng model thực tế đang dùng được fit trên 100% data — **không thể verify**

### 4.2. LightDeltaModel

| Tiêu chí | Đánh giá |
|---|---|
| Cross-validation | ⚠️ 3-fold (nên dùng TimeSeriesSplit nếu có temporal order) |
| In-sample MAE | ❌ **Vô nghĩa** — 0.19s trên 500 mẫu random → model đã overfit hoàn toàn trên data giả |
| Dữ liệu test thực | ❌ **Không có** |

---

## 5. Đánh Giá Pipeline Xử Lý Dữ Liệu

### 5.1. Resample Hourly → 15-min

```python
# train.py dòng 22-31
df['traffic_volume_15min'] = df['traffic_volume'] / 4
series = df['traffic_volume_15min'].groupby(df.index).mean()
         .resample('15min').asfreq().interpolate(method='time')
```

| Bước | Đánh giá |
|---|---|
| Chia ÷4 | ⚠️ Giả định giao thông phân bố đều trong 1 giờ → **sai thực tế** (15 phút cuối giờ cao điểm có thể đông gấp đôi 15 phút đầu) |
| `interpolate('time')` | ⚠️ Tạo dữ liệu "giả" — 3/4 số record là nội suy, không phải dữ liệu thật |
| `groupby().mean()` xử lý trùng lặp | ✅ Hợp lý |

> [!WARNING]
> **~75% dữ liệu training là dữ liệu nội suy**, không phải đo thực tế. Điều này khiến:
> - Lag features (`lag_1`, `lag_2`) học pattern nội suy thay vì pattern thật
> - Metric evaluation bị inflate vì giá trị nội suy có tương quan cao tự nhiên
> - Model sẽ hoạt động kém hơn đáng kể khi gặp dữ liệu thực (có noise, có đột biến)

### 5.2. Scale Factor Cố Định

```python
SCALE_FACTOR = 450.0 / 815.0   # ≈ 0.55
```

Cách tiếp cận này:
- ✅ Đơn giản, dễ hiểu
- ❌ Giả định linear scaling (nhân đều tất cả) — không thực tế
- ❌ Không thay đổi variance, skewness, hoặc pattern phân phối
- ❌ Giao thông Mỹ và VN có phân phối fundamentally khác nhau

---

## 6. Đánh Giá Phần Inference (Dự Báo Thực Tế)

### 6.1. Prediction Service

File [prediction_service.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/backend/services/prediction_service.py):

| Tiêu chí | Đánh giá |
|---|---|
| Fallback khi < 5 data points | ✅ Tốt — dùng trung bình cộng |
| Load model singleton | ⚠️ Mỗi request gọi `_load_predictors()` → không cache |
| Error handling | ✅ Có try/except |
| Kết quả lưu MongoDB | ✅ Traceability tốt |

### 6.2. Green Light Time — Logic Trùng Lặp và Mâu Thuẫn

> [!CAUTION]
> **Có 2 cơ chế tính thời gian đèn xanh hoàn toàn khác nhau:**
>
> 1. **`prediction_service.py` → `_compute_green_light_time()`** (dòng 118-141): Rule-based đơn giản, clamp [30, 45] giây
> 2. **`LightDeltaModel` → `predict_delta()`**: ML-based, baseline + delta, clamp [-30, +45]
>
> Hai cơ chế này **không liên kết** với nhau. Backend API trả về `green_light_time` từ cơ chế 1, trong khi `system_runner.py` dùng cơ chế 2 thông qua `TrafficLightOptimizer`. Kết quả: **frontend có thể nhận 2 giá trị khác nhau** tùy vào endpoint nào được gọi.

### 6.3. Hàm Classify Congestion — Ngưỡng Không Nhất Quán

| Nơi sử dụng | LOW | MEDIUM | HIGH | SEVERE |
|---|---|---|---|---|
| [traffic_predictor.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/ml_service/traffic_predictor.py#L12-L23) dòng 12 | < 200 | < 350 | < 500 | ≥ 500 |
| [aggregation_service.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/backend/services/aggregation_service.py#L16-L27) dòng 16 | < 200 | < 350 | < 500 | ≥ 500 |
| [system_runner.py](file:///Users/cuongvuthanh/Documents/TTCS/traffic-density-analysis-system/integration_system/system_runner.py#L61-L72) dòng 64 | < 15 | < 30 | < 50 | ≥ 50 |

> [!WARNING]
> `CongestionClassifier` trong `system_runner.py` dùng ngưỡng **hoàn toàn khác** (15/30/50) so với các module khác (200/350/500). Có vẻ như `system_runner.py` đếm xe **theo mỗi cycle 5 giây**, trong khi `traffic_predictor.py` đếm **theo 15 phút**. Nhưng điều này **không được document** và có thể gây nhầm lẫn nghiêm trọng.

---

## 7. Đánh Giá Code Quality

### 7.1. Điểm Mạnh

- ✅ **Docstring đầy đủ** (tiếng Việt, dễ hiểu)
- ✅ **README rất chi tiết** — giải thích lý do lựa chọn thuật toán
- ✅ **Kiến trúc rõ ràng** — tách biệt train/predict/service
- ✅ **Error handling** có trong hầu hết các hàm
- ✅ **Fallback mechanism** khi model chưa sẵn sàng

### 7.2. Điểm Yếu

- ❌ **Không có unit test** cho bất kỳ module ML nào
- ❌ **Không có logging** — chỉ dùng `print()` khắp nơi
- ❌ **Không có model versioning** — `model.pkl` bị ghi đè mỗi lần train
- ❌ **Không có data validation** — hàm `create_features` không validate input
- ❌ **Duplicate code** — hàm `to_object()` copy-paste giữa 2 file service
- ❌ **Hardcoded paths** — `model.pkl`, `light_model.pkl` hardcode tên file

---

## 8. Tổng Hợp Vấn Đề Theo Mức Độ

### 🔴 Nghiêm Trọng (Cần Khắc Phục Ngay)

| # | Vấn đề | Ảnh hưởng |
|---|---|---|
| 1 | **Dataset không đại diện** — xa lộ Mỹ ≠ đô thị VN | Model học sai pattern giao thông |
| 2 | **~75% data là nội suy** — metric bị inflate | MAE 6.69 xe **không đáng tin** — real-world sẽ cao hơn nhiều |
| 3 | **LightDeltaModel train trên data giả** | Model đèn xanh **vô dụng trong thực tế** |
| 4 | **Không có held-out test set** | Không thể đánh giá chính xác model production |
| 5 | **Logic đèn xanh mâu thuẫn** giữa backend API và integration system | Frontend nhận kết quả không nhất quán |

### 🟡 Quan Trọng (Nên Khắc Phục)

| # | Vấn đề | Ảnh hưởng |
|---|---|---|
| 6 | Không hyperparameter tuning | Có thể cải thiện 10-30% performance |
| 7 | Thiếu lag dài hạn (1 ngày, 1 tuần) | Bỏ lỡ tính chu kỳ mạnh nhất của giao thông |
| 8 | Feature thời tiết/holiday bị bỏ | Lãng phí thông tin có sẵn trong dataset |
| 9 | Ngưỡng congestion không nhất quán | Gây nhầm lẫn và bug tiềm ẩn |
| 10 | Không có early stopping | Nguy cơ overfitting |

### 🟢 Cải Thiện (Nice to Have)

| # | Vấn đề | Ảnh hưởng |
|---|---|---|
| 11 | Thiếu unit tests | Khó maintain và debug |
| 12 | Dùng `print()` thay logging | Không kiểm soát được log level |
| 13 | Không model versioning | Mất khả năng rollback |
| 14 | Thiếu visualization (actual vs predicted plot) | Khó debug và trình bày kết quả |
| 15 | Thiếu MAPE, R² metrics | Đánh giá chưa toàn diện |

---

## 9. Khuyến Nghị Cải Thiện Cụ Thể

### 9.1. Dataset (Ưu tiên #1)

```diff
- Dùng Metro Interstate Traffic Volume (xa lộ Mỹ)
+ Thu thập dữ liệu thực từ camera hệ thống (dù chỉ 1-2 tuần)
+ Hoặc tìm dataset đô thị châu Á (VD: Kaggle "Urban Traffic Density")
+ Hoặc sử dụng file urban_traffic.csv đã có sẵn (200 records) để augment
```

### 9.2. Feature Engineering Bổ Sung

```python
# Thêm vào create_features():

# Lag dài hạn — chu kỳ ngày và tuần
data['lag_96']  = data['vehicle_count'].shift(96)   # cùng giờ hôm qua (96 x 15min = 24h)
data['lag_672'] = data['vehicle_count'].shift(672)   # cùng giờ cùng thứ tuần trước

# First difference — xu hướng
data['diff_1'] = data['vehicle_count'].diff(1)

# Rolling volatility
data['rolling_std_3'] = data['vehicle_count'].shift(1).rolling(window=3).std()

# Holiday flag (nếu dùng dataset Metro)
data['is_holiday'] = (data['holiday'] != 'None').astype(int)
```

### 9.3. Hyperparameter Tuning

```python
from sklearn.model_selection import RandomizedSearchCV

param_dist = {
    'n_estimators': [100, 200, 300, 500],
    'max_depth': [3, 4, 5, 6, 8],
    'learning_rate': [0.01, 0.03, 0.05, 0.1],
    'subsample': [0.7, 0.8, 0.9],
    'colsample_bytree': [0.7, 0.8, 0.9],
    'min_child_weight': [1, 3, 5],
    'reg_alpha': [0, 0.1, 1],
    'reg_lambda': [1, 1.5, 2],
}

search = RandomizedSearchCV(
    xgb.XGBRegressor(objective='reg:squarederror', random_state=42),
    param_distributions=param_dist,
    n_iter=50,
    cv=TimeSeriesSplit(n_splits=5),
    scoring='neg_mean_absolute_error',
    random_state=42,
)
search.fit(X, y)
best_model = search.best_estimator_
```

### 9.4. Evaluation Đúng Cách

```python
# Hold-out 20% cuối làm test set TRƯỚC khi CV
split_idx = int(len(data) * 0.8)
train_data = data[:split_idx]
test_data  = data[split_idx:]

# CV trên train_data
# Final evaluation trên test_data (KHÔNG dùng để train)

# Thêm metrics
from sklearn.metrics import r2_score, mean_absolute_percentage_error
r2 = r2_score(y_test, y_pred)
mape = mean_absolute_percentage_error(y_test, y_pred)
```

### 9.5. Thống Nhất Logic Đèn Xanh

```diff
- 2 cơ chế tính green_light_time riêng biệt
+ 1 module duy nhất: ml_service/light_delta_model.py
+ prediction_service.py gọi LightDeltaModel.predict_delta() thay vì _compute_green_light_time()
+ Xóa hàm _compute_green_light_time() trong prediction_service.py
```

---

## 10. Điểm Đánh Giá Tổng Thể

| Hạng mục | Điểm (1-10) | Ghi chú |
|---|---|---|
| **Lựa chọn thuật toán** | 7/10 | XGBoost hợp lý, nhưng chưa so sánh với alternatives |
| **Dataset** | 4/10 | Không đại diện, nội suy quá nhiều |
| **Feature Engineering** | 6/10 | Có tư duy tốt (sin/cos, lag, rolling) nhưng thiếu nhiều feature quan trọng |
| **Evaluation** | 5/10 | TimeSeriesSplit đúng, nhưng không hold-out test và thiếu metrics |
| **Code Quality** | 7/10 | Clean, documented, nhưng thiếu test và logging |
| **Pipeline tích hợp** | 5/10 | Logic trùng lặp và mâu thuẫn giữa các module |
| **Production Readiness** | 4/10 | Không model versioning, không monitoring, không A/B test |
| **Tổng thể** | **5.4/10** | Có nền tảng tốt, cần cải thiện đáng kể ở dataset và evaluation |

---

> [!TIP]
> **Lộ trình ưu tiên gợi ý:**
> 1. 🔴 Thu thập dữ liệu thực từ camera (dù chỉ 1 tuần) → train lại model
> 2. 🔴 Tách held-out test set → đánh giá đúng performance thực
> 3. 🟡 Bổ sung lag dài hạn + holiday features
> 4. 🟡 Hyperparameter tuning với RandomizedSearchCV
> 5. 🟡 Thống nhất logic đèn xanh giữa backend và integration
> 6. 🟢 Thêm unit tests, logging, model versioning
