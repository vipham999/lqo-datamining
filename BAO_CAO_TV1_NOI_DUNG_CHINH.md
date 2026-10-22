# PHẦN 1. MỞ ĐẦU, CƠ SỞ LÝ THUYẾT VÀ PHÂN TÍCH PIPELINE ML CỦA LQO

> **Phụ trách:** Thành viên 1 – Ngọc
> **Bài báo:** Lehmann, Sulimov, Stockinger. *Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective.* PVLDB 17(7): 1565–1577, 2024.
> **Quy ước:** `(§x.y)` là mục trong bài báo; `[n]` là số tài liệu trong danh mục REFERENCES của bài báo (xem cuối phần); **[Nhóm]** đánh dấu nhận xét do nhóm bổ sung, không phải nội dung bài báo.

---

## 1. MỞ ĐẦU

**Bối cảnh.** Với một câu SQL, DBMS phải chọn một trong rất nhiều kế hoạch thực thi tương đương về kết quả nhưng khác xa nhau về thời gian chạy. Khi đồ thị join là clique gồm *n* bảng, số kế hoạch logic trong trường hợp xấu nhất là **O(n!)**, và bài toán được xếp vào lớp **NP-khó** [37]. Vì vậy DBMS không thể vét cạn với truy vấn lớn mà phải dùng heuristic. Ví dụ, PostgreSQL bỏ phương pháp vét cạn khi truy vấn có từ 12 bảng trở lên (§1, chú thích 1).

**Sự ra đời của LQO.** Nhờ tiến bộ của học sâu, và vì bài toán tối ưu truy vấn (QOP) dễ phát biểu lại thành bài toán ML, nhiều **bộ tối ưu truy vấn học máy (LQO)** đã ra đời: Neo [23], Bao [22], Balsa [39], Lero [44], LEON [4], LOGER [3], HybridQO [41], RTOS [42] (Abstract, §2).

**Vấn đề.** Mỗi LQO tự chọn cách sinh dữ liệu, cách chia train/test và cấu hình DBMS riêng, đồng thời vi phạm các nguyên tắc ML cơ bản [30]. Do đó kết quả của các LQO **không so sánh công bằng được** với nhau (§1). Ví dụ, RAM dùng trong thực nghiệm dao động từ 15 GB (Bao) đến 512 GB (Lero) (Bảng 2).

**Câu hỏi nghiên cứu.** Khi được đánh giá công bằng và end-to-end, LQO có thật sự tốt hơn PostgreSQL không?

**Cách tiếp cận và đóng góp.** Bài báo xem LQO như một **pipeline ML gồm 4 giai đoạn** và phân tích lỗi ở từng giai đoạn (§1, Hình 1):

| Giai đoạn | Đóng góp | Mục |
|---|---|---|
| (1) Sinh dữ liệu huấn luyện | Chỉ ra các hạn chế khi sinh dữ liệu | §3 |
| (2) Mã hóa truy vấn/kế hoạch | Chẩn đoán lỗi bất biến | §4 |
| (3) Huấn luyện | Đề xuất cách huấn luyện ổn định hơn | §5 |
| (4) Đánh giá | Thống nhất cách chia dữ liệu | §6, §7.2 |
| Đóng góp thêm | Framework benchmark end-to-end và đánh giá 5 LQO | §7, §8 |

**Kết luận chính:** *"current LQOs do not systematically perform better than PostgreSQL"* (§1). Thứ hạng chung là PostgreSQL > HybridQO > Bao > Neo > Balsa > LEON (§8.2.1).

---

## 2. CƠ SỞ LÝ THUYẾT

### 2.1 Bộ tối ưu truyền thống (Hình 1, nửa trên)

SQL → **kế hoạch logic** (thứ tự join) → **kế hoạch vật lý** (thuật toán join: hash, merge, nested loop; cách scan) → **tìm kiếm** bằng quy hoạch động, hoặc thuật toán di truyền GEQO khi có từ 12 bảng [34], [28]. Việc tìm kiếm dựa trên **cost model**, và cost model dựa trên **ước lượng cardinality** (§1, §7.1).

### 2.2 Bộ tối ưu học máy – LQO (Hình 1, nửa dưới)

