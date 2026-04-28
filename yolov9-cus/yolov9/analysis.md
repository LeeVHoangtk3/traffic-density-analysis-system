# Phân tích thư mục `yolov9-cus/yolov9`

## 1. Tổng quan

Thư mục `yolov9-cus/yolov9` là một triển khai YOLOv9 dựa trên PyTorch, gồm các script cho huấn luyện, đánh giá và suy luận (inference). Đây là một bản sao/phiên bản của repo YOLOv9 gốc, được tổ chức theo cấu trúc tiêu chuẩn:

- `detect.py`, `detect_dual.py`: inference cho model đơn và model đôi.
- `train.py`, `train_dual.py`, `train_triple.py`: huấn luyện các cấu hình khác nhau.
- `val.py`, `val_dual.py`, `val_triple.py`: đánh giá model.
- `export.py`: xuất model sang định dạng khác.
- `models/`: định nghĩa kiến trúc mạng và backend.
- `utils/`: tiện ích hỗ trợ data loading, xử lý ảnh, loss, metrics, logging, torch utils.
- `requirements.txt`: khai báo thư viện cần cài.

## 2. Công nghệ & thư viện chính

Thư mục sử dụng các công nghệ và thư viện sau:

- Python 3
- PyTorch: xây dựng mô hình, huấn luyện, infer.
- OpenCV (`cv2`): đọc/ghi ảnh, hiển thị, xử lý video.
- NumPy: các phép toán ma trận và chuyển đổi dữ liệu.
- PIL: xử lý ảnh đầu vào.
- Pandas: xử lý dữ liệu hỗ trợ.
- Requests: tải dữ liệu hoặc mô hình nếu cần.
- IPython.display: hiển thị trong notebook.
- `supervision` (được dùng trong tracker ngoài yolov9): theo dõi đối tượng ByteTrack.

## 3. Cấu trúc thư mục chính

### 3.1 Root của `yolov9`

- `README.md`: mô tả YOLOv9, hiệu năng, cách cài đặt, hướng dẫn inference và training.
- `detect.py`: pipeline inference chính.
- `train.py`, `train_dual.py`, `train_triple.py`: huấn luyện model với các chế độ khác nhau.
- `val.py`, `val_dual.py`, `val_triple.py`: đánh giá hiệu năng trên tập dữ liệu.
- `export.py`: xuất mô hình.
- `models/`: chứa các định nghĩa layer, backbone, head, cấu hình model.
- `utils/`: chứa các module hỗ trợ toàn diện.
- `figure/`: dạng ảnh minh họa/benchmark.
- `hubconf.py`: hỗ trợ dùng model với PyTorch Hub.

### 3.2 `models/`

- `common.py`: định nghĩa các module cơ bản và khối xây dựng cho kiến trúc YOLO.
- `yolo.py`: có khả năng chứa định nghĩa mạng YOLOv9 (không đọc toàn bộ, nhưng thông thường đây là nơi cấu hình backbone/head).
- `detect/`, `panoptic/`, `segment/`: modules chuyên biệt cho các nhiệm vụ khác nhau.
- `experimental.py`: tính năng thử nghiệm.
- `tf.py`: hỗ trợ TensorFlow/ONNX hoặc conversion.

### 3.3 `utils/`

- `augmentations.py`: các phép tăng cường ảnh.
- `dataloaders.py`: load ảnh/video/dòng, định dạng ảnh, augmentation, letterbox.
- `general.py`: các hàm chung như NMS, scale boxes, parse config, logging, kiểm tra requirement.
- `plots.py`: vẽ bounding box và lưu ảnh kết quả.
- `torch_utils.py`: quản lý thiết bị, precision, hàm hỗ trợ mô hình.
- `loss.py`, `loss_tal.py`, `loss_tal_dual.py`, `loss_tal_triple.py`: hàm mất mát cho các chế độ model.
- `metrics.py`: tính chỉ số.
- `coco_utils.py`: hỗ trợ COCO.
- `callbacks.py`, `loggers/`: hỗ trợ training theo epoch, ghi log.

## 4. Luồng xử lý chính trong `detect.py`

`detect.py` là entrypoint inference. Luồng logic chính:

1. `parse_opt()`
   - parse argument CLI: weights, source, data, imgsz, thresholds, device, project, name, v.v.

