# Chi Tiết Quá Trình Tiền Xử Lý Và Huấn Luyện Mô Hình Machine Learning (Traffic Density Analysis)

Tài liệu này trình bày chi tiết các bước, kỹ thuật được áp dụng và lý do lựa chọn các phương pháp đó trong quá trình xây dựng hệ thống dự báo lưu lượng giao thông (Traffic Predictor).

---

## 1. Phân Tích Dataset Gốc & Tại Sao Phải Làm Sạch Dữ Liệu?

Dữ liệu thô ban đầu được thu thập từ file `Automated_Traffic_Volume_Counts_20260521.csv`. Đây là tập dữ liệu ghi nhận tự động từ các cảm biến/camera đếm xe (sensor) đặt tại nhiều nút giao khác nhau trên hệ thống đường bộ.

Tuy nhiên, do tính chất của các thiết bị IoT và môi trường đo đạc thực tế, **dataset gốc chứa rất nhiều khiếm khuyết và không thể đưa trực tiếp vào mô hình Machine Learning**. Dưới đây là những nguyên nhân, thiếu sót cụ thể bắt buộc chúng ta phải có một pipeline tiền xử lý (như đã viết trong `preprocess.py`):

1. **Lỗi định dạng số liệu:** Dữ liệu đếm xe (Volume - `Vol`) chứa các ký tự phân cách hàng nghìn (ví dụ `"1,200"` thay vì `1200`), và thỉnh thoảng có các ký tự rác. Nếu không loại bỏ dấu phẩy và ép kiểu thành dạng số thực/số nguyên, thư viện phân tích sẽ hiểu đây là chuỗi văn bản (String) và gây crash hệ thống.
2. **Giá trị phi logic (Nhiễu cảm biến):** Tồn tại các giá trị âm (`Vol < 0`) hoặc bị bỏ trống (`NaN`). Lưu lượng giao thông âm là điều bất khả thi về mặt vật lý, thường sinh ra do lỗi chập mạch cảm biến, lỗi truyền tải mạng, hoặc lỗi hệ thống đếm ngược. Nếu mô hình học được các giá trị âm này, trọng số toán học của cây quyết định sẽ bị phá vỡ.
3. **Mốc thời gian bị phân mảnh và không chuẩn xác:** Thời gian ghi nhận bị xé nhỏ thành các cột rời rạc (`Yr`, `M`, `D`, `HH`, `MM`) khiến việc truy vấn chuỗi thời gian khó khăn. Thêm vào đó, cảm biến thường không báo cáo đúng boong mốc giờ chuẩn (ví dụ nó báo lúc 08:14, 08:16 thay vì 08:15). Machine Learning dạng Time-Series yêu cầu nhịp độ thời gian phải cố định.
4. **Dữ liệu trùng lặp (Logical Duplicates):** Tại một số thời điểm, cùng một hướng đi (`Direction`) tại cùng một nút giao (`SegmentID`) lại có 2-3 báo cáo lưu lượng khác nhau. Điều này có thể do hệ thống có nhiều cảm biến dự phòng cùng ping dữ liệu về. Chúng ta phải xử lý gộp (dùng `mean`) để lấy con số đại diện chính xác nhất.
5. **Mất tín hiệu & Đứt gãy chuỗi thời gian:** Cảm biến thường xuyên bị mất điện, rớt mạng hoặc bảo trì, tạo ra các khoảng thời gian "trắng" không có dữ liệu (có thể kéo dài vài giờ). Thuật toán học chuỗi thời gian không thể "nhảy cóc" qua các khoảng trắng này mà cần dữ liệu nối tiếp nhau hoàn toàn.
6. **Mô tả hướng đi phụ thuộc địa lý:** Dataset thô phân loại hướng xe chạy theo la bàn địa lý (NB - Northbound, SB - Southbound, EB, WB). Nếu dùng trực tiếp, mô hình sẽ bị "kẹt" vào thiết kế vật lý của từng ngã tư cụ thể và không thể tổng quát hóa. Ta cần đưa về ngôn ngữ giao thông chung: đi thẳng, rẽ trái, rẽ phải.

---

## 2. Quá Trình Làm Sạch Và Tiền Xử Lý (Data Cleaning & Preprocessing)

Từ những thiếu sót phân tích ở trên, chúng tôi xây dựng quy trình giải quyết như sau:

### a) Lọc và làm sạch các giá trị thô
- **Cách làm:** Loại bỏ các dấu phẩy trong cột lưu lượng (`Vol`), chuyển đổi sang kiểu số nguyên. Lọc bỏ toàn bộ các dòng có chứa dữ liệu lỗi (`NaN`) hoặc giá trị âm (`Vol < 0`).
- **Mục đích:** Giải quyết khiếm khuyết số (1) và (2) của dataset, cung cấp một vector số nguyên tịnh tiến và hợp lệ cho toán học.

