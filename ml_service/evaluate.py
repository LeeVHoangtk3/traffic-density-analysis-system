import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_service.traffic_predictor import TrafficPredictor

def compute_mape(y_true, y_pred):
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    mask = y_true_arr > 0
    if np.any(mask):
        return np.mean(np.abs((y_true_arr[mask] - y_pred_arr[mask]) / y_true_arr[mask])) * 100
    return 0.0

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, 'data')
    csv_path = os.path.join(data_dir, 'junction_pivot_clean.csv')

    print("[*] Nạp dữ liệu đánh giá từ:", csv_path)
    if not os.path.exists(csv_path):
        print(f"[!] Lỗi: Không tìm thấy {csv_path}")
        sys.exit(1)

    df_merged = pd.read_csv(csv_path)
    df_merged['timestamp'] = pd.to_datetime(df_merged['timestamp'])

    models_config = {
        'straight': {'col': 'vol_straight', 'file': 'model_straight.pkl'},
        'left': {'col': 'vol_left', 'file': 'model_left.pkl'},
        'right': {'col': 'vol_right', 'file': 'model_right.pkl'}
    }

    results = {}

    for direction, config in models_config.items():
        col = config['col']
        model_path = os.path.join(base, 'model', config['file'])
        
        print(f"\n[*] Đang đánh giá hướng: {direction}")
        
        # Lọc dữ liệu
        df_dir = df_merged[['timestamp', 'segment_id', col]].dropna().copy()
        df_dir = df_dir.rename(columns={col: 'vehicle_count'})
        df_dir = df_dir.sort_values('timestamp').reset_index(drop=True)

        predictor = TrafficPredictor(model_path=model_path)
        if not predictor.load_model():
            print(f"[!] Không tìm thấy mô hình {model_path}")
            continue

        # Tạo features trước khi cắt tập test để lag features không bị mất ở biên
        processed_data = predictor.create_features(df_dir)
        
        # Lọc tập Test từ 2025-01-01
        test_data = processed_data[processed_data['timestamp'] >= '2025-01-01'].copy()
        
        if len(test_data) == 0:
            print(f"[!] Cảnh báo: Tập test của {direction} trống (không có dữ liệu >= 2025-01-01)")
            continue

        X_test = test_data[predictor.features]
        y_test = test_data['vehicle_count']
        
        y_pred = predictor.model.predict(X_test)
        y_pred = np.round(np.clip(y_pred, 0, None)) # Cắt giá trị âm và làm tròn thành số nguyên giống hệt wrapper predict()
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mape = compute_mape(y_test, y_pred)
        
        test_size = len(test_data)
        
        results[direction] = {
            "test_size": test_size,
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mape": round(mape, 2)
        }
        
        # Plot 100 points
        points_to_plot = min(100, test_size)
        y_test_plot = y_test.iloc[:points_to_plot].values
        y_pred_plot = y_pred[:points_to_plot]
        time_plot = test_data['timestamp'].iloc[:points_to_plot].values
        
        plt.figure(figsize=(12, 6))
        plt.plot(time_plot, y_test_plot, color='blue', linestyle='-', label='Actual')
        plt.plot(time_plot, y_pred_plot, color='red', linestyle='--', label='Predicted')
        
        plt.title(f'Actual vs Predicted Traffic Volume - {direction.capitalize()} (100 continuous intervals)')
        plt.xlabel('Time')
        plt.ylabel('Vehicle Count')
        plt.legend()
        
        # Thêm text MAE, MAPE
        text_str = f"MAE: {mae:.2f}\nMAPE: {mape:.2f}%"
        plt.text(0.05, 0.95, text_str, transform=plt.gca().transAxes, fontsize=12,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plot_path = os.path.join(data_dir, f'plot_actual_vs_predicted_{direction}.png')
        plt.tight_layout()
        plt.savefig(plot_path, dpi=300)
        plt.close()
        print(f" -> Đã lưu biểu đồ: {plot_path}")
        
    # Lưu JSON
    json_path = os.path.join(data_dir, 'training_metrics.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n[*] Đã lưu số liệu vào: {json_path}")
        
    print("\n" + "="*90)
    print(" BẢNG KẾT QUẢ THỰC NGHIỆM")
    print("="*90)
    print("| Hướng Di Chuyển (Direction) | Quy Mô Tập Test (Dòng) | Chỉ Số MAE (xe) | Chỉ Số RMSE (xe) | Chỉ Số MAPE (%) | Trạng Thế Đạt Yêu Cầu |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    
    direction_names = {
        'straight': 'Nhánh Đi Thẳng (`straight`)',
        'left': 'Nhánh Rẽ Trái (`left`)',
        'right': 'Nhánh Rẽ Phải (`right`)'
    }
    
    thresholds = {
        'straight': 90,
        'left': 88,
        'right': 90
    }
    
    for d in ['straight', 'left', 'right']:
        if d in results:
            r = results[d]
            acc = 100 - r['mape']
            req = thresholds[d]
            status = "Đạt" if acc >= req else "Không Đạt"
            print(f"| **{direction_names[d]}** | {r['test_size']:,} | {r['mae']:.2f} | {r['rmse']:.2f} | {r['mape']:.2f}% | $\\ge {req}\\%$ ({status}) |")
            
if __name__ == '__main__':
    main()
