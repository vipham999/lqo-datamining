# 4. CODE VÀ TÁI LẬP THỰC NGHIỆM

> **Phụ trách:** Phạm Thúy Vi
> **Quy ước:** `(§x.y)` là mục trong bài báo của Lehmann và cộng sự (PVLDB 2024).

## 4.1. Mục tiêu

Phần này đề xuất cách tái lập thực nghiệm của bài báo và mở rộng thêm một hướng phân tích. Nhóm đặt ra ba mục tiêu:

1. **Tái lập:** kiểm tra xem kết luận chính của bài báo, *"PostgreSQL nhìn chung vẫn tốt nhất, theo sau là HybridQO, Bao, Neo, Balsa và LEON"* (§8.2.1), có còn đúng trên một nền tảng phần cứng khác hay không.
2. **Đo plan mới nhanh hơn bao nhiêu:** với từng câu truy vấn, chỉ ra **plan thực thi cũ** (của PostgreSQL), **plan tối ưu** tìm được, và **mức tăng tốc** giữa hai plan.
3. **Phân loại plan bằng data mining:** dự đoán trước mỗi câu truy vấn nên dùng plan nào, rồi **đếm số câu dự đoán đúng**. Mục đích là chứng minh bằng thuật toán, thay vì liệt kê thủ công từng câu.

Nhóm dùng mã nguồn, danh sách truy vấn của từng split và log thực nghiệm mà tác giả công bố tại github.com/edualc/lqo_ml_perspective.

## 4.2. Hệ quản trị CSDL và môi trường

### 4.2.1. Cấu hình so với bài báo

| Thành phần | Bài báo (§8.1.1, Bảng 2) | Nhóm |
|---|---|---|
| Phần cứng | x86, 16 CPU, 64 GB RAM, GPU Tesla T4 | MacBook Pro M1 Pro (ARM64), 8 CPU, 16 GB RAM, không có GPU NVIDIA |
| Hệ quản trị CSDL | PostgreSQL 12.5 trong Docker | PostgreSQL 12.5 trong Docker, build từ mã nguồn cho ARM64 |
| Ép plan | `pg_hint_plan` | `pg_hint_plan` (nhánh PG12) |
| Đo thời gian | `EXPLAIN ANALYZE` | `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON)` |
| `shared_buffers` / `work_mem` | 32 GB / 4 GB | 3 GB / 128 MB |
| `temp_buffers` / `effective_cache_size` | 32 GB / 32 GB | 256 MB / 8 GB |
| `max_worker_processes` | 8 | 6 |
| GEQO, bitmap/tid scan | Bật | Bật |
| `autovacuum` | Tắt; `ANALYZE` một lần sau khi nạp | Giống bài báo |
| Số lần chạy | 3 lần, lấy lần thứ 3 (hot cache) (§7.3) | Giống bài báo |
| Timeout | 3 phút | 3 phút |

**Những điểm cần lưu ý về hệ quản trị CSDL:**
- **Phải dùng đúng PostgreSQL 12.5.** Đây là phiên bản `pg_hint_plan` và `pg_bao` hỗ trợ. Optimizer của các phiên bản khác có thể chọn plan khác.
- **Bộ nhớ phải thu nhỏ** để vừa 16 GB RAM. Bài báo cho thấy riêng `effective_cache_size` đã ảnh hưởng tới thời gian lập kế hoạch (§7.1), nên nhóm **chỉ so sánh xu hướng và thứ hạng**, không so sánh số tuyệt đối.
- **Giữ nguyên các thiết lập quyết định tính công bằng:** GEQO, bitmap/tid scan, autovacuum, cách đo hot cache. Bài báo chứng minh tắt bitmap/tid scan hoặc GEQO làm thay đổi đáng kể thời gian của nhiều câu (§8.4, §8.5).
- **Thống kê cố định:** tắt autovacuum và chỉ chạy `ANALYZE` một lần, để ước lượng cardinality không thay đổi giữa các lần chạy.

### 4.2.2. Triển khai

Nhóm giữ kiến trúc hai container của repo gốc, kể cả tên container và địa chỉ IP, để các script của tác giả chạy được mà không phải sửa:

| Container | Nội dung |
|---|---|
| `pg_bao` | PostgreSQL 12.5 + `pg_hint_plan` + extension `pg_bao` |
| `bao_server` | Bao server (PyTorch 1.13.0) và các script chạy thí nghiệm |

