"""
detection/calibrate_zones.py  -  Interactive Camera Zone Calibration Tool

This tool provides a graphical user interface (GUI) using OpenCV to manually draw
and calibrate the 4 Region of Interest (ROI) polygons (Trigger Zone, Left Turn,
Straight, and Right Turn Lanes) on a frame from the video source.

It automatically saves/updates the configuration in `detection/configs_cameras/cam_01.json`.

Usage:
  python -m detection.calibrate_zones
"""

import os
import sys
import json
import cv2
import numpy as np
from pathlib import Path

# Setup project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Configurations
CAMERA_ID = os.getenv("TRAFFIC_CAMERA_ID", "CAM_02")
CONFIG_FILE = os.path.join(BASE_DIR, "detection", "configs_cameras", f"{CAMERA_ID.lower()}.json")
DEFAULT_VIDEO_SOURCE = os.path.join(BASE_DIR, "data", "video", "traffic5.mp4")
TARGET_WIDTH = 960
TARGET_HEIGHT = 540

# Define colors (BGR) matching ZoneManager
COLORS = {
    "zone_left": (255, 0, 255),       # Pink / Magenta
    "zone_straight": (0, 255, 255),   # Cyan / Yellowish
    "zone_right": (255, 165, 0),      # Orange
    "zone_trigger": (0, 0, 255)       # Red
}

ZONE_NAMES = {
    "zone_left": "Làn Rẽ Trái (Left Lane)",
    "zone_straight": "Làn Đi Thẳng (Straight Lane)",
    "zone_right": "Làn Rẽ Phải (Right Lane)",
    "zone_trigger": "Vùng Kích Hoạt (Trigger Zone)"
}

