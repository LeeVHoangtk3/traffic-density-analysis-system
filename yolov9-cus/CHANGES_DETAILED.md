# Thay Đổi Chi Tiết - auto_label_test_images.py

## Tóm Tắt Thay Đổi

File `auto_label_test_images.py` đã được **hoàn toàn viết lại** để hỗ trợ:
1. ✅ Chạy inference với 2 models YOLO (best_final.pt và yolov9c.pt)
2. ✅ Tạo separate label files cho mỗi model
3. ✅ Tạo báo cáo so sánh chi tiết trong CSV format

## Các Hàm Mới Được Thêm

### 1. `load_models(confidence_threshold)`
**Mục đích**: Tải 2 YOLO models

**Input**:
- `confidence_threshold`: Ngưỡng confidence (mặc định 0.45)

**Output**: Dictionary chứa cả 2 models đã tải

**Ví dụ**:
```python
models = load_models(confidence=0.5)
# models = {
#     'best_final': {'model': <YOLO>, 'path': '...', 'name': 'best_final.pt'},
#     'yolov9c': {'model': <YOLO>, 'path': '...', 'name': 'yolov9c.pt'}
# }
```

### 2. `normalize_bbox(x1, y1, x2, y2, img_width, img_height)`
**Mục đích**: Chuyển đổi bounding box từ pixel coordinates sang YOLO format

**Input**: 
- x1, y1, x2, y2: pixel coordinates
- img_width, img_height: kích thước ảnh

**Output**: [center_x, center_y, width, height] (normalized 0-1)

### 3. `save_predictions_as_labels(predictions, image_width, image_height, output_path)`
**Mục đích**: Lưu predictions từ YOLO model thành label files

**Input**:
- predictions: YOLO result object với boxes
- image_width, image_height: kích thước ảnh
- output_path: đường dẫn lưu file

**Output**: File .txt với định dạng YOLO

**Ví dụ output file**:
```
0 0.512345 0.567890 0.234567 0.345678 0.9876
1 0.712345 0.467890 0.134567 0.245678 0.8765
```

### 4. `run_inference_and_save_labels(models, images_dir, confidence_threshold)`
**Mục đích**: Chạy inference trên tất cả images và lưu labels

**Input**:
- models: Dictionary models từ `load_models()`
- images_dir: thư mục chứa images
- confidence_threshold: ngưỡng confidence

**Output**: 
```python
results = {
    'best_final': {'image1.jpg': 5, 'image2.jpg': 3, ...},
    'yolov9c': {'image1.jpg': 6, 'image2.jpg': 2, ...},
    'image_count': 100,
    'processed_count': 99,
    'failed_count': 1
}
```

**Side Effects**:
- Tạo files trong `labels_best_final/`
- Tạo files trong `labels_yolov9c/`

### 5. `generate_evaluation_report()`
**Mục đích**: Tạo báo cáo so sánh 2 models

**Input**: Không có (đọc từ OUTPUT_LABELS_BEST và OUTPUT_LABELS_PRETRAINED)

**Output**: 
```python
return report_filename, {
    'total_best': 1250,
    'total_pretrained': 1180,
    'total_images': 100,
    'best_stats': {'bus': 150, 'car': 650, 'motorcycle': 250, 'truck': 200},
    'pretrained_stats': {'bus': 145, 'car': 620, ...},
    'agreements': 75,
    'disagreements': 25,
    'agreement_rate': 75.0
}
```

**Side Effects**:
- Tạo file CSV: `model_comparison_report.csv`

## Các Hàm Cũ Đã Xóa

❌ `get_image_files()` - Không cần nữa (inference sẽ handle)
❌ `denormalize_bbox()` - Không cần nữa (normalize thay thế)
❌ `read_yolo_labels()` - Không cần nữa (generate từ inference)
❌ `draw_detections()` - Không cần nữa (visualization optional)
❌ `process_image()` - Không cần nữa (replaced by run_inference)
❌ `generate_statistics()` - Không cần nữa (generate_evaluation_report thay thế)

## Configuration Changes

### Thêm Model Paths
```python
PRO_MODELS_DIR = os.path.join(YOLOV9_ROOT, "..", "detection", "pro_models")
MODEL_BEST = os.path.join(PRO_MODELS_DIR, "best_final.pt")
MODEL_PRETRAINED = os.path.join(PRO_MODELS_DIR, "yolov9c.pt")
```

