import xgboost as xgb
import joblib
import pandas as pd

class LightDeltaModel:
    def __init__(self, model_path='light_model.pkl'):
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.05, # Học chậm hơn để ổn định nhịp đèn
            max_depth=4,
            objective='reg:squarederror'
        )
        self.model_path = model_path
        self.features = ['hour', 'day_of_week', 'is_peak_hour', 'inbound_count', 'queue_proxy']

    def train(self, df):
        X = df[self.features]
        y = df['delta_green']
        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)
        print(f"✅ Đã huấn luyện và lưu Model Đèn tại: {self.model_path}")

    def predict_delta(self, current_features_df):
        model = joblib.load(self.model_path)
        delta = model.predict(current_features_df[self.features])[0]
        # Giới hạn an toàn (Clamp) từ -30s đến +45s
        return max(-30, min(45, int(round(delta))))