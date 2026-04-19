# Class Mapping Fix - COCO vs Custom Classes

## Vấn Đề Đã Phát Hiện

Hai models sử dụng **class ID khác nhau**:

### best_final.pt (Custom Trained)
Custom class indices:
```
0: bus
1: car
2: motorcycle
3: truck
```

### yolov9c.pt (Pre-trained on COCO)
COCO class indices:
```
2: car
3: motorcycle
5: bus
7: truck
```

## Tại Sao Này Là Vấn Đề?

**Trước khi fix:**
- yolov9c detect car → class_id = 2
- best_final detect car → class_id = 1
- Script sẽ ghi nhầm thành:
  - Car (ID 2) ≠ Car (ID 1) → MISMATCH trong báo cáo
  - Báo cáo sẽ sai lệch, không thể so sánh chính xác

## Giải Pháp Được Implement

### 1. Thêm COCO Class Mapping

```python
COCO_VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

COCO_TO_CUSTOM_MAPPING = {
    2: 1,  # COCO car (2) → custom (1)
    3: 2,  # COCO motorcycle (3) → custom (2)
    5: 0,  # COCO bus (5) → custom (0)
    7: 3   # COCO truck (7) → custom (3)
}
```

### 2. Cập Nhật save_predictions_as_labels()

Thêm parameter `model_type` để xác định có cần mapping:

```python
def save_predictions_as_labels(predictions, image_width, image_height, 
                               output_path, model_type='best_final'):
    """
    model_type='best_final' → Không mapping (đã là custom IDs)
    model_type='yolov9c' → Apply COCO→custom mapping
    """
    for box in predictions.boxes:
        class_id = int(box.cls[0].cpu().numpy())
        
        # Map COCO class ID to custom ID if using yolov9c
        if model_type == 'yolov9c':
            if class_id not in COCO_TO_CUSTOM_MAPPING:
                continue  # Skip non-vehicle COCO classes
            class_id = COCO_TO_CUSTOM_MAPPING[class_id]
        
        # Save with mapped class_id
```

### 3. Cập Nhật run_inference_and_save_labels()

Gọi với model_type parameter:

```python
# best_final - không cần mapping
save_predictions_as_labels(best_results[0], img_width, img_height, 
                          label_path_best, model_type='best_final')

# yolov9c - áp dụng mapping COCO→custom
save_predictions_as_labels(pretrained_results[0], img_width, img_height,
                          label_path_pretrained, model_type='yolov9c')
```

## Kết Quả Sau Fix

### Label Files Output

**Cả 2 models giờ lưu cùng custom class IDs:**

best_final.pt:
```
0 0.512 0.567 0.234 0.345 0.987  # bus
1 0.712 0.467 0.134 0.245 0.876  # car
```

yolov9c.pt (sau mapping):
```
0 0.512 0.512 0.250 0.300 0.950  # bus (từ COCO 5)
1 0.750 0.450 0.150 0.250 0.920  # car (từ COCO 2)
```

### Báo Cáo So Sánh

**Hiệu ứng tích cực:**
✅ Comparison report giờ so sánh đúng class names
✅ Class distribution comparison chính xác
✅ Agreement rate đúng (không bị skew bởi class ID khác)
✅ Có thể so sánh model performance công bằng

## Console Output

Script giờ hiển thị:
```
NOTE: yolov9c.pt class IDs will be mapped to custom class IDs:
  COCO 2 (car) → Custom 1 (car)
  COCO 3 (motorcycle) → Custom 2 (motorcycle)
  COCO 5 (bus) → Custom 0 (bus)
  COCO 7 (truck) → Custom 3 (truck)
```

## Kiểm Chứng

Để verify mapping hoạt động đúng:

1. Chạy script:
```bash
python auto_label_test_images.py --confidence 0.5
```

2. Kiểm tra label files:
```bash
# Mở một label file từ cả 2 models
cat dataset/test/labels_best_final/test_001.txt
cat dataset/test/labels_yolov9c/test_001.txt
```

3. Kiểm tra class IDs:
- Cả 2 files phải chỉ chứa class IDs: 0, 1, 2, 3
- Không có IDs: 5, 7 từ COCO

4. So sánh báo cáo:
```bash
# Mở CSV report
model_comparison_report.csv
```

- CLASS DISTRIBUTION COMPARISON phải có syntax:
  - bus, car, motorcycle, truck (không phải COCO names)
  - Số detections phải reasonable (cả 2 models cùng format)

## Edge Cases Được Xử Lý

1. **COCO non-vehicle classes**
   - Loại bỏ (skip) vì không trong COCO_TO_CUSTOM_MAPPING
   - Ví dụ: person, dog, cat → skip

2. **Unknown class IDs**
   - Xử lý gracefully với try-catch
   - Log warning nếu encounter

3. **Empty predictions**
   - Handle correctly (không error)
   - Số detections = 0

## Files Được Cập Nhật

1. ✅ `auto_label_test_images.py`
   - Thêm COCO_VEHICLE_CLASSES
   - Thêm COCO_TO_CUSTOM_MAPPING
   - Cập nhật save_predictions_as_labels()
   - Cập nhật run_inference_and_save_labels()
   - Thêm console notes về mapping

2. ✅ `AUTO_LABEL_DUAL_MODELS_README.md`
   - Thêm COCO Class Mapping section
   - Giải thích mapping process
   - Clarify output format consistency

## Tóm Tắt

| Aspect | Trước | Sau |
|--------|-------|-----|
| Class Mapping | ❌ Không | ✅ Có |
| Label Format | Khác nhau | 🔄 Nhất quán |
| Báo Cáo | Sai lệch | ✅ Chính xác |
| So Sánh Models | Không công bằng | ✅ Công bằng |
| Output IDs | 0-7 (mix) | 0-3 (custom) |

Giờ script đã hoàn toàn sẵn sàng để tạo báo cáo so sánh chính xác giữa 2 models! 🎯
