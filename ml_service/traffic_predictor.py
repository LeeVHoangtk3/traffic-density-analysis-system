import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import warnings

# Bỏ qua các cảnh báo không cần thiết để output sạch hơn
warnings.filterwarnings('ignore')

class TrafficPredictor:
    """
    Class dự báo lưu lượng giao thông sử dụng XGBoost.
    Mục đích: Dự đoán số lượng xe cho 15 phút tiếp theo dựa trên dữ liệu lịch sử.
    """
    def __init__(self, model_path='model.pkl'):
        # Khởi tạo thuật toán XGBoost Regressor
        # Thuật toán này rất phù hợp với dữ liệu dạng bảng và có thể học tốt các mẫu phức tạp
        self.model = xgb.XGBRegressor(
            n_estimators=100,       # Số lượng cây quyết định
            learning_rate=0.1,      # Tốc độ học
            max_depth=5,            # Độ sâu tối đa của cây (tránh overfitting)
            objective='reg:squarederror', # Hàm mục tiêu dùng cho bài toán hồi quy
            random_state=42         # Cố định random seed để kết quả ổn định
        )
        self.model_path = model_path
        self.is_trained = False
        
        # Danh sách các biến đầu vào (Features) để huấn luyện mô hình
        self.features = ['hour', 'day_of_week', 'is_peak_hour', 'lag_1', 'lag_2', 'rolling_mean_3']

    def create_features(self, df):
        """
        BƯỚC 2: Feature Engineering (Trích xuất đặc trưng)
        Tạo ra các cột dữ liệu mới phản ánh chu kỳ và quá khứ.
        """
        # Copy dữ liệu để tránh lỗi tác động trực tiếp lên biến gốc
        data = df.copy()
        
        # 1. Temporal Features (Đặc trưng thời gian)
        data['hour'] = data['timestamp'].dt.hour
        data['day_of_week'] = data['timestamp'].dt.dayofweek
        # 1 nếu là giờ cao điểm, 0 nếu không phải
        data['is_peak_hour'] = data['hour'].apply(lambda x: 1 if (7 <= x <= 9) or (17 <= x <= 19) else 0)
        
        # 2. Lag Features (Dữ liệu quá khứ)
        # Lấy số lượng xe của 15 phút trước (shift 1 dòng xuống)
        data['lag_1'] = data['vehicle_count'].shift(1)
        # Lấy số lượng xe của 30 phút trước (shift 2 dòng xuống)
        data['lag_2'] = data['vehicle_count'].shift(2)
        
        # 3. Rolling Mean (Trung bình trượt)
        # Tính trung bình lưu lượng của 3 khung giờ gần nhất trước đó
        data['rolling_mean_3'] = data['vehicle_count'].shift(1).rolling(window=3).mean()
        
        # Loại bỏ các dòng chứa giá trị NaN (thường nằm ở 3 dòng đầu do quá trình shift)
        data = data.dropna()
        
        return data

    def train_and_evaluate(self, df):
        """
        BƯỚC 3: Huấn luyện và Đánh giá (Sử dụng Time Series Split)
        Trong bài toán time series, KHÔNG dùng random split (train_test_split random)
        vì sẽ rò rỉ dữ liệu tương lai vào quá khứ.
        """
        print("\n[*] Quá trình huấn luyện và đánh giá bắt đầu...")
        data = self.create_features(df)
        
        X = data[self.features]
        y = data['vehicle_count']
        
        # Time Series Split cắt dữ liệu thành từng cụm liên tiếp theo thời gian
        tscv = TimeSeriesSplit(n_splits=5)
        
        mae_scores = []
        rmse_scores = []
        
        fold = 1
        for train_index, test_index in tscv.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            # Khớp (Fit) dữ liệu vào mô hình
            self.model.fit(X_train, y_train)
            
            # Phóng đoán tương lai trên tập test
            y_pred = self.model.predict(X_test)
            
            # Tính sai số (MAE: Sai số tuyệt đối, RMSE: Sai số bình phương trung bình)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            
            mae_scores.append(mae)
            rmse_scores.append(rmse)
            fold += 1
            
        print(f" -> Kết quả đánh giá bằng Cross Validation (5 folds):")
        print(f"    - MAE trung bình:  {np.mean(mae_scores):.2f} (Lệch khoảng {np.mean(mae_scores):.0f} xe)")
        print(f"    - RMSE trung bình: {np.mean(rmse_scores):.2f}")
        
        # Cuối cùng, fit lại toàn bộ dữ liệu lịch sử để dự đoán cho những ngày tương lai thực tế
        print(" -> Đang cập nhật mô hình với toàn bộ dữ liệu...")
        self.model.fit(X, y)
        self.is_trained = True

    def save_model(self):
        """Lưu mô hình bằng joblib ra cục bộ (.pkl)"""
        if not self.is_trained:
            print("Lỗi: Mô hình chưa huấn luyện.")
            return
            
        joblib.dump(self.model, self.model_path)
        print(f"\n[+] ĐÃ LƯU MÔ HÌNH THÀNH CÔNG VÀO FILE: {self.model_path}")
        
    def load_model(self):
        """Khôi phục mô hình từ file .pkl"""
        try:
            self.model = joblib.load(self.model_path)
            self.is_trained = True
            return True
        except FileNotFoundError:
            return False

    def predict(self, raw_data_df):
        """
        BƯỚC 4: Dự báo thời gian thực.
        Nhận lịch sử gần nhất và trả ra số lượng xe dự báo cho KHUNG 15 PHÚT TỚI.
        """
        # Nếu chưa train, hãy load model lên
        if not self.is_trained:
            if not self.load_model():
                raise Exception("Mô hình chưa sẵn sàng. Hãy chạy train() hoặc check file .pkl")
                
        df = raw_data_df.copy().sort_values('timestamp')
        
        if len(df) < 3:
            raise ValueError("Lỗi dữ liệu: Cần nhập ít nhất 3 quan trắc lịch sử liên tiếp (để tính delay lag).")
            
        # 1. Tìm mốc thời gian mục tiêu (Tương lai 15p)
        last_time = df['timestamp'].iloc[-1]
        next_time = last_time + pd.Timedelta(minutes=15)
        
        # 2. Thêm 1 dòng giả tượng trưng cho tương lai 
        # (Để hàm create_features tự kéo dữ liệu lịch sử xuống thành Lag cho dòng này)
        future_row = pd.DataFrame([{
            'timestamp': next_time,
            'vehicle_count': 0  # con số 0 này vô hại, ta chỉ quan tâm features của dòng tương lai
        }])
        
        temp_df = pd.concat([df, future_row], ignore_index=True)
        
        # 3. Kích hoạt Feature Engineering
        processed_data = self.create_features(temp_df)
        
        # 4. Filter lấy riêng cấu trúc của mốc tương lai (dòng nằm dưới cùng) để đi forecast
        target_features = processed_data.iloc[[-1]][self.features]
        
        # 5. Phán đoán và trả về Model
        predicted_value = self.model.predict(target_features)[0]
        
        return max(0, int(round(predicted_value)))


# =========================================================================
# PHẦN TEST SCRIPT ĐỘC LẬP (Không yêu cầu database)
# Chạy file này bằng Python thẳng: python traffic_predictor.py
# =========================================================================
if __name__ == "__main__":
    print("TrafficPredictor module is ready.")