### b) Chuẩn hóa thời gian (Time Resampling) về bin 15 phút
- **Cách làm:** Ghép các cột năm, tháng, ngày, giờ, phút thành một đối tượng `timestamp` duy nhất. Kế tiếp, thuật toán làm tròn (`round`) thời gian về các mốc 15 phút chuẩn (00, 15, 30, 45).
- **Mục đích:** Giải quyết khiếm khuyết số (3). Việc gom thành các "bin" 15 phút khử được nhiễu do đồng hồ cảm biến chạy sai lệch vài phút. Tần suất 15 phút cũng là "điểm ngọt" (sweet spot): đủ nhanh để hệ thống kịp thời điều phối giao thông, và đủ dài để lượng xe phản ánh đúng bản chất dòng chảy thay vì nhiễu ngẫu nhiên.

### c) Hợp nhất dữ liệu trùng lặp và phân làn hướng chuẩn
- **Cách làm:** Nhóm các báo cáo cùng tọa độ, cùng thời điểm và tính trung bình (`mean`). Sau đó, xoay trục (pivot) các hướng la bàn (NB, SB, EB, WB) thành 3 hướng di chuyển chuẩn mực: Đi thẳng (`vol_straight`), Rẽ trái (`vol_left`), Rẽ phải (`vol_right`). Ánh xạ này được cấu hình riêng lẻ tùy theo hình học của mỗi SegmentID (ví dụ: Nút giao 138, 72887, 83624).
- **Mục đích:** Khắc phục khiếm khuyết số (4) và (6). Xóa bỏ dữ liệu trùng, đồng thời giúp AI tổng quát hóa được quy luật vận hành của ngã 3/ngã 4 bất kỳ mà không cần quan tâm ngã tư đó đang hướng về phương Bắc hay phương Nam.

### d) Phát hiện chu kỳ đo lường & Nội suy dữ liệu (Time Interpolation)
- **Cách làm:** Tự động cắt các chu kỳ đo lường liên tục (nếu cảm biến mất mạng quá 24h, sẽ tách thành một chu kỳ đo lường mới). Bên trong mỗi chu kỳ, nếu có những khoảng hở ngắn (thiếu dữ liệu vài nhịp 15 phút), thuật toán sẽ nội suy tuyến tính theo thời gian (`interpolate(method='time')`) để điền giá trị ước tính cho chỗ trống, kết hợp điền tiến/điền lùi (`ffill`/`bfill`).
- **Mục đích:** Giải quyết khiếm khuyết số (5). Giúp chuỗi thời gian trở nên liền mạch hoàn hảo, phục vụ cho việc tính toán các đặc trưng như "trung bình trượt" (rolling_mean) hay "lưu lượng quá khứ" (lag) sau này.

---

## 3. Trích Xuất Đặc Trưng (Feature Engineering)

Sau khi có dữ liệu sạch, để mô hình "hiểu" được thời gian và quy luật, ta tiến hành "dịch" thời gian thành các thông số toán học đặc biệt (`traffic_predictor.py`):

### a) Đặc trưng thời gian và Lịch học (Temporal & Calendar Features)
- **Các tính năng:** `hour` (giờ), `day_of_week` (thứ trong tuần).
- **Tính năng phái sinh:** `is_peak_hour` (Giờ cao điểm: 7h-9h và 17h-19h) và `is_weekend` (Ngày cuối tuần).
- **Tại sao dùng:** Giao thông phụ thuộc lớn vào lịch sinh hoạt. Giờ đi làm/tan tầm có lưu lượng đột biến; ngày cuối tuần có quy luật lưu lượng phân tán rải rác trong ngày, hoàn toàn khác ngày làm việc. Việc tạo cờ nhị phân `1/0` (Có/Không phải giờ cao điểm) tạo ra các điểm cắt sắc bén, giúp cấu trúc cây quyết định phân chia nhanh chóng và chính xác.

### b) Đặc trưng Chu kỳ (Cyclic Features)
- **Các tính năng:** `hour_sin`, `hour_cos`, `day_of_week_sin`, `day_of_week_cos`.
- **Tại sao dùng:** Với hệ số đếm thông thường, 23 (11h đêm) và 0 (nửa đêm) là hai con số nằm ở hai cực xa nhau. Nhưng thực tế, chúng chỉ cách nhau 1 giờ. Bằng cách chiếu mốc giờ lên một vòng tròn lượng giác (hàm `sin` và `cos`), mô hình bắt đầu hiểu được tính chất "tuần hoàn" của thời gian: thời gian quay thành một vòng lặp kín chứ không phải một đường thẳng cắt đứt ở 24h.

