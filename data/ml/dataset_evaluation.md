# Danh gia dataset: Automated Traffic Volume Counts

File du lieu: `Automated_Traffic_Volume_Counts_20260521.csv`

Ngay tao bao cao: `2026-05-21`

## 1. Tom tat

Dataset nay la tap du lieu dem luu luong xe theo tung doan duong, huong di va thoi diem. Moi dong tuong ung voi mot ban ghi dem xe tai mot `SegmentID`, mot `Direction` va mot moc thoi gian cu the.

Cot quan trong nhat la `Vol`, the hien so luong xe dem duoc trong khoang thoi gian tuong ung. Dataset phu hop de xay dung bai toan du doan luu luong giao thong, phan loai muc do giao thong, hoac phan tich mau hinh giao thong theo thoi gian va khong gian.

Tuy nhien, dataset nay chua phai la dataset "mat do giao thong" hoan chinh theo nghia vat ly. Dataset khong co so lan duong, toc do, do dai doan duong, suc chua duong, occupancy hay khoang cach giua xe. Neu muc tieu la "traffic density", can tu dinh nghia nhan tu `Vol` hoac bo sung them metadata ve ha tang duong.

Danh gia tong quan:

- Dataset lon, du de huan luyen mo hinh ML: `1,875,154` dong.
- Co tin hieu thoi gian tot: nam, thang, ngay, gio, phut.
- Co tin hieu khong gian tot: borough, segment, geometry, street, huong di.
- Chat luong schema kha on dinh, it missing value.
- Can tien xu ly truoc khi train: chuan hoa `Vol`, xu ly duplicate logic, tao datetime, xu ly outlier va tranh leakage.
- Huong ML nen bat dau: du doan `Vol_clean` dang regression, sau do moi tao lop mat do neu can.

## 2. Kich thuoc va pham vi du lieu

| Chi so | Gia tri |
| --- | ---: |
| Kich thuoc file | `286,977,874` bytes |
| So dong | `1,875,154` |
| So cot | `14` |
| Moc thoi gian som nhat | `2000-01-01 00:15` |
| Moc thoi gian moi nhat | `2026-02-03 23:45` |
| So `RequestID` khac nhau | `2,236` |
| So `SegmentID` khac nhau | `3,391` |
| So `WktGeom` khac nhau | `3,746` |
| So borough | `5` |
| So huong di | `6` |

## 3. Mo ta cac cot

| Cot | Y nghia | Kieu nen dung sau khi xu ly | Vai tro trong ML |
| --- | --- | --- | --- |
| `RequestID` | Ma dot yeu cau/khao sat | ID hoac categorical | Can dung can than vi co the gay leakage |
| `Boro` | Ten borough | Categorical | Feature huu ich |
| `Yr` | Nam | Integer | Dung tao datetime, co the dung lam feature |
| `M` | Thang | Integer | Dung tao datetime, feature mua vu |
| `D` | Ngay trong thang | Integer | Dung tao datetime |
| `HH` | Gio | Integer | Feature rat quan trong |
| `MM` | Phut | Integer | Feature moc thoi gian |
| `Vol` | Luu luong xe dem duoc | Numeric sau khi clean | Target chinh |
| `SegmentID` | Ma doan duong | Categorical | Feature khong gian quan trong |
| `WktGeom` | Hinh hoc dang WKT point | Geometry/string | Co the parse thanh toa do |
| `street` | Ten duong | Categorical/text | Feature huu ich nhung can chuan hoa |
| `fromSt` | Duong/cot moc bat dau | Categorical/text | Feature bo sung |
| `toSt` | Duong/cot moc ket thuc | Categorical/text | Co missing value |
| `Direction` | Huong di | Categorical | Feature quan trong |

## 4. Do phu thoi gian

Dataset co du lieu tu nam `2000` den dau nam `2026`, nhung phan bo theo nam khong deu.

| Nam | So dong |
| ---: | ---: |
| 2000 | `1,904` |
| 2006 | `664` |
| 2007 | `8,130` |
| 2008 | `32,482` |
| 2009 | `122,851` |
| 2010 | `132,016` |
| 2011 | `120,249` |
| 2012 | `128,222` |
| 2013 | `128,762` |
| 2014 | `130,754` |
| 2015 | `124,428` |
| 2016 | `129,617` |
| 2017 | `123,901` |
| 2018 | `98,961` |
| 2019 | `115,730` |
| 2020 | `40,224` |
| 2021 | `85,810` |
| 2022 | `78,652` |
| 2023 | `85,106` |
| 2024 | `95,203` |
| 2025 | `82,368` |
| 2026 | `9,120` |

