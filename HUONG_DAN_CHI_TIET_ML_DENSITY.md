# Hướng Dẫn Chi Tiết Nguyên Lý, Cấu Trúc Mã Nguồn & Luồng Dữ Liệu Machine Learning

Tài liệu này là cẩm nang kỹ thuật chi tiết nhất giải thích toàn bộ nguyên lý toán học, cấu trúc mã nguồn Python thực tế (tên file, số dòng), luồng chạy dữ liệu (Data Flow), tham số đầu vào/đầu ra và cấu trúc database MongoDB phục vụ cho mô hình Học Máy trong dự án.

---

## 1. Bản Đồ Mã Nguồn & Luồng Dữ Liệu Tổng Thể (ML Data Flow)

Hệ thống Học Máy (ML) của dự án hoạt động theo 2 giai đoạn chính: **Huấn luyện Offline** (Training Pipeline) và **Dự báo & Phân loại Online** (Real-time Inference).

```mermaid
graph TD
    %% Giai đoạn 1: Offline Training
    subgraph "GIAI ĐOẠN 1: HUẤN LUYỆN OFFLINE (train.py)"
        RawCSV["Dữ liệu giao thông NYC lịch sử (286MB)"] -->|Bước 1: Tiền xử lý & Nội suy| CleanCSV["junction_pivot_clean.csv (Vol_clean)"]
        CleanCSV -->|Bước 2: Trích xuất đặc trưng Lags/Sin/Cos| FeatureMatrix["Ma trận đặc trưng (X, y)"]
        FeatureMatrix -->|Bước 3: Huấn luyện XGBoost| XGBModel["model.pkl (XGBRegressor)"]
        CleanCSV -->|Bước 4: Phân cụm K-Means| Centroids["4 Tâm Cụm (Centroids)"]
        Centroids -->|Bước 4: Tính trung điểm| Thresholds["Ngưỡng Thích Ứng (T1, T2, T3)"]
        Thresholds -->|Lưu cấu hình| MongoDBThresholds[("MongoDB: directional_thresholds")]
    end

    %% Giai đoạn 2: Real-time Inference
    subgraph "GIAI ĐOẠN 2: DỰ BÁO & PHÂN LOẠI ONLINE (Real-time Inference)"
        YOLO["YOLOv9 + Tracker (detection/main.py)"] -->|Phát hiện xe qua ROI| EventData["Sự kiện đếm xe (Real-time Event)"]
        EventData -->|API POST| MongoDBDetections[("MongoDB: vehicle_detections")]
        MongoDBDetections -->|Background Worker (seed_data.py)| MongoDBAggs[("MongoDB: traffic_aggregation")]
        
        %% Nhánh Phân Loại Mật Độ
        MongoDBAggs -->|Đọc lưu lượng xe V| ClassifyLogic["aggregation_service.py"]
        MongoDBThresholds -->|Cung cấp ngưỡng T1, T2, T3| ClassifyLogic
        ClassifyLogic -->|So sánh V với T| CurrentDensity["Nhãn mật độ hiện tại: LOW/MEDIUM/HIGH/HEAVY"]
        
        %% Nhánh Dự Báo AI
        MongoDBAggs -->|Đọc 3 chu kỳ gần nhất: Y_t-1, Y_t-2, Y_t-3| PredictLogic["prediction_service.py"]
        XGBModel -->|Cung cấp trọng số| PredictLogic
        PredictLogic -->|Chạy model.predict| AIResult["Dự báo lưu lượng 15p tới & Phân loại mật độ tương lai"]
    end

    %% Kết nối hiển thị
    CurrentDensity -->|REST API| Frontend["React Frontend (Dashboard Widgets)"]
    AIResult -->|REST API| Frontend
```

---

## 2. Phần 1: Các Đặc Trưng Trễ Tự Hồi Quy (Autoregressive Lags) & Lượng Giác Tuần Hoàn

Mô hình AI dự báo lưu lượng giao thông sử dụng phương pháp phân tích chuỗi thời gian dựa trên các đặc trưng được tính toán từ lịch sử gần nhất. Dưới đây là cấu trúc mã nguồn thực tế thực hiện kỹ nghệ đặc trưng này:

