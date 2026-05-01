# 🤖 ML Service – Dự báo Lưu lượng & Điều phối Đèn Giao thông

Thư mục này chứa toàn bộ logic Machine Learning của hệ thống phân tích mật độ giao thông. Gồm hai mô hình XGBoost hoạt động song song: **Model 1** dự báo số lượng xe cho khung 15 phút tiếp theo, và **Model 2** đề xuất điều chỉnh thời gian đèn xanh (`delta_green`) dựa trên tình trạng giao thông thực tế.

---

## 📁 Cấu trúc thư mục

```
ml_service/
├── data/
│   ├── urban_traffic.csv          # Dataset gốc (dữ liệu đô thị công khai)
│   └── training_data_delta.csv    # Dataset đã xử lý – dùng để train Model 2
│
├── label_generator.py    # Bước tiền xử lý: scale data + tạo nhãn delta_green
├── traffic_predictor.py  # Model 1: XGBoost dự báo số lượng xe (15 phút tới)
├── light_delta_model.py  # Model 2: XGBoost đề xuất điều chỉnh đèn xanh
├── train.py              # Script huấn luyện cả 2 model, xuất file .pkl
├── predict.py            # Client CLI: gọi API backend để lấy kết quả dự báo
│
├── model.pkl             # Model 1 đã huấn luyện (TrafficPredictor)
└── light_model.pkl       # Model 2 đã huấn luyện (LightDeltaModel)
```

---

## 🧠 Chức năng chính

### Model 1 – `TrafficPredictor` (Dự báo số lượng xe)
- **Đầu vào:** Lịch sử số lượng xe theo từng khung 15 phút (ít nhất 3 quan trắc).
- **Đầu ra:** Số lượng xe dự báo cho **15 phút tiếp theo**.
- **Ứng dụng:** Backend gọi dự báo này để hiển thị mật độ tương lai lên dashboard.

### Model 2 – `LightDeltaModel` (Điều phối đèn giao thông)
- **Đầu vào:** Số xe hiện tại, mức thay đổi so với 15 phút trước (`queue_proxy`), giờ trong ngày.
- **Đầu ra:** `delta_green` (giây) – giá trị điều chỉnh thêm hoặc bớt vào pha đèn xanh.
- **Ứng dụng:** Cho phép hệ thống tự động gợi ý kéo dài/rút ngắn đèn xanh thay vì chu kỳ cố định.

---

## ⚙️ Pipeline xử lý dữ liệu & huấn luyện

### Bước 1 – Scale dữ liệu (`label_generator.py`)

Dataset gốc (`urban_traffic.csv`) có phân phối **thấp hơn thực tế ~2.2 lần**:

| Nguồn dữ liệu | `vehicle_count` trung bình / 15 phút |
|---|---|
| Dataset CSV | ~50 xe |
| Database thực tế | ~111 xe |

→ Áp dụng **Scale Factor = 111.0 / 50.2 ≈ 2.21** để kéo dữ liệu training khớp với phân phối thực tế, tránh mô hình học lệch và dự báo sai số lớn.

```python
SCALE_FACTOR = 111.0 / 50.2   # ≈ 2.21
df['inbound_count'] = (df['Vehicle_Count'] * SCALE_FACTOR).round().astype(int)
```

### Bước 2 – Tạo nhãn `delta_green` (heuristic)

```
queue_proxy = inbound_count(hiện tại) − inbound_count(15 phút trước)
```

| `queue_proxy` | `delta_green` | Ý nghĩa |
|---|---|---|
| > 15 | **+30s** | Tắc nặng → Tăng đèn xanh |
| > 5 | **+15s** | Hơi đông → Tăng nhẹ |
| -5 đến 5 | **0s** | Ổn định → Giữ nguyên |
| < -5 | **-15s** | Bắt đầu thoáng → Giảm nhẹ |
| < -15 | **-30s** | Đường vắng → Giảm mạnh |

### Bước 3 – Feature Engineering (`traffic_predictor.py`)

`TrafficPredictor` tự động tạo các đặc trưng từ chuỗi thời gian:

| Feature | Mô tả |
|---|---|
| `hour` | Giờ trong ngày (0–23) |
| `day_of_week` | Thứ trong tuần (0=Thứ 2, 6=Chủ nhật) |
| `is_peak_hour` | 1 nếu giờ cao điểm (7–9h, 17–19h), 0 nếu không |
| `lag_1` | Số xe của khung 15 phút trước |
| `lag_2` | Số xe của khung 30 phút trước |
| `rolling_mean_3` | Trung bình trượt 3 khung gần nhất |

