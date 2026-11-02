# Ghi chú: CSDL IMDB, benchmark JOB và kết quả tái lập

Tổng hợp các câu hỏi đáp ngày 02–03/11/2026 về CSDL IMDB và kết quả thực nghiệm Bao.

---

## 1. Xem CSDL IMDB ở đâu?

CSDL nằm trong container Docker **`pg_bao`** (image `pg_lqo_arm64`, PostgreSQL 12.5, cổng `5432`):

- Database: **`imdbload`**, khoảng **12 GB**, 21 bảng
- Container `pg_bao` còn có database `company`; ngoài ra Postgres có các database hệ thống `postgres`, `template0`, `template1`

Cách vào:

```bash
docker exec -it pg_bao psql -U postgres -d imdbload
```

Trong `psql`: `\dt` liệt kê bảng, `\d title` xem cấu trúc bảng.
Có thể dùng DBeaver, pgAdmin hoặc TablePlus: host `localhost:5432`, user `postgres`, database `imdbload`.

### Các bảng

| Bảng | Số dòng (ước tính) | Dung lượng | Nội dung |
|---|---:|---:|---|
| `cast_info` | 36,2 triệu | 6,4 GB | Ai tham gia phim nào, với vai trò gì |
| `movie_info` | 14,8 triệu | 2,4 GB | Thông tin phim: thể loại, quốc gia, ngân sách… |
| `movie_keyword` | 4,5 triệu | 573 MB | Nối phim với từ khóa |
| `name` | 4,2 triệu | 552 MB | Người (có giới tính) |
| `char_name` | 3,1 triệu | 373 MB | Tên nhân vật |
| `person_info` | 3,0 triệu | 672 MB | Tiểu sử, ngày sinh… |
| `movie_companies` | 2,6 triệu | 401 MB | Nối phim với công ty |
| `title` | 2,5 triệu | 403 MB | Phim/tập phim |
| `movie_info_idx` | 1,4 triệu | 168 MB | Rating, số lượt bình chọn, top 250 |
| `aka_name` / `aka_title` | 901K / 361K | | Tên khác của người / của phim |
| `company_name` | 235K | 30 MB | Công ty (có mã quốc gia) |
| `complete_cast` | 135K | | |
| `keyword` | 134K | | Từ khóa |
| `movie_link` | 30K | | Liên kết giữa các phim (sequel, remake…) |
| Bảng tra cứu | 4–113 | | `info_type`, `link_type`, `role_type`, `kind_type`, `comp_cast_type`, `company_type` |

Bảng trung tâm là `title`. Các bảng `movie_*` và `cast_info` nối với nó qua `movie_id`. `cast_info` nối với `name` qua `person_id` và với `role_type` qua `role_id`.

> ⚠️ `pg_stat_user_tables` đang báo 0 dòng cho mọi bảng, có lẽ vì thống kê bị xóa khi container khởi động lại. Nên chạy `ANALYZE;` trước khi chạy thực nghiệm (xem mục 5).

---

## 2. Đây có phải là benchmark không?

Có. IMDB là dữ liệu của **Join Order Benchmark (JOB)** (Leis et al., VLDB 2015).

- **IMDB** là cơ sở dữ liệu.
- **JOB** là **113 truy vấn SQL** viết tay (1a…33c) chạy trên dữ liệu đó. Mỗi truy vấn nối từ 4 đến 17 bảng. Các truy vấn nằm trong `lqo_ml_perspective/*/queries/join-order-benchmark*/`.
- Bài báo đang tái lập (Lehmann et al., PVLDB 2024) dùng JOB làm benchmark chính. CEB-IMDb cũng dùng được trên cùng CSDL này.

### Các thực nghiệm đã chạy (11–12/10/2026, log trong [logs/](logs/))