### 2.1. Mã nguồn thực hiện trong Giai đoạn Huấn luyện (Offline)
* **Tệp tin thực hiện:** [ml_service/train.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/train.py)
* **Vị trí dòng code:** Dòng `221` đến dòng `238`.

#### Đoạn code thực tế trong `ml_service/train.py`:
```python
    # 1. Autoregressive Lags
    df_feat['lag_1'] = df_feat['Vol_clean'].shift(1)
    df_feat['lag_2'] = df_feat['Vol_clean'].shift(2)
    df_feat['lag_3'] = df_feat['Vol_clean'].shift(3)
    
    # 2. Rolling mean 45p gần nhất
    df_feat['rolling_mean_3'] = (df_feat['lag_1'] + df_feat['lag_2'] + df_feat['lag_3']) / 3.0
    
    # 3. Cyclic Time (Giờ sin/cos)
    hour_float = df_feat['timestamp'].dt.hour + df_feat['timestamp'].dt.minute / 60.0
    df_feat['hour_sin'] = np.sin(2 * np.pi * hour_float / 24.0)
    df_feat['hour_cos'] = np.cos(2 * np.pi * hour_float / 24.0)
    
    # 4. Schedule features
    df_feat['day_of_week'] = df_feat['timestamp'].dt.dayofweek
    df_feat['is_weekend'] = df_feat['day_of_week'].isin([5, 6]).astype(int)
```

---

### 2.2. Mã nguồn thực hiện trong Giai đoạn Dự báo thời gian thực (Online)
* **Tệp tin thực hiện:** [backend/services/prediction_service.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/backend/services/prediction_service.py)
* **Vị trí dòng code:** Dòng `107` đến dòng `135`.

#### Đoạn code thực tế trong `backend/services/prediction_service.py`:
```python
    # 1. Lấy dữ liệu thực đo từ MongoDB
    recent_records = list(
        db.traffic_aggregation.find({"camera_id": camera_id})
        .sort("timestamp", -1)
        .limit(3)
    )
    
    # 2. Xử lý đặc trưng trễ với fallback cực kỳ an toàn
    lag_1 = 50.0
    lag_2 = 50.0
    lag_3 = 50.0
    
    if len(recent_records) >= 1:
        lag_1 = float(recent_records[0].get("vehicle_count", 50.0))
    if len(recent_records) >= 2:
        lag_2 = float(recent_records[1].get("vehicle_count", 50.0))
    if len(recent_records) >= 3:
        lag_3 = float(recent_records[2].get("vehicle_count", 50.0))
        
    rolling_mean_3 = (lag_1 + lag_2 + lag_3) / 3.0
    
    # 3. Tính toán đặc trưng thời gian thực
    now = datetime.now()
    hour_float = now.hour + now.minute / 60.0
    hour_sin = float(np.sin(2 * np.pi * hour_float / 24.0))
    hour_cos = float(np.cos(2 * np.pi * hour_float / 24.0))
    
    day_of_week = int(now.weekday())
    is_weekend = 1 if day_of_week >= 5 else 0
```

---

### 2.3. Giải thích chức năng, tham số và cấu trúc dữ liệu

#### A. Các đặc trưng trễ (`lag_1`, `lag_2`, `lag_3`):
* **Tác dụng/Chức năng:** Đại diện cho số lượng xe đếm được ở **15 phút trước** (`lag_1` / $Y_{t-1}$), **30 phút trước** (`lag_2` / $Y_{t-2}$), và **45 phút trước** (`lag_3` / $Y_{t-3}$). Các đặc trưng này giúp mô hình AI nhận biết được xu hướng tăng/giảm và quán tính của luồng xe để dự báo lưu lượng chu kỳ kế tiếp.
* **Đầu vào (Inputs):** Mảng một chiều chứa lịch sử đếm xe từ MongoDB Atlas (Collection `traffic_aggregation`).
* **Đầu ra (Outputs):** Ba biến số thực biểu diễn lưu lượng trễ phục vụ cho ma trận đặc trưng `X_pred`.
* **Luồng chạy (Data Flow):** 
  `MongoDB: traffic_aggregation` $\rightarrow$ `recent_records` (danh sách Python) $\rightarrow$ Ép kiểu `float` $\rightarrow$ Trình dự báo XGBoost.