LQO thay khối biểu diễn và ra quyết định của bộ tối ưu truyền thống bằng **mã hóa truy vấn/kế hoạch** và **mô hình dự đoán**. Các LQO chính (§2, Bảng 1):

| LQO | Ý tưởng | Mô hình | Đầu ra |
|---|---|---|---|
| Neo [23] | LQO end-to-end đầu tiên; mạng nơ-ron dự đoán latency, tìm kiếm tham lam | Hồi quy, Tree-CNN | Plan |
| Bao [22] | Chọn **hint set** (bật/tắt loại join/scan) cho PostgreSQL | Hồi quy, Tree-CNN | Hint set |
| Balsa [39] | Giống Neo, nhưng pre-train bằng cost, dùng timeout | Hồi quy, Tree-CNN | Plan |
| LEON [4], Lero [44] | Learning-to-rank (LTR) | LTR, Tree-CNN | Plan |
| HybridQO [41] | Lấy ứng viên từ DBMS (MCTS trên cost), rồi chọn theo latency dự đoán | Hồi quy, Tree-LSTM | Plan |
| RTOS [42], LOGER [3] | RL + Tree-LSTM; LOGER thêm loại join | Hồi quy, Tree-LSTM | Plan / Hint |

### 2.3 Khái niệm ML cốt lõi

- **Dữ liệu (D, y)** (§3.3): D là vector đặc trưng (với RL là bộ (s, a, s′)); y là **latency**, **cost** hoặc **ranking**.
- **Nguyên tắc bất biến** [17]: *cùng đầu vào thì phải cùng đầu ra* (§1, chú thích 3). Nói cách khác, ánh xạ D → y phải là 1-1.
- **Benchmark** (§3.1): **JOB** [18] gồm 113 truy vấn từ 33 truy vấn gốc, mỗi gốc có 2–6 biến thể chỉ khác nhau ở filter. **STACK** [22] gồm 6.191 truy vấn từ 16 truy vấn gốc. Bài không dùng TPC [35] vì TPC giả định dữ liệu phân phối đều.

---

## 3. PHÂN TÍCH 4 LỖ HỔNG TRONG PIPELINE ML

### 3.1 Lỗ hổng (1): Sinh dữ liệu huấn luyện (§3)

Benchmark QOP chỉ cung cấp câu SQL, nên LQO phải **tự truy vấn DBMS** để lấy đặc trưng và nhãn. Vì vậy dữ liệu dễ mất nhất quán (§1, §3).

| Vấn đề | Giải thích | Khuyến nghị |
|---|---|---|
| **Thu hẹp không gian kế hoạch** (§3.2) | Một số bài tắt nested loop join [18], tắt bitmap/tid scan (Balsa, LEON) hoặc bỏ cây bushy. Cách này giúp vài truy vấn nhưng **giảm khả năng tổng quát**. Ví dụ: tắt nested loop join làm 16b nhanh hơn nhưng 24b chậm đi [22]. Thí nghiệm của bài: tắt bitmap/tid scan làm 28a nhanh hơn 5,5× nhưng 28b chậm hơn 1,9× (§8.4); bỏ cây bushy làm mất các kế hoạch nhanh nhất (p = 0,015, §8.7) | Không tắt toán tử tùy tiện |
| **Dynamic optimization** (§3.3.1) | `pg_hint_plan` [27] ép kế hoạch, nhưng DBMS có thể đổi kế hoạch khi chạy [1]. Kế hoạch được mã hóa khác kế hoạch thực sự chạy, nên mô hình **học trên dữ liệu sai** | Dùng direct RL, coi DBMS là hộp đen [8] |
| **Cold và hot cache** (§3.3.2) | Cùng một truy vấn chạy lại thì nhanh hơn. Nếu trộn trạng thái cache thì **cùng D có nhiều y** | Ép hot cache: chạy 3 lần, lấy lần 3 (§7.3). Lần 2 nhanh hơn lần 1 14,6%, sau lần 3 hết xu hướng (§8.6) |

### 3.2 Lỗ hổng (2): Mã hóa truy vấn/kế hoạch (§4)

