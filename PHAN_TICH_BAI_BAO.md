# Phân tích bài báo: "Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective"

| | |
|---|---|
| **Tác giả** | Claude Lehmann, Pavel Sulimov (đồng tác giả chính), Kurt Stockinger, ZHAW, Thụy Sĩ |
| **Nơi đăng** | PVLDB, Vol. 17, No. 7, tr. 1565–1577, 2024 · doi:10.14778/3654621.3654625 |
| **Mã nguồn** | [github.com/edualc/lqo_ml_perspective](https://github.com/edualc/lqo_ml_perspective) (có huy hiệu ACM *Artifacts Available*) |
| **Loại bài** | Bài đánh giá thực nghiệm và phương pháp luận (experiment & analysis), **không** đề xuất LQO mới |
| **File gốc** | `2.6 Is Your Learned Query Optimizer Behaving As You Expect 2023.pdf` |

> Hướng dẫn tái lập thực nghiệm và phần data mining mở rộng nằm ở [README.md](README.md).
> File này chỉ phân tích **nội dung bài báo**.

---

## Mục lục

1. [Tóm tắt một đoạn](#1-tóm-tắt-một-đoạn)
2. [Bối cảnh: tối ưu truy vấn cổ điển và LQO](#2-bối-cảnh-tối-ưu-truy-vấn-cổ-điển-và-lqo)
3. [Câu hỏi nghiên cứu và đóng góp](#3-câu-hỏi-nghiên-cứu-và-đóng-góp)
4. [Các LQO được khảo sát](#4-các-lqo-được-khảo-sát)
5. [Phân tích theo 4 giai đoạn của pipeline ML](#5-phân-tích-theo-4-giai-đoạn-của-pipeline-ml)
6. [Framework benchmark end-to-end](#6-framework-benchmark-end-to-end)
7. [Thực nghiệm chính và kết quả](#7-thực-nghiệm-chính-và-kết-quả)
8. [Các nghiên cứu ablation](#8-các-nghiên-cứu-ablation)
9. [Đánh giá phản biện](#9-đánh-giá-phản-biện)
10. [Liên hệ với phần tái lập trong repo này](#10-liên-hệ-với-phần-tái-lập-trong-repo-này)
11. [Thuật ngữ](#11-thuật-ngữ)
12. [Câu hỏi thảo luận](#12-câu-hỏi-thảo-luận)

---

## 1. Tóm tắt một đoạn

Trong vài năm gần đây đã xuất hiện nhiều **bộ tối ưu truy vấn học máy** (Learned Query Optimizer – LQO) như Neo,
Bao, Balsa, LEON, HybridQO. Mỗi bài lại tự chọn cách sinh dữ liệu train, cách chia train/test, cấu hình
PostgreSQL và cách đo thời gian riêng, nên kết quả **không so sánh được với nhau**. Bài báo nhìn LQO như một
**pipeline học máy** gồm 4 giai đoạn: sinh dữ liệu, mã hóa truy vấn/plan, huấn luyện, đánh giá. Ở mỗi giai đoạn,
tác giả chỉ ra các vi phạm nguyên tắc ML và đưa ra khuyến nghị. Họ đề xuất một **framework benchmark end-to-end**
thống nhất: cùng cấu hình DBMS, 3 kiểu chia dữ liệu với độ khó tăng dần, đo hot cache ở lần chạy thứ 3, và tính
cả thời gian suy luận. Đánh giá lại 5 LQO trên JOB và STACK cho kết quả chính:
**PostgreSQL nhìn chung vẫn tốt nhất, theo sau là HybridQO, Bao, Neo, Balsa và cuối cùng là LEON.**
Ngoài ra, thời gian train dài hơn **không** cho kết quả tốt hơn.

---

## 2. Bối cảnh: tối ưu truy vấn cổ điển và LQO

**Bài toán.** Với truy vấn join *n* bảng, số plan logic trong trường hợp xấu nhất là O(n!). Bài toán chọn thứ tự
join là NP-khó, nên DBMS phải dùng heuristic. Ví dụ, PostgreSQL bỏ quy hoạch động khi có từ 12 bảng trở lên và
chuyển sang thuật toán di truyền GEQO.

**Bộ tối ưu cổ điển** (Hình 1, nửa trên) gồm: plan logic → plan vật lý → tìm kiếm (quy hoạch động hoặc GEQO)
dựa trên **cost model** và **ước lượng cardinality**.

**LQO** (Hình 1, nửa dưới) thay một phần hoặc toàn bộ quy trình trên bằng mô hình học, thường là học tăng cường
(RL) hoặc hồi quy với Tree-CNN/Tree-LSTM. Theo góc nhìn ML, pipeline gồm:

```
(1) Sinh dữ liệu train  →  (2) Mã hóa query & plan  →  (3) Huấn luyện  →  (4) Đánh giá
          └────────────────── Framework benchmark end-to-end (1), (3), (4) ──────────────────┘
```

Lập luận chính của bài: cộng đồng tập trung vào **mô hình** ở giai đoạn 3, trong khi các giai đoạn còn lại có
nhiều lỗi phương pháp luận làm sai lệch kết luận.

---

## 3. Câu hỏi nghiên cứu và đóng góp

**Câu hỏi:** Khi đánh giá công bằng và end-to-end, các LQO hiện nay có thật sự tốt hơn PostgreSQL không?

| # | Đóng góp | Mục trong bài |
|---|---|---|
| 1 | Chỉ ra hạn chế khi sinh dữ liệu train: thiếu tính bất biến, dynamic optimization, cold/hot cache | §3 |
| 2 | Chẩn đoán lỗi bất biến (invariance) trong cách mã hóa và đưa khuyến nghị | §4 |
| 3 | Đề xuất cải tiến để huấn luyện ổn định hơn: chống overfitting, đổi biến mục tiêu | §5 |
| 4 | Thống nhất cách chia dữ liệu (3 kiểu chia), cảnh báo về covariate shift | §6 |
| 5 | **Framework benchmark end-to-end** có thể tái lập | §7 |
| 6 | **Đóng góp chính:** đánh giá thực nghiệm quy mô lớn 5 LQO trên JOB và STACK, kèm 5 ablation | §8 |

---

## 4. Các LQO được khảo sát

| LQO | Ý tưởng chính | Đầu ra mô hình | Có trong thực nghiệm? |
|---|---|---|---|
| **Neo** (2019) | LQO end-to-end đầu tiên. Mạng nơ-ron ước lượng latency của plan, rồi tìm kiếm tham lam từ dưới lên | Plan đầy đủ | ✅ (dùng bản cài lại trong Balsa) |
| **RTOS** | GNN + RL. Coi join graph là chuỗi các phép join 2 bảng, bỏ qua scan | Plan | ❌ |
| **Bao** (2021) | Không tự sinh plan mà chọn **hint set** (bật/tắt loại join, scan) cho optimizer của PostgreSQL. Chạy như extension | Hint set | ✅ |
| **Balsa** (2022) | Kiến trúc giống Neo, nhưng pre-train bằng cost của DBMS, dùng timeout, lấy mẫu từ mô hình mới nhất | Plan | ✅ |
| **Lero** | Learning-to-rank. Sinh nhiều plan ứng viên bằng cách thay đổi cardinality nội bộ, rồi so sánh từng cặp | Plan | ❌ |
| **LEON** (2023) | Learning-to-rank. Vét cạn plan bằng quy hoạch động, dùng Bayesian NN để ước lượng độ bất định | Plan | ✅ |
| **LOGER** | Pipeline giống RTOS, thêm loại join, dùng ε-beam search | Hint | ❌ |
| **HybridQO** (2022) | Lấy plan ứng viên từ DBMS qua hint (MCTS + UCB trên cost), rồi mạng nơ-ron dự đoán latency và độ bất định để chọn plan | Plan | ✅ |

Lý do loại RTOS, Lero, LOGER: không có mã nguồn, cần tắt song song hóa, hoặc tốn quá nhiều công để lấy được
đầu ra EXPLAIN.

**Bảng 1 của bài** so sánh thành phần mã hóa. Hai điểm đáng chú ý:
- **Bao và Lero không mã hóa truy vấn**, chỉ mã hóa plan. Bao còn không biết bảng nào nằm ở node nào, chỉ dùng
  cardinality và cost.
- Chỉ **Bao** và **HybridQO** dùng thêm truy vấn ngoài benchmark để sinh dữ liệu. Chỉ **RTOS** dùng
  cross-validation; Bao kiểm tra theo kiểu "time series".

---

## 5. Phân tích theo 4 giai đoạn của pipeline ML

### 5.1 Sinh dữ liệu train (§3)

| Vấn đề | Giải thích | Khuyến nghị |
|---|---|---|
| **Chọn dataset** | Dùng JOB (IMDB) và STACK (StackExchange) vì dữ liệu thực, có tương quan. Không dùng TPC (giả định dữ liệu phân phối đều) và STATS-CEB (thiết kế cho ước lượng cardinality) | — |
| **Giảm không gian plan** | Một số bài tắt nested loop join, tắt bitmap/tid scan hoặc chỉ dùng cây left-deep. Cách này có thể cải thiện vài câu nhưng làm giảm khả năng tổng quát | Không tắt tùy tiện; xem ablation §8.4, §8.5, §8.7 |
| **Dynamic optimization** | `pg_hint_plan` ép plan, nhưng khi chạy DBMS vẫn có thể thay đổi plan. Vì vậy plan trong EXPLAIN có thể khác plan thực sự đã chạy, và **mô hình học trên dữ liệu sai** | Dùng **RL trực tiếp** coi DBMS là hộp đen |
| **Cold và hot cache** | Chạy lại cùng truy vấn thì nhanh hơn. Nếu trộn trạng thái cache thì nhãn *y* không nhất quán | **Luôn đo ở hot cache**, chạy lặp đến khi latency hội tụ |

### 5.2 Mã hóa truy vấn và plan (§4)

- **Nguyên tắc bất biến (principle of invariance):** cùng một đầu vào phải cho cùng một đầu ra. Nếu mã hóa filter
  chỉ bằng selectivity hoặc cardinality, **nhiều filter khác nhau sẽ cho cùng một vector**, trong khi latency
  thật lại khác nhau. Kết quả là ánh xạ (D, y) trở thành 1-nhiều, và mô hình học trên dữ liệu mâu thuẫn.
  - *Khuyến nghị:* dùng **embedding** cho thuộc tính văn bản (như Neo dùng word2vec), vector hóa filter một cách
    tường minh (như RTOS).
- **Tính biểu đạt:** cần cả ngữ cảnh toàn cục (truy vấn) lẫn ngữ cảnh cục bộ (plan). Bao và Lero thiếu phần mã
  hóa truy vấn nên dễ hội tụ về cực trị cục bộ.
  - *Khuyến nghị:* **mã hóa cả query lẫn plan.**

### 5.3 Huấn luyện (§5)

- **Overfitting:** RL ít bị overfitting theo nghĩa cổ điển nhưng có thể kẹt ở chính sách dưới tối ưu.
  Trong các LQO, chỉ RTOS dùng CV. Balsa dừng sớm trên tập validation không cố định. LEON dừng sớm theo
  *accuracy*. Bao kiểm tra kiểu time series.
  - *Khuyến nghị:* vẫn **tinh chỉnh siêu tham số** cho RL. Accuracy là tiêu chí dừng sớm kém, vì ta không biết
    trước plan tối ưu. **Tập holdout phải cố định** để kết quả so sánh được.
- **Đổi biến mục tiêu giữa chừng:** Balsa, LEON, RTOS, Lero pre-train trên *cost* rồi chuyển sang *latency*.
  Hai đại lượng này có thang đo và phương sai khác hẳn nhau, nên phần lớn những gì học được lúc pre-train bị mất.
  - *Khuyến nghị:* dùng **learning-to-rank** (thứ hạng không phụ thuộc thang đo), hoặc **xâu chuỗi nhiều mô hình**
    như HybridQO (mỗi mô hình phục vụ một biến mục tiêu).

### 5.4 Đánh giá (§6)

- **Chọn tập test có vấn đề.**
  - *Ext-JOB* (Neo) thêm GROUP BY/ORDER BY. Merge join được lợi từ ORDER BY nên phép so sánh bị lệch.
  - *JOB-Slow* (Balsa) lấy 19 câu chậm nhất làm tập test. Tuy nhiên, cả 19 câu đều có ≤ 11 join, trong đó
    11 câu có ≤ 6 join, tức là nằm trong vùng PostgreSQL vẫn dùng quy hoạch động vét cạn.
  - Chia theo **số join** như [43] là không hợp lý: Hình 2 cho thấy số join gần như không giải thích được thời gian
    chạy (**R² = −0.11**).
- **Covariate shift:** dữ liệu trong CSDL thay đổi sau khi đã train. DBMS tự cập nhật thống kê, còn LQO thì phải
  train lại. *Khuyến nghị:* mọi LQO mới nên có một thí nghiệm covariate shift đơn giản (xem §8.3).

---

## 6. Framework benchmark end-to-end

Framework yêu cầu công bố đủ: (a) dữ liệu CSDL, (b) toàn bộ mã nguồn LQO, (c) phiên bản ngôn ngữ và thư viện,
(d) cấu hình DBMS, (e) danh sách truy vấn và cách gán vào train/test.

### 6.1 Cấu hình PostgreSQL thống nhất (Bảng 2)

| Tham số | Mặc định | Framework của bài |
|---|---|---|
| `geqo` | on | off; chỉ bật cho Bao và khi PostgreSQL tự điều khiển toàn bộ việc thực thi (baseline) |
| `work_mem` | 4 MB | 4 GB |
| `shared_buffers` | 128 MB | 32 GB |
| `temp_buffers` | 8 MB | 32 GB |
| `effective_cache_size` | 4 GB | 32 GB |
| `max_worker_processes` | 2 | 8 |
| `enable_bitmapscan`, `enable_tidscan` | on | **on** (Balsa và LEON tắt mà không giải thích) |
| `autovacuum` | on | off; `ANALYZE` chạy **một lần** sau khi nạp dữ liệu |

Bảng 2 còn cho thấy mỗi bài trước dùng một cấu hình khác nhau: RAM từ 15 GB (Bao) đến 512 GB (Lero), và LOGER, Lero
tắt song song hóa. Riêng việc tăng `effective_cache_size` từ 4 GB lên 32 GB đã giảm thời gian lập plan của một
số câu ngoại lai **từ khoảng 3 s xuống dưới 100 ms**.

### 6.2 Ba kiểu chia dữ liệu (Hình 3)

JOB có 113 truy vấn, sinh từ **33 truy vấn gốc**. Mỗi truy vấn gốc có 2–6 biến thể (1a, 1b, ...), giống nhau về
bảng và join, chỉ khác filter.

| Kiểu chia | Cách làm | Độ khó | Rò rỉ thông tin |
|---|---|---|---|
| **Leave One Out (LOO)** | Mỗi truy vấn gốc đưa đúng 1 biến thể vào tập test | Dễ | Cao: cùng họ truy vấn đã có trong tập train |
| **Random (RND)** | Chia ngẫu nhiên 80/20 | Trung bình | Một phần |
| **Base Query (BQ)** | Mọi biến thể của một truy vấn gốc nằm cùng phía, 80/20 | **Khó nhất** | Không: mô hình phải tổng quát sang cấu trúc join chưa thấy |

Mỗi kiểu chia có 3 lần chia, tổng cộng **9 split cho JOB**. Ý tưởng này tương đương `GroupKFold` trong ML: nếu
không nhóm theo truy vấn gốc thì tập test bị rò rỉ thông tin.

### 6.3 Đo thời gian

- Chạy mỗi truy vấn **3 lần** và lấy **lần thứ 3** (hot cache). Lý do ở §8.6.
- **Thời gian end-to-end = suy luận + lập plan + thực thi.** Đây là chỉ số chính. Không tính độ trễ mạng.
- **Thời gian train end-to-end:** tính từ lúc bắt đầu đến khi kết thúc, gồm cả thời gian truy vấn DBMS lấy dữ
  liệu, train, đánh giá giữa chừng và tiền/hậu xử lý.

---

## 7. Thực nghiệm chính và kết quả

**Thiết lập:** PostgreSQL 12.5, Docker, GPU Tesla T4, 64 GB RAM, 16 CPU. JOB gồm 113 câu. STACK lấy mẫu xuống
**14 truy vấn gốc × 8 biến thể** (bỏ template 9 và 10 theo Balsa, vì `pg_hint_plan` không xử lý được view và
subquery), để có lượng dữ liệu tương đương JOB.

**Các điều chỉnh so với bài gốc của từng phương pháp:** Bao ban đầu được train trên 2.500 truy vấn tự sinh, ở đây
chỉ được train trên tập train của split. LEON bị giới hạn thời gian train bằng 2 lần Balsa, tức **khoảng 120 giờ**.

### 7.1 Kết quả tổng quát

> **Xếp hạng: PostgreSQL > HybridQO > Bao > Neo > Balsa > LEON**
>
> Tuy vậy, PostgreSQL không thắng mọi split với ý nghĩa thống kê. HybridQO và Bao tương đương PostgreSQL ở nhiều
> split.

### 7.2 JOB theo từng kiểu chia (Hình 4)

| Kiểu chia | Quan sát chính |
|---|---|
| **LOO (dễ)** | PostgreSQL, Bao và HybridQO đều thực thi tập test trong khoảng **30 s**. Bao lập plan lâu hơn **8,5 s**, nên chậm hơn **25%** tính end-to-end. HybridQO tìm được plan nhanh hơn 2,5 s và chỉ tốn 1,4 s suy luận, nhờ đó **vượt PostgreSQL có ý nghĩa thống kê ở split thứ 3**. LEON thực thi 58 s nhưng suy luận mất **khoảng 9,6 giờ**. Neo 93 s, Balsa 134 s, tức chậm hơn PostgreSQL 286% và 411% |
| **RND (trung bình)** | Bao thực thi 25 s so với 28 s của PostgreSQL, nhưng chênh lệch không có ý nghĩa thống kê, và khi cộng thời gian suy luận thì Bao lại chậm hơn. HybridQO ngang PostgreSQL, vượt có ý nghĩa ở split 3 (24 s). Neo và Balsa nhanh hơn 2–3 lần so với khi ở LOO, và tương đương PostgreSQL ở 2/3 split. LEON gặp timeout (26b, 32b), suy luận trung bình 3,8 giờ |
| **BQ (khó)** | Bao chỉ tương đương PostgreSQL ở 1/3 split, HybridQO ở cả 3/3 split. Neo và Balsa gặp khó ở BQ-1 (Neo có 3 câu test timeout, Balsa có 15 câu timeout trên cả tập train lẫn tập test) |

Điều đáng chú ý: Neo và Balsa làm tốt hơn ở RND so với LOO, trái với kỳ vọng "LOO dễ nhất". Tác giả giải thích
rằng kết quả phụ thuộc mạnh vào việc **câu nào rơi vào tập test** (kết quả hướng dữ liệu chứ không hướng mô hình).

### 7.3 STACK (Hình 5)

Kết quả trên STACK về cơ bản khẳng định lại kết quả JOB. Khác biệt:
- Thời gian suy luận của LEON thấp hơn khoảng một bậc độ lớn, vì truy vấn STACK có ít join hơn.
- Neo, Balsa và LEON có nhiều câu timeout.
- Bao **không theo kịp** PostgreSQL vì SQL phức tạp hơn, dẫn đến suy luận lâu.
- HybridQO vượt PostgreSQL ở LOO, ngang ở BQ, nhưng có câu timeout ở RND, cho thấy thiếu ổn định.

### 7.4 Thời gian train (Hình 6)

| Phương pháp | JOB | STACK |
|---|---|---|
| PostgreSQL | 0 | 0 |
| Bao | ~2 giờ | ~2 giờ |
| HybridQO | ~20 giờ | 12–14 giờ |
| Neo | 20–40 giờ | 120–140 giờ |
| Balsa | 40–85 giờ | 170–290 giờ |
| LEON | 110–130 giờ | 120–140 giờ |

**Phát hiện ngược trực giác:** phương pháp train càng lâu thì kết quả **càng kém**. Nguyên nhân chính là số plan
phải xét: trên JOB, Neo chạy 4.000–8.000 plan, Balsa chạy 19.000–21.000 plan. LEON không thực thi hết các plan mà
hỏi PostgreSQL ước lượng cost cho hàng chục nghìn plan con. Riêng truy vấn 29a (17 bảng) mất **khoảng 6,5 giờ chỉ để
dự đoán plan**, và file cache của LEON lên tới 1,7 GB.

**Bài học:** thời gian suy luận và thời gian train quyết định thứ hạng end-to-end. Nếu chỉ báo cáo thời gian thực
thi, như nhiều bài trước đã làm, thì bức tranh bị tô hồng.

---

## 8. Các nghiên cứu ablation

| Mục | Thí nghiệm | Kết quả | Hàm ý |
|---|---|---|---|
| **8.3 Covariate shift** | Tạo IMDB-50% bằng cách lấy mẫu Bernoulli 50% bảng `title` và xóa CASCADE (giảm khoảng 50% dữ liệu liên quan), rồi chạy `ANALYZE`. So sánh Bao-Full với Bao-50 trên BQ-1 | 16b timeout ở 1/4 mô hình Bao-50 và chậm hơn 19 s ở 3 mô hình còn lại. 31c chậm hơn **24 lần** (8,4 s so với 350 ms), 17a chậm hơn 4,5 lần. Một số câu nhanh hơn: 7c (1,9 lần), 26c (1,6 lần), 10c (1,3 lần) | **Cập nhật thống kê của DBMS là không đủ** để mô hình đã train theo kịp dữ liệu mới. Nên ưu tiên phương pháp có thể train lại liên tục |
| **8.4 Bitmap/Tid scan** | Tắt hai loại scan này rồi chạy lại 113 câu JOB | 28 câu lệch hơn 250 ms, trong đó 24 câu có ý nghĩa thống kê. Nhanh hơn: 28a (5,5 lần), 7c (2,0 lần), 30a (1,8 lần). Chậm hơn: 30c (2,4 lần), 28b (1,9 lần), 15c (1,5 lần) | Cấu hình này ảnh hưởng lớn (template 7, 8, 28, 30), nên Balsa và LEON không thể tắt mà không giải thích. Cùng một họ truy vấn (28a/28b) có thể vừa lợi vừa hại |
| **8.5 GEQO** | Tắt GEQO | 5 câu khác biệt có ý nghĩa. 30a nhanh hơn 1,6 lần. Chậm hơn: 24b (9,9 lần, 28 ms lên 272 ms), 26c (2,2 lần), 28a (2,1 lần), 28b (1,7 lần) | Tác động nhỏ hơn bitmap/tid scan nhưng vẫn đáng kể. Khi LQO chỉ hỗ trợ PostgreSQL (qua hint), PostgreSQL nên được chạy ở công suất đầy đủ |
| **8.6 Số lần chạy *k*** | Chạy mỗi câu JOB 50 lần liên tiếp | Lần 2 nhanh hơn lần 1 trung bình **14,6%**, lần 3 nhanh hơn lần 2 thêm **1,03%**, sau đó không còn xu hướng (Hình 7) | Phải chạy ít nhất 2 lần; **lấy lần thứ 3** là cân bằng giữa chi phí và độ ổn định. So với *k* = 5 của [43], cách này nhanh hơn 40% và ổn định hơn so với lấy trung bình 3 lần (vì lần 1 luôn là ngoại lai) |
| **8.7 Bushy và left-deep** | Vét cạn mọi plan của các câu JOB có ≤ 5 join, dùng cardinality ước lượng của DBMS và cho phép mọi loại join | Trung bình thì bushy tương đương left-deep (Mann-Whitney hai phía, p = 0,285). Tuy nhiên ở **đuôi trái** (các plan nhanh nhất), bushy tốt hơn rõ rệt (p = 0,015) | Bỏ cây bushy như RTOS, LOGER, HybridQO làm **giảm mạnh khả năng tìm được plan tốt nhất** |

---

## 9. Đánh giá phản biện

### 9.1 Điểm mạnh

1. **Góc nhìn mới:** đặt LQO vào khung pipeline ML chuẩn, nhờ đó chỉ ra lỗi ở các giai đoạn ít ai để ý, như tính
   bất biến của mã hóa và việc đổi biến mục tiêu giữa chừng.
2. **Đánh giá end-to-end:** tính cả thời gian suy luận và train. Đây là điểm các bài trước thường bỏ qua và nó làm
   thay đổi hoàn toàn thứ hạng.
3. **Ba kiểu chia có độ khó tăng dần**, đặc biệt là Base Query split, giúp kiểm tra tổng quát hóa thật sự và tránh
   rò rỉ thông tin giữa các biến thể của cùng một template.
4. **Thống kê nghiêm túc:** 3 lần chia cho mỗi kiểu, dùng kiểm định ý nghĩa, và dùng Mann-Whitney vì phân phối
   thời gian không chuẩn.
5. **Tái lập được:** mã nguồn, cấu hình, danh sách split và log đều công khai.
6. **Ablation có giá trị thực tế:** chứng minh các lựa chọn cấu hình "nhỏ" (bitmap/tid scan, GEQO, *k*, cây bushy)
   ảnh hưởng đáng kể đến kết luận.

### 9.2 Hạn chế và câu hỏi mở

| Hạn chế | Ảnh hưởng có thể có |
|---|---|
| **Tập test nhỏ:** mỗi split JOB chỉ có 19–33 câu test | Kiểm định thống kê có lực yếu; một vài câu ngoại lai (16b, 29a) có thể chi phối kết quả |
| **Chỉ dùng một hệ thống:** PostgreSQL 12.5 với một cấu hình phần cứng | Chưa rõ kết luận có đúng với PostgreSQL mới hơn hoặc DBMS khác không |
| **Bao bị bất lợi:** không được dùng 2.500 truy vấn sinh thêm như trong bài gốc | Có thể đánh giá thấp Bao. Mặt khác, đây là điều kiện công bằng chung cho mọi phương pháp |
| **LEON bị giới hạn khoảng 120 giờ train** | Có thể đánh giá thấp LEON, dù tác giả lập luận rằng thời gian suy luận mới là vấn đề chính |
| **Neo dùng bản cài lại trong Balsa** | Không phải mã gốc, dù tác giả Neo đã xác nhận bản này dùng được để benchmark |
| **Không có tinh chỉnh siêu tham số cho từng phương pháp**, dù chính bài khuyến nghị điều này ở §5.1 | Các LQO có thể chưa ở trạng thái tốt nhất |
| **GEQO bật với PostgreSQL và Bao nhưng tắt với các LQO tự sinh plan** | Hợp lý về kỹ thuật, nhưng các phương pháp không chạy trên cùng một bộ công cụ của DBMS |
| **Thiếu các LQO mới hơn** như Lero, LOGER, RTOS | Kết luận "LQO chưa vượt PostgreSQL" chưa bao phủ hướng learning-to-rank mạnh nhất |
| **Chỉ đo hot cache** | Hợp lý cho tính nhất quán nhưng không phản ánh workload thực có cold cache |
| **Các khuyến nghị ở §3–§5 chưa được kiểm chứng bằng thực nghiệm** (ví dụ: embedding có thật sự sửa được lỗi bất biến không?) | Phần lớn là khuyến nghị lý thuyết |
| Ablation covariate shift chỉ làm với Bao trên một split | Khó tổng quát cho các LQO khác |

### 9.3 Đánh giá chung

Đây là một bài **"sanity check" cho cả lĩnh vực**: không đưa ra phương pháp mới, nhưng làm rõ rằng lợi thế mà các
LQO báo cáo phần lớn đến từ cách đánh giá. Bao gồm việc chọn split, bỏ qua thời gian suy luận và cấu hình
PostgreSQL không tối ưu. Thông điệp chính: **muốn LQO cạnh tranh được, cần thay đổi về phương pháp luận chứ không
chỉ thay mô hình mạnh hơn.** Hướng "LQO hỗ trợ optimizer có sẵn" (Bao, HybridQO) tỏ ra thực tế hơn hướng
"LQO thay thế hoàn toàn" (Neo, Balsa, LEON).

---

## 10. Liên hệ với phần tái lập trong repo này

Chạy `scripts/c1_win_loss.py` trên log của tác giả (`experiment_logs/20240103__combined.csv`, mọi split JOB, tập
test, ngưỡng hòa ±10%) cho kết quả theo **từng câu truy vấn**:

| Phương pháp | Thắng | Hòa | Thua | Speedup workload |
|---|---|---|---|---|
| HybridQO | 34 | 82 | 117 | 1.00× |
| Bao | 9 | 34 | 190 | 0.83× |
| Balsa | 16 | 4 | 213 | 0.28× |
| Neo | 21 | 12 | 200 | 0.16× |
| LEON | 0 | 0 | 233 | 0.001× |

Kết quả này **khớp với thứ hạng trong bài**. Phân tích từng câu còn cho thấy thêm một điều bài báo chưa nói rõ:
ngay cả HybridQO, phương pháp tốt nhất, cũng **thua ở khoảng một nửa số câu**, và chỉ bù lại về tổng thời gian nhờ
một vài câu được cải thiện lớn. Chi tiết theo split và p-value nằm ở `analysis/output/c1_authors_summary.csv`.

Các hướng mở rộng đã được lên kế hoạch trong [README.md](README.md) bám sát những hạn chế ở §9.2:
- **C2** dùng đúng 3 kiểu chia LOO/RND/BQ của bài cho bài toán phân loại "nên dùng hint set nào".
- **C3** (cây quyết định, luật kết hợp, q-error) giúp giải thích *khi nào* một plan mới tốt hơn, điều bài báo chưa
  phân tích.
- **CEB-IMDb** (khoảng 1.000 câu) khắc phục vấn đề tập test nhỏ.

---

## 11. Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| **LQO** | Learned Query Optimizer: bộ tối ưu truy vấn dùng học máy |
| **JOB** | Join Order Benchmark: 113 truy vấn trên CSDL IMDB |
| **STACK** | Benchmark trên dữ liệu StackExchange: 6.191 truy vấn từ 16 truy vấn gốc |
| **Hint set** | Tập lệnh bật/tắt loại join/scan, truyền cho PostgreSQL qua `pg_hint_plan` |
| **GEQO** | Genetic Query Optimizer: PostgreSQL dùng khi có ≥ 12 bảng (`geqo_threshold`) |
| **Cardinality / q-error** | Số dòng ước lượng; q-error = max(ước lượng/thực tế, thực tế/ước lượng) |
| **Left-deep và bushy** | Cây join mà nhánh phải luôn là bảng đơn, so với cây mà hai nhánh đều có thể là phép join con |
| **Principle of invariance** | Cùng đầu vào thì phải cùng đầu ra; bị vi phạm khi nhiều truy vấn khác nhau có cùng vector mã hóa |
| **Covariate shift** | Phân phối dữ liệu đầu vào thay đổi sau khi train |
| **Dynamic optimization** | DBMS thay đổi plan trong khi thực thi, nên plan thực tế khác plan trong EXPLAIN |
| **Hot/cold cache** | Dữ liệu đã nằm trong bộ đệm, so với phải đọc từ đĩa |
| **Learning-to-rank (LTR)** | Học thứ hạng tương đối giữa các plan thay vì giá trị tuyệt đối |
| **Tree-CNN / Tree-LSTM** | Mạng nơ-ron xử lý plan dạng cây |

---

## 12. Câu hỏi thảo luận

1. Base Query split là khó nhất, nhưng trong thực tế, workload có thường gặp truy vấn với cấu trúc join hoàn
   toàn mới không? Kiểu chia nào phản ánh đúng môi trường triển khai?
2. Tại sao HybridQO, một phương pháp lai, lại ổn định hơn các LQO thay thế hoàn toàn optimizer? Điều này nói gì về
   việc nên thiết kế LQO thế nào?
3. Nếu bỏ thời gian suy luận (ví dụ cache plan cho truy vấn lặp lại), thứ hạng sẽ thay đổi ra sao? Kịch bản nào
   cho phép điều đó?
4. Có thể thiết kế mã hóa truy vấn sao cho vừa bất biến vừa chống chịu được covariate shift không?
5. Khi PostgreSQL thắng về tổng thời gian, có nhóm truy vấn nào mà LQO **luôn** thắng không? Có thể dự đoán trước
   các nhóm đó để chỉ dùng LQO khi có lợi không? (Đây là động lực cho phần C2/C3 trong repo.)
