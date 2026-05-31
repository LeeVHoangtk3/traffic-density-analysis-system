# 🤖 ML Service Module - Dự Báo & Tối Ưu Hóa Pha Đèn

**ML Service** là bộ não toán học của hệ thống. Module này xử lý tiền dữ liệu thô, huấn luyện mô hình dự báo lưu lượng XGBoost, tối ưu hóa phân bổ thời gian xanh dựa trên lưu lượng dự báo, và cung cấp API cho Backend để gọi dự báo real-time.

---

## 🏗️ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│      Raw Traffic Data (Automated_Traffic_Volume_...)        │
│      (286MB CSV: Year, Month, Day, Hour, Volume, Direction) │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  [Task 1] Tiền Xử Lý (preprocess.py)                       │
│  - Load & clean data                                        │
│  - Map segment + direction → (left, straight, right)        │
│  - Chuẩn hóa mốc 15 phút                                    │
│  - Resample & interpolate                                   │
│  Output: junction_pivot_clean.csv (xoay trục ngang)         │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  [Task 2] Kỹ Nghệ Đặc Trưng (traffic_predictor.py)         │
│  - Load clean data                                          │
│  - Trích đặc trưng time-series (lag, rolling stats)         │
│  - Thêm cyclical features (hour, day_of_week)               │
│  Output: Feature matrix X, Target y                         │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  [Task 3] Huấn Luyện (train.py)                            │
│  - Train/test split (chronological: 80% old, 20% recent)   │
│  - Train 3 XGBoost models (straight, left, right)           │
│  - Hyperparameter tuning                                    │
│  - Evaluate MAE, RMSE, MAPE                                 │
│  Output: model_straight.pkl, model_left.pkl, model_right.pkl│
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  [Task 5] Tối Ưu Hóa Pha Đèn (phase_optimizer.py)          │
│  - Nhận dự báo số xe 3 hướng                               │
│  - Phân bổ 80 giây xanh cho 2 pha:                          │
│    · Phase 1: straight + right                             │
│    · Phase 2: left                                         │
│  - Đảm bảo safety constraints                              │
│  Output: phase_1_green, phase_2_green (giây)               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  [Task 6] Bridge Model (light_delta_model.py)              │
│  - Adapter pattern tích hợp khép kín                        │
│  - Gọi 3 mô hình dự báo                                    │
│  - Gọi PhaseLightOptimizer                                 │
│  Output: delta_seconds (điều chỉnh so với baseline)        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  Backend API (GET /predict-next)                            │
│  - Lưu prediction vào MongoDB                               │
│  - Trả về cho integration_system                            │
│  - Trả về cho dashboard                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu Trúc Thư Mục

```
ml_service/
├── data/
│   ├── junction_pivot_clean.csv        # [Output Task 1] Dữ liệu sạch xoay trục
│   └── training_metrics.json           # [Output Task 9] Báo cáo đánh giá
│
├── model/
│   ├── model_straight.pkl              # [Output Task 3] XGBoost: dự báo direct straight
│   ├── model_left.pkl                  # [Output Task 3] XGBoost: dự báo direction left
│   ├── model_right.pkl                 # [Output Task 3] XGBoost: dự báo direction right
│   └── model.pkl                       # (deprecated) Single model cũ
│
├── helpers/
│   ├── predict.py                      # CLI test gọi /predict-next
│   ├── synthesize_data.py              # Sinh dữ liệu giả lập
│   ├── augment_data.py                 # Tăng cường dữ liệu
│   ├── preprocess_multi_junction.py    # Tiền xử lý thay thế (dự phòng)
│   └── data_evaluation.ipynb           # Phân tích EDA
│
├── preprocess.py                       # [Active Task 1]
├── traffic_predictor.py                # [Active Task 2]
├── train.py                            # [Active Task 3]
├── phase_optimizer.py                  # [Active Task 5]
├── light_delta_model.py                # [Active Task 6]
├── evaluate.py                         # [Active Task 9]
├── __init__.py
└── README.md
```