| Thực nghiệm | Trạng thái |
|---|---|
| Baseline PostgreSQL, 113 truy vấn × 3 lần ([test__postgres__job__20261011_1743.txt](logs/test__postgres__job__20261011_1743.txt)) | ✅ Xong |
| Bao, split Leave-One-Out 1: train khoảng 3,75 giờ, test 33 truy vấn | ✅ Xong |
| Bao, split Random 1: train khoảng 2,8 giờ, test 22 truy vấn | ✅ Xong |
| Bao, split Base Query 1 | ⚠️ Dừng ở vòng train 9/19, chưa có kết quả test |
| C1 trên log của tác giả ([analysis/output/c1_authors_*.csv](analysis/output/)) | ✅ Xong |
| Ghi log plan, C2/C3, ablation, CEB trên IMDB thật | ❌ Chưa có kết quả |

---

## 3. Input và output là gì?

### Bài toán tối ưu truy vấn
- **Input:** một câu SQL cùng với CSDL `imdbload`. Ví dụ JOB 1a:
  ```sql
  SELECT MIN(mc.note), MIN(t.title), MIN(t.production_year)
  FROM company_type ct, info_type it, movie_companies mc, movie_info_idx mi_idx, title t
  WHERE ct.kind = 'production companies' AND it.info = 'top 250 rank'
    AND ct.id = mc.company_type_id AND t.id = mc.movie_id AND ...
  ```
- **Output:** một **query plan**, gồm thứ tự nối các bảng, thuật toán nối (Hash Join, Nested Loop, Merge Join) và cách quét bảng (Seq Scan, Index Scan).
- **Thước đo:** thời gian chạy (ms). Kết quả của câu SQL thì giống nhau với mọi plan.

### Thực nghiệm Bao

```
SQL ──► PostgreSQL sinh 49 plan ứng viên, mỗi plan ứng với một hint set (vd: SET enable_nestloop TO off)
    ──► Mô hình Bao (Tree CNN) dự đoán latency của từng plan
    ──► Chọn plan có dự đoán nhanh nhất ──► chạy và đo thời gian
```

- **Input khi train:** các truy vấn trong `lqo_ml_perspective/bao/queries/job__<split>/train/`
- **Input khi test:** các truy vấn trong `.../test/`, mô hình chưa thấy khi train
- **Output:** mỗi dòng log có dạng
  ```
  hint set,                     lần chạy, thời điểm,  truy vấn,     planning ms, execution ms, hệ thống
  SET enable_nestloop TO off; , 0,        2026-10-12…, test/9c.sql,  87.311,      14589.504,    Bao
  ```
  Baseline PostgreSQL có cùng định dạng, với cột hint là `x` và hệ thống là `PG`.
- **Ba loại split:**
  - Random: chia ngẫu nhiên.
  - Leave-One-Out: mỗi template có một truy vấn nằm trong tập test.
  - Base Query: các truy vấn cùng template không được nằm ở cả train lẫn test. Đây là split khó nhất.

### Phần data mining
- **Input:** [analysis/output/app/dataset_a.csv](analysis/output/app/dataset_a.csv), mỗi dòng là một truy vấn, gồm:
  - đặc trưng của SQL (`sql_n_tables`, `sql_n_like`, `sql_n_or`…)
  - đặc trưng của plan mặc định (`plan_n_hashjoin`, `plan_n_nestloop`…)
  - thời gian chạy của từng hệ thống (`t_PostgreSQL`, `t_Bao`, `t_Neo`, `t_Balsa`, `t_LEON`, `t_HybridQO`)
- **Output:**
  - C1: thống kê thắng/thua giữa LQO và PostgreSQL
  - C2: bộ phân loại dự đoán nên dùng LQO hay PostgreSQL (nhãn là `best_hint_set`)
  - C3: giải thích những đặc trưng nào khiến LQO thắng hoặc thua

---

## 4. Dữ liệu có dạng như thế nào? (ví dụ: The Matrix, 1999)

**`title`**

| id | title | kind_id | production_year |
|---|---|---|---|
| 2392833 | The Matrix | 1 (movie) | 1999 |