Nhan xet:

- Cac nam `2000`, `2006`, `2007` co rat it du lieu.
- Nam `2026` chi co du lieu den `2026-02-03`, khong dai dien cho ca nam.
- Nam `2020` co the co hanh vi giao thong bat thuong do anh huong dai dich.
- Neu muc tieu la du doan tuong lai, khong nen chia train/test ngau nhien theo dong.
- Nen chia theo thoi gian, vi du train tren cac nam cu va test tren `2025-2026`.

## 5. Do phu khong gian

Phan bo theo borough:

| Borough | So dong | Ty le |
| --- | ---: | ---: |
| Queens | `560,928` | `29.91%` |
| Brooklyn | `540,695` | `28.83%` |
| Manhattan | `343,555` | `18.32%` |
| Bronx | `308,124` | `16.43%` |
| Staten Island | `121,852` | `6.50%` |

Nhan xet:

- Dataset bao phu du 5 borough.
- Queens va Brooklyn chiem gan 59% du lieu.
- Staten Island co so dong it hon ro ret, nen can danh gia metric rieng cho borough nay.
- Neu train model chung, mo hinh co the hoc tot hon cho Queens/Brooklyn va kem hon cho borough it du lieu.

Top `SegmentID` co nhieu ban ghi:

| SegmentID | So dong |
| ---: | ---: |
| `72887` | `13,398` |
| `83624` | `11,317` |
| `34332` | `11,038` |
| `89528` | `9,512` |
| `146375` | `9,198` |
| `62117` | `8,653` |
| `95433` | `8,170` |
| `156016` | `7,587` |
| `62211` | `7,124` |
| `105839` | `6,737` |

Top ten duong xuat hien nhieu:

| Street | So dong |
| --- | ---: |
| `BROADWAY` | `30,173` |
| `111 STREET` | `17,876` |
| `LINDEN BOULEVARD` | `16,193` |
| `FLATBUSH AVENUE` | `15,067` |
| `SUTTER AVENUE` | `13,813` |
| `3 AVENUE` | `13,371` |
| `WHITE PLAINS ROAD` | `12,490` |
| `LINDEN BLVD` | `11,695` |
| `WEST END AVENUE` | `11,472` |
| `EAST 174 ST BRIDGE` | `10,248` |

Luu y ve hinh hoc:

- `WktGeom` la WKT point, khong phai cap lat/lon truc tiep.
- Gia tri toa do co ve la he toa do projected, nen neu can ve ban do hoac tinh khoang cach thi phai xac dinh CRS va transform toa do.
- `SegmentID` khong hoan toan 1-1 voi `WktGeom`: co `261` segment co nhieu geometry.
- Co `1` geometry gan voi nhieu segment.

## 6. Phan bo huong di

| Direction | So dong |
| --- | ---: |
| `NB` | `474,645` |
| `SB` | `469,877` |
| `EB` | `463,384` |
| `WB` | `460,720` |
| `EW` | `3,564` |
| `NS` | `2,964` |

Nhan xet:

- Bon huong chinh `NB`, `SB`, `EB`, `WB` kha can bang.
- `EW` va `NS` rat hiem, co the can gom nhom hoac xu ly rieng tuy model.
- `Direction` nen duoc dua vao feature vi huong di co anh huong lon den luu luong.

## 7. Phan bo `Vol`

Sau khi bo dau phay hang nghin trong `Vol`, tat ca gia tri deu parse duoc thanh so.

| Thong ke | Gia tri `Vol` |
| --- | ---: |
| Count | `1,875,154` |
| Min | `-1` |
| P25 | `18` |
| Median | `59` |
| Mean | `113.73` |
| P75 | `135` |
| P90 | `253` |
| P95 | `399` |
| P99 | `942` |
| Max | `5,425` |

Nhan xet:

- `Vol` lech phai manh: mean cao hon median kha nhieu.
- Phan lon ban ghi co luu luong vua/thap, nhung co mot so diem rat cao.
- Neu dung regression, nen danh gia bang MAE va RMSE; khong nen chi dung RMSE.
- Neu phan loai muc do giao thong, nguong nen dua theo quantile hoac theo rule nghiep vu.

Mot so dieu kien dang chu y:

| Dieu kien | So dong | Ty le |
| --- | ---: | ---: |
| `Vol` co dau phay hang nghin, vi du `1,147` | `15,257` | `0.81%` |
| `Vol = 0` | `96,278` | `5.13%` |
| `Vol < 0` | `1` | `<0.01%` |

Khuyen nghi:

