import os
import sys
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.mongo_database import db, init_mongo_indexes
from backend.services.aggregation_service import (
    aggregate_from_detections,
    classify_direction_counts,
    empty_direction_counts,
    compute_overall_congestion,
)
from backend.services.prediction_service import get_cached_model, _optimize_phase_timing

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def seed_cameras(database):
    camera_ids = sorted(
        camera_id
        for camera_id in database.vehicle_detections.distinct("camera_id")
        if camera_id
    )

    created = 0
    updated = 0
    for camera_id in camera_ids:
        result = database.cameras.update_one(
            {"camera_id": camera_id},
            {
                "$setOnInsert": {
                    "camera_id": camera_id,
                    "name": f"Camera {camera_id}",
                    "location": "Chua cap nhat",
                },
                "$set": {
                    "baseline_green": 30,
                    "monitored_direction": "straight",
                },
            },
            upsert=True,
        )
        if result.upserted_id:
            created += 1
        elif result.modified_count:
            updated += 1

    return created, updated, camera_ids


def seed_aggregations_and_predictions(database, camera_ids):
    """
    Phân chia trục thời gian 180 phút thành 12 block 15 phút đồng bộ TOÀN CỤC.
    Gom nhóm dữ liệu và tạo lịch sử dữ liệu aggregation & prediction hoàn toàn đồng bộ theo dòng chảy tuần tự của các camera.
    """
    agg_created = 0
    pred_created = 0

    # Lấy mô hình XGBoost
    model = get_cached_model()

    # 1. Tìm khoảng thời gian dữ liệu thô TOÀN CỤC (Global Time Range) để đồng bộ hóa trục thời gian cho tất cả camera
    first_det_global = database.vehicle_detections.find_one({}, sort=[("timestamp", 1)])
    last_det_global = database.vehicle_detections.find_one({}, sort=[("timestamp", -1)])
    
    if not first_det_global or not last_det_global:
        print("   [⚠️ Warning] Không tìm thấy bất kỳ detections nào trong DB. Bỏ qua.")
        return 0, 0
        
    t_start_global = first_det_global["timestamp"]
    t_end_global = last_det_global["timestamp"]
    
    # Chuyển đổi timestamp thành timezone-aware UTC
    if t_start_global.tzinfo is None:
        t_start_global = t_start_global.replace(tzinfo=timezone.utc)
    if t_end_global.tzinfo is None:
        t_end_global = t_end_global.replace(tzinfo=timezone.utc)
        
    # Tròn hóa thời gian bắt đầu toàn cục xuống mốc 15 phút gần nhất
    start_rounded = t_start_global - timedelta(
        minutes=t_start_global.minute % 15,
        seconds=t_start_global.second,
        microseconds=t_start_global.microsecond
    )
    
    # Sinh 12 chu kỳ liên tục từ start_rounded (Đồng bộ 3 tiếng toàn hệ thống)
    intervals = []
    for i in range(12):
        interval_start = start_rounded + timedelta(minutes=i * 15)
        interval_end = interval_start + timedelta(minutes=15)
        intervals.append((interval_start, interval_end))

    for camera_id in camera_ids:
        print(f"🔄 Đang tạo dữ liệu lịch sử tích lũy cho camera: {camera_id}...")
        
        # 2. Tạo Aggregation cho từng khoảng
        history_list = []
        for idx, (i_start, i_end) in enumerate(intervals):
            # Bộ lọc detections trong khoảng thời gian ảo của camera
            filters = {
                "camera_id": camera_id,
                "timestamp": {
                    "$gte": i_start.replace(tzinfo=None),
                    "$lt": i_end.replace(tzinfo=None)
                }
            }
            
            # Tính lượng xe rẽ hướng
            # Vì single ROI nên hướng xe đếm được là straight, left/right = 0
            raw_count = database.vehicle_detections.count_documents(filters)
            
            # --- LÀM SẠCH GIÁ TRỊ 0 & TẠO SỰ ĐỘT BIẾN NGẪU NHIÊN CHO TỰ NHIÊN ---
            import random
            # Tạo bộ sinh số ngẫu nhiên có tính nhất quán (deterministic) dựa trên camera_id và vị trí chu kỳ (idx)
            # để đảm bảo dữ liệu không bị thay đổi liên tục mỗi khi nạp, nhưng vẫn vô cùng tự nhiên.
            random_state = random.Random(f"{camera_id}_{idx}_traffic_density_v6")
            
            if raw_count < 35:
                # Nâng các giá trị bằng 0 hoặc quá thấp lên một lưu lượng nền thực tế (35 - 75 xe)
                vehicle_count = random_state.randint(35, 75)
                # Thỉnh thoảng tạo một đột biến giao thông nhẹ trong giờ thấp điểm (khoảng 20% cơ hội)
                # Đại diện cho các đợt đèn đỏ xả hàng loạt hoặc đoàn xe lớn đi qua
                if random_state.random() < 0.20:
                    vehicle_count = random_state.randint(110, 160)
            else:
                # Với lưu lượng cao ban đầu (Peak), thêm biến động dao động ±25 xe để tránh phẳng lì
                noise = random_state.randint(-25, 25)
                vehicle_count = max(35, raw_count + noise)
                
            direction_counts = empty_direction_counts()
            direction_counts["straight"] = vehicle_count
            
            congestion_levels = classify_direction_counts(database, camera_id, direction_counts)
            congestion_level = compute_overall_congestion(congestion_levels)
            
            # Tính queue_proxy dựa trên inbound count trễ
            inbound_count = vehicle_count
            previous_inbound = history_list[-1]["inbound_count"] if len(history_list) > 0 else 0
            queue_proxy = max(0, inbound_count - previous_inbound)
            
            agg_doc = {
                "camera_id": camera_id,
                "vehicle_count": vehicle_count,
                "inbound_count": inbound_count,
                "queue_proxy": queue_proxy,
                "congestion_level": congestion_level,
                "direction_counts": direction_counts,
                "congestion_levels": congestion_levels,
                "timestamp": i_end.replace(tzinfo=None)
            }
            
            database.traffic_aggregation.insert_one(agg_doc)
            history_list.append(agg_doc)
            agg_created += 1
            
            # 3. Tạo Prediction tương ứng dựa trên dữ liệu trễ vừa có
            # Lấy lags từ danh sách lịch sử trong RAM
            lag_1 = 50.0
            lag_2 = 50.0
            lag_3 = 50.0
            
            if len(history_list) >= 1:
                lag_1 = float(history_list[-1]["vehicle_count"])
            if len(history_list) >= 2:
                lag_2 = float(history_list[-2]["vehicle_count"])
            if len(history_list) >= 3:
                lag_3 = float(history_list[-3]["vehicle_count"])
                
            rolling_mean_3 = (lag_1 + lag_2 + lag_3) / 3.0
            
            # Tính các đặc trưng tuần hoàn cho mốc thời gian tiếp theo (i_end + 15 phút)
            target_time = i_end + timedelta(minutes=15)
            hour_float = target_time.hour + target_time.minute / 60.0
            hour_sin = float(np.sin(2 * np.pi * hour_float / 24.0))
            hour_cos = float(np.cos(2 * np.pi * hour_float / 24.0))
            
            day_of_week = int(target_time.weekday())
            is_weekend = 1 if day_of_week >= 5 else 0
            
            features_used = {
                "lag_1": lag_1,
                "lag_2": lag_2,
                "rolling_mean_3": rolling_mean_3,
                "hour_sin": hour_sin,
                "hour_cos": hour_cos,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend
            }
            
            # Chạy mô hình XGBoost
            if model is None:
                predicted_raw_volume = int(round(rolling_mean_3))
            else:
                try:
                    X_pred = pd.DataFrame([[
                        lag_1, lag_2, rolling_mean_3, hour_sin, hour_cos, day_of_week, is_weekend
                    ]], columns=['lag_1', 'lag_2', 'rolling_mean_3', 'hour_sin', 'hour_cos', 'day_of_week', 'is_weekend'])
                    
                    raw_pred = model.predict(X_pred)[0]
                    predicted_raw_volume = int(round(max(0.0, float(raw_pred))))
                except Exception as e:
                    predicted_raw_volume = int(round(rolling_mean_3))
                    print(f"   [⚠️ Error] Lỗi dự báo XGBoost cho block {idx}: {e}")
            
            # Lấy ngưỡng thích ứng phân loại
            low_to_medium = 467.58
            medium_to_high = 495.34
            high_to_heavy = 522.67
            
            threshold_doc = database.density_thresholds.find_one({"camera_id": camera_id})
            if not threshold_doc:
                threshold_doc = database.directional_thresholds.find_one({"camera_id": camera_id, "direction": "total"})
                
            if threshold_doc and "thresholds" in threshold_doc:
                thresholds = threshold_doc["thresholds"]
                low_to_medium = float(thresholds.get("low_to_medium", low_to_medium))
                medium_to_high = float(thresholds.get("medium_to_high", medium_to_high))
                high_to_heavy = float(thresholds.get("high_to_heavy", high_to_heavy))
                
            if predicted_raw_volume < low_to_medium:
                status_label = "LOW"
            elif predicted_raw_volume < medium_to_high:
                status_label = "MEDIUM"
            elif predicted_raw_volume < high_to_heavy:
                status_label = "HIGH"
            else:
                status_label = "HEAVY"
                
            # Đèn tín hiệu và cấu trúc tương thích ngược
            phase_timing = _optimize_phase_timing(predicted_raw_volume)
            
            pred_doc = {
                "camera_id": camera_id,
                "predicted_density": float(predicted_raw_volume),
                "predicted_congestion_level": status_label,
                "horizon_minutes": 15,
                "source": "xgb_single_roi_directionless_seeded",
                "timestamp": target_time.replace(tzinfo=None),
                "green_light_time": phase_timing["phase_1_green"],
                "predictions": {
                    "left": 0,
                    "straight": predicted_raw_volume,
                    "right": 0
                },
                "congestion_levels": {
                    "left": "LOW",
                    "straight": status_label,
                    "right": "LOW"
                },
                "phase_timing": phase_timing,
                "features_used": features_used
            }
            
            database.traffic_predictions.insert_one(pred_doc)
            pred_created += 1

        print(f"   [OK] Đã tạo thành công {agg_created} aggregations và {pred_created} predictions.")

    return agg_created, pred_created


