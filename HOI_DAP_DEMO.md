# Hỏi – đáp chuẩn bị demo

Tổng hợp các câu hỏi khi chuẩn bị demo. Mỗi mục có phần giải thích và một **câu gọn để nói với cô**.

**Mục lục**
1. [Môi trường và hạ tầng](#1-môi-trường-và-hạ-tầng)
2. [Cách so sánh PostgreSQL với Bao](#2-cách-so-sánh-postgresql-với-bao)
3. [Dữ liệu: 113 câu, 33 họ, 233 lần kiểm tra](#3-dữ-liệu-113-câu-33-họ-233-lần-kiểm-tra)
4. [Thí nghiệm 2: plan, đặc trưng, mô hình](#4-thí-nghiệm-2-plan-đặc-trưng-mô-hình)
5. [Khai phá dữ liệu và ngưỡng tin](#5-khai-phá-dữ-liệu-và-ngưỡng-tin)
6. [Ablation: GEQO, bitmap scan, TID scan](#6-ablation-geqo-bitmap-scan-tid-scan)
7. [Hạn chế](#7-hạn-chế)

---

## 1. Môi trường và hạ tầng

### PostgreSQL 12.5 ở đâu? Có cần tải PostgreSQL không?
- PostgreSQL 12.5 chạy **trong container Docker `pg_bao`**, cổng 5432. **Không cần cài PostgreSQL trên máy**, chỉ cần Docker Desktop đang mở.
- Kiểm tra: `docker exec pg_bao psql -U postgres -d imdbload -c "select version();"`
  → `PostgreSQL 12.5 on aarch64-unknown-linux-gnu ...`
- File dựng: [infra/Dockerfile.pg](infra/Dockerfile.pg). Image tải mã nguồn 12.5 rồi biên dịch cho chip Apple, cài thêm pg_hint_plan và pg_bao. Phải tự biên dịch vì không có image sẵn nào gồm PostgreSQL 12.5, pg_hint_plan và pg_bao cho ARM64.
- Trên Kaggle cũng biên dịch đúng PostgreSQL 12.5 ([kaggle/build_bao_notebook.py:48](kaggle/build_bao_notebook.py#L48)).
- Script demo dùng `docker exec pg_bao psql ...`. Dashboard kết nối qua `localhost:5432`.

### Hai container `pg_bao` và `bao_server` là gì?
Có thể hình dung `pg_bao` là **nhà bếp** (nơi nấu thật) và `bao_server` là **người tư vấn món** (chỉ khuyên nên nấu cách nào).

| Container | IP / cổng | Chứa gì | Làm gì |
|---|---|---|---|
| `pg_bao` | 10.5.0.5 / 5432 | PostgreSQL 12.5, dữ liệu IMDB, extension pg_bao và pg_hint_plan | Lập plan, **chạy thật** câu truy vấn |
| `bao_server` | 10.5.0.6 / 9381 | Python, PyTorch, mạng nơ-ron của Bao, script thí nghiệm | **Dự đoán** plan nào nhanh nhất, **train** mô hình |

Luồng xử lý khi bật Bao:
```
pg_bao: nhận SQL → lập 5 plan ──────► bao_server: dự đoán thời gian 5 plan
pg_bao: chạy plan được chọn ◄──────── bao_server: "chọn arm số 1"
pg_bao: gửi thời gian thật ─────────► bao_server: lưu lại để train
```
- Vì sao tách làm 2 container:
  - Giống thiết kế và IP trong repo của tác giả, nên script gốc chạy được mà không phải sửa.
  - PostgreSQL (C) và Bao (Python/PyTorch) có thư viện riêng, tách ra để không xung đột.
  - Có thể khởi động lại Bao mà không phải tắt PostgreSQL, nên không mất cache.
- Cả hai container mount chung `scripts/` (thành `/app/scripts`) và `logs/` (thành `/app/logs`).
- Trong [infra/docker-compose.yml](infra/docker-compose.yml), tên service là `postgres` và `bao`, tên container là `pg_bao` và `bao_server`. Khi gõ lệnh thì dùng tên container.

> "Hạ tầng gồm 2 container Docker cùng một mạng. pg_bao là PostgreSQL 12.5 chứa dữ liệu IMDB và extension Bao, nơi chạy thật câu truy vấn. bao_server chứa mạng nơ-ron của Bao. Khi bật Bao, PostgreSQL lập 5 plan, gửi sang bao_server dự đoán plan nào nhanh nhất, chạy plan đó rồi gửi thời gian thật về để Bao học. Nhóm tách đúng như tác giả, cùng IP, để chạy được nguyên script của tác giả."

### Bao là gì?
- Bao là một bộ tối ưu học máy (LQO). Bao **không tự viết plan mới**. Nó **chọn 1 trong 5 cấu hình** (gọi là arm, hay bộ gợi ý) của bộ tối ưu sẵn có, ví dụ giữ nguyên, tắt nested loop, tắt hash join.
- Việc lập 5 plan và hỏi mô hình mất khoảng **0,1–0,2 giây mỗi câu**. Đây là lý do Bao hay thua ở câu ngắn.
- Khi bật học (`enable_bao_rewards`), Bao ghi lại thời gian thật để train lại.

> "pg_bao là PostgreSQL 12.5 gắn extension Bao. Khi bật Bao, PostgreSQL lập 5 plan theo 5 bộ gợi ý, gửi sang bao_server để mạng nơ-ron dự đoán thời gian, rồi chạy plan nhanh nhất."

### Chạy baseline PostgreSQL thì có phải gỡ extension Bao không?
- **Không gỡ, chỉ tắt trong phiên.** Extension luôn được nạp (`shared_preload_libraries = pg_bao`) và mặc định `enable_bao = off`.
- Baseline (`--use_postgres`): `SET enable_bao TO off`, khi đó PostgreSQL chạy như bản gốc và không gọi bao_server.
- Bao (`--use_bao`): `SET enable_bao TO on` và `SET enable_bao_selection TO on`. Nguồn: [run_queries.py:32-34](lqo_ml_perspective/bao/run_queries.py#L32-L34).
- Không gỡ vì gỡ thì phải khởi động lại PostgreSQL, cache bị xoá, và hai bên không còn cùng điều kiện.

> "Nhóm không gỡ Bao. Baseline thì SET enable_bao TO off, khi đó PostgreSQL chạy như bình thường. Bao thì SET enable_bao TO on. Hai bên dùng chung CSDL và cache nóng, chỉ khác một tham số, nên so sánh công bằng."

### pg_hint_plan là gì?
- Là extension cho phép **ép PostgreSQL theo plan mong muốn** bằng cách ghi gợi ý trong chú thích ở đầu câu SQL:

| Hint | Ý nghĩa |
|---|---|
| `/*+ HashJoin(t mc) */` | Nối `t` và `mc` bằng hash join |
| `/*+ IndexScan(t) */`, `SeqScan(t)` | Đọc bảng `t` bằng index hoặc quét toàn bảng |
| `/*+ Leading(t mc ci) */` | Ép thứ tự nối: `t` với `mc` trước, rồi mới tới `ci` |

- Ví dụ thật: cùng một câu nối `title` và `movie_companies`, PostgreSQL tự chọn **Parallel Hash Join**, còn thêm `/*+ MergeJoin(t mc) */` thì chuyển thành **Merge Join**.
- Ai dùng pg_hint_plan:
  - **HybridQO** dùng: gắn `/*+ Leading(...) */` theo thứ tự nối mà mô hình đề xuất ([Hinter.py:63](lqo_ml_perspective/hybrid_qo/Hinter.py#L63)). Neo và Balsa cũng dùng.
  - **Bao** không dùng (Bao có extension riêng). **Mô hình của nhóm** cũng không dùng (chỉ `SET enable_x = off`).
- Trên Mac, pg_hint_plan được cài trong `pg_bao` nhưng **không nạp mặc định** (phải `LOAD 'pg_hint_plan'`). Mục đích là để môi trường giống bài báo; nó không ảnh hưởng tới phép đo. Trên Kaggle, HybridQO dùng bản `REL12_1_3_7` giống tác giả.

> "pg_hint_plan cho phép viết gợi ý trong câu SQL để ép PostgreSQL theo plan cụ thể, như thứ tự nối bảng. HybridQO cần nó để áp thứ tự nối mà mô hình đề xuất. Bao và mô hình của nhóm không dùng."

### shared_buffers, work_mem, effective_cache_size là gì?

| Tham số | Là gì | Chiếm RAM thật? | Tác giả | Kaggle | Mac |
|---|---|---|---|---|---|
| `shared_buffers` | Vùng RAM PostgreSQL giữ các trang dữ liệu đã đọc (cache) | Có | 32 GB | 8 GB | 4 GB |
| `work_mem` | RAM cho **mỗi** phép sort hoặc hash, ví dụ dựng bảng băm cho hash join. Vượt quá thì phải ghi tạm ra đĩa | Có, khi cần | 4 GB | 512 MB | 256 MB |
| `effective_cache_size` | Con số gợi ý cho optimizer về lượng cache, ảnh hưởng việc chọn index scan | **Không** | 32 GB | 32 GB | 32 GB |

- Ngoài shared_buffers còn có **cache file của hệ điều hành** dùng phần RAM trống. Thứ tự tìm dữ liệu: shared_buffers, rồi cache của hệ điều hành, rồi mới đến đĩa.
- work_mem nhỏ thì hash join dễ tràn ra đĩa, và optimizer có thể chọn plan khác với máy tác giả.

> "shared_buffers là RAM PostgreSQL dùng giữ dữ liệu đã đọc, work_mem là RAM cho mỗi phép sort hoặc hash join. Máy nhóm ít hơn tác giả (8 GB so với 32 GB, 512 MB so với 4 GB) nên thời gian tuyệt đối chậm hơn và plan có thể hơi khác. Vì vậy nhóm so xu hướng. effective_cache_size chỉ là gợi ý, nhóm để 32 GB giống tác giả."

---

## 2. Cách so sánh PostgreSQL với Bao

### Nhóm so sánh thế nào?
1. **Cùng điều kiện:** khởi động lại PostgreSQL, làm nóng cache, chạy PostgreSQL, rồi chạy Bao ngay sau ([run_fair_comparison.sh](scripts/exp1/run_fair_comparison.sh)). Trên Kaggle, hai bên chạy cùng notebook, cùng máy.
2. **Chỉ so trên tập test** của từng split (Bao học trên tập train), 9 split, tổng 233 lần kiểm tra.
3. **Mỗi câu chạy 3 lần, lấy lần thứ 3.**
4. **Thời gian end-to-end** = inference + planning + execution. Với Bao, phần planning đã gồm thời gian gọi mô hình.
5. **Cách tính** ([c1_win_loss.py](scripts/exp1/c1_win_loss.py)):
   - Từng câu: speedup = PostgreSQL / Bao. **Thắng** khi > 1,1; **thua** khi < 0,9; còn lại là **hòa**. Kèm kiểm định Wilcoxon và sign test.
   - Tổng: tổng thời gian PostgreSQL / tổng thời gian Bao. Kaggle: 398 s / 434 s = **0,92×** (bài báo 0,83×). Bao thắng 8, hòa 46, thua 179.

> "PostgreSQL và Bao chạy cùng câu test, cùng máy, cache nóng. Mỗi câu chạy 3 lần lấy lần thứ 3, đo end-to-end gồm cả thời gian Bao gọi mô hình. Speedup bằng thời gian PostgreSQL chia thời gian Bao, tính theo từng câu (ngưỡng 10%) và theo tổng."

### Có giống cách tác giả làm không?
**Giống** (nhóm dùng nguyên script `run_queries.py` và `run_test_queries.py` của tác giả):

| Bước | Cách làm |
|---|---|
| Phiên bản | PostgreSQL 12.5, pg_bao, 5 arm |
| Chia dữ liệu | Đúng 9 split của tác giả |
| Train | Lấy ngẫu nhiên 500 lượt câu train (`seed 42`). 25 câu đầu chạy bằng PostgreSQL, sau đó cứ 25 câu thì train lại một lần |
| Test | 3 lần mỗi câu, lấy lần thứ 3; timeout 3 phút (quá giờ thì tính 6 phút) |
| GEQO | Bật cho cả Bao và PostgreSQL (chú thích ¹ Bảng 2) |

Trên Kaggle chỉ sửa địa chỉ kết nối `pg_bao` thành `localhost` ([build_bao_notebook.py:178-191](kaggle/build_bao_notebook.py#L178-L191)). Trên Mac, nhóm xoá model cũ trước mỗi split ([run_bao_split.sh](scripts/exp1/run_bao_split.sh)).

**Khác tác giả:**
- Bộ nhớ thấp hơn (xem bảng ở mục 1).
- Bao chỉ train 1 lần mỗi split.
- Kaggle giới hạn train 8,5 giờ (một phiên tối đa 12 giờ).
- Tổng thời gian PostgreSQL cho 113 câu: khoảng 225 s trên Kaggle, khoảng 151 s ở bài báo.

> "Nhóm dùng nguyên script train/test Bao của tác giả, cùng PostgreSQL 12.5, cùng 9 split, cùng cách chạy 3 lần lấy lần thứ 3. Khác biệt là bộ nhớ (8 GB so với 32 GB) nên nhóm so xu hướng. Kết quả cùng xu hướng: Bao 0,92× so với 0,83× của bài báo."

### Vì sao mỗi câu chạy 3 lần?
- Lần 1 phải đọc dữ liệu từ **đĩa** nên chậm. Lần 2 phần lớn đã nằm trong RAM. **Lần 3 ổn định nhất** và phản ánh đúng chất lượng plan.
- Số liệu thật từ log baseline trên Mac ngày 08/11:

| | Lần 1 | Lần 2 | Lần 3 |
|---|---|---|---|
| Tổng 113 câu | 503 s | 276 s | **248 s** |
| 26a | 24,3 s | 9,8 s | **8,1 s** |
| 16b | 57,2 s | 28,1 s | **23,3 s** |

  Giữa lần 2 và lần 3 vẫn có 57/113 câu lệch hơn 10%.
- Bao và PostgreSQL chọn plan khác nhau nên đọc các trang dữ liệu khác nhau. Lấy lần 3 thì cả hai bên đều chạy với cache nóng.
- Tác giả cũng đặt `NUM_EXECUTIONS = 3` ([run_test_queries.py:11](lqo_ml_perspective/bao/run_test_queries.py#L11)).

> "Lần đầu PostgreSQL đọc từ đĩa nên rất chậm: tổng lần 1 là 503 giây, lần 3 là 248 giây. Hai lần đầu để làm nóng cache, lần 3 ổn định nhất. Tác giả cũng làm vậy."

---

## 3. Dữ liệu: 113 câu, 33 họ, 233 lần kiểm tra

### Vì sao 113 câu mà Leave-one-out chỉ có 33 câu test?
- 113 câu JOB thuộc **33 họ câu** (họ 1 đến 33). Phần số trong tên câu là họ, phần chữ là biến thể: `26a, 26b, 26c` cùng họ 26, chỉ khác hằng số trong điều kiện lọc. Mỗi họ có 2–6 biến thể.
- **Leave-one-out** giữ lại **1 câu của mỗi họ** để test, nên tập test có 33 câu và tập train có 80 câu. Ví dụ split 1: `1c 2a 3b 4a 5a 6b 7c 8c 9c 10b … 33c`.

| Cách chia | Câu test là | Mô hình đã thấy họ đó chưa? |
|---|---|---|
| Leave-one-out | 1 câu của mỗi họ | Đã thấy các biến thể khác cùng họ, nên **dễ nhất** |
| Random | Chọn ngẫu nhiên khoảng 20% | Thường đã thấy |
| Base query | Cả họ bị giữ lại | **Chưa từng thấy**, nên **khó nhất** (dùng để kiểm tra H2) |

> "113 câu JOB thuộc 33 họ, mỗi họ có vài biến thể chỉ khác hằng số. Leave-one-out giữ lại 1 biến thể của mỗi họ để test, nên có 33 câu test."

### Vì sao là 233 lần kiểm tra?
233 là **tổng số câu test của 9 split cộng lại**. Một câu có thể là câu test ở nhiều split.

| Cách chia | Split 1 | Split 2 | Split 3 | Cộng |
|---|---|---|---|---|
| Leave-one-out | 33 | 33 | 33 | 99 |
| Random | 22 | 22 | 22 | 66 |
| Base query | 19 | 23 | 26 | 68 |
| **Tổng** | | | | **233** |

> "Cộng số câu test của 9 cách chia thì được 233. Một câu có thể là câu test ở nhiều cách chia, nên con số này lớn hơn 113."

---

## 4. Thí nghiệm 2: plan, đặc trưng, mô hình

### Plan và EXPLAIN là gì?
- **Plan** là cách PostgreSQL định chạy một câu SQL: đọc bảng nào, bằng index hay quét toàn bảng, nối theo thứ tự nào, bằng hash join hay nested loop. SQL chỉ nói "lấy gì", còn optimizer chọn "lấy bằng cách nào".
- **EXPLAIN** cho xem plan **mà không chạy câu**, mất vài mili giây. **EXPLAIN ANALYZE** thì chạy thật và cho thêm số dòng thực tế và thời gian thật.
- Ví dụ (đọc cây từ dưới lên):
```
Finalize Aggregate                          ← 4. tính MIN
  -> Gather (2 workers)                     ← 3. gom kết quả song song
       -> Parallel Hash Join                ← 2. nối 2 bảng bằng hash join
            -> Parallel Seq Scan on movie_companies   ← 1a. quét toàn bảng
            -> Parallel Seq Scan on title             ← 1b. quét toàn bảng, lọc year > 2010
```
- Ở ví dụ này, PostgreSQL ước lượng 168 499 dòng nhưng thực tế khoảng 295 000. **Ước lượng sai** là nguyên nhân chính khiến PostgreSQL chọn sai plan.

> "Plan là cách PostgreSQL định chạy câu SQL. EXPLAIN cho xem plan mà không chạy câu. Mô hình của nhóm đọc plan EXPLAIN mặc định, rút ra đặc trưng, rồi đoán PostgreSQL có đang chọn sai không."

### 34 đặc trưng là gì?
Gồm 11 đặc trưng SQL và 23 đặc trưng plan. **Tất cả đều có trước khi chạy câu** ([extract_features.py](scripts/common/extract_features.py)). Cột cuối là giá trị thật của **câu 26a** (nối 12 bảng tìm phim siêu anh hùng).

**A. 11 đặc trưng SQL**: nhóm tự đếm bằng Python (regex) trên văn bản SQL, **không qua PostgreSQL**.

| # | Đặc trưng | Đếm gì | 26a |
|---|---|---|---|
| 1 | `sql_n_tables` | Số bảng | 12 |
| 2 | `sql_n_join_preds` | Điều kiện nối (`t.id = mk.movie_id`) | 17 |
| 3 | `sql_n_filter_preds` | Điều kiện lọc (`t.production_year > 2000`) | 9 |
| 4 | `sql_n_like` | `LIKE` | 3 |
| 5 | `sql_n_not_like` | `NOT LIKE` | 0 |
| 6 | `sql_n_in` | `IN (...)` | 1 |
| 7 | `sql_n_between` | `BETWEEN` | 0 |
| 8 | `sql_n_or` | `OR` | 1 |
| 9 | `sql_n_is_null` | `IS (NOT) NULL` | 1 |
| 10 | `sql_n_range` | `<`, `>`, `<=`, `>=` | 2 |
| 11 | `sql_len` | Độ dài câu (ký tự) | 1209 |

**B. 23 đặc trưng plan**: lấy từ EXPLAIN.

| # | Nhóm | Đặc trưng | 26a |
|---|---|---|---|
| 12–14 | Cách nối | nested loop / hash join / merge join | 9 / 2 / 0 |
| 15–19 | Cách đọc bảng | seq scan / index scan / index only scan / bitmap heap scan / bitmap index scan | 5 / 7 / 0 / 0 / 0 |
| 20–26 | Toán tử khác | hash / sort / materialize / aggregate / gather / gather merge / memoize | 2 / 0 / 0 / 1 / 0 / 0 / 0 |
| 27 | Hình dạng | `plan_nodes` (số nút) | 26 |
| 28 | | `plan_depth` (độ sâu) | 14 |
| 29 | | `plan_n_joins` (số phép nối) | 11 |
| 30–31 | | `plan_bushy_joins`, `plan_is_bushy` (plan dạng "bụi"?) | 0, 0 |
| 32 | Chi phí | `plan_total_cost` | 11 952 |
| 33 | | `plan_startup_cost` | 11 952 |
| 34 | | `plan_est_rows` (số dòng ước lượng) | 1 |

- **Đã bỏ** 2 đặc trưng q-error ([exp2_analyze.py:48](scripts/exp2/exp2_analyze.py#L48)) vì chúng cần số dòng thực tế, tức là phải chạy câu. Dùng chúng thì mô hình "nhìn trước đáp án".
- 3 đặc trưng luôn bằng nhau ở mọi câu (`gather merge`, `memoize`, `est_rows`), nên thực tế mô hình học từ 31 đặc trưng.
- Quan trọng nhất (Random Forest): `plan_startup_cost` 9,5%, `plan_total_cost` 9,2%, `sql_len` 7,8%, `plan_nodes` 6,8%, `sql_n_filter_preds` 6,2%.
- Ví dụ 26a: có 3 LIKE (khó ước lượng) mà PostgreSQL vẫn dùng 9 nested loop và 7 index scan, tức là PostgreSQL ước lượng rất ít dòng. Tắt index scan thì nhanh gấp 6 lần.

**11 đặc trưng SQL nằm ở bước nào của PostgreSQL?** Không ở bước nào. PostgreSQL xử lý một câu qua 4 bước: Parser, Rewriter, **Planner**, Executor. Đặc trưng SQL được đếm **trước cả bước Parser**, bằng code của nhóm. Đặc trưng plan là **kết quả của bước Planner**, vì EXPLAIN dừng ở bước này và không sang Executor.

> "11 đặc trưng SQL nhóm tự đếm bằng Python trên văn bản câu, như số bảng, số LIKE, số điều kiện lọc. 23 đặc trưng plan lấy từ EXPLAIN, tức là kết quả bước Planner, như số hash join, nested loop, index scan, độ sâu cây và cost. Tất cả có trước khi chạy câu, chỉ mất vài mili giây."

### Dư địa (Oracle 1,53×) là gì?
- **Dư địa** là mức tối đa có thể cải thiện.
- **Oracle** là một "mô hình hoàn hảo" tưởng tượng, luôn chọn đúng phương án nhanh nhất trong 6 phương án. Oracle đạt **1,53×**.

| | Speedup |
|---|---|
| Oracle | **1,53×** (mức trần) |
| Mô hình của nhóm | 0,80–0,82× |
| Random Forest với ngưỡng tin 60% | 1,06× |

- Nếu Oracle chỉ khoảng 1,0× thì ý tưởng sai từ đầu. Oracle đạt 1,53× nghĩa là cơ hội có thật, và vấn đề nằm ở chỗ **mô hình chọn sai**.
- Khi nói với cô có thể dùng "mức tối đa có thể đạt" hoặc "tiềm năng cải thiện".

### "Câu 26a chọn sai rất đắt" nghĩa là gì?

| Phương án | Thời gian |
|---|---|
| PostgreSQL mặc định | 5,7 s |
| Tắt index scan (đúng nhất) | 0,95 s |
| **Tắt hash join (mô hình chọn)** | **32 s**, mất thêm 26 s |

- Phần lớn câu JOB chạy dưới 1 giây, nên chọn đúng chỉ tiết kiệm vài chục đến vài trăm mili giây. **Một lần sai ở 26a bằng phần lợi của hàng chục lần đúng.**
- Bỏ 3 câu sai nặng nhất thì mô hình đã nhanh hơn PostgreSQL. Tab 4 cho thấy cùng hiện tượng: luật "≥2 hash join thì tắt hash join" đúng 13 câu chỉ được khoảng 1 giây, sai 15 câu mất khoảng 77 giây.
- So sánh dễ hiểu: lời 10 lần, mỗi lần 1 đồng, nhưng lỗ 1 lần 30 đồng thì tổng vẫn lỗ.

> "Một lần sai làm mất nhiều thời gian hơn rất nhiều so với phần tiết kiệm khi đúng. Câu 26a: PostgreSQL 5,7 giây, mô hình chọn tắt hash join mất 32 giây. Vì vậy mô hình đúng khoảng một nửa mà tổng vẫn chậm hơn PostgreSQL. Đúng nhiều lần chưa đủ, phải tránh được lần sai đắt."

---

## 5. Khai phá dữ liệu và ngưỡng tin

### Ngưỡng tin là gì?
- Mô hình cho biết **độ tin** của từng phương án (tổng 100%). Ở tab 5 đây là biểu đồ "Mô hình tin bao nhiêu".
- **Ngưỡng tin 60%:** độ tin của phương án được chọn ≥ 60% thì đổi cách chạy; dưới 60% thì **giữ nguyên PostgreSQL**.

| Câu | Mô hình chọn | Độ tin | Theo ngưỡng 60% | Kết quả |
|---|---|---|---|---|
| 26a | Tắt hash join | 35% | Giữ nguyên | Tránh được 32 s, chỉ mất 5,7 s |
| 17c | Tắt nested loop | 91% | Đổi | 6,7 s → 3,6 s |

- Random Forest: không có ngưỡng thì **0,80×**, có ngưỡng 60% thì **1,06×**.
- Code chỉ vài dòng: [exp2_abstain.py:45-52](scripts/exp2/exp2_abstain.py#L45-L52).
- So sánh dễ hiểu: bác sĩ mới ra trường chỉ kê thuốc mạnh khi chắc chắn, còn không thì dùng phác đồ chuẩn.

> "Ngưỡng tin là mức chắc chắn tối thiểu để mô hình được đổi cách chạy. Dưới 60% thì giữ nguyên PostgreSQL. Câu 26a mô hình chỉ tin 35% nên giữ nguyên, tránh được việc chạy 32 giây."

### "Ngưỡng 60% cho 1,06× nhưng chỉ đổi 6/233 lần, đều ở họ câu 17" nghĩa là gì?
- Với ngưỡng 60%, trong 233 lần kiểm tra: **227 lần giữ nguyên PostgreSQL**, **6 lần đổi**.
- 6 lần đổi đó:

| Split | Câu | Chọn | Độ tin | PostgreSQL | Theo mô hình |
|---|---|---|---|---|---|
| LOO-1 | 17c | Tắt nested loop | 91% | 6,7 s | 3,6 s |
| LOO-2 | 17f | Tắt nested loop | 90% | 9,2 s | 5,2 s |
| LOO-3 | 17b | Tắt nested loop | 89% | 7,4 s | 5,3 s |
| RND-1 | 17b | Tắt nested loop | 87% | 7,4 s | 5,3 s |
| RND-1 | 17e | Tắt nested loop | 75% | 12,3 s | 5,5 s |
| RND-2 | 17b | Tắt nested loop | 89% | 7,4 s | 5,3 s |

  Cả 6 lần đều đúng và đều nhanh hơn, tổng tiết kiệm khoảng 20 giây. Câu 17b xuất hiện 3 lần vì nằm trong tập test của 3 split, nên thực tế chỉ có 4 câu khác nhau.
- **Hẹp** ở chỗ mô hình chỉ đủ tự tin ở **1/33 họ câu**. Nếu workload không có câu kiểu họ 17 thì sẽ được khoảng 1,00×. Mức 1,06× còn xa dư địa 1,53×.
- So sánh dễ hiểu: làm trắc nghiệm có trừ điểm, chỉ khoanh 6 câu chắc chắn và đúng cả 6. Điểm dương nhưng chưa cao.

> "Với ngưỡng 60%, mô hình giữ nguyên PostgreSQL 227 lần, chỉ đổi 6 lần. Cả 6 lần đều đúng, đều là tắt nested loop ở họ câu 17, nên tổng thể nhanh hơn 1,06 lần. Lợi ích còn hẹp vì mô hình chỉ tự tin ở một họ câu."

### Tab 4 "Khai phá dữ liệu" nói gì?
Mạch của tab: **① Tìm luật → ② Rút ra nguyên nhân → ③ Sửa và đo lại.**
- ① Luật kết hợp dạng "NẾU câu có đặc điểm A THÌ tắt X có lợi". Thử **695 luật**, giữ lại **37 luật** (lift > 1,5, kiểm định Fisher có hiệu chỉnh p < 0,05) ([exp2_mining.py:92-121](scripts/exp2/exp2_mining.py#L92-L121)).
- ② Luật nổi bật "≥2 hash join → tắt hash join": khớp 28 câu, đúng 13, lift khoảng **2,8**. Nhưng áp cả 28 câu thì 13 câu nhanh hơn được khoảng **1 giây**, còn 15 câu chậm hơn mất khoảng **77 giây** (26a mất 26 s, 10c mất 23 s). Bài học: **chỉ đổi khi chắc chắn**.
- ③ Áp ngưỡng tin 60%: Random Forest từ 0,80 lên **1,06×**. Kết quả ổn định khi ngưỡng từ 50% đến 70%.
- Nếu cô hỏi:
  - *Khác Apriori thế nào?* Cùng ý tưởng: mỗi câu là một giao dịch gồm các đặc điểm và kết quả, tính support, confidence, lift, rồi thêm kiểm định thống kê để loại luật ngẫu nhiên.
  - *Sao chỉ Random Forest vượt 1?* Random Forest lấy trung bình nhiều cây nên độ tin đáng tin hơn.
  - *Còn 65 lần chậm hơn?* Đó là các câu rất ngắn. Riêng EXPLAIN (khoảng 5 ms) đã vượt 10%, và luôn giữ nguyên PostgreSQL cũng bị y như vậy.

---

## 6. Ablation: GEQO, bitmap scan, TID scan

### GEQO là gì?
- **Genetic Query Optimizer**: bộ tối ưu dùng **thuật toán di truyền**, PostgreSQL dùng khi câu nối **từ 12 bảng trở lên** (`geqo_threshold = 12`).
- Dưới 12 bảng, PostgreSQL thử gần như mọi thứ tự nối (quy hoạch động). Từ 12 bảng trở lên, số thứ tự lên tới hàng tỉ, nên GEQO tạo ngẫu nhiên các thứ tự rồi "lai ghép" và "chọn lọc" tới khi được plan **đủ tốt**. Nhanh nhưng không đảm bảo tốt nhất.
- JOB có các câu 12–17 bảng như 24b, 26a, 28a.
- **Ablation 8.5 (`SET geqo TO off`)**, Kaggle 8 lượt: tổng 202,7 s → 205,4 s, gần như không đổi. Nhưng **12 câu thay đổi rõ** (3 nhanh hơn, 9 chậm hơn). Trên Mac: 24b chậm đi 3,8×, 28a chậm đi 8,2×.

### Bitmap scan và TID scan là gì?

| Cách đọc | Hoạt động | Hợp khi |
|---|---|---|
| Seq scan | Đọc toàn bảng | Lấy nhiều dòng |
| Index scan | Tra index rồi nhảy tới từng dòng | Lấy rất ít dòng |
| **Bitmap scan** | Tra index để **đánh dấu các trang** cần đọc, rồi đọc các trang đó **theo thứ tự trên đĩa** | Lượng dòng vừa phải |
| **TID scan** | Lấy dòng theo **địa chỉ vật lý** (`ctid`) | Rất hiếm |

- So sánh dễ hiểu với bitmap scan: tra mục lục, đánh dấu trước các trang cần đọc, rồi lật sách một lượt.
- **Ablation 8.4 (tắt bitmap + TID scan)**: bài báo tắt vì một số LQO không hỗ trợ hai cách đọc này. Kaggle: tổng 202,7 s → 200,6 s, **10 câu thay đổi rõ** (6 nhanh hơn, 4 chậm hơn). Trên Mac: 15c chậm đi 3,5×, 30c nhanh lên 3,7×. Cùng một thay đổi mà tác động theo hai chiều.

> "GEQO là bộ tối ưu di truyền, dùng khi câu nối từ 12 bảng trở lên. Bitmap scan nằm giữa index scan và seq scan: đánh dấu các trang cần đọc rồi đọc theo thứ tự. TID scan đọc theo địa chỉ vật lý, rất hiếm. Tắt từng cái thì tổng gần như không đổi, nhưng 10–12 câu thay đổi rõ theo cả hai chiều."

---

## 7. Hạn chế

1. **Máy yếu hơn máy tác giả.** Bộ nhớ cho PostgreSQL ít hơn (8 GB so với 32 GB) nên câu nào cũng chậm hơn bài báo. Nhóm không so số giây mà so **tỉ lệ nhanh/chậm so với PostgreSQL** đo trên cùng máy.
2. **HybridQO train ít hơn.** Chỉ 11 epoch (0–10, test ở epoch 10) so với 50 epoch của tác giả, vì Kaggle giới hạn 12 giờ mỗi phiên. Kế hoạch ban đầu là 15 epoch nhưng khi đó các split dừng ở các epoch khác nhau. Log tác giả cho thấy từ epoch 10 kết quả đã ổn định khoảng 1,00× tới epoch 49. Kết quả là HybridQO gần như giữ plan PostgreSQL, chỉ đổi **8/233** lần.
3. **Oracle chưa phải tối ưu tuyệt đối.** Oracle chỉ là "chọn đúng trong 6 cách thử". Ngoài 6 cách này còn có thể có cách nhanh hơn.
4. **Ngưỡng tin 60% mới giúp được ít câu.** Ngưỡng được chọn sau khi thử, nhưng từ 50% đến 70% đều cho khoảng 1,06× nên không phải chọn may. Tuy vậy mô hình chỉ đổi **6/233** lần, đều ở họ 17.

Câu ngắn cho slide:
- Máy ít RAM hơn bài báo → so tỉ lệ, không so số giây.
- HybridQO train 11/50 epoch → gần như giữ plan PostgreSQL (đổi 8/233 lần).
- Oracle = tốt nhất trong 6 cách thử, chưa phải tối ưu tuyệt đối.
- Ngưỡng tin 60% → 1,06× nhưng chỉ đổi 6/233 lần, đều ở họ câu 17.