Để chạy trên Apple Silicon, nhóm phải điều chỉnh bốn điểm:

1. **Build PostgreSQL và extension từ mã nguồn:** không có image ARM64 dựng sẵn nào kèm `pg_hint_plan` và `pg_bao`.
2. **Đổi bản PyTorch:** `torch==1.13.0+cpu` chỉ có cho x86, nên thay bằng `torch==1.13.0` (có bản aarch64).
3. **Đổi nguồn tải IMDB:** đường dẫn cũ đã hỏng, nên tải từ event.cwi.nl/da/job/imdb.tgz.
4. **Sửa tên CSDL:** trong `bao.cfg`, tên CSDL được đổi từ `so` (STACK) thành `imdbload` (JOB).

CSDL IMDB được nạp bằng script của Balsa trong repo. Script này có sẵn hai index bổ sung trên `complete_cast` (§8.1.1) và chạy `ANALYZE` một lần. Kết quả nạp: 21 bảng, dung lượng 12 GB.

## 4.3. Các phương pháp trong bài báo và khả năng chạy lại

Bài báo đánh giá 5 LQO cùng PostgreSQL (§8.2). Nhóm xét từng phương pháp xem có chạy lại được trên máy của nhóm hay không:

| Phương pháp | Yêu cầu (§8.2.2) | Kế hoạch của nhóm |
|---|---|---|
| **PostgreSQL** | Không cần train | ✅ Chạy lại 113 câu JOB, mỗi câu 3 lần |
| **Bao** | Chạy trên CPU, khoảng 2 giờ/split | ✅ Chạy lại trên 3 split đại diện cho 3 mức độ khó: LOO-1, RND-1, BQ-1 |
| **HybridQO** | Khoảng 20 giờ/split | ❌ Dùng log của tác giả |
| **Neo, Balsa** | GPU CUDA, 20–85 giờ/split | ❌ Dùng log của tác giả |
| **LEON** | GPU CUDA, 110–130 giờ/split | ❌ Dùng log của tác giả |

Ngoài ra, nhóm chạy lại các **ablation** không cần GPU: tắt bitmap/tid scan (§8.4), tắt GEQO (§8.5), số lần chạy *k* (§8.6), cây bushy so với left-deep (§8.7), và covariate shift trên IMDB-50% (§8.3).

**Cách so sánh với PostgreSQL:**
- Với mỗi câu, tính thời gian end-to-end = suy luận + lập kế hoạch + thực thi (§8.2.1).
- **Thắng** nếu nhanh hơn PostgreSQL trên 10%, **thua** nếu chậm hơn trên 10%, còn lại là **hòa**.
- Kiểm định bằng Wilcoxon signed-rank và sign test, vì dữ liệu bắt cặp theo câu và không có phân phối chuẩn.

## 4.4. Metric đo câu SQL

Nhóm dùng hai nhóm metric: metric **tĩnh**, đo độ phức tạp của câu SQL trước khi chạy, và metric **động**, đo hiệu năng khi chạy.

### 4.4.1. Metric tĩnh (độ phức tạp của câu SQL và plan)

| Metric | Ý nghĩa | Lấy từ |
|---|---|---|
| Số bảng, số điều kiện join | Kích thước bài toán chọn thứ tự join; không gian plan tăng theo O(n!) (§1) | Câu SQL |
| Số filter; số `LIKE`, `IN`, `BETWEEN`, `OR`, `IS NULL`, so sánh khoảng | Độ khó khi ước lượng độ chọn lọc | Câu SQL |
| Số node, độ sâu cây plan | Độ phức tạp của plan | `EXPLAIN` |
| Có cây bushy hay không, số join bushy | Hình dạng cây join (§8.7) | `EXPLAIN` |
| Số Hash / Merge / Nested Loop join | Loại thuật toán join được chọn | `EXPLAIN` |
| Số Seq / Index / Bitmap scan | Cách đọc bảng | `EXPLAIN` |
| **Cost** | Chi phí ước lượng của optimizer | `EXPLAIN` |
| Số dòng ước lượng | Ước lượng cardinality | `EXPLAIN` |

### 4.4.2. Metric động (hiệu năng khi chạy)

