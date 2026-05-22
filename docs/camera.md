ĐẶC TẢ CẤU TRÚC HÌNH HỌC NÚT GIAO VÀ PHÂN CHIA VÙNG KIỂM SOÁT (ROI ZONES)
Dựa trên hình ảnh khảo sát thực tế từ góc camera góc rộng cố định (Fixed Wide-Angle Traffic Camera), hành lang giao thông được lựa chọn nghiên cứu là một trục đường một chiều tuyến tính (1-Way Corridor) đóng vai trò gom luồng xe tiến vào một nút giao phân tách ba nhánh (3-Branch Diverging Junction).

Cấu trúc hình học đô thị và sơ đồ phân luồng của ngã rẽ này được phân tích và số hóa phục vụ cho pipeline Thị giác máy tính (YOLOv9 + ByteTrack) và các mô hình Học máy điều khiển pha đèn tín hiệu động bao gồm:

1. Đặc tả 3 Nhánh di chuyển (Directional Turn-Lanes)
Nhánh Rẽ Trái (left_turn): Là nhánh phân tách nằm về phía bên trái của hành lang chính. Luồng xe tại đây sẽ thực hiện cua rẽ để nhập vào một trục đường một chiều song song hoặc vuông góc khác. Đây là nhánh có đặc thù cua hẹp, tốc độ giải tỏa dòng phương tiện chậm và dễ xảy ra xung đột dòng cắt, có sức chứa hạ tầng (capacity) thấp nhất.

Nhánh Đi Thẳng (straight): Là trục hành lang trung tâm nối tiếp tuyến chính từ dưới lên. Nhánh này sở hữu hạ tầng mặt đường rộng, cho phép phương tiện lưu thông với vận tốc cao và năng lực xả xe tối đa.

Nhánh Rẽ Phải (right_turn): Là nhánh rẽ nằm về phía bên phải, hướng dòng phương tiện tách luồng đi vào làn đường gom nội bộ hoặc dải đường dịch vụ đô thị. Luồng này thường có dòng chảy tương đối độc lập và ít xung đột trực diện.

2. Thiết lập 3 Vùng kiểm soát đếm xe (ROI - Region of Interest)
Để số hóa luồng video thô trên bộ nhớ đệm (RAM Processing) mà không cần lưu trữ video gốc, hệ thống thiết lập 3 đa giác vùng đếm độc lập (Polygon ROI Zones) bằng thư viện supervision, đặt chặn ngay tại các vạch ranh giới bắt đầu phân tách dòng của từng nhánh:

Zone_Left (ROI Rẽ Trái): Giám sát toàn bộ các phương tiện bám theo quỹ đạo rẽ trái. Khi bounding box và track_id của phương tiện do ByteTrack quản lý chạm hoặc đi đè qua vạch cắt của zone này, sự kiện zone_entry hướng left sẽ được kích hoạt.

Zone_Straight (ROI Đi Thẳng): Nằm chắn ngang làn đi thẳng trung tâm để kiểm soát xung lực dòng xe trực diện trên trục chính. Kích hoạt sự kiện zone_entry hướng straight.

Zone_Right (ROI Rẽ Phải): Đặt tại cửa ngõ lối rẽ vào đường gom phía bên phải để ghi nhận lưu lượng thoát xe sang làn trong. Kích hoạt sự kiện zone_entry hướng right.

3. Đồng bộ hóa quy hoạch Pha Đèn Tín Hiệu (Traffic Signal Phase Mapping)
Góc quan sát toàn cảnh từ 1 camera này cho phép hệ thống đồng bộ trực quan trạng thái đèn tín hiệu lên luồng hiển thị giao diện thông qua việc phân chia nút giao làm 2 Pha giao thông động (Dynamic Phases) từ kết quả điều khiển của AI:

Pha 1 (Pha Tuyến Chính): Điều khiển đồng thời trạng thái đèn tín hiệu của Làn Đi Thẳng và Làn Rẽ Phải (Trạng thái mặc định: Đèn Xanh).

Pha 2 (Pha Ngả Rẽ Xung Đột): Điều khiển độc lập đèn tín hiệu của Làn Rẽ Trái để cho phép dòng xe cắt ngang qua các luồng đô thị khác một cách an toàn (Trạng thái mặc định: Đèn Đỏ khi Pha 1 bật và ngược lại).