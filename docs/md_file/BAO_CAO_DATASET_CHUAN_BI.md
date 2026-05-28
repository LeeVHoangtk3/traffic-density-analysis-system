# BÁO CÁO CHUẨN BỊ DỮ LIỆU CHO HỆ THỐNG DỰ BÁO LƯU LƯỢNG GIAO THÔNG

## Phân Tích Toàn Diện: Từ Dữ Liệu Thô Đến Tập Dữ Liệu Sạch Phục Vụ Huấn Luyện Mô Hình Dự Báo

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Dữ liệu thô (Raw Dataset)](#2-dữ-liệu-thô-raw-dataset)
3. [Tại sao phải làm sạch dữ liệu?](#3-tại-sao-phải-làm-sạch-dữ-liệu)
4. [Quy trình làm sạch dữ liệu (Data Cleaning Pipeline)](#4-quy-trình-làm-sạch-dữ-liệu-data-cleaning-pipeline)
5. [Dữ liệu sau khi làm sạch (Clean Dataset)](#5-dữ-liệu-sau-khi-làm-sạch-clean-dataset)
6. [So sánh trực quan: Trước và Sau khi làm sạch](#6-so-sánh-trực-quan-trước-và-sau-khi-làm-sạch)
7. [Đặc trưng kỹ nghệ (Feature Engineering)](#7-đặc-trưng-kỹ-nghệ-feature-engineering)
8. [Đánh giá chất lượng dataset sau khi làm sạch](#8-đánh-giá-chất-lượng-dataset-sau-khi-làm-sạch)
9. [Kết luận](#9-kết-luận)

---

## 1. Tổng quan

Hệ thống dự báo lưu lượng giao thông sử dụng bài toán **hồi quy chuỗi thời gian (time-series regression)** để dự đoán số lượng phương tiện sẽ đi qua mỗi hướng (đi thẳng, rẽ trái, rẽ phải) tại một nút giao đô thị trong **15 phút tiếp theo**.

Quá trình chuẩn bị dữ liệu bao gồm 2 giai đoạn chính:

```
┌─────────────────────────┐     Pipeline tiền xử lý     ┌──────────────────────────┐
│   DỮ LIỆU THÔ (RAW)    │ ──────────────────────────▶  │  DỮ LIỆU SẠCH (CLEAN)   │
│                         │    (preprocess.py)           │                          │
│  287 MB • 1,875,154 dòng│                              │  665 KB • 12,525 dòng    │
│  14 cột • toàn thành phố│                              │  10 cột • 9 nút giao     │
└─────────────────────────┘                              └──────────────────────────┘
```

- **Tệp dữ liệu thô:** `data/ml/Automated_Traffic_Volume_Counts_20260521.csv`
- **Tệp dữ liệu sạch:** `ml_service/data/junction_pivot_clean.csv`
- **Script xử lý:** `ml_service/preprocess.py`

---

## 2. Dữ liệu thô (Raw Dataset)

### 2.1. Nguồn gốc

Dữ liệu được thu thập từ hệ thống **Automated Traffic Recorder (ATR)** — hệ thống đếm phương tiện tự động được triển khai tại thành phố New York (NYC), Hoa Kỳ. Dữ liệu bao phủ nhiều năm quan trắc (từ năm 2000 đến 2026) tại hàng trăm phân đoạn đường khác nhau trên toàn bộ 5 quận (borough) của thành phố.

### 2.2. Thông tin tổng quát

| Thông số | Giá trị |
|----------|---------|
| **Tên tệp** | `Automated_Traffic_Volume_Counts_20260521.csv` |
| **Dung lượng** | ~287 MB |
| **Tổng số dòng** | 1,875,154 dòng (không kể header) |
| **Số cột** | 14 cột |
| **Phạm vi thời gian** | 2000 – 2026 |
| **Phạm vi không gian** | 5 quận NYC (Manhattan, Brooklyn, Queens, Bronx, Staten Island) |
| **Số SegmentID riêng biệt** | Hàng trăm phân đoạn đường |
| **Định dạng** | CSV, giá trị bao bọc bởi dấu ngoặc kép `"` |

### 2.3. Danh sách đầy đủ các cột (Features) trong dữ liệu thô

| # | Tên cột | Kiểu dữ liệu gốc | Mô tả chi tiết | Ví dụ giá trị |
|---|---------|-------------------|----------------|----------------|
| 1 | `RequestID` | Chuỗi (String) | Mã định danh yêu cầu đếm xe — mỗi lần triển khai cảm biến tại một vị trí có 1 mã riêng | `"12512"`, `"17657"` |
| 2 | `Boro` | Chuỗi (String) | Tên quận hành chính nơi đặt cảm biến | `"Manhattan"`, `"Queens"`, `"Brooklyn"` |
| 3 | `Yr` | Số nguyên | Năm ghi nhận | `2009`, `2014`, `2025` |
| 4 | `M` | Số nguyên | Tháng ghi nhận (1–12) | `1`, `7`, `12` |
| 5 | `D` | Số nguyên | Ngày ghi nhận (1–31) | `1`, `15`, `28` |
| 6 | `HH` | Số nguyên | Giờ ghi nhận (0–23) | `0`, `8`, `17` |
| 7 | `MM` | Số nguyên | Phút ghi nhận (0–59) | `0`, `15`, `30`, `45` |
| 8 | `Vol` | **Chuỗi (String)** | Số lượng phương tiện đếm được trong khung thời gian 15 phút. **Lưu ý:** giá trị được lưu dưới dạng chuỗi, có thể chứa dấu phẩy phân cách hàng nghìn | `"5"`, `"138"`, `"1,250"` |
| 9 | `SegmentID` | Chuỗi (String) | Mã định danh phân đoạn đường / nút giao — mỗi vị trí địa lý có 1 mã riêng | `"35875"`, `"72887"`, `"83624"` |
| 10 | `WktGeom` | Chuỗi (String) | Tọa độ địa lý dạng WKT (Well-Known Text) — dùng cho bản đồ GIS | `"POINT (990439.6 218452.3)"` |
| 11 | `street` | Chuỗi (String) | Tên đường nơi đặt cảm biến | `"CENTRAL PARK S"`, `"111 STREET"` |
| 12 | `fromSt` | Chuỗi (String) | Tên đường bắt đầu của phân đoạn đo | `"7 AV/C P 7 AV APPR"` |
| 13 | `toSt` | Chuỗi (String) | Tên đường kết thúc của phân đoạn đo | `"CENTER DR/AVE OF THE AMERICAS"` |
| 14 | `Direction` | Chuỗi (String) | Hướng di chuyển của phương tiện theo la bàn | `"NB"`, `"SB"`, `"EB"`, `"WB"`, `"Dead end"` |

### 2.4. Phân bố dữ liệu theo các chiều quan trọng

**Phân bố theo quận (Boro):**

| Quận | Số bản ghi | Tỷ lệ |
|------|-----------|--------|
| Queens | 560,928 | 29.9% |
| Brooklyn | 540,695 | 28.8% |
| Manhattan | 343,555 | 18.3% |
| Bronx | 308,124 | 16.4% |
| Staten Island | 121,852 | 6.5% |

**Phân bố theo hướng di chuyển (Direction):**

| Hướng | Ý nghĩa | Số bản ghi |
|-------|---------|-----------|
| `NB` | North Bound — hướng Bắc | 471,902 |
| `SB` | South Bound — hướng Nam | 465,333 |
| `EB` | East Bound — hướng Đông | 459,955 |
| `WB` | West Bound — hướng Tây | 456,179 |
| Khác | Dead end, BEND, tên đường cụ thể... | ~21,785 |

> **Nhận xét:** 4 hướng la bàn chính (NB, SB, EB, WB) chiếm **98.8%** tổng dữ liệu. Phần còn lại (~1.2%) là các giá trị bất thường hoặc không chuẩn (ví dụ: `"Dead end"`, `"Gowanus Canal Shoreline"`, `"BEND"`) — đây là nhiễu cần được lọc bỏ trong quá trình tiền xử lý.

### 2.5. Mẫu dữ liệu thô (5 dòng đầu tiên)

```
"RequestID","Boro","Yr","M","D","HH","MM","Vol","SegmentID","WktGeom","street","fromSt","toSt","Direction"
"12512","Queens","2013","3","7","4","15","5","55135","POINT (1035363.4 185093.4)","122 PL","SUTTER AV","ROCKAWAY BLVD","SB"
"12512","Queens","2013","3","7","4","30","8","55135","POINT (1035363.4 185093.4)","122 PL","SUTTER AV","ROCKAWAY BLVD","SB"
"12512","Queens","2013","3","7","4","45","8","55135","POINT (1035363.4 185093.4)","122 PL","SUTTER AV","ROCKAWAY BLVD","SB"
"12512","Queens","2013","3","7","5","0","7","55135","POINT (1035363.4 185093.4)","122 PL","SUTTER AV","ROCKAWAY BLVD","SB"
```

---

## 3. Tại sao phải làm sạch dữ liệu?

Dữ liệu thô **không thể sử dụng trực tiếp** cho việc huấn luyện mô hình học máy vì mắc phải **6 vấn đề nghiêm trọng** sau:

### Vấn đề 1: Kiểu dữ liệu sai — Cột `Vol` là chuỗi ký tự

Cột `Vol` (lưu lượng xe) được lưu dưới dạng chuỗi ký tự thay vì số nguyên. Một số giá trị chứa dấu phẩy phân cách hàng nghìn (ví dụ: `"1,250"` thay vì `1250`).

- **Hậu quả:** Mọi phép toán số học (trung bình, tổng, so sánh) đều thất bại. Mô hình không thể huấn luyện.

### Vấn đề 2: Giá trị bất thường — Giá trị âm và NaN

Cảm biến lỗi tạo ra các giá trị âm (ví dụ: `-5` xe) hoặc trả về ô trống (NaN).

- **Hậu quả:** Mô hình học được quy luật sai — có thể dự đoán ra số phương tiện âm.

### Vấn đề 3: Thời gian phân mảnh và lệch nhịp

Thời gian được lưu rải rác trong 5 cột riêng biệt (`Yr`, `M`, `D`, `HH`, `MM`), và phút ghi nhận đôi khi không đều (08:13, 08:17 thay vì 08:15).

- **Hậu quả:** Không thể xây dựng chuỗi thời gian liên tục. Các đặc trưng trễ (lag features) trở nên vô nghĩa nếu khoảng cách giữa 2 dòng liên tiếp không cố định.

### Vấn đề 4: Trùng lặp logic do nhiều cảm biến

Tại cùng một nút giao và cùng khung giờ, nhiều cảm biến có thể báo cáo giá trị khác nhau (ví dụ: cảm biến A đếm 78 xe, cảm biến B đếm 82 xe).

- **Hậu quả:** Nếu dùng `sum()` sẽ thổi phồng lưu lượng thực tế lên gấp đôi.

### Vấn đề 5: Đứt gãy chuỗi thời gian

Cảm biến mất tín hiệu nhiều ngày liên tiếp, tạo ra các khoảng trống lớn trong chuỗi dữ liệu.

- **Hậu quả:** Giá trị `lag_1` (15 phút trước) thực chất phản ánh dữ liệu cách đó vài ngày → đặc trưng quá khứ hoàn toàn sai lệch.

### Vấn đề 6: Hướng di chuyển mã hóa theo la bàn — mất khả năng tổng quát hóa

Dữ liệu gốc dùng ký hiệu la bàn (NB, SB, EB, WB). Cùng ký hiệu `"NB"` tại hai nút giao khác nhau có thể mang ý nghĩa hoàn toàn khác: "đi thẳng" tại nút giao A nhưng "rẽ trái" tại nút giao B.

- **Hậu quả:** Mô hình bị gắn cứng vào cấu hình vật lý của một nút giao cụ thể, không thể triển khai tại nút giao mới.

### Vấn đề 7: Quá nhiều cột không cần thiết

Dữ liệu thô chứa 14 cột, trong đó có nhiều cột không liên quan đến bài toán dự báo lưu lượng (ví dụ: `RequestID`, `Boro`, `WktGeom`, `street`, `fromSt`, `toSt`).

- **Hậu quả:** Lãng phí bộ nhớ (287 MB), tăng thời gian xử lý, và gây nhiễu nếu đưa vào mô hình.

---

## 4. Quy trình làm sạch dữ liệu (Data Cleaning Pipeline)

Toàn bộ quá trình tiền xử lý được thực hiện bởi script `ml_service/preprocess.py`, gồm **4 bước chính** theo thứ tự:

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────────┐    ┌───────────────────┐
│ Bước 1          │    │ Bước 2           │    │ Bước 3               │    │ Bước 4            │
│ Đọc & Lọc cột  │ ─▶ │ Làm sạch Vol     │ ─▶ │ Chuẩn hóa thời gian │ ─▶ │ Gộp trùng lặp     │
│ (8/14 cột)      │    │ (loại NaN, âm)   │    │ (bin 15 phút)        │    │ (mean aggregation) │
└─────────────────┘    └──────────────────┘    └──────────────────────┘    └───────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                         Vòng lặp cho TỪNG SegmentID được chọn                               │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌───────────────────┐  │
│  │ Phát hiện block  │ ─▶│ Pivot Direction  │ ─▶│ Ánh xạ hướng     │ ─▶│ Nội suy + Lọc     │  │
│  │ liên tục (24h)   │   │ thành cột        │   │ la bàn → chuẩn   │   │ block ngắn (<3h)  │  │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘   └───────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Gộp tất cả Segment → CSV sạch   │
│ junction_pivot_clean.csv         │
└──────────────────────────────────┘
```

### Bước 1: Đọc dữ liệu và lọc cột cần thiết

Chỉ đọc **8 trong tổng số 14 cột** từ file CSV thô, loại bỏ hoàn toàn các cột không liên quan (`RequestID`, `Boro`, `WktGeom`, `street`, `fromSt`, `toSt`):

```python
cols_to_use = ['Yr', 'M', 'D', 'HH', 'MM', 'Vol', 'SegmentID', 'Direction']
df = pd.read_csv(raw_csv, usecols=cols_to_use)
```

**Lý do:** Giảm lượng RAM sử dụng từ ~287 MB xuống còn một phần nhỏ, đồng thời loại bỏ thông tin gây nhiễu cho mô hình.

### Bước 2: Làm sạch cột Vol (Lưu lượng xe)

Thực hiện tuần tự 3 thao tác:

```python
# 1. Loại bỏ dấu phẩy phân cách hàng nghìn: "1,250" → "1250"
df['Vol_clean'] = df['Vol'].astype(str).str.replace(',', '')

# 2. Ép kiểu sang số, giá trị không hợp lệ → NaN
df['Vol_clean'] = pd.to_numeric(df['Vol_clean'], errors='coerce')

# 3. Loại bỏ NaN và giá trị âm
df = df.dropna(subset=['Vol_clean'])
df = df[df['Vol_clean'] >= 0]
df['Vol_clean'] = df['Vol_clean'].astype(int)
```

> **Tại sao không nội suy (imputation) thay vì loại bỏ?** Giá trị âm và NaN ở giai đoạn này phản ánh **lỗi phần cứng** của cảm biến, không phải dữ liệu thiếu ngẫu nhiên (missing at random). Nội suy sẽ tạo ra sai lệch mang tính hệ thống. Loại bỏ hoàn toàn là lựa chọn an toàn nhất.

### Bước 3: Chuẩn hóa thời gian

Ghép 5 cột rời rạc thành 1 trường `timestamp` duy nhất, rồi làm tròn về bin 15 phút chuẩn:

```python
# Ghép: 2014 + 07 + 23 + 15 + 17 → "2014-07-23 15:17"
datetime_str = df['Yr'].astype(str) + '-' + df['M'].astype(str).str.zfill(2) + '-' + ...

df['timestamp'] = pd.to_datetime(datetime_str, errors='coerce')

# Làm tròn: 15:17 → 15:15 | 15:08 → 15:15 | 15:00 → 15:00
df['timestamp'] = df['timestamp'].dt.round('15min')
```

> **Tại sao chọn bin 15 phút?** Đây là điểm cân bằng tối ưu: đủ dài để triệt tiêu nhiễu ngắn hạn (1 xe bus đi chậm tạo đỉnh giả), đủ ngắn để phát hiện ùn tắc đột xuất (thường hình thành trong 15–20 phút). Đây cũng là tiêu chuẩn quốc tế trong nghiên cứu giao thông đô thị.

### Bước 4: Gộp trùng lặp logic

Gộp các bản ghi có cùng `(SegmentID, Direction, timestamp)` bằng phép lấy **trung bình (mean)**:

```python
df_clean = (
    df.groupby(['SegmentID', 'Direction', 'timestamp'])['Vol_clean']
    .mean()
    .reset_index()
)
```

> **Tại sao dùng `mean()` thay vì `sum()` hay `max()`?**
> - `sum()` → **sai hoàn toàn** (hai cảm biến đếm cùng một luồng xe, không phải hai luồng riêng biệt)
> - `max()` → thiên vị hệ thống, luôn overestimate
> - `mean()` → ước lượng không chệch (unbiased) theo Luật Số Lớn

### Bước 5: Phát hiện block liên tục và xử lý đứt gãy

Đối với mỗi SegmentID, thuật toán tự động phát hiện các **chu kỳ đo lường liên tục (block)** bằng cách kiểm tra khoảng cách thời gian giữa các mốc liên tiếp:

```python
# Nếu khoảng cách > 24 giờ → điểm bắt đầu block mới
gap_threshold = pd.Timedelta(hours=24)
block_idx = (diffs > gap_threshold).cumsum()
```

Trong phạm vi mỗi block:
1. **Xoay trục (Pivot):** Chuyển cột `Direction` thành các cột riêng biệt (`NB`, `SB`, `EB`, `WB`)
2. **Ánh xạ hướng:** Đổi tên cột la bàn thành hướng giao thông chuẩn (`vol_straight`, `vol_left`, `vol_right`) theo bảng ánh xạ riêng cho từng SegmentID
3. **Resample:** Đảm bảo chuỗi thời gian liên tục 15 phút, nội suy giá trị thiếu bằng `interpolate(method='time')`
4. **Lọc block ngắn:** Loại bỏ block có ít hơn 12 dòng (< 3 giờ) vì không đủ dữ liệu để xây dựng lag features có ý nghĩa

### Bước 6: Ánh xạ hướng di chuyển — Từ la bàn sang hướng giao thông chuẩn

Đây là bước **quan trọng nhất** để mô hình có khả năng tổng quát hóa. Bảng ánh xạ được định nghĩa riêng cho từng nút giao dựa trên cấu hình vật lý thực tế:

| SegmentID | Mô tả | NB | SB | EB | WB |
|-----------|--------|----|----|----|----|
| **138** | Nút giao ngã ba tách làn | `vol_straight` | — | `vol_right` | `vol_left` |
| **72887** | Tuyến trục Đông-Tây lớn | — | — | `vol_straight` | `vol_left` |
| **83624** | Tuyến song hành Nam-Bắc | `vol_straight` | `vol_left` | — | — |

> **Ý nghĩa:** Sau bước ánh xạ, mô hình học được quy luật tổng quát như *"lưu lượng đi thẳng luôn cao hơn lưu lượng rẽ vào giờ cao điểm"* — bất kể nút giao đó quay hướng nào trên bản đồ.

---

## 5. Dữ liệu sau khi làm sạch (Clean Dataset)

### 5.1. Thông tin tổng quát

| Thông số | Giá trị |
|----------|---------|
| **Tên tệp** | `junction_pivot_clean.csv` |
| **Dung lượng** | ~665 KB (giảm **99.77%** so với file thô 287 MB) |
| **Tổng số dòng** | 12,525 dòng (giảm **99.33%** so với 1,875,154 dòng thô) |
| **Số cột** | 10 cột |
| **Số nút giao (SegmentID)** | 9 nút giao |
| **Phạm vi thời gian** | 2009 – 2025 |
| **Tần suất lấy mẫu** | Cố định 15 phút / dòng |

### 5.2. Danh sách đầy đủ các cột (Features) trong dữ liệu sạch

| # | Tên cột | Kiểu dữ liệu | Mô tả chi tiết | Ví dụ giá trị |
|---|---------|---------------|----------------|----------------|
| 1 | `timestamp` | DateTime | Mốc thời gian chuẩn hóa, đã làm tròn về bin 15 phút (00/15/30/45) | `2014-10-15 12:00:00` |
| 2 | `segment_id` | Số nguyên | Mã định danh phân đoạn đường / nút giao | `138`, `35875`, `72887` |
| 3 | `Yr` | Số nguyên | Năm (trích xuất từ timestamp) | `2014` |
| 4 | `M` | Số nguyên | Tháng (1–12) | `10` |
| 5 | `D` | Số nguyên | Ngày (1–31) | `15` |
| 6 | `HH` | Số nguyên | Giờ (0–23) | `12` |
| 7 | `MM` | Số nguyên | Phút (0, 15, 30, hoặc 45) | `0` |
| 8 | `vol_straight` | Số nguyên | Lưu lượng xe đi thẳng (đã ánh xạ từ hướng la bàn) | `210` |
| 9 | `vol_left` | Số nguyên | Lưu lượng xe rẽ trái (đã ánh xạ từ hướng la bàn) | `129` |
| 10 | `vol_right` | Số nguyên | Lưu lượng xe rẽ phải (đã ánh xạ từ hướng la bàn) | `112` |

### 5.3. Phân bố dữ liệu theo SegmentID

| SegmentID | Số dòng | Tỷ lệ |
|-----------|---------|--------|
| 138 | 3,416 | 27.3% |
| 146686 | 2,686 | 21.4% |
| 117626 | 2,104 | 16.8% |
| 35875 | 893 | 7.1% |
| 148076 | 864 | 6.9% |
| 7431 | 864 | 6.9% |
| 68489 | 722 | 5.8% |
| 72608 | 688 | 5.5% |
| 33662 | 288 | 2.3% |

### 5.4. Mẫu dữ liệu sạch (5 dòng đầu tiên)

```
timestamp,segment_id,Yr,M,D,HH,MM,vol_straight,vol_left,vol_right
2009-09-24 12:45:00,35875,2009,9,24,12,45,201,131,120
2009-09-24 13:00:00,35875,2009,9,24,13,0,222,128,108
2009-09-24 13:15:00,35875,2009,9,24,13,15,210,127,113
2009-09-24 13:30:00,35875,2009,9,24,13,30,215,155,111
2009-09-24 13:45:00,35875,2009,9,24,13,45,219,135,120
```

---

## 6. So sánh trực quan: Trước và Sau khi làm sạch

### 6.1. So sánh cấu trúc dữ liệu

| Đặc điểm | Dữ liệu THÔ | Dữ liệu SẠCH |
|-----------|-------------|---------------|
| **Dung lượng** | 287 MB | 665 KB (**giảm 99.77%**) |
| **Số dòng** | 1,875,154 | 12,525 (**giảm 99.33%**) |
| **Số cột** | 14 | 10 |
| **Kiểu cột Vol** | Chuỗi ký tự (`"1,250"`) | Số nguyên (`1250`) |
| **Cấu trúc thời gian** | 5 cột rời rạc (Yr, M, D, HH, MM) | 1 cột `timestamp` chuẩn hóa + 5 cột hỗ trợ |
| **Tần suất lấy mẫu** | Không đều (có thể lệch phút) | Cố định 15 phút |
| **Hướng di chuyển** | La bàn (NB/SB/EB/WB) | Chuẩn hóa (straight/left/right) |
| **Giá trị bất thường** | Tồn tại (âm, NaN, hướng lạ) | Đã loại bỏ hoàn toàn |
| **Chuỗi thời gian** | Bị đứt gãy, không liên tục | Liên tục trong từng block, đã nội suy |

### 6.2. So sánh mẫu dữ liệu cụ thể — Trước và sau khi clean

**TRƯỚC (Dữ liệu THÔ) — Ví dụ tại SegmentID 35875:**

```
"RequestID","Boro",    "Yr","M","D","HH","MM","Vol",  "SegmentID","WktGeom",                   "street",        "fromSt",                  "toSt",                           "Direction"
"17657",    "Manhattan","2014","7","23","15","15","143","35875",    "POINT (990439.6 218452.3)","CENTRAL PARK S","7 AV/C P 7 AV APPR",      "CENTER DR/AVE OF THE AMERICAS",  "EB"
"17657",    "Manhattan","2014","7","23","15","30","125","35875",    "POINT (990439.6 218452.3)","CENTRAL PARK S","7 AV/C P 7 AV APPR",      "CENTER DR/AVE OF THE AMERICAS",  "EB"
"17657",    "Manhattan","2014","7","23","15","45","127","35875",    "POINT (990439.6 218452.3)","CENTRAL PARK S","7 AV/C P 7 AV APPR",      "CENTER DR/AVE OF THE AMERICAS",  "EB"
"17657",    "Manhattan","2014","7","23","16","0", "119","35875",    "POINT (990439.6 218452.3)","CENTRAL PARK S","7 AV/C P 7 AV APPR",      "CENTER DR/AVE OF THE AMERICAS",  "EB"
```

**Các vấn đề nhận thấy:**
- ❌ 14 cột, trong đó 6 cột (`RequestID`, `Boro`, `WktGeom`, `street`, `fromSt`, `toSt`) **không cần thiết** cho dự báo
- ❌ Vol là chuỗi ký tự: `"143"` thay vì số `143`
- ❌ Thời gian nằm rải rác trong 5 cột: `"2014"`, `"7"`, `"23"`, `"15"`, `"15"`
- ❌ Hướng di chuyển là la bàn: `"EB"` — không rõ đây là "đi thẳng" hay "rẽ phải"
- ❌ Chỉ có 1 hướng (`EB`) trong mỗi dòng — không thể nhìn đồng thời 3 hướng

**SAU (Dữ liệu SẠCH) — Cùng SegmentID 35875:**

```
timestamp,           segment_id, Yr,  M, D, HH, MM, vol_straight, vol_left, vol_right
2009-09-24 12:45:00, 35875,      2009, 9, 24, 12, 45, 201,         131,      120
2009-09-24 13:00:00, 35875,      2009, 9, 24, 13, 0,  222,         128,      108
2009-09-24 13:15:00, 35875,      2009, 9, 24, 13, 15, 210,         127,      113
2009-09-24 13:30:00, 35875,      2009, 9, 24, 13, 30, 215,         155,      111
2009-09-24 13:45:00, 35875,      2009, 9, 24, 13, 45, 219,         135,      120
```

**Cải thiện đạt được:**
- ✅ 10 cột gọn gàng, chỉ chứa thông tin cần thiết
- ✅ Lưu lượng là số nguyên: `201`, `131`, `120`
- ✅ Cột `timestamp` chuẩn hóa: `2009-09-24 12:45:00`
- ✅ 3 hướng chuẩn hóa hiển thị đồng thời: `vol_straight=201`, `vol_left=131`, `vol_right=120`
- ✅ Mỗi dòng = 1 bức tranh hoàn chỉnh về lưu lượng 3 hướng tại 1 thời điểm
- ✅ Khoảng cách giữa các dòng cố định 15 phút

---

## 7. Đặc trưng kỹ nghệ (Feature Engineering)

Sau khi có dữ liệu sạch, script `ml_service/traffic_predictor.py` thực hiện thêm bước **Feature Engineering** — trích xuất **10 đặc trưng đầu vào** cho mô hình XGBoost. Các đặc trưng này được chia thành 3 nhóm:

### 7.1. Nhóm 1: Đặc trưng thời gian (Temporal Features) — *"Bây giờ là khi nào?"*

| Đặc trưng | Công thức / Cách tính | Miền giá trị | Vai trò |
|-----------|----------------------|-------------|---------|
| `hour` | Trích từ `timestamp.hour` | 0–23 | Phân biệt giao thông ban ngày vs. ban đêm |
| `day_of_week` | Trích từ `timestamp.dayofweek` | 0–6 (T2→CN) | Phân biệt ngày làm việc vs. cuối tuần |
| `is_peak_hour` | `1` nếu giờ ∈ {7,8,9,17,18,19}, ngược lại `0` | {0, 1} | Đánh dấu giờ cao điểm sáng/chiều |
| `is_weekend` | `1` nếu `day_of_week` ≥ 5, ngược lại `0` | {0, 1} | Đánh dấu Thứ 7 và Chủ nhật |

### 7.2. Nhóm 2: Mã hóa chu kỳ (Cyclical Encoding) — *"23h và 0h nằm cạnh nhau"*

| Đặc trưng | Công thức | Vai trò |
|-----------|-----------|---------|
| `hour_sin` | $\sin(2\pi \times \text{hour} / 24)$ | Mã hóa tính tuần hoàn theo giờ (thành phần sin) |
| `hour_cos` | $\cos(2\pi \times \text{hour} / 24)$ | Mã hóa tính tuần hoàn theo giờ (thành phần cos) |

> **Giải thích:** Biến `hour` (0–23) có tính tuần hoàn nhưng nếu dùng trực tiếp, mô hình coi 23h và 0h cách nhau 23 đơn vị. Chiếu lên vòng tròn đơn vị bằng cặp sin–cos giúp 23h và 0h nằm cạnh nhau (đúng thực tế: chỉ cách 15 phút).

### 7.3. Nhóm 3: Đặc trưng quá khứ (Lag Features) — *"Gần đây đường đông hay vắng?"*

| Đặc trưng | Công thức | Ý nghĩa thực tiễn |
|-----------|-----------|-------------------|
| `lag_1` | `vehicle_count.shift(1)` | Lưu lượng 15 phút trước — **predictor mạnh nhất** |
| `lag_2` | `vehicle_count.shift(2)` | Lưu lượng 30 phút trước — bối cảnh ngắn hạn |
| `lag_4` | `vehicle_count.shift(4)` | Lưu lượng 1 giờ trước — xu hướng trung hạn |
| `rolling_mean_3` | `shift(1).rolling(3).mean()` | Trung bình trượt 3 khung gần nhất — bộ lọc nhiễu |

> **Quan trọng — Phòng tránh rò rỉ dữ liệu (Data Leakage):**
> - `rolling_mean_3` phải **`shift(1)` trước** khi tính rolling → không bao gồm giá trị hiện tại (giá trị cần dự đoán)
> - Lag tính theo nhóm `groupby('segment_id')` → dữ liệu nút giao A không lẫn sang nút giao B

---

## 8. Đánh giá chất lượng dataset sau khi làm sạch

### 8.1. Đánh giá về cấu trúc

| Tiêu chí | Trạng thái | Ghi chú |
|----------|-----------|---------|
| Không còn giá trị NaN | ✅ Đạt | Đã loại bỏ và nội suy hoàn toàn |
| Không còn giá trị âm | ✅ Đạt | Lọc bỏ tại Bước 2 |
| Kiểu dữ liệu đúng | ✅ Đạt | Lưu lượng là số nguyên, timestamp là DateTime |
| Tần suất lấy mẫu đều | ✅ Đạt | Cố định 15 phút trong mỗi block |
| Hướng di chuyển chuẩn hóa | ✅ Đạt | 3 cột: `vol_straight`, `vol_left`, `vol_right` |
| Không có trùng lặp logic | ✅ Đạt | Đã gộp bằng `mean()` |

### 8.2. Đánh giá về khả năng phục vụ mô hình

| Tiêu chí | Trạng thái | Ghi chú |
|----------|-----------|---------|
| Đủ dữ liệu để train | ✅ Đạt | 12,525 dòng × 9 segment → hàng nghìn mẫu/hướng |
| Đủ đa dạng nút giao | ✅ Đạt | 9 nút giao với đặc điểm hạ tầng khác nhau |
| Đủ bao phủ thời gian | ✅ Đạt | Dữ liệu trải dài 2009–2025 (16 năm) |
| Feature Engineering khả thi | ✅ Đạt | Chuỗi liên tục 15 phút → lag features hợp lệ |
| Chia Train/Test theo thời gian | ✅ Đạt | Chronological split 80/20, test từ 2025-01-01 |

### 8.3. Hiệu quả nén dữ liệu

| Chỉ số | Trước (Thô) | Sau (Sạch) | Tỷ lệ giảm |
|--------|------------|-----------|-------------|
| Dung lượng | 287 MB | 665 KB | **99.77%** |
| Số dòng | 1,875,154 | 12,525 | **99.33%** |
| Số cột | 14 | 10 | **28.6%** |

> **Nhận xét:** Quá trình tiền xử lý giảm dung lượng gần **432 lần** nhưng **không mất thông tin hữu ích** cho bài toán dự báo. Sự giảm đáng kể này đến từ việc:
> 1. Loại bỏ các SegmentID không được chọn (chỉ giữ lại các nút giao phù hợp)
> 2. Gộp nhiều bản ghi thô trùng lặp logic thành 1 bản ghi tổng hợp
> 3. Loại bỏ 6 cột không cần thiết (RequestID, Boro, WktGeom, street, fromSt, toSt)
> 4. Pivot 3 dòng (3 hướng riêng lẻ) thành 1 dòng (3 cột hướng song song)

### 8.4. Kết quả huấn luyện mô hình trên dataset sạch

Mô hình XGBoost Regressor được huấn luyện riêng cho 3 hướng di chuyển trên tập dữ liệu sạch `junction_pivot_clean.csv`. Kết quả đánh giá trên tập Test (20% cuối — từ 2025-01-01):

| Hướng di chuyển | Kích thước tập Test | MAE (xe) | RMSE (xe) | MAPE (%) | Accuracy (100% - MAPE) |
|----------------|:------------------:|:--------:|:---------:|:--------:|:---------------------:|
| **Đi thẳng** (`straight`) | 672 | **12.32** | **15.17** | **5.52%** | **94.48%** |
| **Rẽ trái** (`left`) | 672 | **8.61** | **10.49** | **5.86%** | **94.14%** |
| **Rẽ phải** (`right`) | 672 | **7.25** | **8.74** | **5.90%** | **94.10%** |

> **Đánh giá:** Dataset sau khi làm sạch cho phép mô hình đạt độ chính xác **~94%** trên cả 3 hướng di chuyển, chứng tỏ quá trình tiền xử lý đã tạo ra dữ liệu chất lượng cao, đủ tốt để mô hình học được quy luật giao thông thực tế.

---

## 9. Kết luận

Quá trình chuẩn bị dữ liệu cho hệ thống dự báo lưu lượng giao thông là một pipeline gồm nhiều bước xử lý có chủ đích, mỗi bước giải quyết một vấn đề cụ thể của dữ liệu thô:

1. **Dữ liệu thô** (287 MB, 1.87 triệu dòng, 14 cột) chứa đầy đủ thông tin nhưng mắc nhiều vấn đề về kiểu dữ liệu, giá trị bất thường, cấu trúc thời gian, trùng lặp, đứt gãy và mã hóa hướng di chuyển.

2. **Pipeline tiền xử lý** (`preprocess.py`) thực hiện tuần tự: lọc cột → làm sạch Vol → chuẩn hóa thời gian → gộp trùng lặp → phát hiện block → pivot + ánh xạ hướng → nội suy + lọc block ngắn → gộp segment.

3. **Dữ liệu sạch** (665 KB, 12,525 dòng, 10 cột) là kết quả cuối cùng: gọn gàng, chuẩn hóa, liên tục trong từng block, sẵn sàng cho Feature Engineering và huấn luyện mô hình.

4. **Feature Engineering** bổ sung thêm 10 đặc trưng (temporal + cyclical + lag) từ dữ liệu sạch, tạo thành đầu vào hoàn chỉnh cho mô hình XGBoost.

5. **Kết quả:** Mô hình huấn luyện trên dataset sạch đạt **MAPE trung bình ~5.76%** (tương đương accuracy ~94.2%) trên cả 3 hướng di chuyển — chứng minh chất lượng cao của quá trình chuẩn bị dữ liệu.
