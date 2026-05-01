"""
ml_service/light_delta_model.py
===============================
Model đề xuất delta đèn xanh (giây) — XGBoost Regressor độc lập.

Features đầu vào:
    - queue_proxy       : Ước tính độ dài hàng đợi (xe, float)
    - inbound_count     : Lưu lượng xe vào giao lộ trong chu kỳ (int)
    - congestion_level  : Mức độ tắc nghẽn dạng chuỗi ('low'/'medium'/'high')
    - baseline_green    : Thời gian đèn xanh cơ bản của pha này (giây, int)
    - hour              : Giờ trong ngày (0–23)
    - day_of_week       : Thứ trong tuần (0=Thứ Hai ... 6=Chủ Nhật)

Target:
    - delta_green       : Số giây cần điều chỉnh thêm (âm = giảm, dương = tăng)

API công khai:
    train_delta(df)               → Huấn luyện & lưu light_model.pkl
    predict_delta(feature_dict)   → float (giây, đã clamp)
"""

import os
import warnings
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------
_DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "light_model.pkl")

FEATURES = [
    "queue_proxy",
    "inbound_count",
    "congestion_level_enc",   # congestion_level sau khi encode
    "baseline_green",
    "hour",
    "day_of_week",
]

# Bảng ánh xạ mức tắc nghẽn → số nguyên (dùng khi DataFrame đã có giá trị tường minh)
_CONGESTION_MAP = {"low": 0, "medium": 1, "high": 2}

# Giới hạn an toàn cho delta (giây)
_DELTA_MIN = -30
_DELTA_MAX = 45


# ---------------------------------------------------------------------------
# Hàm tiện ích nội bộ
# ---------------------------------------------------------------------------

