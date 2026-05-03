# Camera Display Module

## Tổng quan

Module `camera_display.py` là một công cụ hiển thị camera/video với overlay thời gian đèn xanh (green time) được tính toán từ hệ thống tối ưu hóa đèn tín hiệu giao thông.

## Chức năng chính

### 1. Hiển thị Camera/Video
- Hỗ trợ webcam (theo index) hoặc file video
- Hiển thị real-time với overlay thông tin

### 2. Tính toán Thời gian Đèn Xanh
- Sử dụng `TrafficLightOptimizer` từ `integration_system`
- Phân loại mức độ tắc nghẽn dựa trên số lượng xe
- Tính toán thời gian đèn xanh tối ưu

### 3. Heads-Up Display (HUD)
- **Panel chính**: Hiển thị thời gian đèn xanh, delta, mức tắc nghẽn
- **Đồng hồ**: Thời gian thực và ngày tháng
- **Đèn tín hiệu mini**: Trạng thái đèn (đỏ/vàng/xanh)
- **Thông tin bổ sung**: Số xe, FPS, chế độ hoạt động

## Cách sử dụng

### Cài đặt và Chạy

```bash
# Sử dụng webcam mặc định (index 0)
python detection/camera_display.py

# Sử dụng webcam cụ thể
python detection/camera_display.py --cam 1

# Phát video file
python detection/camera_display.py --video traffictrim.mp4
```

### Tham số dòng lệnh

- `--video PATH`: Đường dẫn tới file video (mặc định: `traffictrim.mp4`)
- `--cam INDEX`: Index của webcam (0, 1, 2, ...)
- `--camera-id ID`: ID camera cho optimizer (mặc định: `CAM_01`)
- `--update-interval SECONDS`: Tần suất cập nhật green time (mặc định: 5 giây)

### Phím tắt

- **Q / ESC**: Thoát chương trình
- **SPACE**: Tạm dừng / Tiếp tục

## Kiến trúc

### Dependencies

- **OpenCV**: Xử lý video và hiển thị
- **TrafficLightOptimizer**: Tính toán thời gian đèn xanh
- **CongestionClassifier**: Phân loại mức độ tắc nghẽn

### Fallback Mode

Nếu không thể import `TrafficLightOptimizer`, module sẽ sử dụng:
- `_SimpleOptimizer`: Logic đơn giản dựa trên rule
- `_SimpleClassifier`: Phân loại tắc nghẽn cơ bản

### Fake Vehicle Counter

Trong chế độ demo, sử dụng `_FakeVehicleCounter` để giả lập số lượng xe thay vì detector thật.

## Cấu trúc Code

### Các hàm chính

- `draw_hud()`: Vẽ overlay thông tin lên frame
- `_draw_traffic_light()`: Vẽ đèn tín hiệu thu nhỏ
- `_draw_rounded_rect()`: Vẽ hình chữ nhật bo góc mờ
- `main()`: Hàm chính xử lý video loop

### Biến trạng thái

- `green_time`: Thời gian đèn xanh hiện tại
- `congestion`: Mức độ tắc nghẽn ("low", "medium", "high", "severe")
- `mode`: Chế độ tính toán ("rule", "ml")
- `phase`: Giai đoạn đèn tín hiệu
- `delta`: Độ lệch so với baseline
- `baseline`: Thời gian cơ sở

## Màn hình hiển thị

### Panel Chính (Trái trên)
```
TRAFFIC LIGHT MONITOR
─────────────────────
   45.0s
GREEN TIME

Delta: +5.0s  Base: 40s
Congestion: HIGH
Phase: PEAK   Mode: ml
Vehicles: 35   FPS: 29.8
```

### Đồng hồ (Phải trên)
```
14:30:25
25/12/2023
```

### Đèn tín hiệu (Phải dưới)
- Hiển thị trạng thái đèn theo thời gian xanh:
  - Đỏ: < 15 giây
  - Vàng: 15-30 giây
  - Xanh: ≥ 30 giây

## Tích hợp

Module này tích hợp với:
- `integration_system.system_runner`: TrafficLightOptimizer
- Camera detection system: Để lấy số lượng xe thực
- Backend API: Gửi dữ liệu thời gian đèn

## Lưu ý

- Trong chế độ demo, số lượng xe được giả lập
- Để sử dụng với detector thật, cần tích hợp với `detection/main.py`
- Video sẽ tự động rewind khi kết thúc
- FPS được tính toán real-time

## Troubleshooting

### Lỗi import TrafficLightOptimizer
- Module sẽ tự động chuyển sang fallback mode
- Thông báo warning sẽ hiển thị trong console

### Không mở được camera/video
- Kiểm tra đường dẫn file video
- Kiểm tra index webcam
- Đảm bảo camera không bị chiếm bởi ứng dụng khác

### Hiển thị chậm
- Giảm độ phân giải video
- Tăng `--update-interval`
- Sử dụng chế độ headless nếu không cần hiển thị</content>
<parameter name="filePath">d:\GIT REPO\trafffic-density-analysis-system\traffic-density-analysis-system\detection\CAMERA_DISPLAY_README.md