class ZoneCalibrator:
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.video_source = os.getenv("TRAFFIC_VIDEO_SOURCE", DEFAULT_VIDEO_SOURCE)
        self.frame = None
        self.display_frame = None
        
        # Load configuration
        self.load_config()
        
        # Calibration state
        self.zones_data = {}  # {zone_id: list of points}
        for zone in self.config.get("zones", []):
            self.zones_data[zone["id"]] = zone["points"]
            
        # Add fallback empty lists if zones are missing
        for zid in ["zone_left", "zone_straight", "zone_right", "zone_trigger"]:
            if zid not in self.zones_data:
                self.zones_data[zid] = []
                
        self.active_zone = "zone_trigger"  # Default active zone
        self.current_points = []           # Points currently being drawn for active zone
        self.show_all_overlays = True
        self.show_hud = True               # Toggle to show/hide the HUD boxes
        self.mouse_pos = (0, 0)            # Current mouse position tracker
        
        # Load video frame
        self.load_video_frame()
        
    def load_config(self):
        if not os.path.exists(self.config_path):
            print(f"[Warning] Config file not found at {self.config_path}. Creating new default config.")
            self.config = {
                "camera_id": CAMERA_ID,
                "name": "Camera 01 - Main Detection",
                "monitored_direction": "multi",
                "baseline_green": 30,
                "frame_width": TARGET_WIDTH,
                "frame_height": TARGET_HEIGHT,
                "zones": []
            }
        else:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            print(f"[Info] Loaded existing camera configuration from {self.config_path}")

    def load_video_frame(self):
        print(f"[Info] Reading video source: {self.video_source}")
        src = int(self.video_source) if self.video_source.isdigit() else self.video_source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            # Try traffic1.mp4 fallback if traffic3 is missing
            fallback = os.path.join(BASE_DIR, "data", "video", "traffic1.mp4")
            if os.path.exists(fallback):
                print(f"[Info] Default video not found. Loading fallback: {fallback}")
                cap = cv2.VideoCapture(fallback)
                
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("[Error] Could not read any frame from video source. Creating empty canvas.")
            # Create a generic grid image as canvas if video fails to load
            self.frame = np.zeros((TARGET_HEIGHT, TARGET_WIDTH, 3), dtype=np.uint8)
            for x in range(0, TARGET_WIDTH, 50):
                cv2.line(self.frame, (x, 0), (x, TARGET_HEIGHT), (40, 40, 40), 1)
            for y in range(0, TARGET_HEIGHT, 50):
                cv2.line(self.frame, (0, y), (TARGET_WIDTH, y), (40, 40, 40), 1)
            cv2.putText(self.frame, "No Video Source Found - Calibration Grid Mode", (50, TARGET_HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            # Resize frame to target dimensions
            self.frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
            print(f"[Info] Successfully loaded frame resized to {TARGET_WIDTH}x{TARGET_HEIGHT}")

    def save_to_config(self):
        # Format the zones as list of dictionaries
        zones_list = []
        
        # Zone properties dictionary
        zone_props = {
            "zone_left": {"direction": "left", "is_trigger": False},
            "zone_straight": {"direction": "straight", "is_trigger": False},
            "zone_right": {"direction": "right", "is_trigger": False},
            "zone_trigger": {"direction": "trigger", "is_trigger": True}
        }
        
        for zid, points in self.zones_data.items():
            if not points or len(points) < 3:
                # Keep original configuration points if the user didn't draw anything or clicked invalid poly
                original_zone = next((z for z in self.config.get("zones", []) if z["id"] == zid), None)
                if original_zone:
                    zones_list.append(original_zone)
                    continue
                else:
                    print(f"[Warning] Zone {zid} requires at least 3 points. Skipping.")
                    continue
            
            props = zone_props.get(zid, {"direction": "straight", "is_trigger": False})
            zone_dict = {
                "id": zid,
                "direction": props["direction"],
                "points": [[int(p[0]), int(p[1])] for p in points]
            }
            if props["is_trigger"]:
                zone_dict["is_trigger"] = True
                
            zones_list.append(zone_dict)
            
        self.config["zones"] = zones_list
        self.config["frame_width"] = TARGET_WIDTH
        self.config["frame_height"] = TARGET_HEIGHT
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
            
        print("\n" + "="*50)
        print(f"[SUCCESS] Saved configurations successfully to:\n{self.config_path}")
        print("="*50 + "\n")

    def mouse_callback(self, event, x, y, flags, param):
        # Update current mouse position
        self.mouse_pos = (x, y)
        
        # Left button press adds a point
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append([x, y])
            print(f"Point added: [{x}, {y}] (Total: {len(self.current_points)})")
            
        # Right button press undoes the last point
        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.current_points:
                popped = self.current_points.pop()
                print(f"Removed point: {popped}")
            else:
                print("No points to remove.")

    def print_instructions(self):
        print("\n" + "="*70)
        print("    HƯỚNG DẪN HIỆU CHUẨN VÙNG ROI CAMERA THỦ CÔNG (ZONE CALIBRATION)")
        print("="*70)
        print("  Chuột:")
        print("    - Click CHUỘT TRÁI để thêm điểm đỉnh đa giác.")
        print("    - Click CHUỘT PHẢI để xóa điểm đỉnh vừa click (Undo).")
        print("\n  Phím chọn Zone:")
        print("    - Nhấn phím '1': Chọn Làn Rẽ Trái (zone_left - màu Hồng)")
        print("    - Nhấn phím '2': Chọn Làn Đi Thẳng (zone_straight - màu Cyan/Vàng)")
        print("    - Nhấn phím '3': Chọn Làn Rẽ Phải (zone_right - màu Cam)")
        print("    - Nhấn phím '4': Chọn Vùng Kích Hoạt (zone_trigger - màu Đỏ)")
        print("\n  Phím hành động:")
        print("    - Nhấn phím 'c': Xóa toàn bộ điểm đang vẽ dở của Zone hiện tại.")
        print("    - Nhấn phím 's': Lưu đa giác hiện tại vào bộ nhớ tạm của Zone đang chọn.")
        print("    - Nhấn phím 'd': Bật/Tắt hiển thị toàn bộ các Zone đã vẽ đè lên hình.")
        print("    - Nhấn phím 'r': Khôi phục lại cấu hình gốc từ file JSON.")
        print("    - Nhấn phím 'h': In lại bảng hướng dẫn này ra màn hình Console.")
        print("    - Nhấn phím 'q' hoặc phím ESC: Lưu toàn bộ cấu hình vào JSON và THOÁT.")
        print("="*70 + "\n")

    def run(self):
        self.print_instructions()
        
        cv2.namedWindow("Zone Calibrator", cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback("Zone Calibrator", self.mouse_callback)
        
        # If active zone has existing points in the config, populate current_points
        if self.zones_data[self.active_zone]:
            self.current_points = list(self.zones_data[self.active_zone])
            
        while True:
            # Create a working copy of the frame to draw on
            self.display_frame = self.frame.copy()
            
            # Create a transparent overlay for filled zones
            overlay = self.display_frame.copy()
            
            # Draw saved zones
            if self.show_all_overlays:
                for zid, points in self.zones_data.items():
                    # Skip drawing the active zone if we are actively drawing it right now
                    if zid == self.active_zone:
                        continue
                    
                    if len(points) >= 3:
                        pts_arr = np.array(points, np.int32)
                        color = COLORS[zid]
                        # Draw filled polygon on overlay
                        cv2.fillPoly(overlay, [pts_arr], color)
                        # Draw outline
                        cv2.polylines(self.display_frame, [pts_arr], isClosed=True, color=color, thickness=2)
                        # Put text label
                        cv2.putText(self.display_frame, zid.upper(), (points[0][0], points[0][1] - 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            
            # Draw currently drawing points/lines for the active zone
            active_color = COLORS[self.active_zone]
            if len(self.current_points) > 0:
                # Draw small circles at each point
                for idx, pt in enumerate(self.current_points):
                    cv2.circle(self.display_frame, tuple(pt), 5, active_color, -1)
                    cv2.putText(self.display_frame, str(idx+1), (pt[0]+6, pt[1]+6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
                
                # Draw lines connecting points
                pts_arr = np.array(self.current_points, np.int32)
                if len(self.current_points) >= 3:
                    # Draw closed preview polygon
                    cv2.polylines(self.display_frame, [pts_arr], isClosed=True, color=active_color, thickness=2)
                    cv2.fillPoly(overlay, [pts_arr], active_color)
                elif len(self.current_points) == 2:
                    # Draw simple line
                    cv2.line(self.display_frame, tuple(self.current_points[0]), tuple(self.current_points[1]), active_color, 2)
                
                # Draw dynamic preview line from last point to current mouse position
                last_pt = self.current_points[-1]
                cv2.line(self.display_frame, tuple(last_pt), self.mouse_pos, active_color, 1, cv2.LINE_AA)
            
            # Draw mouse pointer dot for precision drawing
            cv2.circle(self.display_frame, self.mouse_pos, 4, active_color, 1)
            
            # Blend overlay
            cv2.addWeighted(overlay, 0.35, self.display_frame, 1 - 0.35, 0, self.display_frame)
            
            # ── DRAW HUD INTERFACE ────────────────────────────────────────────────
            if self.show_hud:
                cv2.rectangle(self.display_frame, (10, 10), (520, 110), (15, 15, 15), -1)
                cv2.rectangle(self.display_frame, (10, 10), (520, 110), (100, 100, 100), 1)
                
                cv2.putText(self.display_frame, f"ZONE CALIBRATION TOOL - {CAMERA_ID}", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
                
                # Active zone description
                cv2.putText(self.display_frame, f"Active Zone: ", (20, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, f"{self.active_zone.upper()}", (120, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, active_color, 2, cv2.LINE_AA)
                cv2.putText(self.display_frame, f"({ZONE_NAMES[self.active_zone]})", (250, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1, cv2.LINE_AA)
                
                # Hotkeys status
                pts_count = len(self.current_points)
                cv2.putText(self.display_frame, f"Points clicked: {pts_count}", (20, 75),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255) if pts_count >= 3 else (100, 100, 255), 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "Status: Press [S] to SAVE | [ESC] or [Q] to Save All & EXIT", (20, 95),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
                
                # Render key maps on the right side
                cv2.rectangle(self.display_frame, (TARGET_WIDTH - 250, 10), (TARGET_WIDTH - 10, 160), (15, 15, 15), -1)
                cv2.rectangle(self.display_frame, (TARGET_WIDTH - 250, 10), (TARGET_WIDTH - 10, 160), (100, 100, 100), 1)
                cv2.putText(self.display_frame, "KEYS SELECT:", (TARGET_WIDTH - 240, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "[1] Zone Left (Pink)", (TARGET_WIDTH - 240, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS["zone_left"], 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "[2] Zone Straight (Cyan)", (TARGET_WIDTH - 240, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS["zone_straight"], 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "[3] Zone Right (Orange)", (TARGET_WIDTH - 240, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS["zone_right"], 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "[4] Zone Trigger (Red)", (TARGET_WIDTH - 240, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS["zone_trigger"], 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "[C] Clear  [D] Toggle Overlays", (TARGET_WIDTH - 240, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1, cv2.LINE_AA)
                cv2.putText(self.display_frame, "[H] Hide/Show HUD Panels", (TARGET_WIDTH - 240, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 255, 100), 1, cv2.LINE_AA)

            # Display window
            cv2.imshow("Zone Calibrator", self.display_frame)
            key = cv2.waitKey(30) & 0xFF
            
            # Keyboard Logic
            if key == ord("q") or key == 27:  # q or ESC
                # Double check to save any unsaved work if appropriate
                print("[Info] Exiting and saving to configuration file...")
                self.save_to_config()
                break
                
            elif key == ord("1"):
                # Switch to zone_left
                self.active_zone = "zone_left"
                self.current_points = list(self.zones_data[self.active_zone])
                print(f"Switched active zone to: {self.active_zone}")
                
            elif key == ord("2"):
                # Switch to zone_straight
                self.active_zone = "zone_straight"
                self.current_points = list(self.zones_data[self.active_zone])
                print(f"Switched active zone to: {self.active_zone}")
                
            elif key == ord("3"):
                # Switch to zone_right
                self.active_zone = "zone_right"
                self.current_points = list(self.zones_data[self.active_zone])
                print(f"Switched active zone to: {self.active_zone}")
                
            elif key == ord("4"):
                # Switch to zone_trigger
                self.active_zone = "zone_trigger"
                self.current_points = list(self.zones_data[self.active_zone])
                print(f"Switched active zone to: {self.active_zone}")
                
            elif key == ord("c") or key == ord("C"):
                # Clear active zone points
                self.current_points = []
                print(f"Cleared points for active zone: {self.active_zone}")
                
            elif key == ord("s") or key == ord("S"):
                # Save current drawing points to the current active zone
                if len(self.current_points) >= 3:
                    self.zones_data[self.active_zone] = list(self.current_points)
                    print(f"[Info] Saved {len(self.current_points)} points locally to {self.active_zone}.")
                else:
                    print("[Warning] A polygon must have at least 3 points to be saved!")
                    
            elif key == ord("d") or key == ord("D"):
                # Toggle displaying all other overlays
                self.show_all_overlays = not self.show_all_overlays
                print(f"Toggle overlays: {self.show_all_overlays}")
                
            elif key == ord("r") or key == ord("R"):
                # Reload original config
                self.load_config()
                self.zones_data = {}
                for zone in self.config.get("zones", []):
                    self.zones_data[zone["id"]] = zone["points"]
                for zid in ["zone_left", "zone_straight", "zone_right", "zone_trigger"]:
                    if zid not in self.zones_data:
                        self.zones_data[zid] = []
                self.current_points = list(self.zones_data[self.active_zone])
                print("[Info] Reset configurations successfully back to file content.")
                
            elif key == ord("h") or key == ord("H"):
                # Toggle displaying HUD panels
                self.show_hud = not self.show_hud
                print(f"[Info] Toggle HUD display: {self.show_hud}")
                
            elif key == ord("i") or key == ord("I"):
                # Print terminal instructions
                self.print_instructions()
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    calibrator = ZoneCalibrator()
    calibrator.run()