def _encode_congestion(series: pd.Series) -> pd.Series:
    """
    Chuyển cột congestion_level (chuỗi) thành số nguyên.
    Hỗ trợ cả giá trị đã là số (bỏ qua encode) và chuỗi (low/medium/high).
    """
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(int)

    # Chuẩn hoá chữ thường, xử lý giá trị lạ bằng LabelEncoder
    lower = series.str.strip().str.lower()
    if lower.isin(_CONGESTION_MAP.keys()).all():
        return lower.map(_CONGESTION_MAP).astype(int)

    # Fallback: sklearn LabelEncoder cho các nhãn tuỳ ý
    le = LabelEncoder()
    return pd.Series(le.fit_transform(lower), index=series.index)


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nhận DataFrame thô (có cột congestion_level dạng chuỗi) và
    trả về DataFrame đã có cột congestion_level_enc sẵn sàng để train/predict.
    """
    data = df.copy()

    if "congestion_level" in data.columns:
        data["congestion_level_enc"] = _encode_congestion(data["congestion_level"])
    elif "congestion_level_enc" not in data.columns:
        raise ValueError(
            "DataFrame phải có cột 'congestion_level' (chuỗi) "
            "hoặc 'congestion_level_enc' (số nguyên)."
        )

    return data


# ---------------------------------------------------------------------------
# Lớp chính
# ---------------------------------------------------------------------------

class LightDeltaModel:
    """
    XGBoost Regressor thứ 2 — đề xuất delta thời gian đèn xanh.
    Train hoàn toàn độc lập với TrafficPredictor (traffic_predictor.py).
    """

    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self._model: xgb.XGBRegressor | None = None

        # Cấu hình XGBoost — học chậm để ổn định, tránh phản ứng thái quá
        self._xgb_params = dict(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
            random_state=42,
        )

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def train_delta(self, df: pd.DataFrame) -> None:
        """
        Huấn luyện mô hình từ DataFrame và lưu ra light_model.pkl.

        Tham số
        -------
        df : pd.DataFrame
            Phải chứa tất cả các cột sau:
            queue_proxy, inbound_count, congestion_level (hoặc congestion_level_enc),
            baseline_green, hour, day_of_week, delta_green.
        """
        print("\n[LightDeltaModel] Bắt đầu huấn luyện Model Đèn...")

        data = _prepare_features(df)

        missing = [c for c in FEATURES + ["delta_green"] if c not in data.columns]
        if missing:
            raise ValueError(f"Thiếu các cột bắt buộc: {missing}")

        X = data[FEATURES]
        y = data["delta_green"]

        print(f"  → Tổng số mẫu: {len(X):,}  |  Phân phối target (delta_green):")
        print(f"     min={y.min():.1f}s  max={y.max():.1f}s  mean={y.mean():.2f}s  std={y.std():.2f}s")

        # Cross-validation nhanh (3-fold) để báo cáo MAE ước tính
        tmp_model = xgb.XGBRegressor(**self._xgb_params)
        cv_scores = cross_val_score(
            tmp_model, X, y,
            cv=3,
            scoring="neg_mean_absolute_error",
        )
        print(f"  → Cross-val MAE (3-fold): {-cv_scores.mean():.2f}s ± {cv_scores.std():.2f}s")

        # Fit trên toàn bộ tập
        self._model = xgb.XGBRegressor(**self._xgb_params)
        self._model.fit(X, y)

        # Đánh giá in-sample
        y_pred = self._model.predict(X)
        mae_full = mean_absolute_error(y, y_pred)
        print(f"  → MAE toàn bộ tập (in-sample): {mae_full:.2f}s")

        # Lưu model
        joblib.dump(self._model, self.model_path)
        print(f"  ✅ Đã lưu Model Đèn tại: {self.model_path}\n")

    def predict_delta(self, feature_dict: dict) -> float:
        """
        Dự đoán delta thời gian đèn xanh cho một quan trắc.

        Tham số
        -------
        feature_dict : dict
            Bắt buộc có các khoá:
            - queue_proxy       (float | int)
            - inbound_count     (int)
            - congestion_level  (str: 'low' | 'medium' | 'high')
            - baseline_green    (int, giây)
            - hour              (int, 0–23)
            - day_of_week       (int, 0–6)

        Trả về
        -------
        float
            Số giây điều chỉnh đề xuất, clamp trong [–30, +45].
        """
        # 1. Load model nếu chưa có trong RAM
        if self._model is None:
            self._load()

        # 2. Xây DataFrame 1 dòng từ dict
        row = {
            "queue_proxy":      float(feature_dict["queue_proxy"]),
            "inbound_count":    int(feature_dict["inbound_count"]),
            "congestion_level": str(feature_dict["congestion_level"]),
            "baseline_green":   int(feature_dict["baseline_green"]),
            "hour":             int(feature_dict["hour"]),
            "day_of_week":      int(feature_dict["day_of_week"]),
        }
        df_input = pd.DataFrame([row])

        # 3. Encode congestion_level → congestion_level_enc
        df_input = _prepare_features(df_input)

        # 4. Predict & clamp
        raw_delta: float = float(self._model.predict(df_input[FEATURES])[0])
        clamped = float(np.clip(raw_delta, _DELTA_MIN, _DELTA_MAX))
        return clamped

    # ------------------------------------------------------------------
    # PRIVATE
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load model từ file .pkl vào bộ nhớ."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Không tìm thấy file model: {self.model_path}\n"
                "Hãy chạy train_delta() hoặc script train.py trước."
            )
        self._model = joblib.load(self.model_path)
        print(f"[LightDeltaModel] Đã tải model từ: {self.model_path}")


# ---------------------------------------------------------------------------
# Hàm tiện ích cấp module (API ngắn gọn)
# ---------------------------------------------------------------------------

def train_delta(df: pd.DataFrame, model_path: str = _DEFAULT_MODEL_PATH) -> LightDeltaModel:
    """
    Hàm-level wrapper: khởi tạo LightDeltaModel, huấn luyện và trả về instance.

    Ví dụ sử dụng
    -------------
    >>> from ml_service.light_delta_model import train_delta
    >>> model = train_delta(df_training)
    """
    mdl = LightDeltaModel(model_path=model_path)
    mdl.train_delta(df)
    return mdl


def predict_delta(feature_dict: dict, model_path: str = _DEFAULT_MODEL_PATH) -> float:
    """
    Hàm-level wrapper: load model và trả về delta đèn (giây).

    Ví dụ sử dụng
    -------------
    >>> from ml_service.light_delta_model import predict_delta
    >>> delta = predict_delta({
    ...     "queue_proxy": 12.5,
    ...     "inbound_count": 45,
    ...     "congestion_level": "high",
    ...     "baseline_green": 30,
    ...     "hour": 8,
    ...     "day_of_week": 1,
    ... })
    >>> print(f"Đề xuất điều chỉnh: {delta:+.1f}s")
    """
    mdl = LightDeltaModel(model_path=model_path)
    return mdl.predict_delta(feature_dict)


# ---------------------------------------------------------------------------
# SCRIPT TEST ĐỘC LẬP
# Chạy: python -m ml_service.light_delta_model
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  LightDeltaModel — Demo Train & Predict (dữ liệu giả)")
    print("=" * 60)

    # --- Tạo dữ liệu giả để minh hoạ ---
    rng = np.random.default_rng(seed=0)
    N = 500
    hours = rng.integers(0, 24, N)
    days = rng.integers(0, 7, N)
    inbound = rng.integers(5, 80, N).astype(float)
    queue_p = rng.uniform(-20, 30, N)
    cong_levels = rng.choice(["low", "medium", "high"], N)
    baseline = rng.choice([20, 25, 30, 35, 40], N).astype(float)

    # Nhãn heuristic đơn giản (giống label_generator.py)
    delta_labels = np.where(queue_p > 15, 30,
                   np.where(queue_p > 5,  15,
                   np.where(queue_p < -15, -30,
                   np.where(queue_p < -5,  -15, 0))))

    df_demo = pd.DataFrame({
        "hour":              hours,
        "day_of_week":       days,
        "inbound_count":     inbound,
        "queue_proxy":       queue_p,
        "congestion_level":  cong_levels,
        "baseline_green":    baseline,
        "delta_green":       delta_labels,
    })

    # --- Train ---
    model_instance = LightDeltaModel(model_path="light_model_demo.pkl")
    model_instance.train_delta(df_demo)

    # --- Predict với feature_dict ---
    sample = {
        "queue_proxy":      18.0,    # Hàng đợi dài → nên tăng đèn xanh
        "inbound_count":    60,
        "congestion_level": "high",
        "baseline_green":   30,
        "hour":             8,       # Giờ cao điểm sáng
        "day_of_week":      1,       # Thứ Ba
    }

    delta = model_instance.predict_delta(sample)
    print(f"\nInput  : {sample}")
    print(f"Output : delta_green = {delta:+.2f}s  (clamp [{_DELTA_MIN}, +{_DELTA_MAX}])")

    # Dọn file demo
    if os.path.exists("light_model_demo.pkl"):
        os.remove("light_model_demo.pkl")
        print("\n[Demo] Đã xoá file light_model_demo.pkl (file thật: light_model.pkl)")
    print("=" * 60)