### Thêm Output Directories
```python
OUTPUT_LABELS_BEST = os.path.join(YOLOV9_ROOT, "dataset", "test", "labels_best_final")
OUTPUT_LABELS_PRETRAINED = os.path.join(YOLOV9_ROOT, "dataset", "test", "labels_yolov9c")
```

### Thêm Confidence Threshold
```python
CONFIDENCE_THRESHOLD = 0.45  # Default
```

## Main Function Changes

### Thêm Arguments
```python
parser.add_argument('--confidence', type=float, default=CONFIDENCE_THRESHOLD,
                   help=f'Confidence threshold for detections')
```

### Thêm Processing Steps
1. ✅ Check model files
2. ✅ Load models
3. ✅ Create output directories
4. ✅ Count test images
5. ✅ Run inference (NEW)
6. ✅ Generate comparison report (NEW)

## Import Changes

### Thêm Import
```python
try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    # Auto-install logic
```

### Packages Cần
- `ultralytics` (YOLO models)
- `opencv-python` (image processing)
- `torch` & `torchvision` (deep learning)

## Workflow So Sánh

```
Input Images
    ↓
┌─────────────────────────┬──────────────────────┐
│                         │                      │
v                         v                      v
Model 1              Model 2              
(best_final.pt)      (yolov9c.pt)         
    ↓                    ↓                      
Predictions 1    Predictions 2           
    ↓                    ↓                      
labels_best_final/   labels_yolov9c/     
    ↓                    ↓                      
└─────────────────────────┴──────────────────────┘
            ↓
    Compare Results
            ↓
model_comparison_report.csv
```

## Report CSV Sections

### 1. Header
```
MODEL COMPARISON REPORT
Generated,2026-03-20 10:30:45
Model 1,best_final.pt
Model 2,yolov9c.pt (pre-trained)
```

### 2. Summary Statistics
```
SUMMARY STATISTICS
Metric,best_final.pt,yolov9c.pt,Difference
Total Detections,1250,1180,70
Total Images Processed,100,100,0
Average Detections per Image,12.50,11.80,0.70
```

### 3. Class Distribution
```
CLASS DISTRIBUTION COMPARISON
Class Name,best_final Count,best_final %,yolov9c Count,yolov9c %,Difference
bus,150,12.00%,145,12.29%,5
car,650,52.00%,620,52.54%,30
motorcycle,250,20.00%,240,20.34%,-10
truck,200,16.00%,175,14.83%,25
```

### 4. Agreement Analysis
```
AGREEMENT ANALYSIS
Metric,Value
Images with Matching Detection Count,75
Images with Different Detection Count,25
Agreement Rate (%),75.00%
```

### 5. Detailed Comparison
```
DETAILED IMAGE COMPARISON
Image Name,best_final Detections,yolov9c Detections,Difference,Agreement,best_final Classes,yolov9c Classes
test_001.jpg,15,14,1,✗ DIFFER,bus:2 car:8 truck:5,bus:2 car:7 truck:5
test_002.jpg,10,10,0,✓ AGREE,bus:1 car:7 motorcycle:2,bus:1 car:7 motorcycle:2
```

## Performance Improvement

| Aspect | Cũ | Mới |
|--------|----|----|
| Chức năng | Visualization static labels | **Inference 2 models** |
| Output | 1 visualization | **2 label sets + comparison** |
| Report | Basic stats | **Detailed comparison analysis** |
| Models | N/A | **best_final.pt + yolov9c.pt** |
| Comparison | N/A | **Agreement rate, class distribution diff** |

## Error Handling

### Model Loading
- ✅ Checks if model files exist
- ✅ Handles missing ultraytics package
- ✅ Auto-installs if missing

### Inference
- ✅ Catches image read errors
- ✅ Handles inference failures per image
- ✅ Logs warnings for problematic images

### File I/O
- ✅ Creates directories if not exist
- ✅ Handles file writing errors
- ✅ Validates output paths

## Next Steps

1. **Run script**: `python auto_label_test_images.py`
2. **Review report**: `model_comparison_report.csv`
3. **Analyze results**: So sánh performance 2 models
4. **Use labels**: Dùng cho training/validation
5. **Fine-tune**: Điều chỉnh confidence threshold nếu cần
