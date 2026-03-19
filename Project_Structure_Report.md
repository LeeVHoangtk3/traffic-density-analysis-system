# Báo cáo Cấu trúc và Vai trò File của Dự án Phân tích Mật độ Giao thông 
(Traffic Density Analysis System)

Tài liệu này tổng hợp vai trò của từng file và thư mục trong hệ thống để quản lý tiến độ và kiến trúc của dự án. Hệ thống được chia thành các module cốt lõi liên quan đến AI (nhận diện, phân tích) và luồng xử lý dữ liệu.

## 1. Thư mục gốc (Root Directory)
Thư mục gốc chứa các file cấu hình, tài liệu và môi trường của toàn bộ dự án:

- **`README.md`**: File giới thiệu tổng quan về dự án bài tập lớn môn Thực tập Cơ sở (TTCS).
- **`requirements.txt`**: Khai báo toàn bộ các thư viện Python phụ thuộc cần thiết để chạy dự án (như OpenCV, Ultralytics/YOLO, PyTorch, FastAPI, v.v.).
- **`traffic_density_git_project.ipynb`**: Notebook Jupyter dùng để nghiên cứu, thử nghiệm thuật toán hoặc phân tích dữ liệu trực quan trong quá trình phát triển (R&D).
- **`yolov9c.pt`**: File trọng số (weights) của mô hình YOLOv9 được huấn luyện sẵn, đóng vai trò phát hiện đối tượng giao thông.

## 2. Thư mục `detection/`
Đây là thư mục cốt lõi của **Module A (Core AI & Detection)**, đảm nhiệm việc đọc video/camera, nhận diện và phân tích luồng phương tiện, sau đó gửi dữ liệu.

- **`main.py`**: File chạy chính (Entry point) của module nhận diện. File này khởi tạo và liên kết tất cả các tiến trình: đọc video, xử lý frame, nhận diện, theo dõi, đếm số lượng, ước tính mật độ và công bố sự kiện.
- **`camera_engine.py`**: Chịu trách nhiệm khởi tạo kết nối với nguồn video hoặc stream camera (sử dụng OpenCV VideoCapture) và đọc từng frame.
- **`yolov9c.pt`**: Bản copy hoặc symbolic link của trọng số YOLOv9 dùng trực tiếp cho xử lý.

### 2.1. Thư mục `detection/engine/`
Chứa các thành phần logic cốt lõi xử lý từng công đoạn riêng biệt trên mỗi khung hình:

- **`frame_processor.py`**: Tiền xử lý khung hình (preprocessing) như thu phóng (resize) khung ảnh trước khi đưa vào model AI để tối ưu hóa hiệu năng.
- **`detector.py`**: Module bọc ngoài mô hình YOLO. Nhận vào khung hình ảnh và trả về danh sách các đối tượng giao thông phát hiện được (bounding boxes, class, confidence).
- **`tracker.py`**: Thuật toán theo dõi (Multi-object tracking) giúp định danh và theo dõi đa mục tiêu trên nhiều khung hình liên tiếp để theo dõi chính xác quỹ đạo của từng chiếc xe.
- **`zone_manager.py`**: Quản lý các vùng phân tích (zones). Chịu trách nhiệm kiểm tra tọa độ phương tiện xem chúng có đi qua hoặc đi vào các vùng (vạch kẻ) đã định nghĩa trước hay không.
- **`counter.py`**: Bộ đếm lưu lại số lượng phương tiện đi qua các vùng hoặc vạch đích, phân loại theo từng loại xe.
- **`density_estimator.py`**: Ước tính và tính toán mật độ giao thông trên đường tại mỗi thời điểm dựa vào tổng số lượng xe đang được theo dõi trên khung ảnh.
- **`event_generator.py`**: Tổng hợp các dữ kiện (có xe vượt tuyến, mật độ xe, loại xe) để tạo thành các sự kiện (Events) có cấu trúc dữ liệu chuẩn chuẩn bị cho việc gửi báo cáo.

### 2.2. Thư mục `detection/integration/`
Xử lý giao tiếp và tích hợp hệ thống nội bộ hoặc đẩy dữ liệu ra bên ngoài:

- **`publisher.py`**: Đóng vai trò làm Event Publisher, gửi các sự kiện phân tích giao thông và nhận diện (thông qua API/HTTP requests) tới máy chủ Backend để lưu trữ hoặc hiển thị trên Dashboard.

### 2.3. Thư mục `detection/configs_cameras/`
- **`cam_01.json`**: File cấu hình riêng cho Camera số 01. Lưu trữ các cấu hình liên quan đến vị trí camera và đặc biệt là tọa độ các vùng kỹ thuật (zones/lines) được vẽ trên camera này để đo đếm.

---
**Tóm tắt tiến độ Module Nhận diện (Detection Module):** 
Kiến trúc hệ thống đã được phân chia module rất rõ ràng theo đúng nguyên lý thiết kế ứng dụng AI (có đủ các lớp: Core Engine, Tracking, Processing, Publisher). Mã nguồn đã có thể chạy toàn luồng từ việc đọc video -> nhận diện (YOLOv9) -> gửi API.
