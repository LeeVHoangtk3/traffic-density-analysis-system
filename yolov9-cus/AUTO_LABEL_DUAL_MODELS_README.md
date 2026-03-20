# Auto-Label Test Images with Dual Models - Documentation

## Overview

Tệp `auto_label_test_images.py` đã được cập nhật để chạy **inference trên 2 YOLO models** khác nhau và **tạo báo cáo so sánh chi tiết**.

## Các Model Được Sử Dụng

1. **best_final.pt** - Model YOLO custom trained từ dữ liệu của bạn
   - Đường dẫn: `../detection/pro_models/best_final.pt`
   
2. **yolov9c.pt** - Pre-trained YOLOv9 model
   - Đường dẫn: `../detection/pro_models/yolov9c.pt`

## Output

Script sẽ tạo ra:

### 1. Label Files
- **`dataset/test/labels_best_final/`** - Nhãn từ model best_final.pt
  - Format YOLO: `class_id center_x center_y width height confidence`
  - Mỗi file ảnh sẽ có một file `.txt` tương ứng

- **`dataset/test/labels_yolov9c/`** - Nhãn từ model yolov9c.pt
  - Format YOLO: `class_id center_x center_y width height confidence`
  - Cùng định dạng với labels từ best_final

### 2. Báo Cáo So Sánh
- **`dataset/test/model_comparison_report.csv`** - Báo cáo chi tiết so sánh 2 models

   Nội dung báo cáo bao gồm:
   - **SUMMARY STATISTICS**: So sánh tổng quan
     - Tổng số detections từ mỗi model
     - Tổng số images xử lý
     - Trung bình detections/image
   
   - **CLASS DISTRIBUTION COMPARISON**: So sánh phân phối các lớp
     - Số lượng detections cho mỗi lớp (bus, car, motorcycle, truck)
     - Phần trăm từng lớp
     - Chênh lệch giữa 2 models
   
   - **AGREEMENT ANALYSIS**: Phân tích sự đồng ý giữa 2 models
     - Số images có cùng số detections
     - Số images có khác số detections
     - Tỷ lệ đồng ý (Agreement Rate)
   
   - **DETAILED IMAGE COMPARISON**: So sánh chi tiết từng ảnh
     - Số detections của mỗi model trên từng ảnh
     - Chênh lệch số detections
     - Trạng thái đồng ý (✓ AGREE / ✗ DIFFER)
     - Phân phối lớp chi tiết trên mỗi ảnh
   
   - **MODEL PERFORMANCE INSIGHTS**: Nhận xét hiệu suất
     - Model nào detect nhiều hơn
     - Lớp được detect phổ biến nhất của mỗi model

## Cách Sử Dụng

### Prerequisites
Cài đặt ultralytics package:
```bash
pip install ultralytics opencv-python torch torchvision
```

### Chạy Script

#### 1. **Chế độ bình thường** (mặc định với confidence = 0.45):
```bash
python auto_label_test_images.py
```

#### 2. **Với confidence threshold tùy chỉnh**:
```bash
# Độ tin cậy 0.5
python auto_label_test_images.py --confidence 0.5

# Độ tin cậy 0.3 (recovery nhiều detections)
python auto_label_test_images.py --confidence 0.3

# Độ tin cậy 0.7 (chặt chẽ hơn)
python auto_label_test_images.py --confidence 0.7
```

#### 3. **Dry-run mode** (chỉ kiểm tra, không xử lý):
```bash
python auto_label_test_images.py --dry-run
```

## Output Chi Tiết

### Console Output

Script sẽ hiển thị:
```
======================================================================
AUTO-LABEL TEST IMAGES WITH DUAL MODELS & GENERATE COMPARISON REPORT
======================================================================
...
Step 1: Checking model files...
Step 2: Loading YOLO models...
Step 3: Creating output directories...
Step 4: Found X test images
...
Step 5: Running inference on all images...
...
Step 6: Generating model comparison report...

======================================================================
MODEL COMPARISON SUMMARY
======================================================================
Total Images Processed: X

best_final.pt Statistics:
  Total Detections: X
  Average per Image: X.XX
  Class Distribution: {...}

yolov9c.pt Statistics:
  Total Detections: Y
  Average per Image: Y.YY
  Class Distribution: {...}

Agreement Analysis:
  Matching Detections: Z images
  Differing Detections: W images
  Agreement Rate: ZZ.ZZ%
======================================================================
```

### File Structure Sau Khi Chạy

```
yolov9-cus/
├── dataset/test/
│   ├── images/
│   │   └── *.jpg (ảnh test gốc)
│   ├── labels/
│   │   └── *.txt (nhãn gốc)
│   ├── labels_best_final/           ← NEW: Từ model best_final.pt
│   │   └── *.txt (nhãn predictions)
│   ├── labels_yolov9c/              ← NEW: Từ model yolov9c.pt
│   │   └── *.txt (nhãn predictions)
│   └── model_comparison_report.csv  ← NEW: Báo cáo so sánh
```