| Metric | Công thức / ý nghĩa |
|---|---|
| **Planning time** | Thời gian PostgreSQL lập kế hoạch |
| **Execution time** | Thời gian thực thi câu truy vấn |
| **End-to-end time** | Suy luận + lập kế hoạch + thực thi; đây là **metric chính** theo bài báo (§8.2.1) |
| **Speedup** | `t_plan_cũ / t_plan_mới`. Giá trị 2,0× nghĩa là plan mới nhanh gấp đôi; 0,5× nghĩa là chậm gấp đôi |
| **% thời gian tiết kiệm** | `(t_cũ − t_mới) / t_cũ × 100%` |
| **q-error** | `max(ước lượng / thực tế, thực tế / ước lượng)` của số dòng tại mỗi node. q-error lớn cho thấy optimizer ước lượng sai và dễ chọn sai plan |
| **Số câu timeout** | Số câu chạy quá 3 phút |
| **Tổng thời gian workload** | Tổng end-to-end time của mọi câu, dùng để so sánh tổng thể như bài báo |

## 4.5. Chạy plan và lưu log

### 4.5.1. Các plan được so sánh

Mỗi câu truy vấn JOB được chạy với **6 hint set** theo kiểu của Bao (§2). Mỗi hint set là một lệnh `SET` bật/tắt một loại toán tử, khiến PostgreSQL phải chọn một plan khác:

| Hint set | Lệnh trong PostgreSQL |
|---|---|
| `default` (**plan cũ**) | Không thay đổi; plan PostgreSQL tự chọn |
| `no_nestloop` | `SET enable_nestloop = off` |
| `no_hashjoin` | `SET enable_hashjoin = off` |
| `no_mergejoin` | `SET enable_mergejoin = off` |
| `no_seqscan` | `SET enable_seqscan = off` |
| `no_indexscan` | `SET enable_indexscan = off; SET enable_indexonlyscan = off` |

- Mỗi tổ hợp (câu, hint set) chạy 3 lần, timeout 3 phút. Tổng cộng khoảng 113 × 6 × 3 ≈ 2.000 lần chạy.
- **Plan tối ưu** của một câu là plan của hint set có end-to-end time nhỏ nhất (lấy lần chạy thứ 3).
- Với Bao, plan mới là plan mà mô hình Bao chọn.

### 4.5.2. Định dạng log

Repo gốc chỉ lưu thời gian chạy. Nhóm bổ sung script ghi thêm **toàn bộ plan thực thi**. Mỗi lần chạy được ghi thành **một dòng JSON** (định dạng JSONL) trong file log. Ví dụ với câu 1a và 1b:

```json
{"query_id": "1a", "benchmark": "JOB", "db": "imdbload", "pg_version": "12.5", "hint_set": "default",     "tag": "", "run": 2, "planning_ms": <số>, "execution_ms": <số>, "timeout": false, "plan": {...}}
{"query_id": "1a", "benchmark": "JOB", "db": "imdbload", "pg_version": "12.5", "hint_set": "no_nestloop", "tag": "", "run": 2, "planning_ms": <số>, "execution_ms": <số>, "timeout": false, "plan": {...}}
{"query_id": "1b", "benchmark": "JOB", "db": "imdbload", "pg_version": "12.5", "hint_set": "default",     "tag": "", "run": 2, "planning_ms": <số>, "execution_ms": <số>, "timeout": false, "plan": {...}}
```

| Trường | Ý nghĩa |
|---|---|
| `query_id` | Tên câu truy vấn (1a, 1b, ...). Phần số (1) là truy vấn gốc, dùng để chia dữ liệu theo Base Query |
| `benchmark`, `db`, `pg_version` | Benchmark, CSDL, phiên bản PostgreSQL; giúp tái lập |
| `hint_set` | Plan nào được chạy |
| `tag` | Tên thí nghiệm (ví dụ `no_geqo`, `imdb50`) để phân biệt các ablation |
| `run` | Lần chạy thứ mấy (0, 1, 2). Phân tích dùng `run = 2`, tức lần chạy thứ 3 (hot cache) |
| `planning_ms`, `execution_ms` | Thời gian lập kế hoạch và thực thi (ms) |
| `timeout` | Câu có bị quá 3 phút hay không. Câu timeout vẫn được giữ lại, tính thời gian bằng timeout |
| `plan` | **Toàn bộ cây plan** dạng JSON lấy từ `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON)` |

Script có thể **chạy tiếp sau khi bị ngắt**: những tổ hợp (câu, hint set, tag) đã có trong log sẽ được bỏ qua.

### 4.5.3. Trình bày plan thực thi