- Chuan hoa `Vol` bang cach bo dau phay truoc khi cast numeric.
- Dong `Vol = -1` nen loai bo hoac set thanh missing.
- Khong nen mac dinh loai `Vol = 0`, vi co the la gia tri hop le vao dem khuya hoac duong vang.
- Cac gia tri rat cao can duoc kiem tra theo segment/duong truoc khi xem la outlier.

## 8. `Vol` theo borough

| Borough | So dong | Mean `Vol` | Median `Vol` | P95 `Vol` | Max `Vol` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Queens | `560,928` | `103.54` | `54` | `379` | `2,187` |
| Brooklyn | `540,695` | `96.92` | `50` | `288` | `4,924` |
| Manhattan | `343,555` | `152.28` | `101` | `488` | `5,425` |
| Bronx | `308,124` | `128.87` | `57` | `566.85` | `4,941` |
| Staten Island | `121,852` | `88.28` | `46` | `358` | `938` |

Nhan xet:

- Manhattan co mean va median cao nhat.
- Bronx co P95 cao so voi median, cho thay co cac hanh lang giao thong rat lon.
- Staten Island co max thap hon va so dong it hon.
- Nen bao cao metric model theo tung borough, khong chi dung metric tong.

## 9. `Vol` theo gio

| Gio | Mean `Vol` | Median `Vol` | P95 `Vol` |
| ---: | ---: | ---: | ---: |
| 0 | `59.50` | `27` | `234` |
| 1 | `40.63` | `17` | `167` |
| 2 | `30.29` | `12` | `126` |
| 3 | `26.90` | `11` | `113` |
| 4 | `34.30` | `13` | `139` |
| 5 | `58.50` | `22` | `229` |
| 6 | `101.37` | `43` | `404` |
| 7 | `134.82` | `72` | `478` |
| 8 | `143.45` | `84` | `478` |
| 9 | `136.47` | `82` | `455` |
| 10 | `134.47` | `83` | `442` |
| 11 | `139.21` | `88` | `456` |
| 12 | `145.21` | `93` | `470` |
| 13 | `150.90` | `97` | `490` |
| 14 | `161.17` | `104` | `515` |
| 15 | `169.14` | `110` | `537` |
| 16 | `170.50` | `111` | `539` |
| 17 | `169.92` | `110` | `537` |
| 18 | `161.05` | `102` | `516` |
| 19 | `145.31` | `89` | `486` |
| 20 | `126.69` | `74` | `433` |
| 21 | `110.69` | `61` | `389` |
| 22 | `97.64` | `50` | `357` |
| 23 | `81.06` | `39` | `305` |

Nhan xet:

- Luu luong thap nhat vao khoang `02:00-04:00`.
- Luu luong tang nhanh tu `05:00-08:00`.
- Trung binh cao nhat vao khoang `15:00-17:00`.
- Nen encode gio theo dang cyclic: `sin(hour)` va `cos(hour)`.

## 10. Van de chat luong du lieu

### 10.1 Missing value

Chi co cot `toSt` bi thieu:

| Cot | So dong thieu | Ty le |
| --- | ---: | ---: |
| `toSt` | `1,246` | `0.07%` |

Khuyen nghi:

- Khong can loai dong chi vi thieu `toSt`.
- Co the fill bang `UNKNOWN` neu dung categorical encoder.
- Nen giu lai dong vi cac cot quan trong khac van day du.

### 10.2 Format so trong `Vol`

Co `15,257` gia tri `Vol` o dang co dau phay hang nghin, vi du:

```text
1,147
1,179
1,218
```

Neu parse truc tiep bang `int()` thi se loi. Can clean:

```text
Vol_clean = int(Vol.replace(",", ""))
```

Sau buoc nay, tat ca gia tri `Vol` deu parse duoc.

### 10.3 Gia tri am trong `Vol`

Co dung `1` dong `Vol = -1`.

| RequestID | Boro | Ngay | Gio | SegmentID | Street | Direction | Vol |
| --- | --- | --- | --- | ---: | --- | --- | ---: |
| `12501` | Bronx | `2010-09-21` | `00:00` | `145593` | `2ND EXIT FROM MALL TO BAYCHESTER AVE` | `WB` | `-1` |

Khuyen nghi:

- Loai dong nay, hoac
- Set `Vol_clean` thanh missing roi xu ly sau.

Voi chi 1 dong loi, cach don gian va an toan la loai bo.

### 10.4 Moc phut khong chuan 15 phut

Phan lon du lieu nam o cac moc `00`, `15`, `30`, `45`. Tuy nhien co `2,871` dong nam o cac moc khac:

