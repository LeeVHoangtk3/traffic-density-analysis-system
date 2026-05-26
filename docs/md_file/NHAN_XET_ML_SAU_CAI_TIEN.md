# 📝 Nhận Xét Phần ML Sau Cải Tiến

> **Ngày đánh giá:** 21/05/2026  
> **Phạm vi:** Toàn bộ phần ML gồm `ml_service/` và các module backend/integration liên quan  
> **Ngữ cảnh:** Hệ thống đếm xe qua video (không phải live camera), dữ liệu thực tế chỉ có vài khung 15 phút mỗi lần chạy, lưu trên MongoDB Atlas

---

## 1. Tổng Quan Sau Cải Tiến

Phần ML đã được cải tiến đáng kể so với phiên bản trước. Dưới đây là bảng so sánh:

| Tiêu chí | Trước cải tiến | Sau cải tiến |
|---|---|---|
| **Dataset** | Metro Interstate (xa lộ Mỹ, hourly) | NYC Automated Traffic Volume (đô thị, 15 phút) |
| **Dữ liệu thật** | ~25% (75% nội suy giả) | **100%** — không có nội suy |
| **Scale Factor** | ×0.55 (tuỳ tiện) | **Đã loại bỏ** |
| **Held-out Test Set** | ❌ Không có | ✅ 20% cuối (chronological) |
| **Early Stopping** | ❌ Không | ✅ `early_stopping_rounds=20` |
| **Metrics** | Chỉ MAE, RMSE (trên CV) | MAE, RMSE, **R², MAPE** (cả CV lẫn held-out) |
| **Features** | 10 | **12** (thêm `rolling_std_3`, `diff_1`, `day_of_week_sin/cos`) |
| **Ngưỡng congestion** | Không nhất quán (3 module khác nhau) | **Đồng bộ 100%** (30/100/200) |

### Kết quả huấn luyện hiện tại

| Metric | Cross-Validation (Train) | Held-out Test (20%) |
|---|---|---|
| MAE | 7.12 xe | **4.76 xe** |
| RMSE | 13.91 xe | **8.31 xe** |
| R² | — | **0.9895** |
| MAPE | — | **3.89%** |

---

## 2. Ưu Điểm (Đã Làm Tốt) ✅

### 2.1. Dataset phù hợp hơn nhiều
Dataset NYC Automated Traffic Volume là dữ liệu **đường phố đô thị** (không phải xa lộ), ghi nhận trực tiếp mỗi 15 phút — hoàn toàn phù hợp với bài toán đếm xe trên đường phố. Không còn phải nội suy 75% dữ liệu giả.

### 2.2. Pipeline huấn luyện chuẩn mực
- **Train/Test split theo thời gian** (80/20 chronological) — đúng chuẩn cho time series.
- **TimeSeriesSplit 5-fold** trên tập train — đánh giá cross-validation không bị data leakage.
- **Early stopping** ngăn overfitting hiệu quả.
- Báo cáo đầy đủ 4 metrics (MAE, RMSE, R², MAPE) trên held-out test.

### 2.3. Feature Engineering hợp lý
- **Cyclical encoding** (sin/cos) cho cả giờ và ngày trong tuần — giải quyết vấn đề giờ 23 ≠ giờ 0.
- **Rolling std** — nắm bắt mức độ biến động.
- **diff_1** — phát hiện xu hướng tăng/giảm ngắn hạn.

### 2.4. Ngưỡng congestion đồng bộ
Ba module (`traffic_predictor.py`, `aggregation_service.py`, `system_runner.py`) đều sử dụng cùng ngưỡng 30/100/200. Đây là điểm đáng khen vì trước đó ba module có ba bộ ngưỡng khác nhau.

### 2.5. Fallback thông minh
Khi DB chưa đủ 5 bản ghi, hệ thống tự động fallback về trung bình cộng thay vì crash — rất phù hợp với thực tế chạy video ngắn.

---

## 3. Khuyết Điểm Còn Tồn Tại ⚠️

### 3.1. 🔴 NGHIÊM TRỌNG — R² = 0.99 có thể là dấu hiệu Data Leakage

**Vấn đề:** R² = 0.9895 là một con số **cực kỳ cao** cho bài toán dự báo giao thông. Trong thực tế nghiên cứu, R² cho traffic forecasting thường nằm trong khoảng **0.75 – 0.92**. Con số 0.99 gợi ý rằng mô hình có thể đang "gian lận" theo cách sau:

