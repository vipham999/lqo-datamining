# PHẦN 1. MỞ ĐẦU, CƠ SỞ LÝ THUYẾT VÀ PHÂN TÍCH ML PIPELINE CỦA LQO

> **Người thực hiện:** Ngọc (Thành viên 1)
> **Bài báo phân tích:** C. Lehmann, P. Sulimov, K. Stockinger. *Is Your Learned Query Optimizer Behaving As You
> Expect? A Machine Learning Perspective.* PVLDB 17(7): 1565–1577, 2024.
> Trong phần này, "[§x]" chỉ mục tương ứng trong bài báo gốc, "[Hình x]" và "[Bảng x]" là hình và bảng của bài báo.

---

## 1. MỞ ĐẦU

### 1.1. Đặt vấn đề

SQL là ngôn ngữ **khai báo**: người dùng chỉ mô tả *cần lấy dữ liệu gì*, còn việc *lấy bằng cách nào* do hệ quản
trị cơ sở dữ liệu (DBMS) quyết định. Thành phần đảm nhận việc này là **bộ tối ưu truy vấn** (query optimizer).
Với cùng một câu truy vấn, có thể có hàng nghìn đến hàng triệu **kế hoạch thực thi** (query plan) cho cùng một kết
quả, nhưng thời gian chạy của chúng có thể chênh nhau nhiều bậc độ lớn. Chọn đúng plan vì vậy là yếu tố quyết định
hiệu năng của toàn hệ thống.

Bài toán này rất khó. Với truy vấn join *n* bảng, số plan logic trong trường hợp xấu nhất là O(n!), và bài toán
chọn thứ tự join được chứng minh là NP-khó [§1]. Các DBMS truyền thống như PostgreSQL giải quyết bằng ba thành phần:
quy hoạch động (dynamic programming) để duyệt không gian plan, **mô hình chi phí** (cost model) để so sánh các plan,
và **ước lượng cardinality** (số dòng trung gian) làm đầu vào cho mô hình chi phí. Khi số bảng lớn, PostgreSQL
chuyển sang thuật toán di truyền GEQO. Điểm yếu đã biết của cách làm này là ước lượng cardinality thường sai
nhiều bậc độ lớn, và sai số đó dẫn đến những plan rất tệ [18].

Khoảng năm 2018 trở lại đây, sự phát triển của học sâu dẫn tới một hướng nghiên cứu mới là **bộ tối ưu truy vấn
học máy** (Learned Query Optimizer – LQO). Ý tưởng là thay thế hoặc hỗ trợ quy hoạch động và mô hình chi phí bằng
các mô hình học từ kinh nghiệm thực thi, như học tăng cường hay mạng nơ-ron trên cây. Nhiều LQO như Neo, Bao, Balsa,
LEON, HybridQO đều báo cáo kết quả vượt PostgreSQL.

Tuy nhiên, các tác giả của bài báo nhận thấy một vấn đề: **mỗi LQO tự chọn cách đánh giá riêng.** Mỗi bài dùng
cách sinh dữ liệu khác nhau, cách chia train/test khác nhau, cấu hình PostgreSQL khác nhau (RAM từ 15 GB đến
512 GB [Bảng 2]), và có bài chỉ báo cáo thời gian thực thi mà bỏ qua thời gian suy luận của mô hình. Như bài báo
nhận định, *"sự vi phạm các nguyên tắc lý thuyết của ML ở mỗi giai đoạn và việc thiếu một framework thống nhất,
có thể tái lập khiến hiện nay không thể so sánh công bằng các kết quả của LQO"* [§1]. Câu hỏi đặt ra là:

> **Nếu đánh giá công bằng và end-to-end, các LQO hiện nay có thực sự tốt hơn bộ tối ưu truyền thống không?**

### 1.2. Mục tiêu của phần này

Phần báo cáo này tập trung vào **nửa lý thuyết** của bài báo, cụ thể:

1. Trình bày bối cảnh và các kiến thức nền về tối ưu truy vấn truyền thống và LQO.
2. Mô hình hóa LQO thành một **pipeline học máy** gồm 4 giai đoạn.
3. Phân tích **4 lỗ hổng kỹ thuật** mà bài báo chỉ ra ở 4 giai đoạn đó. Với mỗi lỗ hổng, báo cáo nêu bản chất,
   lý do đây là vi phạm nguyên tắc ML, hệ quả, và khuyến nghị khắc phục.

Kết quả thực nghiệm và các nghiên cứu ablation, dùng để kiểm chứng những phân tích này, được trình bày ở các phần
sau của báo cáo.

### 1.3. Phạm vi

- **Hệ quản trị:** PostgreSQL, hệ được mọi LQO trong bài sử dụng.
- **Benchmark:** Join Order Benchmark (JOB) trên dữ liệu IMDB và STACK trên dữ liệu StackExchange.
- **LQO được phân tích:** Neo, RTOS, Bao, Balsa, Lero, LEON, LOGER, HybridQO [Bảng 1]. Trong đó 5 phương pháp
  được đánh giá thực nghiệm: Neo, Bao, Balsa, LEON, HybridQO.
- **Chỉ số:** thời gian thực thi end-to-end của workload, gồm thời gian suy luận, lập plan và thực thi.

### 1.4. Đóng góp của bài báo

| # | Đóng góp | Vị trí |
|---|---|---|
| 1 | Chỉ ra các hạn chế khi sinh dữ liệu train cho LQO | §3 |
| 2 | Chẩn đoán vấn đề mất tính bất biến trong mã hóa query/plan, đưa khuyến nghị | §4 |
| 3 | Đề xuất cải tiến để huấn luyện LQO ổn định hơn | §5 |
| 4 | Thống nhất cách chia dữ liệu, đề xuất quy trình kiểm tra nhiều mức tổng quát hóa | §6 |
| 5 | Xây dựng **framework benchmark end-to-end** có thể tái lập | §7 |
| 6 | **Đánh giá thực nghiệm** quy mô lớn, cho thấy LQO hiện tại *không vượt PostgreSQL một cách có hệ thống* | §8 |