LQO là phương pháp hướng truy vấn [12, 40], nên mã hóa phải vừa **bền vững** vừa **giàu biểu đạt** (§4).

- **Vi phạm bất biến** (§4.1)
  - Bao và Lero **không mã hóa truy vấn**, chỉ mã hóa kế hoạch. Bao chỉ dùng cardinality và cost, không biết bảng nào nằm ở node nào.
  - Balsa, LEON, HybridQO mã hóa filter **chỉ bằng một giá trị cardinality**.
  - Hậu quả: các filter khác nhau có thể cho cùng cardinality, nên có **cùng vector D** nhưng latency khác nhau. Ánh xạ (D, y) trở thành **1-nhiều**.
  - *Khuyến nghị:* dùng **embedding** (như word2vec của Neo [23]) và **vector hóa filter tường minh** (như RTOS [42]).
- **Thiếu tính biểu đạt** (§4.2)
  - Cần cả ngữ cảnh **toàn cục** (truy vấn) lẫn **cục bộ** (kế hoạch) [14].
  - Bao và Lero thiếu phần truy vấn nên dễ **hội tụ về cực trị địa phương** [9].
  - *Khuyến nghị:* mã hóa **cả query lẫn plan**.

### 3.3 Lỗ hổng (3): Huấn luyện mô hình (§5)

- **Validation sai cách** (§5.1)
  - Chỉ RTOS dùng CV, nhưng CV không giúp chọn mô hình cuối.
  - Balsa dừng sớm trên tập validation **không cố định**.
  - LEON dừng sớm theo **accuracy**, một chỉ số kém vì ta không biết trước kế hoạch tối ưu.
  - Bao kiểm tra theo kiểu "time series".
  - *Khuyến nghị:* vẫn tinh chỉnh siêu tham số, kể cả với RL; dùng **tập holdout cố định** [7].
- **Đổi biến mục tiêu giữa chừng** (§5.2)
  - RTOS, Balsa, Lero, LEON pre-train một mô hình bằng **cost** rồi chuyển sang **latency**.
  - Hai đại lượng khác nhau về thang đo và phương sai [2], nên phần lớn kiến thức học lúc pre-train bị mất.
  - *Khuyến nghị:* dùng **learning-to-rank** [20], hoặc **xâu chuỗi nhiều mô hình** như HybridQO.
- **Bằng chứng** (§8.2.2): train lâu hơn **không** cho kết quả tốt hơn. LEON train 110–130 giờ và Balsa 40–85 giờ nhưng xếp hai vị trí cuối, trong khi Bao chỉ train khoảng 2 giờ.

### 3.4 Lỗ hổng (4): Đánh giá và rò rỉ dữ liệu (§6, §7.2)

Khi cách chia train/test không cố định, kết quả phụ thuộc vào **dữ liệu** nhiều hơn vào **mô hình** (data-centric thay vì model-centric) (§1).

| Vấn đề | Giải thích | Khuyến nghị |
|---|---|---|
| **Tập test thiên lệch** (§6.1) | **Ext-JOB** [23] thêm ORDER BY, làm lợi cho merge join [13]. **JOB-Slow** [39] chỉ gồm truy vấn ≤ 11 join, đúng vùng PostgreSQL còn vét cạn được. **Chia theo số join** [43] vô nghĩa vì số join không giải thích được thời gian chạy (R² = −0,11, Hình 2) | Thiết kế các split kiểm tra khả năng tổng quát hóa và dữ liệu ngoài phân phối |
| **Rò rỉ dữ liệu** (§7.2) | Các biến thể của cùng một truy vấn gốc có cấu trúc join tối ưu tương tự nhau. Nếu 1a nằm ở tập train còn 1b ở tập test thì thông tin bị rò sang tập test | 3 kiểu chia (Hình 3): **LOO** (dễ), **RND** (trung bình), **BQ** (khó, mọi biến thể của một truy vấn gốc nằm cùng một phía) |
| **Bỏ qua thời gian suy luận** (§8.2.1) | LEON thực thi chỉ 58 s nhưng suy luận mất khoảng 9,6 giờ | Đo end-to-end: suy luận + lập kế hoạch + thực thi |
| **Covariate shift** (§6.2) | Dữ liệu thay đổi sau khi train. Với Bao huấn luyện trên IMDB-50%, truy vấn 31c chậm hơn 24× (§8.3) | Mọi LQO mới nên có thí nghiệm covariate shift |

