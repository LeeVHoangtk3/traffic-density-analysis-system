# 🚦 Light Delta Model (Mô hình Đề xuất Đèn Xanh)

Mô hình `LightDeltaModel` là một thành phần quan trọng trong hệ thống phân tích mật độ giao thông, chịu trách nhiệm tính toán số giây cần điều chỉnh (tăng hoặc giảm) cho thời gian đèn xanh tại các pha giao lộ.

## 1. Giới thiệu Tổng quan
Khác với việc dự báo mật độ giao thông thuần túy, `LightDeltaModel` tập trung vào việc **tối ưu hóa dòng chảy** bằng cách đưa ra các quyết định điều chỉnh thời gian thực. Mô hình sử dụng thuật toán **XGBoost Regressor** để học mối quan hệ giữa trạng thái giao thông hiện tại và nhu cầu điều chỉnh đèn.

- **Vị trí file:** `ml_service/light_delta_model.py`
- **Model file:** `ml_service/light_model.pkl`

---

## 2. Đặc trưng Đầu vào (Input Features)
Mô hình sử dụng 6 đặc trưng chính để đưa ra quyết định:

| Feature | Mô tả | Kiểu dữ liệu |
| :--- | :--- | :--- |
| `queue_proxy` | Ước tính độ dài hàng đợi (số lượng xe đang dừng chờ) | `float` |
| `inbound_count` | Tổng số xe đi vào giao lộ trong một chu kỳ | `int` |
| `congestion_level` | Mức độ tắc nghẽn hiện tại (`low`, `medium`, `high`) | `string` |
| `baseline_green` | Thời gian đèn xanh mặc định (cấu hình tĩnh) | `int` (giây) |
| `hour` | Khung giờ hiện tại (0-23) | `int` |
| `day_of_week` | Thứ trong tuần (0=Thứ Hai ... 6=Chủ Nhật) | `int` |

---

## 3. Biến Mục tiêu (Target Variable)
Mục tiêu của mô hình là dự đoán `delta_green`:
- **Định nghĩa:** Số giây cộng thêm hoặc trừ đi vào thời gian `baseline_green`.
- **Dải giá trị:** `-30` đến `+45` giây.
- **Cơ chế an toàn:** Kết quả đầu ra luôn được **clamp** (giới hạn cứng) trong khoảng an toàn để tránh gây xung đột hoặc lỗi hệ thống đèn.

---

## 4. Kiến trúc Mô hình
Mô hình được xây dựng dựa trên **XGBoost**, một thuật toán Gradient Boosting mạnh mẽ với các tham số tối ưu cho sự ổn định:
- `n_estimators`: 200
- `learning_rate`: 0.05 (Học chậm để tránh phản ứng thái quá với biến động ảo)
- `max_depth`: 4 (Tránh overfitting)
- `objective`: `reg:squarederror`

---

## 5. Hướng dẫn Sử dụng (API)

### Huấn luyện Mô hình
Bạn có thể huấn luyện lại mô hình bằng cách cung cấp một DataFrame chứa các cột đặc trưng và cột `delta_green`.

```python
from ml_service.light_delta_model import train_delta

# df_train là pandas DataFrame chứa dữ liệu lịch sử
model = train_delta(df_train)
```

### Dự đoán (Inference)
Dùng để lấy số giây điều chỉnh dựa trên dữ liệu thời gian thực từ camera/cảm biến.

```python
from ml_service.light_delta_model import predict_delta

features = {
    "queue_proxy": 15.2,
    "inbound_count": 45,
    "congestion_level": "medium",
    "baseline_green": 30,
    "hour": 17,
    "day_of_week": 4
}

delta = predict_delta(features)
print(f"Điều chỉnh đèn xanh: {delta:+.1f} giây")
```

---

## 6. Luồng Xử lý Dữ liệu Nội bộ
1. **Encoding:** Chuyển đổi nhãn chuỗi (`congestion_level`) sang số nguyên (0, 1, 2).
2. **Validation:** Kiểm tra tính đầy đủ của các cột dữ liệu.
3. **Cross-Validation:** Sử dụng 3-fold CV trong quá trình train để đảm bảo tính tổng quát.
4. **Clamping:** Áp dụng giới hạn `_DELTA_MIN` và `_DELTA_MAX` cho mọi kết quả dự đoán (thường là [-30, +45] giây).

---

## 7. Nguồn Dữ liệu (Data Sources)
Mô hình không thu thập dữ liệu trực tiếp từ camera mà nhận thông tin đã qua xử lý từ pipeline của hệ thống:

1.  **Backend API (`/aggregation`):** Cung cấp các chỉ số thực tế như `queue_proxy` (hàng đợi), `inbound_count` (lưu lượng vào), và `congestion_level`.
2.  **Hệ thống (System Time):** Cung cấp `hour` và `day_of_week` để mô hình nhận diện các khung giờ cao điểm hoặc ngày cuối tuần.
3.  **Cấu hình Cục bộ:** `baseline_green` được lấy từ bảng cấu hình mặc định của từng Camera trong mã nguồn.

---

## 8. Luồng Hoạt động Toàn hệ thống
Quy trình từ video đến quyết định đèn xanh:
`Video Camera` ➔ `Detection Engine (YOLO)` ➔ `Backend (Aggregator)` ➔ `System Runner` ➔ **`LightDeltaModel`** ➔ `Điều chỉnh Đèn`

---

## 9. Các tệp tin liên quan
- `light_model.pkl`: File binary chứa trọng số mô hình đã huấn luyện.
- `label_generator.py`: (Tùy chọn) Dùng để tạo dữ liệu nhãn heuristic nếu chưa có dữ liệu thực tế.
- `light_delta_model_result.md`: Nhật ký kết quả của lần chạy/huấn luyện gần nhất.
- `integration_system/delta_applier.py`: Cầu nối trung gian áp dụng model vào thực tế.
