# Nhiệm Vụ 3: Huấn Luyện Hệ Thống 3 Mô Hình Học Máy XGBoost Hợp Nhất Đa Nút Giao
**Mã nhiệm vụ:** `TASK_ML_03` | **Giai đoạn:** 1 | **Thời gian thực hiện dự kiến:** Ngày 5 - Ngày 7

---

## 1. Mô Tả Nhiệm Vụ
Nhiệm vụ này là cột mốc cốt lõi của Giai đoạn 1. Từ bảng dữ liệu xoay trục hợp nhất `junction_pivot_clean.csv` của 3 nút giao thực tế, chúng ta tiến hành huấn luyện **3 mô hình hồi quy XGBoost độc lập** tương ứng với 3 làn di chuyển chuẩn:
1. **Mô hình Đi Thẳng (`model_straight.pkl`):** Học và dự báo volume làn thẳng.
2. **Mô hình Rẽ Trái (`model_left.pkl`):** Học và dự báo volume làn rẽ trái.
3. **Mô hình Rẽ Phải (`model_right.pkl`):** Học và dự báo volume làn rẽ phải.

Mỗi mô hình sẽ được huấn luyện thông qua lớp dự báo `TrafficPredictor` với phương pháp phân chia dữ liệu theo thời gian (chronological split) 80% Train và 20% Test để đánh giá khách quan hiệu năng, tránh rò rỉ dữ liệu (data leakage) trước khi lưu trữ trọng số.

---

## 2. Dữ Liệu Đầu Vào (Inputs)
- **Bảng dữ liệu xoay trục hợp nhất:** [junction_pivot_clean.csv](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/data/junction_pivot_clean.csv).
- **Thư viện yêu cầu:** `xgboost`, `scikit-learn`, `pandas`, `numpy`, `joblib`.

---

## 3. Dữ Liệu Đầu Ra (Outputs)
- **3 File trọng số mô hình đã được đóng gói lưu trữ:**
  - `ml_service/model/model_straight.pkl`
  - `ml_service/model/model_left.pkl`
  - `ml_service/model/model_right.pkl`
- Báo cáo khoa học tổng hợp in ra terminal về các chỉ số lỗi `MAE` (xe), `RMSE` (xe) và `MAPE` (%) trên tập Test.

---

## 4. Luồng Chạy Chi Tiết (Execution Flow)
Tác vụ được thực hiện tự động bằng cách khởi chạy mã nguồn `ml_service/train.py` theo luồng xử lý:

```mermaid
flowchart TD
    A[Đọc junction_pivot_clean.csv chứa dữ liệu 3 nút giao] --> B[Lặp qua 3 hướng: straight, left, right]
    B --> C[Lọc bỏ các dòng bị khuyết NaN ở hướng tương ứng]
    C --> D[Sắp xếp dữ liệu theo trật tự thời gian tăng dần]
    D --> E[Chia dữ liệu: 80% thời gian đầu làm Train | 20% thời gian sau làm Test]
    E --> F[Khởi tạo TrafficPredictor huấn luyện mô hình XGBoost Regressor]
    F --> G[Dự báo tập Test và tính toán MAE, RMSE, MAPE]
    G --> H[Huấn luyện lại fit trên 100% dữ liệu để tối ưu hóa]
    H --> I[Lưu file trọng số .pkl tương ứng vào thư mục ml_service/model/]
```

### Chi tiết kỹ thuật huấn luyện:
1. **Xử lý dữ liệu khuyết:** Do một số ngã rẽ không có làn phải (ví dụ Segment 72887), dòng dữ liệu tại đó sẽ bị rỗng ở cột `vol_right`. Đoạn mã huấn luyện phải sử dụng `.dropna()` riêng cho từng hướng để đảm bảo kích thước ma trận học chính xác.
2. **Tham số tối ưu hóa XGBoost:**
   - `n_estimators`: `200` (Số lượng cây quyết định).
   - `learning_rate`: `0.05` (Tốc độ học vừa phải để tránh overfitting).
   - `max_depth`: `6` (Độ sâu tối đa của cây).
   - `subsample`: `0.8` và `colsample_bytree`: `0.8` (Tỷ lệ lấy mẫu dòng và đặc trưng ngẫu nhiên giúp mô hình ổn định).
3. **Đánh giá & Lưu trữ:**
   - Dự báo sai số trên tập kiểm thử 20% cuối.
   - Chạy tái huấn luyện trên toàn bộ 100% dữ liệu để nạp đầy đủ tri thức lịch sử trước khi gọi phương thức `joblib.dump()` đóng gói file trọng số.

---

## 5. Kiểm Tra & Xác Thực (Verification Plan)
Để chạy huấn luyện và nghiệm thu chất lượng mô hình:

- **Lệnh thực thi huấn luyện:**
  ```powershell
  python -m ml_service.train
  ```
- **Tiêu chí kiểm duyệt chất lượng học:**
  1. **Tạo file thành công:** Cả 3 file `.pkl` phải xuất hiện đầy đủ trong thư mục `ml_service/model/`.
  2. **Chất lượng dự báo:** MAE trung bình của mô hình trên tập Test nên đạt mức $< 45$ xe/15 phút và chỉ số MAPE nên dưới $15\%$ để đảm bảo độ tin cậy khi triển khai thực tế.