**[Nhóm]** Kiểu chia BQ tương đương GroupKFold trong ML, với nhóm là truy vấn gốc.

---

## 4. TIỂU KẾT

| Giai đoạn | Lỗ hổng chính | Khuyến nghị cốt lõi |
|---|---|---|
| (1) Sinh dữ liệu | Thu hẹp không gian kế hoạch, dynamic optimization, trộn trạng thái cache | Không tắt toán tử tùy tiện; luôn đo ở hot cache |
| (2) Mã hóa | Mã hóa bằng một giá trị cardinality; thiếu query encoding | Dùng embedding; mã hóa cả query lẫn plan |
| (3) Huấn luyện | Validation không cố định; chuyển từ cost sang latency | Tập holdout cố định; LTR hoặc xâu chuỗi mô hình |
| (4) Đánh giá | Tập test thiên lệch, rò rỉ dữ liệu, bỏ qua suy luận và covariate shift | Chia LOO/RND/BQ; đo thời gian end-to-end |

**Thông điệp:** lợi thế mà các LQO báo cáo phần lớn đến từ **cách xây dựng pipeline và cách đánh giá**, chứ không phải từ mô hình. Muốn LQO cạnh tranh được với PostgreSQL thì cần sửa phương pháp luận ở cả 4 giai đoạn (§1, §9).

---

## TÀI LIỆU THAM KHẢO (số theo bài báo, tr. 1577)

- [1] Avnur & Hellerstein (2000). *Eddies: Continuously Adaptive Query Processing.* SIGMOD Rec.
- [2] Brownlee (2020). *Data preparation for machine learning.*
- [3] Chen et al. (2023). *LOGER.* PVLDB 16(7).
- [4] Chen et al. (2023). *LEON.* PVLDB 16(9).
- [7] Goodfellow, Bengio, Courville (2016). *Deep Learning.* MIT Press.
- [8] Guan et al. (2021). *Direct and indirect reinforcement learning.* arXiv.
- [9] Guyon & Elisseeff (2006). *An Introduction to Feature Extraction.* Springer.
- [12] Hilprecht et al. (2020). *DeepDB.* PVLDB 13(7).
- [13] Kacimi & Neumann (2009). *System R (R\*) Optimizer.* Springer.
- [14] Kipf & Welling (2017). *Semi-Supervised Classification with Graph Convolutional Networks.* ICLR.
- [17] La Salle (1976). *The stability of dynamical systems.* SIAM.
- [18] Leis et al. (2015). *How good are query optimizers, really?* PVLDB 9(3).
- [20] Liu (2009). *Learning to Rank for Information Retrieval.*
- [22] Marcus et al. (2021). *Bao: Making learned query optimization practical.* SIGMOD.
- [23] Marcus et al. (2019). *Neo: A Learned Query Optimizer.* PVLDB 12(11).
- [27] *pg_hint_plan Documentation* (2012).
- [28] Petković (2011). *Dynamic Programming Algorithm vs. Genetic Algorithm.*
- [30] Russell & Norvig (2010). *Artificial Intelligence: A Modern Approach.*
- [34] PostgreSQL (2023). *Genetic Query Optimizer (GEQO).*
- [35] TPC (2023). *TPC Benchmarks Overview.*
- [37] Wang & Chen (1996). *On the complexity of distributed query optimization.* IEEE TKDE 8(4).
- [39] Yang et al. (2022). *Balsa.* SIGMOD.
- [40] Yang et al. (2020). *NeuroCard.* PVLDB 14(1).
- [41] Yu et al. (2022). *HybridQO.* PVLDB 15(13).
- [42] Yu et al. (2020). *RTOS: Reinforcement learning with tree-LSTM for join order selection.* ICDE.
- [43] Zhang et al. (2023). *Simple Adaptive Query Processing vs. Learned Query Optimizers.* PVLDB 16(9).
- [44] Zhu et al. (2023). *Lero: A Learning-to-Rank Query Optimizer.* arXiv.
