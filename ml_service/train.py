import os
import sys
import pandas as pd
from ml_service.traffic_predictor import TrafficPredictor

def main():
    # Cấu hình stdout/stderr sang UTF-8 để hiển thị tiếng Việt trên Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    base = os.path.dirname(__file__)
    data_dir = os.path.join(base, 'data')
    csv_path = os.path.join(data_dir, 'junction_pivot_clean.csv')

    print("[*] Bắt đầu quá trình huấn luyện hệ thống 3 mô hình học máy thống nhất đa nút giao...")
    print(f" -> Nguồn dữ liệu hợp nhất: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"[!] Lỗi: Không tìm thấy tệp {csv_path}. Hãy chạy preprocess.py trước.")
        sys.exit(1)

    # Đọc dữ liệu lớn hợp nhất
    df_merged = pd.read_csv(csv_path)
    print(f" -> Đã nạp thành công {len(df_merged):,} dòng dữ liệu từ 3 nút giao.")

    # Cấu hình huấn luyện cho 3 mô hình thống nhất
    models_config = {
        'straight': {
            'col': 'vol_straight',
            'desc': 'Mô hình đi thẳng thống nhất (Straight Model)',
            'file': 'model_straight.pkl'
        },
        'left': {
            'col': 'vol_left',
            'desc': 'Mô hình rẽ trái thống nhất (Left Model)',
            'file': 'model_left.pkl'
        },
        'right': {
            'col': 'vol_right',
            'desc': 'Mô hình rẽ phải thống nhất (Right Model)',
            'file': 'model_right.pkl'
        }
    }

    all_metrics = {}

    for direction, config in models_config.items():
        col = config['col']
        desc = config['desc']
        model_file = config['file']
        model_path = os.path.join(base, 'model', model_file)

        print("\n" + "="*80)
        print(f" 🚀 ĐANG HUẤN LUYỆN: {desc}")
        print(f" Cột mục tiêu: {col} | Đường dẫn lưu mô hình: {model_path}")
        print("="*80)

        # 1. Lọc và chuẩn bị dữ liệu cho mô hình này
        # Loại bỏ các dòng NaN ở hướng tương ứng (ví dụ: vol_right bị trống ở Segment 72887 và 83624)
        df_dir = df_merged[['timestamp', 'segment_id', col]].dropna().copy()
        
        # Đổi tên cột mục tiêu để tương thích với TrafficPredictor
        df_dir = df_dir.rename(columns={col: 'vehicle_count'})
        
        # Chuyển đổi timestamp và sắp xếp thời gian để chia Train/Test chronological chuẩn xác
        df_dir['timestamp'] = pd.to_datetime(df_dir['timestamp'])
        df_dir = df_dir.sort_values('timestamp').reset_index(drop=True)

        print(f"    - Lực lượng dữ liệu thực đo (không NaN): {len(df_dir):,} dòng")
        print(f"    - Phân bố phân đoạn vật lý (segment_id):")
        seg_counts = df_dir['segment_id'].value_counts()
        for s_id, cnt in seg_counts.items():
            print(f"      * Segment {s_id}: {cnt:,} dòng ({cnt/len(df_dir)*100:.1f}%)")
        print(f"    - Khoảng thời gian: {df_dir['timestamp'].min()} -> {df_dir['timestamp'].max()}")

        # 2. Khởi tạo TrafficPredictor và chạy huấn luyện 80/20 split
        # TrafficPredictor tự động áp dụng Grouped Feature Engineering vì df_dir có cột 'segment_id'
        predictor = TrafficPredictor(model_path=model_path)
        metrics = predictor.train_and_evaluate_split(df_dir)

        # 3. Lưu trữ trọng số mô hình
        predictor.save_model()
        all_metrics[direction] = {
            'desc': desc,
            'metrics': metrics
        }

    # Báo cáo đánh giá khoa học tổng hợp cho 3 mô hình
    print("\n" + "="*80)
    print(" BÁO CÁO KHOA HỌC TỔNG HỢP HIỆU NĂNG 3 MÔ HÌNH HỢP NHẤT TRÊN TẬP TEST")
    print("="*80)
    print(f"{'Mô hình':<40} | {'MAE':<10} | {'RMSE':<10} | {'MAPE':<10}")
    print("-"*80)
    for direction, result in all_metrics.items():
        desc = result['desc']
        m = result['metrics']
        if m:
            print(f"{desc:<40} | {m['mae']:>8.2f} xe | {m['rmse']:>8.2f} xe | {m['mape']:>8.2f}%")
        else:
            print(f"{desc:<40} | Không có kết quả đánh giá.")
    print("="*80)
    print("[+] TIẾN TRÌNH HUẤN LUYỆN 3 MÔ HÌNH THỐNG NHẤT ĐÃ HOÀN THÀNH XUẤT SẮC!")
    print("="*80)

if __name__ == '__main__':
    main()