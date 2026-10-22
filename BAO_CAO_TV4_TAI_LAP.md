# 4. CODE VÀ TÁI LẬP THỰC NGHIỆM

> **Phụ trách:** Phạm Thúy Vi · `(§x.y)` là mục trong bài báo của Lehmann và cộng sự (PVLDB 2024).

## 4.1. Mục tiêu

1. **Tái lập** kết luận chính của bài báo trên một nền tảng phần cứng khác: *PostgreSQL nhìn chung vẫn tốt nhất* (§8.2.1).
2. **Đo plan mới nhanh hơn bao nhiêu:** với mỗi câu truy vấn, chỉ ra plan cũ (của PostgreSQL), plan tối ưu và mức tăng tốc.
3. **Phân loại plan bằng data mining:** dự đoán mỗi câu nên dùng plan nào và **đếm số câu dự đoán đúng**, để chứng minh bằng thuật toán thay vì liệt kê từng câu.

Nhóm dùng mã nguồn và log mà tác giả công bố tại github.com/edualc/lqo_ml_perspective.

## 4.2. Hệ quản trị CSDL và môi trường

| Thành phần | Bài báo (§8.1.1, Bảng 2) | Nhóm |
|---|---|---|
| Phần cứng | x86, 16 CPU, 64 GB RAM, GPU T4 | MacBook M1 Pro (ARM64), 8 CPU, 16 GB RAM, không GPU |
| DBMS | PostgreSQL 12.5 + `pg_hint_plan` | Giống bài báo, build từ mã nguồn cho ARM64 |
| `shared_buffers` / `work_mem` / `effective_cache_size` | 32 GB / 4 GB / 32 GB | 3 GB / 128 MB / 8 GB |
| GEQO, bitmap/tid scan | Bật | Bật |
| `autovacuum` | Tắt, `ANALYZE` một lần | Giống bài báo |
| Đo thời gian | Chạy 3 lần, lấy lần thứ 3 (hot cache); timeout 3 phút | Giống bài báo |

**Lưu ý về hệ quản trị CSDL:**
- Phải dùng đúng PostgreSQL 12.5, vì `pg_hint_plan` và `pg_bao` chỉ hỗ trợ phiên bản này.
- Bộ nhớ phải thu nhỏ cho vừa 16 GB RAM. Vì vậy nhóm chỉ so sánh **xu hướng và thứ hạng**, không so sánh số tuyệt đối (§7.1).
- Giữ nguyên GEQO, bitmap/tid scan và autovacuum như bài báo, vì bài báo chứng minh thay đổi các thiết lập này làm thay đổi đáng kể kết quả (§8.4, §8.5).

**Triển khai:**
- Hệ thống gồm 2 container giống repo gốc: `pg_bao` (PostgreSQL) và `bao_server` (Bao, PyTorch).
- Để chạy trên ARM64, nhóm build PostgreSQL và các extension từ mã nguồn, đổi PyTorch sang bản aarch64, và sửa đường dẫn tải IMDB cùng tên CSDL trong `bao.cfg`.
- Dữ liệu IMDB nạp xong gồm 21 bảng, dung lượng 12 GB.

## 4.3. Phương pháp chạy lại

| Phương pháp | Yêu cầu (§8.2.2) | Kế hoạch |
|---|---|---|
| PostgreSQL | Không cần train | ✅ Chạy 113 câu JOB × 3 lần |
| Bao | CPU, khoảng 2 giờ/split | ✅ Ưu tiên BQ-1 (khó nhất); thêm RND-1 và LOO-1 nếu đủ thời gian |
| HybridQO, Neo, Balsa, LEON | 20–130 giờ/split, phần lớn cần GPU | ❌ Dùng log của tác giả |

Nhóm chạy thêm 3 ablation ít tốn kém:
- **Bitmap/tid scan** (§8.4) và **GEQO** (§8.5): mỗi thí nghiệm là một lần chạy lại baseline với thiết lập tương ứng bị tắt.
- **Số lần chạy *k*** (§8.6): lấy trực tiếp từ 3 lần chạy của baseline, không cần chạy thêm.

