"""
Visualize Test Images with Existing Labels & Generate Evaluation Report

Script này tạo visualization cho các ảnh trong dataset/test/images
sử dụng nhãn đã có sẵn trong dataset/test/labels/
Đồng thời xuất ra báo cáo đánh giá chi tiết (CSV format)

Output: 
  - Ảnh visualization với bounding box vào dataset/test/visualized/
  - File báo cáo CSV: dataset/test/test_evaluation_report.csv

Usage:
    python auto_label_test_images.py
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

# ===== Configuration =====
DATASET_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "dataset", "test", "images")
DATASET_LABELS_DIR = os.path.join(os.path.dirname(__file__), "dataset", "test", "labels")
OUTPUT_VIZ_DIR = os.path.join(os.path.dirname(__file__), "dataset", "test", "visualized")

# ===== Class index mapping =====
CLASS_NAMES = {
    0: "bus",
    1: "car",
    2: "motorcycle",
    3: "truck"
}

# Reverse mapping: name -> index
CLASS_NAME_TO_ID = {v: k for k, v in CLASS_NAMES.items()}


def create_directories():
    """Tạo thư mục visualized nếu chưa tồn tại"""
    os.makedirs(OUTPUT_VIZ_DIR, exist_ok=True)
    print(f"✓ Created directory: {OUTPUT_VIZ_DIR}")


def get_image_files(images_dir):
    """Get all image files có nhãn tương ứng"""
    if not os.path.exists(images_dir):
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    
    if not os.path.exists(DATASET_LABELS_DIR):
        raise FileNotFoundError(f"Labels directory not found: {DATASET_LABELS_DIR}")
    
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = []
    
    for file in os.listdir(images_dir):
        if file.lower().endswith(supported_formats):
            # Check if corresponding label exists
            label_name = os.path.splitext(file)[0] + '.txt'
            label_path = os.path.join(DATASET_LABELS_DIR, label_name)
            
            if os.path.exists(label_path):
                image_files.append(os.path.join(images_dir, file))
    
    if not image_files:
        raise ValueError(f"No images with matching labels found in: {images_dir}")
    
    print(f"Found {len(image_files)} images with corresponding labels")
    return sorted(image_files)


def denormalize_bbox(norm_bbox, img_width, img_height):
    """
    Convert bbox từ YOLO normalized format sang pixel coordinates
    
    Input: [center_x, center_y, width, height] (0-1 normalized)
    Output: [x1, y1, x2, y2] (pixel coordinates)
    """
    center_x, center_y, width, height = norm_bbox
    
    # Denormalize
    center_x_px = center_x * img_width
    center_y_px = center_y * img_height
    width_px = width * img_width
    height_px = height * img_height
    
    # Calculate corners
    x1 = int(center_x_px - width_px / 2.0)
    y1 = int(center_y_px - height_px / 2.0)
    x2 = int(center_x_px + width_px / 2.0)
    y2 = int(center_y_px + height_px / 2.0)
    
    return [x1, y1, x2, y2]


def read_yolo_labels(label_path):
    """
    Read YOLO format labels
    
    Format: class_id center_x center_y width height (normalized 0-1)
    Returns: List of [class_id, center_x, center_y, width, height]
    """
    labels = []
    
    if not os.path.exists(label_path):
        return labels
    
    with open(label_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            try:
                class_id = int(parts[0])
                center_x = float(parts[1])
                center_y = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                labels.append([class_id, center_x, center_y, width, height])
            except (ValueError, IndexError) as e:
                print(f"⚠ Skipping invalid label line: {line.strip()}")
    
    return labels


def draw_detections(frame, labels, save_path=None):
    """
    Draw bounding boxes from YOLO labels on frame
    
    labels: List of [class_id, center_x, center_y, width, height] (normalized)
    """
    img_copy = frame.copy()
    img_height, img_width = frame.shape[:2]
    
    colors = {
        0: (255, 0, 0),          # bus - Blue
        1: (0, 255, 0),          # car - Green
        2: (0, 165, 255),        # motorcycle - Orange
        3: (255, 0, 255)         # truck - Magenta
    }
    
    class_names = {
        0: "bus",
        1: "car",
        2: "motorcycle",
        3: "truck"
    }
    
    for label in labels:
        class_id = int(label[0])
        center_x = float(label[1])
        center_y = float(label[2])
        width = float(label[3])
        height = float(label[4])
        
        # Denormalize
        bbox = denormalize_bbox([center_x, center_y, width, height], img_width, img_height)
        x1, y1, x2, y2 = bbox
        
        # Clamp to image bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(img_width - 1, x2)
        y2 = min(img_height - 1, y2)
        
        class_name = class_names.get(class_id, "unknown")
        color = colors.get(class_id, (0, 0, 255))
        
        # Draw rectangle
        cv2.rectangle(img_copy, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label_text = class_name
        label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img_copy, (x1, y1 - label_size[1] - 4), 
                     (x1 + label_size[0], y1), color, -1)
        cv2.putText(img_copy, label_text, (x1, y1 - 2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Save if path provided
    if save_path:
        cv2.imwrite(save_path, img_copy)
    
    return img_copy


def process_image(image_path):
    """
    Process single image: read labels, create visualization
    
    Returns: (num_labels, success)
    """
    try:
        # Read image
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"⚠ Cannot read image: {image_path}")
            return 0, False
        
        # Get corresponding label file
        image_name = os.path.basename(image_path)
        label_name = os.path.splitext(image_name)[0] + '.txt'
        label_path = os.path.join(DATASET_LABELS_DIR, label_name)
        
        # Read labels
        labels = read_yolo_labels(label_path)
        
        # Create visualization
        viz_name = os.path.splitext(image_name)[0] + '_viz.jpg'
        viz_path = os.path.join(OUTPUT_VIZ_DIR, viz_name)
        draw_detections(frame, labels, viz_path)
        
        return len(labels), True
        
    except Exception as e:
        print(f"✗ Error processing {image_path}: {str(e)}")
        return 0, False


def generate_statistics():
    """Generate and print statistics after visualization creation"""
    total_images = len(os.listdir(OUTPUT_VIZ_DIR))
    total_labels = 0
    labels_by_class = {v: 0 for v in CLASS_NAMES.values()}
    
    print("\n" + "="*60)
    print("VISUALIZATION STATISTICS")
    print("="*60)
    
    for label_file in os.listdir(DATASET_LABELS_DIR):
        if label_file.endswith('.txt'):
            label_path = os.path.join(DATASET_LABELS_DIR, label_file)
            
            with open(label_path, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                parts = line.strip().split()
                if parts:
                    class_id = int(parts[0])
                    class_name = CLASS_NAMES.get(class_id, "unknown")
                    labels_by_class[class_name] += 1
                    total_labels += 1
    
    print(f"Total visualized images: {total_images}")
    print(f"Total labels (objects): {total_labels}")
    print(f"Average labels per image: {total_labels/total_images:.2f}" if total_images > 0 else "N/A")
    print("\nLabels by class:")
    for class_name, count in labels_by_class.items():
        percentage = (count / total_labels * 100) if total_labels > 0 else 0
        print(f"  {class_name:12s}: {count:4d} ({percentage:5.1f}%)")
    print("="*60 + "\n")


def generate_evaluation_report():
    """
    Generate comprehensive evaluation report and save to CSV
    
    Metrics calculated:
    - Total images
    - Total objects detected
    - Average objects per image
    - Objects per class
    - Class distribution
    - Min/Max/Avg objects in images
    """
    
    print("Generating evaluation report...")
    
    # ===== Collect statistics =====
    image_files = []
    labels_by_class = defaultdict(int)
    objects_per_image = []
    dataset_info = []
    
    # Get all image files with labels
    for img_file in os.listdir(DATASET_IMAGES_DIR):
        if img_file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
            label_file = os.path.splitext(img_file)[0] + '.txt'
            label_path = os.path.join(DATASET_LABELS_DIR, label_file)
            
            if os.path.exists(label_path):
                img_path = os.path.join(DATASET_IMAGES_DIR, img_file)
                image_files.append(img_path)
                
                # Read labels
                with open(label_path, 'r') as f:
                    lines = f.readlines()
                
                num_objects = 0
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        try:
                            class_id = int(parts[0])
                            class_name = CLASS_NAMES.get(class_id, "unknown")
                            labels_by_class[class_name] += 1
                            num_objects += 1
                        except (ValueError, IndexError):
                            pass
                
                objects_per_image.append(num_objects)
                
                # Image info
                img = cv2.imread(img_path)
                img_height, img_width = img.shape[:2] if img is not None else (0, 0)
                
                dataset_info.append({
                    'image_name': img_file,
                    'width': img_width,
                    'height': img_height,
                    'num_objects': num_objects,
                    'label_file': label_file
                })
    
    # ===== Calculate aggregate statistics =====
    total_images = len(dataset_info)
    total_objects = sum(objects_per_image)
    avg_objects = total_objects / total_images if total_images > 0 else 0
    min_objects = min(objects_per_image) if objects_per_image else 0
    max_objects = max(objects_per_image) if objects_per_image else 0
    
    # ===== Create CSV report =====
    report_filename = os.path.join(os.path.dirname(DATASET_IMAGES_DIR), "test_evaluation_report.csv")
    
    with open(report_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # ===== Header section =====
        writer.writerow(["DATASET EVALUATION REPORT"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])
        
        # ===== Summary section =====
        writer.writerow(["SUMMARY STATISTICS"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Images", total_images])
        writer.writerow(["Total Objects", total_objects])
        writer.writerow(["Average Objects per Image", f"{avg_objects:.2f}"])
        writer.writerow(["Min Objects per Image", min_objects])
        writer.writerow(["Max Objects per Image", max_objects])
        writer.writerow(["Image Directory", DATASET_IMAGES_DIR])
        writer.writerow(["Labels Directory", DATASET_LABELS_DIR])
        writer.writerow([])
        
        # ===== Class distribution =====
        writer.writerow(["CLASS DISTRIBUTION"])
        writer.writerow(["Class Name", "Count", "Percentage"])
        for class_name in CLASS_NAMES.values():
            count = labels_by_class[class_name]
            percentage = (count / total_objects * 100) if total_objects > 0 else 0
            writer.writerow([class_name, count, f"{percentage:.2f}%"])
        writer.writerow([])
        
        # ===== Per-image details =====
        writer.writerow(["DETAILED IMAGE INFORMATION"])
        writer.writerow(["Image Name", "Width (px)", "Height (px)", "Label File", "Number of Objects"])
        for info in sorted(dataset_info, key=lambda x: x['image_name']):
            writer.writerow([
                info['image_name'],
                info['width'],
                info['height'],
                info['label_file'],
                info['num_objects']
            ])
        writer.writerow([])
        
        # ===== Statistics by object count =====
        writer.writerow(["IMAGES BY OBJECT COUNT"])
        writer.writerow(["Object Count", "Number of Images", "Percentage"])
        count_freq = defaultdict(int)
        for count in objects_per_image:
            count_freq[count] += 1
        
        for obj_count in sorted(count_freq.keys()):
            num_imgs = count_freq[obj_count]
            percentage = (num_imgs / total_images * 100) if total_images > 0 else 0
            writer.writerow([obj_count, num_imgs, f"{percentage:.2f}%"])
    
    print(f"✓ Evaluation report saved to: {report_filename}")
    return report_filename, {
        'total_images': total_images,
        'total_objects': total_objects,
        'avg_objects': avg_objects,
        'min_objects': min_objects,
        'max_objects': max_objects,
        'class_distribution': dict(labels_by_class)
    }



def main():
    parser = argparse.ArgumentParser(
        description="Visualize test images with existing labels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auto_label_test_images.py
  python auto_label_test_images.py --dry-run
        """
    )
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Only show what would be processed, don\'t save')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("VISUALIZE TEST IMAGES WITH EXISTING LABELS")
    print("="*60)
    print(f"Images dir: {DATASET_IMAGES_DIR}")
    print(f"Labels dir: {DATASET_LABELS_DIR}")
    print(f"Output dir: {OUTPUT_VIZ_DIR}")
    print(f"Dry run: {args.dry_run}")
    print("="*60 + "\n")
    
    try:
        # Check directories exist
        if not os.path.exists(DATASET_IMAGES_DIR):
            print(f"✗ Images directory not found: {DATASET_IMAGES_DIR}")
            return
        
        if not os.path.exists(DATASET_LABELS_DIR):
            print(f"✗ Labels directory not found: {DATASET_LABELS_DIR}")
            return
        
        # Create output directories
        if not args.dry_run:
            create_directories()
            print("")
        
        # Get image files with matching labels
        image_files = get_image_files(DATASET_IMAGES_DIR)
        print("")
        
        # Process images
        print("Creating visualizations...")
        processed = 0
        failed = 0
        total_labels = 0
        
        for image_path in tqdm(image_files, desc="Progress"):
            if args.dry_run:
                print(f"Would process: {os.path.basename(image_path)}")
            else:
                num_labels, success = process_image(image_path)
                
                if success:
                    processed += 1
                    total_labels += num_labels
                else:
                    failed += 1
        
        print(f"\n")
        if not args.dry_run:
            print(f"✓ Successfully processed: {processed} images")
            print(f"✗ Failed: {failed} images")
            print(f"✓ Total labels visualized: {total_labels}")
            
            # Generate statistics
            generate_statistics()
            
            # Generate evaluation report (CSV)
            report_path, metrics = generate_evaluation_report()
            
            print("\n" + "="*60)
            print("EVALUATION METRICS")
            print("="*60)
            print(f"Total Images: {metrics['total_images']}")
            print(f"Total Objects: {metrics['total_objects']}")
            print(f"Average Objects per Image: {metrics['avg_objects']:.2f}")
            print(f"Min Objects per Image: {metrics['min_objects']}")
            print(f"Max Objects per Image: {metrics['max_objects']}")
            print("\nClass Distribution:")
            for class_name, count in metrics['class_distribution'].items():
                percentage = (count / metrics['total_objects'] * 100) if metrics['total_objects'] > 0 else 0
                print(f"  {class_name:12s}: {count:4d} ({percentage:5.1f}%)")
            print("="*60)
            
            print(f"\n✓ Visualizations saved to: {OUTPUT_VIZ_DIR}")
            print(f"✓ Evaluation report saved to: {report_path}")
            
            print("\nNext steps:")
            print("1. Review visualizations in dataset/test/visualized/")
            print("2. Check evaluation report (test_evaluation_report.csv)")
            print("3. Verify labels are correct")
            print("4. Use labeled dataset for training: python yolov9/train.py ...")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