| Phut | So dong |
| ---: | ---: |
| `10` | `718` |
| `20` | `718` |
| `40` | `718` |
| `50` | `717` |

Khuyen nghi:

- Neu model yeu cau du lieu 15 phut chuan, can resample ve bin `00/15/30/45`.
- Neu model du doan theo timestamp bat ky, co the giu lai va dung feature `minute`.
- Neu aggregate theo gio, van de nay khong lon.

### 10.5 Duplicate theo khoa logic

Khong co dong trung hoan toan, nhung co `5,146` duplicate theo khoa:

```text
RequestID + SegmentID + Direction + timestamp
```

Mot so ban ghi co cung vi tri, cung thoi diem, cung huong di nhung `Vol` khac nhau. Dieu nay co the den tu viec dem lap, nhieu dot ghi nhan, hoac duplication trong pipeline du lieu.

Khuyen nghi:

- Phai dinh nghia rule xu ly duplicate truoc khi train.
- Neu duplicate la cac lan do lap cua cung mot interval, nen lay `mean`.
- Chi nen lay `sum` neu xac nhan cac dong duplicate la cac phan dem can cong lai.
- Nen log lai so duplicate truoc va sau khi clean.

### 10.6 Quan he giua `SegmentID` va `WktGeom`

Ket qua kiem tra:

- `3,391` `SegmentID` khac nhau.
- `3,746` `WktGeom` khac nhau.
- `261` segment co nhieu geometry.
- `1` geometry gan voi nhieu segment.

Ket luan:

- Khong nen gia dinh `SegmentID` va `WktGeom` la quan he 1-1.
- Neu can feature khong gian, nen tao bang mapping rieng va validate lai.

## 11. Danh gia muc do san sang cho ML

Dataset phu hop cho cac bai toan:

- Du doan luu luong xe `Vol`.
- Forecast luu luong theo segment, borough, huong di va thoi gian.
- Phan loai muc do giao thong sau khi tao label tu `Vol`.
- Phat hien bat thuong ve luu luong.
- Tao dashboard phan tich pattern giao thong.

Dataset chua du cho cac bai toan:

- Uoc luong mat do giao thong vat ly chinh xac.
- Du doan toc do hoac travel time.
- Danh gia tac nghen theo suc chua duong neu khong co capacity/lane/speed.

Target nen dung dau tien:

```text
Vol_clean
```

Neu can tao label phan loai tam thoi:

| Lop | Rule de xuat |
| --- | --- |
| `low` | `Vol_clean <= 59` |
| `medium` | `59 < Vol_clean <= 135` |
| `high` | `135 < Vol_clean <= 399` |
| `very_high` | `Vol_clean > 399` |

Day la nguong theo quantile cua dataset, khong phai nguong nghiep vu chinh thuc. Neu dung cho san pham that, nen dinh nghia nguong theo tung loai duong, suc chua hoac baseline lich su cua tung segment.

## 12. Goi y feature engineering

| Feature | Nguon | Ghi chu |
| --- | --- | --- |
| `datetime` | `Yr`, `M`, `D`, `HH`, `MM` | Bat buoc nen tao |
| `year` | `datetime` | Xu huong dai han |
| `month` | `datetime` | Mua vu |
| `day_of_week` | `datetime` | Rat huu ich cho giao thong |
| `is_weekend` | `datetime` | Feature nhi phan |
| `hour_sin`, `hour_cos` | `HH` | Encode chu ky ngay |
| `minute_sin`, `minute_cos` | `MM` | Encode chu ky phut |
| `Boro` | cot goc | Categorical |
| `Direction` | cot goc | Categorical |
| `SegmentID` | cot goc | Categorical cardinality cao |
| `street` | cot goc | Can chuan hoa text |
| `fromSt`, `toSt` | cot goc | Optional |
| `x`, `y` | parse tu `WktGeom` | Can xac dinh CRS |
| lag features | `Vol` truoc do theo segment/direction | Huu ich cho forecasting |
| rolling mean | rolling `Vol` theo segment/direction | Giam nhieu va bat pattern |

Can tranh leakage:

- `RequestID` co the ma hoa dot do/khao sat, de lam model hoc thuoc neu chia train/test khong can than.
- Random split theo dong co the dua cac thoi diem gan nhau cua cung segment vao ca train va test.
- Lag/rolling feature phai chi dung du lieu qua khu, khong duoc dung tuong lai.

## 13. Pipeline tien xu ly de xuat