2. `run(...)`
   - xác định kiểu nguồn `source`: ảnh, video, stream, webcam, file list.
   - tạo thư mục lưu kết quả.
   - tải model với `DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)`.
   - tính `stride`, `names`, `pt` từ backend.
   - điều chỉnh kích thước ảnh `imgsz` bằng `check_img_size`.

3. Chọn DataLoader
   - `LoadStreams`, `LoadScreenshots`, hoặc `LoadImages` từ `utils.dataloaders`.
   - `vid_stride` để giảm tốc độ khung hình cho video/stream.

4. Warmup model
   - `model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))`

5. Vòng lặp inference trên từng frame/image
   - chuyển `im` từ NumPy sang Tensor, trên device và chuẩn hoá `im /= 255`.
   - `model(im, augment=augment, visualize=visualize)` để lấy `pred`.
   - `non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)`.
   - rescale bounding box về kích thước gốc `scale_boxes(...)`.
   - tạo nhãn và vẽ bounding box bằng `Annotator`.
   - nếu `save_txt`, xuất kết quả sang file `.txt`.
   - nếu `save_img`, lưu ảnh/video.
   - nếu `view_img`, hiển thị lên màn hình bằng OpenCV.

6. Kết luận
   - ghi thời gian xử lý.
   - báo thư mục lưu kết quả.
   - nếu `update`, gọi `strip_optimizer(weights[0])` để lưu lại model.

## 5. Các thành phần chức năng chính trong YOLOv9

### 5.1 `models/common.py`

Đây là file xây dựng các khối mạng dùng chung. Một số module quan trọng:

- `Conv`: convolution + batchnorm + activation (SiLU mặc định).
- `AConv`: average pooling + Conv cho downsample.
- `ADown`: downsample kết hợp avgpool và maxpool, sau đó concat.
- `RepConvN`: khối RepVGG style, hỗ trợ `deploy` bằng cách fuse BN vào Conv.
- `SP`, `MP`: pooling cơ bản.
- `ConvTranspose`: transpose convolution dùng cho upsample.
- `DWConv`: depthwise convolution.
- `DFL`: Distribution Focal Loss module, dùng cho object detection head.
- `BottleneckBase`: bottleneck chuẩn với skip connection tùy chọn.

Các module này dùng để xây dựng backbone và head của YOLOv9, cho phép reuse các block conv, downsample, repconv, v.v.

### 5.2 `utils/dataloaders.py`

Đây là nơi xử lý đầu vào:

- `IMG_FORMATS`, `VID_FORMATS`: định nghĩa định dạng ảnh/video.
- `LoadImages`: đọc ảnh/video từ file hoặc thư mục, trả về `path, im, im0s, vid_cap, s`.
- `LoadStreams`: đọc nhiều nguồn stream/webcam.
- `LoadScreenshots`: lấy ảnh chụp màn hình.
- `letterbox(...)`: resize giữ tỉ lệ và padding hình ảnh.

### 5.3 `utils/general.py`

Chứa các hàm nền tảng:

- `non_max_suppression(...)`: lọc prediction overlapping.
- `scale_boxes(...)`: chuyển box từ kích thước mạng về kích thước ảnh gốc.
- `xyxy2xywh`, `xywh2xyxy`: chuyển đổi tọa độ box.
- `check_img_size`, `check_file`, `check_requirements`.

### 5.4 `utils/plots.py`

Hàm vẽ bounding box và nhãn trên ảnh:

- `Annotator`: vẽ box, text, màu sắc.
- `colors()`: chọn màu cho class.
- `save_one_box(...)`: lưu vùng crop.

## 6. Vị trí và chức năng Tracker trong repository

Trong repository hiện tại, phần tracker không nằm trực tiếp trong `yolov9-cus/yolov9`, mà ở `detection/engine/tracker.py`.

### 6.1 Tổng quan module tracker

Đường dẫn: `detection/engine/tracker.py`

Nhiệm vụ: theo dõi đối tượng (tracking) dựa trên detections từ detector và trả về danh sách đối tượng có `track_id` cố định.

### 6.2 Phân tích chi tiết `Tracker`

#### `class Tracker`

