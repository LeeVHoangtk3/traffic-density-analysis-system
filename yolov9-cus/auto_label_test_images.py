"""
Auto Label Test Images with Dual Models & Generate Comparison Report

Script này chạy inference với 2 YOLO models trên tập test:
  1. best_final.pt (model custom trained)
  2. yolov9c.pt (pre-trained YOLOv9 model)

Sau đó:
  - Tạo label files riêng cho mỗi model
  - Tạo visualization với predictions từ cả 2 models
  - Tạo báo cáo so sánh chi tiết (CSV format)

Output: 
  - Label files cho model 1: dataset/test/labels_best_final/
  - Label files cho model 2: dataset/test/labels_yolov9c/
  - Ảnh visualization với predictions vào dataset/test/visualized/
  - File báo cáo CSV: dataset/test/model_comparison_report.csv

Usage:
    python auto_label_test_images.py
    python auto_label_test_images.py --confidence 0.5
    python auto_label_test_images.py --dry-run
"""

import os
import sys
import argparse
import csv
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from collections import defaultdict

# Import PyTorch (models are PyTorch format)
import torch
import torchvision

# ===== Configuration =====
YOLOV9_ROOT = os.path.dirname(__file__)
DATASET_IMAGES_DIR = os.path.join(YOLOV9_ROOT, "dataset", "test", "images")
DATASET_LABELS_DIR = os.path.join(YOLOV9_ROOT, "dataset", "test", "labels")
PRO_MODELS_DIR = os.path.join(YOLOV9_ROOT, "..", "detection", "pro_models")

# Model paths
MODEL_BEST = os.path.join(PRO_MODELS_DIR, "yolov9_ultimate_final.pt") # <-- Update this to your best model filename
MODEL_PRETRAINED = os.path.join(PRO_MODELS_DIR, "yolov9c.pt")

# Output directories
OUTPUT_LABELS_BEST = os.path.join(YOLOV9_ROOT, "dataset", "test", "labels_ultimate_final") # <-- Update this to match your best model name
OUTPUT_LABELS_PRETRAINED = os.path.join(YOLOV9_ROOT, "dataset", "test", "labels_yolov9c")
OUTPUT_VIZ_DIR = os.path.join(YOLOV9_ROOT, "dataset", "test", "visualized")

# ===== Class index mapping =====
# Custom training classes (best_final.pt)
CLASS_NAMES = {
    0: "bus",
    1: "car",
    2: "motorcycle",
    3: "truck"
}

# COCO pre-trained classes (yolov9c.pt)
COCO_VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# Mapping từ COCO class ID sang custom class ID
COCO_TO_CUSTOM_MAPPING = {
    2: 1,  # car: COCO 2 -> custom 1
    3: 2,  # motorcycle: COCO 3 -> custom 2
    5: 0,  # bus: COCO 5 -> custom 0
    7: 3   # truck: COCO 7 -> custom 3
}

# Reverse mapping: name -> index (custom)
CLASS_NAME_TO_ID = {v: k for k, v in CLASS_NAMES.items()}

# ===== Confidence threshold =====
CONFIDENCE_THRESHOLD = 0.45  # Default confidence threshold


def create_directories():
    """Tạo các thư mục output nếu chưa tồn tại"""
    os.makedirs(OUTPUT_VIZ_DIR, exist_ok=True)
    os.makedirs(OUTPUT_LABELS_BEST, exist_ok=True)
    os.makedirs(OUTPUT_LABELS_PRETRAINED, exist_ok=True)
    print(f"✓ Created directory: {OUTPUT_VIZ_DIR}")
    print(f"✓ Created directory: {OUTPUT_LABELS_BEST}")
    print(f"✓ Created directory: {OUTPUT_LABELS_PRETRAINED}")