Từ trường `plan`, nhóm trích ra các thông tin chính của mỗi node: **loại toán tử** (join, scan, aggregate), **bảng**, **thứ tự join**, **cost**, **số dòng ước lượng**, **số dòng thực tế** và **thời gian thực tế**. Plan được trình bày dạng cây, plan cũ đặt cạnh plan mới.

**Minh họa cách trình bày với câu 1a** (join 5 bảng: `company_type ct`, `info_type it`, `movie_companies mc`, `movie_info_idx mi_idx`, `title t`). Cây dưới đây chỉ minh họa cách trình bày, chưa phải kết quả đo:

```
Plan cũ (default)                              Plan mới (no_nestloop)
Aggregate                                      Aggregate
└─ Nested Loop                                 └─ Hash Join  (t.id = mc.movie_id)
   ├─ Nested Loop                                 ├─ Seq Scan on title t
   │  ├─ Nested Loop                              └─ Hash
   │  │  ├─ Seq Scan on info_type it                 └─ Hash Join  (mi_idx.movie_id = mc.movie_id)
   │  │  └─ Index Scan on movie_info_idx mi_idx         ├─ Hash Join (it.id = mi_idx.info_type_id)
   │  └─ Index Scan on movie_companies mc               │  ├─ Seq Scan on movie_info_idx mi_idx
   │     (+ join với ct)                                │  └─ Hash → Seq Scan on info_type it
   └─ Index Scan on title t                             └─ Hash Join (ct.id = mc.company_type_id)
                                                           ├─ Seq Scan on movie_companies mc
                                                           └─ Hash → Seq Scan on company_type ct
Thứ tự join: ((it ⋈ mi_idx) ⋈ mc ⋈ ct) ⋈ t     Thứ tự join: ((it ⋈ mi_idx) ⋈ (mc ⋈ ct)) ⋈ t
```

Mỗi cặp plan được so sánh theo bốn điểm:
1. **Thứ tự join** có thay đổi không.
2. **Loại join và loại scan** đã thay đổi ở những node nào.
3. **Hình dạng cây:** left-deep hay bushy.
4. **Khoảng cách giữa hai cây**, đo bằng tree edit distance.

### 4.5.4. Bảng plan tối ưu cho toàn bộ dataset

Kết quả được tổng hợp thành một bảng, mỗi câu một dòng:

| Cột | Ý nghĩa |
|---|---|
| `query_id` | Câu truy vấn |
| `plan_cu` | `default` |
| `plan_toi_uu` | Hint set nhanh nhất |
| `t_cu_ms`, `t_moi_ms` | End-to-end time của plan cũ và plan tối ưu |
| `speedup` | `t_cu / t_moi` |
| `cung_cay_plan` | Plan tối ưu có trùng cây plan với plan cũ không |

Từ bảng này, nhóm báo cáo:
- **Số câu** có plan tốt hơn plan mặc định, và **số câu** mà plan mặc định đã là tốt nhất.
- **Phân phối speedup:** trung vị, lớn nhất, và số câu có speedup trên 1,5× hoặc trên 2×.
- **Tổng thời gian workload** khi luôn dùng plan cũ so với khi luôn dùng plan tối ưu. Đây là giới hạn trên của mức cải thiện có thể đạt được.

## 4.6. Phân loại plan bằng data mining

### 4.6.1. Phát biểu bài toán

- **Đầu vào:** metric tĩnh của câu SQL và của **plan mặc định** (mục 4.4.1). Đây là những thông tin có sẵn trước khi thử các plan khác, nên không rò rỉ nhãn vào đặc trưng.
- **Nhãn:** hint set tốt nhất của câu đó (mục 4.5.4).
- **Bài toán:** với mỗi câu truy vấn, dự đoán nên chạy plan nào. Ví dụ với 1.000 câu truy vấn, mô hình gán cho mỗi câu một trong 6 plan.

**Quy tắc gán nhãn:**
- Một hint set chỉ được coi là tốt hơn `default` nếu **nhanh hơn ít nhất 5%**. Ngưỡng này giúp tránh gán nhãn theo nhiễu đo.
- Nếu một hint set cho ra **cùng cây plan** với `default`, nó được tính bằng thời gian của `default`.

### 4.6.2. Chia dữ liệu theo đúng 3 kiểu của bài báo (§7.2)