#### B. Đặc trưng trung bình trượt (`rolling_mean_3`):
* **Tác dụng/Chức năng:** Làm mịn dữ liệu lịch sử bằng cách lấy trung bình cộng của 3 chu kỳ trễ gần nhất. Việc này triệt tiêu các nhiễu động ngẫu nhiên tăng/giảm xe đột ngột, giúp AI nắm bắt được **xu hướng nền thực tế** của làn đường.
* **Đầu vào (Inputs):** Ba giá trị trễ `lag_1`, `lag_2`, `lag_3`.
* **Đầu ra (Outputs):** Một biến số thực đại diện cho trung bình trượt.
* **Toán học áp dụng:**
  $$\text{rolling\_mean\_3} = \frac{\text{lag\_1} + \text{lag\_2} + \text{lag\_3}}{3}$$

#### C. Đặc trưng chu kỳ thời gian tuần hoàn (`hour_sin`, `hour_cos`):
* **Tác dụng/Chức năng:** Chuyển đổi mốc giờ thẳng (0-23 giờ) thành hai tọa độ sin/cos chạy trên một vòng tròn lượng giác có chu kỳ 24 giờ. Nó giải quyết triệt để lỗi logic số học: giúp AI nhận biết giờ `23:59` và giờ `00:01` thực chất rất sát nhau về mặt vật lý giao thông đô thị, và tự động học được tính chất tuần hoàn lượng xe lặp lại theo khung giờ hàng ngày.
* **Đầu vào (Inputs):** `datetime.now()` (lấy mốc thời gian chạy thực tế của hệ thống).
* **Đầu ra (Outputs):** Hai giá trị số thực nằm trong khoảng $[-1, 1]$.
* **Toán học áp dụng:**
  $$\text{hour\_float} = \text{Hour} + \frac{\text{Minute}}{60}$$
  $$\text{hour\_sin} = \sin\left(\frac{2\pi \times \text{hour\_float}}{24}\right)$$
  $$\text{hour\_cos} = \cos\left(\frac{2\pi \times \text{hour\_float}}{24}\right)$$

---

## 3. Phần 2: Thuật Toán Dự Báo AI (XGBoost Regressor)

Mô hình lõi thực hiện dự báo lưu lượng xe chu kỳ tiếp theo là thuật toán cây quyết định tăng cường độ dốc cực đoan **XGBoost Regressor**.

### 3.1. Mã nguồn thực hiện trong Giai đoạn Huấn luyện (Offline)
* **Tệp tin thực hiện:** [ml_service/train.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/train.py)
* **Vị trí dòng code:** Dòng `241` đến dòng `284`.

#### Đoạn code huấn luyện và xuất model:
```python
    feature_cols = ['lag_1', 'lag_2', 'rolling_mean_3', 'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend']
    X = df_feat[feature_cols]
    y = df_feat['Vol_clean']
    
    # Chia tách Train/Test 80/20 theo thời gian
    split_idx = int(len(df_feat) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Huấn luyện mô hình XGBoost
    model = xgb.XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Đánh giá và lưu trữ model.pkl
    with open(model_path2, 'wb') as f:
        pickle.dump(model, f)
```

---

### 3.2. Mã nguồn thực hiện trong Giai đoạn Dự báo thời gian thực (Online)
* **Tệp tin thực hiện:** [backend/services/prediction_service.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/backend/services/prediction_service.py)
* **Vị trí dòng code:** Dòng `136` đến dòng `150`.

#### Đoạn code nạp model và dự báo thực tế:
```python
    model = get_cached_model()
    if model is None:
        predicted_raw_volume = int(round(rolling_mean_3))
    else:
        try:
            # Tạo DataFrame đúng cấu trúc các cột đặc trưng như lúc train
            X_pred = pd.DataFrame([[
                lag_1, lag_2, rolling_mean_3, hour_sin, hour_cos, day_of_week, is_weekend
            ]], columns=['lag_1', 'lag_2', 'rolling_mean_3', 'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend'])
            
            raw_pred = model.predict(X_pred)[0]
            predicted_raw_volume = int(round(max(0.0, float(raw_pred))))
        except Exception as e:
            predicted_raw_volume = int(round(rolling_mean_3))
```

