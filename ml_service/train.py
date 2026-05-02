import os
import pandas as pd
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
    predictor.train_and_evaluate(df_15min.rename(columns={'traffic_volume': 'vehicle_count'}))
    predictor.save_model()

    output_csv = os.path.join(base, 'data/Metro_Interstate_Traffic_Volume_15min.csv')
    df_15min.to_csv(output_csv, index=False)
    print(f"[+] Saved: {output_csv}")

    print("\n--- Section 4 ---")

    df = pd.read_csv(output_csv, keep_default_na=False)

    avg = df['traffic_volume'].mean()
    df['time-green-light'] = 45
    print(avg)

    for i in range(len(df)):
        t = df.iloc[i]['time-green-light']

        delta = (abs(df.iloc[i]['traffic_volume'] - avg) / avg) * 100
        t = t + (delta // 10) * 5

        if df.iloc[i]['holiday'] not in ["None", "", None]:
            t += 10

        df.at[i, 'time-green-light'] = t

    print(df[['traffic_volume', 'holiday', 'time-green-light']].head())
    df.to_csv(output_csv, index=False, na_rep="None")


if __name__ == "__main__":
    main()