| Kiểu chia | Cách làm | Mục đích |
|---|---|---|
| **Leave One Out** | Mỗi fold lấy 1 biến thể của mỗi truy vấn gốc làm tập test | Dễ nhất |
| **Random** | KFold 5 lần | Trung bình |
| **Base Query** | GroupKFold theo truy vấn gốc: mọi biến thể của một truy vấn gốc nằm cùng một phía | Khó nhất; không rò rỉ dữ liệu giữa các biến thể |

### 4.6.3. Mô hình và mốc so sánh

- **Mô hình:** Decision Tree, Random Forest, Gradient Boosting, kNN, Naive Bayes, SVM, Logistic Regression.
- **Mốc dưới, "Luôn dùng PostgreSQL":** không bao giờ đổi plan.
- **Mốc trên, "Oracle":** luôn chọn đúng plan tốt nhất.

### 4.6.4. Đếm số câu đúng và các chỉ số đánh giá

Với mỗi kiểu chia và mỗi mô hình, nhóm báo cáo:

| Chỉ số | Ý nghĩa |
|---|---|
| **Số câu dự đoán đúng / tổng số câu** | Ví dụ 80/113 câu chọn đúng plan tốt nhất |
| **Ma trận nhầm lẫn** | Plan thật so với plan dự đoán, cho biết mô hình hay nhầm giữa những plan nào |
| Accuracy, macro-F1 | Chỉ số phân loại chuẩn; macro-F1 xử lý được việc các lớp lệch nhau (phần lớn câu có nhãn `default`) |
| **Tổng thời gian workload khi dùng plan mô hình chọn** | So với "Luôn dùng PostgreSQL" và với Oracle |
| **Regret** | Thời gian mất thêm so với Oracle |
| **Số câu bị chậm đi trên 10%** | Số câu mô hình chọn sai và làm chậm hơn plan cũ |
| Kiểm định McNemar | Mô hình có khác biệt có ý nghĩa thống kê so với "Luôn dùng PostgreSQL" hay không |

Một mô hình đúng nhiều câu nhưng chọn sai ở một câu chạy rất lâu vẫn có thể làm chậm cả workload. Vì vậy nhóm **ưu tiên chỉ số theo thời gian hơn accuracy**, đúng với nhận xét ở §5.1 của bài báo rằng accuracy không phải chỉ số phù hợp cho tối ưu truy vấn.

### 4.6.5. Giải thích vì sao plan mới tốt hơn

Thay vì liệt kê từng câu, nhóm dùng thuật toán để tìm quy luật chung:

| Thuật toán | Câu hỏi trả lời |
|---|---|
| **K-means + PCA** | Các câu truy vấn tự chia thành những nhóm nào? Nhóm nào thường được lợi khi đổi plan? |
| **Luật kết hợp (Apriori)** | Luật dạng `{đặc điểm câu SQL / plan} → plan tốt nhất`, kèm support, confidence, lift |
| **Permutation importance** (Random Forest) | Metric nào quyết định việc nên đổi plan? Ví dụ q-error lớn có phải dấu hiệu PostgreSQL chọn sai không? |
| **Cây quyết định độ sâu 3** | Quy tắc ngắn gọn, dễ đọc cho người quản trị CSDL |
| **Tree edit distance + tương quan Spearman** | Plan mới khác plan cũ càng nhiều thì có càng nhanh không? |

## 4.7. Thêm benchmark

JOB chỉ có 113 câu, nên mỗi tập test chỉ có khoảng 19–33 câu. Con số này quá ít cho bài toán phân loại.

- **Nhóm đề xuất CEB-IMDb** (github.com/learned-systems/CEB). Benchmark này chạy trên **cùng CSDL IMDB**, nên không cần nạp dữ liệu mới, và có hàng nghìn câu sinh từ template. Nhóm sẽ lấy mẫu khoảng **1.000 câu**, lặp lại toàn bộ mục 4.5–4.6, rồi so sánh với kết quả trên JOB.
- **Phương án dự phòng:** DSB (dữ liệu lệch) ở scale factor nhỏ.
- **STACK** không được dùng vì dung lượng dữ liệu quá lớn so với máy của nhóm.

## 4.8. Kết quả sơ bộ: phân tích lại log của tác giả

Bước đầu, nhóm phân tích file `experiment_logs/20240103__combined.csv` của tác giả. Dữ liệu gồm 9 split JOB, chỉ tập test, so sánh từng câu của mỗi LQO với PostgreSQL (233 cặp câu–split cho mỗi phương pháp):

