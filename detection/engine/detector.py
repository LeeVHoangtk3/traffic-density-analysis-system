import sys
import os
import torch
import cv2
import numpy as np
import torchvision

# 1. Thiết lập đường dẫn tìm code YOLOv9 core
current_dir     = os.path.dirname(os.path.abspath(__file__))
project_root    = os.path.join(current_dir, "..")
yolo_core_path  = os.path.join(project_root, "ultralytics_yolov9")
local_yolo_config = os.path.join(project_root, "Ultralytics")

os.environ.setdefault("YOLO_CONFIG_DIR",   local_yolo_config)
os.environ.setdefault("YOLOV5_CONFIG_DIR", local_yolo_config)
os.makedirs(local_yolo_config, exist_ok=True)

if yolo_core_path not in sys.path:
    sys.path.insert(0, yolo_core_path)

# Custom classes — model đã train với 4 class này
VEHICLE_CLASSES = {
    0: "bus",
    1: "car",
    2: "motorcycle",
    3: "truck",
}

# FIX #4: Per-class confidence threshold
# motorcycle nhỏ hơn → confidence thấp hơn tự nhiên → threshold thấp hơn
# Tránh bỏ sót motorcycle trong khi vẫn lọc được false positive của class lớn
CLASS_CONF_THRESHOLD = {
    0: 0.40,  # bus      — to, dễ detect, giữ ngưỡng cao
    1: 0.40,  # car
    2: 0.25,  # motorcycle — nhỏ, chiếm 70-80% traffic VN, cần ngưỡng thấp hơn
    3: 0.40,  # truck
}


