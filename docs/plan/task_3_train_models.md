# Nhiệm Vụ 3: Kỹ Nghệ Đặc Trưng Chuỗi Thời Gian & Huấn Luyện 3 Mô Hình XGBoost
**Mã nhiệm vụ:** `TASK_ML_03` | **Giai đoạn:** 1 | **Thời gian thực hiện dự kiến:** Ngày 5 - Ngày 7

---

## 1. Mô Tả Nhiệm Vụ
Nhiệm vụ này là bước then chốt trong Giai đoạn 1. Từ dữ liệu xoay trục của nút giao thu được ở Nhiệm vụ 2, chúng ta tiến hành xây dựng ma trận tính năng (feature matrix) phục vụ bài toán hồi quy chuỗi thời gian ngắn hạn (15 phút). Chúng ta cần tạo ra các đặc trưng tự hồi quy (lags), đặc trưng trượt (rolling mean) độc lập cho từng hướng rẽ, kết hợp với các biến tuần hoàn mã hóa mốc thời gian ngày-đêm.

Mục tiêu cuối cùng là huấn luyện thành công 3 mô hình XGBoost độc lập cho 3 hướng (`straight`, `left`, `right`), tính toán các chỉ số sai số (MAE, RMSE, MAPE) trên tập kiểm thử riêng biệt và xuất ra 3 file mô hình `.pkl` sẵn sàng nhúng vào hệ thống.

---

## 2. Dữ Liệu Đầu Vào (Inputs)
- **Tệp dữ liệu xoay trục:** [junction_pivot_clean.csv](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/data/junction_pivot_clean.csv).
- **Thư viện yêu cầu:** `xgboost`, `scikit-learn`, `pandas`, `numpy`, `joblib`.

---

## 3. Dữ Liệu Đầu Ra (Outputs)
- **3 File trọng số mô hình đã được đóng gói:**
  - `ml_service/model_straight.pkl`
  - `ml_service/model_left.pkl`
  - `ml_service/model_right.pkl`
- **Tệp log/kết quả đánh giá sai số:** `ml_service/data/training_metrics.json` ghi lại MAE, RMSE và MAPE trên tập Test của 3 mô hình.

---

## 4. Luồng Chạy Chi Tiết (Execution Flow)
Tác vụ được lập trình trong tệp `ml_service/train.py` thực hiện theo các bước tuần tự sau:

```mermaid
flowchart TD
    A[Đọc junction_pivot_clean.csv] --> B[Xây dựng Đặc trưng Tuần hoàn & Lịch trình]
    B --> C[Tạo Đặc trưng Trễ tự hồi quy cho riêng từng hướng]
    C --> D[Xóa bỏ các dòng NaN sinh ra do tính trễ]
    D --> E[Chia dữ liệu theo thời gian: Train <= 2024 | Test >= 2025]
    E --> F[Huấn luyện 3 mô hình XGBoost Regressor độc lập]
    F --> G[Dự báo tập Test & Tính MAE, RMSE, MAPE]
    G --> H[Lưu 3 file .pkl và xuất tệp tin metrics JSON]
```

### Chi tiết xây dựng Đặc trưng (Feature Engineering):
1. **Đặc trưng Tuần hoàn (Circular Features):**
   - Giúp mô hình hiểu sự liên tục giữa phút 23:45 của ngày hôm trước và phút 00:00 của ngày hôm sau.
   - Công thức tính toán:
     $$\text{hour\_sin} = \sin\left(\frac{2\pi \times \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \times \text{hour}}{24}\right)$$
     (Với `hour` được lấy từ cột thời gian dưới dạng số thực, bao gồm cả số phút lẻ chia cho 60, ví dụ: 14h15 = 14.25).
2. **Đặc trưng Lịch trình (Calendar Features):**
   - `day_of_week` (0 đến 6): Ngày trong tuần.
   - `is_weekend` (0 hoặc 1): Xác định ngày cuối tuần (Thứ 7, Chủ Nhật).