| Phương pháp | Thắng | Hòa | Thua | Tổng thời gian PostgreSQL (s) | Tổng thời gian LQO (s) | Speedup |
|---|---|---|---|---|---|---|
| HybridQO | 34 | 82 | 117 | 264,2 | 263,9 | 1,00× |
| Bao | 9 | 34 | 190 | 264,2 | 320,1 | 0,83× |
| Balsa | 16 | 4 | 213 | 264,2 | 958,9 | 0,28× |
| Neo | 21 | 12 | 200 | 264,2 | 1.665,4 | 0,16× |
| LEON | 0 | 0 | 233 | 264,2 | 265.553,4 | 0,001× |

*Speedup = tổng thời gian PostgreSQL / tổng thời gian LQO; lớn hơn 1 nghĩa là LQO nhanh hơn.*

**Nhận xét:**
- **Thứ hạng khớp với bài báo:** PostgreSQL ≈ HybridQO > Bao > Balsa, Neo > LEON (§8.2.1).
- **HybridQO ngang PostgreSQL về tổng thời gian nhưng thua ở khoảng một nửa số câu** (117/233). Phương pháp này bù lại nhờ một số ít câu được cải thiện lớn. Bài báo không nêu điểm này vì chỉ báo cáo tổng thời gian.
- **Kết quả phụ thuộc mạnh vào split.** Speedup của HybridQO dao động từ 0,79× đến 1,11×; Bao chỉ nhanh hơn PostgreSQL ở 1/9 split (RND-1, 1,25×). Điều này minh họa nhận định "đánh giá data-centric" của bài báo (§1).
- **Thời gian suy luận quyết định thứ hạng.** Tổng thời gian của LEON (khoảng 74 giờ) gần như hoàn toàn là thời gian suy luận (§8.2.1).

Kết quả này là động lực cho phần phân loại plan ở mục 4.6. LQO nào cũng thắng rõ ở một số câu nhưng thua ở phần lớn các câu còn lại. Nếu dự đoán trước được câu nào nên đổi plan, ta có thể giữ phần lợi và tránh phần thiệt.

## 4.9. Kết quả kỳ vọng và tiêu chí đánh giá

| Câu hỏi | Tiêu chí kết luận |
|---|---|
| Kết luận của bài báo có tái lập được trên ARM64 không? | Thứ hạng giữa PostgreSQL và Bao trên 3 split giống log của tác giả; kiểu chia Base Query vẫn khó nhất |
| Plan tối ưu nhanh hơn plan mặc định bao nhiêu? | Số câu có plan tốt hơn, phân phối speedup, tổng thời gian workload so với Oracle (mục 4.5.4) |
| Mô hình phân loại có hữu ích không? | Số câu đúng cao hơn mốc "Luôn dùng PostgreSQL"; tổng thời gian workload thấp hơn PostgreSQL; ít câu bị chậm đi; vẫn giữ được ưu thế ở split Base Query |
| Có giải thích được khi nào plan mới tốt hơn không? | Tìm được luật hoặc metric ổn định (q-error, số join, loại toán tử), nhất quán giữa JOB và CEB-IMDb |

## 4.10. Hạn chế dự kiến

- **Không chạy lại HybridQO, Neo, Balsa, LEON** vì thiếu GPU và thời gian train quá dài (20–130 giờ/split); phần đánh giá các phương pháp này dựa trên log của tác giả.
- **Cấu hình bộ nhớ nhỏ hơn bài báo** có thể làm PostgreSQL chọn plan khác (§7.1).
- **Oracle chỉ là "tốt nhất trong 6 hint set",** không phải plan tối ưu toàn cục trong toàn bộ không gian plan.

## 4.11. Tiểu kết

Nhóm đã dựng xong môi trường tái lập trên ARM64, giữ nguyên các thiết lập của hệ quản trị CSDL quyết định tính công bằng của bài báo. Phân tích lại log của tác giả xác nhận kết luận chính: **không có LQO nào vượt PostgreSQL một cách ổn định.** Dựa trên đó, nhóm đề xuất:
- **Chạy các plan khác nhau** cho từng câu và **lưu log kèm toàn bộ plan thực thi.**
- **Đo plan tối ưu nhanh hơn bao nhiêu** bằng các metric tĩnh và động.
- **Dùng phân loại và data mining** để dự đoán plan cho từng câu, **đếm số câu đúng**, và giải thích quy luật bằng thuật toán.
- **Mở rộng sang benchmark CEB-IMDb** với khoảng 1.000 câu.