def load_models(confidence_threshold=CONFIDENCE_THRESHOLD):
    """
    Load YOLO models using torch.load (PyTorch format)
    
    Returns: Dictionary with loaded models
    """
    import torch
    
    # Add detection module path to sys.path so 'models' module can be found
    # (matching detector.py pattern)
    detection_path = os.path.join(os.path.dirname(__file__), "..", "detection")
    ultralytics_path = os.path.join(detection_path, "ultralytics_yolov9")
    if ultralytics_path not in sys.path:
        sys.path.insert(0, ultralytics_path)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    models = {}
    
    # Load best_final model
    if os.path.exists(MODEL_BEST):
        print(f"Loading model: {MODEL_BEST}")
        try:
            ckpt = torch.load(MODEL_BEST, map_location=device, weights_only=False)
            model = ckpt['model'].float().eval()
            models['best_final'] = {
                'model': model,
                'path': MODEL_BEST,
                'name': 'best_final.pt',
                'device': device,
                'conf_threshold': confidence_threshold
            }
            print(f"✓ Loaded: best_final.pt (device: {device})")
        except Exception as e:
            print(f"✗ Failed to load best_final.pt: {str(e)}")
    else:
        print(f"⚠ Model not found: {MODEL_BEST}")
    
    # Load pre-trained model
    if os.path.exists(MODEL_PRETRAINED):
        print(f"Loading model: {MODEL_PRETRAINED}")
        try:
            ckpt = torch.load(MODEL_PRETRAINED, map_location=device, weights_only=False)
            model = ckpt['model'].float().eval()
            models['yolov9c'] = {
                'model': model,
                'path': MODEL_PRETRAINED,
                'name': 'yolov9c.pt',
                'device': device,
                'conf_threshold': confidence_threshold
            }
            print(f"✓ Loaded: yolov9c.pt (device: {device})")
        except Exception as e:
            print(f"✗ Failed to load yolov9c.pt: {str(e)}")
    else:
        print(f"⚠ Model not found: {MODEL_PRETRAINED}")
    
    if not models:
        raise FileNotFoundError("No models found. Please check model paths.")
    
    return models


def normalize_bbox(x1, y1, x2, y2, img_width, img_height):
    """
    Convert bbox từ pixel coordinates sang YOLO normalized format
    
    Input: [x1, y1, x2, y2] (pixel coordinates)
    Output: [center_x, center_y, width, height] (0-1 normalized)
    """
    center_x = ((x1 + x2) / 2.0) / img_width
    center_y = ((y1 + y2) / 2.0) / img_height
    width = (x2 - x1) / img_width
    height = (y2 - y1) / img_height
    
    # Clamp to [0, 1]
    center_x = max(0, min(1, center_x))
    center_y = max(0, min(1, center_y))
    width = max(0, min(1, width))
    height = max(0, min(1, height))
    
    return center_x, center_y, width, height


def save_predictions_as_labels(predictions, image_width, image_height, output_path, model_type='best_final'):
    """
    Save predictions from YOLO model in YOLO label format
    
    predictions: YOLO result object with boxes
    output_path: Path to save label file
    model_type: 'best_final' or 'yolov9c' - determines class mapping
    """
    with open(output_path, 'w') as f:
        for box in predictions.boxes:
            # Get bounding box coordinates (xyxy format)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            # Get class id and confidence
            class_id = int(box.cls[0].cpu().numpy())
            confidence = float(box.conf[0].cpu().numpy())
            
            # Map COCO class ID to custom class ID if using yolov9c model
            if model_type == 'yolov9c':
                # Only save if this COCO class is in our vehicle classes
                if class_id not in COCO_TO_CUSTOM_MAPPING:
                    continue  # Skip non-vehicle COCO classes
                # Map COCO ID to custom ID
                class_id = COCO_TO_CUSTOM_MAPPING[class_id]
            
            # Convert to YOLO format
            center_x, center_y, width, height = normalize_bbox(x1, y1, x2, y2, image_width, image_height)
            
            # Write to file with confidence
            f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f} {confidence:.4f}\n")