---

## 🔧 Chi Tiết Các File Chính

### 1. preprocess.py - Tiền Xử Lý Dữ Liệu

**Chức Năng:** Tải dữ liệu thô ~286MB, làm sạch, chuẩn hóa, xoay trục và lưu dữ liệu sạch.

**Workflow:**

```
Input: Automated_Traffic_Volume_Counts_20260521.csv (286MB)
  ├─ Đọc: Year, Month, Day, Hour, Minute, Volume, SegmentID, Direction
  ├─ Clean:
  │   ├─ Loại bỏ dấu phẩy từ cột Volume
  │   ├─ Convert sang int, loại NaN
  │   ├─ Lọc loại Vol < 0
  │   ├─ Chuẩn hóa mốc thời gian → 15 phút (00, 15, 30, 45)
  │   ├─ Xóa duplicates: groupby(SegmentID, Direction, timestamp) → mean()
  ├─ Phân tách 3 segment (138, 72887, 83624):
  │   ├─ Segment 138: NB→straight, WB→left, EB→right
  │   ├─ Segment 72887: EB→straight, WB→left
  │   ├─ Segment 83624: NB→straight, SB→left
  ├─ Xoay trục (pivot):
  │   └─ Index: timestamp | Columns: vol_straight, vol_left, vol_right
  ├─ Nội suy (interpolate):
  │   ├─ Tạo date_range đầy đủ 15 phút
  │   ├─ Interpolate tuyến tính mịn
  │   ├─ Forward fill / backward fill edge cases
  └─ Output: ml_service/data/junction_pivot_clean.csv
```

**Các Tham Số Quan Trọng:**

```python
raw_csv = "data/ml/Automated_Traffic_Volume_Counts_20260521.csv"
out_csv = "ml_service/data/junction_pivot_clean.csv"

# Segment mapping
segments_config = {
    138: {'mapping': {'NB': 'vol_straight', 'WB': 'vol_left', 'EB': 'vol_right'}},
    72887: {'mapping': {'EB': 'vol_straight', 'WB': 'vol_left'}},
    83624: {'mapping': {'NB': 'vol_straight', 'SB': 'vol_left'}},
}

# Nội suy
gap_threshold = pd.Timedelta(hours=24)  # Block separator
resample_freq = '15min'                 # Mốc 15 phút
interp_method = 'time'                  # Tuyến tính theo thời gian
min_block_length = 12                   # Loại block < 3 giờ
```

**Output Schema:**

```csv
timestamp,segment_id,vol_straight,vol_left,vol_right
2025-01-01 00:00:00,138,25,8,5
2025-01-01 00:15:00,138,27,9,6
...
```

---

### 2. traffic_predictor.py - Kỹ Nghệ Đặc Trưng

**Chức Năng:** Trích đặc trưng từ dữ liệu time-series để chuẩn bị input cho XGBoost.

**Class: `TrafficPredictor`**

```python
class TrafficPredictor:
    def __init__(self, lookback: int = 6):  # 6 mốc × 15min = 90 phút
        self.lookback = lookback
    
    def engineer_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        # Returns: (features X, target y)
```

**Đặc Trưng (Features):**

| Loại | Tên | Giải Thích |
|------|-----|-----------|
| **Lag (Quá khứ)** | `vol_straight_lag1` → `lag6` | Thể tích 15, 30, ..., 90 phút trước |
| | `vol_left_lag1` → `lag6` | - |
| | `vol_right_lag1` → `lag6` | - |
| **Rolling Stats** | `vol_straight_roll_mean_3` | Trung bình 45 phút (3×15min) |
| | `vol_straight_roll_std_3` | Độ lệch chuẩn 45 phút |
| **Cyclical** | `hour` | 0-23 |
| | `day_of_week` | 0-6 (Monday-Sunday) |
| | `hour_sin`, `hour_cos` | Mã hóa cyclical: sin(hour × 2π/24) |
| | `dow_sin`, `dow_cos` | sin(dow × 2π/7) |
| **Temporal** | `is_weekend` | 0/1 flag |
| | `month` | 1-12 |

