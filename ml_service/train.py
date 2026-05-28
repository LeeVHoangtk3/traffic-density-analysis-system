import os
import sys
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.cluster import KMeans
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

# Đảm bảo PYTHONPATH đúng
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from backend.mongo_database import db

def run_pipeline():
    # Cấu hình stdout/stderr UTF-8 cho console Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    print("="*80)
    print(" 🚀 KHỞI ĐỘNG PIPELINE: TIỀN XỬ LÝ - VALIDATE DATA - HUẤN LUYỆN - DỌN DẸP")
    print("="*80)

    raw_csv = os.path.join(PROJECT_ROOT, "data", "ml", "Automated_Traffic_Volume_Counts_20260521.csv")
    out_dir = os.path.join(PROJECT_ROOT, "ml_service", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "junction_pivot_clean.csv")

    if not os.path.exists(raw_csv):
        print(f"[!] Lỗi nghiêm trọng: Không tìm thấy file dữ liệu thô tại: {raw_csv}")
        sys.exit(1)

    # ==========================================================================
    # BƯỚC 1: TIỀN XỬ LÝ & LÀM SẠCH DỮ LIỆU THÔ (RAW DATA PREPROCESSING)
    # ==========================================================================
    print("\n[*] Bước 1: Đang nạp dữ liệu thô (286MB) và xử lý tối ưu bộ nhớ...")
    cols_to_use = ['Yr', 'M', 'D', 'HH', 'MM', 'Vol', 'SegmentID', 'Direction']
    
    # Nạp dữ liệu hiệu năng cao bằng cách chỉ chọn cột cần dùng và ép kiểu
    df_raw = pd.read_csv(raw_csv, usecols=cols_to_use)
    print(f" -> Đã nạp {len(df_raw):,} dòng dữ liệu thô.")

    print("[*] Đang làm sạch cột lưu lượng (Vol)...")
    # Làm sạch dấu phẩy trong cột Vol và đưa về định dạng số
    df_raw['Vol_clean'] = df_raw['Vol'].astype(str).str.replace(',', '', regex=False)
    df_raw['Vol_clean'] = pd.to_numeric(df_raw['Vol_clean'], errors='coerce')
    
    # Lọc bỏ giá trị trống (NaN) và các lưu lượng lỗi âm (Vol < 0)
    df_raw = df_raw.dropna(subset=['Vol_clean'])
    df_raw = df_raw[df_raw['Vol_clean'] >= 0]
    df_raw['Vol_clean'] = df_raw['Vol_clean'].astype(int)

    print("[*] Đang chuẩn hóa mốc thời gian và làm tròn chu kỳ 15 phút...")
    # Tạo chuỗi thời gian timestamp
    datetime_str = (
        df_raw['Yr'].astype(str) + '-' +
        df_raw['M'].astype(str).str.zfill(2) + '-' +
        df_raw['D'].astype(str).str.zfill(2) + ' ' +
        df_raw['HH'].astype(str).str.zfill(2) + ':' +
        df_raw['MM'].astype(str).str.zfill(2)
    )
    df_raw['timestamp'] = pd.to_datetime(datetime_str, errors='coerce')
    df_raw = df_raw.dropna(subset=['timestamp'])
    
    # Làm tròn thời gian về khoảng 15 phút chuẩn (00, 15, 30, 45)
    df_raw['timestamp'] = df_raw['timestamp'].dt.round('15min')

    # Loại bỏ trùng lặp và tính trung bình nếu có trùng lặp mốc đo
    df_clean = (
        df_raw.groupby(['SegmentID', 'Direction', 'timestamp'])['Vol_clean']
        .mean()
        .reset_index()
    )
    df_clean['Vol_clean'] = df_clean['Vol_clean'].round().astype(int)

    # Cấu hình segment rẽ hướng đô thị của dự án cũ để giữ tính tương thích ngược cột
    segments_config = {
        138: {
            'mapping': {'NB': 'vol_straight', 'WB': 'vol_left', 'EB': 'vol_right'},
            'desc': 'Nút giao ngã ba tách làn (SegmentID 138)'
        },
        72887: {
            'mapping': {'EB': 'vol_straight', 'WB': 'vol_left'},
            'desc': 'Tuyến trục Đông-Tây lớn (SegmentID 72887)'
        },
        83624: {
            'mapping': {'NB': 'vol_straight', 'SB': 'vol_left'},
            'desc': 'Tuyến song hành Nam-Bắc (SegmentID 83624)'
        }
    }

    target_cols = ['timestamp', 'segment_id', 'vol_straight', 'vol_left', 'vol_right']
    all_segments_chunks = []

    print("[*] Đang xoay trục và nội suy mượt mà chuỗi thời gian cho từng Segment...")
    for seg_id, config in segments_config.items():
        df_seg = df_clean[df_clean['SegmentID'] == seg_id].copy()
        if df_seg.empty:
            continue

        unique_timestamps = sorted(df_seg['timestamp'].unique())
        ts_series = pd.Series(unique_timestamps)
        diffs = ts_series.diff()
        
        # Nếu khoảng cách giữa 2 mốc liên tiếp > 24 giờ, xem như chu kỳ đo mới (tránh lệch nội suy)
        gap_threshold = pd.Timedelta(hours=24)
        block_idx = (diffs > gap_threshold).cumsum()
        ts_to_block = dict(zip(unique_timestamps, block_idx))
        df_seg['block_id'] = df_seg['timestamp'].map(ts_to_block)

        chunks = []
        for block_id, block_df in df_seg.groupby('block_id'):
            p_pivot = block_df.pivot(index='timestamp', columns='Direction', values='Vol_clean').reset_index()
            p_pivot = p_pivot.rename(columns=config['mapping'])
            p_pivot['segment_id'] = seg_id
            
            for col in target_cols:
                if col not in p_pivot.columns:
                    p_pivot[col] = np.nan
            
            p_pivot = p_pivot[target_cols]
            
            for col in ['vol_straight', 'vol_left', 'vol_right']:
                p_pivot[col] = p_pivot[col].astype(float)
                
            p_pivot = p_pivot.set_index('timestamp').sort_index()
            # Nội suy thời gian tuyến tính mượt mà cho các khoảng trống nhỏ
            p_pivot_res = p_pivot[['vol_straight', 'vol_left', 'vol_right']].resample('15min').asfreq()
            p_pivot_res = p_pivot_res.interpolate(method='time').ffill().bfill()
            p_pivot_res['segment_id'] = seg_id
            
            if len(p_pivot_res) >= 12:  # Bỏ qua block dưới 3 tiếng
                chunks.append(p_pivot_res.reset_index())

        if chunks:
            df_seg_final = pd.concat(chunks, ignore_index=True)
            all_segments_chunks.append(df_seg_final)

    if not all_segments_chunks:
        print("[!] Lỗi: Không thể cấu trúc được dữ liệu sạch. Dừng pipeline.")
        sys.exit(1)

    df_final = pd.concat(all_segments_chunks, ignore_index=True)
    df_final = df_final.sort_values(['timestamp', 'segment_id']).reset_index(drop=True)
    
    # Tính toán Vol_clean tổng cộng
    df_final['vol_straight'] = df_final['vol_straight'].fillna(0)
    df_final['vol_left'] = df_final['vol_left'].fillna(0)
    df_final['vol_right'] = df_final['vol_right'].fillna(0)
    df_final['Vol_clean'] = df_final['vol_straight'] + df_final['vol_left'] + df_final['vol_right']

    # Xuất file CSV sạch tối giản, chỉ giữ lại các cột cần thiết cho hệ thống đếm tổng đơn ROI
    df_export = df_final[['timestamp', 'segment_id', 'Vol_clean']]
    df_export.to_csv(out_csv, index=False)
    print(f"[+] Đã hoàn thành xử lý và lưu tệp dữ liệu đơn ROI tối giản vào: {out_csv}")

    # ==========================================================================
    # BƯỚC 2: KIỂM ĐỊNH & ĐÁNH GIÁ CHẤT LƯỢNG DỮ LIỆU (VALIDATE DATA REPORT)
    # ==========================================================================
    print("\n" + "="*80)
    print(" 📊 BÁO CÁO KIỂM ĐỊNH VÀ ĐÁNH GIÁ DỮ LIỆU (DATA VALIDATION REPORT)")
    print("="*80)
    
    total_rows = len(df_final)
    missing_straight = df_final['vol_straight'].isnull().sum()
    missing_left = df_final['vol_left'].isnull().sum()
    missing_right = df_final['vol_right'].isnull().sum()
    
    # Thống kê mô tả về Vol_clean tổng
    vol_stats = df_final['Vol_clean'].describe()
    
    print(f" 1. Quy mô dữ liệu sạch: {total_rows:,} bản ghi chuỗi thời gian 15 phút.")
    print(f" 2. Kiểm tra dữ liệu khuyết thiếu (NaN):")
    print(f"    - vol_straight : {missing_straight} dòng ({(missing_straight/total_rows)*100:.2f}%)")
    print(f"    - vol_left     : {missing_left} dòng ({(missing_left/total_rows)*100:.2f}%)")
    print(f"    - vol_right    : {missing_right} dòng ({(missing_right/total_rows)*100:.2f}%)")
    print(f"    -> Đã được tự động điền khuyết thiếu bằng 0 và nội suy mượt mà.")
    
    print(f"\n 3. Thống kê phân phối lưu lượng xe tổng cộng (Vol_clean):")
    print(f"    - Giá trị trung bình (Mean)  : {vol_stats['mean']:.2f} xe / 15 phút")
    print(f"    - Độ lệch chuẩn (Std Dev)    : {vol_stats['std']:.2f} xe")
    print(f"    - Lưu lượng tối thiểu (Min)  : {vol_stats['min']:.2f} xe / 15 phút")
    print(f"    - 25% (Q1 - Mức thấp)        : {vol_stats['25%']:.2f} xe / 15 phút")
    print(f"    - 50% (Trung vị - Median)    : {vol_stats['50%']:.2f} xe / 15 phút")
    print(f"    - 75% (Q3 - Mức cao)        : {vol_stats['75%']:.2f} xe / 15 phút")
    print(f"    - Lưu lượng tối đa (Max - Peak): {vol_stats['max']:.2f} xe / 15 phút")
    
    # Phát hiện bất thường
    anomalous_records = df_final[df_final['Vol_clean'] < 0]
    extreme_outliers = df_final[df_final['Vol_clean'] > 3000]
    print(f"\n 4. Phát hiện bất thường & Ngoại lai (Outliers):")
    print(f"    - Số bản ghi âm (Vol < 0)    : {len(anomalous_records)} dòng -> Đã lọc bỏ.")
    print(f"    - Số bản ghi cực đoan (>3000): {len(extreme_outliers)} dòng -> Đã lọc bỏ để ổn định mô hình.")
    
    # Trích xuất phân phối thời gian
    df_final['hour'] = df_final['timestamp'].dt.hour
    peak_hours = df_final.groupby('hour')['Vol_clean'].mean()
    busy_hour = peak_hours.idxmax()
    quiet_hour = peak_hours.idxmin()
    print(f"\n 5. Phân tích chuỗi thời gian thực tế:")
    print(f"    - Giờ cao điểm trung bình nhất: {busy_hour}:00 -> {busy_hour}:45 ({peak_hours[busy_hour]:.1f} xe / 15p)")
    print(f"    - Giờ thấp điểm trung bình nhất: {quiet_hour}:00 -> {quiet_hour}:45 ({peak_hours[quiet_hour]:.1f} xe / 15p)")
    print("="*80)

    # ==========================================================================
    # BƯỚC 3: TRÍCH XUẤT ĐẶC TRƯNG & HUẤN LUYỆN MÔ HÌNH XGBOOST REGRESSOR
    # ==========================================================================
    print("\n[*] Bước 3: Đang tạo ma trận đặc trưng Feature Engineering...")
    
    # Lọc bỏ giá trị cực đoan
    df_feat = df_final[df_final['Vol_clean'] <= 3000].copy()
    
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
    
    df_feat = df_feat.dropna(subset=['lag_1', 'lag_2', 'rolling_mean_3']).reset_index(drop=True)

    print("[*] Đang thực hiện chia tách Train/Test 80/20 theo thời gian...")
    feature_cols = ['lag_1', 'lag_2', 'rolling_mean_3', 'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend']
    X = df_feat[feature_cols]
    y = df_feat['Vol_clean']
    
    split_idx = int(len(df_feat) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print("[*] Đang huấn luyện XGBoost Regressor...")
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

    # Đánh giá mô hình
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / np.clip(y_test, 1, None))) * 100

    print("\n" + "-"*80)
    print(" KẾT QUẢ ĐÁNH GIÁ MÔ HÌNH HỢP NHẤT TRÊN TẬP TEST:")
    print(f"  * Mean Absolute Error (MAE)      : {mae:.2f} xe")
    print(f"  * Root Mean Squared Error (RMSE)  : {rmse:.2f} xe")
    print(f"  * Mean Absolute Percentage (MAPE): {mape:.2f}%")
    print(f"  * R-squared (R2 Score)           : {r2:.4f}")
    print("-"*80)

    # Lưu trữ mô hình pkl duy nhất vào thư mục ml_service/model/
    model_dir = os.path.join(PROJECT_ROOT, 'ml_service')
    model_sub_dir = os.path.join(model_dir, 'model')
    os.makedirs(model_sub_dir, exist_ok=True)
    model_path2 = os.path.join(model_sub_dir, 'model.pkl')
    with open(model_path2, 'wb') as f:
        pickle.dump(model, f)
        
    print(f"[+] Đã xuất mô hình thành công vào thư mục chuyên dụng: {model_path2}")

    # ==========================================================================
    # BƯỚC 4: CHẠY K-MEANS PHÂN CỤM NGƯỠNG THÍCH ỨNG & CẬP NHẬT MONGODB
    # ==========================================================================
    print("\n[*] Bước 4: Đang chạy phân cụm K-Means mật độ tự thích ứng...")
    volumes = df_feat['Vol_clean'].values.reshape(-1, 1)
    
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=15)
    kmeans.fit(volumes)
    centroids = sorted(kmeans.cluster_centers_.flatten())
    
    C0, C1, C2, C3 = centroids
    T1 = (C0 + C1) / 2.0
    T2 = (C1 + C2) / 2.0
    T3 = (C2 + C3) / 2.0

    print(f"    - Trọng tâm cụm: C0={C0:.1f}, C1={C1:.1f}, C2={C2:.1f}, C3={C3:.1f}")
    print(f"    - Ngưỡng động: T1={T1:.2f}, T2={T2:.2f}, T3={T3:.2f}")

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

    try:
        # Cập nhật các collection để tương thích
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
        print("[+] Đã lưu cập nhật ma trận ngưỡng K-Means thích ứng thành công vào MongoDB.")
    except Exception as e:
        print(f"[!] Lỗi khi ghi MongoDB: {e}")

    # ==========================================================================
    # BƯỚC 5: DỌN DẸP SẠCH SẼ THƯ MỤC ML_SERVICE (CLEANUP WORKSPACE)
    # ==========================================================================
    print("\n[*] Bước 5: Đang quét dọn các mô hình cũ và file tạm lỗi thời...")
    
    # Các file cần giữ lại ở thư mục gốc ml_service/
    keep_files = {'train.py', 'traffic_predictor.py', 'density_cluster.py', 
                  'preprocess.py', 'README.md', '__init__.py'}
    
    # Dọn dẹp thư mục ml_service trực tiếp
    for item in os.listdir(model_dir):
        item_path = os.path.join(model_dir, item)
        if os.path.isfile(item_path) and item not in keep_files:
            # Kiểm tra xem có phải file tạm hoặc model rẽ cũ không
            if item.endswith('.pkl') or item.endswith('.csv') or item.endswith('.png') or item.endswith('.json'):
                try:
                    os.remove(item_path)
                    print(f"  -> Đã xóa file rác: {item}")
                except Exception as e:
                    print(f"  -> Lỗi xóa file {item}: {e}")

    # Dọn dẹp thư mục ml_service/model/
    if os.path.exists(model_sub_dir):
        for item in os.listdir(model_sub_dir):
            item_path = os.path.join(model_sub_dir, item)
            if os.path.isfile(item_path) and item != 'model.pkl':
                try:
                    os.remove(item_path)
                    print(f"  -> Đã xóa model rẽ cũ trong sub-folder: {item}")
                except Exception as e:
                    print(f"  -> Lỗi xóa sub-file {item}: {e}")

    # Dọn dẹp thư mục ml_service/data/
    data_dir_files = os.listdir(out_dir)
    for item in data_dir_files:
        item_path = os.path.join(out_dir, item)
        if os.path.isfile(item_path) and item != 'junction_pivot_clean.csv':
            try:
                os.remove(item_path)
                print(f"  -> Đã xóa file tạm trong data-folder: {item}")
            except Exception as e:
                print(f"  -> Lỗi xóa data-file {item}: {e}")

    print("\n" + "="*80)
    print(" 🎉 PIPELINE HOÀN THÀNH XUẤT SẮC - MÔI TRƯỜNG DỰ ÁN SẠCH SẼ & TỐI ƯU!")
    print("="*80)

if __name__ == '__main__':
    run_pipeline()
