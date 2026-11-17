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
- Bao là một bộ tối ưu học máy (LQO). Bao **không tự viết plan mới**. Nó **chọn 1 trong 5 cấu hình** (gọi là arm, hay bộ gợi ý) của bộ tối ưu sẵn có, ví dụ giữ nguyên, tắt nested loop, tắt merge join. Chi tiết 5 arm ở mục [Arm của Bao là gì](#arm-của-bao-là-gì-vì-sao-chỉ-5-arm).
- Việc lập 5 plan và hỏi mô hình mất khoảng **0,1–0,2 giây mỗi câu**. Đây là lý do Bao hay thua ở câu ngắn.
- Khi bật học (`enable_bao_rewards`), Bao ghi lại thời gian thật để train lại.

> "pg_bao là PostgreSQL 12.5 gắn extension Bao. Khi bật Bao, PostgreSQL lập 5 plan theo 5 bộ gợi ý, gửi sang bao_server để mạng nơ-ron dự đoán thời gian, rồi chạy plan nhanh nhất."

### Bao có chạy thật cả 5 arm rồi chọn cái nhanh nhất không?
**Không.** Bao chỉ **lập plan** cho 5 arm, **dự đoán** thời gian, rồi **chạy thật đúng 1 plan**.

| Bước | Ở đâu | Làm gì | Chạy câu? |
|---|---|---|---|
| 1 | pg_bao, [bao_planner.h:390-393](lqo_ml_perspective/bao/pg_extension/bao_planner.h#L390-L393) | Lặp 5 arm: bật/tắt cờ rồi gọi bộ tối ưu PostgreSQL lập plan | Không |
| 2 | bao_server, [main.py:36-37](lqo_ml_perspective/bao/bao_server/main.py#L36-L37) | Mô hình dự đoán thời gian 5 plan, chọn `argmin` | Không |
| 3 | pg_bao | Chạy plan được chọn, gửi thời gian thật về để train | **Có, 1 lần** |

- Chưa có mô hình thì chọn luôn plan mặc định của PostgreSQL ([main.py:31-32](lqo_ml_perspective/bao/bao_server/main.py#L31-L32)).
- Bao chỉ biết thời gian thật của arm đã chạy. Nó dùng Thompson sampling để thỉnh thoảng thử arm khác.
- Khác mô hình nhóm: nhóm chỉ `EXPLAIN` 1 lần (plan mặc định), mô hình đoán thẳng phương án (khoảng 25 ms so với 150 ms của Bao). Nhóm đã chạy thật đủ 6 phương án **một lần lúc thu thập dữ liệu** để làm nhãn và tính Oracle, không chạy lúc dùng mô hình.

> "Bao không chạy thử cả 5 cách. Nó lập 5 plan, mạng nơ-ron dự đoán thời gian từng plan, rồi chỉ chạy plan có dự đoán nhỏ nhất. Phần lập 5 plan và dự đoán là khoảng 0,15 giây mỗi câu."

### Arm của Bao là gì? Vì sao chỉ 5 arm?
- Một **arm** là một **tổ hợp bật/tắt** 6 cờ `enable_*` của PostgreSQL. Arm **không phải** "mỗi cờ một arm": có arm tắt 3 cờ cùng lúc.
- 6 cờ có 2⁶ = **64 tổ hợp** (mỗi cờ có 2 trạng thái on/off). Code pg_bao định nghĩa **26 arm** (`BAO_MAX_ARMS = 26`, [bao_configs.h:6](lqo_ml_perspective/bao/pg_extension/bao_configs.h#L6); `case 0`–`case 25` trong [bao_planner.h](lqo_ml_perspective/bao/pg_extension/bao_planner.h)). Cả 26 khác nhau, không arm nào tắt cả 3 loại join, không arm nào tắt quá 4 cờ.
- Tham số `bao_num_arms` mặc định là **5** (cho phép 1–26, [main.c:119-128](lqo_ml_perspective/bao/pg_extension/main.c#L119-L128)). Tác giả ghi: *"Higher values give better plans, but higher optimization times."* Tác giả bài báo giữ nguyên 5 ([run_queries.py:35](lqo_ml_perspective/bao/run_queries.py#L35)).
- Vì sao chỉ 5: mỗi arm thêm là thêm 1 lần lập plan và 1 plan đưa qua mô hình, **cho mọi câu**. Với 5 arm đã tốn khoảng 0,15 s mỗi câu.
- Chi phí tăng theo **số arm**, không theo **số cờ**. Thêm cờ mà vẫn giữ 5 arm thì tốc độ không đổi, chỉ là chọn 5 arm từ tập lớn hơn.

5 arm mặc định:

| Arm | Tắt |
|---|---|
| 0 | không tắt gì (default) |
| 1 | nested loop |
| 2 | merge join + index scan |
| 3 | nested loop + merge join + index scan |
| 4 | merge join |

5 arm này **không bao giờ tắt hash join, seq scan hay index-only scan**.

> "Bao có sẵn 26 arm, mỗi arm là một tổ hợp bật/tắt 6 cờ của PostgreSQL, nhưng mặc định chỉ xét 5 và tác giả bài báo giữ nguyên. Mỗi arm thêm là thêm một lần lập plan cho mọi câu; với 5 arm đã tốn khoảng 0,15 giây mỗi câu. Đây là đánh đổi giữa plan tốt hơn và thời gian tối ưu."

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

### 6 phương án là gì? Có lấy từ bài báo hay Bao không?
Mỗi phương án tắt **đúng 1 loại toán tử** bằng lệnh `SET` trước khi chạy ([app/prototype.py:25-31](app/prototype.py#L25-L31)):

| Phương án | Lệnh | Ý nghĩa |
|---|---|---|
| `default` | (không có) | Giữ plan PostgreSQL tự chọn |
| `no_nestloop` | `SET enable_nestloop = off` | Không nối bằng nested loop |
| `no_hashjoin` | `SET enable_hashjoin = off` | Không nối bằng hash join |
| `no_mergejoin` | `SET enable_mergejoin = off` | Không nối bằng merge join |
| `no_seqscan` | `SET enable_seqscan = off` | Hạn chế quét toàn bảng |
| `no_indexscan` | `SET enable_indexscan = off` + `enable_indexonlyscan = off` | Không đọc qua index |

Ý nghĩa 6 cờ:

| Cờ | Cách làm | Tốt khi |
|---|---|---|
| nested loop | Mỗi dòng bảng ngoài tìm dòng khớp ở bảng trong (thường qua index) | Bảng ngoài rất ít dòng |
| hash join | Dựng bảng băm từ bảng nhỏ, duyệt bảng lớn một lượt để dò | Hai bảng lớn, điều kiện `=` |
| merge join | Sắp xếp 2 bảng theo khóa rồi đi song song | Dữ liệu đã có thứ tự |
| seq scan | Đọc toàn bộ bảng | Lấy nhiều dòng |
| index scan | Tra index rồi nhảy tới bảng | Lấy ít dòng |
| index-only scan | Lấy dữ liệu ngay trong index | Mọi cột cần đều có trong index |

- `off` **không cấm hẳn**, chỉ cộng chi phí rất lớn. Không còn cách khác thì PostgreSQL vẫn dùng.
- **Cả 6 cờ là tham số có sẵn của PostgreSQL**, không phải của pg_bao. pg_bao chỉ bật/tắt chúng theo arm. Tham số riêng của pg_bao là `enable_bao`, `bao_num_arms`, `bao_host`…
- **Nguồn gốc:** nhóm lấy đúng 6 cờ mà Bao dùng ([reg_blocker.py:17-20](lqo_ml_perspective/bao/bao_server/reg_blocker.py#L17-L20)), nhưng **cách chia 6 phương án là nhóm tự thiết kế**:

| Phương án nhóm | Trong 5 arm mặc định của Bao? | Trong 26 arm của Bao? |
|---|---|---|
| `default` | Có (arm 0) | Có |
| `no_nestloop` | Có (arm 1) | Có |
| `no_mergejoin` | Có (arm 4) | Có |
| `no_seqscan` | Không | Có (arm 17) |
| `no_hashjoin` | **Không** | **Không** (Bao chỉ tắt hash join kèm cờ khác) |
| `no_indexscan` | **Không** | **Không** (Bao chỉ tắt riêng indexscan hoặc indexonlyscan) |

- `no_hashjoin` lại là nhãn phổ biến thứ hai (14/113 câu) và là lựa chọn sai đắt nhất ở 26a.

> "6 phương án dùng đúng 6 cờ enable_* có sẵn của PostgreSQL mà Bao cũng dùng. Nhưng cách chia là của nhóm: mỗi phương án tắt đúng 1 loại toán tử. Bao mặc định chỉ chọn 5 tổ hợp và không bao giờ tắt hash join hay seq scan; 'tắt hash join' và 'tắt index scan' của nhóm không có trong cả 26 arm của Bao."

### Sao không thêm bitmap scan, TID scan, GEQO vào 6 phương án?
- Ba tham số này **cũng là cấu hình có sẵn của PostgreSQL**, mặc định `on` ([infra/postgresql.lqo.conf:24-26](infra/postgresql.lqo.conf#L24-L26)). Nhóm chỉ tắt chúng **cho cả workload** trong ablation 8.4 và 8.5, không chọn theo từng câu.
- **TID scan:** chỉ dùng khi SQL có `WHERE ctid = ...`. JOB có 0/113 câu như vậy, plan mặc định có 0/113 `Tid Scan`, nên tắt cũng không đổi gì.
- **GEQO:** không phải toán tử mà là **cách tìm thứ tự join**, chỉ có tác dụng với câu ≥ 12 bảng. Tắt thì lập plan lâu hơn.
- **Bitmap scan:** có tác dụng thật, xuất hiện trong **69/113** plan mặc định. Ablation 8.4 cho thấy tắt nó làm 10 câu đổi rõ (6 nhanh hơn, 4 chậm hơn). Nhóm không thêm vì giữ cùng 6 cờ với Bao để so sánh, và mỗi phương án thêm là đo thêm 113 câu × 3 lần. Đây là **hướng mở rộng**: `no_bitmapscan` làm phương án thứ 7. Thêm phương án không làm mô hình nhóm chậm hơn lúc ra quyết định (vẫn 1 lần EXPLAIN).

> "Nhóm giữ đúng 6 cờ của Bao để so sánh được. TID scan không câu JOB nào dùng, GEQO là chiến lược tìm thứ tự join chứ không phải toán tử. Bitmap scan có trong 69/113 plan và tắt nó làm khoảng 10 câu thay đổi theo cả hai chiều, nên thêm 'tắt bitmap scan' là hướng mở rộng nhóm chưa làm."

### "Giữ nguyên PostgreSQL" có phải là bật hết nested loop, hash join, merge join, seq scan, index scan?
- **Đúng.** Phương án `default` không `SET` gì ([app/prototype.py:26](app/prototype.py#L26)), nên mọi cờ `enable_*` giữ giá trị mặc định là `on`. Đã kiểm tra trực tiếp trên `pg_bao`: `enable_nestloop`, `enable_hashjoin`, `enable_mergejoin`, `enable_seqscan`, `enable_indexscan`, `enable_indexonlyscan` đều `on`.
- Các cờ khác cũng `on`: `enable_bitmapscan`, `enable_tidscan`, `enable_material`, `enable_sort`…, và `geqo = on`. Mỗi phương án "Tắt …" chỉ tắt đúng 1 loại, các cờ còn lại giữ như mặc định.
- Khi kết nối, dashboard chỉ đặt thêm chế độ chỉ đọc, `statement_timeout` và `enable_bao = off` (để Bao không can thiệp) ([app/prototype.py:82-96](app/prototype.py#L82-L96)).
- **Bật hết không có nghĩa là dùng hết.** Planner vẫn chọn plan có cost ước lượng thấp nhất, nên một plan có thể chỉ có hash join và seq scan.

> "Giữ nguyên PostgreSQL là không SET gì, mọi cờ enable_* đều bật, PostgreSQL tự chọn plan rẻ nhất theo ước lượng. 5 phương án còn lại mỗi cái chỉ tắt đúng 1 loại toán tử."

### Ba mô hình train thế nào? Input và output là gì?
Ba mô hình là **Decision Tree, Random Forest và LightGBM** (không có Logistic Regression). Đây là bài toán **phân loại có giám sát 6 lớp**: mỗi câu SQL là 1 mẫu.

| | Nội dung |
|---|---|
| **Input (X)** | 34 đặc trưng (11 từ SQL + 23 từ plan EXPLAIN mặc định), xem mục "34 đặc trưng là gì?". Có trước khi chạy câu, mất vài ms |
| **Output (y)** | 1 trong 6 nhãn: `default`, `no_nestloop`, `no_hashjoin`, `no_mergejoin`, `no_seqscan`, `no_indexscan`. Mô hình trả thêm xác suất từng lớp (biểu đồ "độ tin" ở Bước 3 tab Demo) |

**Cách tạo nhãn** ([exp2_analyze.py:75-109](scripts/exp2/exp2_analyze.py#L75-L109)):
1. Chạy thật mỗi câu × 6 phương án × 3 lần, lấy **lần thứ 3** (cache đã ấm). Thời gian = planning + execution. Timeout hoặc thiếu số đo tính là 180 s.
2. Phương án nào cho plan giống hệt `default` thì gán cùng thời gian với `default`, để nhiễu đo không tạo "người thắng" giả.
3. Nhãn là phương án nhanh nhất. **Nếu nhanh hơn `default` dưới 5% thì nhãn vẫn là `default`**, vì không đáng đổi.

Phân bố nhãn 113 câu JOB: `default` 60, `no_hashjoin` 14, `no_indexscan` 13, `no_seqscan` 11, `no_nestloop` 10, `no_mergejoin` 5. Dữ liệu lệch: hơn nửa là "giữ nguyên".

**Siêu tham số** ([exp2_analyze.py:56-64](scripts/exp2/exp2_analyze.py#L56-L64)): không chuẩn hoá đặc trưng (mô hình cây không cần), không đặt trọng số lớp, seed cố định.

| Mô hình | Tham số |
|---|---|
| Decision Tree | `max_depth=4`, `min_samples_leaf=3` (cây nông để đọc được luật) |
| Random Forest | 300 cây, `min_samples_leaf=2` |
| LightGBM | 200 cây, `learning_rate=0.05`, `num_leaves=15`, `min_child_samples=5` |

**Train và đánh giá:**
- **Thí nghiệm 2:** train trên đúng **9 split của bài báo** (LOO/RND/BQ × 3). Không chấm bằng accuracy mà bằng **thời gian**: EXPLAIN + suy luận + thời gian thật của phương án được chọn, so với PostgreSQL (thắng/hòa/thua ±10%), Oracle và Bao.
- **Tab Demo:** train trên cả 113 câu JOB. Nếu tick "không cho học các câu cùng họ" thì bỏ cả họ của câu đang demo (chọn 23a thì bỏ 23a, 23b, 23c) để mô hình gặp câu như câu mới ([app/prototype.py:61-67](app/prototype.py#L61-L67)).

**Khác Bao thế nào:** Bao lập plan cho cả 5 arm, dùng mạng cây (TCNN) đoán thời gian từ cây plan và học kiểu bandit, **chỉ chạy thật arm nó chọn**. Nhóm thì **chạy thật đủ 6 phương án** để có nhãn đúng, rồi dùng mô hình cây nhỏ phân loại trên 34 con số.

> "Input là 34 con số lấy từ câu SQL và plan EXPLAIN. Output là 1 trong 6 cấu hình hint. Nhãn có được bằng cách chạy thật cả 6 cấu hình và lấy cái nhanh nhất; nếu không nhanh hơn mặc định ít nhất 5% thì giữ mặc định. Ba mô hình cây train có giám sát trên 9 split giống bài báo và được chấm bằng thời gian chạy thật, không chỉ accuracy."

### HybridQO hoạt động thế nào? Input, output và cách train?
HybridQO (còn gọi là HyperQO, bài "Cost-based or Learning-based? A Hybrid Query Optimizer for Query Plan Selection", VLDB 2022) là một LQO bài báo đánh giá. Code nằm ở [lqo_ml_perspective/hybrid_qo/](lqo_ml_perspective/hybrid_qo/). "Hybrid" nghĩa là **kết hợp**: mô hình chỉ đề xuất vài plan ứng viên, còn PostgreSQL (dựa trên cost) vẫn tự lập phần còn lại của plan.

**Khác nhóm và Bao ở chỗ chọn cái gì:** HybridQO không bật/tắt toán tử mà **chọn thứ tự nối của 2 bảng đầu tiên** (`leading_length = 2`), áp vào câu bằng hint `/*+ Leading(t mk) */` của pg_hint_plan ([Hinter.py:63](lqo_ml_perspective/hybrid_qo/Hinter.py#L63)).

**Các bước cho mỗi câu** (`hinterRun`, [Hinter.py:74](lqo_ml_perspective/hybrid_qo/Hinter.py#L74)):
1. EXPLAIN lấy plan mặc định của PostgreSQL.
2. **MCTS** (tìm kiếm cây Monte Carlo, [mcts.py](lqo_ml_perspective/hybrid_qo/mcts.py)) dùng một mạng nhỏ để đề xuất các cặp bảng nối đầu tiên đáng thử.
3. Với mỗi ứng viên: gắn `Leading(...)` rồi EXPLAIN để PostgreSQL lập plan đầy đủ.
4. **Mạng giá trị** (TreeLSTM, 10 "đầu" như một ensemble nhỏ) dự đoán thời gian của từng plan, kèm độ bất định (mean và độ lệch giữa 10 đầu). Plan mặc định cũng được chấm cùng lúc.
5. **Chỉ đổi plan khi đủ 3 điều kiện** ([Hinter.py:87](lqo_ml_perspective/hybrid_qo/Hinter.py#L87)):
   - plan ứng viên được dự đoán nhanh hơn plan mặc định;
   - **KNN** trên các lần dự đoán sai trước đó cho thấy mô hình đủ tin cậy (sai số ước lượng dưới khoảng 3 lần, `threshold = log 3 / log 180 000`);
   - plan mặc định dự đoán chạy **lâu hơn 100 ms** (câu ngắn thì không đáng đổi).
   Không đủ điều kiện thì **giữ nguyên PostgreSQL**. Ý tưởng này giống ngưỡng tin 60% của nhóm.
6. Chạy thật plan được chọn. Nếu bị timeout thì chạy lại plan PostgreSQL.

| | HybridQO |
|---|---|
| **Input** | (a) **Véc-tơ câu SQL**: ma trận bảng nào nối với bảng nào (40 × 40 alias) và độ chọn lọc của các điều kiện lọc theo cột (100 cột), lấy bằng EXPLAIN từng điều kiện trên một bảng ([sql2fea.py:25-82](lqo_ml_perspective/hybrid_qo/sql2fea.py#L25-L82)). (b) **Cây plan**: mỗi nút gồm 9 số: loại nút (3 loại join + 4 loại scan, one-hot), total cost và số dòng ước lượng |
| **Output** | Thời gian chạy dự đoán (thang log) + độ bất định cho mỗi plan. Quyết định cuối: một hint `Leading(...)` hoặc giữ plan PostgreSQL |
| **Nhãn** | Thời gian chạy thật của plan đã chọn (và plan PostgreSQL khi cần), mã hoá theo log |
| **Kiểu học** | **Học trực tuyến**: chạy câu nào thì học câu đó ngay, cập nhật mạng giá trị, mạng của MCTS và bộ nhớ KNN. Không có tập nhãn đo sẵn như nhóm |

**Cách train trong bài báo và trong nhóm:**
- Cùng 9 split như Bao và nhóm. Train bằng cách chạy lặp tập train nhiều epoch (tác giả 50 epoch), test ở epoch 0, 10, 20…, 49 ([run_mcts.py](lqo_ml_perspective/hybrid_qo/run_mcts.py)).
- Lưu ý: code gốc gọi **cùng hàm `hinterRun`** cho câu test, mà hàm này cũng cập nhật mô hình sau mỗi câu. Tức là trong lúc test, mô hình vẫn học tiếp.
- Nhóm chạy trên **Kaggle, 11 epoch (0–10), so ở epoch 10**, vì giới hạn 12 giờ mỗi phiên. Log tác giả cho thấy từ epoch 10 tới 49 kết quả gần như đứng yên khoảng 1,00× (xem [HUONG_DAN_KAGGLE_HYBRIDQO.md](HUONG_DAN_KAGGLE_HYBRIDQO.md) mục "Vì sao 11 epoch"). Siêu tham số giữ nguyên như tác giả. Nhóm chỉ vá để dừng đúng giờ và để chạy được khi không có GPU.

**Kết quả của nhóm** (9 split, epoch 10, [c1_HybridQO_kaggle_9split_summary.csv](analysis/output/c1_HybridQO_kaggle_9split_summary.csv)):
- **0 thắng / 124 hòa / 109 thua, 0,97×**. Bài báo (log tác giả): 34 / 82 / 117, 1,00×.
- HybridQO **chỉ đổi plan 8/233 lần**, còn lại giữ plan PostgreSQL. Nếu chỉ tính thời gian thực thi thì speedup khoảng **1,00×** ở mọi split.
- **Vì sao thua dù gần như giữ nguyên plan:** chi phí ra quyết định (MCTS + nhiều lần EXPLAIN + mạng TreeLSTM) khoảng **0,5–2,5 s mỗi split**. Với câu chạy nhanh, phần chi phí này vượt ngưỡng 10% nên bị tính là thua.

**So sánh ba cách:**

| | Bao | HybridQO | Mô hình nhóm |
|---|---|---|---|
| Chọn cái gì | 1 trong 5 tổ hợp bật/tắt toán tử | Thứ tự nối 2 bảng đầu (`Leading`) | 1 trong 6 phương án tắt 1 toán tử |
| Cần pg_hint_plan | Không (extension pg_bao) | **Có** | Không |
| Mô hình | Mạng cây TCNN đoán thời gian | MCTS + TreeLSTM 10 đầu + KNN | Cây quyết định / RF / LightGBM phân loại |
| Input | Cây plan của từng arm | Véc-tơ SQL + cây plan của từng ứng viên | 34 con số từ SQL + plan mặc định |
| Học | Trực tuyến, bandit | Trực tuyến, nhiều epoch | Có giám sát, nhãn đo sẵn đủ 6 phương án |
| Cơ chế an toàn | Không có | KNN + ngưỡng 100 ms → giữ PostgreSQL | Ngưỡng tin 60% → giữ PostgreSQL |
| Kết quả nhóm đo | 1,08× (Mac), 0,92× (Kaggle) | 0,97×, đổi 8/233 lần | 0,80×; 1,06× với ngưỡng tin |

> "HybridQO không tắt toán tử mà chọn 2 bảng nối đầu tiên rồi để PostgreSQL lập phần còn lại, ép bằng hint Leading của pg_hint_plan. Nó dùng MCTS tìm ứng viên, mạng TreeLSTM đoán thời gian và KNN để biết khi nào không nên tin mô hình. Nhờ cẩn thận nên nó gần như luôn giữ plan PostgreSQL, chỉ đổi 8 trên 233 lần, nhưng tốn thời gian suy nghĩ nên tổng chậm hơn một chút: 0,97 lần."

### Feature importance: mô hình dựa vào đặc trưng nào? Ví dụ câu 23a
**Ví dụ câu 23a** (train 110 câu, đã bỏ 3 câu cùng họ 23, giống tab Demo):

| Phương án | default | no_nestloop | **no_hashjoin** | no_mergejoin | no_seqscan | no_indexscan |
|---|---|---|---|---|---|---|
| ms (lần 3) | 171,7 | 778,6 | **115,2** | 171,7 | 172,6 | 178,3 |

Nhãn đúng là `no_hashjoin`, nhanh hơn mặc định khoảng 1,49×.

| Mô hình | Chọn | Độ tin | Kết quả |
|---|---|---|---|
| Decision Tree | `no_indexscan` | 75% | Sai, nhưng chỉ chậm ~4% → **hòa** |
| Random Forest | `no_hashjoin` | 37% (default 28%) | Đúng, nhưng không chắc lắm |
| LightGBM | `no_hashjoin` | ~100% | Đúng |

**Top 10 đặc trưng quan trọng** (xếp theo RF, mỗi cột chuẩn hoá tổng = 1). DT và RF dùng mức giảm impurity, LightGBM dùng tổng gain:

| Đặc trưng | DT | RF | LightGBM | Câu 23a | Trung vị 113 câu |
|---|---|---|---|---|---|
| plan_total_cost | 0,095 | **0,104** | **0,174** | 57 936 | 11 197 |
| plan_startup_cost | 0 | 0,083 | 0 | 57 936 | 11 197 |
| sql_len | 0,149 | 0,075 | 0,099 | 990 | 776 |
| plan_nodes | **0,217** | 0,073 | 0,075 | 26 | 19 |
| sql_n_filter_preds | **0,230** | 0,058 | 0,089 | 8 | 7 |
| plan_depth | 0 | 0,055 | 0,020 | 15 | 11 |
| plan_n_indexonlyscan | 0,118 | 0,046 | 0,027 | 2 | 0 |
| plan_n_nestloop | 0,073 | 0,046 | 0,048 | 7 | 7 |
| sql_n_join_preds | 0 | 0,045 | 0,059 | 16 | 11 |
| plan_n_indexscan | 0 | 0,045 | 0,086 | 5 | 5 |

- **Quan trọng nhất là cost ước lượng và độ lớn của câu** (cost, số node, độ dài SQL, số điều kiện lọc), chứ không phải số lượng từng loại toán tử. Câu 23a có cost gấp khoảng 5 lần trung vị.
- **Decision Tree chỉ dùng vài đặc trưng** (sâu tối đa 4) nên nhiều ô bằng 0. RF trải đều hơn, LightGBM dồn vào `plan_total_cost`.
- `plan_startup_cost` gần như trùng `plan_total_cost`, nên RF chia đôi importance cho hai cột. Nên nói hai cột này là cùng một thông tin.

**Vì sao Decision Tree chọn sai 23a?** Đường đi của câu trong cây:
```
plan_nodes = 26 > 25.5
plan_n_mergejoin = 0 <= 0.5
plan_n_seqscan = 4 <= 5.5
→ lá: no_indexscan (chỉ 4 câu train rơi vào lá này)
```
Cây hỏi 3 câu rồi đưa 23a vào một lá chỉ có 4 câu train, nên dễ sai. RF và LightGBM gộp nhiều cây nên ổn định hơn.

**Lưu ý:**
- **Feature importance là toàn cục**: cho biết mô hình hay dựa vào đặc trưng nào trên cả tập train, không giải thích riêng một câu. Muốn giải thích một câu thì xem đường đi trong cây (như trên) hoặc dùng SHAP.
- Bảng trên train trên 110 câu JOB nên hơi khác bản ở tab "3. Nhóm: Thí nghiệm 2" ([exp2_feature_importance_all.csv](analysis/output/exp2/exp2_feature_importance_all.csv), train trên toàn bộ dữ liệu). Thứ tự top đầu gần giống nhau.

> "Feature importance cho thấy mô hình dựa nhiều nhất vào cost ước lượng và độ phức tạp của câu: số node, độ dài SQL, số điều kiện lọc. Ví dụ 23a: RF và LightGBM chọn đúng 'tắt hash join', nhanh hơn 1,5 lần; Decision Tree chọn 'tắt index scan' vì câu rơi vào một lá chỉ có 4 câu train, nhưng cũng chỉ chậm 4%, tính là hòa."

### Bước 4 tab Demo ("Chạy thật để kiểm tra mô hình đúng hay sai") có phải ablation không?
- **Không.** Bước 4 chạy thật câu đang chọn với **cả 6 phương án** để biết phương án nào thật sự nhanh nhất, rồi đối chiếu với phương án mô hình chọn ở Bước 3 ([app/prototype.py:293-311](app/prototype.py#L293-L311)).
- Mỗi phương án: mở kết nối, `SET` cờ tương ứng, chạy `EXPLAIN (ANALYZE, FORMAT JSON)` N lần, lấy lần cuối (`run_hint`, [app/prototype.py:124](app/prototype.py#L124)). Thời gian theo mô hình đã cộng EXPLAIN + suy luận. Kết luận thắng/hòa/thua theo ngưỡng ±10%.
- Đây chính là cách Thí nghiệm 2 **tạo nhãn**, chỉ làm lại cho 1 câu.
- Tắt từng toán tử ở đây là **6 lựa chọn để mô hình chọn 1**, không phải ablation. **Ablation** trong project là phần khác (mục 6): tắt GEQO, bitmap/TID scan **cho cả workload** để xem kết quả Bao/HybridQO có bị ảnh hưởng không.

> "Bước 4 chạy thật cả 6 cấu hình hint trên PostgreSQL để có đáp án đúng, rồi đối chiếu với lựa chọn của mô hình. Đây là cách nhóm tạo nhãn, không phải ablation; ablation là tắt GEQO, bitmap scan cho cả workload ở Thí nghiệm 1."

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

### So với Bao và HybridQO thì mô hình nhóm thế nào?
Mỗi phương pháp so với PostgreSQL đo cùng phiên, 9 split, 233 lần kiểm tra.

| Phương pháp | Thắng / hòa / thua | Speedup | Thấp nhất – cao nhất theo split |
|---|---|---|---|
| Bao (Mac) | 28 / 28 / 177 | 1,08× | 0,62 – 1,90 |
| Bao (Kaggle) | 8 / 46 / 179 | 0,92× | 0,66 – 1,61 |
| HybridQO (Kaggle) | 0 / 124 / 109 | 0,97× | 0,94 – 1,00 |
| Random Forest, không ngưỡng | 12 / 112 / 109 | 0,80× | 0,45 – 1,28 |
| **Random Forest, ngưỡng 60%** | **6 / 162 / 65** | **1,06×** | **0,97 – 1,31** |
| Oracle | 93 / 140 / 0 | 1,53× | 1,22 – 1,88 |

- Bao dao động mạnh nhất, kết quả còn đổi theo máy. HybridQO ổn định nhưng không thắng câu nào. Mô hình nhóm có ngưỡng **an toàn nhất**: không split nào dưới 0,97×.
- **Lưu ý khi so:** môi trường khác nhau (Mac và Kaggle), nên chỉ so tỉ lệ, không so giây. Mô hình nhóm được tính lại từ log đã đo đủ 6 phương án (thời gian phương án được chọn + EXPLAIN), không chạy trực tiếp như Bao và HybridQO. Ngưỡng 60% chọn sau khi thử.

> "Bao lúc nhanh gấp đôi, lúc chậm còn 0,6 lần; HybridQO gần như luôn chậm hơn PostgreSQL một chút. Mô hình nhóm có ngưỡng tin không split nào dưới 0,97 và tổng 1,06 lần. Nó thắng không phải nhờ đoán giỏi hơn mà nhờ biết lúc nào nên giữ nguyên PostgreSQL."

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