**Ví Dụ Feature Vector cho 15 phút tiếp theo:**

```python
# Thực tế lúc 14:45
features = {
    'vol_straight_lag1': 45,    # 90min trước (14:15)
    'vol_straight_lag2': 48,    # 105min trước (14:00)
    'vol_straight_lag3': 50,    # ...
    'vol_straight_lag4': 47,
    'vol_straight_lag5': 49,
    'vol_straight_lag6': 46,    # 180min trước (12:15)
    'vol_left_lag1': 12,
    'vol_left_lag2': 13,
    ...
    'vol_right_lag1': 8,
    ...
    'hour': 14,
    'day_of_week': 2,           # Tuesday
    'hour_sin': sin(14/24 * 2π),
    'hour_cos': cos(14/24 * 2π),
    'dow_sin': sin(2/7 * 2π),
    'dow_cos': cos(2/7 * 2π),
    'is_weekend': 0,
    'month': 5
}
# → Dự báo: vol_straight cho 15:00
```

**Output:**

```python
X.shape  # (N_samples - lookback, n_features)
y.shape  # (N_samples - lookback,)
```

---

### 3. train.py - Huấn Luyện Mô Hình

**Chức Năng:** Huấn luyện 3 mô hình XGBoost độc lập (straight, left, right).

**Workflow:**

```python
# 1. Load dữ liệu sạch
df_clean = pd.read_csv("ml_service/data/junction_pivot_clean.csv")

# 2. Kỹ nghệ đặc trưng
predictor = TrafficPredictor(lookback=6)
X, y_straight = predictor.engineer_features(df_clean[['vol_straight']])
_, y_left = predictor.engineer_features(df_clean[['vol_left']])
_, y_right = predictor.engineer_features(df_clean[['vol_right']])

# 3. Train/Test Split (Chronological)
split_idx = int(len(X) * 0.8)  # 80% train, 20% test
X_train, X_test = X[:split_idx], X[split_idx:]
y_train_s, y_test_s = y_straight[:split_idx], y_straight[split_idx:]
y_train_l, y_test_l = y_left[:split_idx], y_left[split_idx:]
y_train_r, y_test_r = y_right[:split_idx], y_right[split_idx:]

# 4. Train 3 models
models = {}
for direction in ['straight', 'left', 'right']:
    model = xgb.XGBRegressor(
        n_estimators=100,      # Số cây
        max_depth=5,           # Độ sâu max
        learning_rate=0.1,     # Learning rate
        subsample=0.8,         # Subsample ratio
        colsample_bytree=0.8,  # Feature subsampling
        objective='reg:squarederror',
        random_state=42,
        verbosity=0
    )
    
    if direction == 'straight':
        model.fit(X_train, y_train_s, eval_set=[(X_test, y_test_s)])
    elif direction == 'left':
        model.fit(X_train, y_train_l, eval_set=[(X_test, y_test_l)])
    else:  # right
        model.fit(X_train, y_train_r, eval_set=[(X_test, y_test_r)])
    
    models[direction] = model
    
    # 5. Đánh giá
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test_*, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test_*, y_pred))
    mape = np.mean(np.abs((y_test_* - y_pred) / y_test_*)) * 100
    
    print(f"Direction {direction}:")
    print(f"  MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.2f}%")
    
    # 6. Lưu model
    with open(f"ml_service/model/model_{direction}.pkl", 'wb') as f:
        pickle.dump(model, f)
```

**Hyperparameters:**

| Tham Số | Giá Trị | Giải Thích |
|---------|--------|-----------|
| `n_estimators` | 100 | Số cây quyết định |
| `max_depth` | 5 | Độ sâu cây (tránh overfitting) |
| `learning_rate` | 0.1 | Shrinkage (regularization) |
| `subsample` | 0.8 | Dữ liệu per tree |
| `colsample_bytree` | 0.8 | Features per tree |
| `objective` | reg:squarederror | Hàm mục tiêu regression |

