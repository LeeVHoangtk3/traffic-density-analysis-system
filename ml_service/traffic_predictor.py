import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import warnings

warnings.filterwarnings('ignore')


def classify_congestion(vehicle_count: int) -> str:
    """
    Phân loại mức độ mật độ giao thông dựa trên số xe / 15 phút.
    Ngưỡng được hiệu chỉnh cho thực tế đường đô thị Việt Nam (~400–500 xe/15p).
    """
    if vehicle_count < 200:
        return "LOW"
    if vehicle_count < 350:
        return "MEDIUM"
    if vehicle_count < 500:
        return "HIGH"
    return "SEVERE"


class TrafficPredictor:
    """
    Dự báo lưu lượng giao thông (số xe + mức độ mật độ) cho khung 15 phút tiếp theo.
    Sử dụng XGBoost Regressor với Time Series Cross-Validation.
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

        # Feature list – bao gồm các feature mới: is_weekend, lag_4, rolling_mean_8, hour_sin/cos
        self.features = [
            'hour', 'day_of_week', 'is_peak_hour', 'is_weekend',
            'lag_1', 'lag_2', 'lag_4',
            'rolling_mean_3',
            'hour_sin', 'hour_cos',
        ]

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature Engineering: Trích xuất đặc trưng thời gian và lịch sử.
        """
        data = df.copy()
        data['timestamp'] = pd.to_datetime(data['timestamp'])

        # --- Temporal features ---
        data['hour']         = data['timestamp'].dt.hour
        data['day_of_week']  = data['timestamp'].dt.dayofweek
        # Giờ cao điểm sáng 7–9h và chiều 17–19h (phù hợp Việt Nam)
        data['is_peak_hour'] = data['hour'].apply(
            lambda x: 1 if (7 <= x <= 9) or (17 <= x <= 19) else 0
        )
        # Cuối tuần (Thứ 7 = 5, Chủ nhật = 6)
        data['is_weekend']   = (data['day_of_week'] >= 5).astype(int)

        # Mã hóa vòng tròn theo giờ (tốt hơn số nguyên cho mô hình ML)
        data['hour_sin']     = np.sin(2 * np.pi * data['hour'] / 24)
        data['hour_cos']     = np.cos(2 * np.pi * data['hour'] / 24)

        # --- Lag features (dữ liệu quá khứ) ---
        data['lag_1'] = data['vehicle_count'].shift(1)   # 15 phút trước
        data['lag_2'] = data['vehicle_count'].shift(2)   # 30 phút trước
        data['lag_4'] = data['vehicle_count'].shift(4)   # 1 giờ trước

        # --- Rolling mean features ---
        data['rolling_mean_3'] = data['vehicle_count'].shift(1).rolling(window=3).mean()

        data = data.dropna()
        return data

    def train_and_evaluate(self, df: pd.DataFrame):
        """
        Huấn luyện mô hình với Time Series Cross-Validation (5 folds).
        """
        print("\n[*] Quá trình huấn luyện và đánh giá bắt đầu...")
        data = self.create_features(df)

        X = data[self.features]
        y = data['vehicle_count']

        tscv = TimeSeriesSplit(n_splits=5)
        mae_scores  = []
        rmse_scores = []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X), start=1):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            self.model.fit(X_train, y_train)
            y_pred = self.model.predict(X_test)

            mae  = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae_scores.append(mae)
            rmse_scores.append(rmse)

        print(f" -> Kết quả đánh giá bằng Cross Validation (5 folds):")
        print(f"    - MAE trung bình:  {np.mean(mae_scores):.2f} xe")
        print(f"    - RMSE trung bình: {np.mean(rmse_scores):.2f} xe")

        # Fit lại toàn bộ dữ liệu để dự báo thực tế
        print(" -> Đang cập nhật mô hình với toàn bộ dữ liệu...")
        self.model.fit(X, y)
        self.is_trained = True

    def save_model(self):
        """Lưu mô hình ra file .pkl."""
        if not self.is_trained:
            print("Lỗi: Mô hình chưa được huấn luyện.")
            return
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
        Yêu cầu DataFrame có ít nhất 3 dòng lịch sử với cột 'timestamp' và 'vehicle_count'.
        """
        if not self.is_trained:
            if not self.load_model():
                raise Exception("Mô hình chưa sẵn sàng. Hãy chạy train() hoặc kiểm tra file .pkl")

        df = raw_data_df.copy().sort_values('timestamp')

        if len(df) < 5:
            raise ValueError("Cần ít nhất 5 quan trắc lịch sử liên tiếp để dự báo.")

        # Tạo dòng giả tượng trưng cho mốc tương lai 15 phút tới
        last_time = pd.to_datetime(df['timestamp'].iloc[-1])
        next_time = last_time + pd.Timedelta(minutes=15)
        future_row = pd.DataFrame([{'timestamp': next_time, 'vehicle_count': 0}])

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
