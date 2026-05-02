import os
import pandas as pd
from ml_service.traffic_predictor import TrafficPredictor

# Scale Factor: kéo dữ liệu Metro (Mỹ, ~815 xe/15p) về thực tế Việt Nam (~450 xe/15p)
SCALE_FACTOR = 450.0 / 815.0   # ≈ 0.55


def main():
    base = os.path.dirname(__file__)
    raw_csv = os.path.join(base, 'data/Metro_Interstate_Traffic_Volume.csv')

    # BƯỚC 1: Đọc và parse datetime
    print("[1] Đọc dữ liệu từ CSV...")
    df = pd.read_csv(raw_csv)
    df['date_time'] = pd.to_datetime(df['date_time'])
    df = df.set_index('date_time').sort_index()
    print(f"    Tổng số record gốc (hourly): {len(df)}")

    # BƯỚC 2: Hourly → 15-minute (chia ÷4 + nội suy theo thời gian)
    print("[2] Chuyển đổi dữ liệu từ 1 giờ → 15 phút (÷4 + interpolate)...")
    df['traffic_volume_15min'] = df['traffic_volume'] / 4
    # Loại bỏ timestamp trùng lặp (giữ lại giá trị trung bình)
    series = (
        df['traffic_volume_15min']
        .groupby(df.index)
        .mean()
        .resample('15min')
        .asfreq()
        .interpolate(method='time')
    )
    df_15min = (
        series
        .reset_index()
        .rename(columns={'date_time': 'timestamp', 'traffic_volume_15min': 'vehicle_count'})
    )
    print(f"    Tổng số record sau chuyển đổi (15-min): {len(df_15min)}")

    # BƯỚC 3: Áp dụng Scale Factor về thực tế Việt Nam (~400–500 xe/15p)
    print(f"[3] Áp dụng Scale Factor ({SCALE_FACTOR:.3f}) về thực tế Việt Nam...")
    df_15min['vehicle_count'] = (
        df_15min['vehicle_count'] * SCALE_FACTOR
    ).round().astype(int).clip(lower=0)
    print(f"    Trung bình vehicle_count sau scale: {df_15min['vehicle_count'].mean():.1f} xe/15p")

    # BƯỚC 4: Huấn luyện Model dự báo số xe
    print("\n--- Training Model: Vehicle Forecast + Density Level ---")
    predictor = TrafficPredictor(os.path.join(base, 'model.pkl'))
    predictor.train_and_evaluate(df_15min)
    predictor.save_model()


    # 4. Tạo nhãn thời gian đèn xanh
    print("\n--- Section 4: Generate Green Light Time Labels ---")
    light_green_time()


if __name__ == "__main__":
    main()