**`cast_info`** nối với `name`, `role_type`, `char_name` (phim này có 150 dòng):

| person_id | name | gender | role | nhân vật | nr_order | note |
|---|---|---|---|---|---|---|
| 1288968 | Reeves, Keanu | m | actor | Neo | 1 | |
| 491079 | Fishburne, Laurence | m | actor | Morpheus | 2 | |
| 2343905 | Moss, Carrie-Anne | f | actress | Trinity | 3 | |
| 1637226 | Wachowski, Andy | m | director | | | (as The Wachowski Brothers) |

**`movie_info` / `movie_info_idx`** lưu thông tin dạng key–value. Loại thông tin được xác định bởi `info_type`; giá trị luôn nằm trong cột `info` kiểu text. Phim này có 606 dòng trong `movie_info`.

| info_type | info |
|---|---|
| languages | English |
| runtimes | 136 |
| release dates | USA:31 March 1999 |
| rating | 8.7 |
| votes | 697812 |
| top 250 rank | 19 |

**`movie_keyword` → `keyword`:** `1990s`, `20th-century`, `2190s`… (247 keyword)
**`movie_companies` → `company_name`:** `Argentina Video Home`, mã quốc gia `[ar]`, loại `distributors`, note `(1999) (Argentina) (DVD)`

### Vì sao dữ liệu này làm khó optimizer?
- **Tương quan giữa các cột:** ví dụ `country_code='[jp]'` đi kèm keyword về anime, trong khi PostgreSQL giả định các điều kiện độc lập với nhau.
- **Phân phối lệch:** phim nổi tiếng có hàng trăm dòng, nhiều tập phim nhỏ chỉ có một hai dòng.
- **Nhiều điều kiện `LIKE` trên chuỗi**, rất khó ước lượng.

Hệ quả là PostgreSQL ước lượng sai số dòng, chọn sai thứ tự nối hoặc sai thuật toán nối. LQO như Bao được đề xuất để sửa đúng lỗi này.

---

## 5. Kết quả tái lập có giống tác giả không?

So sánh bằng [scripts/compare_baseline.py](scripts/compare_baseline.py) và [scripts/c1_win_loss.py](scripts/c1_win_loss.py), dùng lần chạy thứ 3 (cache đã nóng), thời gian end-to-end, với log tác giả trong `lqo_ml_perspective/experiment_logs/20240103__combined.csv`.

**Kết luận ngắn:** kết luận chính của bài báo được tái lập được, tức là Bao thua PostgreSQL ở đa số truy vấn. Các con số tổng thời gian thì không khớp, vì baseline PostgreSQL của nhóm có vài truy vấn chạy chậm bất thường.

### 5.1 Baseline PostgreSQL (113 truy vấn)

| Chỉ số | Nhóm | Tác giả |
|---|---:|---:|
| Tổng thời gian | **1110 s** | 141 s |
| Tổng thời gian khi bỏ 25c | 390 s | 135 s |
| Tỉ lệ thời gian (nhóm / tác giả), trung vị theo truy vấn | **0,79** | – |
| Tương quan thứ hạng Spearman | **ρ = 0,97** | – |
| Số câu khớp ±25% / chậm hơn / nhanh hơn | 27 / 39 / 47 | – |

- **Phần khớp:** thứ tự khó/dễ của các truy vấn gần như giống hệt tác giả. Một truy vấn điển hình của nhóm còn chạy nhanh hơn tác giả khoảng 20%.
- **Phần lệch:** tổng thời gian cao gấp khoảng 8 lần, do vài truy vấn:

  | Truy vấn | Nhóm | Tác giả | Tỉ lệ |
  |---|---:|---:|---:|
  | 25c | 720 s (**timeout**) | 5,9 s | 122× |
  | 18a | 48,9 s | 2,9 s | 17× |
  | 18c | 45,6 s | 3,3 s | 14× |
  | 23c | 3,6 s | 0,29 s | 12× |
  | 8a | 6,3 s | 0,70 s | 9× |

  Chậm đến mức này thường có nghĩa là PostgreSQL đã **chọn một plan khác hẳn**. Nguyên nhân khả dĩ là thiếu thống kê (chưa `ANALYZE`), cấu hình bộ nhớ khác, hoặc khác phần cứng (M1 so với server của tác giả).

