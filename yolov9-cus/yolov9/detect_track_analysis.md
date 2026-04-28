# Phân tích chi tiết các file Detect / Track trong `yolov9-cus/yolov9`

## 1. Mục tiêu tài liệu

Tài liệu này tập trung vào:

- Các file `detect` trong thư mục `yolov9`
- Cách các file này thực hiện phát hiện (detection)
- Các thành phần hỗ trợ detection
- Vị trí và cách xử lý track nếu có trong hệ thống

> Lưu ý: trong thư mục `yolov9` không có file tracker riêng. Tracking được thực hiện bên ngoài ở `detection/engine/tracker.py`.

---

## 2. Các file detect chính trong `yolov9`

### 2.1 `detect.py`

Đây là entrypoint inference chuẩn cho YOLOv9.

#### 2.1.1 Nhập khẩu chính

- `DetectMultiBackend` từ `models.common`
- `LoadImages`, `LoadScreenshots`, `LoadStreams` từ `utils.dataloaders`
- `non_max_suppression`, `scale_boxes`, `xyxy2xywh`, `check_img_size`, `check_file`, `check_imshow`, `increment_path` từ `utils.general`
- `Annotator`, `colors`, `save_one_box` từ `utils.plots`
- `select_device`, `smart_inference_mode` từ `utils.torch_utils`

#### 2.1.2 Luồng inference chính

Hàm `run(...)` gồm các bước:

1. Xác định loại nguồn đầu vào:
   - `image` hay `video` hay `webcam`
   - `source` có thể là file, thư mục, URL, stream, webcam, hoặc file list
2. Tạo thư mục lưu kết quả với `increment_path`
3. Khởi tạo model với `DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)`
4. Kiểm tra kích thước ảnh với `check_img_size(imgsz, s=stride)`
5. Tạo dataloader phù hợp:
   - `LoadStreams` khi webcam/stream
   - `LoadScreenshots` khi chụp màn hình
   - `LoadImages` khi file ảnh/video
6. Warmup model với `model.warmup(...)`
7. Duyệt qua từng frame/image từ dataset:
   - chuẩn hóa ảnh: chuyển sang tensor, nén xuống FP16 nếu cần, chia 255
   - gọi model infer: `pred = model(im, augment=augment, visualize=visualize)`
   - chạy NMS: `non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)`
   - rescale bounding box về kích thước ảnh gốc bằng `scale_boxes(...)`
   - vẽ bbox và nhãn với `Annotator`
   - lưu file `.txt` nếu `save_txt`
   - lưu ảnh/video nếu `save_img`
   - hiển thị ảnh nếu `view_img`
8. In thời gian xử lý và kết quả lưu

#### 2.1.3 Các tham số quan trọng

- `weights`: đường dẫn đến file model (`.pt`, `.onnx`, v.v.)
- `imgsz`: kích thước ảnh đầu vào
- `conf_thres`: ngưỡng confidence
- `iou_thres`: ngưỡng NMS IoU
- `max_det`: số lượng detection tối đa trên một ảnh
- `device`: `cpu` hoặc `cuda`
- `half`: dùng FP16 để tăng tốc inference nếu GPU hỗ trợ
- `dnn`: dùng OpenCV DNN cho ONNX
- `vid_stride`: bỏ frame cho video/stream

#### 2.1.4 Hàm `parse_opt()`

`parse_opt()` xây dựng parser CLI và chuyển các tham số sang dạng dictionary để gọi `run(**vars(opt))`.

---

### 2.2 `detect_dual.py`

`detect_dual.py` có cấu trúc rất giống `detect.py`, nhưng sử dụng một kiểu output khác từ model.

#### 2.2.1 Khác biệt chính so với `detect.py`

Sau khi gọi model, `detect_dual.py` thực hiện:

```python
pred = model(im, augment=augment, visualize=visualize)
pred = pred[0][1]
```

Điều này cho thấy:

- model trả về một output nhiều thành phần.
- `detect_dual.py` chỉ dùng phần tử thứ hai của đầu ra `pred[0]`.
- Do đó, đây có thể là inference cho model "dual" với 2 head hoặc 2 luồng output.

#### 2.2.2 Luồng xử lý còn lại

Tương tự `detect.py`: NMS, scale boxes, vẽ bounding box, lưu ảnh/text.

---

### 2.3 `val.py`

`val.py` không phải script dò tìm trực tiếp dùng cho deploy, nhưng nó thực hiện inference để đánh giá chất lượng model.

#### 2.3.1 Chức năng

- Nạp model với `DetectMultiBackend`
- Dùng `create_dataloader` từ `utils.dataloaders`
- Chạy inference trên tập validation
- Tính mAP, precision, recall, confusion matrix
- Lưu ra `.txt`, `.json` hoặc hình nếu cần

#### 2.3.2 Thao tác quan trọng

- `non_max_suppression(preds, conf_thres, iou_thres, labels=lb, multi_label=True, agnostic=single_cls, max_det=max_det)`
- `scale_boxes(...)` chuyển box về không gian ảnh gốc
- `process_batch(...)` đối chiếu phát hiện với labels để tính metrics

---

## 3. Thành phần hỗ trợ detect