### c) Đặc trưng Quá khứ (Lag Features & Rolling Windows)
- **Các tính năng:** `lag_1`, `lag_2`, `lag_4` (lưu lượng của 15 phút, 30 phút, 1 giờ trước) và `rolling_mean_3` (trung bình 3 khung giờ gần nhất).
- **Tại sao dùng:** Áp dụng nguyên lý Autocorrelation (Tự tương quan) - tương lai gần chịu chi phối bởi quá khứ gần. Con số dự đoán tốt nhất cho lượng xe 15 phút tới chính là tham chiếu số xe ở 15 phút trước đó. Việc bổ sung `rolling_mean` giúp mô hình thấy được "quán tính" (dòng xe đang có xu hướng dày lên hay vãn đi) để không bị phản ứng thái quá bởi một giá trị lag đột biến.

---

## 4. Quá Trình Huấn Luyện Mô Hình (Model Training)

Hệ thống sử dụng **XGBoost Regressor** làm thuật toán cốt lõi. Có 3 mô hình dự báo hoàn toàn độc lập được huấn luyện, song hành tương ứng với 3 luồng xe (`straight`, `left`, `right`) trong tệp `train.py`.

### a) Tại sao lại chọn XGBoost?
- **Khả năng nắm bắt đường cong phi tuyến:** Lưu lượng giao thông không phải là đường thẳng tăng dần mà dao động rất phức tạp. Cấu trúc Boosting (huấn luyện liên tiếp nhiều cây quyết định bù trừ sai số cho nhau) của XGBoost phù hợp tuyệt vời cho các bề mặt dữ liệu gập ghềnh này.
- **Khả năng xử lý kết cấu đặc trưng hỗn hợp:** Nhận được đầu vào có cả chuỗi sin/cos liên tục, có giá trị boolean nhị phân (giờ cao điểm) và cả số liệu đếm rời rạc (rolling mean) mà không cần phải chuẩn hóa tỉ lệ (scaler) ngặt nghèo như Neural Networks.
- **Chống Học vẹt (Overfitting):** Hệ thống được cấu hình siêu tham số chống nhiễu rất tốt: `subsample=0.8` (mỗi cây chỉ thấy 80% dữ liệu), `colsample_bytree=0.8` (mỗi cây chỉ dùng 80% đặc trưng). Việc này buộc mô hình phải học luật chung, không được phép "ghi nhớ" một thói quen lưu lượng cụ thể của riêng một ngày nào đó.

### b) Chiến lược chia tập dữ liệu (Data Splitting)
- **Cách làm:** **Chronological 80/20 split**. Chúng ta sắp xếp toàn bộ dữ liệu từ quá khứ đến hiện tại. Cắt 80% thời gian đầu làm tập Train, 20% đoạn thời gian cuối làm tập Test. Kết hợp Time Series Cross-Validation khi huấn luyện nội bộ.
- **Tại sao dùng:** Nếu dùng ngẫu nhiên (Random Split, ví dụ trích xuất ngẫu nhiên 20% số dòng ra test), mô hình sẽ dính lỗi chí mạng **Look-ahead Bias (Rò rỉ tương lai)**. Thực tế không bao giờ cho phép lấy dữ liệu ngày thứ Sáu để dạy mô hình cách đoán lưu lượng cho ngày thứ Năm. Chia cắt theo trình tự thời gian là bắt buộc để mô phỏng bối cảnh triển khai thật.

### c) Các độ đo đánh giá (Evaluation Metrics)
- Hệ thống đo lường hiệu năng bằng: **MAE** (Sai số tuyệt đối), **RMSE** (Sai số bình phương), và **MAPE** (Phần trăm sai số).
- **Tại sao dùng:** 
  - `MAE`: Dễ diễn giải. Kết quả "MAE = 10" nghĩa là trung bình mỗi dự báo, mô hình lệch 10 chiếc xe.
  - `RMSE`: Có tính "phạt nặng" các lần đoán sai nghiêm trọng do cơ chế bình phương. Nếu lúc đường vắng đoán sai không sao, nhưng lúc kẹt xe nghiêm trọng mà đoán sai sẽ làm hệ thống rối loạn. RMSE giúp theo dõi mức độ rủi ro này.

### d) Phân loại mức độ ùn tắc tự động
- **Cách làm:** Từ output lưu lượng liên tục của mô hình Regressor, hệ thống dùng một hàm phân ngưỡng để ánh xạ sang dạng lớp (Classification): LOW (<30 xe), MEDIUM (<100 xe), HIGH (<200 xe), SEVERE (>= 200 xe / 15 phút).
- **Tại sao dùng:** Output dạng "Có khoảng 142 xe trong 15 phút tới" rất thiếu trực quan cho cảnh sát giao thông hoặc người tham gia giao thông. Họ chỉ cần biết "Mật độ Cao hay Thấp".
Việc kết hợp huấn luyện Hồi quy (Regression) sau đó mới Phân lớp tĩnh (Static Classification) tốt hơn hẳn so với việc bắt mô hình học Phân lớp trực tiếp từ đầu, vì bài toán Regression tận dụng được hoàn toàn bản chất liên tục, tỉ lệ thuận của số lượng xe chạy trên đường.