Hai ablation **covariate shift** (§8.3) và **cây bushy** (§8.7) cần thêm khoảng 10 GB ổ đĩa và hàng nghìn lần chạy, nên được để lại làm hướng mở rộng.

**Cách so sánh:** một câu là **thắng** nếu nhanh hơn PostgreSQL trên 10%, **thua** nếu chậm hơn trên 10%, còn lại là **hòa**. Kiểm định bằng Wilcoxon và sign test.

## 4.4. Metric đo câu SQL

| Loại | Metric |
|---|---|
| **Tĩnh** (đo độ phức tạp trước khi chạy) | Số bảng, số join, số filter, số `LIKE`/`IN`/`OR`/`BETWEEN`; số node và độ sâu của cây plan; có dùng cây bushy hay không; số Hash/Merge/Nested Loop join; số Seq/Index/Bitmap scan; **cost** và số dòng ước lượng |
| **Động** (đo khi chạy) | Planning time, execution time, **end-to-end time** (metric chính, §8.2.1); **speedup = t_cũ / t_mới**; % thời gian tiết kiệm; **q-error** = max(ước lượng/thực tế, thực tế/ước lượng); số câu timeout; tổng thời gian workload |

## 4.5. Chạy plan và lưu log

**Các plan được so sánh.** Mỗi câu được chạy với 6 hint set kiểu Bao (§2):
- `default`: **plan cũ**, do PostgreSQL tự chọn.
- `no_nestloop`, `no_hashjoin`, `no_mergejoin`, `no_seqscan`, `no_indexscan`: mỗi hint set tắt một loại toán tử bằng lệnh `SET enable_... = off`, buộc PostgreSQL chọn một plan khác.

Tổng cộng khoảng 113 × 6 × 3 ≈ 2.000 lần chạy. **Plan tối ưu** của một câu là hint set có end-to-end time nhỏ nhất.

Một số hint set như `no_indexscan` hay `no_hashjoin` có thể làm câu chạy rất lâu. Để giới hạn thời gian, nếu một (câu, hint set) bị timeout ở lần chạy đầu thì không chạy lại 2 lần sau và ghi luôn thời gian bằng timeout.

**Định dạng log.** Mỗi lần chạy được ghi thành một dòng JSON, kèm toàn bộ plan lấy từ `EXPLAIN (ANALYZE, FORMAT JSON)`:

```json
{"query_id": "1a", "db": "imdbload", "pg_version": "12.5", "hint_set": "default",     "run": 2, "planning_ms": ..., "execution_ms": ..., "timeout": false, "plan": {...}}
{"query_id": "1a", "db": "imdbload", "pg_version": "12.5", "hint_set": "no_nestloop", "run": 2, "planning_ms": ..., "execution_ms": ..., "timeout": false, "plan": {...}}
{"query_id": "1b", "db": "imdbload", "pg_version": "12.5", "hint_set": "default",     "run": 2, "planning_ms": ..., "execution_ms": ..., "timeout": false, "plan": {...}}
```

- `query_id`: phần số (1) là truy vấn gốc, dùng khi chia dữ liệu theo Base Query.
- `run = 2`: lần chạy thứ 3 (hot cache), lần được dùng để phân tích.
- `plan`: cây plan đầy đủ của lần chạy đó.

**Trình bày plan thực thi.** Từ trường `plan`, nhóm trích ra loại toán tử, bảng, thứ tự join, cost, số dòng ước lượng và số dòng thực tế, rồi đặt plan cũ cạnh plan mới. Ví dụ minh họa cách trình bày với câu 1a (chưa phải kết quả đo):

