import sys
import os
import torch
import cv2
import numpy as np
import torchvision 

# 1. Thiết lập đường dẫn tìm code YOLOv9 core
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
yolo_core_path = os.path.join(project_root, "ultralytics_yolov9")

if yolo_core_path not in sys.path:
    sys.path.insert(0, yolo_core_path)

# ĐÂY LÀ NƠI BẠN CHỌN MODEL YOLOv9 CỦA MÌNH

# COCO vehicle classes
# VEHICLE_CLASSES = {
#     2: "car",
#     3: "motorcycle",
#     5: "bus",
#     7: "truck"
# }

# YOLOv9 custom classes (nếu dùng model custom)
VEHICLE_CLASSES = {
    0: "bus",
    1: "car",
    2: "motorcycle",
    3: "truck"
}

class Detector:
    def __init__(self, model_path, conf_threshold=0.4):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.conf_threshold = conf_threshold
        
        try:
            ckpt = torch.load(model_path, map_location=self.device, weights_only=False)
            self.model = ckpt['model'].float().eval()
            print(f"✅ Đã load thành công model từ: {model_path}")
        except Exception as e:
            print(f"❌ Lỗi load model: {e}")
            raise e

    def detect(self, frame):
        # 1. Preprocessing
        h, w = frame.shape[:2]
        img_size = 640
        img = cv2.resize(frame, (img_size, img_size))
        img = img.transpose((2, 0, 1))[::-1]
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device).float() / 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # 2. Inference
        with torch.no_grad():
            output = self.model(img)
            
            # --- ĐOẠN HOÀNG VỪA SỬA (ĐÃ CĂN CHỈNH) ---
            pred = output
            while isinstance(pred, (list, tuple)):
                if len(pred) > 0:
                    pred = pred[0]
                else:
                    return []

        # 3. Kiểm tra và ĐỊNH DẠNG SHAPE (BẮT BUỘC PHẢI CÓ)
        if not isinstance(pred, torch.Tensor):
            if isinstance(output, (list, tuple)) and len(output) > 1:
                pred = output[1]
                while isinstance(pred, (list, tuple)):
                    pred = pred[0]
            
            if not isinstance(pred, torch.Tensor):
                print(f"⚠️ Cảnh báo: Không thể trích xuất Tensor từ output")
                return []

        # Đưa về dạng [8400, 8] để mask [8400] hoạt động được
        if pred.ndim == 3 and pred.shape[0] == 1:
            pred = pred.squeeze(0) # [1, 8, 8400] -> [8, 8400]
        
        if pred.shape[0] < pred.shape[1]: 
            pred = pred.transpose(0, 1) # [8, 8400] -> [8400, 8]

        # 4. Filter & NMS
        detections = []
        
        # Lấy score và lọc theo ngưỡng
        scores, class_ids = torch.max(pred[:, 4:], dim=1)
        mask = scores > self.conf_threshold
        
        det = pred[mask]
        final_scores = scores[mask]
        final_cls = class_ids[mask]

        if len(det) > 0:
            boxes = det[:, :4]
            new_boxes = boxes.clone()
            new_boxes[:, 0] = boxes[:, 0] - boxes[:, 2] / 2 # x1
            new_boxes[:, 1] = boxes[:, 1] - boxes[:, 3] / 2 # y1
            new_boxes[:, 2] = boxes[:, 0] + boxes[:, 2] / 2 # x2
            new_boxes[:, 3] = boxes[:, 1] + boxes[:, 3] / 2 # y2

            keep = torchvision.ops.nms(new_boxes, final_scores, iou_threshold=0.45)
            
            for idx in keep:
                cls_id = int(final_cls[idx])
                if cls_id in VEHICLE_CLASSES:
                    x1, y1, x2, y2 = new_boxes[idx]
                    
                    x1 = int(torch.clamp(x1 * w / img_size, min=0, max=w))
                    y1 = int(torch.clamp(y1 * h / img_size, min=0, max=h))
                    x2 = int(torch.clamp(x2 * w / img_size, min=0, max=w))
                    y2 = int(torch.clamp(y2 * h / img_size, min=0, max=h))
                    
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(final_scores[idx]),
                        "class_id": cls_id,
                        "class_name": VEHICLE_CLASSES[cls_id]
                    })
        return detections