### Bước 4 – Huấn luyện với Time Series Cross-Validation

Vì đây là **dữ liệu chuỗi thời gian**, không thể dùng random split thông thường (dễ rò rỉ dữ liệu tương lai vào quá khứ). Hệ thống sử dụng **TimeSeriesSplit (5 folds)** của scikit-learn để đảm bảo thứ tự thời gian được bảo toàn trong mỗi lần đánh giá.

```
Fold 1: Train [0..N₁]   → Test [N₁..N₂]
Fold 2: Train [0..N₂]   → Test [N₂..N₃]
...
Fold 5: Train [0..N₄]   → Test [N₄..N₅]
```

---

## 📊 Kết quả đạt được (sau khi chạy `train.py`)

### Model 1 – TrafficPredictor (XGBoost Regressor)

```
--- Training Model 1: Vehicle Forecast ---

[*] Quá trình huấn luyện và đánh giá bắt đầu...
 -> Kết quả đánh giá bằng Cross Validation (5 folds):
    - MAE trung bình:  8.57  (Lệch khoảng 9 xe)
    - RMSE trung bình: 11.23
 -> Đang cập nhật mô hình với toàn bộ dữ liệu...

[+] ĐÃ LƯU MÔ HÌNH THÀNH CÔNG VÀO FILE: ml_service/model.pkl
```

| Chỉ số | Giá trị | Ý nghĩa |
|---|---|---|
| **MAE** | ~8.57 xe | Sai số tuyệt đối trung bình mỗi dự báo |
| **RMSE** | ~11.23 xe | Phạt nặng hơn các lỗi dự báo lớn |
| **Thực tế vs Dự báo** | ~111 xe vs ~103–119 xe | Sai lệch trong phạm vi ±8% |

> ✅ Sau khi áp dụng Scale Factor 2.21, dự báo đã khớp với phân phối thực tế thay vì bị lệch hoàn toàn xuống ~41 xe.

### Model 2 – LightDeltaModel (XGBoost Regressor)

```
--- Training Model 2: Light Delta ---
 Đã tạo dữ liệu huấn luyện đèn tại: ml_service/data/training_data_delta.csv
✅ Đã huấn luyện và lưu Model Đèn tại: ml_service/light_model.pkl
```

| Đầu ra | Phạm vi | Ý nghĩa |
|---|---|---|
| `delta_green` | -30s → +45s | Số giây gợi ý điều chỉnh pha đèn xanh |
| Clamp an toàn | [-30, +45] | Tránh thay đổi quá cực đoan ảnh hưởng an toàn |

---

## 🚀 Cách chạy

### 1. Huấn luyện lại cả 2 model

```bash
# Từ thư mục gốc của dự án
python -m ml_service.train
```

### 2. Lấy kết quả dự báo từ backend (yêu cầu backend đang chạy)

```bash
# Đảm bảo backend đang chạy tại localhost:8000
uvicorn backend.main:app --reload

# Gọi dự báo
python -m ml_service.predict
```

**Kết quả mẫu từ `predict.py`:**
```
----------------------------------------
[*] Đang gọi API dự báo: http://127.0.0.1:8000/predict-next
    Camera ID : CAM_01
----------------------------------------
Camera             : CAM_01
Giá trị dự báo     : 109
Dự báo delta đèn   : +15 giây
Khung dự báo       : 15 phút
Nguồn dự báo       : ml_model
Thời điểm dự báo   : 2026-05-01T20:15:00
----------------------------------------
```

---

## 🔧 Cách điều chỉnh độ chính xác

Nếu mô hình dự báo **vẫn thấp hơn** thực tế → **tăng** `SCALE_FACTOR` trong `label_generator.py`.  
Nếu mô hình dự báo **cao hơn** thực tế → **giảm** `SCALE_FACTOR` xuống.

```python
# label_generator.py – dòng 24
SCALE_FACTOR = 111.0 / 50.2   # Thay đổi giá trị này rồi chạy lại train.py
```

---

## 📦 Thư viện phụ thuộc

| Thư viện | Mục đích |
|---|---|
| `xgboost` | Thuật toán Gradient Boosting cho cả 2 model |
| `scikit-learn` | TimeSeriesSplit, MAE/RMSE metrics |
| `pandas` | Xử lý dữ liệu dạng bảng, chuỗi thời gian |
| `numpy` | Tính toán mảng số học |
| `joblib` | Lưu/tải model dưới dạng file `.pkl` |
| `requests` | Client HTTP cho `predict.py` gọi backend |