- `__init__(self, track_activation_threshold=0.25, lost_track_buffer=30)`
  - khởi tạo `self.tracker = sv.ByteTrack(...)`.
  - sử dụng `supervision.ByteTrack` để quản lý tracklet.
  - `track_activation_threshold`: ngưỡng kích hoạt theo dõi.
  - `lost_track_buffer`: số frame giữ track khi mất detection.

- `update(self, detections, frame=None)`
  - mục đích: nhận danh sách detections của detector, trả về detections có `track_id`.
  - nếu `detections` rỗng, trả về `[]`.

#### Bước 1: chuyển đổi định dạng

`detections` trong hệ thống gốc có cấu trúc:

- `det["bbox"]`: [x1, y1, x2, y2]
- `det["confidence"]`: xác suất detection.
- `det["class_id"]`: id class.
- `det["class_name"]`: tên class.

Module xây dựng 3 mảng:

- `xyxy`: danh sách bounding box.
- `confidence`: danh sách confidence.
- `class_id`: danh sách class id.

Và tạo `id_to_name` để map `class_id` -> `class_name`, vì tracker chỉ giữ class id.

#### Bước 2: tạo `supervision.Detections`

```python
sv_detections = sv.Detections(
    xyxy=np.array(xyxy),
    confidence=np.array(confidence),
    class_id=np.array(class_id)
)
```

Đây là đối tượng chuẩn của thư viện `supervision` để truyền vào ByteTrack.

#### Bước 3: cập nhật tracker

```python
tracked_detections = self.tracker.update_with_detections(sv_detections)
```

- `update_with_detections(...)` trả về detections đã track: mỗi detections có `tracker_id`, `xyxy`, `class_id`.
- Tracker sẽ quản lý tracklet, gán cùng `track_id` cho cùng một đối tượng qua nhiều frame.

#### Bước 4: chuyển dữ liệu trở lại format cũ

Với mỗi detection đã track, module chuyển về dict:

- `track_id`: id theo dõi.
- `bbox`: [x1, y1, x2, y2] (ép kiểu int).
- `class_name`: trả về từ `id_to_name`.

Nếu `tracker_id` là `None`, detection đó bị bỏ qua.

#### Kết quả trả về

`results` là danh sách dict:

```python
{
    "track_id": int(tracker_id),
    "bbox": [x1, y1, x2, y2],
    "class_name": id_to_name.get(cls_id, "unknown")
}
```

### 6.3 Đặc điểm quan trọng của Tracker

- Tracker độc lập với YOLOv9: nó chỉ nhận detections đầu vào và không tương tác trực tiếp với mô hình.
- Sử dụng `supervision.ByteTrack`: thuật toán ByteTrack dựa vào IoU và velocity để gán ID.
- Không giữ thông tin `confidence` hay `raw detection` trong kết quả trả về, chỉ giữ bbox và class_name.
- `frame` được truyền vào `update()` nhưng hiện tại không được sử dụng trong hàm.

## 7. Luồng tích hợp giữa YOLOv9 và Tracker trong dự án

1. YOLOv9 thực hiện inference, tạo ra các detection với bbox, confidence, class_id, class_name.
2. Detections này được chuyển sang tracker wrapper ở `detection/engine/tracker.py`.
3. Tracker sử dụng `supervision.ByteTrack` để gán `track_id` cho mỗi đối tượng.
4. Kết quả trả về dùng cho downstream như đếm, phân tích luồng giao thông, gán ID xe qua các frame.

## 8. Ghi chú thêm

- `yolov9-cus/yolov9` là phần code YOLOv9 thuần túy, phù hợp cho inference và training.
- `detection/engine/tracker.py` là phần mở rộng trong hệ thống của bạn, bổ sung chức năng tracking sau khi detect.
- File `README.md` trong `yolov9` mô tả rõ cách cài đặt, demo và benchmark, nhưng không chứa logic tracking.

## 9. Kết luận

Thư mục `yolov9-cus/yolov9` chịu trách nhiệm về việc:

- xây dựng và nạp mô hình YOLOv9,
- xử lý dữ liệu ảnh/video,
- thực hiện inference và sau xử lý bounding box,
- vẽ, lưu và báo cáo kết quả phát hiện.

Phần `tracker` trong `detection/engine/tracker.py` là thành phần bổ sung, chuyển detections từ YOLOv9 thành đối tượng có ID theo dõi, và dùng `supervision.ByteTrack` để đảm bảo nhất quán giữa các frame.