def run_inference_and_save_labels(models, images_dir, confidence_threshold):
    """
    Run inference on all test images using both models and save labels
    
    Returns: Dictionary with inference results
    """
    import torch
    import torchvision
    
    results = {
        'best_final': {},
        'yolov9c': {},
        'image_count': 0,
        'processed_count': 0,
        'failed_count': 0
    }
    
    # Get all image files
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = []
    
    for file in sorted(os.listdir(images_dir)):
        if file.lower().endswith(supported_formats):
            image_files.append(os.path.join(images_dir, file))
    
    results['image_count'] = len(image_files)
    
    print(f"\nRunning inference on {len(image_files)} images...")
    
    # Helper function to run inference
    def run_model_inference(model, img_tensor, img_size=640):
        """Run single inference on image tensor"""
        with torch.no_grad():
            output = model(img_tensor)
            
            # Extract predictions
            pred = output
            while isinstance(pred, (list, tuple)):
                if len(pred) > 0:
                    pred = pred[0]
                else:
                    return None
        
        if not isinstance(pred, torch.Tensor):
            if isinstance(output, (list, tuple)) and len(output) > 1:
                pred = output[1]
                while isinstance(pred, (list, tuple)):
                    pred = pred[0]
            if not isinstance(pred, torch.Tensor):
                return None
        
        # Reshape if needed
        if pred.ndim == 3 and pred.shape[0] == 1:
            pred = pred.squeeze(0)
        if pred.shape[0] < pred.shape[1]:
            pred = pred.transpose(0, 1)
        
        return pred
    
    # Run inference on each image
    for image_path in tqdm(image_files, desc="Inference Progress"):
        try:
            image_name = os.path.basename(image_path)
            label_name = os.path.splitext(image_name)[0] + '.txt'
            
            # Read image
            frame = cv2.imread(image_path)
            if frame is None:
                print(f"⚠ Cannot read image: {image_path}")
                results['failed_count'] += 1
                continue
            
            h, w = frame.shape[:2]
            img_size = 640
            
            # Preprocess image
            img = cv2.resize(frame, (img_size, img_size))
            img = img.transpose((2, 0, 1))[::-1]
            img = np.ascontiguousarray(img)
            
            # Run inference with best_final model
            if 'best_final' in models:
                try:
                    model_info = models['best_final']
                    model = model_info['model']
                    device = model_info['device']
                    
                    img_tensor = torch.from_numpy(img).to(device).float() / 255.0
                    if img_tensor.ndimension() == 3:
                        img_tensor = img_tensor.unsqueeze(0)
                    
                    pred = run_model_inference(model, img_tensor, img_size)
                    
                    if pred is not None:
                        # Process detections
                        detections = []
                        
                        # Get scores and classes
                        scores, class_ids = torch.max(pred[:, 4:], dim=1)
                        mask = scores > confidence_threshold
                        
                        det = pred[mask]
                        final_scores = scores[mask]
                        final_cls = class_ids[mask]
                        
                        if len(det) > 0:
                            boxes = det[:, :4]
                            new_boxes = boxes.clone()
                            new_boxes[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1
                            new_boxes[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1
                            new_boxes[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2
                            new_boxes[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2
                            
                            keep = torchvision.ops.nms(new_boxes, final_scores, iou_threshold=0.45)
                            
                            for idx in keep:
                                cls_id = int(final_cls[idx])
                                detections.append({
                                    'bbox': new_boxes[idx].cpu().numpy(),
                                    'confidence': float(final_scores[idx]),
                                    'class_id': cls_id
                                })
                        
                        # Save labels
                        label_path_best = os.path.join(OUTPUT_LABELS_BEST, label_name)
                        with open(label_path_best, 'w') as f:
                            for det in detections:
                                x1, y1, x2, y2 = det['bbox']
                                confidence = det['confidence']
                                class_id = det['class_id']
                                
                                center_x, center_y, width, height = normalize_bbox(x1, y1, x2, y2, w, h)
                                f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f} {confidence:.4f}\n")
                        
                        results['best_final'][image_name] = len(detections)
                    else:
                        results['best_final'][image_name] = 0
                        # Create empty label file
                        open(os.path.join(OUTPUT_LABELS_BEST, label_name), 'w').close()
                    
                except Exception as e:
                    print(f"⚠ best_final inference error for {image_name}: {str(e)}")
                    results['best_final'][image_name] = -1
            
            # Run inference with yolov9c model
            if 'yolov9c' in models:
                try:
                    model_info = models['yolov9c']
                    model = model_info['model']
                    device = model_info['device']
                    
                    img_tensor = torch.from_numpy(img).to(device).float() / 255.0
                    if img_tensor.ndimension() == 3:
                        img_tensor = img_tensor.unsqueeze(0)
                    
                    pred = run_model_inference(model, img_tensor, img_size)
                    
                    if pred is not None:
                        # Process detections
                        detections = []
                        
                        # Get scores and classes
                        scores, class_ids = torch.max(pred[:, 4:], dim=1)
                        mask = scores > confidence_threshold
                        
                        det = pred[mask]
                        final_scores = scores[mask]
                        final_cls = class_ids[mask]
                        
                        if len(det) > 0:
                            boxes = det[:, :4]
                            new_boxes = boxes.clone()
                            new_boxes[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1
                            new_boxes[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1
                            new_boxes[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2
                            new_boxes[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2
                            
                            keep = torchvision.ops.nms(new_boxes, final_scores, iou_threshold=0.45)
                            
                            detections_to_save = []
                            for idx in keep:
                                cls_id = int(final_cls[idx])
                                
                                # Map COCO class ID to custom class ID
                                if cls_id not in COCO_TO_CUSTOM_MAPPING:
                                    continue  # Skip non-vehicle classes
                                mapped_cls_id = COCO_TO_CUSTOM_MAPPING[cls_id]
                                
                                detections_to_save.append({
                                    'bbox': new_boxes[idx].cpu().numpy(),
                                    'confidence': float(final_scores[idx]),
                                    'class_id': mapped_cls_id
                                })
                        
                        # Save labels
                        label_path_pretrained = os.path.join(OUTPUT_LABELS_PRETRAINED, label_name)
                        with open(label_path_pretrained, 'w') as f:
                            for det in detections_to_save:
                                x1, y1, x2, y2 = det['bbox']
                                confidence = det['confidence']
                                class_id = det['class_id']
                                
                                center_x, center_y, width, height = normalize_bbox(x1, y1, x2, y2, w, h)
                                f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f} {confidence:.4f}\n")
                        
                        results['yolov9c'][image_name] = len(detections_to_save)
                    else:
                        results['yolov9c'][image_name] = 0
                        # Create empty label file
                        open(os.path.join(OUTPUT_LABELS_PRETRAINED, label_name), 'w').close()
                    
                except Exception as e:
                    print(f"⚠ yolov9c inference error for {image_name}: {str(e)}")
                    results['yolov9c'][image_name] = -1
            
            results['processed_count'] += 1
            
        except Exception as e:
            print(f"✗ Error processing {image_path}: {str(e)}")
            results['failed_count'] += 1
    
    return results


def generate_evaluation_report():
    """
    Generate comprehensive comparison report and save to CSV
    
    Compares predictions from both models:
    - Detection counts
    - Class distribution differences
    - Model agreement/disagreement analysis
    """
    
    print("\nGenerating model comparison report...")
    
    # ===== Collect statistics from both models =====
    best_stats = defaultdict(int)
    pretrained_stats = defaultdict(int)
    comparison_data = []
    
    # Get all label files from both models
    # Use yolov9c as reference if best_final folder is empty (fallback for when best_final.pt fails to load)
    best_files = sorted([f for f in os.listdir(OUTPUT_LABELS_BEST) if f.endswith('.txt')]) if os.path.exists(OUTPUT_LABELS_BEST) else []
    pretrained_files = sorted([f for f in os.listdir(OUTPUT_LABELS_PRETRAINED) if f.endswith('.txt')]) if os.path.exists(OUTPUT_LABELS_PRETRAINED) else []
    
    # Use whichever has files as reference
    if not best_files and pretrained_files:
        image_files = pretrained_files
        using_pretrained_as_ref = True
    else:
        image_files = best_files
        using_pretrained_as_ref = False
    
    for label_file in image_files:
        if not label_file.endswith('.txt'):
            continue
        
        image_name = label_file.replace('.txt', '')
        best_detections = 0
        pretrained_detections = 0
        best_classes = defaultdict(int)
        pretrained_classes = defaultdict(int)
        
        # Read best_final labels
        best_label_path = os.path.join(OUTPUT_LABELS_BEST, label_file)
        if os.path.exists(best_label_path):
            with open(best_label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        try:
                            class_id = int(parts[0])
                            class_name = CLASS_NAMES.get(class_id, "unknown")
                            best_detections += 1
                            best_classes[class_name] += 1
                            best_stats[class_name] += 1
                        except (ValueError, IndexError):
                            pass
        
        # Read yolov9c labels
        pretrained_label_path = os.path.join(OUTPUT_LABELS_PRETRAINED, label_file)
        if os.path.exists(pretrained_label_path):
            with open(pretrained_label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        try:
                            class_id = int(parts[0])
                            class_name = CLASS_NAMES.get(class_id, "unknown")
                            pretrained_detections += 1
                            pretrained_classes[class_name] += 1
                            pretrained_stats[class_name] += 1
                        except (ValueError, IndexError):
                            pass
        
        # Calculate differences
        detection_diff = best_detections - pretrained_detections
        agreement = "✓ AGREE" if best_detections == pretrained_detections else "✗ DIFFER"
        
        comparison_data.append({
            'image_name': image_name,
            'best_final_detections': best_detections,
            'yolov9c_detections': pretrained_detections,
            'detection_diff': detection_diff,
            'agreement': agreement,
            'best_classes': dict(best_classes),
            'yolov9c_classes': dict(pretrained_classes)
        })
    
    # ===== Generate CSV report =====
    report_filename = os.path.join(os.path.dirname(DATASET_IMAGES_DIR), "model_comparison_report.csv")
    
    with open(report_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # ===== Header section =====
        writer.writerow(["MODEL COMPARISON REPORT"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["Model 1", "best_final.pt"])
        writer.writerow(["Model 2", "yolov9c.pt (pre-trained)"])
        writer.writerow([])
        
        # ===== Summary statistics =====
        total_best = sum(comp['best_final_detections'] for comp in comparison_data)
        total_pretrained = sum(comp['yolov9c_detections'] for comp in comparison_data)
        total_images = len(comparison_data)
        
        writer.writerow(["SUMMARY STATISTICS"])
        writer.writerow(["Metric", "best_final.pt", "yolov9c.pt", "Difference"])
        writer.writerow(["Total Detections", total_best, total_pretrained, total_best - total_pretrained])
        writer.writerow(["Total Images Processed", total_images, total_images, 0])
        writer.writerow(["Average Detections per Image", 
                        f"{total_best/total_images:.2f}" if total_images > 0 else 0,
                        f"{total_pretrained/total_images:.2f}" if total_images > 0 else 0,
                        f"{(total_best-total_pretrained)/total_images:.2f}" if total_images > 0 else 0])
        writer.writerow([])
        
        # ===== Class distribution comparison =====
        writer.writerow(["CLASS DISTRIBUTION COMPARISON"])
        writer.writerow(["Class Name", "best_final Count", "best_final %", "yolov9c Count", "yolov9c %", "Difference"])
        
        all_classes = set(best_stats.keys()) | set(pretrained_stats.keys())
        for class_name in sorted(all_classes):
            best_count = best_stats.get(class_name, 0)
            pretrained_count = pretrained_stats.get(class_name, 0)
            best_pct = (best_count / total_best * 100) if total_best > 0 else 0
            pretrained_pct = (pretrained_count / total_pretrained * 100) if total_pretrained > 0 else 0
            diff = best_count - pretrained_count
            
            writer.writerow([
                class_name,
                best_count,
                f"{best_pct:.2f}%",
                pretrained_count,
                f"{pretrained_pct:.2f}%",
                diff
            ])
        
        writer.writerow([])
        
        # ===== Agreement analysis =====
        agreements = sum(1 for comp in comparison_data if comp['agreement'] == "✓ AGREE")
        disagreements = total_images - agreements
        agreement_rate = (agreements / total_images * 100) if total_images > 0 else 0
        
        writer.writerow(["AGREEMENT ANALYSIS"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Images with Matching Detection Count", agreements])
        writer.writerow(["Images with Different Detection Count", disagreements])
        writer.writerow(["Agreement Rate (%)", f"{agreement_rate:.2f}%"])
        writer.writerow([])
        
        # ===== Per-image comparison =====
        writer.writerow(["DETAILED IMAGE COMPARISON"])
        writer.writerow(["Image Name", "best_final Detections", "yolov9c Detections", "Difference", "Agreement", 
                        "best_final Classes", "yolov9c Classes"])
        
        for comp in comparison_data:
            best_classes_str = ", ".join([f"{k}:{v}" for k, v in sorted(comp['best_classes'].items())])
            yolo_classes_str = ", ".join([f"{k}:{v}" for k, v in sorted(comp['yolov9c_classes'].items())])
            
            writer.writerow([
                comp['image_name'],
                comp['best_final_detections'],
                comp['yolov9c_detections'],
                comp['detection_diff'],
                comp['agreement'],
                best_classes_str if best_classes_str else "No detections",
                yolo_classes_str if yolo_classes_str else "No detections"
            ])
        
        writer.writerow([])
        
        # ===== Model performance insights =====
        writer.writerow(["MODEL PERFORMANCE INSIGHTS"])
        writer.writerow(["Insight", "Value"])
        
        if total_best > total_pretrained:
            writer.writerow(["More Detections", f"best_final.pt detected {total_best - total_pretrained} more objects"])
        elif total_pretrained > total_best:
            writer.writerow(["More Detections", f"yolov9c.pt detected {total_pretrained - total_best} more objects"])
        else:
            writer.writerow(["Detection Parity", "Both models detected the same total number of objects"])
        
        # Find most detected class in each model
        if best_stats:
            best_most_common = max(best_stats.items(), key=lambda x: x[1])
            writer.writerow(["best_final Most Common Class", f"{best_most_common[0]} ({best_most_common[1]} detections)"])
        
        if pretrained_stats:
            pretrained_most_common = max(pretrained_stats.items(), key=lambda x: x[1])
            writer.writerow(["yolov9c Most Common Class", f"{pretrained_most_common[0]} ({pretrained_most_common[1]} detections)"])
    
    print(f"✓ Comparison report saved to: {report_filename}")
    
    return report_filename, {
        'total_best': total_best,
        'total_pretrained': total_pretrained,
        'total_images': total_images,
        'best_stats': dict(best_stats),
        'pretrained_stats': dict(pretrained_stats),
        'agreements': agreements,
        'disagreements': disagreements,
        'agreement_rate': agreement_rate
    }



def main():
    parser = argparse.ArgumentParser(
        description="Auto-label test images with dual YOLOv9 models and generate comparison report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auto_label_test_images.py
  python auto_label_test_images.py --confidence 0.5
  python auto_label_test_images.py --dry-run
        """
    )
    
    parser.add_argument('--confidence', type=float, default=CONFIDENCE_THRESHOLD,
                       help=f'Confidence threshold for detections (default: {CONFIDENCE_THRESHOLD})')
    parser.add_argument('--dry-run', action='store_true',
                       help='Only show what would be processed, don\'t save')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("AUTO-LABEL TEST IMAGES WITH DUAL MODELS & GENERATE COMPARISON REPORT")
    print("="*70)
    print(f"Model 1: {MODEL_BEST} (Custom training)")
    print(f"Model 2: {MODEL_PRETRAINED} (Pre-trained YOLOv9)")
    print(f"Confidence Threshold: {args.confidence}")
    print(f"Images Directory: {DATASET_IMAGES_DIR}")
    print(f"Output Labels Directory 1: {OUTPUT_LABELS_BEST}")
    print(f"Output Labels Directory 2: {OUTPUT_LABELS_PRETRAINED}")
    print(f"Dry run: {args.dry_run}")
    print("\nNOTE: yolov9c.pt class IDs will be mapped to custom class IDs:")
    print("  COCO 2 (car) → Custom 1 (car)")
    print("  COCO 3 (motorcycle) → Custom 2 (motorcycle)")
    print("  COCO 5 (bus) → Custom 0 (bus)")
    print("  COCO 7 (truck) → Custom 3 (truck)")
    print("="*70 + "\n")
    
    try:
        # Check directories exist
        if not os.path.exists(DATASET_IMAGES_DIR):
            print(f"✗ Images directory not found: {DATASET_IMAGES_DIR}")
            return
        
        print("Step 1: Checking model files...")
        if not os.path.exists(MODEL_BEST):
            print(f"⚠ Warning: best_final.pt not found at {MODEL_BEST}")
        if not os.path.exists(MODEL_PRETRAINED):
            print(f"⚠ Warning: yolov9c.pt not found at {MODEL_PRETRAINED}")
        
        print("\nStep 2: Loading YOLO models...")
        if not args.dry_run:
            models = load_models(args.confidence)
            print(f"✓ Successfully loaded {len(models)} model(s)\n")
        else:
            print("(Skipping model loading in dry-run mode)\n")
        
        print("Step 3: Creating output directories...")
        if not args.dry_run:
            create_directories()
            print()
        
        # Get image files
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        image_files = []
        for file in sorted(os.listdir(DATASET_IMAGES_DIR)):
            if file.lower().endswith(supported_formats):
                image_files.append(os.path.join(DATASET_IMAGES_DIR, file))
        
        print(f"Step 4: Found {len(image_files)} test images")
        print()
        
        if not args.dry_run:
            print("Step 5: Running inference on all images...")
            print("-" * 70)
            inference_results = run_inference_and_save_labels(models, DATASET_IMAGES_DIR, args.confidence)
            
            print("\n" + "="*70)
            print("INFERENCE RESULTS")
            print("="*70)
            print(f"Total Images: {inference_results['image_count']}")
            print(f"Successfully Processed: {inference_results['processed_count']}")
            print(f"Failed: {inference_results['failed_count']}")
            
            if 'best_final' in models:
                detections_best = sum(1 for v in inference_results['best_final'].values() if v > 0)
                print(f"Images with best_final detections: {detections_best}")
            
            if 'yolov9c' in models:
                detections_yolo = sum(1 for v in inference_results['yolov9c'].values() if v > 0)
                print(f"Images with yolov9c detections: {detections_yolo}")
            
            print("="*70 + "\n")
            
            print("Step 6: Generating model comparison report...")
            print("-" * 70)
            report_path, metrics = generate_evaluation_report()
            
            print("\n" + "="*70)
            print("MODEL COMPARISON SUMMARY")
            print("="*70)
            print(f"Total Images Processed: {metrics['total_images']}")
            print(f"\nbest_final.pt Statistics:")
            print(f"  Total Detections: {metrics['total_best']}")
            if metrics['total_images'] > 0:
                print(f"  Average per Image: {metrics['total_best']/metrics['total_images']:.2f}")
            print(f"  Class Distribution: {dict(metrics['best_stats'])}")
            
            print(f"\nyolov9c.pt Statistics:")
            print(f"  Total Detections: {metrics['total_pretrained']}")
            if metrics['total_images'] > 0:
                print(f"  Average per Image: {metrics['total_pretrained']/metrics['total_images']:.2f}")
            print(f"  Class Distribution: {dict(metrics['pretrained_stats'])}")
            
            print(f"\nAgreement Analysis:")
            print(f"  Matching Detections: {metrics['agreements']} images")
            print(f"  Differing Detections: {metrics['disagreements']} images")
            print(f"  Agreement Rate: {metrics['agreement_rate']:.2f}%")
            print("="*70)
            
            print(f"\n✓ Label files saved to:")
            print(f"  - {OUTPUT_LABELS_BEST}")
            print(f"  - {OUTPUT_LABELS_PRETRAINED}")
            print(f"✓ Comparison report saved to: {report_path}")
            
            print("\nNext steps:")
            print("1. Review the comparison report: model_comparison_report.csv")
            print("2. Analyze the detection differences between models")
            print("3. Check label files in the output directories")
            print("4. Use labels for training or validation")
        else:
            print("(Dry-run mode: no actual processing performed)")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
