"""
detection/calibrate_zones.py  -  Interactive Camera Zone Calibration Tool (Single ROI Edition)

Công cụ hiệu chuẩn đồ họa OpenCV giúp vẽ duy nhất 1 vùng ROI đa giác dẹt
(Vùng chốt đếm tổng) chặn mặt cắt đường một chiều cho cam01, cam02, cam03, etc.

Tự động nhận diện CAMERA_ID và nạp đúng cấu hình cam (.json) dựa theo tên video nguồn đầu vào,
bảo toàn các cấu hình vùng đa dạng có sẵn (multi-zone) của từng Camera.

Sử dụng:
  TRAFFIC_CAMERA_ID=cam01 python -m detection.calibrate_zones
  TRAFFIC_VIDEO_SOURCE=data/video/cam02-traffic4.mp4 python -m detection.calibrate_zones
"""

import os
import sys
import json
import cv2
import numpy as np
import re
from pathlib import Path

# Thêm thư mục gốc vào hệ thống
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Cấu hình Camera và Đường dẫn dữ liệu mặc định
CAMERA_ID = os.getenv("TRAFFIC_CAMERA_ID", "cam01")
DEFAULT_VIDEO_SOURCE = os.path.join(BASE_DIR, "data", "video", "cam03-traffic2.mp4")
TARGET_WIDTH = 960
TARGET_HEIGHT = 540

# BGR Color - Màu xanh lá ngọc bảo cao cấp đại diện cho ROI
ROI_COLOR = (129, 185, 16) 

