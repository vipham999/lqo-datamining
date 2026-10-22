# PHẦN 1. MỞ ĐẦU, CƠ SỞ LÝ THUYẾT VÀ PHÂN TÍCH 4 LỖ HỔNG TRONG PIPELINE ML CỦA LQO

> **Người phụ trách:** Thành viên 1 – Ngọc
>
> **Bài báo phân tích:** C. Lehmann, P. Sulimov, K. Stockinger. *Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective.* PVLDB 17(7): 1565–1577, 2024. doi:10.14778/3654621.3654625. Mã nguồn: github.com/edualc/lqo_ml_perspective
>
> **Quy ước trích dẫn**
> - `(§x.y)` là số mục trong bài báo gốc; `(Hình n)`, `(Bảng n)` là hình/bảng của bài báo; `(tr. n)` là số trang theo PVLDB (1565–1577).
> - `[n]` là **số thứ tự tài liệu tham khảo trong danh mục REFERENCES của bài báo** (tr. 1577). Danh mục đầy đủ ở **Phụ lục B**.
> - `(PT §x)` là mục tương ứng trong file phân tích của nhóm, [PHAN_TICH_BAI_BAO.md](PHAN_TICH_BAI_BAO.md).
> - Nội dung đánh dấu **[Nhận xét của nhóm]** hoặc **[Ví dụ minh họa của nhóm]** là phần nhóm tự bổ sung để giải thích, **không phải** phát biểu của bài báo.

---

## MỤC LỤC

