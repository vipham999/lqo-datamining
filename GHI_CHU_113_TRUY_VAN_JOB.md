# Ghi chú 113 truy vấn JOB: input và output

Ghi chú cho từng truy vấn của Join Order Benchmark (JOB) chạy trên CSDL `imdbload`. Xem thêm phần tổng quan trong [GHI_CHU_IMDB_JOB.md](GHI_CHU_IMDB_JOB.md).

File này được sinh tự động từ `lqo_ml_perspective/bao/queries/join-order-benchmark/*.sql`, log baseline PostgreSQL của nhóm (`logs/test__postgres__job__20261011_1743.txt`), log Bao của nhóm (LOO-1, RND-1) và log của tác giả (`experiment_logs/20240103__combined.csv`).

## Cách đọc

Với mọi truy vấn:

- **Input** gồm:
  - **Bảng:** các bảng tham gia, viết dạng `bí danh = bảng`.
  - **Điều kiện nối:** các phép so khớp khóa giữa hai bảng, vd `t.id = mc.movie_id`.
  - **Điều kiện lọc:** các điều kiện trên giá trị, vd `t.production_year > 2005`. Đây là phần làm khác nhau giữa các biến thể a, b, c… của cùng một template.
- **Output (kết quả SQL):** luôn là **đúng 1 dòng**. Mỗi cột là `MIN(...)` của một thuộc tính. JOB dùng `MIN` để kết quả nhỏ, nhờ đó thời gian đo phản ánh chất lượng plan chứ không phải thời gian trả dữ liệu.
- **Output (thực nghiệm):** thời gian end-to-end ở lần chạy thứ 3 (cache nóng), gồm:
  - **PG nhóm:** PostgreSQL trên máy của nhóm.
  - **PG tác giả:** PostgreSQL trong log của tác giả.
  - **Bao LOO-1 / RND-1:** Bao của nhóm, chỉ có khi truy vấn nằm trong tập test của split đó.
- **Test trong split:** các split có truy vấn này trong tập test. BQ = Base Query, LOO = Leave-One-Out, RND = Random. Mỗi loại có 3 lần chia (-1, -2, -3).

> Giá trị thực của các cột output (vd tên phim cụ thể) chưa được ghi lại. Lúc sinh file, CSDL đang bận chạy thực nghiệm Base Query 1, và chạy thêm truy vấn sẽ làm sai số đo của thực nghiệm đó.

## Tổng quan 113 truy vấn