## Label Files Format

Các label files sử dụng YOLO format (mở rộng với confidence):
```
class_id center_x center_y width height confidence
class_id center_x center_y width height confidence
...
```

**Ví dụ:**
```
0 0.512345 0.567890 0.234567 0.345678 0.9876
1 0.712345 0.467890 0.134567 0.245678 0.8765
```

Trong đó:
- `0` = bus, `1` = car, `2` = motorcycle, `3` = truck
- `center_x, center_y` = tọa độ normalized [0, 1]
- `width, height` = chiều rộng, cao normalized [0, 1]
- `confidence` = độ tin cậy [0, 1]

## Phân Tích Kết Quả

### Ví Dụ Báo Cáo

```csv
SUMMARY STATISTICS
Metric,best_final.pt,yolov9c.pt,Difference
Total Detections,1250,1180,70
Total Images Processed,100,100,0
Average Detections per Image,12.50,11.80,0.70

CLASS DISTRIBUTION COMPARISON
Class Name,best_final Count,best_final %,yolov9c Count,yolov9c %,Difference
bus,150,12.00%,145,12.29%,5
car,650,52.00%,620,52.54%,30
motorcycle,250,20.00%,240,20.34%,-10
truck,200,16.00%,175,14.83%,25

AGREEMENT ANALYSIS
Metric,Value
Images with Matching Detection Count,75
Images with Different Detection Count,25
Agreement Rate (%),75.00%
```

### Nhận Xét

- **Nếu Agreement Rate cao (70-80%+)**: 2 models có khả năng detect tương đương
- **Nếu Agreement Rate thấp (<50%)**: 2 models detect khác biệt đáng kể
- **Chênh lệch trong từng lớp**: Cho biết model nào tốt hơn cho lớp cụ thể

## Model Classes

Script có thể detect 4 lớp:
- `0` - **Bus** (Xe buýt) - Blue
- `1` - **Car** (Ô tô) - Green  
- `2` - **Motorcycle** (Xe máy) - Orange
- `3` - **Truck** (Xe tải) - Magenta

### COCO Class Mapping (Quan Trọng!)

**yolov9c.pt** (pre-trained trên COCO) sử dụng các class ID khác:
- COCO ID 2 = Car
- COCO ID 3 = Motorcycle
- COCO ID 5 = Bus
- COCO ID 7 = Truck

**best_final.pt** (custom trained) sử dụng:
- Custom ID 0 = Bus
- Custom ID 1 = Car
- Custom ID 2 = Motorcycle
- Custom ID 3 = Truck

**Script tự động mapping:**
```
COCO 2 (car)       → Custom 1 (car)
COCO 3 (motorcycle) → Custom 2 (motorcycle)
COCO 5 (bus)       → Custom 0 (bus)
COCO 7 (truck)     → Custom 3 (truck)
```

✅ Cả 2 models sẽ lưu labels với **cùng custom class IDs** (0, 1, 2, 3)
- Cho phép so sánh công bằng trong báo cáo
- Loại bỏ COCO classes khác (không phải vehicle)
- Output consistency giữa 2 models

## Confidence Threshold

- **Cao (0.7-0.9)**: Chặt chẽ, ít false positives nhưng có thể miss detections
- **Trung bình (0.4-0.6)**: Cân bằng, được khuyến cáo cho hầu hết cases
- **Thấp (0.1-0.3)**: Lnhạy, bắt được nhiều detections nhưng có nhiều false positives

## Troubleshooting

### Lỗi: "No modules found"
```bash
pip install -r requirements.txt
```

### Lỗi: "Model files not found"
- Kiểm tra đường dẫn model: `../detection/pro_models/best_final.pt`
- Kiểm tra đường dẫn model: `../detection/pro_models/yolov9c.pt`

### Script chạy chậm
- Điều chế GPU: Đảm bảo PyTorch được cấu hình dùng GPU
- Dùng confidence cao hơn để giảm xử lý

## Next Steps

1. **Review báo cáo**: Mở `model_comparison_report.csv` và phân tích kết quả
2. **So sánh models**: Quyết định model nào tốt hơn cho use case của bạn
3. **Sử dụng labels**: Dùng label files cho training, testing, hoặc validation
4. **Tinh chỉnh**: Điều chỉnh confidence threshold nếu cần

## Các Hàm Chính

- `load_models()` - Tải 2 YOLO models
- `normalize_bbox()` - Chuẩn hóa bounding box về format YOLO
- `save_predictions_as_labels()` - Lưu predictions thành label files
- `run_inference_and_save_labels()` - Chạy inference trên tất cả images
- `generate_evaluation_report()` - Tạo báo cáo so sánh chi tiết

## Performance Metrics Được Tính

- Total detections (tổng)
- Average detections per image (trung bình)
- Class distribution (phân phối lớp)
- Agreement rate (tỷ lệ đồng ý)
- Per-image comparison (so sánh từng ảnh)