### 3.1 `models/common.py` – `DetectMultiBackend`

Đây là lớp trung tâm của toàn bộ pipeline inference.

#### 3.1.1 Chức năng

- hỗ trợ nhiều backend khác nhau: PyTorch `.pt`, TorchScript, ONNX, ONNX DNN, OpenVINO, TensorRT, CoreML, TF SavedModel, TFLite, Paddle, Triton
- tự động xác định backend dựa trên suffix hoặc URL
- nạp model và metadata class names, stride
- chuyển model sang `fp16` nếu cần
- chuẩn hóa đầu vào và trả về output dạng Tensor

#### 3.1.2 `forward()`

- nếu backend là PyTorch: gọi `self.model(im, augment=augment, visualize=visualize)`
- với các backend khác, thực hiện convert về NumPy và xử lý tương ứng
- với TensorRT, dynamic shape được quản lý bằng `context.set_binding_shape(...)`
- output được chuyển về Tensor với `from_numpy(...)`

#### 3.1.3 `warmup()`

- chạy inference mẫu 1-2 lần để khởi tạo backend
- giúp tăng tốc inference lần đầu

#### 3.1.4 `from_numpy()`

- chuyển NumPy output sang `torch.Tensor`
- đảm bảo output về đúng device

### 3.2 `utils/dataloaders.py`

Các thành phần quan trọng dùng cho detect:

- `IMG_FORMATS`, `VID_FORMATS`: chuỗi định dạng file ảnh và video
- `LoadImages`: dataloader đọc ảnh và video từ file hoặc thư mục
- `LoadStreams`: dataloader đọc webcam/stream đa nguồn
- `LoadScreenshots`: chụp màn hình làm nguồn dữ liệu
- `letterbox(...)`: resize ảnh giữ tỷ lệ + padding, đảm bảo ảnh vào model với kích thước phù hợp

`LoadImages` còn quản lý:

- chế độ `image`, `video`, `stream`
- `frame` index
- vòng lặp xuất tuple `(path, im, im0s, vid_cap, s)`

### 3.3 `utils/general.py`

Các hàm hỗ trợ cần thiết cho detect:

- `check_img_size(imgsz, s=stride)`: điều chỉnh kích thước về bội số của stride
- `non_max_suppression(...)`: loại bỏ các box trùng nhau và giữ phát hiện tốt nhất
- `scale_boxes(im.shape[2:], det[:, :4], im0.shape)`: chuyển tọa độ bounding box về kích thước ảnh gốc
- `xyxy2xywh` / `xywh2xyxy`: chuyển đổi format box
- `check_file`, `check_requirements`, `check_imshow`, `increment_path`

### 3.4 `utils/plots.py`

Dùng để vẽ và ghi kết quả:

- `Annotator`: vẽ bounding box, nhãn, độ tin cậy, màu sắc
- `colors(c, True)`: chọn màu sinh động cho mỗi class
- `save_one_box(xyxy, imc, file=..., BGR=True)`: save ROI crop

---

## 4. Tracking hiện tại trong hệ thống

### 4.1 Track nằm ở đâu?

Trong repository này, file tracking không nằm trong `yolov9` mà ở:

- `detection/engine/tracker.py`

### 4.2 Cách tracker hoạt động

`detection/engine/tracker.py` có lớp `Tracker`:

- khởi tạo `sv.ByteTrack(track_activation_threshold=..., lost_track_buffer=...)`
- nhận danh sách detections từ detector
- chuyển dữ liệu sang `supervision.Detections`
- gọi `self.tracker.update_with_detections(sv_detections)`
- trả về danh sách track đã gán `track_id`

### 4.3 Luồng tích hợp chung

1. YOLOv9 infer ra detections gồm bbox, confidence, class_id, class_name
2. Detections này được gửi tới `Tracker.update(...)`
3. `Tracker` chuyển thành định dạng `supervision` và cập nhật ByteTrack
4. Kết quả trả về chứa `track_id`, `bbox`, `class_name`

### 4.4 Điểm quan trọng

- `yolov9` chỉ cung cấp phần detection
- `Tracker` là lớp middleware ngoài `yolov9`
- Tracking trong repo dựa trên thuật toán ByteTrack thông qua thư viện `supervision`
- Nếu muốn tracking trong luồng `yolov9`, cần nối output `detect.py` vào wrapper tracker này

---

## 5. Tổng kết

### 5.1 `yolov9` thực hiện:

- nạp model với `DetectMultiBackend`
- đọc ảnh/video/stream
- chạy inference và lọc result bằng NMS
- chuyển bounding box về ảnh gốc
- hiển thị/lưu kết quả

### 5.2 `Tracker` hiện tại trong dự án thực hiện:

- gán `track_id` ổn định qua các frame
- dùng `supervision.ByteTrack`
- chỉ nhận input là detections từ detector

### 5.3 Nếu cần mở rộng

- `detect_dual.py` dùng cho model trả về output nhiều đầu
- bạn có thể thêm bước kết nối output `detect.py` với `detection/engine/tracker.py`
- nếu muốn tracking trực tiếp trong `yolov9`, cần bổ sung file mới hoặc mở rộng `detect.py` để gọi tracker
