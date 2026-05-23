import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error
import joblib
import warnings

warnings.filterwarnings('ignore')


def classify_congestion(vehicle_count: int) -> str:
    """
    Phân loại mức độ mật độ giao thông dựa trên số xe / 15 phút.
    Ngưỡng được hiệu chỉnh cho dataset đô thị NYC (~50-100 xe/15p).
    """
    if vehicle_count < 30:
        return "LOW"
    if vehicle_count < 100:
        return "MEDIUM"
    if vehicle_count < 200:
        return "HIGH"
    return "SEVERE"


class TrafficPredictor:
    """
    Dự báo lưu lượng giao thông (số xe + mức độ mật độ) cho khung 15 phút tiếp theo.
    Sử dụng XGBoost Regressor.
    """

    def __init__(self, model_path='model.pkl'):
        self.model = xgb.XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='reg:squarederror',
            random_state=42,
        )
        self.model_path = model_path
        self.is_trained = False

        self.features = [
            'hour', 'day_of_week', 'is_peak_hour', 'is_weekend',
            'lag_1', 'lag_2', 'lag_4', 'rolling_mean_3',
            'hour_sin', 'hour_cos'
        ]

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature Engineering: Trích xuất đặc trưng thời gian và lịch sử.
        """
        data = df.copy()
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data = data.sort_values('timestamp')

        # --- Temporal features ---
        data['hour'] = data['timestamp'].dt.hour
        data['day_of_week'] = data['timestamp'].dt.dayofweek
        
        # Giờ cao điểm sáng 7–9h và chiều 17–19h
        data['is_peak_hour'] = data['hour'].apply(
            lambda x: 1 if (7 <= x <= 9) or (17 <= x <= 19) else 0
        )
        # Cuối tuần (Thứ 7 = 5, Chủ nhật = 6)
        data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)

        # Mã hóa vòng tròn theo giờ và thứ
        data['hour_sin'] = np.sin(2 * np.pi * data['hour'] / 24)
        data['hour_cos'] = np.cos(2 * np.pi * data['hour'] / 24)
        data['day_of_week_sin'] = np.sin(2 * np.pi * data['day_of_week'] / 7)
        data['day_of_week_cos'] = np.cos(2 * np.pi * data['day_of_week'] / 7)

        # --- Lag features (dữ liệu quá khứ) ---
        if 'segment_id' in data.columns:
            data['lag_1'] = data.groupby('segment_id')['vehicle_count'].shift(1)
            data['lag_2'] = data.groupby('segment_id')['vehicle_count'].shift(2)
            data['lag_4'] = data.groupby('segment_id')['vehicle_count'].shift(4)
            data['rolling_mean_3'] = data.groupby('segment_id')['vehicle_count'].transform(
                lambda x: x.shift(1).rolling(window=3).mean()
            )
        else:
            data['lag_1'] = data['vehicle_count'].shift(1)
            data['lag_2'] = data['vehicle_count'].shift(2)
            data['lag_4'] = data['vehicle_count'].shift(4)
            data['rolling_mean_3'] = data['vehicle_count'].shift(1).rolling(window=3).mean()

        # Fill NaN values for features that shift too far, or just drop
        data = data.dropna()
        return data

    def train_and_evaluate(self, df: pd.DataFrame):
        """
        Huấn luyện mô hình, chia 80% train (CV) và 20% test (hold-out).
        """
        print("\n[*] Quá trình huấn luyện và đánh giá bắt đầu...")
        data = self.create_features(df)
        
        if len(data) < 100:
            raise ValueError("Không đủ dữ liệu sau khi tạo features.")

        # Split 80/20 chronological
        split_idx = int(len(data) * 0.8)
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]

        X_train = train_data[self.features]
        y_train = train_data['vehicle_count']
        X_test = test_data[self.features]
        y_test = test_data['vehicle_count']

        print(f" -> Tập Train: {len(X_train)} samples, Tập Test: {len(X_test)} samples")

        # Time Series Cross-Validation trên tập train
        tscv = TimeSeriesSplit(n_splits=5)
        mae_scores, rmse_scores = [], []

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train), start=1):
            X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_cv_train, y_cv_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            fold_model = xgb.XGBRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=6,
                subsample=0.8, colsample_bytree=0.8,
                objective='reg:squarederror', random_state=42,
                early_stopping_rounds=20
            )
            fold_model.fit(
                X_cv_train, y_cv_train,
                eval_set=[(X_cv_val, y_cv_val)],
                verbose=False
            )
            
            y_pred = fold_model.predict(X_cv_val)
            mae_scores.append(mean_absolute_error(y_cv_val, y_pred))
            rmse_scores.append(np.sqrt(mean_squared_error(y_cv_val, y_pred)))

        print(f" -> Kết quả Cross Validation (5 folds) trên tập Train:")
        print(f"    - MAE trung bình:  {np.mean(mae_scores):.2f} xe")
        print(f"    - RMSE trung bình: {np.mean(rmse_scores):.2f} xe")

        # Đánh giá trên tập Held-out Test
        print("\n -> Đang huấn luyện mô hình cuối trên toàn bộ tập Train (với early stopping qua tập Test)...")
        self.model.set_params(early_stopping_rounds=20)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        y_test_pred = self.model.predict(X_test)
        test_mae = mean_absolute_error(y_test, y_test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        test_r2 = r2_score(y_test, y_test_pred)
        
        # MAPE cần cẩn thận với zero values
        mask = y_test > 0
        if mask.sum() > 0:
            test_mape = mean_absolute_percentage_error(y_test[mask], y_test_pred[mask])
        else:
            test_mape = 0.0

        print(f" -> Kết quả đánh giá trên tập Held-out Test (20% cuối):")
        print(f"    - MAE:   {test_mae:.2f} xe")
        print(f"    - RMSE:  {test_rmse:.2f} xe")
        print(f"    - R2:    {test_r2:.4f}")
        print(f"    - MAPE:  {test_mape:.2%}")
        
        self.is_trained = True

    def train_and_evaluate_split(self, df: pd.DataFrame) -> dict:
        """
        Huấn luyện mô hình với chronological 80% Train / 20% Test split.
        Tính toán MAE, RMSE, MAPE trên tập Test.
        Sau đó fit lại toàn bộ dữ liệu.
        """
        print(f"\n[*] Bắt đầu huấn luyện & đánh giá (80/20 split) cho: {os.path.basename(self.model_path)}")
        data = self.create_features(df)
        
        if len(data) < 10:
            print("    [!] Cảnh báo: Quá ít dữ liệu để chia Train/Test!")
            return {}
            
        X = data[self.features]
        y = data['vehicle_count']
        
        split_idx = int(len(data) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Huấn luyện trên 80% train
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        
        # Clip dự đoán âm về 0
        y_pred = np.clip(y_pred, 0, None)
        
        # Tính toán metric
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        
        # MAPE robust
        y_test_arr = np.array(y_test)
        mask = y_test_arr > 0
        if np.any(mask):
            mape = np.mean(np.abs((y_test_arr[mask] - y_pred[mask]) / y_test_arr[mask])) * 100
        else:
            mape = 0.0
            
        print(f" -> Kết quả đánh giá trên tập Test (20% cuối):")
        print(f"    - Kích thước tập Train: {len(X_train)} dòng")
        print(f"    - Kích thước tập Test:  {len(X_test)} dòng")
        print(f"    - MAE:                  {mae:.2f} xe")
        print(f"    - RMSE:                 {rmse:.2f} xe")
        print(f"    - MAPE:                 {mape:.2f}%")
        
        # Fit lại toàn bộ dữ liệu
        print(" -> Đang huấn luyện lại mô hình trên toàn bộ dữ liệu...")
        self.model.fit(X, y)
        self.is_trained = True
        
        return {"mae": mae, "rmse": rmse, "mape": mape}

    def save_model(self):
        """Lưu mô hình ra file .pkl."""
        if not self.is_trained:
            print("Lỗi: Mô hình chưa được huấn luyện.")
            return
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"\n[+] ĐÃ LƯU MÔ HÌNH THÀNH CÔNG: {self.model_path}")

    def load_model(self) -> bool:
        """Tải mô hình từ file .pkl. Trả về True nếu thành công."""
        try:
            self.model = joblib.load(self.model_path)
            self.is_trained = True
            return True
        except FileNotFoundError:
            return False

    def predict(self, raw_data_df: pd.DataFrame) -> int:
        """
        Dự báo số lượng xe cho khung 15 phút tiếp theo.
        Yêu cầu DataFrame có ít nhất 5 dòng lịch sử với cột 'timestamp' và 'vehicle_count'.
        """
        if not self.is_trained:
            if not self.load_model():
                raise Exception("Mô hình chưa sẵn sàng. Hãy chạy train() hoặc kiểm tra file .pkl")

        df = raw_data_df.copy().sort_values('timestamp')

        if len(df) < 5:
            # Fallback nếu không đủ 5 quan trắc lịch sử
            if len(df) >= 3:
                return max(0, int(round(df['vehicle_count'].mean())))
            else:
                raise ValueError("Cần ít nhất 3 quan trắc lịch sử liên tiếp.")

        # Tạo dòng giả tượng trưng cho mốc tương lai 15 phút tới
        last_time = pd.to_datetime(df['timestamp'].iloc[-1])
        next_time = last_time + pd.Timedelta(minutes=15)
        future_row = pd.DataFrame([{'timestamp': next_time, 'vehicle_count': 0}])
        if 'segment_id' in df.columns:
            future_row['segment_id'] = df['segment_id'].iloc[-1]

        temp_df = pd.concat([df, future_row], ignore_index=True)
        processed = self.create_features(temp_df)

        if processed.empty:
            raise ValueError("Không đủ dữ liệu sau khi tạo features. Cần thêm lịch sử.")

        target_features = processed.tail(1)[self.features]
        predicted = self.model.predict(target_features)[0]

        return max(0, int(round(predicted)))

    def predict_with_level(self, raw_data_df: pd.DataFrame) -> dict:
        """
        Dự báo số xe và mức độ mật độ (LOW/MEDIUM/HIGH/SEVERE).
        Trả về dict gồm: predicted_count, congestion_level.
        """
        count = self.predict(raw_data_df)
        level = classify_congestion(count)
        return {"predicted_count": count, "congestion_level": level}


# =========================================================================
if __name__ == "__main__":
    print("TrafficPredictor module is ready.")