---

### 4. phase_optimizer.py - Tối Ưu Hóa Pha Đèn

**Chức Năng:** Phân bổ thời gian xanh 80 giây cho 2 pha giao thông dựa trên dự báo lưu lượng.

**Class: `PhaseLightOptimizer`**

```python
class PhaseLightOptimizer:
    def __init__(
        self,
        total_green_seconds: int = 80,      # Tổng giây xanh/cycle
        phase_1_min: int = 10,              # Min green cho pha 1
        phase_2_min: int = 10,              # Min green cho pha 2
    )
    
    def optimize(
        self,
        predicted_straight: int,
        predicted_left: int,
        predicted_right: int
    ) -> dict
    # Returns: {phase_1_green, phase_2_green, delta_straight, delta_left, delta_right}
```

**Logic Tối Ưu Hóa:**

```python
# Phase 1: Straight + Right
# Phase 2: Left

# Tính tỷ lệ flow
total_flow = predicted_straight + predicted_left + predicted_right
if total_flow == 0:
    total_flow = 1  # Tránh division by zero

flow_ratio_1 = (predicted_straight + predicted_right) / total_flow
flow_ratio_2 = predicted_left / total_flow

# Phân bổ xanh dựa tỷ lệ
available_green = total_green_seconds - phase_1_min - phase_2_min
phase_1_green = phase_1_min + int(available_green * flow_ratio_1)
phase_2_green = phase_2_min + int(available_green * flow_ratio_2)

# Ensure sum = total
if phase_1_green + phase_2_green != total_green_seconds:
    phase_1_green = total_green_seconds - phase_2_green

# Safety constraints
phase_1_green = max(phase_1_min, min(phase_1_green, total_green_seconds - phase_2_min))
phase_2_green = max(phase_2_min, min(phase_2_green, total_green_seconds - phase_1_min))
```

**Output:**

```json
{
  "phase_1_green": 52,       // Giây xanh cho straight + right
  "phase_2_green": 28,       // Giây xanh cho left
  "delta_straight": 5,       // Điều chỉnh so với baseline
  "delta_left": 0,
  "delta_right": 0
}
```

---

### 5. light_delta_model.py - Bridge Model

**Chức Năng:** Adapter pattern tích hợp khép kín để gọi dự báo và điều chỉnh pha đèn.

**Class: `LightDeltaModel`**

```python
class LightDeltaModel:
    def __init__(self, model_dir: str = "ml_service/model"):
        self.models = {
            'straight': pickle.load(open(f"{model_dir}/model_straight.pkl", 'rb')),
            'left': pickle.load(open(f"{model_dir}/model_left.pkl", 'rb')),
            'right': pickle.load(open(f"{model_dir}/model_right.pkl", 'rb')),
        }
        self.optimizer = PhaseLightOptimizer()
    
    def predict_delta(self, features: dict) -> dict:
        """
        Input features: {
            'timestamp': datetime,
            'hour': int,
            'day_of_week': int,
            'vol_straight_lag1-6': int,
            'vol_left_lag1-6': int,
            'vol_right_lag1-6': int,
            'vol_straight_roll_mean_3': float,
            ...
        }
        """
        # 1. Run predictions
        pred_straight = self.models['straight'].predict([features])[0]
        pred_left = self.models['left'].predict([features])[0]
        pred_right = self.models['right'].predict([features])[0]
        
        # 2. Optimize phase timing
        phase_timing = self.optimizer.optimize(
            pred_straight, pred_left, pred_right
        )
        
        # 3. Return delta
        return {
            'predictions': {
                'straight': int(pred_straight),
                'left': int(pred_left),
                'right': int(pred_right)
            },
            'phase_timing': phase_timing
        }
```

**Dùng từ Backend:**

```python
# backend/services/prediction_service.py
from ml_service.light_delta_model import LightDeltaModel

light_model = LightDeltaModel()

# Khi GET /predict-next
features = extract_features_from_aggregation(camera_id)
result = light_model.predict_delta(features)
# result.predictions: {straight: 48, left: 14, right: 9}
# result.phase_timing: {phase_1_green: 52, phase_2_green: 28, ...}
```