Phần 1 của báo cáo bao phủ các đóng góp 1–4.

---

## 2. CƠ SỞ LÝ THUYẾT

### 2.1. Quy trình xử lý một câu truy vấn SQL

Một câu truy vấn SQL đi qua các bước sau trong DBMS:

```
SQL ──► Phân tích cú pháp ──► Viết lại truy vấn ──► TỐI ƯU HÓA ──► Thực thi ──► Kết quả
        (parser)              (rewriter)            (optimizer)     (executor)
```

Bộ tối ưu nhận cây truy vấn logic và trả về một **plan vật lý**: một cây trong đó mỗi node lá là một phép **quét
bảng** (scan) và mỗi node trong là một phép **join** hoặc toán tử khác (sort, aggregate, ...). Plan vật lý xác
định ba điều:

| Quyết định | Các lựa chọn trong PostgreSQL |
|---|---|
| **Thứ tự join** | Bảng nào join với bảng nào trước |
| **Thuật toán join** | Nested Loop Join, Hash Join, Merge Join |
| **Phương thức quét** | Sequential Scan, Index Scan, Index Only Scan, Bitmap Scan, Tid Scan |

### 2.2. Không gian tìm kiếm và độ phức tạp

Cây join có hai dạng chính:

- **Left-deep:** nhánh phải của mọi phép join luôn là một bảng đơn. Với *n* bảng có *n!* cây left-deep.
- **Bushy:** cả hai nhánh đều có thể là kết quả của một phép join con. Số cây bushy là (2(n−1))!/(n−1)!, lớn hơn
  rất nhiều.

```
       Left-deep                  Bushy
           ⋈                        ⋈
          / \                     /   \
         ⋈   D                   ⋈     ⋈
        / \                     / \   / \
       ⋈   C                   A   B C   D
      / \
     A   B
```

Nhân thêm 3 thuật toán join cho mỗi node và nhiều phương thức quét cho mỗi bảng, không gian plan tăng bùng nổ. Vì
bài toán là NP-khó, không thể vét cạn khi *n* lớn. Một số LQO (RTOS, LOGER, HybridQO) chỉ xét cây left-deep để thu
hẹp không gian. Ablation §8.7 của bài báo cho thấy lựa chọn này có cái giá của nó.

### 2.3. Bộ tối ưu truyền thống dựa trên chi phí

Bộ tối ưu của PostgreSQL theo kiến trúc System R (Selinger và cộng sự, 1979), gồm ba thành phần [Hình 1, nửa trên]:

1. **Thuật toán tìm kiếm.** Quy hoạch động xây plan từ dưới lên, giữ plan rẻ nhất cho mỗi tập con bảng. Khi số
   bảng trong FROM từ `geqo_threshold` (mặc định 12) trở lên, PostgreSQL bỏ quy hoạch động và dùng **GEQO**
   (Genetic Query Optimizer), một thuật toán di truyền cho lời giải xấp xỉ.
2. **Mô hình chi phí.** Ước lượng "chi phí" của plan bằng một công thức tuyến tính theo số trang I/O và số dòng CPU
   phải xử lý. Chi phí là đơn vị trừu tượng, không phải mili giây.
3. **Ước lượng cardinality.** Ước lượng số dòng đầu ra của mỗi toán tử dựa trên thống kê (histogram, giá trị phổ
   biến, số giá trị phân biệt) do lệnh `ANALYZE` thu thập. Để đơn giản, bộ ước lượng giả định các cột **độc lập**
   và dữ liệu **phân phối đều**.

Sai số của ước lượng cardinality thường đo bằng **q-error**:

$$
\text{q-error} = \max\left(\frac{\hat{c}}{c}, \frac{c}{\hat{c}}\right) \ge 1
$$

trong đó $\hat{c}$ là cardinality ước lượng và $c$ là cardinality thực. Trên dữ liệu thực có tương quan như IMDB,
giả định độc lập bị vi phạm nặng, sai số tích lũy theo số phép join, và mô hình chi phí chọn sai plan. Đây chính là
**động lực ra đời của LQO**.

### 2.4. Bộ tối ưu truy vấn học máy (LQO)

LQO thay thế một phần hoặc toàn bộ quy trình trên bằng mô hình học máy [Hình 1, nửa dưới]. Có hai hướng chính:

| Hướng | Cách làm | Đại diện |
|---|---|---|
| **Thay thế optimizer** | Mô hình tự xây plan đầy đủ (thứ tự join, thuật toán join, phương thức quét), rồi ép DBMS thực thi | Neo, RTOS, Balsa, LEON |
| **Hỗ trợ optimizer** | Mô hình chỉ đưa "gợi ý" (hint): bật/tắt loại join hoặc scan, hoặc chọn một plan trong các ứng viên do DBMS sinh | Bao, LOGER, HybridQO, Lero |

Trong cả hai hướng, LQO giao tiếp với PostgreSQL qua extension **`pg_hint_plan`**. Extension này cho phép chèn
chú thích như `/*+ Leading((a b) c) HashJoin(a b) */` vào câu SQL để ép plan.

**Hình thức hóa dưới góc nhìn ML [§3.3].** Dữ liệu cho LQO có dạng cặp **(D, y)**:

- **D** là vector đặc trưng. Với học có giám sát, D là các biến độc lập X mô tả truy vấn và plan. Với học tăng
  cường, D là bộ (s, a, s′) gồm trạng thái (plan con hiện tại), hành động (thêm một phép join) và trạng thái kế tiếp.