3. **Đặc trưng Trễ & Trượt Tự Hồi Quy (Lags & Rolling Features):**
   - Cho mỗi hướng $D \in \{\text{straight}, \text{left}, \text{right}\}$, tạo các cột đặc trưng trễ dựa trên cột lưu lượng gốc `vol_D`:
     - `D_lag_1`: Lưu lượng xe ở mốc 15 phút trước ($t - 1$).
     - `D_lag_2`: Lưu lượng xe ở mốc 30 phút trước ($t - 2$).
     - `D_rolling_mean_3`: Trung bình trượt của 3 mốc trễ gần nhất:
       $$\text{rolling\_mean\_3} = \frac{D\_lag\_1 + D\_lag\_2 + D\_lag\_3}{3}$$

### Chi tiết quy trình Huấn luyện & Đánh giá:
1. **Phân chia Tập dữ liệu (Train/Test Split):**
   - Để tránh rò rỉ dữ liệu chuỗi thời gian (data leakage), không sử dụng phép chia ngẫu nhiên.
   - Thực hiện chia theo mốc thời gian cứng: Tập Train chứa toàn bộ dữ liệu trước hoặc bằng ngày `2024-12-31`. Tập Test chứa dữ liệu từ ngày `2025-01-01` trở đi.
2. **Huấn luyện mô hình:**
   - Khởi tạo `xgb.XGBRegressor` cho mỗi hướng với các tham số tối ưu (ví dụ: `n_estimators=100`, `max_depth=5`, `learning_rate=0.08`, `random_state=42`).
   - Xây dựng ma trận đặc trưng $X$ gồm tất cả đặc trưng đã tạo và target $y$ là cột lưu lượng tương ứng ở mốc hiện tại.
   - Thực hiện `fit(X_train, y_train)`.
3. **Đánh giá & Xuất mô hình:**
   - Dự báo trên tập kiểm thử: `y_pred = model.predict(X_test)`.
   - Tính toán chỉ số:
     - Mean Absolute Error (MAE)
     - Root Mean Square Error (RMSE)
     - Mean Absolute Percentage Error (MAPE)
   - Lưu 3 file trọng số `.pkl` bằng thư viện `joblib`.
   - Ghi lại các chỉ số đánh giá ra tệp JSON.

---

## 5. Kiểm Tra & Xác Thực (Verification Plan)
Hãy viết mã kiểm thử tại `ml_service/smoke_test_training.py` để xác định mô hình đã được đóng gói chính xác và có khả năng dự đoán:

```python
import joblib
import pandas as pd
import numpy as np
import os

def test_inference():
    models = ["straight", "left", "right"]
    for m in models:
        path = f"ml_service/model_{m}.pkl"
        assert os.path.exists(path), f"LỖI: Thiếu file trọng số {path}!"
        
        # Load thử mô hình
        model = joblib.load(path)
        
        # Giả lập 1 dòng đặc trưng đầu vào để predict thử
        # Thứ tự cột đặc trưng phải trùng khớp chính xác với X_train
        dummy_features = np.array([[14.25, 0.5, 0.86, 2, 0, 50, 45, 48]]) # Ví dụ 8 đặc trưng
        try:
            pred = model.predict(dummy_features)
            assert len(pred) == 1, "LỖI: Kết quả dự báo phải trả về 1 phần tử!"
            print(f"Kiểm thử hướng '{m}' OK! Dự báo giả lập: {pred[0]:.2f} xe.")
        except Exception as e:
            assert False, f"LỖI: Chạy predict thử nghiệm cho hướng '{m}' thất bại! Chi tiết: {str(e)}"

if __name__ == "__main__":
    test_inference()
```

- **Lệnh thực thi chạy huấn luyện:**
  ```bash
  python ml_service/train.py
  ```
- **Lệnh thực thi smoke test xác thực:**
  ```bash
  python ml_service/smoke_test_training.py
  ```