---

### 6. evaluate.py - Đánh Giá Mô Hình

**Chức Năng:** Đánh giá độ chính xác mô hình trên tập test, vẽ biểu đồ so sánh Actual vs Predicted.

**Metrics:**

| Chỉ Số | Công Thức | Giải Thích |
|--------|---------|-----------|
| **MAE** | $\frac{1}{n}\sum\|y_i - \hat{y}_i\|$ | Sai số tuyệt đối trung bình (cùng đơn vị với y) |
| **RMSE** | $\sqrt{\frac{1}{n}\sum(y_i - \hat{y}_i)^2}$ | Sai số bình phương trung bình |
| **MAPE** | $\frac{1}{n}\sum\frac{\|y_i - \hat{y}_i\|}{y_i} \times 100\%$ | Sai số phần trăm tuyệt đối (%) |
| **R²** | $1 - \frac{\sum(y_i - \hat{y}_i)^2}{\sum(y_i - \bar{y})^2}$ | Độ giải thích phương sai (0-1) |

**Output:**

```json
{
  "training_metrics": {
    "straight": {
      "mae": 3.2,
      "rmse": 4.1,
      "mape": 6.5,
      "r2": 0.87
    },
    "left": {
      "mae": 1.5,
      "rmse": 2.1,
      "mape": 8.2,
      "r2": 0.84
    },
    "right": {
      "mae": 0.8,
      "rmse": 1.2,
      "mape": 7.9,
      "r2": 0.89
    }
  }
}
```

**Biểu Đồ (Matplotlib):**

```
Actual vs Predicted - Direction: STRAIGHT
─────────────────────────────────────────
|                            pred
|                           /----\
|  actual              pred /      \
|  ────────────────────────        \───
| /                                     \
0  50  100  150  200  250  300  350  400 (giờ/days)
```

---

## ⚙️ Biến Môi Trường

```env
# Đường dẫn dữ liệu
ML_RAW_DATA=data/ml/Automated_Traffic_Volume_Counts_20260521.csv
ML_DATA_DIR=ml_service/data
ML_MODEL_DIR=ml_service/model

# Hyperparameters
XGB_N_ESTIMATORS=100
XGB_MAX_DEPTH=5
XGB_LEARNING_RATE=0.1

# Tối ưu hóa pha đèn
TOTAL_GREEN_SECONDS=80
PHASE_MIN_GREEN=10
```

---

## 🚀 Hướng Dẫn Chạy

### Step 1: Tiền Xử Lý

```bash
python ml_service/preprocess.py
```

**Output:** `ml_service/data/junction_pivot_clean.csv`

**Kiểm tra:**
```bash
head -5 ml_service/data/junction_pivot_clean.csv
# timestamp,segment_id,vol_straight,vol_left,vol_right
# 2025-01-01 00:00:00,138,25,8,5
# ...
```

### Step 2: Huấn Luyện

```bash
python ml_service/train.py
```

**Output:** 
- `ml_service/model/model_straight.pkl`
- `ml_service/model/model_left.pkl`
- `ml_service/model/model_right.pkl`

**Kiểm tra:**
```bash
ls -lah ml_service/model/model_*.pkl
# Mỗi file ~50-100KB
```

### Step 3: Đánh Giá (Optional)

```bash
python ml_service/evaluate.py
```

**Output:**
- `ml_service/data/training_metrics.json`
- `ml_service/data/predictions_straight.png`
- `ml_service/data/predictions_left.png`
- `ml_service/data/predictions_right.png`

### Step 4: Test CLI Predict

```bash
python ml_service/helpers/predict.py
# Output:
# Camera: CAM_01
# Predictions (next 15 min):
#   Straight: 48 vehicles
#   Left: 14 vehicles
#   Right: 9 vehicles
# Phase Timing:
#   Phase 1 (straight+right): 52 sec
#   Phase 2 (left): 28 sec
```