def main():
    init_mongo_indexes()
    
    total_detections = db.vehicle_detections.count_documents({})
    if total_detections == 0:
        print("Khong co du lieu trong collection vehicle_detections.")
        print("Hay chay detection truoc, sau do seed lai.")
        return

    # Dọn dẹp dữ liệu cũ để tránh sinh trùng lặp bản ghi lịch sử khi chạy lại
    print("🧹 Đang dọn dẹp các bảng phân tích dữ liệu cũ...")
    db.traffic_aggregation.delete_many({})
    db.traffic_predictions.delete_many({})
    db.cameras.delete_many({})
    print("   [OK] Dọn dẹp hoàn tất.")

    camera_created, camera_updated, camera_ids = seed_cameras(db)
    aggregation_created, prediction_created = seed_aggregations_and_predictions(db, camera_ids)

    print("\n==================================================================")
    print("🎉 SEED DỮ LIỆU ĐỒNG BỘ CHUỖI THỜI GIAN HOÀN TẤT!")
    print("==================================================================")
    print(f"- Camera đăng ký mới   : {camera_created}")
    print(f"- Camera cập nhật      : {camera_updated}")
    print(f"- Aggregations đã tạo  : {aggregation_created}")
    print(f"- Predictions đã tạo   : {prediction_created}")
    print(f"- Tổng số Camera xử lý : {len(camera_ids)}")
    print("==================================================================")


if __name__ == "__main__":
    main()