- **y** là biến mục tiêu: **latency** (thời gian chạy thật), **cost** (chi phí ước lượng của DBMS) hoặc **thứ
  hạng** giữa các plan (learning-to-rank).

**Kiến trúc mô hình.** Vì plan là cây, các LQO dùng mạng nơ-ron trên cây: **Tree-CNN** (tích chập trên cây; Neo,
Bao, Balsa, Lero, LEON) hoặc **Tree-LSTM** (RTOS, LOGER, HybridQO) [Bảng 1].

Tóm tắt các LQO trong bài báo:

| LQO | Ý tưởng | Học |
|---|---|---|
| Neo | Mạng nơ-ron ước lượng latency của plan con; tìm kiếm tham lam từ dưới lên | Hồi quy + RL |
| RTOS | GNN cho join graph; chỉ xét join, bỏ qua scan | RL |
| Bao | Chọn 1 trong nhiều *hint set* cho PostgreSQL; chạy như extension | Hồi quy (Thompson sampling) |
| Balsa | Như Neo, nhưng pre-train bằng cost của DBMS, dùng timeout | Hồi quy + RL |
| Lero | Sinh plan ứng viên bằng cách thay đổi cardinality nội bộ; so sánh từng cặp | Learning-to-rank |
| LEON | Vét cạn plan bằng quy hoạch động; Bayesian NN để ước lượng độ bất định | Learning-to-rank |
| LOGER | Như RTOS, thêm loại join; ε-beam search | RL |
| HybridQO | MCTS sinh plan ứng viên qua hint; mạng nơ-ron dự đoán latency và độ bất định để chọn plan | Hồi quy |

### 2.5. Benchmark

- **JOB (Join Order Benchmark)** [18]: 113 truy vấn trên CSDL IMDB (21 bảng), sinh từ **33 truy vấn gốc**
  (template). Mỗi template có 2–6 biến thể, ký hiệu 1a, 1b, 1c, .... Các biến thể có cùng bảng và điều kiện join,
  chỉ khác điều kiện lọc (ví dụ `production_year < 2000` và `production_year = 2023`). Mỗi truy vấn có từ 4 đến
  17 bảng.
- **STACK** [22]: 6.191 truy vấn trên dữ liệu StackExchange, từ 16 template. Bài báo lấy mẫu 14 template × 8 biến
  thể để có lượng dữ liệu tương đương JOB.

Cả hai đều dùng **dữ liệu thực có tương quan**, nên khó hơn các benchmark sinh dữ liệu đều như TPC.

### 2.6. Các khái niệm ML liên quan

| Khái niệm | Định nghĩa | Vai trò trong phân tích |
|---|---|---|
| **Train / validation / test** | Dữ liệu dùng để học, để chọn mô hình và siêu tham số, và để đo khả năng tổng quát | Lỗ hổng 3 và 4 |
| **Overfitting** | Mô hình tốt trên tập train nhưng kém trên dữ liệu mới | Lỗ hổng 3 |
| **Rò rỉ dữ liệu** (data leakage) | Thông tin của tập test lọt vào quá trình huấn luyện, làm kết quả đánh giá cao hơn thực tế | Lỗ hổng 4 |
| **Tổng quát hóa** (generalization) | Khả năng làm tốt trên dữ liệu chưa thấy | Lỗ hổng 4 |
| **Covariate shift** | Phân phối đầu vào lúc dùng khác lúc train (ví dụ dữ liệu trong CSDL thay đổi) | Lỗ hổng 4 |
| **Nguyên tắc bất biến** (principle of invariance) [17] | *"Với cùng một đầu vào, hệ thống sinh dữ liệu phải trả về cùng một đầu ra"* [§1, chú thích 3] | Lỗ hổng 1 và 2 |

---

## 3. PHÂN TÍCH LÝ THUYẾT ML PIPELINE CỦA LQO

### 3.1. LQO dưới góc nhìn pipeline học máy

Bài báo đề xuất nhìn mọi LQO như một pipeline ML gồm 4 giai đoạn [Hình 1]:

```
 ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │ (1) Sinh dữ liệu │──►│ (2) Mã hóa       │──►│ (3) Huấn luyện   │──►│ (4) Đánh giá     │
 │     huấn luyện   │   │     Query & Plan │   │     mô hình      │   │     LQO          │
 └──────────────────┘   └──────────────────┘   └──────────────────┘   └──────────────────┘
   Lỗ hổng 1              Lỗ hổng 2              Lỗ hổng 3              Lỗ hổng 4
   Dữ liệu không          Mã hóa mất tính        Overfitting, đổi       Chia tập tùy ý,
   bất biến               bất biến               mục tiêu giữa chừng    rò rỉ dữ liệu
```

Lập luận trung tâm: cộng đồng nghiên cứu tập trung vào **giai đoạn 3** (thiết kế mô hình ngày càng phức tạp). Các
giai đoạn 1, 2 và 4, vốn được coi là "chuẩn mực" trong ML thông thường, lại bị làm tùy tiện. Khác với bài toán ML
thông thường có sẵn bộ dữ liệu chuẩn (như ImageNet), **benchmark tối ưu truy vấn chỉ cung cấp các câu SQL**. Mỗi
nhóm nghiên cứu phải tự chạy chúng trên CSDL để tạo dữ liệu (D, y), và chính khâu tự làm này sinh ra sai lệch.

Các mục dưới đây phân tích từng lỗ hổng theo cùng một cấu trúc: **hiện trạng → vì sao là vi phạm nguyên tắc ML →
hệ quả → khuyến nghị của bài báo.**

---

### 3.2. Lỗ hổng 1: Sinh dữ liệu huấn luyện [§3]

#### a) Benchmark không cung cấp dữ liệu huấn luyện