class Detector:
    """
    YOLOv9 detector wrapper.

    Thay đổi so với bản gốc:
    ─────────────────────────────────────────────────────────────────
    1. [CRITICAL] bbox scale tách scale_x / scale_y riêng biệt
       → Tránh lệch bbox khi frame không phải hình vuông (16:9, v.v.)

    2. [CRITICAL] img_size chuyển thành __init__ param (self.img_size)
       → Không hardcode trong detect(), dễ override từ config

    3. [CRITICAL] torch.load() thêm comment cảnh báo weights_only
       → Giữ nguyên weights_only=False vì YOLOv9 custom ckpt cần pickle,
         nhưng thêm guard kiểm tra file tồn tại và log rõ ràng

    4. [HIGH] Per-class confidence threshold (CLASS_CONF_THRESHOLD)
       → motorcycle dùng 0.25, các class khác 0.40

    5. [HIGH] Output parsing thêm max depth guard (depth < 10)
       → Tránh infinite loop nếu model trả về nested structure bất thường

    6. [HIGH] GPU memory: del tensor sau mỗi frame, empty_cache định kỳ
       → Tránh VRAM leak khi chạy nhiều giờ trên Colab T4
    ─────────────────────────────────────────────────────────────────
    """

    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.40,
        img_size: int = 960,          # FIX #2: không hardcode trong detect()
    ):
        self.device         = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.conf_threshold = conf_threshold
        self.img_size       = img_size   # FIX #2
        self._frame_count   = 0          # dùng cho empty_cache định kỳ

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        try:
            # weights_only=False cần thiết vì YOLOv9 custom ckpt dùng pickle
            # Chỉ load file .pt từ nguồn tin cậy (model do bạn train)
            ckpt = torch.load(model_path, map_location=self.device, weights_only=False)
            self.model = ckpt["model"].float().eval()
            print(f"[Detector] Loaded: {os.path.basename(model_path)}")
            print(f"[Detector] Device: {self.device} | img_size: {self.img_size} | conf: {self.conf_threshold}")
        except Exception as e:
            print(f"[Detector] Load error: {e}")
            raise

    def detect(self, frame: np.ndarray) -> list[dict]:
        """
        Args:
            frame: BGR numpy array (bất kỳ resolution nào)
        Returns:
            List of dicts: {bbox, confidence, class_id, class_name}
            bbox đã được scale về kích thước frame gốc
        """
        self._frame_count += 1

        # ── 1. Lưu kích thước gốc để scale bbox về sau ──────────────
        h_orig, w_orig = frame.shape[:2]
        img_size = self.img_size

        # ── 2. Preprocessing ────────────────────────────────────────
        img = cv2.resize(frame, (img_size, img_size))
        img = img.transpose((2, 0, 1))[::-1]          # HWC BGR → CHW RGB
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device).float() / 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)                     # → [1, 3, 960, 960]

        # ── 3. Inference ─────────────────────────────────────────────
        try:
            with torch.no_grad():
                output = self.model(img)

            # FIX #5: Parse output với max depth guard — tránh infinite loop
            pred  = output
            depth = 0
            while isinstance(pred, (list, tuple)) and depth < 10:
                if len(pred) == 0:
                    return []
                pred  = pred[0]
                depth += 1

            # Fallback: thử lấy output[1] nếu output[0] không phải tensor
            if not isinstance(pred, torch.Tensor):
                if isinstance(output, (list, tuple)) and len(output) > 1:
                    pred  = output[1]
                    depth = 0
                    while isinstance(pred, (list, tuple)) and depth < 10:
                        pred  = pred[0]
                        depth += 1
                if not isinstance(pred, torch.Tensor):
                    print("[Detector] Warning: không extract được Tensor từ model output")
                    return []

            # ── 4. Chuẩn hóa shape → [N, 8] ─────────────────────────
            if pred.ndim == 3 and pred.shape[0] == 1:
                pred = pred.squeeze(0)          # [1, 8, 8400] → [8, 8400]
            if pred.shape[0] < pred.shape[1]:
                pred = pred.transpose(0, 1)     # [8, 8400]    → [8400, 8]

            # ── 5. Filter theo confidence ────────────────────────────
            scores, class_ids = torch.max(pred[:, 4:], dim=1)
            mask = scores > self.conf_threshold     # pre-filter thô
            det          = pred[mask]
            final_scores = scores[mask]
            final_cls    = class_ids[mask]

            if len(det) == 0:
                return []

            # ── 6. Convert cx,cy,w,h → x1,y1,x2,y2 ─────────────────
            boxes     = det[:, :4]
            new_boxes = boxes.clone()
            new_boxes[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1
            new_boxes[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1
            new_boxes[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2
            new_boxes[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2

            # ── 7. NMS ───────────────────────────────────────────────
            keep = torchvision.ops.nms(new_boxes, final_scores, iou_threshold=0.45)

            # FIX #1: scale_x và scale_y tách biệt
            # frame gốc 16:9 → resize thành 960×960 squash
            # → phải scale x theo w_orig, y theo h_orig riêng biệt
            scale_x = w_orig / img_size
            scale_y = h_orig / img_size

            detections = []
            for idx in keep:
                cls_id  = int(final_cls[idx])
                score   = float(final_scores[idx])

                if cls_id not in VEHICLE_CLASSES:
                    continue

                # FIX #4: per-class threshold — motorcycle dùng ngưỡng thấp hơn
                cls_threshold = CLASS_CONF_THRESHOLD.get(cls_id, self.conf_threshold)
                if score < cls_threshold:
                    continue

                x1, y1, x2, y2 = new_boxes[idx]

                # FIX #1: scale về kích thước frame gốc đúng tỷ lệ
                x1 = int(torch.clamp(x1 * scale_x, min=0, max=w_orig))
                y1 = int(torch.clamp(y1 * scale_y, min=0, max=h_orig))
                x2 = int(torch.clamp(x2 * scale_x, min=0, max=w_orig))
                y2 = int(torch.clamp(y2 * scale_y, min=0, max=h_orig))

                # Bỏ box degenerate (w hoặc h = 0)
                if x2 <= x1 or y2 <= y1:
                    continue

                detections.append({
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": score,
                    "class_id":   cls_id,
                    "class_name": VEHICLE_CLASSES[cls_id],
                })

            return detections

        finally:
            # FIX #6: Giải phóng VRAM sau mỗi frame
            try:
                del img
            except NameError:
                pass
            if self.device.type == "cuda" and self._frame_count % 200 == 0:
                torch.cuda.empty_cache()