**Nguyên nhân gốc:** Dữ liệu SegmentID `72887` gồm 13,398 records nhưng **không phải là một chuỗi thời gian liên tục**. Đây là dữ liệu khảo sát rời rạc (mỗi đợt khảo sát chỉ kéo dài vài ngày). Khi sắp xếp theo thời gian rồi tính `lag_1`, `lag_2`, `lag_4`:

- **Trong cùng một đợt khảo sát** (liền nhau): lag values chính xác → model dự đoán tốt.
- **Giữa hai đợt khảo sát** (cách nhau vài tháng): lag values hoàn toàn sai (lấy giá trị của đợt khảo sát trước, cách xa hàng tháng) → model vẫn train trên data này mà không phát hiện.

Khi train, `dropna()` loại bỏ 4 dòng đầu tiên của **toàn bộ dataset** (chỉ 4 dòng) nhưng đáng ra phải loại bỏ 4 dòng đầu **mỗi đợt khảo sát**.

**Mức độ ảnh hưởng:** Trung bình — trong thực tế predict, hệ thống chỉ truyền lịch sử liên tục từ DB nên lag values đúng. Vấn đề chỉ ảnh hưởng đến **độ tin cậy của metrics training** (metrics trông đẹp hơn thực tế).

**Đề xuất cải thiện:**
```python
# Trong train.py, sau khi sort theo timestamp:
# Phát hiện các "gap" lớn hơn 30 phút giữa các dòng liên tiếp
df['time_diff'] = df['timestamp'].diff()
df['is_new_survey'] = (df['time_diff'] > pd.Timedelta(minutes=30)).astype(int)

# Đánh dấu session_id cho mỗi đợt khảo sát liên tục
df['session_id'] = df['is_new_survey'].cumsum()

# Tính lag features theo từng session, không xuyên session
for session_id, group in df.groupby('session_id'):
    df.loc[group.index, 'lag_1'] = group['vehicle_count'].shift(1)
    # ... tương tự cho lag_2, lag_4, rolling, diff
```

---

### 3.2. 🟡 Ngưỡng Congestion chưa được validate bằng dữ liệu

**Vấn đề:** Ngưỡng 30/100/200 được chọn dựa trên **phân vị thống kê** của toàn bộ dataset (gồm tất cả ~4,355 segments), nhưng SegmentID `72887` được chọn để train có trung bình **192 xe/15p** — cao gần gấp đôi trung bình toàn dataset (102 xe).

Điều này có nghĩa là với dữ liệu train:
- ~50% trường hợp sẽ là **HIGH** hoặc **SEVERE**
- Rất ít trường hợp **LOW**

Ngưỡng 30/100/200 phù hợp với toàn bộ dataset nhưng có thể không phản ánh đúng thực tế của segment cụ thể này.

**Đề xuất:** Không cần thay đổi ngưỡng ngay, nhưng nên ghi chú rằng ngưỡng này là tạm thời và cần được hiệu chỉnh khi triển khai với dữ liệu thực tế camera.

---

### 3.3. 🟡 `vehicle_count = 0` khi tạo future row gây nhiễu diff_1

**Vấn đề:** Trong hàm `predict()` (dòng 208-212), khi tạo dòng giả cho thời điểm tương lai:

```python
future_row = pd.DataFrame([{'timestamp': next_time, 'vehicle_count': 0}])
```

Giá trị `vehicle_count = 0` này sẽ bị dùng để tính `diff_1` cho dòng tương lai:
```
diff_1 = 0 - (giá trị thật cuối cùng)  →  luôn là số âm lớn
```

Điều này khiến model luôn nhận tín hiệu "giao thông đang giảm mạnh" khi predict, dẫn đến **dự báo thấp hơn thực tế** (under-prediction bias).

**Đề xuất cải thiện:**

```python
# Thay vì vehicle_count = 0, dùng giá trị cuối cùng (forward-fill)
last_count = int(df['vehicle_count'].iloc[-1])
future_row = pd.DataFrame([{'timestamp': next_time, 'vehicle_count': last_count}])
```

---

### 3.4. 🟡 `_compute_green_light_time()` logic thiếu tính thực tế

**Vấn đề:** Hàm tính thời gian đèn xanh (prediction_service.py, dòng 118-141) dùng **chênh lệch % so với trung bình lịch sử** để tăng/giảm thời gian đèn. Nhưng:

1. `history` chỉ có 8 records gần nhất (có thể toàn bộ nằm trong 1 giờ) → trung bình rất không ổn định.
2. Mỗi 10% chênh lệch = 5 giây → nếu predicted = 200 và avg = 100, thì delta = +50s, bị clamp thành 60s.
3. Nếu predicted = 10 và avg = 100, thì delta = -45s, bị clamp thành 20s.

Khoảng dao động thực tế rất hẹp (20-60 giây) trong khi logic quá nhạy với biến động.

**Đề xuất:** Đơn giản hoá bằng bảng tra theo mức congestion thay vì tính toán phức tạp:

```python
_GREEN_MAP = {"Low": 25, "Medium": 35, "High": 45, "Severe": 55}

def _compute_green_light_time(predicted_density, history):
    from backend.services.aggregation_service import compute_congestion
    level = compute_congestion(int(predicted_density))
    return _GREEN_MAP.get(level, 30)
```

---

### 3.5. 🟢 NHỎ — `classify_congestion()` trả về UPPERCASE nhưng `compute_congestion()` trả về Titlecase

**Vấn đề:**
- `traffic_predictor.py` → `classify_congestion()` trả về `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"SEVERE"`
- `aggregation_service.py` → `compute_congestion()` trả về `"Low"`, `"Medium"`, `"High"`, `"Severe"`

Hai hàm có cùng logic nhưng khác format output. Trong `prediction_service.py` dòng 155-156, congestion_level được lấy từ `compute_congestion()` (Titlecase). Nhưng nếu ai đó dùng `classify_congestion()` sẽ nhận UPPERCASE → gây nhầm lẫn.

**Đề xuất:** Thống nhất thành một hàm duy nhất. Xoá `classify_congestion()` trong `traffic_predictor.py` và import `compute_congestion()` từ `aggregation_service`:

```python
# traffic_predictor.py
from backend.services.aggregation_service import compute_congestion as classify_congestion
```

Hoặc đơn giản hơn: sửa `classify_congestion()` trả về Titlecase để khớp.

---

### 3.6. 🟢 NHỎ — Thiếu logging cho quá trình predict

**Vấn đề:** Hàm `predict()` không in bất kỳ log nào khi chạy. Khi debug production, không biết model đang dùng bao nhiêu history, fallback hay ML, features có giá trị gì.

**Đề xuất:** Thêm logging cơ bản:

```python
import logging
logger = logging.getLogger(__name__)

# Trong predict():
logger.info(f"Predicting with {len(df)} history records")
logger.debug(f"Last 3 counts: {df['vehicle_count'].tail(3).tolist()}")
```

---

## 4. Tóm Tắt Đánh Giá

| Hạng mục | Điểm | Ghi chú |
|---|---|---|
| **Dataset** | 9/10 | Phù hợp, đủ lớn, dữ liệu thật 100% |
| **Pipeline Training** | 8/10 | Chuẩn mực, có held-out test + early stopping |
| **Feature Engineering** | 7/10 | Tốt, nhưng bug `vehicle_count = 0` ở future row |
| **Evaluation** | 6/10 | Metrics đầy đủ nhưng R² = 0.99 đáng nghi (cross-session leakage) |
| **Code Quality** | 7/10 | Sạch, có docstring, nhưng thiếu logging và case inconsistency |
| **Integration** | 8/10 | Ngưỡng đồng bộ, fallback hợp lý |
| **Tổng thể** | **7.5/10** | Cải thiện rất lớn so với phiên bản cũ |

---

## 5. Các Bước Cải Thiện Ưu Tiên

Thứ tự theo mức độ quan trọng và dễ triển khai:

| # | Cải thiện | Độ khó | Ảnh hưởng |
|---|---|---|---|
| 1 | Sửa `future_row` dùng `last_count` thay vì 0 | ⭐ Dễ | 🔴 Cao — fix under-prediction bias |
| 2 | Thống nhất format congestion level (Titlecase) | ⭐ Dễ | 🟡 Trung bình |
| 3 | Phát hiện và tách session khảo sát trong train.py | ⭐⭐ Vừa | 🔴 Cao — metrics chính xác hơn |
| 4 | Thêm logging cơ bản | ⭐ Dễ | 🟢 Hữu ích khi debug |
| 5 | Đơn giản hoá `_compute_green_light_time` | ⭐ Dễ | 🟡 Trung bình |