**Hiện trạng.** JOB và STACK chỉ cho câu SQL. Các đặc trưng mà LQO thực sự cần, như cardinality, cost, latency,
plan đã chạy, đều phải lấy bằng cách truy vấn CSDL. Kết quả lại phụ thuộc vào phần cứng, cấu hình DBMS và trạng
thái bộ nhớ đệm.

**Vì sao là vấn đề.** Trong ML chuẩn, mọi phương pháp được so sánh trên **cùng một bộ dữ liệu**. Ở đây, mỗi LQO
thực chất được train và test trên một bộ dữ liệu khác nhau, nên so sánh kết quả giữa các bài không còn ý nghĩa.
Bài báo nêu hai rủi ro: (1) dữ liệu sinh dưới các ràng buộc vô lý sẽ thu hẹp miền dữ liệu và giảm khả năng tổng
quát; (2) cùng một đầu vào có thể cho ra đầu ra khác nhau [§3].

#### b) Thu hẹp không gian plan một cách tùy tiện [§3.2]

**Hiện trạng.** Để bài toán dễ hơn, một số tác giả tắt bớt lựa chọn: tắt nested loop join, tắt bitmap scan và tid
scan (Balsa, LEON), tắt GEQO, hoặc chỉ dùng cây left-deep (RTOS, LOGER, HybridQO).

**Vì sao là vấn đề.** Đây là **lời giải phụ thuộc dữ liệu**. Một ràng buộc có thể giúp một số truy vấn nhưng làm
hại truy vấn khác. Ví dụ, tắt nested loop join làm truy vấn 16b của JOB nhanh hơn nhưng làm 24b chậm đi [22]. Việc
thu hẹp không gian vì vậy *có thể* làm tăng khả năng chỉ tìm được plan dưới tối ưu.

**Hệ quả.** LQO được so sánh với một PostgreSQL đã bị "cắt bớt công cụ", nên lợi thế của LQO bị phóng đại. Các phần
sau của báo cáo (ablation §8.4, §8.5, §8.7) cho thấy tắt bitmap/tid scan làm 24 câu JOB thay đổi có ý nghĩa thống
kê, còn bỏ cây bushy làm giảm khả năng tìm được plan nhanh nhất.

#### c) Dynamic optimization: plan được ép chưa chắc là plan được chạy [§3.3.1]

**Hiện trạng.** Mọi LQO được đánh giá đều dùng `pg_hint_plan` để ép PostgreSQL thực thi plan do mô hình chọn, rồi
lấy plan và cardinality từ `EXPLAIN` để mã hóa.

**Vì sao là vấn đề.** DBMS có thể điều chỉnh plan **trong lúc thực thi** (dynamic optimization) [1]. Vì vậy plan
trong `EXPLAIN` có thể khác plan thực sự đã chạy. Cặp (D, y) khi đó **không khớp nhau**: đặc trưng D mô tả plan A,
nhưng latency y lại là của plan A′. Mô hình học trên **nhãn sai**, và cardinality lấy từ `EXPLAIN` cũng không chính
xác.

**Khuyến nghị.** Dùng **học tăng cường trực tiếp** (direct RL): coi DBMS là hộp đen, tối ưu trực tiếp hàm mục tiêu
mà không cần mô hình hóa xác suất chuyển trạng thái hay giải phương trình Bellman [8].

#### d) Cache nóng và cache lạnh [§3.3.2]

**Hiện trạng.** Lần chạy đầu của một truy vấn đọc dữ liệu từ đĩa (cold cache). Các lần sau đọc từ bộ đệm
(hot cache) nên nhanh hơn. Nếu không kiểm soát trạng thái cache, cùng một truy vấn với cùng một plan có thể có
latency khác nhau.

**Vì sao là vấn đề.** Điều này **vi phạm trực tiếp nguyên tắc bất biến**: cùng đầu vào D nhưng biến mục tiêu y khác
nhau, tức là nhãn có nhiễu hệ thống. Hơn nữa, các truy vấn trong JOB có chung template, nên chạy câu 1a trước sẽ
"làm nóng" cache cho 1b, và latency của một câu phụ thuộc vào câu nào chạy trước nó.

**Khuyến nghị.** Cache phải ở trạng thái **hoàn toàn lạnh hoặc hoàn toàn nóng**, không được "ấm". Cold cache hoàn
toàn là không thực tế [19] và vô hiệu hóa các tối ưu dựa trên bộ đệm của DBMS. Bài báo cho rằng **hot cache là
công bằng hơn**, đạt được bằng cách chạy lặp cùng một truy vấn đến khi latency hội tụ. Thực nghiệm §8.6 xác định
chạy 3 lần và lấy lần thứ 3 là đủ.

---

### 3.3. Lỗ hổng 2: Mã hóa truy vấn và plan [§4]

Mã hóa (encoding) là bước chuyển truy vấn và plan thành vector số cho mô hình. Bài báo phân biệt:

- **Mã hóa truy vấn** (query encoding): thông tin không phụ thuộc vào cách thực thi, gồm bảng nào, join nào, điều
  kiện lọc nào.
- **Mã hóa plan** (plan encoding): thông tin từ plan vật lý, gồm loại join, loại scan, cardinality và cost tại mỗi
  node.

Các LQO hiện nay đều **hướng truy vấn** (query-driven), tức là dùng truy vấn làm đại diện cho dữ liệu bên dưới
DBMS, khác với các phương pháp ước lượng cardinality hướng dữ liệu như DeepDB hay NeuroCard [§4]. Do đó, mã hóa phải
đạt hai yêu cầu: **bền vững** (robust) và **đủ biểu đạt** (expressive).

#### a) Mã hóa mất tính bất biến [§4.1]

**Hiện trạng.** Theo Bảng 1 của bài báo:

| LQO | Mã hóa truy vấn | Thuộc tính số | Thuộc tính văn bản | Mã hóa plan |
|---|---|---|---|---|
| Neo | ✓ | cardinality | word2vec | ✓ |
| RTOS | ✓ | vector hóa filter | cardinality | chỉ bảng |
| **Bao** | **✗** | — | — | loại join, loại scan (không có định danh bảng) |
| Balsa | ✓ | cardinality | cardinality | ✓ |
| **Lero** | **✗** | — | — | ✓ |
| LEON | ✓ | cardinality | cardinality | ✓ |
| LOGER | ✓ | vector hóa filter | cardinality | loại join, bảng |
| HybridQO | ✓ | cardinality | cardinality | ✓ |

Phần lớn LQO mã hóa điều kiện lọc **chỉ bằng cardinality hoặc selectivity** của nó. Bao không dùng mã hóa truy vấn,
và trong plan cũng không biết node nào ứng với bảng nào, chỉ có cardinality và cost.

**Vì sao là vấn đề.** Bài báo đưa ra hai thí nghiệm tư duy:

1. **Các filter khác nhau có thể cho cùng cardinality trên cùng một bảng.** Ví dụ minh họa (do nhóm đặt):
   `title.production_year > 2010` và `title.kind_id = 1` có thể cùng lọc ra khoảng 500.000 dòng. Nếu mã hóa bằng
   cardinality thì hai filter này có **vector giống hệt nhau**. Tuy nhiên, chúng giữ lại hai tập phim khác nhau, và
   số dòng sau khi join với `cast_info` hay `movie_keyword` có thể chênh nhau rất xa. Plan tối ưu và latency vì vậy
   khác nhau.
2. **Các bảng có cùng cardinality cũng có cùng mã hóa** (trường hợp của Bao, vì không có định danh bảng).

Lý tưởng nhất, cần có **ánh xạ 1-1** giữa đặc trưng D và latency hay cost y của truy vấn với plan cho trước. Thực
tế, latency vốn đã dao động giữa các lần chạy, nên khi mã hóa còn gộp nhiều truy vấn khác nhau vào cùng một vector,
ánh xạ (D, y) trở thành **1-nhiều**. Với mô hình hồi quy, đây là dữ liệu **mâu thuẫn**: cùng X nhưng có nhiều y
khác nhau. Mô hình sẽ học giá trị trung bình, và không có kiến trúc nào, dù sâu đến đâu, khắc phục được sự mất
thông tin ở đầu vào.

Ngay cả khi có thêm mã hóa truy vấn, bất biến vẫn không được đảm bảo nếu mỗi thuộc tính chỉ được mã hóa bằng một
con số cardinality.

**Khuyến nghị.** Dùng **embedding** thay cho biểu diễn bằng một giá trị đơn, ví dụ word2vec cho thuộc tính văn
bản như Neo, và **vector hóa tường minh các điều kiện lọc** (toán tử `>`, `=`, `<` kèm giá trị đã chuẩn hóa
min-max) như RTOS.

**Nhận xét của nhóm.** Mã hóa chỉ bằng cardinality có một ưu điểm: không phụ thuộc lược đồ (schema-agnostic), nên
dễ train lại khi lược đồ thay đổi. Đây là lý do Bao chọn cách này. Bài báo chỉ ra rằng ưu điểm đó phải trả bằng sự
vi phạm tính bất biến. Đây là một **đánh đổi thiết kế** chứ không phải sai sót đơn thuần.

#### b) Mã hóa thiếu biểu đạt [§4.2]

**Hiện trạng.** Tập đặc trưng cuối cùng cần phản ánh cả **ngữ cảnh toàn cục** (truy vấn, không đổi trong suốt quá
trình tìm plan) và **ngữ cảnh cục bộ** (plan đang xét). Ý tưởng này lấy từ Graph CNN [14]: càng nhiều vòng tích
chập thì embedding của node càng chứa nhiều ngữ cảnh toàn cục. LOGER dùng graph transformer để tổng hợp mã hóa
truy vấn. Ngược lại, **Bao và Lero thiếu hẳn phần mã hóa truy vấn.**

**Hệ quả.** Mô hình chỉ thấy cấu trúc cục bộ của plan mà không biết toàn bộ truy vấn đang cần gì, nên **dễ hội tụ
về cực trị cục bộ** [9].

**Khuyến nghị.** **Dùng đồng thời mã hóa truy vấn và mã hóa plan** để hội tụ tốt hơn.

---

### 3.4. Lỗ hổng 3: Huấn luyện mô hình [§5]

Bảng 1 của bài báo cho thấy các LQO có pipeline huấn luyện rất khác nhau: Tree-CNN hay Tree-LSTM, hồi quy hay
learning-to-rank, đầu ra là plan hay hint set, và cách kiểm thử cũng khác nhau. Chưa có một chuẩn chung nào về cách
phân tích hiệu năng trong quá trình huấn luyện hay cách chọn phương pháp huấn luyện. Bài báo tập trung vào hai vấn
đề phổ biến nhất.

#### a) Kiểm soát overfitting và chọn mô hình [§5.1]

**Hiện trạng.**

| LQO | Cách kiểm soát |
|---|---|
| RTOS | Cross-validation, nhưng chỉ để đo chỉ số tổng hợp, không dùng để chọn mô hình cuối cùng |
| Balsa | Early stopping dựa trên tập validation **không cố định** |
| LEON | Early stopping dựa trên **accuracy** |
| Bao | Kiểm tra liên tục kiểu "time series" trên truy vấn mới |
| Các LQO còn lại | Không nêu rõ |

**Vì sao là vấn đề.** Bài báo nêu ba điểm:

1. **Lầm tưởng "RL không bị overfitting".** RL tối ưu một hàm mục tiêu không dừng (non-stationary) phụ thuộc vào
   chính chính sách hành động, nên không overfitting theo nghĩa cổ điển. Tuy nhiên, nếu khám phá (exploration)
   không đủ, RL vẫn có thể **kẹt ở chính sách dưới tối ưu** [32]. Phương pháp có giám sát thì dễ hội tụ về lời giải
   dưới tối ưu.
2. **Accuracy là tiêu chí dừng sớm kém.** Với bài toán tối ưu truy vấn, ta **không biết trước plan tối ưu**, nhất
   là với truy vấn nhiều join, nên không có "đáp án đúng" để tính accuracy.
3. **Tập validation không cố định** (Balsa) hoặc **time series** (Bao) khiến điểm số ở các thời điểm khác nhau
   được đo trên dữ liệu khác nhau, nên không so sánh được. Các kỹ thuật cơ bản như tinh chỉnh siêu tham số bằng
   cross-validation, early stopping và regularization (ví dụ dropout) chưa được áp dụng đầy đủ.

**Khuyến nghị.**
- Với RL, vẫn nên **tinh chỉnh siêu tham số** vì điều này giúp cải thiện hiệu năng chung.
- **Không** dùng accuracy hoặc cross-validation làm tiêu chí dừng sớm.
- **Tập holdout phải cố định**, không dùng CV hay time series, để phép đo trên đó so sánh được [7].

#### b) Đổi biến mục tiêu giữa chừng [§5.2]

**Hiện trạng.** LQO phải cân bằng giữa **tốc độ** và **độ chính xác** của biến mục tiêu. *Cost* tính nhanh vì do
mô hình chi phí của DBMS ước lượng, nhưng không chính xác. *Latency* là giá trị thật nhưng phải chạy truy vấn mới có.
Vì vậy RTOS, Balsa, Lero và LEON **pre-train trên cost, sau đó tiếp tục train trên latency** với cùng một mô hình.

**Vì sao là vấn đề.** Cost và latency có **thang đo và phương sai hoàn toàn khác nhau**. Cost là đơn vị trừu tượng,
có thể lên tới hàng triệu; latency tính bằng mili giây. Khi đổi biến mục tiêu, mô hình phải thích nghi với một phân
phối mới, nên **phần lớn những gì học được ở giai đoạn pre-train bị mất** [2]. Nhìn theo ML, đây là một dạng
*dịch chuyển phân phối nhãn* (label shift) do chính người thiết kế tạo ra.

**Khuyến nghị.**
1. Dùng **learning-to-rank**: thay giá trị thực bằng **thứ hạng tương đối** giữa các plan [20]. Thứ hạng không phụ
   thuộc thang đo, nên có thể đổi từ cost sang latency mà không mất kiến thức đã học.
2. Dùng **kiến trúc xâu chuỗi nhiều mô hình** như HybridQO: một mô hình dựa trên cost đề xuất plan ứng viên, một
   mô hình khác dựa trên latency chọn plan cuối. Mỗi biến mục tiêu được phục vụ bởi một mô hình riêng.

---

### 3.5. Lỗ hổng 4: Đánh giá và rò rỉ dữ liệu [§6, §7]

Đây là lỗ hổng mà bài báo nhấn mạnh nhiều nhất: *"khi mô hình được train và đánh giá trên một cách chia train/test
không cố định, phép so sánh trở thành **hướng dữ liệu** (data-centric) thay vì **hướng mô hình** (model-centric)"*.
Nói cách khác, kết quả phụ thuộc vào việc *câu nào nằm trong tập test* hơn là vào việc *mô hình nào tốt hơn*. Ngay
cả hai cách chia cùng loại (ví dụ hai lần chia ngẫu nhiên) cũng cho kết quả không so sánh được [Hình 4, 5].

#### a) Cách chọn tập test tùy ý [§6.1]

Bài báo phân tích ba cách chọn tập test trong các nghiên cứu trước:

| Cách chọn | Đề xuất bởi | Vấn đề |
|---|---|---|
| **Ext-JOB** | Neo | Thêm truy vấn có GROUP BY và ORDER BY không có trong JOB. Merge join được lợi từ ORDER BY, nên LQO ưu tiên merge join sẽ có lợi thế, và phép so sánh bị lệch |
| **JOB-Slow** | Balsa | Lấy 19 câu chậm nhất làm tập test. Trực giác là hợp lý (tối ưu chỗ tốn thời gian nhất), nhưng cả 19 câu đều có ≤ 11 join, trong đó 11 câu chỉ có ≤ 6 join. Đây là vùng PostgreSQL vẫn dùng quy hoạch động vét cạn, nên phép thử không đánh vào điểm yếu thật sự của optimizer |
| **Chia theo số join** | [43] | Ví dụ: truy vấn 3–4 join làm tập test. Hình 2 của bài báo cho thấy **số join gần như không giải thích được thời gian chạy (R² = −0,11)**, nên chia theo số join là dùng một đại lượng không liên quan đến mục tiêu tối ưu |

Hình 2 còn cho thấy truy vấn có **6–11 join** có thời gian chạy lớn nhất, tức là tiềm năng tối ưu cao nhất. Đây
cũng là khoảng mà PostgreSQL vẫn dùng quy hoạch động, vì GEQO chỉ bật từ 12 bảng.

#### b) Rò rỉ dữ liệu qua template [§7.2]

Đây là **lỗ hổng rò rỉ dữ liệu cốt lõi**. 113 truy vấn JOB sinh từ 33 template. Các biến thể cùng template
(1a, 1b, 1c, 1d) có **cùng bảng và cùng cấu trúc join**, chỉ khác điều kiện lọc. Do đó plan tối ưu của chúng thường
rất giống nhau.

