Tổng quan

  - Kích thước: 286,977,874 bytes, 1,875,154 dòng, 14 cột.
  - Thời gian dữ liệu: từ 2000-01-01 00:15 đến 2026-02-03 23:45.
  - Cột chính: Vol là lưu lượng xe; Yr/M/D/HH/MM là thời gian; Boro, SegmentID, WktGeom, street/fromSt/toSt, Direction là thông tin
    vị trí/hướng.
  - Không có label “traffic density” trực tiếp. Nếu dùng cho ML, nên coi Vol là target regression hoặc tự tạo nhãn mật độ từ Vol.

  Chất lượng dữ liệu

  - Thiếu dữ liệu rất ít: chỉ toSt thiếu 1,246 dòng, khoảng 0.07%.
  - Vol có 15,257 giá trị dạng 1,147, 1,218... Nếu parse số thô sẽ lỗi, nhưng sau khi bỏ dấu phẩy thì parse được toàn bộ.
  - Sau khi chuẩn hóa Vol: min -1, median 59, mean 113.73, p95 399, p99 942, max 5425.
  - Có 96,278 dòng Vol = 0, khoảng 5.13%; cần kiểm tra có phải lưu lượng thật bằng 0 hay lỗi đo.
  - Có đúng 1 dòng Vol = -1; nên loại hoặc set null.
  - Không có dòng trùng hoàn toàn, nhưng có 5,146 khóa logic trùng theo RequestID + SegmentID + Direction + timestamp, với Vol khác
    nhau. Cần quyết định aggregate bằng mean, sum, hoặc giữ theo rule nghiệp vụ.
  - Hầu hết dữ liệu theo mốc 15 phút 0/15/30/45, nhưng có 2,871 dòng ở phút 10/20/40/50; nên resample hoặc xử lý riêng.

  Phân bố đáng chú ý

  - Borough: Queens 560,928, Brooklyn 540,695, Manhattan 343,555, Bronx 308,124, Staten Island 121,852.
  - SegmentID: 3,391 unique; WktGeom: 3,746 unique.
  - Direction: chủ yếu NB/SB/EB/WB; EW và NS rất hiếm.
  - Lưu lượng theo giờ hợp lý: thấp nhất khoảng 2h-4h, cao nhất khoảng 14h-17h.
  - Dữ liệu theo năm không đều: các năm 2000, 2006, 2007, 2020, 2026 ít hơn rõ rệt; 2026 chỉ đến 2026-02-03.

  Đánh giá dùng cho ML
  Dữ liệu dùng được, nhưng cần tiền xử lý trước khi train:

  1. Ghép Yr/M/D/HH/MM thành datetime.
  2. Chuẩn hóa Vol bằng cách bỏ dấu phẩy hàng nghìn, rồi cast numeric.
  3. Loại hoặc flag dòng Vol = -1.
  4. Xử lý duplicate key theo rule cố định.
  5. Xử lý các mốc phút ngoài 15 phút.
  6. Không nên random split đơn giản nếu dự đoán tương lai; nên split theo thời gian, ví dụ train đến 2024, test 2025-2026.
  7. Cẩn thận với RequestID: đây có thể là ID đợt đo, dễ gây leakage nếu đưa thẳng vào model.
  8. WktGeom không phải lat/lon dạng độ; nếu vẽ bản đồ hoặc tính khoảng cách cần biết CRS/transform đúng.

  Kết luận: dataset khá sạch và có tín hiệu thời gian/không gian tốt cho bài toán dự đoán Vol, nhưng chưa phải “traffic density”
  hoàn chỉnh nếu chưa chuẩn hóa theo năng lực đường/làn xe hoặc tự định nghĩa class mật độ.