---

## 📊 Luồng Dữ Liệu Chi Tiết

```
[14:30] Backend GET /predict-next?camera_id=CAM_01
         ↓
[Backend] Trích lịch sử 6 mốc aggregation gần nhất
         ├─ 13:00, 13:15, 13:30, 13:45, 14:00, 14:15
         ├─ Extract: vol_straight, vol_left, vol_right
         ├─ Calculate: hour=14, day_of_week=2, ...
         └─ Build feature dict
         ↓
[Light Model] Gọi 3 mô hình XGBoost
         ├─ Model straight.predict(features) → 48
         ├─ Model left.predict(features) → 14
         ├─ Model right.predict(features) → 9
         ↓
[Phase Optimizer] Phân bổ 80 giây
         ├─ flow_ratio_1 = (48+9)/(48+14+9) = 0.663
         ├─ flow_ratio_2 = 14/(48+14+9) = 0.337
         ├─ phase_1_green = 10 + 60 × 0.663 = 50 sec
         ├─ phase_2_green = 10 + 60 × 0.337 = 30 sec
         ↓
[Backend] Lưu vào traffic_predictions
         ├─ camera_id: CAM_01
         ├─ prediction_period: 2026-05-31T14:30:00Z
         ├─ predictions: {straight: 48, left: 14, right: 9}
         ├─ phase_timing: {phase_1_green: 50, phase_2_green: 30}
         ↓
[Dashboard] Hiển thị dự báo & pha đèn tối ưu
```

---

## 🧪 Testing

### Test Preprocess

```python
from ml_service.preprocess import load_and_clean_data

df_clean = load_and_clean_data("data/ml/Automated_...")
print(df_clean.head())
print(df_clean.describe())
```

### Test Predictor

```python
from ml_service.traffic_predictor import TrafficPredictor
import pandas as pd

df = pd.read_csv("ml_service/data/junction_pivot_clean.csv")
predictor = TrafficPredictor(lookback=6)
X, y = predictor.engineer_features(df[['vol_straight']])
print(X.shape, y.shape)
```

### Test Light Model

```python
from ml_service.light_delta_model import LightDeltaModel

model = LightDeltaModel()
features = {
    'hour': 14,
    'day_of_week': 2,
    'vol_straight_lag1': 45,
    'vol_straight_lag2': 48,
    # ... thêm tất cả lag features
}
result = model.predict_delta(features)
print(result)
```

---

## 📈 Performance Tuning

| Vấn Đề | Nguyên Nhân | Giải Pháp |
|--------|-----------|---------|
| **Sai số cao (MAPE > 15%)** | Dữ liệu training thiếu hoặc quá đơn giản | Thêm dữ liệu, augment features |
| **Overfitting (train MAE << test MAE)** | Model quá phức tạp | Tăng `max_depth`, tăng regularization |
| **Dự báo lag (dự báo luôn xảy ra sau) | Lookback quá ngắn | Tăng `lookback` từ 6 → 8 hoặc 10 |
| **Pha đèn lúc nào cũng như nhau** | Model predictions không đa dạng | Kiểm tra dữ liệu training, kiểm tra features |

---

## 🐛 Troubleshooting

| Lỗi | Giải Pháp |
|-----|---------|
| `File not found: Automated_Traffic_Volume_Counts_...` | Download raw data → `data/ml/` |
| `ValueError: could not convert string to float` | CSV format lỗi, kiểm tra delimiter & encoding |
| `VRAM OOM` | Giảm batch size hoặc split dữ liệu |
| `Pickle error loading model` | Model pkl bị hỏng hoặc incompatible Python version |
| `Negative predictions` | Bình thường với regression, post-process: `max(0, pred)` |

---

## 📚 Tham Khảo

- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [Scikit-learn Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [Time Series Forecasting](https://machinelearningmastery.com/time-series-forecasting/)
- [ByteTrack Paper](https://arxiv.org/abs/2110.06864)

**Cập nhật lần cuối:** 2026-05-31