Nếu chia ngẫu nhiên, rất có thể 1a, 1b, 1c nằm trong tập train còn 1d nằm trong tập test. Khi đó mô hình chỉ cần
**"nhớ" plan tốt của họ truy vấn 1** chứ không cần tổng quát hóa. Điểm số trên tập test vì vậy phản ánh khả năng
ghi nhớ hơn là khả năng tổng quát. Đây là dạng rò rỉ kinh điển trong ML khi các mẫu **không độc lập** (dữ liệu có
cấu trúc nhóm) mà vẫn chia như thể chúng độc lập.

**Khuyến nghị: ba kiểu chia với mức độ khó và rò rỉ khác nhau** [Hình 3]:

| Kiểu chia | Cách làm | Độ khó | Mức rò rỉ | Tương đương trong ML |
|---|---|---|---|---|
| **Leave One Out** | Mỗi template đưa **đúng 1 biến thể** vào tập test, các biến thể còn lại vào tập train | Dễ | Tối đa | Chia phân tầng (stratified) theo nhóm |
| **Random** | Chia ngẫu nhiên 80/20, bỏ qua template | Trung bình | Ngẫu nhiên | `KFold` / `train_test_split` |
| **Base Query** | **Mọi biến thể của một template nằm cùng phía**, 80/20 | **Khó nhất** | **Không có** | `GroupKFold` theo template |

Ví dụ với 5 template đầu của JOB [Hình 3]:

```
Truy vấn       1a 1b 1c 1d | 2a 2b 2c 2d | 3a 3b 3c | 4a 4b 4c | 5a 5b 5c
Leave One Out  Tr Te Tr Tr | Tr Tr Tr Te | Tr Te Tr | Te Tr Tr | Tr Tr Te
Random         Tr Tr Te Tr | Tr Te Tr Te | Tr Tr Tr | Te Te Tr | Tr Tr Te
Base Query     Tr Tr Tr Tr | Te Te Te Te | Te Te Te | Tr Tr Tr | Te Te Te
(Tr = train, Te = test)
```

Base Query split buộc mô hình phải áp dụng kiến thức lên **cấu trúc join chưa từng thấy**, nên mới đo được khả năng
tổng quát thật sự. Ba kiểu chia này không thay thế nhau mà **bổ sung cho nhau**: khoảng cách hiệu năng giữa
Leave One Out và Base Query cho biết mô hình phụ thuộc vào việc ghi nhớ template đến mức nào. Bài báo đề xuất dùng
cả ba để bao phủ các vùng tổng quát hóa khác nhau, từ khoảng cách tổng quát hóa (generalization gap) đến lấy mẫu
ngoài phân phối (out-of-distribution).

#### c) Covariate shift [§6.2]

**Hiện trạng.** Dữ liệu trong CSDL thay đổi theo thời gian. Ví dụ, truy vấn "phim phát hành sau 2022" sẽ trả về
ngày càng nhiều dòng khi có phim mới. DBMS xử lý bằng cách cập nhật thống kê định kỳ (`ANALYZE`), còn trọng số của
LQO thì đứng yên cho đến khi được train lại hoặc fine-tune.

**Vì sao là vấn đề.** Phân phối đặc trưng đầu vào lúc dùng khác lúc train, đúng định nghĩa covariate shift. Một số
phương pháp như Bao cố gắng thiết kế mã hóa chống chịu với thay đổi, bằng cách bỏ định danh bảng và cột, chỉ dùng
cardinality đã cập nhật. Thực nghiệm §8.3 của bài báo cho thấy cách này **chưa đủ**: Bao train trên CSDL đầy đủ
rồi chạy trên CSDL đã giảm 50% dữ liệu làm một số truy vấn chậm đi tới 24 lần.

**Khuyến nghị.** Mọi LQO mới nên **kèm theo một thí nghiệm đơn giản đo khả năng chịu covariate shift**.

#### d) Đo lường không nhất quán [§7.1, §7.3, §8.2]

Ngoài cách chia dữ liệu, các nghiên cứu trước còn khác nhau ở cách đo:

- **Cấu hình DBMS khác nhau** [Bảng 2]: `work_mem` từ 4 MB đến 4 GB, `shared_buffers` từ 128 MB đến 64 GB, có
  hoặc không có song song hóa, có hoặc không có bitmap/tid scan. Chỉ Balsa và LEON công bố đầy đủ file cấu hình.
  Riêng việc tăng `effective_cache_size` từ 4 GB lên 32 GB đã giảm thời gian lập plan của vài truy vấn từ khoảng
  3 s xuống dưới 100 ms.
- **Số lần chạy khác nhau:** LEON lấy trung bình nhân của 3 lần, [43] lấy trung bình cộng của 5 lần.
- **Bỏ qua thời gian suy luận.** Một LQO có thể tìm ra plan thực thi nhanh hơn, nhưng nếu phải mất hàng giờ để
  suy luận (như LEON, khoảng 9,6 giờ cho tập test LOO của JOB) thì không có giá trị thực tế.

**Khuyến nghị: framework benchmark end-to-end** [§7]. Framework yêu cầu công bố đầy đủ (a) dữ liệu CSDL, (b) mã
nguồn LQO, (c) phiên bản ngôn ngữ và thư viện, (d) cấu hình DBMS, (e) danh sách truy vấn và cách chia train/test.
Ngoài ra:
- Mọi phương pháp dùng **cùng một cấu hình PostgreSQL**.
- Chạy mỗi truy vấn 3 lần và lấy lần thứ 3.
- Chỉ số chính là **thời gian end-to-end = suy luận + lập plan + thực thi**.
- Báo cáo **thời gian train end-to-end**, gồm cả thời gian truy vấn DBMS để lấy dữ liệu.

---

### 3.6. Tổng hợp 4 lỗ hổng

