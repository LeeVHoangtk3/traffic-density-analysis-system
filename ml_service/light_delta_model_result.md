# 📊 Kết Quả Chạy: LightDeltaModel

> **File:** `ml_service/light_delta_model.py`  
> **Thời gian chạy:** 2026-04-30 00:11 (GMT+7)  
> **Lệnh:** `python -m ml_service.light_delta_model`

---

## 1. Tổng Quan Module

`LightDeltaModel` là mô hình **XGBoost Regressor độc lập** dùng để đề xuất điều chỉnh thời gian đèn xanh (`delta_green`) theo giây.

### Features đầu vào

| Feature | Ý nghĩa | Kiểu |
|---|---|---|
| `queue_proxy` | Ước tính độ dài hàng đợi (xe) | `float` |
| `inbound_count` | Lưu lượng xe vào giao lộ trong chu kỳ | `int` |
| `congestion_level` | Mức độ tắc nghẽn | `str` ('low' / 'medium' / 'high') |
| `baseline_green` | Thời gian đèn xanh cơ bản của pha (giây) | `int` |
| `hour` | Giờ trong ngày | `int` (0–23) |
| `day_of_week` | Thứ trong tuần | `int` (0=Thứ Hai … 6=Chủ Nhật) |

### Target

| Target | Ý nghĩa | Giới hạn an toàn |
|---|---|---|
| `delta_green` | Số giây cần điều chỉnh thêm | `-30s` đến `+45s` |

---

## 2. Kết Quả Huấn Luyện (Demo — 500 mẫu giả)

```
[LightDeltaModel] Bắt đầu huấn luyện Model Đèn...
  → Tổng số mẫu: 500  |  Phân phối target (delta_green):
     min=-30.0s  max=30.0s  mean=5.82s  std=20.46s
  → Cross-val MAE (3-fold): 0.83s ± 0.14s
  → MAE toàn bộ tập (in-sample): 0.19s
  ✅ Đã lưu Model Đèn tại: light_model_demo.pkl
```

### Diễn giải

| Chỉ số | Giá trị | Ý nghĩa |
|---|---|---|
| **Số mẫu** | 500 | Tổng số bản ghi dữ liệu demo |
| **min delta** | -30.0s | Trường hợp giảm đèn xanh tối đa |
| **max delta** | +30.0s | Trường hợp tăng đèn xanh tối đa |
| **mean delta** | +5.82s | Trung bình cần tăng nhẹ đèn xanh |
| **std delta** | 20.46s | Độ lệch chuẩn lớn → dữ liệu phân tán nhiều mức |
| **Cross-val MAE** | **0.83s ± 0.14s** | ✅ Sai số trung bình trên tập kiểm tra (3-fold) |
| **In-sample MAE** | **0.19s** | Sai số trên toàn bộ tập huấn luyện |

> **Nhận xét:** Cross-val MAE ~0.83s rất tốt — mô hình sai lệch chưa đến 1 giây so với nhãn heuristic. In-sample MAE 0.19s cho thấy model khớp rất tốt với dữ liệu train (có thể do dữ liệu demo có pattern đơn giản).

---

## 3. Kết Quả Dự Đoán (Predict)

### Input mẫu

```python
{
    "queue_proxy":      18.0,    # Hàng đợi dài → nên tăng đèn xanh
    "inbound_count":    60,
    "congestion_level": "high",
    "baseline_green":   30,
    "hour":             8,       # Giờ cao điểm sáng
    "day_of_week":      1,       # Thứ Ba
}
```

### Output

```
Output : delta_green = +29.59s  (clamp [-30, +45])
```

> **Nhận xét:** Với tình huống hàng đợi dài (`queue_proxy=18`), tắc nghẽn cao (`high`), giờ cao điểm (8h sáng Thứ Ba), mô hình đề xuất **tăng thêm ~30 giây đèn xanh** — kết quả hợp lý.

---

## 4. Cấu Hình XGBoost

```python
{
    "n_estimators":    200,
    "learning_rate":   0.05,
    "max_depth":       4,
    "subsample":       0.8,
    "colsample_bytree": 0.8,
    "objective":       "reg:squarederror",
    "random_state":    42,
}
```

---

## 5. API Công Khai

```python
from ml_service.light_delta_model import train_delta, predict_delta

# 1. Huấn luyện
model = train_delta(df_training)

# 2. Dự đoán
delta = predict_delta({
    "queue_proxy":      12.5,
    "inbound_count":    45,
    "congestion_level": "high",
    "baseline_green":   30,
    "hour":             8,
    "day_of_week":      1,
})
print(f"Đề xuất điều chỉnh: {delta:+.1f}s")
```

---

## 6. File Được Tạo Ra

| File | Mô tả |
|---|---|
| `ml_service/light_model.pkl` | Model đã train, dùng cho production |
| `light_model_demo.pkl` | File demo tạm thời — **đã tự động xóa** sau khi chạy |
