# Phân Tích Phần Tính Thời Gian Đèn Xanh 15 Phút và Front-End

## 1. Phần Tính Thời Gian Đèn Xanh 15 Phút

### Tổng Quan
Phần tính thời gian đèn xanh được triển khai trong file `ml_service/train.py`, cụ thể là trong phần "SECTION 4: GREEN LIGHT LOGIC". Logic này dựa trên dữ liệu lưu lượng giao thông đã được xử lý và dự đoán để điều chỉnh thời gian đèn xanh cho mỗi khoảng thời gian 15 phút.

### Dữ Liệu Đầu Vào
- File CSV: `data/traffic_after_train.csv` chứa dữ liệu sau khi đào tạo mô hình, bao gồm:
  - `traffic_volume`: Lưu lượng giao thông (số xe)
  - `predicted_vehicle_count`: Dự đoán số xe
  - Các cột khác như `holiday`, `timestamp`, v.v.

### Logic Tính Toán
1. **Thời Gian Cơ Bản**: Mỗi khoảng thời gian bắt đầu với 45 giây đèn xanh.

2. **Điều Chỉnh Dựa Trên Lưu Lượng**:1
   - Tính trung bình lưu lượng (`avg = df['traffic_volume'].mean()`)
   - Cho mỗi bản ghi, tính phần trăm chênh lệch: `delta = ((traffic_volume - avg) / avg) * 100`
   - Điều chỉnh thời gian: `t = t + max(((delta // 10) * 5), -15)`
     - Mỗi 10% chênh lệch tăng/giảm 5 giây
     - Giới hạn giảm tối đa 15 giây

3. **Điều Chỉnh Cho Ngày Lễ**:
   - Nếu là ngày lễ (`holiday` không phải "None", "", hoặc None), tăng thêm 10 giây.

4. **Công Thức Tổng Quát**:
   ```
   time_green_light = 45 + adjustment_based_on_traffic + holiday_bonus
   ```

### Ví Dụ
Giả sử lưu lượng trung bình là 100 xe:
- Nếu lưu lượng hiện tại là 120 xe (tăng 20%):
  - delta = 20
  - adjustment = max((20 // 10) * 5, -15) = max(10, -15) = 10
  - Nếu là ngày lễ: time_green_light = 45 + 10 + 10 = 65 giây
- Nếu lưu lượng hiện tại là 80 xe (giảm 20%):
  - delta = -20
  - adjustment = max((-20 // 10) * 5, -15) = max(-10, -15) = -10
  - time_green_light = 45 - 10 = 35 giây

### Lưu Trữ Kết Quả
Kết quả được lưu lại vào `data/traffic_after_train.csv` với cột mới `time-green-light`.

## 2. Phần Front-End

### Tổng Quan
Front-end của hệ thống được xây dựng bằng React và nằm trong thư mục `traffic-frontend/`. Đây là giao diện người dùng để hiển thị và tương tác với dữ liệu phân tích mật độ giao thông.

### Cấu Trúc Thư Mục
```
traffic-frontend/
├── public/
│   ├── index.html          # File HTML chính
│   ├── manifest.json       # Cấu hình PWA
│   └── robots.txt          # Cấu hình SEO
├── src/
│   ├── App.css             # CSS chính cho ứng dụng
│   ├── App.js              # Component chính của ứng dụng
│   ├── App.test.js         # File test cho App.js
│   ├── index.css           # CSS toàn cục
│   ├── index.js            # Điểm vào của React
│   ├── reportWebVitals.js  # Báo cáo hiệu suất
│   └── setupTests.js       # Cấu hình testing
└── package.json            # Quản lý dependencies và scripts
```

### Công Nghệ Sử Dụng
- **React**: Framework JavaScript để xây dựng giao diện người dùng
- **CSS**: Styling cho các component
- **Jest**: Framework testing (cấu hình trong setupTests.js)

### Chức Năng Chính
1. **Hiển Thị Dữ Liệu**: Hiển thị thông tin về mật độ giao thông, dự đoán, và thời gian đèn xanh
2. **Tương Tác Người Dùng**: Cho phép người dùng xem báo cáo, biểu đồ, và điều khiển hệ thống
3. **Responsive Design**: Thiết kế đáp ứng cho các thiết bị khác nhau

### Scripts Quan Trọng
- `npm start`: Chạy ứng dụng ở chế độ development
- `npm test`: Chạy các test
- `npm run build`: Build ứng dụng cho production
- `npm run eject`: Eject khỏi Create React App (không khuyến nghị)

### Tích Hợp Với Backend
Front-end kết nối với backend thông qua API để lấy dữ liệu thời gian thực về:
- Lưu lượng giao thông
- Dự đoán mật độ
- Thời gian đèn xanh được tính toán
- Thông tin camera và video

### Giao Diện Chính
- **Dashboard**: Tổng quan về tình trạng giao thông
- **Báo Cáo**: Hiển thị dữ liệu phân tích và dự đoán
- **Cài Đặt**: Cấu hình hệ thống và tham số

## Kết Luận
Phần tính thời gian đèn xanh 15 phút sử dụng thuật toán đơn giản nhưng hiệu quả dựa trên dữ liệu lưu lượng, trong khi front-end cung cấp giao diện thân thiện để người dùng tương tác với hệ thống phân tích mật độ giao thông.