| Giai đoạn | Lỗ hổng | Nguyên tắc ML bị vi phạm | Hệ quả | Khuyến nghị chính | Kiểm chứng thực nghiệm |
|---|---|---|---|---|---|
| **(1) Sinh dữ liệu** | Không có dữ liệu chuẩn; thu hẹp không gian plan; dynamic optimization; cache không kiểm soát | Bất biến của dữ liệu; nhãn chính xác | Nhãn nhiễu hoặc sai; PostgreSQL bị "cắt bớt công cụ" | Direct RL; hot cache; không tắt toán tử tùy tiện | §8.4, §8.5, §8.6, §8.7 |
| **(2) Mã hóa** | Filter và bảng khác nhau cho cùng vector; thiếu mã hóa truy vấn | Ánh xạ (D, y) phải là 1-1 | Dữ liệu mâu thuẫn; cực trị cục bộ | Embedding; vector hóa filter; dùng cả query và plan encoding | (lý thuyết) |
| **(3) Huấn luyện** | Validation không cố định; dừng sớm theo accuracy; đổi cost sang latency | Chọn mô hình trên holdout cố định; phân phối nhãn ổn định | Mô hình dưới tối ưu; mất kiến thức pre-train | Holdout cố định; tinh chỉnh siêu tham số; learning-to-rank hoặc xâu chuỗi mô hình | (lý thuyết) |
| **(4) Đánh giá** | Chọn tập test tùy ý; rò rỉ qua template; covariate shift; đo lường không thống nhất | Tập test độc lập với tập train; so sánh trong cùng điều kiện | Kết quả hướng dữ liệu, phóng đại hiệu năng LQO | 3 kiểu chia LOO/RND/BQ; framework end-to-end; thí nghiệm covariate shift | §8.2, §8.3 |

### 3.7. Tiểu kết

Từ góc nhìn học máy, các LQO hiện nay mắc lỗi ở **cả 4 giai đoạn** của pipeline, và các lỗi này cộng dồn:

- Ở **đầu vào**, dữ liệu train và cách mã hóa vi phạm tính bất biến. Mô hình nhận dữ liệu mâu thuẫn hoặc sai nhãn,
  nên dù kiến trúc mạnh đến đâu cũng bị giới hạn bởi chất lượng dữ liệu (*garbage in, garbage out*).
- Ở **quá trình học**, thiếu quy trình chọn mô hình chuẩn và đổi biến mục tiêu giữa chừng làm mô hình khó hội tụ
  về lời giải tốt.
- Ở **đầu ra**, cách đánh giá tùy ý và rò rỉ dữ liệu qua template làm kết quả công bố có thể **cao hơn thực tế**.

Điểm đáng chú ý là phần lớn các lỗ hổng này **không nằm ở mô hình** mà ở các khâu "kỹ thuật" xung quanh, những khâu
thường bị xem nhẹ trong các bài báo LQO. Điều này dẫn tới giả thuyết mà phần thực nghiệm của bài báo (trình bày ở
các phần sau của báo cáo) kiểm chứng: khi loại bỏ các lỗ hổng trên bằng một framework thống nhất,
**các LQO hiện tại không còn vượt PostgreSQL một cách có hệ thống.**

---

## TÀI LIỆU THAM KHẢO

Số thứ tự theo danh mục tài liệu của bài báo gốc.

- **[Bài báo]** C. Lehmann, P. Sulimov, K. Stockinger. *Is Your Learned Query Optimizer Behaving As You Expect? A
  Machine Learning Perspective.* PVLDB 17(7): 1565–1577, 2024. doi:10.14778/3654621.3654625
- [1] R. Avnur, J. M. Hellerstein. *Eddies: Continuously Adaptive Query Processing.* SIGMOD Record, 2000.
- [2] J. Brownlee. *Data Preparation for Machine Learning.* Machine Learning Mastery, 2020.
- [7] I. Goodfellow, Y. Bengio, A. Courville. *Deep Learning.* MIT Press, 2016.
- [8] Y. Guan et al. *Direct and Indirect Reinforcement Learning.* arXiv:2112.10600, 2021.
- [9] I. Guyon, A. Elisseeff. *An Introduction to Feature Extraction.* Springer, 2006.
- [14] T. N. Kipf, M. Welling. *Semi-Supervised Classification with Graph Convolutional Networks.* ICLR 2017.
- [17] J. P. La Salle. *The Stability of Dynamical Systems.* SIAM, 1976.
- [18] V. Leis et al. *How Good Are Query Optimizers, Really?* PVLDB 9(3), 2015.
- [19] J. J. Levandoski, P.-Å. Larson, R. Stoica. *Identifying Hot and Cold Data in Main-Memory Databases.* ICDE 2013.
- [20] T.-Y. Liu. *Learning to Rank for Information Retrieval.* 2009.
- [22] R. Marcus et al. *Bao: Making Learned Query Optimization Practical.* SIGMOD 2021.
- [23] R. Marcus et al. *Neo: A Learned Query Optimizer.* PVLDB 12(11), 2019.
- [32] R. S. Sutton, A. G. Barto. *Reinforcement Learning: An Introduction.* MIT Press, 2018.
- [39] Z. Yang et al. *Balsa: Learning a Query Optimizer Without Expert Demonstrations.* SIGMOD 2022.
- [41] X. Yu et al. *Cost-based or Learning-based? A Hybrid Query Optimizer for Query Plan Selection.* PVLDB 15(13), 2022.
- [43] Z. Yunjia et al. *Simple Adaptive Query Processing vs. Learned Query Optimizers.* PVLDB 16(9), 2023.
- P. G. Selinger et al. *Access Path Selection in a Relational Database Management System.* SIGMOD 1979.
  (Tài liệu bổ sung cho mục 2.3, không có trong danh mục của bài báo.)