- [Chương 1. Mở đầu](#chương-1-mở-đầu)
- [Chương 2. Cơ sở lý thuyết](#chương-2-cơ-sở-lý-thuyết)
- [Chương 3. Phân tích 4 lỗ hổng trong pipeline ML của LQO](#chương-3-phân-tích-4-lỗ-hổng-trong-pipeline-ml-của-lqo)
- [Chương 4. Tiểu kết](#chương-4-tiểu-kết)
- [Phụ lục A. Thuật ngữ](#phụ-lục-a-thuật-ngữ)
- [Phụ lục B. Tài liệu tham khảo](#phụ-lục-b-tài-liệu-tham-khảo)

---

## CHƯƠNG 1. MỞ ĐẦU

### 1.1 Đặt vấn đề: tối ưu hóa truy vấn SQL

SQL là ngôn ngữ **khai báo**: người dùng mô tả *muốn lấy dữ liệu gì*, không mô tả *lấy bằng cách nào*. Việc chọn cách thực thi do **bộ tối ưu truy vấn (query optimizer)** của DBMS đảm nhận. Với một câu SQL, có rất nhiều **kế hoạch thực thi (query plan)** cho cùng một kết quả, khác nhau ở thứ tự join, thuật toán join và cách đọc bảng. Thời gian chạy của các kế hoạch này có thể chênh nhau nhiều bậc độ lớn, nên chọn đúng kế hoạch quyết định hiệu năng của cả hệ thống.

Bài báo nêu rõ độ khó của bài toán ngay ở câu thứ hai của phần Mở đầu (§1, tr. 1565):

> *"Having in total O(n!) possible logical plans in the worst case for queries where the join graph is a clique with n tables, the problem is classified as NP-hard [37]. This implies that exhaustive methods cannot solve the problem for a higher order of joins, thus demanding the need for heuristical approaches."*

Diễn giải:
- Với truy vấn join *n* bảng mà bảng nào cũng join được với nhau (đồ thị join là clique), số kế hoạch logic trong trường hợp xấu nhất là **O(n!)**.
- Bài toán chọn kế hoạch tối ưu vì thế thuộc lớp **NP-khó**. Kết quả này được chứng minh trong [37] (Wang & Chen, 1996), bài báo chỉ dẫn lại.
- Hệ quả: **không thể vét cạn** khi số join lớn, DBMS buộc phải dùng **heuristic**. Ví dụ, PostgreSQL bỏ phương pháp vét cạn khi truy vấn có từ **12 mục FROM** trở lên (§1, chú thích 1).

**[Ví dụ minh họa của nhóm]** Sự bùng nổ của n!:

| Số bảng *n* | n! |
|---|---|
| 4 | 24 |
| 8 | 40.320 |
| 12 | ≈ 4,8 × 10⁸ |
| 17 (truy vấn 29a của JOB, §8.2.2) | ≈ 3,6 × 10¹⁴ |

### 1.2 Sự ra đời của bộ tối ưu truy vấn học máy (LQO)

Trong khoảng mười năm qua, các phương pháp ML đã "chiếm ưu thế mạnh" trong nghiên cứu tối ưu truy vấn (§1, tr. 1565). Theo phần Tóm tắt (Abstract), sự bùng nổ của **LQO (Learned Query Optimizer)** có hai nguyên nhân:

1. Sự tiến bộ liên tục của học sâu (DL).
2. Bài toán tối ưu truy vấn (QOP) **dễ dàng được phát biểu lại thành một bài toán ML**. Ý tưởng thường gặp là thay quy hoạch động, phương pháp phổ biến trong QOP, bằng các phương pháp mạnh hơn như **học tăng cường (RL)**.

Nhiều LQO đã ra đời, như Neo [23], Bao [22], Balsa [39], Lero [44], LEON [4], LOGER [3], HybridQO [41], RTOS [42] (§2). Mỗi bài đều báo cáo kết quả tốt hơn bộ tối ưu truyền thống trong thực nghiệm của riêng mình.

### 1.3 Vấn đề của lĩnh vực: "thay đổi nhanh nhưng có hệ quả"

Bài báo cho rằng sự "thay đổi cuộc chơi" quá nhanh này **"không thể không để lại hệ quả"** (Abstract). Cụ thể:

1. **Chỉ một giai đoạn được chú trọng.** Ngoài khâu phát triển mô hình dự đoán, các giai đoạn khác của pipeline ML còn nhiều chỗ có thể cải thiện (Abstract).
2. **Mỗi LQO tự đặt luật chơi riêng.** Các LQO khác nhau tự đặt giới hạn khi sinh dữ liệu train từ truy vấn, dùng cách chia train/validation tùy ý, và đánh giá trên một tập truy vấn tự chọn (Abstract).
3. **Vi phạm nguyên tắc ML.** Các nguyên tắc ML lý thuyết [30] bị vi phạm ở từng giai đoạn. Cộng với việc thiếu một framework thống nhất và tái lập được, điều này khiến hiện nay **"không thể so sánh công bằng kết quả của các LQO"** (§1, tr. 1566).
4. **Khó tái lập.** Một phương pháp ML trong học thuật *"gần như không có giá trị thực tiễn nếu không tái lập được trên phần mềm và phần cứng bất kỳ"* (§1, đoạn Reproducibility). LQO đòi hỏi kiến thức cả về CSDL lẫn ML, mã nguồn phức tạp và mô hình có tính ngẫu nhiên, nên khả năng tái lập ngày càng đáng lo ngại.

Bằng chứng cụ thể cho sự thiếu thống nhất là **Bảng 2** của bài báo (§7.1). Dung lượng RAM mà các nhóm tác giả dùng dao động từ **15 GB (Bao) tới 512 GB (Lero)**. LOGER và Lero **tắt song song hóa**, còn Balsa và LEON **tắt bitmap/tid scan** mà không giải thích lý do. Neo [23] và HybridQO [41] thậm chí không công bố cấu hình (PT §6.1).

### 1.4 Câu hỏi nghiên cứu và mục tiêu của bài báo

**Câu hỏi trung tâm:** khi được đánh giá công bằng và end-to-end, các LQO hiện nay có thật sự tốt hơn bộ tối ưu truyền thống (PostgreSQL) không? (PT §3)

Bài báo đặt ra ba mục tiêu (Abstract):
1. **Chuẩn hóa pipeline ML** để đánh giá LQO, thông qua một **framework benchmark end-to-end** mới.
2. **Dẫn dắt người đọc qua từng giai đoạn** của pipeline ML và đưa ra nhận định mới từ góc nhìn ML, có tính đến đặc thù của QOP.
3. **Đánh giá nghiêm ngặt** các LQO hiện có.

Đây là bài **đánh giá thực nghiệm và phương pháp luận**. Bài **không** đề xuất LQO mới, cũng không đề xuất phương pháp cổ điển thay thế; bài chỉ đưa ra *khuyến nghị cải thiện LQO* dựa trên đánh giá quy mô lớn (cuối §2; PT bảng thông tin).

### 1.5 Hướng tiếp cận: nhìn LQO như một pipeline ML

Ý tưởng cốt lõi của bài báo là nhìn LQO **"từ góc nhìn ML"**. Theo góc nhìn này, pipeline gồm 4 giai đoạn (§1, tr. 1566; Hình 1):

```
 (1) Training Data Generation ─► (2) Query & Plan Encoding ─► (3) LQO Training ─► (4) LQO Evaluation
      Sinh dữ liệu huấn luyện         Mã hóa truy vấn/kế hoạch       Huấn luyện mô hình      Đánh giá mô hình
```

Ở mỗi giai đoạn, bài báo trả lời câu hỏi *"điều gì có thể sai, xét cả từ góc độ khoa học dữ liệu lẫn kỹ thuật"* và gắn mỗi vấn đề với một **đóng góp** (§1, tr. 1566):

| # | Giai đoạn / chủ đề | Vấn đề tóm tắt (§1) | Đóng góp | Mục |
|---|---|---|---|---|
| 1 | Sinh dữ liệu | Benchmark không có dữ liệu train sẵn, nên dễ sinh dữ liệu **thiên lệch** | Thảo luận các hạn chế chung khi sinh dữ liệu train | §3 |
| 2 | Mã hóa | Vi phạm **nguyên tắc bất biến** gây mâu thuẫn trong dữ liệu | Chẩn đoán lỗi bất biến ở từng phương pháp, đưa khuyến nghị mã hóa | §4 |
| 3 | Huấn luyện | Sai kỹ thuật huấn luyện, áp dụng sai mô hình toán | Đề xuất cải tiến để huấn luyện ổn định, đáng tin cậy hơn | §5 |
| 4 | Đánh giá | Cách chia train/test không cố định làm so sánh trở thành **data-centric** | Thống nhất cách chia dữ liệu, đưa quy trình kiểm tra các mức tổng quát hóa | §6, §7.2 |
| 5 | Tái lập | Thiếu framework chung | **Framework benchmark end-to-end** (meta-benchmarking) | §7 |
| 6 | **Đóng góp chính** | — | Đánh giá thực nghiệm quy mô lớn 5 LQO trên JOB và STACK, kèm các ablation | §8 |

Bài báo cũng phân loại khuyến nghị của mình thành **khuyến nghị thực tiễn** (§3 và §6) và **khuyến nghị lý thuyết** (§4 và §5) (§1, đoạn cuối).

### 1.6 Kết luận chính của bài báo

> *"Our results demonstrate that current LQOs do not systematically perform better than PostgreSQL."* (§1, tr. 1566)

Trong thực nghiệm (§8.2.1), thứ hạng chung là:

> **PostgreSQL > HybridQO > Bao > Neo > Balsa > LEON**

PostgreSQL không thắng mọi split với ý nghĩa thống kê, và HybridQO, Bao đạt kết quả tương đương ở nhiều split (PT §7.1). Thông điệp của tác giả: *cần nghiên cứu mới để LQO cạnh tranh được với phương pháp truyền thống, không chỉ trong vài trường hợp riêng lẻ* (§1).

### 1.7 Phạm vi và cấu trúc của phần báo cáo này

Phần này trả lời hai câu hỏi: **(a)** cần nền tảng lý thuyết gì để hiểu bài báo (Chương 2), và **(b)** 4 lỗ hổng trong pipeline ML của LQO là gì, vì sao chúng sai về mặt ML, và bài báo khuyến nghị gì (Chương 3). Framework benchmark (§7) và kết quả thực nghiệm (§8) do các thành viên khác trình bày chi tiết. Ở đây chỉ dẫn chiếu các thí nghiệm dùng làm **bằng chứng** cho từng lỗ hổng.

---

## CHƯƠNG 2. CƠ SỞ LÝ THUYẾT

### 2.1 Bộ tối ưu truy vấn truyền thống trong DBMS

Nửa trên của **Hình 1** (§1, tr. 1565) mô tả pipeline cổ điển gồm hai khối: **Data Representation** (biểu diễn) và **Decision Making** (ra quyết định).

```
        ┌─────── Data Representation ───────┐   ┌──────────── Decision Making ─────────────┐
 SQL ──►│ Kế hoạch logic ──► Kế hoạch vật lý │──►│ Exact Optimization (quy hoạch động)      │──► Chosen Plan ──► SQL Result
        └────────────────────────────────────┘   │ Genetic Optimization (GEQO)              │
                                                 │            ▲                              │
                                                 │       Cost Model (dựa trên cardinality)  │
                                                 └──────────────────────────────────────────┘
```

#### 2.1.1 Kế hoạch logic và kế hoạch vật lý

- **Kế hoạch logic:** cây biểu diễn *thứ tự* thực hiện các phép join, chưa quy định thuật toán cụ thể.
- **Kế hoạch vật lý:** gán cho mỗi node một **toán tử cụ thể**:
  - *Thuật toán join:* nested loop join, hash join, merge join.
  - *Cách đọc bảng (scan):* sequential scan, index scan, bitmap scan, tid scan, ...
- Các lựa chọn này chính là những gì LQO tác động, bằng cách sinh trực tiếp kế hoạch hoặc bằng hint (Bảng 1, cột *Plan Encoding*: Join Type, Scan Type, Table Identifier).

#### 2.1.2 Hình dạng cây join: left-deep và bushy

- **Left-deep:** nhánh phải của mỗi phép join luôn là một bảng đơn. Bài báo gộp right-deep vào left-deep "mà không mất tính tổng quát" (§8.7, chú thích 8).
- **Bushy:** cả hai nhánh đều có thể là kết quả của một phép join con.
- Số cây bushy **lớn hơn nhiều** số cây left-deep (§8.7). Một số LQO (RTOS, LOGER, HybridQO) chỉ xét left-deep để thu hẹp không gian tìm kiếm. Bài báo chứng minh lựa chọn này có hại (xem 3.1.3).

#### 2.1.3 Cost model và ước lượng cardinality

- **Cardinality** là số dòng (ước lượng) mà mỗi toán tử trả về.
- **Cost model** dùng cardinality ước lượng để tính **cost** (đơn vị trừu tượng) cho từng kế hoạch. Bộ tối ưu chọn kế hoạch có cost thấp nhất.
- Bài báo mô tả cách tiếp cận cổ điển là *"tìm kế hoạch tối ưu dựa trên ước lượng của cost model theo cardinality"* (§1, tr. 1565).
- Lệnh `EXPLAIN` của PostgreSQL trả về kế hoạch được chọn kèm cardinality và cost ước lượng. `EXPLAIN ANALYZE` chạy thật và trả thêm thời gian lập kế hoạch và thời gian thực thi. Bài báo dùng `EXPLAIN ANALYZE` để đo (§8.1.1).

#### 2.1.4 Thuật toán tìm kiếm: quy hoạch động và thuật toán di truyền

- **Quy hoạch động (DP):** duyệt có hệ thống không gian kế hoạch ("Exact Optimization" trong Hình 1). Cho kết quả tối ưu theo cost model nhưng chi phí tăng rất nhanh theo số bảng.
- **Thuật toán di truyền:** ngoài DP, DBMS còn dùng thuật toán di truyền [34] vì chúng *"đã được chứng minh hiệu quả hơn với truy vấn có nhiều join"* [28] (§1, tr. 1565).
- Trong PostgreSQL, đó là **GEQO (Genetic Query Optimizer)**, mặc định dùng cho truy vấn có **từ 12 bảng trở lên** (`geqo_threshold = 12`). Có thể tắt bằng cách đặt `geqo_threshold` lớn hơn số join hoặc đặt `geqo = off` (§7.1, đoạn Join Order).
- Có thể ép thứ tự join bằng thư viện `pg_hint_plan` [27], hoặc đặt `join_collapse_limit = 1` để PostgreSQL theo đúng thứ tự viết trong câu SQL (§7.1).

### 2.2 Bộ tối ưu truy vấn học máy (LQO)

#### 2.2.1 Định nghĩa và vị trí trong pipeline

Nửa dưới của **Hình 1** mô tả LQO: các khối biểu diễn và ra quyết định được thay bằng **Query & Plan Encoding** và **Predictive Model** (mô hình dự đoán). Mô hình này được huấn luyện và đánh giá qua các giai đoạn Training Data Generation, LQO Training và LQO Evaluation. Bài báo gọi LQO là *"xu hướng mới nhất cho tối ưu truy vấn end-to-end"*, đi kèm một *"pipeline phức tạp hơn do sử dụng phương pháp ML"* (§1).

#### 2.2.2 Các hướng tiếp cận trước LQO end-to-end

Trước khi LQO end-to-end xuất hiện, đã có nhiều bước tiến dùng ML hiện đại cho QOP (§2):
- **DQ** [15], **ReJOIN** [24, 25] và các nghiên cứu khác [11, 16] áp dụng **RL** theo chiến lược *khám phá–khai thác (exploration–exploitation)* để tìm thứ tự join tối ưu.
- Các phương pháp này dùng **cost model** để tạo "điểm join" làm phần thưởng (reward) cho agent.

#### 2.2.3 Các LQO được bài báo khảo sát

Bảng dưới tổng hợp §2 và **Bảng 1** (tr. 1569) của bài báo, cùng PT §4:

| LQO | Ý tưởng chính (§2) | Mô hình | Xử lý plan | Đầu ra | Dữ liệu ngoài benchmark | Cách kiểm tra | Tích hợp DBMS | Trong thực nghiệm? |
|---|---|---|---|---|---|---|---|---|
| **Neo** [23] | LQO end-to-end **đầu tiên**: mạng nơ-ron ước lượng latency của kế hoạch đầy đủ khi biết một kế hoạch con; tìm kiếm cây tham lam, xây kế hoạch từ dưới lên | Hồi quy | Tree-CNN | Plan | – | Static | – | ✅ (bản cài lại trong Balsa) |
| **RTOS** [42] | Coi join graph là chuỗi phép join 2 bảng, **bỏ qua scan**; GNN huấn luyện agent RL; tìm theo chiều sâu | Hồi quy | Tree-LSTM | Plan | – | **CV** | – | ❌ |
| **Bao** [22] | Nằm **trên** optimizer của PostgreSQL, bật/tắt một tập con loại join và scan (**hint set**); không quyết định thứ tự join hay scan cụ thể cho từng bảng | Hồi quy | Tree-CNN | Hint set | ✅ | **Time Series** | ✅ | ✅ |
| **Balsa** [39] | Kiến trúc giống Neo nhưng **pre-train bằng cost** của DBMS thay vì latency thật; dùng **timeout**; lấy mẫu dữ liệu từ trạng thái NN mới nhất thay vì replay buffer | Hồi quy | Tree-CNN | Plan | – | Static | – | ✅ |
| **Lero** [44] | **Learning-to-rank (LTR)**: sinh kế hoạch ứng viên bằng cách thay đổi cardinality nội bộ; bộ so sánh chọn kế hoạch tốt hơn trong từng cặp | LTR | Tree-CNN | Plan | – | Static | ✅ | ❌ |
| **LEON** [4] | LTR; **vét cạn** kế hoạch vật lý theo kiểu DP trước khi huấn luyện; chỉ huấn luyện trên các cặp SQL–plan tốt nhất, xếp hạng theo latency và độ bất định từ **Bayesian NN** | LTR | Tree-CNN | Plan | – | Static | – | ✅ |
| **LOGER** [3] | Pipeline của RTOS, mở rộng không gian hành động bằng loại join; khuyến nghị loại join *không nên dùng*; **ε-beam search** | Hồi quy | Tree-LSTM | Hint | – | Static | – | ❌ |
| **HybridQO** [41] | Kết hợp cost và latency: lấy kế hoạch ứng viên từ DBMS qua hint (chọn bằng **MCTS** với cận tin cậy trên, cost ước lượng bằng NN của RTOS), rồi NN dự đoán latency và độ bất định; bộ ước lượng nhiều đầu ra (multi-head) chọn kế hoạch cuối | Hồi quy | Tree-LSTM | Plan | ✅ | Static | – | ✅ |

**Lý do 3 LQO bị loại khỏi thực nghiệm** (§8.2): (a) không có sẵn mã nguồn, (b) yêu cầu tắt song song hóa, hoặc (c) phải bỏ rất nhiều công kỹ thuật mới lấy được đầu ra `EXPLAIN`.

**Một hướng thay thế:** bài [43] (Zhang et al., 2023) đặt câu hỏi về tính hợp lý của việc huấn luyện các LQO phức tạp và tốn kém. Bài này đề xuất kết hợp *look-ahead information passing* (LIP) với *adaptive join* (AJA), tức kiểm tra ngay lúc chạy xem có nên thay hash join bằng nested loop join hay không (§2).

#### 2.2.4 Hai triết lý thiết kế LQO

**[Nhận xét của nhóm, dựa trên §2, §8.5 và PT §9.3]** Có thể chia các LQO theo mức độ can thiệp vào DBMS:

| Triết lý | Đại diện | Cách làm | Ưu / nhược |
|---|---|---|---|
| **Thay thế** optimizer | Neo, Balsa, LEON, RTOS | Mô hình tự sinh kế hoạch đầy đủ, ép DBMS chạy qua `pg_hint_plan` | Linh hoạt nhưng phải tự học mọi thứ, tốn thời gian train và suy luận |
| **Hướng dẫn / hỗ trợ** optimizer | Bao, HybridQO, LOGER (hint) | Tận dụng optimizer có sẵn, chỉ gợi ý bằng hint hoặc chọn trong số ứng viên do DBMS sinh | Ổn định hơn, nhưng bị giới hạn bởi không gian mà optimizer sinh ra |

Bài báo nhận xét ở §8.5 rằng *PostgreSQL cần chạy ở công suất đầy đủ (bật GEQO), đặc biệt khi LQO không thay thế mà chỉ tăng cường hoặc dẫn dắt optimizer có sẵn (ví dụ qua hint)*. Kết quả thực nghiệm cũng cho thấy hai LQO thuộc nhóm "hỗ trợ" (HybridQO, Bao) xếp ngay sau PostgreSQL.

### 2.3 Nền tảng học máy liên quan

#### 2.3.1 Dạng dữ liệu chuẩn (D, y)

Mọi mô hình LQO, dù đầu ra là *reward* hay *giá trị dự đoán*, đều có dữ liệu đầu vào dạng chuẩn là các cặp **(D, y)** (§3.3, tr. 1567):

- **D** là vector **biến đặc trưng (feature variables)**:
  - Với **học có giám sát**: tập biến độc lập **X**.
  - Với **RL**: bộ **(s, a, s′)** gồm *trạng thái*, *hành động*, *trạng thái kế tiếp*.
- **y** là **biến mục tiêu (target variable)**, có thể là **latency** (thời gian chạy thực tế), **cost** (chi phí ước lượng), hoặc **ranking** (thứ hạng), tùy mô hình.

Ba biến mục tiêu này có tính chất rất khác nhau, và đây là gốc rễ của lỗ hổng 3.3.3:

| Biến mục tiêu | Ưu điểm | Nhược điểm |
|---|---|---|
| Cost | Rẻ, tính được ngay bằng cost model (không cần chạy) | Không chính xác, đơn vị tùy ý |
| Latency | Chính xác, phản ánh đúng mục tiêu tối ưu | Đắt (phải chạy thật), biến động giữa các lần chạy |
| Ranking | Không phụ thuộc thang đo | Chỉ cho biết thứ tự tương đối |

#### 2.3.2 Học có giám sát và học tăng cường

- **Học có giám sát:** học ánh xạ D → y từ dữ liệu có nhãn. Có nguy cơ **overfitting** và hội tụ về nghiệm dưới tối ưu (§5.1).
- **Học tăng cường (RL):** agent học một **chính sách (policy)** bằng cách tối đa hóa phần thưởng thông qua tương tác với môi trường (ở đây là DBMS). Có thể *kẹt ở chính sách dưới tối ưu nếu không khám phá đủ* [32] (§5.1).
- **Direct RL và indirect RL** [8]: direct RL tối ưu trực tiếp hàm mục tiêu mà không cần mô hình hóa xác suất chuyển trạng thái của môi trường (§3.3.1).

#### 2.3.3 Kiến trúc mô hình cho dữ liệu dạng cây

Kế hoạch truy vấn có cấu trúc cây. Theo §5 (tr. 1568), có hai cách xử lý chính:
- **Tree Convolution (Tree-CNN)** [26]: coi cây như một ảnh và áp dụng tích chập trên cây (Neo, Bao, Balsa, Lero, LEON).
- **Tree-LSTM** [33]: coi cây như một chuỗi các cặp node, tương tự văn bản (RTOS, LOGER, HybridQO).

Các kiến trúc khác được nhắc tới:
- **Graph CNN** [14]: nền tảng cho ý tưởng ngữ cảnh toàn cục và cục bộ (§4.2).
- **Graph Transformer** [5]: dùng trong LOGER để gộp mã hóa truy vấn (§4.2).
- **Bayesian NN** (LEON) và **MCTS** (HybridQO) để ước lượng độ bất định và tìm kiếm (§2).

#### 2.3.4 Hồi quy và Learning-to-rank (LTR)

- **Hồi quy:** dự đoán giá trị tuyệt đối (cost hoặc latency) của từng kế hoạch, rồi chọn kế hoạch có giá trị nhỏ nhất.
- **Learning-to-rank** [20]: học *thứ tự tương đối* giữa các kế hoạch. Giá trị thực được chuyển thành thứ hạng, nên mô hình không phụ thuộc thang đo của biến mục tiêu (§5.2). Lero và LEON dùng LTR (Bảng 1).

#### 2.3.5 Các khái niệm đánh giá mô hình

| Khái niệm | Ý nghĩa | Vị trí trong bài |
|---|---|---|
| **Train / validation / test split** | Tách phần dữ liệu mô hình được thấy khi huấn luyện khỏi phần dùng để kiểm tra khả năng xử lý dữ liệu chưa thấy, tức **khả năng tổng quát hóa**. Đây là "nền tảng của mọi phương pháp có giám sát" | §6.1 |
| **Overfitting** | Hiệu năng trên tập train tăng nhưng trên tập validation giảm [38] | §5.1 |
| **Cross-validation (CV)** | Chia dữ liệu nhiều lần để tinh chỉnh siêu tham số và ước lượng hiệu năng | §5.1 |
| **Early stopping** | Dừng huấn luyện khi chỉ số trên tập validation không còn cải thiện | §5.1 |
| **Regularization** | Ví dụ dropout/DropConnect [36]: giảm overfitting nhưng thêm siêu tham số cần tinh chỉnh | §5.1 |
| **Holdout cố định** | Tập kiểm tra không đổi giữa các lần chạy, để kết quả so sánh được [7] | §5.1 |
| **Rò rỉ dữ liệu (data leakage)** | Thông tin từ tập train "lọt" sang tập test, làm kết quả kiểm tra lạc quan giả tạo | §7.2 |
| **Covariate shift** | Phân phối dữ liệu đầu vào thay đổi sau khi mô hình đã được huấn luyện | §6.2 |
| **Out-of-distribution** | Dữ liệu kiểm tra nằm ngoài phân phối dữ liệu huấn luyện | §6.1, §8.3 |

#### 2.3.6 Nguyên tắc bất biến (principle of invariance)

Đây là khái niệm then chốt, được dùng xuyên suốt §3 và §4. Khái niệm gốc lấy từ lý thuyết ổn định của hệ động lực [17]. Bài báo phát biểu lại cho bài toán sinh dữ liệu (§1, chú thích 3):

> *"When given the same input, the data generating system should return the same output."*
> (Với cùng một đầu vào, hệ thống sinh dữ liệu phải trả về cùng một đầu ra.)

Về mặt toán học, trong điều kiện lý tưởng cần có **ánh xạ 1-1** giữa đặc trưng D và biến mục tiêu y của một truy vấn và kế hoạch của nó (§4.1). Khi nguyên tắc này bị vi phạm, ánh xạ trở thành **1-nhiều** và dữ liệu huấn luyện tự mâu thuẫn. Có hai cách vi phạm:
- Phía **D** (đầu vào): hai truy vấn khác nhau có cùng vector mã hóa (§4.1), hoặc kế hoạch được mã hóa khác kế hoạch thực sự chạy (§3.3.1).
- Phía **y** (đầu ra): cùng một truy vấn và kế hoạch nhưng latency đo được khác nhau do trạng thái cache (§3.3.2).

### 2.4 Benchmark dùng trong bài báo

#### 2.4.1 JOB và STACK

| | **JOB** (Join Order Benchmark) [18] | **STACK** [22] |
|---|---|---|
| Dữ liệu | IMDB (phim) | StackExchange (hỏi đáp) |
| Quy mô | **113 truy vấn** từ **33 truy vấn gốc**; mỗi gốc có 2–6 biến thể (1a, 1b, ...) | **6.191 truy vấn** từ **16 truy vấn gốc**, mỗi gốc có 100–1.010 biến thể |
| Dùng trong thực nghiệm | Toàn bộ 113 truy vấn | Lấy mẫu xuống **14 truy vấn gốc × 8 biến thể** (bỏ template 9 và 10 theo Balsa, vì `pg_hint_plan` không xử lý được view và subquery) để có lượng dữ liệu tương đương JOB |
| Nguồn | §3.1, §7.2, §8.1.2 | §7.2, §8.1.2 (chú thích 4) |

Lý do chọn (§3.1):
- Cả hai lấy dữ liệu từ IMDB và StackExchange, nên **phản ánh thách thức tự nhiên của workload thực tế**.
- Theo [44], JOB là benchmark **thách thức nhất** cho LQO, và đa số phương pháp hiện nay dùng JOB và/hoặc STACK.

Lý do **không** chọn (§3.1):
- **STATS-CEB** [10]: được thiết kế cho bài toán *ước lượng cardinality*, không phải tối ưu truy vấn end-to-end.
- **Họ TPC** [35]: dựa trên giả định **dữ liệu phân phối đều đa biến**, nên không tạo ra thách thức hợp lý cho LQO.

#### 2.4.2 Cấu trúc "template – biến thể"

Các biến thể của cùng một truy vấn gốc **dùng chung bảng và phép join**, chỉ khác nhau ở **giá trị filter** (ví dụ `production_year < 2000` so với `production_year = 2023`) hoặc ở **cột được lọc** (ví dụ `genre = 'horror'` so với `name LIKE %an%`) (§7.2). Cấu trúc này là nguồn gốc của vấn đề **rò rỉ dữ liệu** (mục 3.4.3).

### 2.5 Tóm tắt: pipeline ML của LQO và framework của bài báo

```
 ┌────────────────────────── End-to-End Benchmarking Framework ──────────────────────────┐
 │  ① Training Data Generation             ③ LQO Training          ④ LQO Evaluation       │
 └──────────────┬──────────────────────────────────▲─────────────────────────┬───────────┘
                │                                  │                         │
                ▼                                  │                         ▼
        ② Query & Plan Encoding ─────────► Predictive Model ─────────► Chosen Plan ─► SQL Result
```

Theo chú thích của Hình 1: giai đoạn **(1), (3), (4)** là thành phần chính của **framework benchmark end-to-end**. Cùng với giai đoạn **(2)** (gắn với từng mô hình cụ thể), chúng tạo thành **pipeline ML điển hình** của một LQO. Chương 3 phân tích lần lượt từng giai đoạn.

---

## CHƯƠNG 3. PHÂN TÍCH 4 LỖ HỔNG TRONG PIPELINE ML CỦA LQO

Mỗi lỗ hổng được trình bày theo cấu trúc: **Mô tả vấn đề → Vì sao sai về mặt ML → Bằng chứng (từ bài báo hoặc thực nghiệm §8) → Khuyến nghị của tác giả → Nhận xét**.

---

### 3.1 LỖ HỔNG (1): SINH DỮ LIỆU HUẤN LUYỆN (§3)

#### 3.1.1 Gốc rễ: QOP không có dữ liệu huấn luyện "đóng gói sẵn"

**Mô tả.** Bài toán ML thông thường có benchmark công khai với **dữ liệu train sẵn dùng, giống nhau cho mọi người tham gia**. Benchmark QOP thì khác: chúng *khác nhau về dữ liệu cung cấp* và *chỉ là nguồn để sinh dữ liệu train* làm đầu vào cho mô hình ML (§3, tr. 1567).

Phần mở đầu (§1, tr. 1566) giải thích rõ hơn:
- Với các benchmark phổ biến như JOB [18], **chỉ có các câu lệnh SQL**.
- Các câu SQL này **không thể dùng trực tiếp** làm đầu vào cho mô hình ML. LQO phải **truy vấn CSDL** để trích xuất metadata như **cardinality** hay **thời gian thực thi**.
- Do đó có một **khoảng cách** giữa dữ liệu benchmark và đặc trưng thực sự dùng để huấn luyện, và các đặc trưng này **phụ thuộc mạnh vào điều kiện tham số khi truy vấn CSDL** (cấu hình, cache, phiên bản, ...).

**Vì sao nguy hiểm.** Điều này khiến *toàn bộ pipeline ML dễ bị mất nhất quán ngay từ khâu sinh dữ liệu* (§3). Bài báo nêu hai rủi ro chính:

> (1) Sinh dữ liệu dưới các **giới hạn không hợp lý** làm thu hẹp miền dữ liệu dùng cho train và validation, và có thể làm giảm khả năng tổng quát của mô hình.
> (2) Dữ liệu sinh ra có thể chứa những trường hợp **cùng đầu vào nhưng khác đầu ra**. (§3)

Chú thích 2 (§1) lưu ý: các nhận xét về dữ liệu train cũng áp dụng cho dữ liệu validation và test.

#### 3.1.2 Lựa chọn dataset (§3.1)

Đây không phải lỗ hổng mà là **lựa chọn có chủ đích** của bài báo để tránh dữ liệu "quá dễ". TPC dùng giả định phân phối đều, không có các tương quan phức tạp của dữ liệu thực, nên không đủ thách thức để đánh giá LQO (xem 2.4.1).

#### 3.1.3 Rủi ro (1): thu hẹp không gian kế hoạch một cách tùy tiện (§3.2)

**Mô tả.** Khi đánh giá các LQO, tác giả nhận thấy một số bài **giảm mạnh số kế hoạch vật lý**, ví dụ:
- **Tắt nested loop join** (như trong [18]).
- **Tắt bitmap scan và tid scan** (Balsa [39], LEON [4], và cả [43]; §8.4).
- **Chỉ xét cây left-deep, bỏ cây bushy** (RTOS, LOGER, HybridQO; §8.7).
- **Tắt GEQO** (§8.5).

**Vì sao sai về mặt ML.**
- Cách này *có thể cải thiện một số truy vấn*, nhưng thực chất là **giải bài toán bằng một giải pháp phụ thuộc dữ liệu**, đánh đổi bằng **khả năng tổng quát** (§3.2).
- Giới hạn loại scan, loại join, chế độ tối ưu không chính xác hay hình dạng cây **có thể làm tăng xác suất tìm ra kế hoạch dưới tối ưu** (§3.2).
- **[Nhận xét của nhóm]** Theo ngôn ngữ ML, đây là thu hẹp **không gian giả thuyết** mà mô hình được phép chọn. Nếu kế hoạch tối ưu nằm ngoài không gian đã bị cắt thì mô hình *không bao giờ* tìm được nó, dù có huấn luyện tốt đến đâu.

**Bằng chứng.**

*(a) Từ tài liệu khác (§3.2):*
- Cộng đồng PostgresPro [29] chỉ ra rằng **mỗi thuật toán join đều có lúc tốt hơn** các thuật toán khác, tùy theo độ chọn lọc của truy vấn con.
- Các tác giả Bao [22] chứng minh bằng thực nghiệm rằng tắt nested loop join trong PostgreSQL **có thể làm truy vấn 16b nhanh hơn nhưng làm truy vấn 24b chậm đi**.

*(b) Từ thực nghiệm của bài báo* (các phản ví dụ được hứa ở §3.2):

| Ablation | Thiết lập | Kết quả chính | Mục |
|---|---|---|---|
| **Tắt bitmap/tid scan** | Chạy lại 113 truy vấn JOB, so với baseline PostgreSQL ở §8.2 | **28 truy vấn** lệch hơn 250 ms, **24** trong số đó có ý nghĩa thống kê. *Nhanh hơn:* 28a (5,5×), 7c (2,0×), 30a (1,8×). *Chậm hơn:* 30c (2,4×), 28b (1,9×), 15c (1,5×). Ảnh hưởng rõ nhất ở các template 7, 8, 28, 30 | §8.4 |
| **Tắt GEQO** | Chạy JOB khi tắt GEQO | **5 truy vấn** khác biệt có ý nghĩa. *Nhanh hơn:* 30a (1,6×). *Chậm hơn:* 24b (9,9×, từ 28 ms lên 272 ms), 26c (2,2×), 28a (2,1×), 28b (1,7×) | §8.5 |
| **Bỏ cây bushy** | Vét cạn mọi kế hoạch của truy vấn JOB có ≤ 5 join, dùng **bộ ước lượng cardinality của DBMS** (không dùng cardinality thật như [18]) và cho phép mọi loại join | *Trung bình:* bushy ≈ left-deep (kiểm định Mann-Whitney U [21] hai phía, **p = 0,285**). *Ở đuôi trái* (các kế hoạch nhanh nhất): bushy **tốt hơn rõ rệt** (**p = 0,015**) | §8.7 |

**Diễn giải các bằng chứng:**
- **Cùng một họ truy vấn có thể vừa được lợi vừa bị hại:** khi tắt bitmap/tid scan, 28a nhanh hơn 5,5× nhưng 28b lại chậm đi 1,9× (§8.4). Đây chính là bản chất "phụ thuộc dữ liệu" mà §3.2 cảnh báo.
- Balsa, LEON và [43] tắt bitmap/tid scan **mà không đưa ra lý do** (§7.1, §8.4), trong khi thay đổi này ảnh hưởng đáng kể tới hiệu năng.
- Với cây bushy: bỏ cây bushy **làm giảm mạnh khả năng mô hình tìm được kế hoạch tốt nhất** (§8.7). Lý do là kế hoạch tốt nhất thường nằm ở đuôi trái của phân phối.
- Với GEQO: tác động nhỏ hơn bitmap/tid scan nhưng vẫn quan trọng, *đặc biệt ở các template chậm nhất*. Tác giả kết luận PostgreSQL phải chạy **ở công suất đầy đủ** (§8.5).

**Khuyến nghị (rút ra từ §3.2 và §8.4–§8.7):** không giới hạn không gian kế hoạch một cách tùy tiện. Nếu có giới hạn thì phải giải thích và đo ảnh hưởng của nó. Framework của bài báo **bật lại bitmap/tid scan** (§8.1.1; Bảng 2).

#### 3.1.4 Rủi ro (2a): biến đặc trưng không bất biến do Dynamic Optimization (§3.3.1)

**Mô tả.**
- Phần lớn LQO dùng extension `pg_hint_plan` [27] để **ép PostgreSQL chạy một kế hoạch cụ thể** thay vì kế hoạch do optimizer có sẵn dự đoán.
- Tuy nhiên, *"không nên kỳ vọng rằng kế hoạch kèm hint thực sự được thực thi"*. Lý do là DBMS có thể **cập nhật kế hoạch động trong quá trình thực thi** [1] (bài *Eddies* về xử lý truy vấn thích ứng liên tục). Hiện tượng này gọi là **dynamic optimization**.

**Vì sao sai về mặt ML.**
- **Mọi LQO được đánh giá** đều ép DBMS thực thi kế hoạch của mình trong giai đoạn mã hóa kế hoạch, nên **có thể đang huấn luyện trên dữ liệu sai** (§3.3.1).
- Dynamic optimization cũng có thể giải thích **sự khác biệt giữa kế hoạch thực sự chạy và đầu ra của `EXPLAIN`**. Các LQO dựa vào cardinality ước lượng từ `EXPLAIN` vì thế *có thể đưa vào các ước lượng sai lệch đáng kể* (§3.3.1).
- **[Nhận xét của nhóm]** Đây là vi phạm bất biến ở **phía D**: vector đặc trưng mô tả kế hoạch A, nhưng nhãn y (latency) lại là của kế hoạch A′ mà DBMS thực sự chạy. Mô hình học một quan hệ "D(A) → y(A′)" không tồn tại trong thực tế.

**Khuyến nghị (§3.3.1).** Dùng **direct RL**:
- Coi DBMS là một **"hộp đen"**.
- Tối đa hóa trực tiếp hàm mục tiêu bằng **gradient descent**.
- **Không cần học xác suất chuyển trạng thái** (tức hành vi ngẫu nhiên của DBMS) và **không cần giải phương trình Bellman** [8].

**[Nhận xét của nhóm]** Đây là khuyến nghị **lý thuyết**. Bài báo không thực nghiệm để đo mức độ dynamic optimization xảy ra trên JOB (PT §9.2: các khuyến nghị ở §3–§5 phần lớn chưa được kiểm chứng bằng thực nghiệm).

#### 3.1.5 Rủi ro (2b): biến mục tiêu không bất biến do Cold cache và Hot cache (§3.3.2)

**Mô tả.**
- Khi một truy vấn chạy nhiều lần, thời gian thực thi **giảm dần** vì DBMS đọc thông tin đã tính sẵn từ lần trước (**hot cache**), thay vì tạo lại mọi thứ từ đầu (**cold cache**).
- Muốn kết quả *so sánh được và nhất quán* cho mọi truy vấn thì trạng thái cache phải **hoàn toàn cold** hoặc **hoàn toàn hot**, tức mọi bộ nhớ đệm có thể dùng đều đã được dùng. **Không chấp nhận trạng thái "warm" ở giữa** (§3.3.2).

**Vì sao sai về mặt ML.**
- Nếu dữ liệu train trộn các phép đo ở trạng thái cache khác nhau thì **cùng một (truy vấn, kế hoạch)** sẽ có **nhãn y khác nhau**. Đây là vi phạm bất biến ở **phía y** (PT §5.1).
- **[Ví dụ minh họa của nhóm]** Kế hoạch P của truy vấn 1a được đo 2 lần: lần đầu (cold) 1.200 ms, lần sau (hot) 950 ms. Mô hình nhận hai mẫu (D(P), 1200) và (D(P), 950), tức cùng đầu vào nhưng hai đầu ra. Sai số này không đến từ chất lượng kế hoạch mà từ thứ tự chạy.

**Lựa chọn giữa cold và hot (§3.3.2).**
- Ép **toàn bộ cold cache** là *không thực tế* [19].
- Ngoài ra, việc chạy truy vấn với cold cache có công bằng hay không cũng là *một câu hỏi về đạo đức*, vì nó **vô hiệu hóa mọi kỹ thuật tối ưu dựa trên buffer** của DBMS.

**Khuyến nghị (§3.3.2).**
- Workload như JOB có tương quan giữa các truy vấn (do sinh từ template), nên **ép trạng thái hot cache là công bằng hơn**, vì nó *giảm ảnh hưởng của các truy vấn chạy trước* lên thời gian của từng truy vấn.
- Về mặt khái niệm: **chạy liên tiếp cùng một truy vấn đến khi latency hội tụ**. Cách hiện thực cụ thể ở §7.3.

**Bằng chứng và hiện thực (§7.3, §8.6).**
- Ở các LQO khác: LEON [4] dùng trung bình nhân với k = 3 lần chạy, [43] chạy k = 5 lần và lấy trung bình cộng (§8.6). Mỗi bài một kiểu.
- Thí nghiệm của bài báo: chạy mọi truy vấn JOB bằng `EXPLAIN ANALYZE` **50 lần liên tiếp**, theo thứ tự 1a, 1a, ..., 1a, 1b, 1b, ... (§8.6).
- Kết quả (**Hình 7**, tr. 1576):
  - Từ lần 1 sang lần 2: thời gian giảm trung bình **14,6%**.
  - Từ lần 2 sang lần 3: giảm thêm **1,03%**.
  - Từ lần 3 trở đi: dao động **không còn xu hướng**.
- Kết luận: phải chạy **ít nhất 2 lần**; lần thứ 3 tăng thêm độ ổn định, sau đó có thể dừng. So với k = 5 của [43], **lấy lần chạy thứ 3** *nhanh hơn 40%* và *ổn định hơn so với lấy trung bình 3 lần* (vì lần đầu thường là ngoại lai) (§8.6).
- Framework của bài báo vì thế **chạy mỗi truy vấn 3 lần và lấy lần thứ 3** (§7.3, §8.1.1).

**[Nhận xét của nhóm, theo PT §9.2]** Chỉ đo ở hot cache đảm bảo tính nhất quán, nhưng **không phản ánh workload thực tế có cold cache**.

#### 3.1.6 Tóm tắt lỗ hổng (1)

| Vấn đề | Vi phạm | Khuyến nghị | Bằng chứng |
|---|---|---|---|
| Không có dữ liệu train sẵn | Đặc trưng phụ thuộc điều kiện truy vấn DBMS | Chuẩn hóa điều kiện sinh dữ liệu (framework §7) | §1, §3 |
| Thu hẹp không gian kế hoạch | Giảm tổng quát hóa, tăng xác suất chọn kế hoạch dưới tối ưu | Không tắt tùy tiện; bật lại bitmap/tid scan | §3.2; §8.4, §8.5, §8.7 |
| Dynamic optimization | Bất biến phía **D** | Direct RL, DBMS là hộp đen | §3.3.1; [1], [8], [27] |
| Cold và hot cache | Bất biến phía **y** | Ép hot cache: chạy 3 lần, lấy lần 3 | §3.3.2, §7.3, §8.6; [19] |

---

### 3.2 LỖ HỔNG (2): MÃ HÓA TRUY VẤN VÀ KẾ HOẠCH (§4)

#### 3.2.1 Vai trò của bước mã hóa

Mã hóa là bước chuyển **câu SQL và kế hoạch vật lý** thành **vector số** làm đầu vào cho mô hình ML (§4, tr. 1568).

Theo hiểu biết của tác giả, các LQO hiện nay đều là phương pháp **hướng truy vấn (query-driven)**, trái với các phương pháp **hướng dữ liệu (data-driven)** cho ước lượng cardinality như DeepDB [12] và NeuroCard [40] (§4).
- Nghĩa là LQO dùng **truy vấn làm đại diện (proxy) không thể thiếu** cho dữ liệu nằm dưới DBMS.
- Hệ quả: lược đồ mã hóa truy vấn phải vừa **giàu biểu đạt (expressive)** vừa **bền vững (robust)** (§4).

#### 3.2.2 Giải phẫu các thành phần mã hóa (Bảng 1)

Bài báo phân biệt hai loại mã hóa (§4.1, Bảng 1):

**(A) Query encoding**: thông tin *độc lập với cách truy vấn được thực thi*:

| Thành phần | Ý nghĩa (chú thích Bảng 1) | Các lựa chọn |
|---|---|---|
| Adjacency Matrix | One-hot hóa đồ thị con của các phép join trong (sub)query | Có / không |
| Numerical Attributes | Cách mã hóa filter trên cột số | **cardinality** (một giá trị), hoặc **filters**: mã hóa tường minh các toán tử >, =, < cùng giá trị filter đã chuẩn hóa min-max |
| Text Attributes | Cách mã hóa filter trên cột văn bản | **cardinality**, hoặc **word2vec** (embedding) |
| Encoding Aggregation | Cách gộp các vector | **stacking** (ghép nối), **pooling** (giảm chiều), **FC** (lớp fully-connected), **GT** (graph transformation) |

**(B) Plan encoding**: thông tin *dựa trên kế hoạch vật lý*:

| Thành phần | Ý nghĩa |
|---|---|
| Join Type | Loại thuật toán join tại mỗi node |
| Scan Type | Loại scan tại mỗi lá |
| Table Identifier | One-hot hóa bảng trong lược đồ DBMS |

**Đối chiếu từng LQO** (Bảng 1, tr. 1569):

| LQO | Adj. Matrix | Numerical | Text | Aggregation | Join | Scan | Table ID |
|---|---|---|---|---|---|---|---|
| Neo [23] | ✓ | cardinality | **word2vec** | stacking | ✓ | ✓ | ✓ |
| RTOS [42] | ✓ | **filters** | cardinality | FC + pooling | – | – | ✓ |
| Bao [22] | **–** | **–** | **–** | **–** | ✓ | ✓ | **–** |
| Balsa [39] | ✓ | cardinality | cardinality | stacking | ✓ | ✓ | ✓ |
| Lero [44] | **–** | **–** | **–** | **–** | ✓ | ✓ | ✓ |
| LEON [4] | ✓ | cardinality | cardinality | stacking | ✓ | ✓ | ✓ |
| LOGER [3] | ✓ | **filters** | cardinality | FC + pooling + GT | ✓ | – | ✓ |
| HybridQO [41] | ✓ | cardinality | cardinality | stacking + FC | ✓ | ✓ | ✓ |

**Quan sát:**
- **Bao và Lero không có query encoding.** Bao còn thiếu cả Table Identifier.
- Chỉ **Neo** dùng embedding (word2vec) cho thuộc tính văn bản.
- Chỉ **RTOS** và **LOGER** mã hóa filter số một cách tường minh.
- Các LQO còn lại (Balsa, LEON, HybridQO) mã hóa **cả thuộc tính số lẫn văn bản chỉ bằng cardinality**.

#### 3.2.3 Lỗ hổng 2a: độ bền vững, tức vi phạm nguyên tắc bất biến (§4.1)

**Vấn đề 1: không có query encoding (Bao, Lero).**
- Bao [22] và Lero [44] **chỉ dùng plan encoding**. Ví dụ, Bao **không xác định bảng nào được dùng ở node nào** trong cây kế hoạch, mà chỉ dùng **cardinality và cost** của bảng (§4.1).
- Thiết kế này có ưu điểm: *không phụ thuộc lược đồ (schema-agnostic)* và *dễ huấn luyện lại khi lược đồ CSDL thay đổi*. Nhưng nó **vi phạm nguyên tắc bất biến** [17] (§4.1).

**Thí nghiệm tư duy của tác giả (§4.1):**
1. *Áp dụng các filter khác nhau* trong một truy vấn có thể cho **cùng một cardinality** trên cùng một bảng.
2. *Các bảng có cùng cardinality* có thể có **cùng một mã hóa**.
3. Trong điều kiện lý tưởng cần **ánh xạ 1-1** giữa D và y. Tuy nhiên **latency vốn biến động** và khác nhau giữa các lần chạy, nên mã hóa kế hoạch sẽ dẫn tới **ánh xạ 1-nhiều** cho các cặp (D, y).

**Vấn đề 2: có query encoding vẫn chưa đủ.**
- Ngay cả khi thêm query encoding, *việc mã hóa thuộc tính bằng một giá trị cardinality duy nhất vẫn không đảm bảo bất biến*. Như ví dụ trên, các filter khác nhau trên cùng một cột có thể cho cùng ước lượng cardinality, nên tính bất biến bị mất (§4.1).
- Phần mở đầu (§1, đoạn Query & Plan Encoding) nói rõ hơn: khi mã hóa bằng **selectivity của cột**, *"có thể nhiều phần lớn của vector mã hóa (thậm chí toàn bộ vector) trùng nhau"*, vì nhiều tổ hợp filter cho cùng selectivity. Khi đó *mô hình sẽ chịu ảnh hưởng của sự không khớp giữa đặc trưng và biến mục tiêu, và chỉ hoạt động tốt nếu sự mâu thuẫn này được giảm thiểu*.
- Theo Bảng 1, Balsa, LEON, HybridQO (mã hóa cả số lẫn văn bản bằng cardinality) đều chịu rủi ro này.

**[Ví dụ minh họa của nhóm]** Trên bảng `title` của IMDB, giả sử hai truy vấn cùng cấu trúc join:

```
Q1: ... WHERE t.production_year > 2010   -- ước lượng 50.000 dòng
Q2: ... WHERE t.title LIKE '%love%'      -- ước lượng 50.000 dòng
```

Nếu `title` chỉ được mã hóa bằng cardinality 50.000 thì Q1 và Q2 có **cùng vector D**. Nhưng các dòng thỏa mãn Q1 và Q2 phân bố khác nhau, có độ tương quan khác nhau với các bảng được join tiếp theo, nên **latency thực tế khác nhau**. Mô hình nhận cùng D với hai y khác nhau, và chỉ có thể học được "giá trị trung bình", không phân biệt được hai trường hợp.

**Khuyến nghị (§4.1).** Để không làm hỏng quá trình huấn luyện vì ánh xạ (D, y) không 1-1:
- **Dùng embedding thay cho biểu diễn bằng một giá trị**, ví dụ embedding cho thuộc tính văn bản như Neo (xem Hình 12 và 13 trong bài gốc của Neo [23]).
- **Vector hóa tường minh các filter** như RTOS [42], tức mã hóa riêng toán tử và giá trị.

#### 3.2.4 Lỗ hổng 2b: tính biểu đạt của mã hóa (§4.2)

**Nguyên lý.** Bộ đặc trưng cuối cùng phải phản ánh rõ cả hai loại ngữ cảnh (§4.2):
- **Ngữ cảnh toàn cục** là **truy vấn**, vì truy vấn *không đổi* trong suốt quá trình tìm kiếm trong không gian kế hoạch vật lý.
- **Ngữ cảnh cục bộ** là **kế hoạch truy vấn**.

**Nguồn gốc ý tưởng.** Khái niệm này đến từ **Graph CNN** [14]: càng nhiều vòng tích chập thì embedding của node càng mang nhiều ngữ cảnh toàn cục và ít ngữ cảnh cục bộ. Tiếp nối hướng GNN, **graph transformer** [5] được LOGER [3] dùng trong một bối cảnh tương tự để gộp mã hóa truy vấn (§4.2).

**Vấn đề.** Bao [22] và Lero [44] **thiếu phần query encoding**, làm **tăng xác suất hội tụ về cực trị địa phương** [9] (§4.2).

**[Nhận xét của nhóm]** Thiếu ngữ cảnh toàn cục thì mô hình chỉ thấy "mảnh ghép" là kế hoạch con, không biết truy vấn tổng thể cần gì. Vì vậy mô hình có thể chọn những kế hoạch con tốt cục bộ nhưng kém về toàn cục.

**Khuyến nghị (§4.2):** **dùng cả query encoding và plan encoding**, để mô hình hội tụ tốt hơn.

#### 3.2.5 Mâu thuẫn giữa bất biến và khả năng chống covariate shift

**[Nhận xét của nhóm, dựa trên §4.1, §6.2, §8.3 và PT §12 câu 4]**
- Bao **cố ý bỏ** định danh bảng và cột để **không phụ thuộc lược đồ** và **chống chịu covariate shift** (§4.1, §6.2).
- Chính lựa chọn này lại khiến Bao **vi phạm bất biến** (§4.1).
- Thí nghiệm §8.3 cho thấy *chỉ cập nhật cardinality trong mã hóa là không đủ* để theo kịp dữ liệu thay đổi (chi tiết ở 3.4.5).
- Như vậy, thiết kế mã hóa phải cân bằng giữa **độ chính xác (bất biến)** và **độ linh hoạt (chống thay đổi)**. Bài báo chưa đưa ra lời giải cho mâu thuẫn này.

#### 3.2.6 Tóm tắt lỗ hổng (2)

| Vấn đề | LQO bị ảnh hưởng (Bảng 1) | Hậu quả | Khuyến nghị |
|---|---|---|---|
| Không có query encoding | Bao, Lero | Vi phạm bất biến; thiếu ngữ cảnh toàn cục, dễ rơi vào cực trị địa phương [9] | Mã hóa cả query lẫn plan (§4.2) |
| Mã hóa filter bằng một giá trị cardinality | Balsa, LEON, HybridQO (cả số và văn bản); Neo (thuộc tính số); RTOS, LOGER (thuộc tính văn bản) | Nhiều truy vấn trùng vector, ánh xạ (D, y) 1-nhiều | Embedding (Neo/word2vec), vector hóa filter (RTOS) (§4.1) |

**[Nhận xét của nhóm, theo PT §9.2]** Các khuyến nghị ở §4 **chưa được kiểm chứng bằng thực nghiệm** trong bài. Ví dụ, bài chưa đo xem embedding có thật sự cải thiện kết quả trên JOB hay không.

---

### 3.3 LỖ HỔNG (3): HUẤN LUYỆN MÔ HÌNH (§5)

#### 3.3.1 Bối cảnh: thiếu một "mặt bằng chung" khi huấn luyện

- Đặc điểm then chốt của LQO là khả năng **học toàn bộ quy trình tối ưu truy vấn bằng ML** (§5, tr. 1568).
- Bảng 1 cho thấy các pipeline huấn luyện **rất khác nhau**: hồi quy hay LTR, Tree-CNN [26] hay Tree-LSTM [33], đầu ra là plan, hint set hay hint.
- *"Vẫn chưa có một mặt bằng chung nào"*, chẳng hạn về **phân tích hiệu năng trong quá trình huấn luyện** hay **lựa chọn phương pháp huấn luyện** (§5).
- Phần mở đầu (§1, đoạn LQO Training) cảnh báo: *"vi phạm các kỹ thuật huấn luyện cơ bản và áp dụng sai mô hình toán học khiến mô hình ML hoạt động bất thường"*. Mô hình DL phức tạp khó huấn luyện, nên **tinh chỉnh siêu tham số và quy trình validation là nền tảng** để có sức dự đoán cao. Thêm các cơ chế toán học phụ có thể *gây tác dụng phụ*, ảnh hưởng xấu tới quá trình huấn luyện và qua đó tới hiệu năng truy vấn.

#### 3.3.2 Lỗ hổng 3a: overfitting và quy trình validation (§5.1)

**Lý thuyết (§5.1).**
- **Overfitting:** hiệu năng trên tập train cải thiện nhưng trên tập validation giảm [38].
- **Với RL:** theo định nghĩa, các phương pháp RL *không gặp vấn đề này*, vì chúng học chính sách tối ưu bằng cách tối đa hoặc tối thiểu một **hàm mục tiêu không dừng (non-stationary)** phụ thuộc chính chính sách hành động. Tuy nhiên RL *có thể kẹt ở chính sách dưới tối ưu nếu không khám phá đủ* [32].
- **Với học có giám sát cổ điển:** dễ hội tụ về **nghiệm dưới tối ưu**.
- **Kỹ thuật phòng chống phổ biến:** tinh chỉnh siêu tham số bằng **cross-validation (CV)**, **early stopping** và **chính quy hóa**. Chính quy hóa như dropout [36] dễ dùng nhưng làm tăng số siêu tham số cần tinh chỉnh; các kỹ thuật khác khó điều chỉnh hơn.

**Thực trạng ở các LQO (§5.1; cột *Testing* của Bảng 1):**

| LQO | Cách validation/kiểm tra | Vấn đề theo bài báo |
|---|---|---|
| **RTOS** [42] | Dùng **CV** (LQO duy nhất) | CV chỉ dùng để *đo chỉ số hiệu năng tổng hợp cuối cùng*, **không giúp chọn mô hình cuối** |
| **Balsa** [39] | **Early stopping** theo mức cải thiện trên **tập validation không cố định** | Tập validation thay đổi giữa các lần chạy, nên kết quả không so sánh được |
| **LEON** [4] | Early stopping tương tự nhưng dùng **accuracy** làm chỉ số | Accuracy là chỉ số kém cho QOP (xem dưới) |
| **Bao** [22] | Kiểm tra **"time series"** liên tục trên các truy vấn chưa thấy | Holdout không cố định |
| Neo, Lero, LOGER, HybridQO | Chia **Static** trên JOB | Một lần chia cố định, không tinh chỉnh siêu tham số theo CV |

**Vì sao "accuracy" là chỉ số kém (§5.1).** Với QOP, accuracy (cho cả cost lẫn latency) là *chỉ số chất lượng dưới tối ưu*, vì **ta không biết trước kế hoạch tối ưu**, ít nhất là với truy vấn có nhiều join. Muốn tính "đúng/sai" thì phải biết đáp án đúng, mà đáp án đúng chính là thứ NP-khó để tìm (xem 1.1).

**Vì sao holdout phải cố định (§5.1).** Phép đo trên tập holdout chỉ **so sánh được** khi tập này không đổi [7]. Validation kiểu "time series" (Bao) hay tập validation không cố định (Balsa) khiến kết quả của các lần chạy hoặc các phương pháp khác nhau không thể đặt cạnh nhau.

**Khuyến nghị (§5.1).**
1. Với RL, **vẫn nên tinh chỉnh siêu tham số**, vì việc này giúp cải thiện hiệu năng chung của mô hình.
2. **Không dùng accuracy** làm tiêu chí early stopping hay tiêu chí CV.
3. **Dữ liệu holdout phải cố định**, không dùng CV và không dùng "time series".

**[Nhận xét của nhóm, theo PT §9.2]** Bài báo công bố siêu tham số của mọi phương pháp trong kho mã nguồn (§8.1.3) nhưng **không mô tả quy trình tinh chỉnh siêu tham số cho từng LQO**, dù chính §5.1 khuyến nghị việc này. Vì vậy các LQO có thể chưa ở trạng thái tốt nhất.

#### 3.3.3 Lỗ hổng 3b: đổi biến mục tiêu giữa chừng (§5.2)

**Bối cảnh.** QOP có một đặc thù: mục tiêu tối ưu có thể là **cost** hoặc **latency**. Điều này dẫn tới một sự đánh đổi giữa (§5.2):
- **Tốc độ:** cost có thể *ước lượng nhanh* bằng một cost model tùy ý.
- **Độ chính xác:** latency cho *giá trị chính xác* của thời gian chạy.

**Hai cách tiếp cận trong các LQO hiện có (§5.2):**

| Cách tiếp cận | LQO | Mô tả |
|---|---|---|
| **Một mô hình, đổi mục tiêu giữa chừng** | RTOS, Balsa, Lero, LEON | Một mô hình duy nhất: **pre-train bằng cost**, sau đó **train tiếp bằng latency** |
| **Xâu chuỗi nhiều mô hình** | HybridQO | Mô hình thứ nhất gợi ý kế hoạch dựa trên **cost**; mô hình thứ hai chọn giữa các ứng viên dựa trên **latency** |

**Vì sao cách thứ nhất sai về mặt ML (§5.2).**
- Latency và cost có **tính chất số học rất khác nhau**, cụ thể là **khác thang đo và khác phương sai** (độ lệch so với trung bình của giá trị mục tiêu) [2].
- Khi chuyển mục tiêu, mô hình phải **thích nghi với một thang đo và phương sai hoàn toàn mới**, nên *phần lớn tiến bộ đạt được ở giai đoạn pre-train bị mất*.

**[Ví dụ minh họa của nhóm]** Với cùng một kế hoạch, PostgreSQL có thể báo `cost = 1.250.000` (đơn vị trừu tượng), trong khi latency thực tế là `850 ms`. Mạng nơ-ron pre-train trên cost đã điều chỉnh trọng số lớp cuối để xuất ra giá trị cỡ 10⁶. Khi đổi sang latency, sai số ban đầu cực lớn tạo ra gradient lớn, làm "ghi đè" các trọng số đã học. Hơn nữa, tương quan giữa cost và latency không hoàn hảo, nên thứ tự mà mô hình học từ cost có thể không còn đúng với latency.

**Khuyến nghị (§5.2).** Có hai cách:
1. **Learning-to-rank** [20]: *có thể đổi cost/latency giữa chừng khi dùng mô hình LTR*, vì giá trị thực được chuyển thành **thứ hạng tương đối** của biến mục tiêu, không còn phụ thuộc thang đo.
2. **Kiến trúc xâu chuỗi các mô hình ML** như HybridQO: *mỗi biến mục tiêu được phục vụ bởi một mô hình riêng* trong pipeline.

**[Nhận xét của nhóm]** Lero và LEON dùng LTR (Bảng 1) nên về nguyên tắc ít bị ảnh hưởng bởi vấn đề thang đo, dù vẫn được bài báo liệt kê vào nhóm "pre-train cost rồi chuyển sang latency". Trong khi đó, HybridQO, LQO duy nhất đi theo cách xâu chuỗi, là LQO tốt nhất trong thực nghiệm (§8.2.1). Đây là một gợi ý (chưa phải chứng minh) rằng khuyến nghị §5.2 có cơ sở.

#### 3.3.4 Hệ quả thực nghiệm: huấn luyện lâu hơn không có nghĩa là tốt hơn (§8.2.2)

Thời gian huấn luyện thể hiện rõ nhất hậu quả của thiết kế huấn luyện. Bài báo định nghĩa **thời gian huấn luyện end-to-end** gồm (§8.2.2): (a) thời gian truy vấn DBMS để lấy dữ liệu, (b) thời gian huấn luyện mô hình, (c) thời gian đánh giá mô hình giữa chừng, (d) tiền và hậu xử lý, khởi tạo, sinh artifact. Nói ngắn gọn, đó là *toàn bộ thời gian từ khi bắt đầu đến khi quy trình huấn luyện kết thúc*.

| Phương pháp | JOB | STACK |
|---|---|---|
| PostgreSQL | 0 (không cần train) | 0 |
| Bao | ~2 giờ | ~2 giờ |
| HybridQO | ~20 giờ | 12–14 giờ |
| Neo | 20–40 giờ | 120–140 giờ |
| Balsa | 40–85 giờ | 170–290 giờ |
| LEON | 110–130 giờ | 120–140 giờ |

*(Hình 6, §8.2.2; PT §7.4)*

**Phát hiện ngược trực giác:** *"các phương pháp tốn nhiều thời gian xây dựng và huấn luyện mô hình hơn lại cho kết quả kém hơn"* so với các phương pháp huấn luyện nhanh (§8.2.2). Nguyên nhân chính là **số kế hoạch phải xét**:
- Trên JOB, Neo chạy **4.000–8.000** kế hoạch, Balsa chạy **19.000–21.000** kế hoạch trong PostgreSQL.
- LEON không thực thi phần lớn kế hoạch nó sinh ra, nhưng gọi PostgreSQL để lấy ước lượng cost cho **hàng chục nghìn kế hoạch con**. Riêng việc dự đoán kế hoạch cho truy vấn **29a** (17 bảng, nhiều nhất JOB) đã mất **khoảng 6,5 giờ**. File cache của LEON lên tới **1,7 GB** với JOB và 120 MB với STACK (chú thích 7).

**[Nhận xét của nhóm]** Kết quả này phù hợp với lập luận ở 3.3.1 và 3.3.3: một mô hình phức tạp hơn và huấn luyện lâu hơn **không bù được** các lỗi ở thiết kế pipeline (chọn biến mục tiêu, cách tìm kiếm, cách sinh dữ liệu).

#### 3.3.5 Tóm tắt lỗ hổng (3)

| Vấn đề | LQO | Vi phạm | Khuyến nghị |
|---|---|---|---|
| CV không dùng để chọn mô hình | RTOS | Quy trình chọn mô hình | Tinh chỉnh siêu tham số, kể cả với RL |
| Validation không cố định / "time series" | Balsa, Bao | Kết quả không so sánh được | Holdout cố định [7] |
| Early stopping theo accuracy | LEON | Chỉ số không phù hợp (không biết kế hoạch tối ưu) | Không dùng accuracy |
| Pre-train cost rồi chuyển sang latency trên một mô hình | RTOS, Balsa, Lero, LEON | Khác thang đo và phương sai [2], mất kiến thức pre-train | LTR [20] hoặc xâu chuỗi mô hình (HybridQO) |

---

### 3.4 LỖ HỔNG (4): ĐÁNH GIÁ VÀ RÒ RỈ DỮ LIỆU (§6, §7.2, §8.2.1)

#### 3.4.1 Gốc rễ: đánh giá "data-centric" thay vì "model-centric"

Phần mở đầu (§1, đoạn LQO Evaluation) nêu luận điểm trung tâm:

> Khi mô hình được huấn luyện rồi đánh giá trên một **cách chia train/test không cố định**, phép so sánh trở thành **data-centric (hướng dữ liệu)** chứ không còn **model-centric (hướng mô hình)**. Nói cách khác, *việc chọn cách chia train/test tương quan mạnh với hiệu năng của mô hình*.

Hệ quả: **hiệu năng trên hai lần chia khác nhau cùng một kiểu** (ví dụ hai lần chia ngẫu nhiên) **không thể so sánh với nhau** (§1). Bài báo chỉ ra ví dụ trong Hình 4 và Hình 5.

Mặc dù đã có benchmark tối ưu truy vấn công khai [18], [22], câu hỏi *truy vấn nào làm tập train, truy vấn nào làm tập test* **vẫn còn bỏ ngỏ**. Các nỗ lực đề xuất quy trình đánh giá thống nhất **chỉ mới xuất hiện gần đây** trong [23], [39], [43] (§1).

**Bằng chứng thực nghiệm (§8.2.1; PT §7.2):**
- Trên JOB, Neo và Balsa đạt thời gian end-to-end **nhanh hơn 2–3 lần** ở Random split so với Leave One Out split. Điều này *trái với kỳ vọng* "LOO là dễ nhất".
- Ở cùng kiểu chia, kết quả giữa các split khác nhau rất nhiều. Ví dụ ở Base Query split 1, 3 truy vấn test của Neo và 15 truy vấn (cả train lẫn test) của Balsa bị timeout, trong khi các split BQ khác không gặp vấn đề tương tự.
- Bài báo kết luận: kết quả cho thấy *"tầm quan trọng của cách chia truy vấn để huấn luyện"* (§8.2.1).

#### 3.4.2 Lỗ hổng 4a: chọn tập test có thiên lệch (§6.1)

**Nguyên lý (§6.1).** Train/test split là **nền tảng của mọi phương pháp có giám sát**. Nó tách phần dữ liệu mô hình được thấy khi huấn luyện khỏi phần dùng để kiểm tra khả năng xử lý dữ liệu chưa thấy, tức **đo khả năng tổng quát hóa**.

Bài báo phân tích ba cách chọn tập test đã có trong các nghiên cứu trước:

**(1) Ext-JOB, do Neo [23] đề xuất**
- *Mục đích:* lần đầu kiểm tra khả năng xử lý các truy vấn **khác hẳn** truy vấn gốc của JOB.
- *Vấn đề:* Ext-JOB có thêm các toán tử **không có trong JOB**, như **GROUP BY** hay **ORDER BY**. Do bản chất của merge join [13], *những LQO ưa chuộng phương pháp join này sẽ được lợi khi có ORDER BY* (dữ liệu đã được sắp xếp sẵn).
- *Hậu quả:* phép so sánh giữa các phương pháp **bị lệch một cách không công bằng**.

**(2) JOB-Slow, do Balsa [39] đề xuất**
- *Cách làm:* lấy **19 truy vấn chậm nhất** làm tập test, các truy vấn còn lại làm tập train. Cách chia này *dễ hiểu một cách trực quan*, vì tập trung vào những truy vấn ảnh hưởng nhiều nhất tới tổng thời gian của workload.
- *Vấn đề:* cả 19 truy vấn đều có **≤ 11 join**, trong đó **11 truy vấn có ≤ 6 join**.
- *Vì sao đó là vấn đề:* Hình 2 cho thấy truy vấn có **6–11 join** có thời gian chạy lớn nhất, nên có tiềm năng được tối ưu cao nhất. Nhưng đây cũng chính là vùng mà **các bộ tối ưu không vét cạn thường bị tắt** (GEQO của PostgreSQL mặc định chỉ bật từ 12 bảng). Vì vậy **phương pháp vét cạn vẫn duyệt được toàn bộ không gian kế hoạch** ở vùng này.
- **[Nhận xét của nhóm]** Nói cách khác, JOB-Slow kiểm tra LQO ở vùng mà optimizer truyền thống *mạnh nhất*, nhưng lại bỏ qua vùng nhiều join (≥ 12), nơi heuristic của DBMS yếu và LQO có thể thực sự hữu ích.

**(3) Chia theo số join, do [43] đề xuất**
- *Cách làm:* chia train/test dựa trên số join, ví dụ mọi truy vấn có 3 hoặc 4 join làm tập test, phần còn lại làm tập train.
- *Vấn đề:* **Hình 2** (tr. 1570) là biểu đồ phân tán thời gian thực thi theo số join của toàn bộ JOB. Hồi quy cho **R² = −0,11**, tức *số join là một đại diện không liên quan cho thời gian thực thi*.
- *Hậu quả:* chia truy vấn theo cách này tạo ra những nhóm **không gắn với mục tiêu tối ưu thật sự**, là thời gian thực thi.
- **[Giải thích của nhóm]** R² âm nghĩa là mô hình hồi quy theo số join dự đoán *còn kém hơn* việc luôn đoán bằng giá trị trung bình. Như vậy số join **gần như không có khả năng giải thích** thời gian chạy.

**Khuyến nghị (§6.1).** Đề xuất nhiều **trường hợp biên (edge case)** khi chia train/test để bao phủ các vùng tổng quát hóa khác nhau, cụ thể là **khoảng cách tổng quát hóa (generalization gap)** và **lấy mẫu ngoài phân phối (out-of-distribution)**. Chi tiết ở §7.2.

#### 3.4.3 Lỗ hổng 4b: rò rỉ dữ liệu giữa tập train và tập test (§7.2)

**Nguyên lý (§7.2, tr. 1570–1571).** Hai tập train và test nên chứa dữ liệu từ **phân phối tương tự**, nhưng *phải cẩn thận để tránh rò rỉ thông tin từ tập này sang tập kia*.

**Cơ chế rò rỉ trong JOB và STACK.**
- JOB có 113 truy vấn sinh từ **33 truy vấn gốc**, mỗi gốc có **2–6 biến thể** (1a, 1b, 1c, ...). Các biến thể **dùng chung bảng và join**, chỉ khác filter (xem 2.4.2). STACK cũng theo đúng mẫu này với 16 truy vấn gốc.
- *"Sinh truy vấn từ template tạo ra **tương quan mạnh trong cấu trúc của kế hoạch join tối ưu** với một số truy vấn, nhưng không phải tất cả"* (§7.2).
- **[Giải thích của nhóm]** Nếu 1a nằm trong tập train và 1b nằm trong tập test, mô hình có thể đã "thấy" thứ tự join tốt cho template 1 và chỉ cần **nhớ lại** cấu trúc đó thay vì thực sự tổng quát hóa. Kết quả trên tập test vì thế bị **lạc quan giả tạo**.

**Đề xuất: ba kiểu chia với độ khó tăng dần** (§7.2; **Hình 3**, tr. 1571):

| Kiểu chia | Cách làm (§7.2) | Mức rò rỉ | Độ khó |
|---|---|---|---|
| **(1) Leave One Out Sampling (LOO)** | Lấy **đúng 1 biến thể** của mỗi truy vấn gốc vào tập test; mọi biến thể còn lại vào tập train | **Tối đa:** lượng thông tin từ tập train có thể dùng cho tập test là lớn nhất | **Dễ nhất** |
| **(2) Random Sampling (RND)** | Phân phối ngẫu nhiên mọi truy vấn vào train và test, **bỏ qua quan hệ với truy vấn gốc** | Một phần | **Trung bình**; áp dụng được cho *mọi workload*, kể cả khi không có họ truy vấn gốc |
| **(3) Base Query Sampling (BQ)** | Giữ **mọi biến thể của một truy vấn gốc** cùng nằm trong tập train hoặc cùng nằm trong tập test | **Không:** sự tương đồng trong cùng họ truy vấn không rò sang tập test | **Khó nhất**: mô hình *không thể áp dụng cấu trúc join học từ một biến thể sang biến thể khác* |

**Minh họa theo Hình 3** (5 truy vấn gốc đầu tiên của JOB; Tr = train, **Te** = test):

| Truy vấn | 1a | 1b | 1c | 1d | 2a | 2b | 2c | 2d | 3a | 3b | 3c | 4a | 4b | 4c | 5a | 5b | 5c |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **LOO** (dễ) | Tr | **Te** | Tr | Tr | Tr | Tr | Tr | **Te** | Tr | **Te** | Tr | **Te** | Tr | Tr | Tr | Tr | **Te** |
| **RND** (trung bình) | Tr | Tr | **Te** | Tr | Tr | **Te** | Tr | **Te** | Tr | Tr | Tr | **Te** | **Te** | Tr | Tr | Tr | **Te** |
| **BQ** (khó) | Tr | Tr | Tr | Tr | **Te** | **Te** | **Te** | **Te** | **Te** | **Te** | **Te** | Tr | Tr | Tr | **Te** | **Te** | **Te** |

Có thể thấy ở dòng BQ, truy vấn gốc 1 và 4 nằm trọn trong tập train, còn truy vấn gốc 2, 3, 5 nằm trọn trong tập test.

**Hiện thực trong thực nghiệm (§8.1.3).**
- Tỷ lệ **80/20** cho Random split và Base Query split.
- Các split được **lấy mẫu một lần và dùng chung cho mọi phương pháp**, đúng với khuyến nghị "holdout cố định" ở §5.1.
- Với JOB, mỗi kiểu chia có 3 split, tổng cộng **9 split** (Hình 4; PT §6.2). Danh sách chi tiết công bố trong kho mã nguồn.
- Thực nghiệm tăng dần độ khó, từ LOO đến RND rồi đến BQ (§8.2.1).

**Bằng chứng (§8.2.1; PT §7.2).** Ở BQ (khó nhất), Bao chỉ đạt kết quả tương đương PostgreSQL ở **1/3 split**, HybridQO ở **3/3 split**. Neo và Balsa gặp khó khăn rõ rệt ở BQ-1. Điều này *khẳng định độ khó tăng lên* của kiểu chia BQ.

**[Nhận xét của nhóm]** BQ tương đương với **chia theo nhóm (GroupKFold)** trong ML, trong đó "nhóm" là truy vấn gốc. Nếu không nhóm thì các biến thể của cùng một template rơi vào cả hai tập, gây rò rỉ. Đây là cách nhóm diễn giải lại theo thuật ngữ ML, bài báo không dùng thuật ngữ này.

#### 3.4.4 Lỗ hổng 4c: chỉ báo cáo thời gian thực thi, bỏ qua thời gian suy luận (§8.2.1)

**Mô tả.** Bài báo định nghĩa 4 loại thời gian (§8.2.1):
1. **Inference Time:** toàn bộ thời gian LQO dùng để mã hóa truy vấn, duyệt các biến thể kế hoạch, thu thập thông tin cost và chạy mô hình ML để dự đoán.
2. **Planning Time:** thời gian PostgreSQL lập kế hoạch trước khi thực thi. Với LQO chạy như extension bên trong PostgreSQL (Bao), thời gian suy luận thường được tính vào thời gian lập kế hoạch.
3. **Execution Time:** thời gian PostgreSQL thực thi truy vấn và thu kết quả.
4. **End-to-end Execution Time = (1) + (2) + (3)**. Theo tác giả, đây phải là **mục tiêu chính** của tối ưu. Độ trễ mạng không được tính vì LQO không tác động được tới nó.

**Vì sao là lỗ hổng.** Một LQO có thể tìm được kế hoạch thực thi nhanh, nhưng nếu thời gian suy luận quá lớn thì người dùng vẫn phải chờ lâu hơn. Bài báo nhấn mạnh: *"đánh giá phải bao gồm thời gian suy luận, vì nó định hình mạnh thứ hạng giữa các phương pháp so với khi chỉ xét thời gian thực thi"* (§8.2.1).

**Bằng chứng (§8.2.1, Hình 4; PT §7.2):**
- Ở LOO, Bao mất thêm **8,5 giây** để lập kế hoạch, nên **chậm hơn 25%** tính end-to-end dù thời gian thực thi tương đương PostgreSQL (khoảng 30 giây).
- LEON là phương pháp **nhanh thứ tư xét theo thời gian thực thi (58 giây)**, nhưng thời gian suy luận khoảng **9,6 giờ**, nên *không thực tế cho truy vấn tương tác*.
- Ở RND, Bao thực thi trong 25 giây so với 28 giây của PostgreSQL. Tuy nhiên chênh lệch này không có ý nghĩa thống kê, và khi cộng thời gian suy luận và lập kế hoạch thì Bao lại chậm hơn.

**[Nhận xét của nhóm, theo PT §7.4]** Nếu chỉ báo cáo thời gian thực thi, như nhiều bài trước đã làm, thì bức tranh về LQO bị **tô hồng**.

#### 3.4.5 Lỗ hổng 4d: bỏ qua covariate shift (§6.2, §8.3)

**Định nghĩa (§6.2).** Covariate shift là *sự thay đổi trong nội dung CSDL* so với thời điểm phương pháp được huấn luyện.

**Vì sao LQO dễ bị ảnh hưởng (§6.2).**
- **DBMS** xử lý vấn đề này bằng cách **liên tục cập nhật thống kê nội bộ**.
- **Với LQO**, thay đổi nội dung CSDL ảnh hưởng tới **cách truy vấn được mã hóa** và tới **kết quả dự đoán**.
- *Ví dụ của bài báo:* truy vấn tìm phim có năm phát hành sau 2022 sẽ **liên tục tăng kích thước kết quả** khi phim mới được thêm vào DBMS.
- DBMS cũng *không có sự xa xỉ* là tự động cập nhật trọng số mô hình đã huấn luyện. Lựa chọn duy nhất là huấn luyện lại từ đầu hoặc fine-tune (§8.3).

**Thực trạng (§6.2).** Chủ đề này **thường chỉ được nhắc trong phần "hướng phát triển"**. Một số phương pháp như Bao đã bắt đầu thiết kế mã hóa để chống covariate shift, bằng cách **bỏ định danh bảng và cột** (liên hệ 3.2.3 và 3.2.5).

**Bằng chứng: thí nghiệm IMDB-50% (§8.3; PT §8):**
- *Tạo dữ liệu:* giữ **50% số dòng** của bảng `title` bằng **lấy mẫu Bernoulli**, để lượng dữ liệu giảm một nửa nhưng phân phối giá trị tương tự bản gốc. 50% còn lại bị xóa bằng **CASCADE** để đảm bảo toàn vẹn tham chiếu. Bảng `title` được chọn vì đây là bảng duy nhất của IMDB xuất hiện trong *mọi* truy vấn JOB. Sau khi lấy mẫu, các bảng liên quan tới phim và diễn viên giảm khoảng 50%. Thống kê nội bộ của PostgreSQL được cập nhật.
- *Thiết lập:* huấn luyện **Bao-Full** trên IMDB và **Bao-50** trên IMDB-50%, cùng split **BQ-1**. Mục đích là mô phỏng covariate shift theo hướng *thêm dữ liệu* (mô hình học trên dữ liệu nhỏ rồi chạy trên dữ liệu lớn).
- *Kết quả:*
  - Truy vấn **16b** là ngoại lai rõ nhất: **timeout ở 1/4 mô hình Bao-50**, 3 mô hình còn lại chậm hơn Bao-Full **19 giây**.
  - **31c chậm hơn 24 lần** (8,4 giây so với 350 ms), **17a chậm hơn 4,5 lần** (12,2 giây so với 2,7 giây).
  - Ngược lại, một số truy vấn nhanh hơn: 7c (1,9×), 26c (1,6×), 10c (1,3×).
- *Kết luận của bài báo (§8.3):* **việc DBMS cập nhật thống kê (tức ước lượng cardinality) là không đủ để theo kịp một mô hình mới được huấn luyện**. Sự suy giảm hiệu năng cho thấy khó khăn trong tổng quát hóa, nhất là khi gặp các giá trị cardinality lớn hơn chưa từng thấy lúc huấn luyện, tức **out-of-distribution**. Hiện *chưa có giải pháp nào ngoài huấn luyện lại hoặc fine-tune*, nên các phương pháp **có thể cập nhật và huấn luyện lại liên tục** được ưu tiên.

**Khuyến nghị (§6.2).** Các phương pháp tương lai nên **kèm một thí nghiệm đơn giản đo khả năng xử lý covariate shift**, như bài báo đã làm ở §8.3.

**[Nhận xét của nhóm, theo PT §9.2]** Thí nghiệm này chỉ làm với **Bao** trên **một split**, nên khó tổng quát cho các LQO khác.

#### 3.4.6 Tóm tắt lỗ hổng (4)

| Vấn đề | Ví dụ | Vi phạm | Khuyến nghị / giải pháp | Mục |
|---|---|---|---|---|
| Đánh giá data-centric | Neo và Balsa tốt hơn ở RND so với LOO | Kết quả phụ thuộc split, không phụ thuộc mô hình | Holdout cố định, dùng chung cho mọi phương pháp | §1, §8.1.3 |
| Tập test thiên lệch | Ext-JOB, JOB-Slow, chia theo số join | Tập test không đại diện; đại diện không liên quan (R² = −0,11) | Các edge case: generalization gap, out-of-distribution | §6.1, Hình 2 |
| Rò rỉ dữ liệu | Biến thể 1a ở tập train, 1b ở tập test | Thông tin cấu trúc join rò sang tập test | 3 kiểu chia LOO / RND / BQ | §7.2, Hình 3 |
| Bỏ qua thời gian suy luận | LEON: 58 s thực thi nhưng ~9,6 giờ suy luận | Chỉ số đánh giá không end-to-end | Báo cáo inference + planning + execution | §8.2.1 |
| Bỏ qua covariate shift | Bao-50: 31c chậm hơn 24× | Không kiểm tra out-of-distribution | Thí nghiệm covariate shift bắt buộc | §6.2, §8.3 |

---

### 3.5 Mối liên hệ giữa 4 lỗ hổng: lỗi lan truyền qua pipeline

**[Tổng hợp của nhóm, dựa trên §1–§7]** Bốn lỗ hổng không độc lập mà **khuếch đại lẫn nhau** theo chiều của pipeline:

```
(1) Sinh dữ liệu ── nhãn y nhiễu (cache), D không khớp kế hoạch thật (dynamic opt.),
        │            miền dữ liệu bị cắt (tắt join/scan, bỏ bushy)
        ▼
(2) Mã hóa ──────── nhiều truy vấn trùng vector D, ánh xạ (D, y) 1-nhiều
        │
        ▼
(3) Huấn luyện ──── học trên dữ liệu mâu thuẫn; validation không cố định;
        │            đổi thang đo cost → latency làm mất kiến thức
        ▼
(4) Đánh giá ────── split có rò rỉ / thiên lệch và chỉ đo thời gian thực thi
                     ⇒ CHE GIẤU các lỗi ở (1)–(3), cho kết quả "đẹp" giả tạo
```

Giai đoạn (4) đặc biệt nguy hiểm vì nó **quyết định chúng ta có phát hiện được lỗi ở (1)–(3) hay không**. Khi framework của bài báo sửa giai đoạn (4) (chia BQ, tính thời gian suy luận, cấu hình thống nhất), lợi thế của nhiều LQO biến mất, và PostgreSQL trở lại vị trí dẫn đầu (§8.2.1).

### 3.6 Bảng tổng hợp toàn bộ

| # | Giai đoạn | Lỗ hổng chính | Nguyên lý ML bị vi phạm | Khuyến nghị cốt lõi | Mục | Tham khảo chính |
|---|---|---|---|---|---|---|
| 1 | Sinh dữ liệu train | Thu hẹp không gian kế hoạch; dynamic optimization; trộn cold/hot cache | Tính tổng quát của miền dữ liệu; bất biến của **D** và **y** | Không tắt toán tử tùy tiện; direct RL; ép hot cache (lần chạy thứ 3) | §3.2, §3.3; §7.3; §8.4–§8.7 | [1], [8], [18], [19], [22], [27], [29] |
| 2 | Mã hóa Query/Plan | Mã hóa bằng một giá trị cardinality; thiếu query encoding | Ánh xạ (D, y) phải 1-1; đặc trưng phải đủ biểu đạt | Embedding và vector hóa filter; mã hóa cả query lẫn plan | §4.1, §4.2; Bảng 1 | [3], [5], [9], [12], [14], [17], [22], [23], [40], [42], [44] |
| 3 | Huấn luyện | Validation không cố định; early stopping theo accuracy; đổi cost → latency | Quy trình chọn mô hình; chỉ số phù hợp; nhất quán thang đo của biến mục tiêu | Tinh chỉnh siêu tham số; holdout cố định; LTR hoặc xâu chuỗi mô hình | §5.1, §5.2; §8.2.2 | [2], [7], [20], [26], [32], [33], [36], [38] |
| 4 | Đánh giá | Đánh giá data-centric; tập test thiên lệch; rò rỉ giữa các biến thể; bỏ qua suy luận; bỏ qua covariate shift | Tập test đại diện và độc lập; đánh giá end-to-end và out-of-distribution | LOO/RND/BQ; thời gian end-to-end; thí nghiệm covariate shift | §6.1, §6.2, §7.2; §8.2.1, §8.3 | [13], [18], [22], [23], [39], [43] |

### 3.7 Nhận xét phản biện về phần lý thuyết của bài báo

**[Nhận xét của nhóm, tổng hợp từ PT §9]**

**Điểm mạnh:**
- **Góc nhìn mới:** đặt LQO vào khung pipeline ML chuẩn, nhờ đó phát hiện lỗi ở những giai đoạn ít ai để ý, như tính bất biến của mã hóa và việc đổi biến mục tiêu giữa chừng (PT §9.1).
- **Các khuyến nghị có cơ sở trong lý thuyết ML,** đều được trích dẫn từ tài liệu nền tảng: [7], [17], [20], [30], [32], [38].
- **Lý thuyết đi kèm bằng chứng:** các lỗ hổng ở giai đoạn (1) và (4) được minh chứng bằng ablation (§8.3–§8.7).

**Hạn chế:**
- **Khuyến nghị ở §3–§5 phần lớn mang tính lý thuyết.** Bài báo chưa kiểm chứng bằng thực nghiệm việc embedding có sửa được lỗi bất biến, direct RL có tránh được dynamic optimization, hay LTR có giữ được kiến thức pre-train hay không (PT §9.2).
- **Bài báo chưa tự áp dụng hết khuyến nghị của mình,** chẳng hạn chưa tinh chỉnh siêu tham số cho từng LQO (PT §9.2).
- **Chỉ đo ở hot cache,** hợp lý cho tính nhất quán nhưng không phản ánh workload có cold cache (PT §9.2).
- **Ablation covariate shift chỉ làm với Bao trên một split** (PT §9.2).

---

## CHƯƠNG 4. TIỂU KẾT

Phần này đã trình bày bối cảnh, cơ sở lý thuyết và phân tích chi tiết 4 lỗ hổng mà bài báo chỉ ra trong pipeline ML của các bộ tối ưu truy vấn học máy:

1. **Sinh dữ liệu (§3):** QOP không có dữ liệu train sẵn. Dữ liệu sinh ra dễ bị **thu hẹp miền** (tắt toán tử, bỏ cây bushy) và **vi phạm bất biến** ở cả phía đầu vào (dynamic optimization) lẫn phía đầu ra (trạng thái cache).
2. **Mã hóa (§4):** mã hóa filter bằng một giá trị cardinality, hoặc bỏ hẳn query encoding, làm ánh xạ (D, y) trở thành **1-nhiều**, đồng thời làm mất **ngữ cảnh toàn cục** của truy vấn.
3. **Huấn luyện (§5):** quy trình validation không chuẩn (không cố định, dùng accuracy) và việc **đổi biến mục tiêu từ cost sang latency** trên cùng một mô hình làm huấn luyện kém ổn định. Thực nghiệm cho thấy huấn luyện lâu hơn không cho kết quả tốt hơn.
4. **Đánh giá (§6, §7.2):** đánh giá **data-centric**, tập test **thiên lệch**, **rò rỉ** giữa các biến thể của cùng một template, bỏ qua **thời gian suy luận** và **covariate shift**. Những lỗi này che giấu các vấn đề ở ba giai đoạn trước.

Thông điệp chung của bài báo: **lợi thế mà các LQO báo cáo phần lớn có thể đến từ cách xây dựng pipeline và cách đánh giá, chứ không hẳn từ mô hình.** Muốn LQO thật sự cạnh tranh được với bộ tối ưu truyền thống, cần **thay đổi về phương pháp luận** ở cả 4 giai đoạn, không chỉ thay một mô hình mạnh hơn (§1, §9; PT §9.3). Đây là cơ sở để các phần tiếp theo của báo cáo trình bày framework benchmark end-to-end (§7) và kết quả thực nghiệm (§8).

---

## PHỤ LỤC A. THUẬT NGỮ

| Thuật ngữ | Nghĩa | Mục |
|---|---|---|
| **QOP** (Query Optimization Problem) | Bài toán chọn kế hoạch thực thi tối ưu cho một truy vấn | §1 |
| **LQO** (Learned Query Optimizer) | Bộ tối ưu truy vấn dùng học máy | §1, §2 |
| **NP-khó** | Lớp bài toán chưa có thuật toán giải chính xác trong thời gian đa thức | §1 [37] |
| **Kế hoạch logic / vật lý** | Thứ tự join / thứ tự join kèm thuật toán join và scan cụ thể | Hình 1 |
| **Left-deep / bushy** | Cây join có nhánh phải luôn là bảng đơn / cây có cả hai nhánh có thể là join con | §8.7 |
| **Cardinality** | Số dòng (ước lượng) mà một toán tử trả về | §3.3.1, §4.1 |
| **Cost / Latency** | Chi phí ước lượng của cost model / thời gian chạy thực tế | §5.2 |
| **GEQO** | Genetic Query Optimizer của PostgreSQL, mặc định bật từ 12 bảng | §7.1, §8.5 |
| **pg_hint_plan** | Extension của PostgreSQL để ép kế hoạch bằng hint | §3.3.1 [27] |
| **Hint set** | Tập lệnh bật/tắt loại join/scan (Bao) | §2 |
| **Dynamic optimization** | DBMS thay đổi kế hoạch trong lúc thực thi | §3.3.1 [1] |
| **Hot / cold cache** | Dữ liệu đã nằm trong bộ đệm / phải đọc lại từ đầu | §3.3.2 |
| **Principle of invariance** | Cùng đầu vào thì phải cùng đầu ra | §1 (chú thích 3), §4.1 [17] |
| **Query encoding / Plan encoding** | Mã hóa thông tin độc lập với cách thực thi / thông tin từ kế hoạch vật lý | §4.1, Bảng 1 |
| **Query-driven / Data-driven** | Học từ truy vấn / học trực tiếp từ dữ liệu | §4 [12, 40] |
| **Tree-CNN / Tree-LSTM** | Mạng nơ-ron xử lý kế hoạch dạng cây | §5 [26, 33] |
| **Learning-to-rank (LTR)** | Học thứ hạng tương đối thay vì giá trị tuyệt đối | §5.2 [20] |
| **Direct RL** | RL tối ưu trực tiếp hàm mục tiêu, không mô hình hóa môi trường | §3.3.1 [8] |
| **Overfitting** | Tốt trên tập train nhưng kém trên tập validation | §5.1 [38] |
| **Holdout cố định** | Tập kiểm tra không đổi giữa các lần chạy | §5.1 [7] |
| **Data leakage** | Thông tin từ tập train lọt sang tập test | §7.2 |
| **LOO / RND / BQ** | Leave One Out / Random / Base Query sampling | §7.2, Hình 3 |
| **Covariate shift** | Phân phối dữ liệu thay đổi sau khi huấn luyện | §6.2, §8.3 |
| **Data-centric / Model-centric** | Kết quả phụ thuộc vào cách chia dữ liệu / phụ thuộc vào chất lượng mô hình | §1 |
| **End-to-end execution time** | Thời gian suy luận + lập kế hoạch + thực thi | §8.2.1 |

---

## PHỤ LỤC B. TÀI LIỆU THAM KHẢO

**Tài liệu chính**

Lehmann, C., Sulimov, P., Stockinger, K. (2024). *Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective.* Proceedings of the VLDB Endowment 17(7): 1565–1577. doi:10.14778/3654621.3654625

**Tài liệu do bài báo dẫn** *(giữ nguyên số thứ tự trong REFERENCES của bài báo, tr. 1577)*

| Số | Tài liệu | Dùng ở mục (báo cáo này) |
|---|---|---|
| [1] | R. Avnur, J. M. Hellerstein (2000). *Eddies: Continuously Adaptive Query Processing.* SIGMOD Rec. 29(2), 261–272 | 3.1.4 |
| [2] | J. Brownlee (2020). *Data preparation for machine learning.* Machine Learning Mastery | 3.3.3 |
| [3] | T. Chen, J. Gao, H. Chen, Y. Tu (2023). *LOGER: A Learned Optimizer Towards Generating Efficient and Robust Query Execution Plans.* PVLDB 16(7), 1777–1789 | 2.2.3, 3.2 |
| [4] | X. Chen et al. (2023). *LEON: A New Framework for ML-Aided Query Optimization.* PVLDB 16(9), 2261–2273 | 2.2.3, 3.1, 3.2, 3.3 |
| [5] | V. P. Dwivedi, X. Bresson (2021). *A Generalization of Transformer Networks to Graphs.* arXiv:2012.09699 | 2.3.3, 3.2.4 |
| [7] | I. Goodfellow, Y. Bengio, A. Courville (2016). *Deep Learning.* MIT Press | 2.3.5, 3.3.2 |
| [8] | Y. Guan et al. (2021). *Direct and indirect reinforcement learning.* arXiv:2112.10600 | 2.3.2, 3.1.4 |
| [9] | I. Guyon, A. Elisseeff (2006). *An Introduction to Feature Extraction.* Springer, 1–25 | 3.2.4 |
| [10] | Y. Han et al. (2022). *Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation.* VLDB 15(4) | 2.4.1 |
| [11] | J. Heitz, K. Stockinger (2019). *Join query optimization with deep reinforcement learning algorithms.* arXiv:1911.11689 | 2.2.2 |
| [12] | B. Hilprecht et al. (2020). *DeepDB: Learn from Data, Not from Queries!* PVLDB 13(7), 992–1005 | 3.2.1 |
| [13] | M. Kacimi, T. Neumann (2009). *System R (R\*) Optimizer.* Springer, 2900–2905 | 3.4.2 |
| [14] | T. N. Kipf, M. Welling (2017). *Semi-Supervised Classification with Graph Convolutional Networks.* ICLR | 2.3.3, 3.2.4 |
| [15] | S. Krishnan et al. (2018). *Learning to Optimize Join Queries With Deep Reinforcement Learning* (DQ) | 2.2.2 |
| [16] | S. Krishnan et al. (2018). *Learning to optimize join queries with deep reinforcement learning.* arXiv:1808.03196 | 2.2.2 |
| [17] | J. P. La Salle (1976). *The stability of dynamical systems.* SIAM | 2.3.6, 3.2.3 |
| [18] | V. Leis et al. (2015). *How good are query optimizers, really?* PVLDB 9(3), 204–215 (JOB) | 2.4, 3.1.3, 3.4.1 |
| [19] | J. J. Levandoski, P.-Å. Larson, R. Stoica (2013). *Identifying hot and cold data in main-memory databases.* ICDE, 26–37 | 3.1.5 |
| [20] | T.-Y. Liu (2009). *Learning to Rank for Information Retrieval.* Found. Trends Inf. Retr. 3(3), 225–331 | 2.3.4, 3.3.3 |
| [21] | H. B. Mann, D. R. Whitney (1947). *On a Test of Whether one of Two Random Variables is Stochastically Larger than the Other.* Ann. Math. Stat. 18(1), 50–60 | 3.1.3 |
| [22] | R. Marcus et al. (2021). *Bao: Making learned query optimization practical.* SIGMOD, 1275–1288 (cũng là nguồn của STACK) | 2.2.3, 2.4, 3.1.3, 3.2, 3.3, 3.4 |
| [23] | R. Marcus et al. (2019). *Neo: A Learned Query Optimizer.* PVLDB 12(11) | 2.2.3, 3.2.3, 3.4.1, 3.4.2 |
| [24] | R. Marcus, O. Papaemmanouil (2018). *Deep Reinforcement Learning for Join Order Enumeration* (ReJOIN). aiDM | 2.2.2 |
| [25] | R. Marcus, O. Papaemmanouil (2018). *Towards a Hands-Free Query Optimizer through Deep Learning.* | 2.2.2 |
| [26] | L. Mou et al. (2016). *Convolutional Neural Networks over Tree Structures for Programming Language Processing.* AAAI, 1287–1293 | 2.3.3, 3.3.1 |
| [27] | Nippon Telegraph and Telephone Corporation (2012). *pg_hint_plan Documentation.* | 2.1.4, 3.1.4 |
| [28] | D. Petković (2011). *Dynamic Programming Algorithm vs. Genetic Algorithm: Which is Faster?* Springer, 483–488 | 2.1.4 |
| [29] | E. Rogov (2022). *Queries in PostgreSQL: Sort and Merge.* PostgresPro blog | 3.1.3 |
| [30] | S. Russell, P. Norvig (2010). *Artificial Intelligence: A Modern Approach* (3rd ed.). Prentice Hall | 1.3 |
| [32] | R. S. Sutton, A. G. Barto (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press | 2.3.2, 3.3.2 |
| [33] | K. S. Tai, R. Socher, C. D. Manning (2015). *Improved Semantic Representations From Tree-Structured Long Short-Term Memory Networks.* ACL, 1556–1566 | 2.3.3, 3.3.1 |
| [34] | The PostgreSQL Global Development Group (2023). *Genetic Query Optimizer (GEQO) in PostgreSQL.* | 2.1.4 |
| [35] | Transaction Processing Performance Council (2023). *TPC Benchmarks Overview.* | 2.4.1 |
| [36] | L. Wan et al. (2013). *Regularization of Neural Networks using DropConnect.* ICML, PMLR 28, 1058–1066 | 2.3.5, 3.3.2 |
| [37] | C. Wang, M.-S. Chen (1996). *On the complexity of distributed query optimization.* IEEE TKDE 8(4), 650–662 | 1.1 |
| [38] | G. I. Webb (2010). *Overfitting.* Springer, 744 | 2.3.5, 3.3.2 |
| [39] | Z. Yang et al. (2022). *Balsa: Learning a Query Optimizer Without Expert Demonstrations.* SIGMOD, 931–944 | 2.2.3, 3.1, 3.3, 3.4.2 |
| [40] | Z. Yang et al. (2020). *NeuroCard: One Cardinality Estimator for All Tables.* PVLDB 14(1), 61–73 | 3.2.1 |
| [41] | X. Yu, C. Chai, G. Li, J. Liu (2022). *Cost-based or learning-based? A hybrid query optimizer for query plan selection* (HybridQO). PVLDB 15(13), 3924–3936 | 2.2.3, 3.3.3 |
| [42] | X. Yu, G. Li, C. Chai, N. Tang (2020). *Reinforcement learning with tree-LSTM for join order selection* (RTOS). ICDE, 1297–1308 | 2.2.3, 3.2.3, 3.3.2 |
| [43] | Y. Zhang, Y. Chronis, J. M. Patel, T. Rekatsinas (2023). *Simple Adaptive Query Processing vs. Learned Query Optimizers: Observations and Analysis.* PVLDB 16(9), 2962–2975 | 2.2.3, 3.1.5, 3.4.2 |
| [44] | R. Zhu et al. (2023). *Lero: A Learning-to-Rank Query Optimizer.* arXiv:2302.06873 | 2.2.3, 2.4.1, 3.2 |