### 5.2 Bao so với PostgreSQL trên các truy vấn test

Thắng/thua được tính với ngưỡng ±10%. Speedup lớn hơn 1 nghĩa là Bao nhanh hơn PostgreSQL.

| Split | | Thắng / Hòa / Thua | Speedup trung vị theo truy vấn | Speedup theo tổng thời gian | p (sign test) |
|---|---|---:|---:|---:|---:|
| **Random 1** (22 câu) | Nhóm | **3 / 2 / 17** | 0,60 | 10,05 (0,89 nếu bỏ 25c) | 0,003 |
| | Tác giả | **3 / 2 / 17** | 0,36 | 1,25 | 0,003 |
| **Leave-One-Out 1** (33 câu) | Nhóm | 7 / 3 / 23 | 0,61 | 1,61 | 0,005 |
| | Tác giả | 2 / 3 / 28 | 0,43 | 0,78 | < 0,001 |

- **Khớp với tác giả:**
  - Bao thua ở đa số truy vấn. Kết quả của Random 1 **trùng hoàn toàn** với tác giả (3/2/17).
  - Speedup trung vị nhỏ hơn 1, tức với một truy vấn điển hình Bao chậm hơn PostgreSQL.
  - Sign test có ý nghĩa thống kê.
- **Không khớp:**
  - Ở Random 1, Bao "nhanh gấp 10 lần" chỉ vì PostgreSQL timeout ở 25c (PG 720 s, Bao 26 s). Bỏ 25c ra thì Bao chậm hơn (0,89), đúng với xu hướng của tác giả.
  - Ở Leave-One-Out 1, Bao thắng 7 câu thay vì 2. Đó là các câu 17c, 25a, 26c, 30a, trong đó PostgreSQL của nhóm chạy chậm hơn bình thường.

### 5.3 Còn thiếu
- **Split Base Query 1 chưa xong.** Đây là split mà bài báo nhấn mạnh là khó nhất.
- Mỗi loại split mới chạy 1 lần chia, trong khi tác giả chạy 3.

### 5.4 Việc nên làm tiếp
1. Chạy `ANALYZE;` trên `imdbload`, rồi chạy lại baseline PostgreSQL. Kiểm tra 25c, 18a, 18c bằng `EXPLAIN` để xem plan có thay đổi không.
2. Chạy lại cho xong split Base Query 1 (`scripts/run_bao_split.sh`).
3. Trong báo cáo, dùng **số thắng/thua và speedup trung vị** làm thước đo chính. Tổng thời gian thì ghi kèm chú thích về 25c.

### Ghi chú kỹ thuật
- Python trong `analysis/.venv` (trỏ tới `/opt/miniconda3/bin/python3`) bị treo ngay khi khởi động. Các script so sánh ở trên được chạy bằng `python3` của hệ thống (pandas 3.0.3, scipy 1.17.0).
- Lệnh tái tạo kết quả:
  ```bash
  python3 scripts/compare_baseline.py --ours logs/test__postgres__job__20261011_1743.txt \
      --authors lqo_ml_perspective/experiment_logs/20240103__combined.csv --out_dir analysis/output
  python3 scripts/c1_win_loss.py --baseline txt:logs/test__postgres__job__20261011_1743.txt \
      --candidate txt:logs/test__bao__job__random_split_1__20261012_0602.txt --name Bao_RND1 --out_dir analysis/output
  python3 scripts/c1_win_loss.py --baseline txt:logs/test__postgres__job__20261011_1743.txt \
      --candidate txt:logs/test__bao__job__leave_one_out_split_1__20261012_0213.txt --name Bao_LOO1 --out_dir analysis/output
  ```