1. Doc CSV voi cac cot dang string ban dau.
2. Tao `datetime` tu `Yr`, `M`, `D`, `HH`, `MM`.
3. Tao `Vol_clean` bang cach bo dau phay va cast numeric.
4. Loai dong `Vol_clean < 0`.
5. Fill missing `toSt` bang `UNKNOWN`.
6. Chuan hoa text cho `street`, `fromSt`, `toSt` neu dung lam feature.
7. Parse `WktGeom` thanh `x`, `y`.
8. Quyet dinh xu ly moc phut `10/20/40/50`: giu, resample, hoac aggregate.
9. Xu ly duplicate logic bang rule co dinh.
10. Chia train/validation/test theo thoi gian.
11. Fit encoder/scaler chi tren train set.
12. Bao cao metric tong va metric theo borough, direction, segment frequency.

Khoa aggregate nen can nhac:

```text
SegmentID + Direction + datetime
```

Chi them `RequestID` vao khoa neu nghiep vu yeu cau tach rieng cac dot khao sat.

## 14. Goi y mo hinh

Baseline nen co:

- Trung binh/median lich su theo `SegmentID + Direction + hour + day_of_week`.
- Trung binh/median theo `Boro + Direction + hour`.
- Linear regression hoac ridge regression voi feature thoi gian va categorical da encode.

Mo hinh tabular manh hon:

- LightGBM.
- XGBoost.
- CatBoost.
- Random forest co the dung lam baseline, nhung co the nang voi dataset lon.

Neu lam forecasting:

- Tao lag feature theo `SegmentID + Direction`.
- Tao rolling mean theo cac cua so thoi gian.
- Chia theo thoi gian, khong random.
- Co the train model global cho tat ca segment, voi `SegmentID` va `Direction` la categorical.

Metric nen dung:

- MAE: de dien giai theo so xe.
- RMSE: phat nang loi lon.
- SMAPE/MAPE: dung can than vi co nhieu gia tri nho va `Vol = 0`.
- Metric rieng theo borough/direction/segment de phat hien bias.

## 15. Rui ro chinh

| Rui ro | Muc do | Ly do | Cach giam thieu |
| --- | --- | --- | --- |
| Goi la density nhung target la volume | Cao | Thieu lane, capacity, speed, road length | Goi bai toan la volume prediction hoac bo sung metadata |
| Leakage theo thoi gian | Cao | Random split co the dua timestamp gan nhau vao train/test | Dung time-based split |
| Leakage tu `RequestID` | Trung binh/cao | ID dot do co the giup model hoc thuoc | Loai khoi feature ban dau hoac split theo group |
| Duplicate logic | Trung binh | Cung vi tri/thoi diem co nhieu `Vol` | Aggregate bang rule ro rang |
| Outlier `Vol` | Trung binh | Max cao hon median rat nhieu | Kiem tra va dung metric robust |
| Moc phut khong chuan | Thap/trung binh | Co 2,871 dong khong o bin 15 phut | Resample hoac giu exact minute |
| Nam du lieu khong deu | Trung binh | Mot so nam rat it du lieu | Bao cao metric theo nam |
| CRS cua `WktGeom` chua xac dinh | Trung binh | Khong phai lat/lon truc tiep | Xac dinh CRS truoc khi tinh distance/map |

## 16. Ket luan

Dataset nay co chat luong kha tot de lam bai toan ML ve luu luong giao thong. No co quy mo lon, co cot target ro rang (`Vol`), co thong tin thoi gian, khong gian va huong di. Cac van de du lieu ton tai nhung deu co the xu ly bang pipeline tien xu ly tuong doi ro rang.

Tuy nhien, khong nen xem day la dataset "traffic density" hoan chinh neu chua dinh nghia lai target hoac bo sung thong tin ve suc chua duong. Cach tiep can an toan nhat la:

```text
Du doan luu luong xe da lam sach (`Vol_clean`) theo doan duong, huong di, borough va thoi gian.
```

Sau khi mo hinh du doan `Vol_clean` on dinh, co the xay tang phan loai mat do/muc do giao thong bang:

- nguong quantile cua `Vol_clean`,
- baseline rieng theo tung segment,
- metadata ve so lan duong/suc chua duong,
- du lieu toc do hoac occupancy tu nguon khac.

Cot nen co trong dataset da clean:

```text
datetime, year, month, day, day_of_week, is_weekend,
hour, minute, Boro, SegmentID, Direction,
street, fromSt, toSt, x, y, Vol_clean
```

Buoc tiep theo nen lam la tao file clean tu CSV goc, sau do train baseline model du doan `Vol_clean` va so sanh voi baseline trung binh lich su.
