import os
import sys
import pandas as pd

# Add parent directory to sys.path to import ml_service modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ml_service.traffic_predictor import TrafficPredictor

SCALE_FACTOR = 450.0 / 815.0


def main():
    base = os.path.dirname(__file__)
    raw_csv = os.path.join(base, 'data/Metro_Interstate_Traffic_Volume.csv')

    print("[1] Đọc dữ liệu từ CSV...")
    df = pd.read_csv(raw_csv, keep_default_na=False)
    df['date_time'] = pd.to_datetime(df['date_time'])
    df = df.set_index('date_time').sort_index()

    df_num = df.select_dtypes(include=['number']).groupby(df.index).mean()
    df_cat = df.select_dtypes(exclude=['number']).groupby(df.index).first()
    df = pd.concat([df_num, df_cat], axis=1)

    print(f"    Tổng số record gốc (hourly sau clean): {len(df)}")

    print("[2] Chuyển đổi dữ liệu từ 1 giờ → 15 phút...")

    df_15min = df.resample('15min').asfreq()

    df_15min['traffic_volume'] = (
        df['traffic_volume']
        .resample('15min')
        .interpolate('time')
    )

    for col in df.columns:
        if col != 'traffic_volume':
            df_15min[col] = df[col].resample('15min').ffill()

    df_15min['traffic_volume'] = df_15min['traffic_volume'] / 4

    print(f"    Tổng số record sau chuyển đổi (15-min): {len(df_15min)}")

    print(f"[3] Áp dụng Scale Factor ({SCALE_FACTOR:.3f})...")
    df_15min['traffic_volume'] = (
        df_15min['traffic_volume'] * SCALE_FACTOR
    ).round().astype(int).clip(lower=0)

    print(f"    Trung bình traffic_volume sau scale: {df_15min['traffic_volume'].mean():.1f}")

    df_15min = df_15min.reset_index()
    df_15min.rename(columns={'date_time': 'timestamp'}, inplace=True)

    print("\n--- Training Model ---")
    predictor = TrafficPredictor(os.path.join(base, 'model.pkl'))
    predictor.train_and_evaluate(
        df_15min.rename(columns={'traffic_volume': 'vehicle_count'})
    )
    predictor.save_model()

    print("\n--- Save data after training (with predictions) ---")

    df_after_train = df_15min.copy()

    feature_cols = predictor.model.feature_names_in_
    features = df_after_train.reindex(columns=feature_cols, fill_value=0)

    df_after_train['predicted_vehicle_count'] = predictor.model.predict(features)

    output_train_csv = os.path.join(base, 'data/traffic_after_train.csv')
    os.makedirs(os.path.dirname(output_train_csv), exist_ok=True)

    df_after_train.to_csv(output_train_csv, index=False)

    print(f"[+] Saved trained data: {output_train_csv}")


if __name__ == "__main__":
    main()