# 🚦 Tài Liệu Chi Tiết Thư Mục `scratch`

Thư mục `scratch` trong dự án **Traffic Density Analysis System** chứa các kịch bản (scripts) bổ trợ, được phát triển để phân tích dữ liệu, kiểm tra phát hiện lỗi (debugging) và tự động hóa việc khởi tạo các tài liệu Jupyter Notebook phục vụ cho việc vận hành hệ thống cục bộ cũng như trên môi trường đám mây (Google Colab).

Đây là khu vực dành cho các mã nguồn bổ trợ giúp nhà phát triển và người vận hành quản lý, đánh giá hệ thống một cách trực quan mà không làm ảnh hưởng đến luồng code chính của Backend, Frontend, Detection hay Machine Learning.

---

## 📂 Chi Tiết Từng File Trong Thư Mục `scratch`

### 1. 📊 [analyze_diurnal_stats.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/analyze_diurnal_stats.py)
* **Tác dụng**: Phân tích thống kê lưu lượng giao thông theo giờ trong ngày và theo từng phân đoạn đường.
* **Cách thức hoạt động**:
  * Tệp tin tải dữ liệu sạch đã xử lý từ `ml_service/data/junction_pivot_clean.csv`.
  * Trích xuất giờ (`hour`) từ trường thời gian `timestamp`.
  * Thực hiện gom nhóm (group by) theo mã đoạn đường (`segment_id`) và giờ để tính toán:
    * Lưu lượng trung bình của từng làn đường riêng biệt (`vol_straight` - đi thẳng, `vol_left` - rẽ trái, `vol_right` - rẽ phải).
    * Thống kê lưu lượng tổng cộng của cả nút giao (bao gồm giá trị Nhỏ nhất - Min, Trung bình - Mean, Lớn nhất - Max).
  * Hỗ trợ đắc lực trong việc nghiên cứu phân phối lưu lượng giao thông theo chu kỳ ngày/đêm để phục vụ việc tối ưu hóa pha đèn AI.

### 2. 🔍 [analyze_zeros.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/analyze_zeros.py)
* **Tác dụng**: Kiểm tra và thống kê các giai đoạn không có phương tiện qua lại (giá trị bằng 0) liên tục từ 1 giờ trở lên.
* **Cách thức hoạt động**:
  * Duyệt qua dữ liệu của từng đoạn đường (`segment_id`) và từng làn đường (`vol_straight`, `vol_left`, `vol_right`).
  * Sử dụng kỹ thuật dịch chuyển dữ liệu (`shift()`) kết hợp cộng dồn (`cumsum()`) của Pandas để xác định các chuỗi (streaks) số 0 liên tiếp.
  * Lọc ra các chuỗi có độ dài từ **4 khoảng thời gian 15 phút trở lên** (tương đương $\ge 1$ giờ liên tục).
  * In ra màn hình tỷ lệ % số 0 trên toàn bộ tập dữ liệu, chi tiết mốc thời gian bắt đầu/kết thúc và thời lượng kéo dài của từng chuỗi số 0. Giúp phát hiện sự cố cảm biến hoặc camera bị gián đoạn.

### 3. 🚨 [check_zero_periods.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/check_zero_periods.py)
* **Tác dụng**: Kiểm tra chuyên sâu các khoảng thời gian không có lưu lượng giao thông kéo dài cực hạn (từ 4 giờ trở lên).
* **Cách thức hoạt động**:
  * Hoạt động tương tự `analyze_zeros.py`, tuy nhiên bộ lọc được siết chặt hơn để chỉ tìm kiếm các chuỗi số 0 kéo dài từ **16 khoảng thời gian trở lên** (tương đương $\ge 4$ giờ liên tục).
  * Việc này giúp cô lập và cảnh báo nhanh các trường hợp bất thường nghiêm trọng như: hỏng hóc cảm biến kéo dài, camera bị che khuất hoặc lỗi mất dữ liệu hệ thống trong nhiều giờ liền.

### 4. 🎛️ [generate_notebook.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/generate_notebook.py)
* **Tác dụng**: Tự động sinh ra tệp Jupyter Notebook điều khiển hệ thống [run_system.ipynb](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/run_system.ipynb) ở thư mục gốc.
* **Cách thức hoạt động**:
  * Lưu trữ cấu trúc JSON hoàn chỉnh của Jupyter Notebook với thiết kế UI cực kỳ hiện đại (sử dụng CSS inline gradient, bo góc, bóng mờ chuyên nghiệp).
  * Tích hợp sẵn các mã nguồn Python để:
    * Kiểm tra sức khỏe hệ thống (thư viện cài đặt, khả dụng của GPU CUDA và ping kiểm tra MongoDB Atlas).
    * Định nghĩa lớp quản lý tiến trình `TrafficSystemManager` giúp khởi chạy ngầm toàn bộ các dịch vụ (Backend, Detection, Frontend, ML Service, Pipeline đồng bộ) và xuất log ra thư mục riêng biệt.
    * Cung cấp giao diện trực quan hóa dữ liệu lưu lượng giao thông thời gian thực bằng biểu đồ `matplotlib` / `seaborn` trực tiếp từ database MongoDB Atlas.

### 5. ☁️ [update_notebook.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/update_notebook.py)
* **Tác dụng**: Tự động sinh ra tệp Jupyter Notebook tích hợp chạy trên Google Colab [colab_run.ipynb](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/colab_run.ipynb) ở thư mục gốc.
* **Cách thức hoạt động**:
  * Tạo tệp notebook chuyên dùng để huấn luyện và chạy thử nghiệm hệ thống trên đám mây Google Colab.
  * Tự động hóa các bước cài đặt phức tạp trên Colab:
    * Kết nối Google Drive để đồng bộ video và tệp trọng số mạng nơ-ron YOLOv9.
    * Clone mã nguồn từ GitHub nhánh `hoang` và thiết lập biến môi trường kết nối database Atlas.
    * Tự động loại bỏ thư viện xung đột (`setuptools` trên Python 3.12) và cài đặt `pymongo`, `dnspython`.
    * Khởi chạy Backend và Detection ngầm, thực hiện dịch chuyển thời gian thực tế để đồng bộ hóa dữ liệu lịch sử và seed dữ liệu.

### 6. 📖 [read_notebook_output.py](file:///D:/GIT%20REPO/trafffic-density-analysis-system/traffic-density-analysis-system/scratch/read_notebook_output.py)
* **Tác dụng**: Trích xuất nhanh và đọc kết quả thực thi của một Jupyter Notebook trực tiếp từ giao diện dòng lệnh (Terminal).
* **Cách thức hoạt động**:
  * Script thực hiện đọc tệp notebook huấn luyện mô hình (ví dụ: `ml_service/data_evaluation.ipynb`).
  * Phân tích tệp dưới dạng cấu trúc JSON, duyệt qua từng cell code.
  * In ra 3 dòng mã đầu tiên của mỗi cell để định vị vùng xử lý.
  * Trích xuất và in toàn bộ nội dung output dạng văn bản (`text`) hoặc thông tin định dạng hình ảnh/đồ thị (`image/png`) đã được tạo ra sau khi cell được thực thi. Điều này giúp đánh giá kết quả huấn luyện mô hình nhanh chóng mà không cần mở trình duyệt.

---

## 🎯 Tổng kết

Thư mục `scratch` đóng vai trò như một **bộ công cụ kỹ sư (Engineer Toolkit)** hỗ trợ đắc lực cho việc phát triển, kiểm thử, phân tích dữ liệu lưu lượng giao thông lịch sử và tự động cấu hình các kịch bản chạy thử nghiệm trên cả local cũng như cloud.