```
Plan cũ (default)                         Plan mới (no_nestloop)
Aggregate                                 Aggregate
└─ Nested Loop                            └─ Hash Join
   ├─ Nested Loop                            ├─ Seq Scan on title t
   │  ├─ Seq Scan on info_type it            └─ Hash Join
   │  └─ Index Scan on movie_info_idx           ├─ Hash Join (mi_idx ⋈ it)
   └─ Index Scan on title t ...                 └─ Hash Join (mc ⋈ ct)
```

Hai plan được so sánh theo 4 điểm: thứ tự join, loại join/scan, hình dạng cây (left-deep hay bushy), và khoảng cách giữa hai cây (tree edit distance).

**Bảng plan tối ưu cho toàn bộ dataset.** Mỗi câu một dòng, gồm các cột: `query_id`, plan cũ, plan tối ưu, thời gian cũ, thời gian mới, speedup. Từ bảng này nhóm báo cáo:
- Số câu có plan tốt hơn plan mặc định.
- Phân phối speedup: trung vị, lớn nhất, số câu nhanh hơn 2×.
- Tổng thời gian workload khi luôn dùng plan cũ so với khi luôn dùng plan tối ưu.

## 4.6. Phân loại plan bằng data mining

**Bài toán.**
- **Đầu vào:** metric tĩnh của câu SQL và của plan mặc định. Đây là thông tin có sẵn trước khi thử các plan khác, nên không rò rỉ nhãn.
- **Nhãn:** plan tối ưu. Một hint set chỉ được tính là tốt hơn `default` nếu nhanh hơn ít nhất 5%.
- **Đầu ra:** mỗi câu được gán một trong 6 plan. Ví dụ với 500 câu, mô hình gán cho mỗi câu một plan.

**Hai mức bài toán:**
- **Phân loại 2 lớp (bài toán chính):** câu này *có nên đổi plan hay không*. Bài toán này dễ học hơn khi ít dữ liệu, và vẫn đếm được số câu đúng.
- **Phân loại 6 lớp (mở rộng):** câu này *nên dùng plan nào trong 6 hint set*. Với 113 câu JOB, phần lớn câu có nhãn `default`, nên bài toán 6 lớp dễ bị lệch lớp. Nhóm chỉ làm bài toán này khi đã có thêm dữ liệu CEB.

**Chia dữ liệu theo đúng 3 kiểu của bài báo (§7.2):**
- **Leave One Out** (dễ).
- **Random** (KFold, trung bình).
- **Base Query** (GroupKFold theo truy vấn gốc, khó nhất, không rò rỉ giữa các biến thể).

**Mô hình:** Decision Tree, Random Forest, Gradient Boosting, kNN, Naive Bayes, SVM, Logistic Regression. So sánh với hai mốc:
- **"Luôn dùng PostgreSQL":** không bao giờ đổi plan.
- **"Oracle":** luôn chọn đúng plan tối ưu.

**Đánh giá:**
- **Số câu dự đoán đúng / tổng số câu** (ví dụ: 80/113), kèm **ma trận nhầm lẫn**.
- Accuracy và macro-F1.
- **Tổng thời gian workload** khi dùng plan do mô hình chọn, so với hai mốc ở trên.
- **Số câu bị chậm đi trên 10%.**
- Kiểm định McNemar.

Nhóm ưu tiên các chỉ số theo thời gian, vì bài báo chỉ ra accuracy không phù hợp cho tối ưu truy vấn (§5.1).

**Giải thích bằng thuật toán:**

| Thuật toán | Mục đích |
|---|---|
| K-means + PCA | Tìm các nhóm câu truy vấn thường được lợi khi đổi plan |
| Apriori | Tìm luật `{đặc điểm câu/plan} → plan tốt nhất` (support, confidence, lift) |
| Permutation importance | Xác định metric quyết định việc nên đổi plan, ví dụ q-error |
| Cây quyết định độ sâu 3 | Đưa ra quy tắc ngắn gọn, dễ đọc |
| Tree edit distance + Spearman | Kiểm tra plan mới khác plan cũ càng nhiều thì có càng nhanh không |