class ZoneCalibrator:
    def __init__(self):
        # 1. Giữ nguyên định dạng lấy nguồn video đầu vào (từ biến môi trường hoặc mặc định)
        # HỆ THỐNG TỰ ĐỘNG MAP NGUỒN VIDEO VÀ FILE CẤU HÌNH THEO CAMERA_ID (MẶC ĐỊNH LÀ CAM01, HỖ TRỢ ĐỘNG CAM02, CAM03,...)
        self.video_source = os.getenv("TRAFFIC_VIDEO_SOURCE", DEFAULT_VIDEO_SOURCE)
        
        # 2. Tự động nhận diện CAMERA_ID chính xác dựa trên tên của tệp video nguồn đầu vào
        self.camera_id = CAMERA_ID.lower()
        match = re.search(r'(cam\d+)', os.path.basename(self.video_source).lower())
        if match:
            self.camera_id = match.group(1)
            print(f"[Smart-Detect] Phát hiện thấy CAMERA_ID '{self.camera_id.upper()}' từ tên video: {os.path.basename(self.video_source)}")

        # 3. Chỉ định đúng đường dẫn cấu hình của camera đó
        self.config_path = os.path.join(BASE_DIR, "detection", "configs_cameras", f"{self.camera_id}.json")
        print(f"[Smart-Config] Sử dụng file cấu hình: {self.config_path}")
        print(f"[Smart-Video] Nguồn video đầu vào: {self.video_source}")
        
        self.frame = None
        self.display_frame = None
        
        # 4. Nạp cấu hình hiện tại
        self.load_config()
        
        # 5. Trích xuất dữ liệu của duy nhất zone_trigger để chỉnh sửa
        self.zone_points = []
        for zone in self.config.get("zones", []):
            if zone.get("id") == "zone_trigger" or zone.get("is_trigger"):
                self.zone_points = zone["points"]
                break
        
        self.active_zone = "zone_trigger"
        self.current_points = list(self.zone_points)
        self.show_hud = True
        self.mouse_pos = (0, 0)
        
        # 6. Nạp khung hình video làm nền vẽ
        self.load_video_frame()
        
    def load_config(self):
        """
        Nạp cấu hình JSON. Nếu chưa tồn tại, khởi tạo cấu hình mẫu phù hợp.
        """
        if not os.path.exists(self.config_path):
            print(f"[Warning] Config file không tồn tại tại {self.config_path}. Tạo cấu hình mặc định cho {self.camera_id.upper()}.")
            monitored_dir = "multi" if self.camera_id == "cam02" else "single_roi"
            self.config = {
                "camera_id": self.camera_id,
                "name": f"Camera {self.camera_id.upper()}",
                "monitored_direction": monitored_dir,
                "baseline_green": 30,
                "frame_width": TARGET_WIDTH,
                "frame_height": TARGET_HEIGHT,
                "zones": []
            }
        else:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            print(f"[Info] Đã nạp cấu hình camera từ: {self.config_path}")

    def load_video_frame(self):
        """
        Nạp khung hình từ video nguồn làm hình nền vẽ ROI.
        """
        print(f"[Info] Đang mở nguồn video: {self.video_source}")
        src = int(self.video_source) if self.video_source.isdigit() else self.video_source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            # Fallback sang traffic1.mp4 nếu file mặc định không tồn tại
            fallback = os.path.join(BASE_DIR, "data", "video", "traffic1.mp4")
            if os.path.exists(fallback):
                print(f"[Info] Nguồn mặc định lỗi. Khôi phục sang fallback: {fallback}")
                cap = cv2.VideoCapture(fallback)
                
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("[Error] Không đọc được khung hình video. Chuyển sang lưới tọa độ ảo.")
            self.frame = np.zeros((TARGET_HEIGHT, TARGET_WIDTH, 3), dtype=np.uint8)
            for x in range(0, TARGET_WIDTH, 50):
                cv2.line(self.frame, (x, 0), (x, TARGET_HEIGHT), (40, 40, 40), 1)
            for y in range(0, TARGET_HEIGHT, 50):
                cv2.line(self.frame, (0, y), (TARGET_WIDTH, y), (40, 40, 40), 1)
            cv2.putText(self.frame, "No Video Source - Grid Mode", (50, TARGET_HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            self.frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
            print(f"[Info] Đã nạp thành công khung hình kích thước {TARGET_WIDTH}x{TARGET_HEIGHT}")

    def save_to_config(self):
        """
        Cập nhật duy nhất tọa độ zone_trigger, bảo toàn các zone khác (ví dụ: zone_left, zone_straight)
        và ghi đè vào file JSON cấu hình của đúng camera tương ứng.
        """
        if not self.current_points or len(self.current_points) < 3:
            print("[Warning] Đa giác phải có ít nhất 3 điểm đỉnh! Hủy lưu file.")
            return

        formatted_points = [[int(p[0]), int(p[1])] for p in self.current_points]
        
        if "zones" not in self.config:
            self.config["zones"] = []
            
        # Tìm và cập nhật zone_trigger hiện có, bảo toàn các zone định hướng khác
        updated = False
        for zone in self.config["zones"]:
            if zone.get("id") == "zone_trigger" or zone.get("is_trigger"):
                zone["points"] = formatted_points
                zone["id"] = "zone_trigger"
                zone["direction"] = "trigger"
                zone["is_trigger"] = True
                updated = True
                print(f"[Info] Đã cập nhật tọa độ 'zone_trigger' trong danh sách vùng.")
                break
                
        # Nếu chưa có zone_trigger, tiến hành append mới
        if not updated:
            self.config["zones"].append({
                "id": "zone_trigger",
                "direction": "trigger",
                "points": formatted_points,
                "is_trigger": True
            })
            print(f"[Info] Đã thêm mới vùng 'zone_trigger' vào danh sách vùng.")
            
        self.config["frame_width"] = TARGET_WIDTH
        self.config["frame_height"] = TARGET_HEIGHT
        
        # Ghi cấu hình ra file JSON của camera tương ứng
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
            
        print("\n" + "="*70)
        print(f"[SUCCESS] Đã lưu vùng ROI thành công vào cấu hình Camera {self.camera_id.upper()}:")
        print(f" 👉 File Path: {self.config_path}")
        print(f" 👉 Số lượng zone đang có: {len(self.config['zones'])}")
        print("="*70 + "\n")

    def mouse_callback(self, event, x, y, flags, param):
        self.mouse_pos = (x, y)
        
        # Click chuột trái để thêm điểm đỉnh
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append([x, y])
            print(f"Thêm điểm đỉnh: [{x}, {y}] (Tổng: {len(self.current_points)})")
            
        # Click chuột phải để xóa điểm vừa vẽ (Undo)
        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.current_points:
                popped = self.current_points.pop()
                print(f"Đã Undo (Xóa điểm cuối): {popped}")
            else:
                print("Chưa có điểm nào để Undo.")

    def print_instructions(self):
        print("\n" + "="*70)
        print(f"   SMART ZONE CALIBRATION TOOL - CAMERA: {self.camera_id.upper()}")
        print("="*70)
        print(f"  👉 Config File: {self.config_path}")
        print(f"  👉 Video Source: {self.video_source}")
        print("\n  Thao tác chuột:")
        print("    - Click CHUỘT TRÁI để tạo điểm đỉnh đa giác.")
        print("    - Click CHUỘT PHẢI để xóa điểm đỉnh vừa tạo (Undo).")
        print("\n  Thao tác phím nóng:")
        print("    - Nhấn phím 'c' hoặc 'C': Xóa sạch toàn bộ điểm vẽ làm lại từ đầu.")
        print("    - Nhấn phím 's' hoặc 'S': Lưu đa giác hiện hành vào cấu hình tạm thời.")
        print("    - Nhấn phím 'h' hoặc 'H': Bật/Tắt bảng thông tin hướng dẫn trên màn hình.")
        print("    - Nhấn phím 'q', 'ESC' hoặc đóng cửa sổ: GHI LÊN FILE JSON VÀ THOÁT.")
        print("="*70 + "\n")

    def run(self):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            
        self.print_instructions()
        
        window_title = f"Smart ROI Calibrator - {self.camera_id.upper()}"
        cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(window_title, self.mouse_callback)
        
        while True:
            self.display_frame = self.frame.copy()
            overlay = self.display_frame.copy()
            
            # Vẽ các điểm đỉnh và đường nối preview của ROI
            if len(self.current_points) > 0:
                for idx, pt in enumerate(self.current_points):
                    cv2.circle(self.display_frame, tuple(pt), 6, ROI_COLOR, -1)
                    cv2.putText(self.display_frame, str(idx+1), (pt[0]+8, pt[1]+5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
                
                pts_arr = np.array(self.current_points, np.int32)
                if len(self.current_points) >= 3:
                    # Vẽ đa giác khép kín kèm màu tô trong suốt
                    cv2.polylines(self.display_frame, [pts_arr], isClosed=True, color=ROI_COLOR, thickness=2)
                    cv2.fillPoly(overlay, [pts_arr], ROI_COLOR)
                elif len(self.current_points) == 2:
                    cv2.line(self.display_frame, tuple(self.current_points[0]), tuple(self.current_points[1]), ROI_COLOR, 2)
                
                # Đường kéo lê từ điểm đỉnh cuối đến chuột để căn chỉnh
                last_pt = self.current_points[-1]
                cv2.line(self.display_frame, tuple(last_pt), self.mouse_pos, ROI_COLOR, 1, cv2.LINE_AA)
            
            # Vẽ hồng tâm chuột phục vụ vẽ độ chính xác cao
            cv2.circle(self.display_frame, self.mouse_pos, 5, ROI_COLOR, 1)
            
            # Áp dụng độ mờ trong suốt cho đa giác vẽ
            cv2.addWeighted(overlay, 0.25, self.display_frame, 0.75, 0, self.display_frame)
            
            # ── HIỂN THỊ CÁC ZONE KHÁC CÓ SẴN (ĐỂ TRÁNH VẼ TRÙNG) ───────────────
            # Vẽ viền nét đứt hoặc mờ của các zone khác như straight, left, right nếu có
            for zone in self.config.get("zones", []):
                if zone.get("id") != "zone_trigger" and not zone.get("is_trigger"):
                    pts = np.array(zone["points"], np.int32)
                    cv2.polylines(self.display_frame, [pts], isClosed=True, color=(150, 150, 150), thickness=1)
                    # Ghi tên zone
                    if len(pts) > 0:
                        cv2.putText(self.display_frame, zone["id"], tuple(pts[0]),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)

            # ── HIỂN THỊ HUD ĐỒ HỌA ───────────────────────────────────────────
            if self.show_hud:
                # Vẽ HUD panel mờ đục màu đen sang trọng
                cv2.rectangle(self.display_frame, (12, 12), (580, 112), (15, 15, 15), -1)
                cv2.rectangle(self.display_frame, (12, 12), (580, 112), (80, 80, 80), 1)
                
                cv2.putText(self.display_frame, f"ROI CALIBRATION (SMART ZONE MODE) - {self.camera_id.upper()}", (22, 32),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
                
                cv2.putText(self.display_frame, "Target:", (22, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "ZONE_TRIGGER (ROI DỰ BÁO & ĐẾM XE CHUNG)", (100, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, ROI_COLOR, 1, cv2.LINE_AA)
                
                pts_count = len(self.current_points)
                cv2.putText(self.display_frame, f"Points drawn: {pts_count}/4+", (22, 77),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100) if pts_count >= 3 else (100, 100, 255), 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "Controls: [C] Clear | [S] Save | [ESC / Q] Save & Exit", (22, 96),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

            cv2.imshow(window_title, self.display_frame)
            key = cv2.waitKey(30) & 0xFF
            
            # Xử lý sự kiện bàn phím
            if key == ord("q") or key == 27:  # Phím q hoặc ESC để thoát
                print("[Info] Đang lưu cấu hình và thoát công cụ hiệu chuẩn...")
                self.save_to_config()
                break
                
            elif key == ord("c") or key == ord("C"):
                self.current_points = []
                print("[Info] Đã xóa toàn bộ điểm đỉnh vẽ.")
                
            elif key == ord("s") or key == ord("S"):
                if len(self.current_points) >= 3:
                    self.save_to_config()
                else:
                    print("[Warning] Cần tối thiểu 3 điểm để tạo đa giác đóng!")
                    
            elif key == ord("h") or key == ord("H"):
                self.show_hud = not self.show_hud
                print(f"[Info] Trạng thái hiển thị HUD: {self.show_hud}")
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    calibrator = ZoneCalibrator()
    calibrator.run()