---

### 3.3. Cấu trúc tham số và luồng dữ liệu (XGBoost)

* **Tham số đầu vào (Model Inputs):**
  Một DataFrame chứa 1 hàng và 7 cột đặc trưng:
  `['lag_1', 'lag_2', 'rolling_mean_3', 'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend']`
* **Tham số đầu ra (Model Outputs):**
  Một số nguyên (`predicted_raw_volume`) đại diện cho **số lượng xe dự kiến đi qua ROI trong 15 phút tiếp theo**.
* **Luồng chạy dữ liệu (Data Flow):**
  1. Frontend gọi API `GET /api/prediction/next?camera_id=cam02`.
  2. Backend truy vấn 3 bản ghi aggregation mới nhất từ MongoDB để lấy các giá trị `lag`.
  3. Backend nạp mô hình cache `model.pkl` từ thư mục `ml_service/model/`.
  4. Backend chạy phương thức `.predict()` trên ma trận đặc trưng thời gian thực.
  5. Trả về đối tượng JSON gồm lưu lượng dự đoán và mức độ mật độ giao thông tương lai.

---

## 4. Phần 3: Thuật Toán Phân Loại Mật Độ Thích Ứng (K-Means Clustering)

Để phân loại lưu lượng giao thông thành 4 mức độ (**LOW, MEDIUM, HIGH, HEAVY**), hệ thống chạy thuật toán phân cụm **K-Means Clustering** trên dữ liệu lịch sử để tự động tối ưu hóa và sinh ra các ngưỡng chuyển tiếp.

### 4.1. Mã nguồn thực hiện trong Giai đoạn Huấn luyện (Offline)
* **Tệp tin thực hiện:** [ml_service/train.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/ml_service/train.py)
* **Vị trí dòng code:** Dòng `289` đến dòng `331`.

#### Đoạn code chạy K-Means và cập nhật Database:
```python
    # Chạy phân cụm K-Means trên toàn bộ cột Vol_clean lịch sử
    volumes = df_feat['Vol_clean'].values.reshape(-1, 1)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=15)
    kmeans.fit(volumes)
    
    # Sắp xếp các tâm cụm (centroids) tăng dần
    centroids = sorted(kmeans.cluster_centers_.flatten())
    C0, C1, C2, C3 = centroids
    
    # Tính các ngưỡng động bằng trung điểm các tâm cụm kế tiếp
    T1 = (C0 + C1) / 2.0
    T2 = (C1 + C2) / 2.0
    T3 = (C2 + C3) / 2.0

    camera_id = "cam01"
    document = {
        "camera_id": camera_id,
        "direction": "total",
        "thresholds": {
            "low_to_medium": float(round(T1, 2)),
            "medium_to_high": float(round(T2, 2)),
            "high_to_heavy": float(round(T3, 2))
        },
        "centroids": [float(round(c, 2)) for c in centroids],
        "updated_at": datetime.now(timezone.utc)
    }

    # Cập nhật các bảng trong MongoDB để hệ thống truy vấn
    db.directional_thresholds.update_one(
        {"camera_id": camera_id, "direction": "total"},
        {"$set": document},
        upsert=True
    )
    db.density_thresholds.update_one(
        {"camera_id": camera_id},
        {"$set": document},
        upsert=True
    )
```

---

### 4.2. Mã nguồn thực hiện trong Giai đoạn Phân loại thời gian thực (Online)
* **Tệp tin thực hiện:** [backend/services/aggregation_service.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/backend/services/aggregation_service.py)
* **Vị trí dòng code:** Dòng `38` đến dòng `76`.