## 4.7. Thêm benchmark

JOB chỉ có 113 câu, quá ít cho bài toán phân loại. Nhóm đề xuất thêm **CEB-IMDb**:
- Chạy trên cùng CSDL IMDB nên không cần nạp dữ liệu mới.
- Nhóm lấy mẫu khoảng **500 câu**, chia đều theo template, rồi lặp lại mục 4.5–4.6. Để vừa thời gian, timeout giảm từ 3 phút xuống **30 giây**. Nếu còn thời gian, nhóm sẽ tăng lên 1.000 câu.
- Phương án dự phòng: DSB.
- Không dùng STACK vì dữ liệu quá lớn.

## 4.8. Lộ trình thực hiện

| Ưu tiên | Công việc | Thời gian ước tính |
|---|---|---|
| ✅ Đã xong | Dựng môi trường, nạp IMDB, phân tích log tác giả | — |
| 1 | Baseline PostgreSQL; ablation số lần chạy *k* | Khoảng 1 giờ |
| 2 | Chạy 6 plan trên JOB; lập bảng plan tối ưu | Vài giờ đến 1 ngày |
| 3 | Phân loại 2 lớp và data mining trên JOB | Vài phút (script có sẵn) |
| 4 | Bao trên BQ-1; ablation bitmap/tid scan và GEQO | Vài giờ |
| 5 | CEB-IMDb khoảng 500 câu; phân loại 2 lớp và 6 lớp | 1–2 ngày |
| Mở rộng | Bao trên RND-1, LOO-1; ablation covariate shift và cây bushy; CEB 1.000 câu | Nếu còn thời gian |

Các bước 1–3 đã đủ để trả lời ba mục tiêu ở mục 4.1. Các bước sau giúp kết quả chắc chắn hơn.

## 4.9. Kết quả sơ bộ trên log của tác giả

Nhóm phân tích lại log của tác giả trên 9 split JOB (chỉ tập test), so sánh từng câu với PostgreSQL:

| Phương pháp | Thắng | Hòa | Thua | Speedup tổng |
|---|---|---|---|---|
| HybridQO | 34 | 82 | 117 | 1,00× |
| Bao | 9 | 34 | 190 | 0,83× |
| Balsa | 16 | 4 | 213 | 0,28× |
| Neo | 21 | 12 | 200 | 0,16× |
| LEON | 0 | 0 | 233 | 0,001× |

**Nhận xét:**
- **Thứ hạng khớp với bài báo** (§8.2.1).
- **HybridQO ngang PostgreSQL về tổng thời gian nhưng thua ở khoảng một nửa số câu.** Điều này cho thấy mỗi LQO chỉ có lợi ở một số câu nhất định.
- Đây chính là động lực cho phần phân loại plan: **nếu dự đoán trước được câu nào nên đổi plan, có thể giữ phần lợi và tránh phần thiệt.**

## 4.10. Kết luận và hạn chế

Nhóm đã dựng xong môi trường PostgreSQL 12.5 trên ARM64 với cấu hình bám sát bài báo. Phân tích lại log của tác giả xác nhận không có LQO nào vượt PostgreSQL một cách ổn định. Bước tiếp theo là chạy 6 plan cho mỗi câu, đo mức tăng tốc, rồi dùng phân loại và data mining để dự đoán plan phù hợp cho từng câu trên JOB và CEB-IMDb.

**Hạn chế:**
- Chỉ chạy lại PostgreSQL và Bao; các LQO khác dùng log của tác giả.
- Chưa làm ablation covariate shift (§8.3) và cây bushy (§8.7).
- CEB dùng timeout ngắn hơn JOB (30 giây so với 3 phút), nên những câu rất chậm bị cắt ở 30 giây.
- Mốc tối ưu chỉ là plan tốt nhất trong 6 hint set, chưa phải plan tối ưu toàn cục.