| Truy vấn | Số bảng | Số điều kiện nối | Số điều kiện lọc | Số cột output | PG nhóm | PG tác giả | Tỉ lệ (nhóm/tác giả) |
|---|---:|---:|---:|---:|---:|---:|---:|
| [1a](#1a) | 5 | 5 | 4 | 3 | 125 ms | 96 ms | 1.30× |
| [1b](#1b) | 5 | 5 | 4 | 3 | 55 ms | 88 ms | 0.63× |
| [1c](#1c) | 5 | 5 | 5 | 3 | 61 ms | 93 ms | 0.66× |
| [1d](#1d) | 5 | 5 | 4 | 3 | 56 ms | 90 ms | 0.62× |
| [2a](#2a) | 5 | 5 | 2 | 1 | 1.26 s | 451 ms | 2.79× |
| [2b](#2b) | 5 | 5 | 2 | 1 | 502 ms | 452 ms | 1.11× |
| [2c](#2c) | 5 | 5 | 2 | 1 | 965 ms | 427 ms | 2.26× |
| [2d](#2d) | 5 | 5 | 2 | 1 | 690 ms | 562 ms | 1.23× |
| [3a](#3a) | 4 | 4 | 3 | 1 | 93 ms | 118 ms | 0.79× |
| [3b](#3b) | 4 | 4 | 3 | 1 | 56 ms | 75 ms | 0.75× |
| [3c](#3c) | 4 | 4 | 3 | 1 | 179 ms | 233 ms | 0.77× |
| [4a](#4a) | 5 | 5 | 4 | 2 | 62 ms | 83 ms | 0.75× |
| [4b](#4b) | 5 | 5 | 4 | 2 | 43 ms | 61 ms | 0.70× |
| [4c](#4c) | 5 | 5 | 4 | 2 | 84 ms | 92 ms | 0.91× |
| [5a](#5a) | 5 | 5 | 5 | 1 | 87 ms | 117 ms | 0.75× |
| [5b](#5b) | 5 | 5 | 6 | 1 | 85 ms | 110 ms | 0.77× |
| [5c](#5c) | 5 | 5 | 5 | 1 | 120 ms | 153 ms | 0.79× |
| [6a](#6a) | 5 | 5 | 3 | 3 | 17 ms | 16 ms | 1.09× |
| [6b](#6b) | 5 | 5 | 3 | 3 | 155 ms | 154 ms | 1.01× |
| [6c](#6c) | 5 | 5 | 3 | 3 | 7 ms | 10 ms | 0.66× |
| [6d](#6d) | 5 | 5 | 3 | 3 | 20.48 s | 3.64 s | 5.63× |
| [6e](#6e) | 5 | 5 | 3 | 3 | 13 ms | 18 ms | 0.72× |
| [6f](#6f) | 5 | 5 | 2 | 3 | 14.21 s | 3.80 s | 3.74× |
| [7a](#7a) | 8 | 11 | 7 | 2 | 1.84 s | 619 ms | 2.98× |
| [7b](#7b) | 8 | 11 | 7 | 2 | 163 ms | 163 ms | 1.00× |
| [7c](#7c) | 8 | 11 | 8 | 2 | 2.11 s | 2.93 s | 0.72× |
| [8a](#8a) | 7 | 8 | 7 | 2 | 6.33 s | 698 ms | 9.06× |
| [8b](#8b) | 7 | 8 | 10 | 2 | 130 ms | 144 ms | 0.90× |
| [8c](#8c) | 7 | 8 | 2 | 2 | 5.99 s | 3.19 s | 1.88× |
| [8d](#8d) | 7 | 8 | 2 | 2 | 2.28 s | 1.45 s | 1.58× |
| [9a](#9a) | 8 | 9 | 8 | 3 | 343 ms | 194 ms | 1.76× |
| [9b](#9b) | 8 | 9 | 8 | 4 | 216 ms | 195 ms | 1.11× |
| [9c](#9c) | 8 | 9 | 5 | 4 | 341 ms | 375 ms | 0.91× |
| [9d](#9d) | 8 | 9 | 4 | 4 | 4.19 s | 2.63 s | 1.59× |
| [10a](#10a) | 7 | 7 | 5 | 2 | 250 ms | 317 ms | 0.79× |
| [10b](#10b) | 7 | 7 | 4 | 2 | 197 ms | 227 ms | 0.87× |
| [10c](#10c) | 7 | 7 | 3 | 2 | 5.70 s | 4.30 s | 1.33× |
| [11a](#11a) | 8 | 10 | 7 | 3 | 38 ms | 59 ms | 0.65× |
| [11b](#11b) | 8 | 10 | 8 | 3 | 18 ms | 31 ms | 0.57× |
| [11c](#11c) | 8 | 10 | 7 | 3 | 99 ms | 155 ms | 0.64× |
| [11d](#11d) | 8 | 10 | 6 | 3 | 85 ms | 138 ms | 0.62× |
| [12a](#12a) | 8 | 10 | 7 | 3 | 109 ms | 208 ms | 0.53× |
| [12b](#12b) | 8 | 10 | 7 | 2 | 51 ms | 91 ms | 0.56× |
| [12c](#12c) | 8 | 10 | 7 | 3 | 393 ms | 641 ms | 0.61× |
| [13a](#13a) | 9 | 11 | 5 | 3 | 1.24 s | 1.31 s | 0.95× |
| [13b](#13b) | 9 | 11 | 7 | 3 | 350 ms | 587 ms | 0.60× |
| [13c](#13c) | 9 | 11 | 7 | 3 | 364 ms | 575 ms | 0.63× |
| [13d](#13d) | 9 | 11 | 5 | 3 | 1.28 s | 1.99 s | 0.65× |
| [14a](#14a) | 8 | 10 | 7 | 2 | 171 ms | 223 ms | 0.77× |
| [14b](#14b) | 8 | 10 | 8 | 2 | 59 ms | 89 ms | 0.66× |
| [14c](#14c) | 8 | 10 | 8 | 2 | 292 ms | 463 ms | 0.63× |
| [15a](#15a) | 9 | 14 | 7 | 2 | 182 ms | 278 ms | 0.65× |
| [15b](#15b) | 9 | 14 | 8 | 2 | 16 ms | 35 ms | 0.45× |
| [15c](#15c) | 9 | 14 | 6 | 2 | 956 ms | 556 ms | 1.72× |
| [15d](#15d) | 9 | 14 | 4 | 2 | 284 ms | 730 ms | 0.39× |
| [16a](#16a) | 8 | 11 | 4 | 2 | 113 ms | 144 ms | 0.79× |
| [16b](#16b) | 8 | 11 | 2 | 2 | 39.36 s | 17.53 s | 2.25× |
| [16c](#16c) | 8 | 11 | 3 | 2 | 1.93 s | 1.46 s | 1.32× |
| [16d](#16d) | 8 | 11 | 4 | 2 | 1.75 s | 1.14 s | 1.54× |
| [17a](#17a) | 7 | 9 | 3 | 2 | 25.53 s | 9.63 s | 2.65× |
| [17b](#17b) | 7 | 9 | 2 | 2 | 13.22 s | 4.95 s | 2.67× |
| [17c](#17c) | 7 | 9 | 2 | 2 | 14.31 s | 4.95 s | 2.89× |
| [17d](#17d) | 7 | 9 | 2 | 1 | 15.37 s | 4.86 s | 3.16× |
| [17e](#17e) | 7 | 9 | 2 | 1 | 18.29 s | 9.66 s | 1.89× |
| [17f](#17f) | 7 | 9 | 2 | 1 | 20.89 s | 7.77 s | 2.69× |
| [18a](#18a) | 7 | 9 | 5 | 3 | 48.91 s | 2.91 s | 16.78× |
| [18b](#18b) | 7 | 9 | 9 | 3 | 97 ms | 167 ms | 0.58× |
| [18c](#18c) | 7 | 9 | 5 | 3 | 45.60 s | 3.33 s | 13.68× |
| [19a](#19a) | 10 | 13 | 11 | 2 | 246 ms | 204 ms | 1.21× |
| [19b](#19b) | 10 | 13 | 12 | 2 | 97 ms | 120 ms | 0.81× |
| [19c](#19c) | 10 | 13 | 9 | 2 | 1.65 s | 420 ms | 3.92× |
| [19d](#19d) | 10 | 13 | 6 | 2 | 9.43 s | 5.03 s | 1.87× |
| [20a](#20a) | 10 | 12 | 7 | 1 | 4.05 s | 1.93 s | 2.10× |
| [20b](#20b) | 10 | 12 | 8 | 1 | 3.77 s | 1.50 s | 2.51× |
| [20c](#20c) | 10 | 12 | 7 | 2 | 1.13 s | 852 ms | 1.33× |
| [21a](#21a) | 9 | 14 | 8 | 3 | 57 ms | 72 ms | 0.79× |
| [21b](#21b) | 9 | 14 | 8 | 3 | 42 ms | 68 ms | 0.63× |
| [21c](#21c) | 9 | 14 | 8 | 3 | 49 ms | 72 ms | 0.68× |
| [22a](#22a) | 11 | 16 | 10 | 3 | 275 ms | 387 ms | 0.71× |
| [22b](#22b) | 11 | 16 | 10 | 3 | 175 ms | 223 ms | 0.78× |
| [22c](#22c) | 11 | 16 | 10 | 3 | 1.23 s | 1.85 s | 0.67× |
| [22d](#22d) | 11 | 16 | 8 | 3 | 2.10 s | 752 ms | 2.79× |
| [23a](#23a) | 11 | 16 | 8 | 2 | 228 ms | 231 ms | 0.99× |
| [23b](#23b) | 11 | 16 | 8 | 2 | 42 ms | 70 ms | 0.60× |
| [23c](#23c) | 11 | 16 | 8 | 2 | 3.57 s | 289 ms | 12.36× |
| [24a](#24a) | 12 | 18 | 10 | 3 | 185 ms | 334 ms | 0.55× |
| [24b](#24b) | 12 | 18 | 12 | 3 | 53 ms | 87 ms | 0.61× |
| [25a](#25a) | 9 | 14 | 6 | 4 | 11.58 s | 2.15 s | 5.38× |
| [25b](#25b) | 9 | 14 | 8 | 4 | 226 ms | 252 ms | 0.90× |
| [25c](#25c) | 9 | 14 | 6 | 4 | **timeout (720 s)** | 5.88 s | 122.45× |
| [26a](#26a) | 12 | 17 | 9 | 4 | 3.70 s | 964 ms | 3.84× |
| [26b](#26b) | 12 | 17 | 9 | 3 | 100 ms | 139 ms | 0.72× |
| [26c](#26c) | 12 | 17 | 8 | 3 | 6.03 s | 1.79 s | 3.37× |
| [27a](#27a) | 12 | 21 | 10 | 3 | 58 ms | 77 ms | 0.75× |
| [27b](#27b) | 12 | 21 | 10 | 3 | 99 ms | 69 ms | 1.43× |
| [27c](#27c) | 12 | 21 | 10 | 3 | 41 ms | 84 ms | 0.48× |
| [28a](#28a) | 14 | 23 | 12 | 3 | 489 ms | 1.82 s | 0.27× |
| [28b](#28b) | 14 | 23 | 12 | 3 | 330 ms | 647 ms | 0.51× |
| [28c](#28c) | 14 | 23 | 12 | 3 | 487 ms | 979 ms | 0.50× |
| [29a](#29a) | 17 | 28 | 15 | 3 | 121 ms | 138 ms | 0.88× |
| [29b](#29b) | 17 | 28 | 14 | 3 | 143 ms | 107 ms | 1.34× |
| [29c](#29c) | 17 | 28 | 13 | 3 | 213 ms | 590 ms | 0.36× |
| [30a](#30a) | 12 | 21 | 9 | 4 | 9.87 s | 2.41 s | 4.10× |
| [30b](#30b) | 12 | 21 | 10 | 4 | 304 ms | 392 ms | 0.77× |
| [30c](#30c) | 12 | 21 | 8 | 4 | 6.53 s | 2.03 s | 3.22× |
| [31a](#31a) | 11 | 20 | 7 | 4 | 153 ms | 250 ms | 0.61× |
| [31b](#31b) | 11 | 20 | 10 | 4 | 91 ms | 159 ms | 0.57× |
| [31c](#31c) | 11 | 20 | 6 | 4 | 247 ms | 394 ms | 0.63× |
| [32a](#32a) | 6 | 6 | 1 | 3 | 6 ms | 11 ms | 0.55× |
| [32b](#32b) | 6 | 6 | 1 | 3 | 64 ms | 94 ms | 0.68× |
| [33a](#33a) | 14 | 19 | 8 | 6 | 71 ms | 115 ms | 0.62× |
| [33b](#33b) | 14 | 19 | 8 | 6 | 68 ms | 109 ms | 0.62× |
| [33c](#33c) | 14 | 19 | 8 | 6 | 59 ms | 124 ms | 0.47× |

## Chi tiết theo template

### Template 1 (1a, 1b, 1c, 1d)

**Ý nghĩa:** Phim trong top 250 do một công ty sản xuất, ghi chú sản xuất có “co-production”/“presents”.

**Bảng (5):** `ct = company_type` (loại công ty), `it = info_type` (loại thông tin), `mc = movie_companies` (phim–công ty), `mi_idx = movie_info_idx` (rating/votes/top 250), `t = title` (phim)

#### 1a

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `it.info = 'top 250 rank'`
  - `mc.note NOT LIKE '%(as Metro-Goldwyn-Mayer Pictures)%'`
  - `(mc.note LIKE '%(co-production)%' OR mc.note LIKE '%(presents)%')`
- **Output (1 dòng):** `production_note` = `MIN(mc.note)`, `movie_title` = `MIN(t.title)`, `movie_year` = `MIN(t.production_year)`
- **Thời gian:** PG nhóm 125 ms · PG tác giả 96 ms
- **Test trong split:** BQ-3, RND-2

#### 1b

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `it.info = 'bottom 10 rank'`
  - `mc.note NOT LIKE '%(as Metro-Goldwyn-Mayer Pictures)%'`
  - `t.production_year BETWEEN 2005 AND 2010`
- **Output (1 dòng):** `production_note` = `MIN(mc.note)`, `movie_title` = `MIN(t.title)`, `movie_year` = `MIN(t.production_year)`
- **Thời gian:** PG nhóm 55 ms · PG tác giả 88 ms
- **Test trong split:** BQ-3

#### 1c

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `it.info = 'top 250 rank'`
  - `mc.note NOT LIKE '%(as Metro-Goldwyn-Mayer Pictures)%'`
  - `(mc.note LIKE '%(co-production)%')`
  - `t.production_year >2010`
- **Output (1 dòng):** `production_note` = `MIN(mc.note)`, `movie_title` = `MIN(t.title)`, `movie_year` = `MIN(t.production_year)`
- **Thời gian:** PG nhóm 61 ms · PG tác giả 93 ms · Bao LOO-1 103 ms · Bao RND-1 105 ms
- **Test trong split:** BQ-3, LOO-1, LOO-3, RND-1

#### 1d

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `it.info = 'bottom 10 rank'`
  - `mc.note NOT LIKE '%(as Metro-Goldwyn-Mayer Pictures)%'`
  - `t.production_year >2000`
- **Output (1 dòng):** `production_note` = `MIN(mc.note)`, `movie_title` = `MIN(t.title)`, `movie_year` = `MIN(t.production_year)`
- **Thời gian:** PG nhóm 56 ms · PG tác giả 90 ms
- **Test trong split:** BQ-3, LOO-2

### Template 2 (2a, 2b, 2c, 2d)

**Ý nghĩa:** Phim có từ khóa `character-name-in-title` (tên nhân vật nằm trong tựa phim) của công ty thuộc một quốc gia.

**Bảng (5):** `cn = company_name` (công ty), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 2a

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[de]'`
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.26 s · PG tác giả 451 ms · Bao LOO-1 365 ms
- **Test trong split:** BQ-1, LOO-1, RND-3

#### 2b

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[nl]'`
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 502 ms · PG tác giả 452 ms
- **Test trong split:** BQ-1

#### 2c

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[sm]'`
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 965 ms · PG tác giả 427 ms · Bao RND-1 469 ms
- **Test trong split:** BQ-1, RND-1

#### 2d

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 690 ms · PG tác giả 562 ms
- **Test trong split:** BQ-1, LOO-2, LOO-3

### Template 3 (3a, 3b, 3c)

**Ý nghĩa:** Phim có từ khóa chứa “sequel”, có thông tin quốc gia/ngôn ngữ Bắc Âu, sản xuất sau một năm nhất định.

**Bảng (4):** `k = keyword` (từ khóa), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 3a

- **Input:** 4 bảng, 4 điều kiện nối. Điều kiện lọc:
  - `k.keyword LIKE '%sequel%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German')`
  - `t.production_year > 2005`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 93 ms · PG tác giả 118 ms
- **Test trong split:** LOO-2

#### 3b

- **Input:** 4 bảng, 4 điều kiện nối. Điều kiện lọc:
  - `k.keyword LIKE '%sequel%'`
  - `mi.info IN ('Bulgaria')`
  - `t.production_year > 2010`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 56 ms · PG tác giả 75 ms · Bao LOO-1 103 ms
- **Test trong split:** LOO-1, LOO-3, RND-3

#### 3c

- **Input:** 4 bảng, 4 điều kiện nối. Điều kiện lọc:
  - `k.keyword LIKE '%sequel%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German', 'USA', 'American')`
  - `t.production_year > 1990`
- **Output (1 dòng):** `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 179 ms · PG tác giả 233 ms
- **Test trong split:** không có (chỉ nằm trong train)

### Template 4 (4a, 4b, 4c)

**Ý nghĩa:** Phim có từ khóa chứa “sequel” và rating vượt một ngưỡng.

**Bảng (5):** `it = info_type` (loại thông tin), `k = keyword` (từ khóa), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 4a

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `it.info ='rating'`
  - `k.keyword LIKE '%sequel%'`
  - `mi_idx.info > '5.0'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `rating` = `MIN(mi_idx.info)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 62 ms · PG tác giả 83 ms · Bao LOO-1 103 ms
- **Test trong split:** LOO-1, LOO-3

#### 4b

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `it.info ='rating'`
  - `k.keyword LIKE '%sequel%'`
  - `mi_idx.info > '9.0'`
  - `t.production_year > 2010`
- **Output (1 dòng):** `rating` = `MIN(mi_idx.info)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 43 ms · PG tác giả 61 ms · Bao RND-1 88 ms
- **Test trong split:** LOO-2, RND-1

#### 4c

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `it.info ='rating'`
  - `k.keyword LIKE '%sequel%'`
  - `mi_idx.info > '2.0'`
  - `t.production_year > 1990`
- **Output (1 dòng):** `rating` = `MIN(mi_idx.info)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 84 ms · PG tác giả 92 ms · Bao RND-1 1.01 s
- **Test trong split:** RND-1, RND-2

### Template 5 (5a, 5b, 5c)

**Ý nghĩa:** Phim của công ty sản xuất, phát hành rạp (theatrical) ở một nước, có thông tin quốc gia/ngôn ngữ Bắc Âu.

**Bảng (5):** `ct = company_type` (loại công ty), `it = info_type` (loại thông tin), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `t = title` (phim)

#### 5a

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `mc.note LIKE '%(theatrical)%'`
  - `mc.note LIKE '%(France)%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German')`
  - `t.production_year > 2005`
- **Output (1 dòng):** `typical_european_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 87 ms · PG tác giả 117 ms · Bao LOO-1 176 ms
- **Test trong split:** BQ-3, LOO-1

#### 5b

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `mc.note LIKE '%(VHS)%'`
  - `mc.note LIKE '%(USA)%'`
  - `mc.note LIKE '%(1994)%'`
  - `mi.info IN ('USA', 'America')`
  - `t.production_year > 2010`
- **Output (1 dòng):** `american_vhs_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 85 ms · PG tác giả 110 ms
- **Test trong split:** BQ-3

#### 5c

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `ct.kind = 'production companies'`
  - `mc.note NOT LIKE '%(TV)%'`
  - `mc.note LIKE '%(USA)%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German', 'USA', 'American')`
  - `t.production_year > 1990`
- **Output (1 dòng):** `american_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 120 ms · PG tác giả 153 ms · Bao RND-1 184 ms
- **Test trong split:** BQ-3, LOO-2, LOO-3, RND-1, RND-2

### Template 6 (6a, 6b, 6c, 6d, 6e, 6f)

**Ý nghĩa:** Phim có một từ khóa cụ thể (vd: Marvel) và diễn viên có tên khớp mẫu (vd: Downey Robert).

**Bảng (5):** `ci = cast_info` (ai đóng/làm phim nào), `k = keyword` (từ khóa), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 6a

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `k.keyword = 'marvel-cinematic-universe'`
  - `n.name LIKE '%Downey%Robert%'`
  - `t.production_year > 2010`
- **Output (1 dòng):** `movie_keyword` = `MIN(k.keyword)`, `actor_name` = `MIN(n.name)`, `marvel_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 17 ms · PG tác giả 16 ms · Bao RND-1 52 ms
- **Test trong split:** RND-1

#### 6b

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `k.keyword IN ('superhero', 'sequel', 'second-part', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence')`
  - `n.name LIKE '%Downey%Robert%'`
  - `t.production_year > 2014`
- **Output (1 dòng):** `movie_keyword` = `MIN(k.keyword)`, `actor_name` = `MIN(n.name)`, `hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 155 ms · PG tác giả 154 ms · Bao LOO-1 241 ms
- **Test trong split:** LOO-1

#### 6c

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `k.keyword = 'marvel-cinematic-universe'`
  - `n.name LIKE '%Downey%Robert%'`
  - `t.production_year > 2014`
- **Output (1 dòng):** `movie_keyword` = `MIN(k.keyword)`, `actor_name` = `MIN(n.name)`, `marvel_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 7 ms · PG tác giả 10 ms · Bao RND-1 47 ms
- **Test trong split:** RND-1, RND-2

#### 6d

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `k.keyword IN ('superhero', 'sequel', 'second-part', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence')`
  - `n.name LIKE '%Downey%Robert%'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_keyword` = `MIN(k.keyword)`, `actor_name` = `MIN(n.name)`, `hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 20.48 s · PG tác giả 3.64 s
- **Test trong split:** LOO-2, LOO-3, RND-2, RND-3

#### 6e

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `k.keyword = 'marvel-cinematic-universe'`
  - `n.name LIKE '%Downey%Robert%'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_keyword` = `MIN(k.keyword)`, `actor_name` = `MIN(n.name)`, `marvel_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 13 ms · PG tác giả 18 ms · Bao RND-1 56 ms
- **Test trong split:** RND-1

#### 6f

- **Input:** 5 bảng, 5 điều kiện nối. Điều kiện lọc:
  - `k.keyword IN ('superhero', 'sequel', 'second-part', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence')`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_keyword` = `MIN(k.keyword)`, `actor_name` = `MIN(n.name)`, `hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 14.21 s · PG tác giả 3.80 s
- **Test trong split:** không có (chỉ nằm trong train)

### Template 7 (7a, 7b, 7c)

**Ý nghĩa:** Người có tiểu sử (mini biography) và tên khác, đóng trong phim có liên kết “features”.

**Bảng (8):** `an = aka_name` (tên khác của người), `ci = cast_info` (ai đóng/làm phim nào), `it = info_type` (loại thông tin), `lt = link_type` (loại liên kết phim), `ml = movie_link` (liên kết giữa hai phim), `n = name` (người), `pi = person_info` (thông tin người), `t = title` (phim)

#### 7a

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `an.name LIKE '%a%'`
  - `it.info ='mini biography'`
  - `lt.link ='features'`
  - `n.name_pcode_cf BETWEEN 'A' AND 'F'`
  - `(n.gender='m' OR (n.gender = 'f' AND n.name LIKE 'B%'))`
  - `pi.note ='Volker Boehm'`
  - `t.production_year BETWEEN 1980 AND 1995`
- **Output (1 dòng):** `of_person` = `MIN(n.name)`, `biography_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.84 s · PG tác giả 619 ms
- **Test trong split:** BQ-1, LOO-2

#### 7b

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `an.name LIKE '%a%'`
  - `it.info ='mini biography'`
  - `lt.link ='features'`
  - `n.name_pcode_cf LIKE 'D%'`
  - `n.gender='m'`
  - `pi.note ='Volker Boehm'`
  - `t.production_year BETWEEN 1980 AND 1984`
- **Output (1 dòng):** `of_person` = `MIN(n.name)`, `biography_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 163 ms · PG tác giả 163 ms
- **Test trong split:** BQ-1, LOO-3, RND-2

#### 7c

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `an.name IS NOT NULL`
  - `(an.name LIKE '%a%' OR an.name LIKE 'A%')`
  - `it.info ='mini biography'`
  - `lt.link IN ('references', 'referenced in', 'features', 'featured in')`
  - `n.name_pcode_cf BETWEEN 'A' AND 'F'`
  - `(n.gender='m' OR (n.gender = 'f' AND n.name LIKE 'A%'))`
  - `pi.note IS NOT NULL`
  - `t.production_year BETWEEN 1980 AND 2010`
- **Output (1 dòng):** `cast_member_name` = `MIN(n.name)`, `cast_member_info` = `MIN(pi.info)`
- **Thời gian:** PG nhóm 2.11 s · PG tác giả 2.93 s · Bao LOO-1 2.34 s
- **Test trong split:** BQ-1, LOO-1

### Template 8 (8a, 8b, 8c, 8d)

**Ý nghĩa:** Diễn viên lồng tiếng (voice) trong phim của công ty Nhật; lấy bí danh của họ.

**Bảng (7):** `an1 = aka_name` (tên khác của người), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `mc = movie_companies` (phim–công ty), `n1 = name` (người), `rt = role_type` (vai trò), `t = title` (phim)

#### 8a

- **Input:** 7 bảng, 8 điều kiện nối. Điều kiện lọc:
  - `ci.note ='(voice: English version)'`
  - `cn.country_code ='[jp]'`
  - `mc.note LIKE '%(Japan)%'`
  - `mc.note NOT LIKE '%(USA)%'`
  - `n1.name LIKE '%Yo%'`
  - `n1.name NOT LIKE '%Yu%'`
  - `rt.role ='actress'`
- **Output (1 dòng):** `actress_pseudonym` = `MIN(an1.name)`, `japanese_movie_dubbed` = `MIN(t.title)`
- **Thời gian:** PG nhóm 6.33 s · PG tác giả 698 ms
- **Test trong split:** LOO-3

#### 8b

- **Input:** 7 bảng, 8 điều kiện nối. Điều kiện lọc:
  - `ci.note ='(voice: English version)'`
  - `cn.country_code ='[jp]'`
  - `mc.note LIKE '%(Japan)%'`
  - `mc.note NOT LIKE '%(USA)%'`
  - `(mc.note LIKE '%(2006)%' OR mc.note LIKE '%(2007)%')`
  - `n.name LIKE '%Yo%'`
  - `n.name NOT LIKE '%Yu%'`
  - `rt.role ='actress'`
  - `t.production_year BETWEEN 2006 AND 2007`
  - `(t.title LIKE 'One Piece%' OR t.title LIKE 'Dragon Ball Z%')`
- **Output (1 dòng):** `acress_pseudonym` = `MIN(an.name)`, `japanese_anime_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 130 ms · PG tác giả 144 ms · Bao RND-1 148 ms
- **Test trong split:** RND-1

#### 8c

- **Input:** 7 bảng, 8 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `rt.role ='writer'`
- **Output (1 dòng):** `writer_pseudo_name` = `MIN(a1.name)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 5.99 s · PG tác giả 3.19 s · Bao LOO-1 4.45 s · Bao RND-1 5.55 s
- **Test trong split:** LOO-1, LOO-2, RND-1, RND-2

#### 8d

- **Input:** 7 bảng, 8 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `rt.role ='costume designer'`
- **Output (1 dòng):** `costume_designer_pseudo` = `MIN(an1.name)`, `movie_with_costumes` = `MIN(t.title)`
- **Thời gian:** PG nhóm 2.28 s · PG tác giả 1.45 s
- **Test trong split:** không có (chỉ nằm trong train)

### Template 9 (9a, 9b, 9c, 9d)

**Ý nghĩa:** Nữ diễn viên lồng tiếng trong phim của công ty Mỹ; lấy tên khác, tên nhân vật.

**Bảng (8):** `an = aka_name` (tên khác của người), `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `mc = movie_companies` (phim–công ty), `n = name` (người), `rt = role_type` (vai trò), `t = title` (phim)

#### 9a

- **Input:** 8 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `mc.note IS NOT NULL`
  - `(mc.note LIKE '%(USA)%' OR mc.note LIKE '%(worldwide)%')`
  - `n.gender ='f'`
  - `n.name LIKE '%Ang%'`
  - `rt.role ='actress'`
  - `t.production_year BETWEEN 2005 AND 2015`
- **Output (1 dòng):** `alternative_name` = `MIN(an.name)`, `character_name` = `MIN(chn.name)`, `movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 343 ms · PG tác giả 194 ms
- **Test trong split:** LOO-3

#### 9b

- **Input:** 8 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note = '(voice)'`
  - `cn.country_code ='[us]'`
  - `mc.note LIKE '%(200%)%'`
  - `(mc.note LIKE '%(USA)%' OR mc.note LIKE '%(worldwide)%')`
  - `n.gender ='f'`
  - `n.name LIKE '%Angel%'`
  - `rt.role ='actress'`
  - `t.production_year BETWEEN 2007 AND 2010`
- **Output (1 dòng):** `alternative_name` = `MIN(an.name)`, `voiced_character` = `MIN(chn.name)`, `voicing_actress` = `MIN(n.name)`, `american_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 216 ms · PG tác giả 195 ms
- **Test trong split:** RND-3

#### 9c

- **Input:** 8 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
- **Output (1 dòng):** `alternative_name` = `MIN(an.name)`, `voiced_character_name` = `MIN(chn.name)`, `voicing_actress` = `MIN(n.name)`, `american_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 341 ms · PG tác giả 375 ms · Bao LOO-1 355 ms · Bao RND-1 6.21 s
- **Test trong split:** LOO-1, LOO-2, RND-1

#### 9d

- **Input:** 8 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `n.gender ='f'`
  - `rt.role ='actress'`
- **Output (1 dòng):** `alternative_name` = `MIN(an.name)`, `voiced_char_name` = `MIN(chn.name)`, `voicing_actress` = `MIN(n.name)`, `american_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 4.19 s · PG tác giả 2.63 s
- **Test trong split:** không có (chỉ nằm trong train)

### Template 10 (10a, 10b, 10c)

**Ý nghĩa:** Nhân vật lồng tiếng không ghi danh (uncredited) trong phim của công ty thuộc một nước (vd: Nga).

**Bảng (7):** `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `ct = company_type` (loại công ty), `mc = movie_companies` (phim–công ty), `rt = role_type` (vai trò), `t = title` (phim)

#### 10a

- **Input:** 7 bảng, 7 điều kiện nối. Điều kiện lọc:
  - `ci.note LIKE '%(voice)%'`
  - `ci.note LIKE '%(uncredited)%'`
  - `cn.country_code = '[ru]'`
  - `rt.role = 'actor'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `uncredited_voiced_character` = `MIN(chn.name)`, `russian_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 250 ms · PG tác giả 317 ms
- **Test trong split:** LOO-2, RND-2

#### 10b

- **Input:** 7 bảng, 7 điều kiện nối. Điều kiện lọc:
  - `ci.note LIKE '%(producer)%'`
  - `cn.country_code = '[ru]'`
  - `rt.role = 'actor'`
  - `t.production_year > 2010`
- **Output (1 dòng):** `character` = `MIN(chn.name)`, `russian_mov_with_actor_producer` = `MIN(t.title)`
- **Thời gian:** PG nhóm 197 ms · PG tác giả 227 ms · Bao LOO-1 264 ms
- **Test trong split:** LOO-1, RND-3

#### 10c

- **Input:** 7 bảng, 7 điều kiện nối. Điều kiện lọc:
  - `ci.note LIKE '%(producer)%'`
  - `cn.country_code = '[us]'`
  - `t.production_year > 1990`
- **Output (1 dòng):** `character` = `MIN(chn.name)`, `movie_with_american_producer` = `MIN(t.title)`
- **Thời gian:** PG nhóm 5.70 s · PG tác giả 4.30 s
- **Test trong split:** LOO-3

### Template 11 (11a, 11b, 11c, 11d)

**Ý nghĩa:** Phim tiếp nối (liên kết “follow”) có từ khóa sequel, của công ty không phải Ba Lan có tên chứa Film/Warner.

**Bảng (8):** `cn = company_name` (công ty), `ct = company_type` (loại công ty), `k = keyword` (từ khóa), `lt = link_type` (loại liên kết phim), `mc = movie_companies` (phim–công ty), `mk = movie_keyword` (phim–từ khóa), `ml = movie_link` (liên kết giữa hai phim), `t = title` (phim)

#### 11a

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `t.production_year BETWEEN 1950 AND 2000`
- **Output (1 dòng):** `from_company` = `MIN(cn.name)`, `movie_link_type` = `MIN(lt.link)`, `non_polish_sequel_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 38 ms · PG tác giả 59 ms
- **Test trong split:** LOO-2, RND-2

#### 11b

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follows%'`
  - `mc.note IS NULL`
  - `t.production_year = 1998`
  - `t.title LIKE '%Money%'`
- **Output (1 dòng):** `from_company` = `MIN(cn.name)`, `movie_link_type` = `MIN(lt.link)`, `sequel_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 18 ms · PG tác giả 31 ms · Bao LOO-1 72 ms
- **Test trong split:** LOO-1, RND-3

#### 11c

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '20th Century Fox%' OR cn.name LIKE 'Twentieth Century Fox%')`
  - `ct.kind != 'production companies'`
  - `ct.kind IS NOT NULL`
  - `k.keyword IN ('sequel', 'revenge', 'based-on-novel')`
  - `mc.note IS NOT NULL`
  - `t.production_year > 1950`
- **Output (1 dòng):** `from_company` = `MIN(cn.name)`, `production_note` = `MIN(mc.note)`, `movie_based_on_book` = `MIN(t.title)`
- **Thời gian:** PG nhóm 99 ms · PG tác giả 155 ms
- **Test trong split:** RND-3

#### 11d

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `ct.kind != 'production companies'`
  - `ct.kind IS NOT NULL`
  - `k.keyword IN ('sequel', 'revenge', 'based-on-novel')`
  - `mc.note IS NOT NULL`
  - `t.production_year > 1950`
- **Output (1 dòng):** `from_company` = `MIN(cn.name)`, `production_note` = `MIN(mc.note)`, `movie_based_on_book` = `MIN(t.title)`
- **Thời gian:** PG nhóm 85 ms · PG tác giả 138 ms · Bao RND-1 137 ms
- **Test trong split:** LOO-3, RND-1, RND-2

### Template 12 (12a, 12b, 12c)

**Ý nghĩa:** Phim theo thể loại (Drama/Horror…) có rating cao, của công ty sản xuất Mỹ.

**Bảng (8):** `cn = company_name` (công ty), `ct = company_type` (loại công ty), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `t = title` (phim)

#### 12a

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code = '[us]'`
  - `ct.kind = 'production companies'`
  - `it1.info = 'genres'`
  - `it2.info = 'rating'`
  - `mi.info IN ('Drama', 'Horror')`
  - `mi_idx.info > '8.0'`
  - `t.production_year BETWEEN 2005 AND 2008`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `drama_horror_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 109 ms · PG tác giả 208 ms
- **Test trong split:** BQ-3, LOO-2, LOO-3

#### 12b

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `ct.kind IS NOT NULL`
  - `(ct.kind ='production companies' OR ct.kind = 'distributors')`
  - `it1.info ='budget'`
  - `it2.info ='bottom 10 rank'`
  - `t.production_year >2000`
  - `(t.title LIKE 'Birdemic%' OR t.title LIKE '%Movie%')`
- **Output (1 dòng):** `budget` = `MIN(mi.info)`, `unsuccsessful_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 51 ms · PG tác giả 91 ms
- **Test trong split:** BQ-3

#### 12c

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `cn.country_code = '[us]'`
  - `ct.kind = 'production companies'`
  - `it1.info = 'genres'`
  - `it2.info = 'rating'`
  - `mi.info IN ('Drama', 'Horror', 'Western', 'Family')`
  - `mi_idx.info > '7.0'`
  - `t.production_year BETWEEN 2000 AND 2010`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `mainstream_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 393 ms · PG tác giả 641 ms · Bao LOO-1 641 ms
- **Test trong split:** BQ-3, LOO-1

### Template 13 (13a, 13b, 13c, 13d)

**Ý nghĩa:** Phim của công ty một nước (vd: Đức): ngày phát hành và rating.

**Bảng (9):** `cn = company_name` (công ty), `ct = company_type` (loại công ty), `it = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `kt = kind_type` (loại phim), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `miidx = movie_info_idx` (rating/votes/top 250), `t = title` (phim)

#### 13a

- **Input:** 9 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[de]'`
  - `ct.kind ='production companies'`
  - `it.info ='rating'`
  - `it2.info ='release dates'`
  - `kt.kind ='movie'`
- **Output (1 dòng):** `release_date` = `MIN(mi.info)`, `rating` = `MIN(miidx.info)`, `german_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.24 s · PG tác giả 1.31 s
- **Test trong split:** BQ-2, LOO-3

#### 13b

- **Input:** 9 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `ct.kind ='production companies'`
  - `it.info ='rating'`
  - `it2.info ='release dates'`
  - `kt.kind ='movie'`
  - `t.title != ''`
  - `(t.title LIKE '%Champion%' OR t.title LIKE '%Loser%')`
- **Output (1 dòng):** `producing_company` = `MIN(cn.name)`, `rating` = `MIN(miidx.info)`, `movie_about_winning` = `MIN(t.title)`
- **Thời gian:** PG nhóm 350 ms · PG tác giả 587 ms · Bao LOO-1 489 ms
- **Test trong split:** BQ-2, LOO-1

#### 13c

- **Input:** 9 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `ct.kind ='production companies'`
  - `it.info ='rating'`
  - `it2.info ='release dates'`
  - `kt.kind ='movie'`
  - `t.title != ''`
  - `(t.title LIKE 'Champion%' OR t.title LIKE 'Loser%')`
- **Output (1 dòng):** `producing_company` = `MIN(cn.name)`, `rating` = `MIN(miidx.info)`, `movie_about_winning` = `MIN(t.title)`
- **Thời gian:** PG nhóm 364 ms · PG tác giả 575 ms
- **Test trong split:** BQ-2, RND-2, RND-3

#### 13d

- **Input:** 9 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `ct.kind ='production companies'`
  - `it.info ='rating'`
  - `it2.info ='release dates'`
  - `kt.kind ='movie'`
- **Output (1 dòng):** `producing_company` = `MIN(cn.name)`, `rating` = `MIN(miidx.info)`, `movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.28 s · PG tác giả 1.99 s
- **Test trong split:** BQ-2, LOO-2, RND-2, RND-3

### Template 14 (14a, 14b, 14c)

**Ý nghĩa:** Phim “u tối” (từ khóa murder/blood/violence…) ở Bắc Âu/Mỹ với rating dưới một ngưỡng.

**Bảng (8):** `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `kt = kind_type` (loại phim), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 14a

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind = 'movie'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info < '8.5'`
  - `t.production_year > 2010`
- **Output (1 dòng):** `rating` = `MIN(mi_idx.info)`, `northern_dark_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 171 ms · PG tác giả 223 ms · Bao LOO-1 304 ms
- **Test trong split:** LOO-1

#### 14b

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title')`
  - `kt.kind = 'movie'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info > '6.0'`
  - `t.production_year > 2010`
  - `(t.title LIKE '%murder%' OR t.title LIKE '%Murder%' OR t.title LIKE '%Mord%')`
- **Output (1 dòng):** `rating` = `MIN(mi_idx.info)`, `western_dark_production` = `MIN(t.title)`
- **Thời gian:** PG nhóm 59 ms · PG tác giả 89 ms
- **Test trong split:** LOO-2, LOO-3

#### 14c

- **Input:** 8 bảng, 10 điều kiện nối. Điều kiện lọc:
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IS NOT NULL`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Danish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info < '8.5'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `rating` = `MIN(mi_idx.info)`, `north_european_dark_production` = `MIN(t.title)`
- **Thời gian:** PG nhóm 292 ms · PG tác giả 463 ms
- **Test trong split:** không có (chỉ nằm trong train)

### Template 15 (15a, 15b, 15c, 15d)

**Ý nghĩa:** Phim phát hành qua internet ở Mỹ: ngày phát hành.

**Bảng (9):** `aka_t = aka_title` (tên khác của phim), `cn = company_name` (công ty), `ct = company_type` (loại công ty), `it1 = info_type` (loại thông tin), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 15a

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code = '[us]'`
  - `it1.info = 'release dates'`
  - `mc.note LIKE '%(200%)%'`
  - `mc.note LIKE '%(worldwide)%'`
  - `mi.note LIKE '%internet%'`
  - `mi.info LIKE 'USA:% 200%'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `release_date` = `MIN(mi.info)`, `internet_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 182 ms · PG tác giả 278 ms · Bao RND-1 301 ms
- **Test trong split:** BQ-1, BQ-2, LOO-3, RND-1

#### 15b

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code = '[us]'`
  - `cn.name = 'YouTube'`
  - `it1.info = 'release dates'`
  - `mc.note LIKE '%(200%)%'`
  - `mc.note LIKE '%(worldwide)%'`
  - `mi.note LIKE '%internet%'`
  - `mi.info LIKE 'USA:% 200%'`
  - `t.production_year BETWEEN 2005 AND 2010`
- **Output (1 dòng):** `release_date` = `MIN(mi.info)`, `youtube_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 16 ms · PG tác giả 35 ms · Bao LOO-1 76 ms
- **Test trong split:** BQ-1, BQ-2, LOO-1, LOO-2

#### 15c

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code = '[us]'`
  - `it1.info = 'release dates'`
  - `mi.note LIKE '%internet%'`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'USA:% 199%' OR mi.info LIKE 'USA:% 200%')`
  - `t.production_year > 1990`
- **Output (1 dòng):** `release_date` = `MIN(mi.info)`, `modern_american_internet_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 956 ms · PG tác giả 556 ms
- **Test trong split:** BQ-1, BQ-2

#### 15d

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code = '[us]'`
  - `it1.info = 'release dates'`
  - `mi.note LIKE '%internet%'`
  - `t.production_year > 1990`
- **Output (1 dòng):** `aka_title` = `MIN(at.title)`, `internet_movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 284 ms · PG tác giả 730 ms
- **Test trong split:** BQ-1, BQ-2, RND-2

### Template 16 (16a, 16b, 16c, 16d)

**Ý nghĩa:** Series/tập phim có tên nhân vật trong tựa, của công ty Mỹ; lấy bí danh diễn viên.

**Bảng (8):** `an = aka_name` (tên khác của người), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 16a

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
  - `t.episode_nr >= 50`
  - `t.episode_nr < 100`
- **Output (1 dòng):** `cool_actor_pseudonym` = `MIN(an.name)`, `series_named_after_char` = `MIN(t.title)`
- **Thời gian:** PG nhóm 113 ms · PG tác giả 144 ms
- **Test trong split:** LOO-2, RND-2

#### 16b

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `cool_actor_pseudonym` = `MIN(an.name)`, `series_named_after_char` = `MIN(t.title)`
- **Thời gian:** PG nhóm 39.36 s · PG tác giả 17.53 s
- **Test trong split:** RND-3

#### 16c

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
  - `t.episode_nr < 100`
- **Output (1 dòng):** `cool_actor_pseudonym` = `MIN(an.name)`, `series_named_after_char` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.93 s · PG tác giả 1.46 s · Bao LOO-1 1.12 s
- **Test trong split:** LOO-1

#### 16d

- **Input:** 8 bảng, 11 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
  - `t.episode_nr >= 5`
  - `t.episode_nr < 100`
- **Output (1 dòng):** `cool_actor_pseudonym` = `MIN(an.name)`, `series_named_after_char` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.75 s · PG tác giả 1.14 s
- **Test trong split:** LOO-3

### Template 17 (17a, 17b, 17c, 17d, 17e, 17f)

**Ý nghĩa:** Người tham gia phim Mỹ có tên nhân vật trong tựa, tên người khớp mẫu.

**Bảng (7):** `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 17a

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
  - `n.name LIKE 'B%'`
- **Output (1 dòng):** `member_in_charnamed_american_movie` = `MIN(n.name)`, `a1` = `MIN(n.name)`
- **Thời gian:** PG nhóm 25.53 s · PG tác giả 9.63 s
- **Test trong split:** BQ-3

#### 17b

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `k.keyword ='character-name-in-title'`
  - `n.name LIKE 'Z%'`
- **Output (1 dòng):** `member_in_charnamed_movie` = `MIN(n.name)`, `a1` = `MIN(n.name)`
- **Thời gian:** PG nhóm 13.22 s · PG tác giả 4.95 s · Bao RND-1 16.25 s
- **Test trong split:** BQ-3, LOO-3, RND-1, RND-2

#### 17c

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `k.keyword ='character-name-in-title'`
  - `n.name LIKE 'X%'`
- **Output (1 dòng):** `member_in_charnamed_movie` = `MIN(n.name)`, `a1` = `MIN(n.name)`
- **Thời gian:** PG nhóm 14.31 s · PG tác giả 4.95 s · Bao LOO-1 6.10 s
- **Test trong split:** BQ-3, LOO-1

#### 17d

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `k.keyword ='character-name-in-title'`
  - `n.name LIKE '%Bert%'`
- **Output (1 dòng):** `member_in_charnamed_movie` = `MIN(n.name)`
- **Thời gian:** PG nhóm 15.37 s · PG tác giả 4.86 s
- **Test trong split:** BQ-3

#### 17e

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `cn.country_code ='[us]'`
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `member_in_charnamed_movie` = `MIN(n.name)`
- **Thời gian:** PG nhóm 18.29 s · PG tác giả 9.66 s · Bao RND-1 13.56 s
- **Test trong split:** BQ-3, RND-1

#### 17f

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `k.keyword ='character-name-in-title'`
  - `n.name LIKE '%B%'`
- **Output (1 dòng):** `member_in_charnamed_movie` = `MIN(n.name)`
- **Thời gian:** PG nhóm 20.89 s · PG tác giả 7.77 s
- **Test trong split:** BQ-3, LOO-2

### Template 18 (18a, 18b, 18c)

**Ý nghĩa:** Phim có nhà sản xuất/người tham gia khớp điều kiện; lấy budget, votes (hoặc thông tin tương tự).

**Bảng (7):** `ci = cast_info` (ai đóng/làm phim nào), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `n = name` (người), `t = title` (phim)

#### 18a

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(producer)', '(executive producer)')`
  - `it1.info = 'budget'`
  - `it2.info = 'votes'`
  - `n.gender = 'm'`
  - `n.name LIKE '%Tim%'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 48.91 s · PG tác giả 2.91 s
- **Test trong split:** LOO-2

#### 18b

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'rating'`
  - `mi.info IN ('Horror', 'Thriller')`
  - `mi.note IS NULL`
  - `mi_idx.info > '8.0'`
  - `n.gender IS NOT NULL`
  - `n.gender = 'f'`
  - `t.production_year BETWEEN 2008 AND 2014`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 97 ms · PG tác giả 167 ms · Bao LOO-1 156 ms · Bao RND-1 147 ms
- **Test trong split:** LOO-1, LOO-3, RND-1

#### 18c

- **Input:** 7 bảng, 9 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `mi.info IN ('Horror', 'Action', 'Sci-Fi', 'Thriller', 'Crime', 'War')`
  - `n.gender = 'm'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 45.60 s · PG tác giả 3.33 s
- **Test trong split:** RND-3

### Template 19 (19a, 19b, 19c, 19d)

**Ý nghĩa:** Nữ diễn viên lồng tiếng trong phim phát hành ở Nhật/Mỹ trong một khoảng năm.

**Bảng (10):** `an = aka_name` (tên khác của người), `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `it = info_type` (loại thông tin), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `n = name` (người), `rt = role_type` (vai trò), `t = title` (phim)

#### 19a

- **Input:** 10 bảng, 13 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `mc.note IS NOT NULL`
  - `(mc.note LIKE '%(USA)%' OR mc.note LIKE '%(worldwide)%')`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%200%' OR mi.info LIKE 'USA:%200%')`
  - `n.gender ='f'`
  - `n.name LIKE '%Ang%'`
  - `rt.role ='actress'`
  - `t.production_year BETWEEN 2005 AND 2009`
- **Output (1 dòng):** `voicing_actress` = `MIN(n.name)`, `voiced_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 246 ms · PG tác giả 204 ms · Bao LOO-1 365 ms
- **Test trong split:** LOO-1, RND-2

#### 19b

- **Input:** 10 bảng, 13 điều kiện nối. Điều kiện lọc:
  - `ci.note = '(voice)'`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `mc.note LIKE '%(200%)%'`
  - `(mc.note LIKE '%(USA)%' OR mc.note LIKE '%(worldwide)%')`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%2007%' OR mi.info LIKE 'USA:%2008%')`
  - `n.gender ='f'`
  - `n.name LIKE '%Angel%'`
  - `rt.role ='actress'`
  - `t.production_year BETWEEN 2007 AND 2008`
  - `t.title LIKE '%Kung%Fu%Panda%'`
- **Output (1 dòng):** `voicing_actress` = `MIN(n.name)`, `kung_fu_panda` = `MIN(t.title)`
- **Thời gian:** PG nhóm 97 ms · PG tác giả 120 ms
- **Test trong split:** không có (chỉ nằm trong train)

#### 19c

- **Input:** 10 bảng, 13 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%200%' OR mi.info LIKE 'USA:%200%')`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `voicing_actress` = `MIN(n.name)`, `jap_engl_voiced_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.65 s · PG tác giả 420 ms
- **Test trong split:** RND-3

#### 19d

- **Input:** 10 bảng, 13 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `n.gender ='f'`
  - `rt.role ='actress'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `voicing_actress` = `MIN(n.name)`, `jap_engl_voiced_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 9.43 s · PG tác giả 5.03 s
- **Test trong split:** LOO-2, LOO-3

### Template 20 (20a, 20b, 20c)

**Ý nghĩa:** Phim có nhân vật Iron Man/Tony Stark (hoặc tương tự) và danh sách cast đầy đủ.

**Bảng (10):** `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cct2 = comp_cast_type` (loại danh sách cast), `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `k = keyword` (từ khóa), `kt = kind_type` (loại phim), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 20a

- **Input:** 10 bảng, 12 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE '%complete%'`
  - `chn.name NOT LIKE '%Sherlock%'`
  - `(chn.name LIKE '%Tony%Stark%' OR chn.name LIKE '%Iron%Man%')`
  - `k.keyword IN ('superhero', 'sequel', 'second-part', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence')`
  - `kt.kind = 'movie'`
  - `t.production_year > 1950`
- **Output (1 dòng):** `complete_downey_ironman_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 4.05 s · PG tác giả 1.93 s · Bao RND-1 4.39 s
- **Test trong split:** BQ-2, LOO-2, RND-1, RND-2

#### 20b

- **Input:** 10 bảng, 12 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE '%complete%'`
  - `chn.name NOT LIKE '%Sherlock%'`
  - `(chn.name LIKE '%Tony%Stark%' OR chn.name LIKE '%Iron%Man%')`
  - `k.keyword IN ('superhero', 'sequel', 'second-part', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence')`
  - `kt.kind = 'movie'`
  - `n.name LIKE '%Downey%Robert%'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `complete_downey_ironman_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 3.77 s · PG tác giả 1.50 s
- **Test trong split:** BQ-2, LOO-3

#### 20c

- **Input:** 10 bảng, 12 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE '%complete%'`
  - `chn.name IS NOT NULL`
  - `(chn.name LIKE '%man%' OR chn.name LIKE '%Man%')`
  - `k.keyword IN ('superhero', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence', 'magnet', 'web', 'claw', 'laser')`
  - `kt.kind = 'movie'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `cast_member` = `MIN(n.name)`, `complete_dynamic_hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.13 s · PG tác giả 852 ms · Bao LOO-1 2.46 s
- **Test trong split:** BQ-2, LOO-1

### Template 21 (21a, 21b, 21c)

**Ý nghĩa:** Như template 11, thêm điều kiện thông tin quốc gia/ngôn ngữ Bắc Âu.

**Bảng (9):** `cn = company_name` (công ty), `ct = company_type` (loại công ty), `k = keyword` (từ khóa), `lt = link_type` (loại liên kết phim), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `ml = movie_link` (liên kết giữa hai phim), `t = title` (phim)

#### 21a

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German')`
  - `t.production_year BETWEEN 1950 AND 2000`
- **Output (1 dòng):** `company_name` = `MIN(cn.name)`, `link_type` = `MIN(lt.link)`, `western_follow_up` = `MIN(t.title)`
- **Thời gian:** PG nhóm 57 ms · PG tác giả 72 ms · Bao RND-1 129 ms
- **Test trong split:** LOO-3, RND-1

#### 21b

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `mi.info IN ('Germany', 'German')`
  - `t.production_year BETWEEN 2000 AND 2010`
- **Output (1 dòng):** `company_name` = `MIN(cn.name)`, `link_type` = `MIN(lt.link)`, `german_follow_up` = `MIN(t.title)`
- **Thời gian:** PG nhóm 42 ms · PG tác giả 68 ms
- **Test trong split:** LOO-2

#### 21c

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German', 'English')`
  - `t.production_year BETWEEN 1950 AND 2010`
- **Output (1 dòng):** `company_name` = `MIN(cn.name)`, `link_type` = `MIN(lt.link)`, `western_follow_up` = `MIN(t.title)`
- **Thời gian:** PG nhóm 49 ms · PG tác giả 72 ms · Bao LOO-1 119 ms
- **Test trong split:** LOO-1, RND-3

### Template 22 (22a, 22b, 22c, 22d)

**Ý nghĩa:** Phim bạo lực của công ty ngoài Mỹ, có thông tin quốc gia và rating dưới ngưỡng.

**Bảng (11):** `cn = company_name` (công ty), `ct = company_type` (loại công ty), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `kt = kind_type` (loại phim), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 22a

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mc.note NOT LIKE '%(USA)%'`
  - `mc.note LIKE '%(200%)%'`
  - `mi.info IN ('Germany', 'German', 'USA', 'American')`
  - `mi_idx.info < '7.0'`
  - `t.production_year > 2008`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `western_violent_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 275 ms · PG tác giả 387 ms
- **Test trong split:** BQ-3, LOO-3, RND-3

#### 22b

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mc.note NOT LIKE '%(USA)%'`
  - `mc.note LIKE '%(200%)%'`
  - `mi.info IN ('Germany', 'German', 'USA', 'American')`
  - `mi_idx.info < '7.0'`
  - `t.production_year > 2009`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `western_violent_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 175 ms · PG tác giả 223 ms · Bao LOO-1 263 ms
- **Test trong split:** BQ-3, LOO-1, RND-2

#### 22c

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mc.note NOT LIKE '%(USA)%'`
  - `mc.note LIKE '%(200%)%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Danish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info < '8.5'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `western_violent_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 1.23 s · PG tác giả 1.85 s
- **Test trong split:** BQ-3, LOO-2

#### 22d

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Danish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info < '8.5'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `western_violent_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 2.10 s · PG tác giả 752 ms
- **Test trong split:** BQ-3, RND-3

### Template 23 (23a, 23b, 23c)

**Ý nghĩa:** Phim Mỹ phát hành qua internet, danh sách cast đã đầy đủ và được kiểm chứng.

**Bảng (11):** `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cn = company_name` (công ty), `ct = company_type` (loại công ty), `it1 = info_type` (loại thông tin), `k = keyword` (từ khóa), `kt = kind_type` (loại phim), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 23a

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'complete+verified'`
  - `cn.country_code = '[us]'`
  - `it1.info = 'release dates'`
  - `kt.kind IN ('movie')`
  - `mi.note LIKE '%internet%'`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'USA:% 199%' OR mi.info LIKE 'USA:% 200%')`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_kind` = `MIN(kt.kind)`, `complete_us_internet_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 228 ms · PG tác giả 231 ms
- **Test trong split:** không có (chỉ nằm trong train)

#### 23b

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'complete+verified'`
  - `cn.country_code = '[us]'`
  - `it1.info = 'release dates'`
  - `k.keyword IN ('nerd', 'loner', 'alienation', 'dignity')`
  - `kt.kind IN ('movie')`
  - `mi.note LIKE '%internet%'`
  - `mi.info LIKE 'USA:% 200%'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_kind` = `MIN(kt.kind)`, `complete_nerdy_internet_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 42 ms · PG tác giả 70 ms · Bao LOO-1 134 ms
- **Test trong split:** LOO-1, LOO-2, LOO-3

#### 23c

- **Input:** 11 bảng, 16 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'complete+verified'`
  - `cn.country_code = '[us]'`
  - `it1.info = 'release dates'`
  - `kt.kind IN ('movie', 'tv movie', 'video movie', 'video game')`
  - `mi.note LIKE '%internet%'`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'USA:% 199%' OR mi.info LIKE 'USA:% 200%')`
  - `t.production_year > 1990`
- **Output (1 dòng):** `movie_kind` = `MIN(kt.kind)`, `complete_us_internet_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 3.57 s · PG tác giả 289 ms
- **Test trong split:** không có (chỉ nằm trong train)

### Template 24 (24a, 24b)

**Ý nghĩa:** Nữ diễn viên lồng tiếng trong phim hành động (hero, martial-arts…) phát hành ở Nhật/Mỹ.

**Bảng (12):** `an = aka_name` (tên khác của người), `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `it = info_type` (loại thông tin), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `rt = role_type` (vai trò), `t = title` (phim)

#### 24a

- **Input:** 12 bảng, 18 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `k.keyword IN ('hero', 'martial-arts', 'hand-to-hand-combat')`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%201%' OR mi.info LIKE 'USA:%201%')`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
  - `t.production_year > 2010`
- **Output (1 dòng):** `voiced_char_name` = `MIN(chn.name)`, `voicing_actress_name` = `MIN(n.name)`, `voiced_action_movie_jap_eng` = `MIN(t.title)`
- **Thời gian:** PG nhóm 185 ms · PG tác giả 334 ms · Bao LOO-1 620 ms
- **Test trong split:** BQ-1, LOO-1, LOO-3

#### 24b

- **Input:** 12 bảng, 18 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `cn.name = 'DreamWorks Animation'`
  - `it.info = 'release dates'`
  - `k.keyword IN ('hero', 'martial-arts', 'hand-to-hand-combat', 'computer-animated-movie')`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%201%' OR mi.info LIKE 'USA:%201%')`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
  - `t.production_year > 2010`
  - `t.title LIKE 'Kung Fu Panda%'`
- **Output (1 dòng):** `voiced_char_name` = `MIN(chn.name)`, `voicing_actress_name` = `MIN(n.name)`, `kung_fu_panda` = `MIN(t.title)`
- **Thời gian:** PG nhóm 53 ms · PG tác giả 87 ms
- **Test trong split:** BQ-1, LOO-2

### Template 25 (25a, 25b, 25c)

**Ý nghĩa:** Phim kinh dị/bạo lực có biên kịch nam; lấy thông tin phim, votes, tên biên kịch.

**Bảng (9):** `ci = cast_info` (ai đóng/làm phim nào), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 25a

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'blood', 'gore', 'death', 'female-nudity')`
  - `mi.info = 'Horror'`
  - `n.gender = 'm'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `male_writer` = `MIN(n.name)`, `violent_movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 11.58 s · PG tác giả 2.15 s · Bao LOO-1 4.53 s
- **Test trong split:** BQ-1, LOO-1, LOO-2

#### 25b

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'blood', 'gore', 'death', 'female-nudity')`
  - `mi.info = 'Horror'`
  - `n.gender = 'm'`
  - `t.production_year > 2010`
  - `t.title LIKE 'Vampire%'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `male_writer` = `MIN(n.name)`, `violent_movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm 226 ms · PG tác giả 252 ms
- **Test trong split:** BQ-1, LOO-3, RND-2

#### 25c

- **Input:** 9 bảng, 14 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mi.info IN ('Horror', 'Action', 'Sci-Fi', 'Thriller', 'Crime', 'War')`
  - `n.gender = 'm'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `male_writer` = `MIN(n.name)`, `violent_movie_title` = `MIN(t.title)`
- **Thời gian:** PG nhóm **timeout (720 s)** · PG tác giả 5.88 s · Bao RND-1 26.12 s
- **Test trong split:** BQ-1, RND-1

### Template 26 (26a, 26b, 26c)

**Ý nghĩa:** Phim siêu anh hùng có rating cao, nhân vật có tên chứa “man”, cast đầy đủ.

**Bảng (12):** `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cct2 = comp_cast_type` (loại danh sách cast), `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `kt = kind_type` (loại phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 26a

- **Input:** 12 bảng, 17 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE '%complete%'`
  - `chn.name IS NOT NULL`
  - `(chn.name LIKE '%man%' OR chn.name LIKE '%Man%')`
  - `it2.info = 'rating'`
  - `k.keyword IN ('superhero', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence', 'magnet', 'web', 'claw', 'laser')`
  - `kt.kind = 'movie'`
  - `mi_idx.info > '7.0'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `character_name` = `MIN(chn.name)`, `rating` = `MIN(mi_idx.info)`, `playing_actor` = `MIN(n.name)`, `complete_hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 3.70 s · PG tác giả 964 ms
- **Test trong split:** BQ-2, LOO-2, LOO-3, RND-3

#### 26b

- **Input:** 12 bảng, 17 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE '%complete%'`
  - `chn.name IS NOT NULL`
  - `(chn.name LIKE '%man%' OR chn.name LIKE '%Man%')`
  - `it2.info = 'rating'`
  - `k.keyword IN ('superhero', 'marvel-comics', 'based-on-comic', 'fight')`
  - `kt.kind = 'movie'`
  - `mi_idx.info > '8.0'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `character_name` = `MIN(chn.name)`, `rating` = `MIN(mi_idx.info)`, `complete_hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 100 ms · PG tác giả 139 ms
- **Test trong split:** BQ-2, RND-3

#### 26c

- **Input:** 12 bảng, 17 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE '%complete%'`
  - `chn.name IS NOT NULL`
  - `(chn.name LIKE '%man%' OR chn.name LIKE '%Man%')`
  - `it2.info = 'rating'`
  - `k.keyword IN ('superhero', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence', 'magnet', 'web', 'claw', 'laser')`
  - `kt.kind = 'movie'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `character_name` = `MIN(chn.name)`, `rating` = `MIN(mi_idx.info)`, `complete_hero_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 6.03 s · PG tác giả 1.79 s · Bao LOO-1 1.86 s
- **Test trong split:** BQ-2, LOO-1

### Template 27 (27a, 27b, 27c)

**Ý nghĩa:** Như template 21, thêm điều kiện danh sách cast/crew đầy đủ.

**Bảng (12):** `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cct2 = comp_cast_type` (loại danh sách cast), `cn = company_name` (công ty), `ct = company_type` (loại công ty), `k = keyword` (từ khóa), `lt = link_type` (loại liên kết phim), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `ml = movie_link` (liên kết giữa hai phim), `t = title` (phim)

#### 27a

- **Input:** 12 bảng, 21 điều kiện nối. Điều kiện lọc:
  - `cct1.kind IN ('cast', 'crew')`
  - `cct2.kind = 'complete'`
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `mi.info IN ('Sweden', 'Germany', 'Swedish', 'German')`
  - `t.production_year BETWEEN 1950 AND 2000`
- **Output (1 dòng):** `producing_company` = `MIN(cn.name)`, `link_type` = `MIN(lt.link)`, `complete_western_sequel` = `MIN(t.title)`
- **Thời gian:** PG nhóm 58 ms · PG tác giả 77 ms
- **Test trong split:** BQ-3, LOO-3

#### 27b

- **Input:** 12 bảng, 21 điều kiện nối. Điều kiện lọc:
  - `cct1.kind IN ('cast', 'crew')`
  - `cct2.kind = 'complete'`
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `mi.info IN ('Sweden', 'Germany', 'Swedish', 'German')`
  - `t.production_year = 1998`
- **Output (1 dòng):** `producing_company` = `MIN(cn.name)`, `link_type` = `MIN(lt.link)`, `complete_western_sequel` = `MIN(t.title)`
- **Thời gian:** PG nhóm 99 ms · PG tác giả 69 ms
- **Test trong split:** BQ-3, LOO-2

#### 27c

- **Input:** 12 bảng, 21 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind LIKE 'complete%'`
  - `cn.country_code !='[pl]'`
  - `(cn.name LIKE '%Film%' OR cn.name LIKE '%Warner%')`
  - `ct.kind ='production companies'`
  - `k.keyword ='sequel'`
  - `lt.link LIKE '%follow%'`
  - `mc.note IS NULL`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Denish', 'Norwegian', 'German', 'English')`
  - `t.production_year BETWEEN 1950 AND 2010`
- **Output (1 dòng):** `producing_company` = `MIN(cn.name)`, `link_type` = `MIN(lt.link)`, `complete_western_sequel` = `MIN(t.title)`
- **Thời gian:** PG nhóm 41 ms · PG tác giả 84 ms · Bao LOO-1 176 ms
- **Test trong split:** BQ-3, LOO-1, RND-3

### Template 28 (28a, 28b, 28c)

**Ý nghĩa:** Phim bạo lực châu Âu của công ty ngoài Mỹ, crew chưa được kiểm chứng đầy đủ.

**Bảng (14):** `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cct2 = comp_cast_type` (loại danh sách cast), `cn = company_name` (công ty), `ct = company_type` (loại công ty), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `kt = kind_type` (loại phim), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `t = title` (phim)

#### 28a

- **Input:** 14 bảng, 23 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'crew'`
  - `cct2.kind != 'complete+verified'`
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mc.note NOT LIKE '%(USA)%'`
  - `mc.note LIKE '%(200%)%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Danish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info < '8.5'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `complete_euro_dark_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 489 ms · PG tác giả 1.82 s · Bao LOO-1 525 ms
- **Test trong split:** BQ-3, LOO-1, RND-3

#### 28b

- **Input:** 14 bảng, 23 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'crew'`
  - `cct2.kind != 'complete+verified'`
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mc.note NOT LIKE '%(USA)%'`
  - `mc.note LIKE '%(200%)%'`
  - `mi.info IN ('Sweden', 'Germany', 'Swedish', 'German')`
  - `mi_idx.info > '6.5'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `complete_euro_dark_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 330 ms · PG tác giả 647 ms · Bao RND-1 697 ms
- **Test trong split:** BQ-3, LOO-3, RND-1

#### 28c

- **Input:** 14 bảng, 23 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind = 'complete'`
  - `cn.country_code != '[us]'`
  - `it1.info = 'countries'`
  - `it2.info = 'rating'`
  - `k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')`
  - `kt.kind IN ('movie', 'episode')`
  - `mc.note NOT LIKE '%(USA)%'`
  - `mc.note LIKE '%(200%)%'`
  - `mi.info IN ('Sweden', 'Norway', 'Germany', 'Denmark', 'Swedish', 'Danish', 'Norwegian', 'German', 'USA', 'American')`
  - `mi_idx.info < '8.5'`
  - `t.production_year > 2005`
- **Output (1 dòng):** `movie_company` = `MIN(cn.name)`, `rating` = `MIN(mi_idx.info)`, `complete_euro_dark_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 487 ms · PG tác giả 979 ms
- **Test trong split:** BQ-3, LOO-2, RND-3

### Template 29 (29a, 29b, 29c)

**Ý nghĩa:** Nữ diễn viên lồng tiếng một nhân vật cụ thể trong phim hoạt hình (vd: “Queen” trong Shrek 2). Template có nhiều bảng nhất (17).

**Bảng (17):** `an = aka_name` (tên khác của người), `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cct2 = comp_cast_type` (loại danh sách cast), `chn = char_name` (tên nhân vật), `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `it = info_type` (loại thông tin), `it3 = info_type` (loại thông tin), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `pi = person_info` (thông tin người), `rt = role_type` (vai trò), `t = title` (phim)

#### 29a

- **Input:** 17 bảng, 28 điều kiện nối. Điều kiện lọc:
  - `cct1.kind ='cast'`
  - `cct2.kind ='complete+verified'`
  - `chn.name = 'Queen'`
  - `ci.note IN ('(voice)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `it3.info = 'trivia'`
  - `k.keyword = 'computer-animation'`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%200%' OR mi.info LIKE 'USA:%200%')`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
  - `t.title = 'Shrek 2'`
  - `t.production_year BETWEEN 2000 AND 2010`
- **Output (1 dòng):** `voiced_char` = `MIN(chn.name)`, `voicing_actress` = `MIN(n.name)`, `voiced_animation` = `MIN(t.title)`
- **Thời gian:** PG nhóm 121 ms · PG tác giả 138 ms
- **Test trong split:** BQ-2, LOO-2

#### 29b

- **Input:** 17 bảng, 28 điều kiện nối. Điều kiện lọc:
  - `cct1.kind ='cast'`
  - `cct2.kind ='complete+verified'`
  - `chn.name = 'Queen'`
  - `ci.note IN ('(voice)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `it3.info = 'height'`
  - `k.keyword = 'computer-animation'`
  - `mi.info LIKE 'USA:%200%'`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
  - `t.title = 'Shrek 2'`
  - `t.production_year BETWEEN 2000 AND 2005`
- **Output (1 dòng):** `voiced_char` = `MIN(chn.name)`, `voicing_actress` = `MIN(n.name)`, `voiced_animation` = `MIN(t.title)`
- **Thời gian:** PG nhóm 143 ms · PG tác giả 107 ms · Bao LOO-1 330 ms
- **Test trong split:** BQ-2, LOO-1, RND-2

#### 29c

- **Input:** 17 bảng, 28 điều kiện nối. Điều kiện lọc:
  - `cct1.kind ='cast'`
  - `cct2.kind ='complete+verified'`
  - `ci.note IN ('(voice)', '(voice: Japanese version)', '(voice) (uncredited)', '(voice: English version)')`
  - `cn.country_code ='[us]'`
  - `it.info = 'release dates'`
  - `it3.info = 'trivia'`
  - `k.keyword = 'computer-animation'`
  - `mi.info IS NOT NULL`
  - `(mi.info LIKE 'Japan:%200%' OR mi.info LIKE 'USA:%200%')`
  - `n.gender ='f'`
  - `n.name LIKE '%An%'`
  - `rt.role ='actress'`
  - `t.production_year BETWEEN 2000 AND 2010`
- **Output (1 dòng):** `voiced_char` = `MIN(chn.name)`, `voicing_actress` = `MIN(n.name)`, `voiced_animation` = `MIN(t.title)`
- **Thời gian:** PG nhóm 213 ms · PG tác giả 590 ms
- **Test trong split:** BQ-2, LOO-3

### Template 30 (30a, 30b, 30c)

**Ý nghĩa:** Phim kinh dị/thriller bạo lực có biên kịch nam và cast đã kiểm chứng đầy đủ.

**Bảng (12):** `cc = complete_cast` (độ đầy đủ của cast), `cct1 = comp_cast_type` (loại danh sách cast), `cct2 = comp_cast_type` (loại danh sách cast), `ci = cast_info` (ai đóng/làm phim nào), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 30a

- **Input:** 12 bảng, 21 điều kiện nối. Điều kiện lọc:
  - `cct1.kind IN ('cast', 'crew')`
  - `cct2.kind ='complete+verified'`
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mi.info IN ('Horror', 'Thriller')`
  - `n.gender = 'm'`
  - `t.production_year > 2000`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `writer` = `MIN(n.name)`, `complete_violent_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 9.87 s · PG tác giả 2.41 s · Bao LOO-1 6.53 s
- **Test trong split:** BQ-2, LOO-1, LOO-3, RND-3

#### 30b

- **Input:** 12 bảng, 21 điều kiện nối. Điều kiện lọc:
  - `cct1.kind IN ('cast', 'crew')`
  - `cct2.kind ='complete+verified'`
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mi.info IN ('Horror', 'Thriller')`
  - `n.gender = 'm'`
  - `t.production_year > 2000`
  - `(t.title LIKE '%Freddy%' OR t.title LIKE '%Jason%' OR t.title LIKE 'Saw%')`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `writer` = `MIN(n.name)`, `complete_gore_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 304 ms · PG tác giả 392 ms
- **Test trong split:** BQ-2, LOO-2

#### 30c

- **Input:** 12 bảng, 21 điều kiện nối. Điều kiện lọc:
  - `cct1.kind = 'cast'`
  - `cct2.kind ='complete+verified'`
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mi.info IN ('Horror', 'Action', 'Sci-Fi', 'Thriller', 'Crime', 'War')`
  - `n.gender = 'm'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `writer` = `MIN(n.name)`, `complete_violent_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 6.53 s · PG tác giả 2.03 s
- **Test trong split:** BQ-2

### Template 31 (31a, 31b, 31c)

**Ý nghĩa:** Như template 30 nhưng giới hạn công ty Lionsgate.

**Bảng (11):** `ci = cast_info` (ai đóng/làm phim nào), `cn = company_name` (công ty), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `k = keyword` (từ khóa), `mc = movie_companies` (phim–công ty), `mi = movie_info` (thông tin phim), `mi_idx = movie_info_idx` (rating/votes/top 250), `mk = movie_keyword` (phim–từ khóa), `n = name` (người), `t = title` (phim)

#### 31a

- **Input:** 11 bảng, 20 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `cn.name LIKE 'Lionsgate%'`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mi.info IN ('Horror', 'Thriller')`
  - `n.gender = 'm'`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `writer` = `MIN(n.name)`, `violent_liongate_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 153 ms · PG tác giả 250 ms
- **Test trong split:** BQ-1, LOO-2, LOO-3, RND-2

#### 31b

- **Input:** 11 bảng, 20 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `cn.name LIKE 'Lionsgate%'`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mc.note LIKE '%(Blu-ray)%'`
  - `mi.info IN ('Horror', 'Thriller')`
  - `n.gender = 'm'`
  - `t.production_year > 2000`
  - `(t.title LIKE '%Freddy%' OR t.title LIKE '%Jason%' OR t.title LIKE 'Saw%')`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `writer` = `MIN(n.name)`, `violent_liongate_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 91 ms · PG tác giả 159 ms · Bao LOO-1 209 ms
- **Test trong split:** BQ-1, LOO-1

#### 31c

- **Input:** 11 bảng, 20 điều kiện nối. Điều kiện lọc:
  - `ci.note IN ('(writer)', '(head writer)', '(written by)', '(story)', '(story editor)')`
  - `cn.name LIKE 'Lionsgate%'`
  - `it1.info = 'genres'`
  - `it2.info = 'votes'`
  - `k.keyword IN ('murder', 'violence', 'blood', 'gore', 'death', 'female-nudity', 'hospital')`
  - `mi.info IN ('Horror', 'Action', 'Sci-Fi', 'Thriller', 'Crime', 'War')`
- **Output (1 dòng):** `movie_budget` = `MIN(mi.info)`, `movie_votes` = `MIN(mi_idx.info)`, `writer` = `MIN(n.name)`, `violent_liongate_movie` = `MIN(t.title)`
- **Thời gian:** PG nhóm 247 ms · PG tác giả 394 ms
- **Test trong split:** BQ-1

### Template 32 (32a, 32b)

**Ý nghĩa:** Phim có một từ khóa cụ thể và các phim được liên kết với nó.

**Bảng (6):** `k = keyword` (từ khóa), `lt = link_type` (loại liên kết phim), `mk = movie_keyword` (phim–từ khóa), `ml = movie_link` (liên kết giữa hai phim), `t1 = title` (phim), `t2 = title` (phim)

#### 32a

- **Input:** 6 bảng, 6 điều kiện nối. Điều kiện lọc:
  - `k.keyword ='10,000-mile-club'`
- **Output (1 dòng):** `link_type` = `MIN(lt.link)`, `first_movie` = `MIN(t1.title)`, `second_movie` = `MIN(t2.title)`
- **Thời gian:** PG nhóm 6 ms · PG tác giả 11 ms
- **Test trong split:** LOO-3

#### 32b

- **Input:** 6 bảng, 6 điều kiện nối. Điều kiện lọc:
  - `k.keyword ='character-name-in-title'`
- **Output (1 dòng):** `link_type` = `MIN(lt.link)`, `first_movie` = `MIN(t1.title)`, `second_movie` = `MIN(t2.title)`
- **Thời gian:** PG nhóm 64 ms · PG tác giả 94 ms · Bao LOO-1 110 ms · Bao RND-1 135 ms
- **Test trong split:** LOO-1, LOO-2, RND-1, RND-2

### Template 33 (33a, 33b, 33c)

**Ý nghĩa:** Cặp series/phim liên kết (sequel/follows…) cùng rating và công ty của cả hai phim.

**Bảng (14):** `cn1 = company_name` (công ty), `cn2 = company_name` (công ty), `it1 = info_type` (loại thông tin), `it2 = info_type` (loại thông tin), `kt1 = kind_type` (loại phim), `kt2 = kind_type` (loại phim), `lt = link_type` (loại liên kết phim), `mc1 = movie_companies` (phim–công ty), `mc2 = movie_companies` (phim–công ty), `mi_idx1 = movie_info_idx` (rating/votes/top 250), `mi_idx2 = movie_info_idx` (rating/votes/top 250), `ml = movie_link` (liên kết giữa hai phim), `t1 = title` (phim), `t2 = title` (phim)

#### 33a

- **Input:** 14 bảng, 19 điều kiện nối. Điều kiện lọc:
  - `cn1.country_code = '[us]'`
  - `it1.info = 'rating'`
  - `it2.info = 'rating'`
  - `kt1.kind IN ('tv series')`
  - `kt2.kind IN ('tv series')`
  - `lt.link IN ('sequel', 'follows', 'followed by')`
  - `mi_idx2.info < '3.0'`
  - `t2.production_year BETWEEN 2005 AND 2008`
- **Output (1 dòng):** `first_company` = `MIN(cn1.name)`, `second_company` = `MIN(cn2.name)`, `first_rating` = `MIN(mi_idx1.info)`, `second_rating` = `MIN(mi_idx2.info)`, `first_movie` = `MIN(t1.title)`, `second_movie` = `MIN(t2.title)`
- **Thời gian:** PG nhóm 71 ms · PG tác giả 115 ms · Bao RND-1 233 ms
- **Test trong split:** BQ-2, RND-1

#### 33b

- **Input:** 14 bảng, 19 điều kiện nối. Điều kiện lọc:
  - `cn1.country_code = '[nl]'`
  - `it1.info = 'rating'`
  - `it2.info = 'rating'`
  - `kt1.kind IN ('tv series')`
  - `kt2.kind IN ('tv series')`
  - `lt.link LIKE '%follow%'`
  - `mi_idx2.info < '3.0'`
  - `t2.production_year = 2007`
- **Output (1 dòng):** `first_company` = `MIN(cn1.name)`, `second_company` = `MIN(cn2.name)`, `first_rating` = `MIN(mi_idx1.info)`, `second_rating` = `MIN(mi_idx2.info)`, `first_movie` = `MIN(t1.title)`, `second_movie` = `MIN(t2.title)`
- **Thời gian:** PG nhóm 68 ms · PG tác giả 109 ms
- **Test trong split:** BQ-2, LOO-2

#### 33c

- **Input:** 14 bảng, 19 điều kiện nối. Điều kiện lọc:
  - `cn1.country_code != '[us]'`
  - `it1.info = 'rating'`
  - `it2.info = 'rating'`
  - `kt1.kind IN ('tv series', 'episode')`
  - `kt2.kind IN ('tv series', 'episode')`
  - `lt.link IN ('sequel', 'follows', 'followed by')`
  - `mi_idx2.info < '3.5'`
  - `t2.production_year BETWEEN 2000 AND 2010`
- **Output (1 dòng):** `first_company` = `MIN(cn1.name)`, `second_company` = `MIN(cn2.name)`, `first_rating` = `MIN(mi_idx1.info)`, `second_rating` = `MIN(mi_idx2.info)`, `first_movie` = `MIN(t1.title)`, `second_movie` = `MIN(t2.title)`
- **Thời gian:** PG nhóm 59 ms · PG tác giả 124 ms · Bao LOO-1 256 ms
- **Test trong split:** BQ-2, LOO-1, LOO-3, RND-3