#### Đoạn code đọc ngưỡng và phân loại mật độ:
```python
def get_direction_thresholds(db, camera_id: Optional[str], direction: str) -> dict | None:
    filters = {"direction": direction}
    if camera_id:
        filters["camera_id"] = camera_id
    document = db.directional_thresholds.find_one(filters)
    if document:
        return document.get("thresholds")
    return None

def classify_direction_count(db, camera_id: Optional[str], direction: str, vehicle_count: int) -> str:
    # Lấy các ngưỡng thích ứng K-Means từ MongoDB
    thresholds = get_direction_thresholds(db, camera_id, direction)
    if thresholds:
        low_to_medium = float(thresholds.get("low_to_medium", 0))
        medium_to_high = float(thresholds.get("medium_to_high", 0))
        high_to_heavy = float(thresholds.get("high_to_heavy", 0))
        
        # So sánh lưu lượng thực tế đếm được (vehicle_count) với các ngưỡng động
        if vehicle_count < low_to_medium:
            return "Low"
        if vehicle_count < medium_to_high:
            return "Medium"
        if vehicle_count < high_to_heavy:
            return "High"
        return "Heavy"

    # Fallback mặc định nếu chưa chạy seed/train
    return compute_congestion(vehicle_count)
```

---

### 4.3. Giải thích chức năng, tham số và toán học áp dụng

* **Đầu vào của K-Means (Offline):** 
  Mảng 1 chiều chứa toàn bộ lưu lượng đếm xe lịch sử (`Vol_clean`) từ dữ liệu làm sạch.
* **Đầu vào của Phân loại (Online):**
  Số nguyên `vehicle_count` đại diện cho số xe đếm được trong chu kỳ 15 phút hiện tại của camera.
* **Nguyên lý toán học của Ngưỡng Thích Ứng:**
  K-Means chia dữ liệu thành 4 cụm. Ta thu được 4 tâm cụm (centroids) đại diện: $C_0, C_1, C_2, C_3$.
  Các ngưỡng động phân loại được định nghĩa là trung điểm hình học của các tâm cụm này:
  $$T_1 \text{ (Low } \rightarrow \text{ Medium)} = \frac{C_0 + C_1}{2}$$
  $$T_2 \text{ (Medium } \rightarrow \text{ High)} = \frac{C_1 + C_2}{2}$$
  $$T_3 \text{ (High } \rightarrow \text{ Heavy)} = \frac{C_2 + C_3}{2}$$

---

## 5. Cấu Trúc Cơ Sở Dữ Liệu MongoDB Liên Quan (Schemas)

Dưới đây là cấu trúc các Document thực tế được lưu trữ trong MongoDB Atlas để liên kết toàn bộ luồng xử lý Học Máy này:

### 5.1. Collection: `directional_thresholds` / `density_thresholds`
*Lưu trữ các ngưỡng động phân loại mật độ được sinh ra từ K-Means.*
```json
{
  "_id": "6657a8a1f812ab572cf93b01",
  "camera_id": "cam01",
  "direction": "total",
  "thresholds": {
    "low_to_medium": 32.45,
    "medium_to_high": 105.80,
    "high_to_heavy": 210.15
  },
  "centroids": [12.4, 52.5, 159.1, 261.2],
  "updated_at": "2026-05-30T02:00:00.000Z"
}
```

### 5.2. Collection: `vehicle_detections`
*Lưu trữ các sự kiện nhận diện xe thời gian thực do YOLO gửi lên.*
```json
{
  "_id": "6657a9f8f812ab572cf93b22",
  "event_id": "e8d7a85c-4f99-470b-bd09-17d4526d1101",
  "camera_id": "cam02",
  "track_id": "42",
  "vehicle_type": "car",
  "density": "MEDIUM",
  "direction": "straight",
  "event_type": "zone_entry",
  "confidence": 0.8954,
  "timestamp": "2026-05-30T02:15:30.000Z"
}
```

### 5.3. Collection: `traffic_aggregation`
*Lưu trữ dữ liệu tổng hợp theo chu kỳ 15 phút (nguồn cung cấp các đặc trưng trễ `lag` cho AI).*
```json
{
  "_id": "6657aa1af812ab572cf93c55",
  "camera_id": "cam02",
  "vehicle_count": 145,
  "inbound_count": 145,
  "queue_proxy": 145,
  "congestion_level": "High",
  "direction_counts": {
    "left": 0,
    "straight": 145,
    "right": 0
  },
  "congestion_levels": {
    "left": "Low",
    "straight": "High",
    "right": "Low"
  },
  "timestamp": "2026-05-30T02:30:00.000Z"
}
```
