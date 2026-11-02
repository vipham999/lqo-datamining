# Bộ tối ưu truy vấn học máy của bạn có hoạt động như bạn mong đợi? Một góc nhìn từ học máy

> **Bản dịch tiếng Việt** của bài báo *"Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective"*
> — Claude Lehmann\*, Pavel Sulimov\*, Kurt Stockinger (Zurich University of Applied Sciences, Winterthur, Thụy Sĩ).
> PVLDB, 17(7): 1565–1577, 2024. doi:10.14778/3654621.3654625
>
> Bài gốc được cấp phép **CC BY-NC-ND 4.0**. Bản dịch này chỉ dùng cho mục đích học tập cá nhân / nội bộ nhóm,
> không phát hành công khai. Khi trích dẫn, hãy trích dẫn bài gốc.
>
> **Quy ước dịch:** thuật ngữ chuyên ngành được giữ tiếng Anh trong ngoặc ở lần xuất hiện đầu tiên; các tên riêng
> (Neo, Bao, Balsa, LEON, HybridQO, JOB, STACK, PostgreSQL…) và tên tham số giữ nguyên. Số thứ tự tài liệu tham
> khảo `[n]` giữ như bài gốc. Hình vẽ không được chép lại, chỉ dịch chú thích và mô tả nội dung chính.
>
> \* Hai tác giả đóng góp ngang nhau.

---

## TÓM TẮT

Sự bùng nổ hiện nay của các bộ tối ưu truy vấn học máy (learned query optimizer – LQO) không chỉ được giải thích bởi
sự tiến bộ liên tục của các phương pháp học sâu (deep learning – DL), mà còn bởi việc bài toán tối ưu truy vấn (query
optimization problem – QOP) có thể được phát biểu một cách đơn giản thành một bài toán học máy (machine learning – ML).
Ý tưởng thường là thay thế các phương pháp quy hoạch động (dynamic programming) – vốn phổ biến để giải QOP – bằng
những phương pháp mạnh hơn như học tăng cường (reinforcement learning). Tuy nhiên, một sự "thay đổi cuộc chơi" nhanh
như vậy trong lĩnh vực QOP không thể không để lại hệ quả: các phần khác của quy trình ML (ML pipeline), ngoài việc
phát triển mô hình dự đoán, vẫn còn nhiều tiềm năng cải thiện. Chẳng hạn, các LQO khác nhau tự đặt ra những ràng buộc
riêng khi sinh dữ liệu huấn luyện từ truy vấn, dùng cách chia train/validation tùy ý, và đánh giá trên một cách chia
tùy chọn các truy vấn của benchmark.

Trong bài báo này, chúng tôi cố gắng chuẩn hóa ML pipeline dùng để đánh giá các LQO bằng cách giới thiệu một *khung
benchmark đầu-cuối (end-to-end benchmarking framework)* mới. Ngoài ra, chúng tôi dẫn dắt người đọc qua từng giai đoạn
khoa học dữ liệu trong ML pipeline và đưa ra những nhận định mới từ góc nhìn học máy, có xét đến các đặc thù của QOP.
Cuối cùng, chúng tôi thực hiện một *đánh giá chặt chẽ các LQO hiện có, cho thấy PostgreSQL vượt trội các LQO này trong
hầu hết các thí nghiệm, tùy thuộc vào cách chia train/test*.

**Tính sẵn có của artifact (PVLDB Artifact Availability):** Mã nguồn, dữ liệu và/hoặc các artifact khác được công bố
tại https://github.com/edualc/lqo_ml_perspective.

---

## 1. GIỚI THIỆU

Trong thập kỷ qua, các phương pháp học máy (ML) đã lấn át mạnh mẽ các phương pháp tối ưu truy vấn cổ điển. Với tổng
cộng 𝑂(𝑛!) kế hoạch logic (logical plan) có thể có trong trường hợp xấu nhất – đối với các truy vấn có đồ thị join là
một clique gồm 𝑛 bảng – bài toán được xếp vào loại NP-khó (NP-hard) [37]. Điều này có nghĩa là các phương pháp vét cạn
không thể giải bài toán khi số lượng join lớn¹, do đó cần đến các cách tiếp cận heuristic.

> **Hình 1: So sánh bộ tối ưu truy vấn cổ điển và bộ tối ưu truy vấn học máy (LQO)** – lần lượt ở nửa trên và nửa
> dưới. Các giai đoạn (1) Sinh dữ liệu huấn luyện (Training Data Generation), (3) Huấn luyện LQO (LQO Training) và (4)
> Đánh giá LQO (LQO Evaluation) là các thành phần chính của *Khung benchmark đầu-cuối* của chúng tôi. Cùng với giai
> đoạn (2) Mã hóa truy vấn & kế hoạch (Query & Plan Encoding), chúng tạo thành ML pipeline điển hình của một LQO.
>
> *(Mô tả hình: Nửa trên – bộ tối ưu cổ điển: câu SQL → biểu diễn dữ liệu bằng các kế hoạch logic và kế hoạch vật lý →
> ra quyết định bằng tối ưu chính xác (exact optimization) hoặc tối ưu di truyền (genetic optimization), dựa trên mô
> hình chi phí (cost model) → kế hoạch được chọn → kết quả SQL. Nửa dưới – LQO: câu SQL → mã hóa truy vấn & kế hoạch
> thành vector → mô hình dự đoán → kế hoạch được chọn; bên dưới là khung benchmark gồm sinh dữ liệu huấn luyện, huấn
> luyện LQO và đánh giá LQO.)*

Trong Hình 1, chúng tôi so sánh các pipeline điển hình của bộ tối ưu truy vấn cổ điển và bộ tối ưu truy vấn học máy.
*Cách tiếp cận cổ điển*, được cài đặt bên trong hệ quản trị cơ sở dữ liệu (DBMS), gồm các giai đoạn biểu diễn truy vấn
thông qua kế hoạch logic và kế hoạch vật lý, tiếp theo là tìm kiếm kế hoạch tối ưu bằng các ước lượng của mô hình chi
phí dựa trên cardinality. Bên cạnh các phương pháp dựa trên quy hoạch động, các thuật toán di truyền [34] cũng được sử
dụng vì chúng đã được chứng minh là hiệu quả hơn với các truy vấn có số lượng join lớn [28].

Phần dưới của Hình 1 thể hiện *bộ tối ưu truy vấn học máy* (LQO) – xu hướng mới nhất cho tối ưu truy vấn đầu-cuối.
Các cách tiếp cận này đòi hỏi một pipeline phức tạp hơn do sử dụng các phương pháp ML. Nhìn từ *góc độ ML*, pipeline
nên gồm các giai đoạn: (1) sinh dữ liệu huấn luyện, (2) mã hóa truy vấn & kế hoạch, (3) huấn luyện mô hình ML, và (4)
đánh giá mô hình ML. Việc vi phạm các nguyên tắc lý thuyết của ML [30] ở mỗi giai đoạn, cùng với việc thiếu một khung
thống nhất có thể tái lập, khiến hiện nay *không thể so sánh công bằng kết quả của các LQO*.

Chúng tôi xin mô tả ngắn gọn những gì có thể sai ở mỗi giai đoạn – tức là những thách thức chính của ML pipeline cho
LQO, cả từ góc độ khoa học dữ liệu lẫn kỹ thuật – và cách chúng tôi giải quyết chúng, đó cũng là các đóng góp của bài
báo này.

**Sinh dữ liệu huấn luyện.**² *Khi không có sẵn dữ liệu huấn luyện dùng ngay cho việc benchmark, sẽ nảy sinh cơ hội
tạo dữ liệu bị thiên lệch.* Với LQO, chúng tôi nhận thấy rằng trong các benchmark phổ biến như JOB [18], chỉ có các
truy vấn được cung cấp dưới dạng câu lệnh SQL. Vấn đề then chốt là các câu lệnh này không thể được dùng trực tiếp làm
đầu vào cho mô hình ML nếu không truy vấn cơ sở dữ liệu (CSDL) và trích xuất siêu dữ liệu như cardinality hay thời gian
thực thi. Điều này tạo ra khoảng cách giữa dữ liệu benchmark được cung cấp và các đặc trưng thực sự dùng để huấn luyện
LQO – vốn phụ thuộc mạnh vào các điều kiện tham số khi truy vấn CSDL.

<u>Đóng góp:</u> *Chúng tôi thảo luận các hạn chế chung có thể cản trở quá trình tạo dữ liệu huấn luyện tương đương
trong Mục 3.*

**Mã hóa truy vấn & kế hoạch.** *Mã hóa truy vấn theo cách vi phạm nguyên tắc bất biến (principle of invariance)³ sẽ
dẫn đến hiệu năng không nhất quán.* Khi các truy vấn khác nhau được mã hóa bằng độ chọn lọc (selectivity) của cột, có
thể xảy ra trường hợp những phần lớn của vector mã hóa (thậm chí toàn bộ vector) giống hệt nhau. Lý do là nhiều tổ hợp
bộ lọc cho ra cùng một selectivity. Vì vậy, mô hình có thể bị ảnh hưởng bởi sự không khớp giữa đặc trưng và biến mục
tiêu, và chỉ hoạt động tốt nếu sự không nhất quán này được giảm thiểu.

<u>Đóng góp:</u> *Chúng tôi chẩn đoán các vấn đề về tính bất biến trong từng phương pháp cụ thể và đưa ra khuyến nghị
mã hóa trong Mục 4.*

**Huấn luyện LQO.** *Đi ngược các kỹ thuật huấn luyện cơ bản và áp dụng sai các mô hình toán học khiến mô hình ML của
bạn hoạt động không như mong đợi.* Các mô hình DL phức tạp rất khó huấn luyện, khiến việc tinh chỉnh siêu tham số
(hyperparameter tuning) và các quy trình kiểm định (validation) trở thành nền tảng để đạt năng lực dự đoán cao. Hơn
nữa, việc đưa thêm các cơ chế toán học bổ sung có thể gây tác dụng phụ, ảnh hưởng tiêu cực đến bản thân quá trình
huấn luyện và, kéo theo đó, đến hiệu năng truy vấn.

<u>Đóng góp:</u> *Chúng tôi đề xuất các cải tiến để quá trình huấn luyện các phương pháp LQO ổn định và đáng tin cậy
hơn trong Mục 5.*

**Đánh giá LQO.** *Khi mô hình được huấn luyện rồi đánh giá trên một cách chia train/test không cố định, việc so sánh
trở nên lấy dữ liệu làm trung tâm (data-centric) thay vì lấy mô hình làm trung tâm (model-centric)*, tức là lựa chọn
cách chia train/test tương quan mạnh với hiệu năng của mô hình. Ví dụ, hiệu năng trên hai cách chia train/test khác
nhau thuộc cùng một loại (như chia truy vấn ngẫu nhiên) là không thể so sánh được. Các ví dụ cụ thể có thể thấy trong
Hình 4 và Hình 5 ở phần thí nghiệm. Dù đã có các benchmark tối ưu truy vấn công khai như [18] và [22], câu hỏi truy
vấn nào làm dữ liệu train và truy vấn nào làm dữ liệu test vẫn còn bỏ ngỏ. Những nỗ lực đề xuất một quy trình đánh giá
thống nhất chỉ mới xuất hiện gần đây trong [23], [39] và [43].

<u>Đóng góp:</u> *Chúng tôi thống nhất cách chia dữ liệu cho LQO và giới thiệu một quy trình để kiểm tra các mức độ
tổng quát hóa khác nhau trong Mục 6.*

**Khả năng tái lập (Reproducibility).** *Bất kỳ phương pháp ML nào được phát triển trong giới học thuật đều có giá trị
thực tiễn không đáng kể nếu không thể tái lập trên phần mềm và phần cứng bất kỳ.* Khi các phương pháp ML được sử dụng
rộng rãi trong nghiên cứu học thuật, việc làm chủ lĩnh vực tối ưu truy vấn học máy đặt ra nhiều thách thức, vì nó đòi
hỏi thành thạo cả chủ đề cốt lõi của nghiên cứu cơ sở dữ liệu lẫn nhiều lĩnh vực kỹ thuật liên quan. Các cách tiếp cận
này thường cần mã nguồn phức tạp và các mô hình (ML) có tính ngẫu nhiên nội tại. Do đó, khả năng tái lập đang trở thành
mối quan tâm ngày càng lớn trong giới học thuật.

<u>Đóng góp:</u> *Chúng tôi đề xuất một* ***Khung benchmark đầu-cuối*** *– một khung meta-benchmark mới có khả năng
cân bằng các điều kiện mà dưới đó các LQO dựa trên ML được huấn luyện và kiểm thử, bảo đảm tính nhất quán khi so sánh,
trong Mục 7.*

<u>Đóng góp chính:</u> Chúng tôi thực hiện một đánh giá toàn diện các LQO hiện có bằng khung benchmark đầu-cuối của
mình trong Mục 8. **Kết quả của chúng tôi cho thấy các LQO hiện tại không tốt hơn PostgreSQL một cách có hệ
thống.** Những phát hiện này cho thấy *cần có nghiên cứu mới để LQO có thể cạnh tranh* với các cách tiếp cận truyền
thống hơn – và không chỉ trong một số trường hợp cụ thể.

Bài báo được tổ chức như sau: Đầu tiên, chúng tôi điểm qua ngắn gọn các phương pháp LQO gần đây trong Mục 2. Sau đó,
chúng tôi phân tích các giai đoạn khoa học dữ liệu trong ML pipeline khi áp dụng cho tối ưu truy vấn, không chỉ thảo
luận các trở ngại có thể gặp ở mỗi giai đoạn mà còn đề xuất cách khắc phục thông qua các khuyến nghị thực tiễn (Mục 3
& 6) và lý thuyết (Mục 4 & 5). Dựa trên những thách thức về khả năng tái lập của các phương pháp ML, chúng tôi đề xuất
Khung benchmark đầu-cuối trong Mục 7. Tiếp theo, chúng tôi thực hiện một đánh giá thực nghiệm chi tiết các LQO được
công bố gần đây từ góc nhìn ML trong Mục 8. Cuối cùng, chúng tôi kết luận bài báo trong Mục 9.

---

¹ PostgreSQL từ bỏ các phương pháp vét cạn với các truy vấn có từ 12 phần tử `FROM` trở lên.
² Các nhận định về dữ liệu huấn luyện cũng áp dụng cho dữ liệu validation và test.
³ Chúng tôi phát biểu nguyên tắc bất biến [17] trong sinh dữ liệu như sau: *Khi được cho cùng một đầu vào, hệ thống
sinh dữ liệu phải trả về cùng một đầu ra.*

---

## 2. CÁC NGHIÊN CỨU LIÊN QUAN

Trước khi các LQO đầu-cuối xuất hiện, đã có những tiến bộ đáng kể trong việc dùng các phương pháp ML hiện đại cho tối
ưu truy vấn. Ví dụ, DQ [15], ReJOIN [24, 25] và các công trình khác [11, 16] áp dụng học tăng cường (RL) theo chiến
lược khám phá–khai thác (exploration–exploitation) với mục tiêu tìm thứ tự join tối ưu. Các phương pháp này dùng một
mô hình chi phí để tạo ra phần thưởng "điểm join" (join score) cho tác tử học (learning agent).

LQO đầu-cuối đầu tiên là **Neo** [23], dùng một mạng nơ-ron (neural network – NN) để ước lượng độ trễ (latency) của
toàn bộ kế hoạch truy vấn khi đầu vào là một kế hoạch con (sub-plan). Kế hoạch tối ưu được dự đoán bằng tìm kiếm cây
tham lam (greedy tree search) trong không gian join và scan, kết hợp xây dựng kế hoạch từ dưới lên một cách tuần tự.

**RTOS** [42] giả định đồ thị join được xây dựng như một chuỗi các phép join giữa hai bảng, bỏ qua các phép scan, và
áp dụng mạng nơ-ron đồ thị (graph NN) để huấn luyện một tác tử RL. Kế hoạch truy vấn dự đoán được xây dựng tương tự
Neo, nhưng dùng tìm kiếm theo chiều sâu (depth-first search).

**Bao** [22] nằm phía trên bộ tối ưu truy vấn của PostgreSQL, điều khiển luồng thực thi bằng cách bật hoặc tắt một tập
con các phép join và scan. Các tập con này được gọi là *tập gợi ý (hint set)*; Bao không cung cấp thứ tự join đầy đủ
cũng như loại scan nào dùng cho bảng nào, mà chỉ khuyên những phép toán nào không nên dùng.

**Balsa** [39] dựa trên cùng kiến trúc với Neo. Tuy nhiên, nó đưa vào một số sửa đổi trong pipeline huấn luyện: nó
tiền huấn luyện (pre-train) bằng các ước lượng của mô hình chi phí của DBMS thay vì độ trễ thực tế, nó dùng timeout khi
thực thi truy vấn, và nó không lấy mẫu dữ liệu huấn luyện từ bộ đệm phát lại (replay buffer) mà dùng các điểm dữ liệu
sinh ra từ trạng thái mới nhất của mạng nơ-ron.

**Lero** [44] phát biểu bài toán thành một tác vụ học xếp hạng (learning-to-rank – LTR) và sinh nhiều kế hoạch truy
vấn ứng viên từ DBMS bằng cách thay đổi các ước lượng cardinality nội bộ. Mô-đun so sánh kế hoạch (plan comparator)
chọn kế hoạch tốt hơn trong hai kế hoạch ứng viên được sinh ra, và cũng chọn kế hoạch tối ưu theo cách tương tự khi suy
luận (inference). **LEON** [4] là một phương pháp LTR khác. Khác với Lero, nó vét cạn nhiều kế hoạch vật lý có thể có
theo kiểu quy hoạch động và cắt tỉa chúng trước khi huấn luyện. Việc huấn luyện chỉ diễn ra trên các cặp SQL/kế hoạch
truy vấn được chọn hàng đầu, xếp hạng theo độ trễ và ước lượng độ bất định hậu nghiệm (posterior uncertainty) thu được
từ một mạng nơ-ron Bayes (Bayesian NN).

**LOGER** [3] dùng pipeline mô hình ML về mặt khái niệm của RTOS, nhưng mở rộng không gian hành động cho việc gợi ý thứ
tự join bằng cách thêm loại join. LOGER giới hạn việc gợi ý phép toán, tức là loại join nào không nên dùng, bằng cách
áp dụng 𝜖-beam search để dự đoán kế hoạch.

**HybridQO** [41] dùng kết hợp ước lượng chi phí và độ trễ, giống một số phương pháp khác, nhưng theo cách khác: đầu
tiên nó lấy các kế hoạch ứng viên từ DBMS thông qua hint. Các hint này được lấy từ các tầng trên cùng của cây kế hoạch
truy vấn được khám phá bởi Tìm kiếm cây Monte-Carlo (Monte-Carlo Tree Search – MCTS) với cận tin cậy trên (upper
confidence bound), dùng chi phí làm mục tiêu (chi phí được ước lượng bằng một mạng nơ-ron từ RTOS). Sau đó, cùng kiến
trúc mạng đó được dùng để dự đoán độ trễ và độ bất định từ các kế hoạch ứng viên. Một bộ ước lượng hiệu năng nhiều đầu
(multi-head performance estimator) đưa ra lựa chọn kế hoạch cuối cùng.

Trong bài báo gần đây [43], các tác giả đặt câu hỏi về tính hợp lý của việc huấn luyện những LQO phức tạp và tốn kém
về tính toán. Thay vào đó, họ đề xuất kết hợp *truyền thông tin nhìn trước (look-ahead information passing – LIP)*,
trong đó dùng các kỹ thuật semi-join thích ứng, và các *thuật toán join thích ứng (adaptive join algorithms – AJA)*.
Thuật toán sau kiểm tra trong lúc chạy xem có nên thay một hash join bằng một nested loop join hay không.

Trong bài báo này, chúng tôi không giới thiệu một LQO mới cũng như một phương án cổ điển thay thế. Thay vào đó, chúng
tôi đưa ra *các khuyến nghị để cải thiện LQO* dựa trên *một đánh giá quy mô lớn các LQO hiện có từ góc nhìn ML*.

---

## 3. SINH DỮ LIỆU HUẤN LUYỆN

Thông thường, các bài toán ML có các benchmark công khai với dữ liệu huấn luyện dùng ngay, giống hệt nhau cho mọi người
tham gia. Các benchmark QOP thì khác về dữ liệu được cung cấp: chúng chỉ đóng vai trò nguồn để sinh ra dữ liệu huấn
luyện phù hợp làm đầu vào cho mô hình ML. Điều này khiến toàn bộ ML pipeline dễ bị ảnh hưởng bởi sự không nhất quán
trong quá trình sinh dữ liệu, cụ thể là:

(1) Dữ liệu huấn luyện được sinh ra dưới những ràng buộc không hợp lý sẽ thu hẹp miền các điểm dữ liệu có thể dùng để
huấn luyện và có khả năng làm giảm khả năng tổng quát hóa của mô hình ML. (2) Dữ liệu huấn luyện được sinh ra có thể
dẫn đến các trường hợp cùng một đầu vào lại cho ra đầu ra (hay mục tiêu) khác nhau.

Trong mục này, trước hết chúng tôi giải thích lựa chọn benchmark, rồi thảo luận các vấn đề xung quanh việc sinh dữ
liệu huấn luyện từ benchmark đó.

### 3.1 Lựa chọn tập dữ liệu

Chúng tôi dùng các benchmark JOB [18] và STACK [22] cho mọi thí nghiệm trong bài báo này. Lấy dữ liệu lần lượt từ IMDB
và StackExchange, cả hai tập dữ liệu đều phản ánh những thách thức tự nhiên của các workload thực tế. Hơn nữa, một bài
báo gần đây [44] khẳng định JOB là benchmark khó nhất đối với LQO, và phần lớn các phương pháp hiện nay dùng JOB và/hoặc
STACK. Chúng tôi không dùng benchmark STATS-CEB được đề xuất trong [10], vì ban đầu nó được phát triển cho các thách
thức về ước lượng cardinality chứ không phải cho tối ưu truy vấn đầu-cuối – vốn là trọng tâm của bài báo này. Chúng tôi
cũng không dùng họ benchmark TPC [35], vì chúng có giả định nền về tính đồng đều đa biến (multivariate uniformity), vốn
không tạo ra thách thức hợp lý cho các phương pháp LQO.

### 3.2 Giảm độ phức tạp của kế hoạch truy vấn

Trong quá trình đánh giá các LQO, chúng tôi nhận thấy một số tác giả đề xuất cắt giảm mạnh số lượng kế hoạch vật lý có
thể có, ví dụ bằng cách tắt nested loop join (như đã làm trong [18]). Điều này có thể cải thiện một số truy vấn,
nhưng giải quyết bài toán tối ưu truy vấn bằng một giải pháp phụ thuộc dữ liệu, với cái giá là giảm khả năng tổng quát
hóa. Nhìn chung, chúng tôi quan sát từ một số truy vấn rằng các giới hạn như tắt một số phương thức scan hoặc join cụ
thể, tối ưu không chính xác (non-exact optimization), hoặc giới hạn loại cây join đều có thể làm tăng khả năng tìm ra
một kế hoạch dưới tối ưu.

Ví dụ, cộng đồng PostgresPro [29] đã thảo luận rằng bất kỳ phương thức join nào cũng có thể có lợi thế hơn các phương
thức khác tùy thuộc vào selectivity của các truy vấn con. Các tác giả của [22] đã chỉ ra bằng thực nghiệm rằng tắt
nested loop join trong PostgreSQL có thể cải thiện hiệu năng của truy vấn 16b nhưng làm giảm hiệu năng của truy vấn
24b. Đối với bitmap scan và tid scan, Bộ tối ưu truy vấn di truyền (Genetic Query Optimizer – GEQO), và cây bushy,
chúng tôi cung cấp các thí nghiệm mở rộng đưa ra các phản ví dụ lần lượt trong Mục 8.4, 8.5 và 8.7.

### 3.3 Sinh dữ liệu huấn luyện bất biến

Dữ liệu được dùng làm đầu vào cho các mô hình ML của LQO – tất cả đều có một giá trị phần thưởng (reward) hoặc giá trị
dự đoán – có dạng chính tắc là các cặp (𝐷, 𝑦): 𝐷 là vector các *biến đặc trưng (feature variables)*, gồm hoặc một
tập biến độc lập 𝑋 đối với các phương pháp có giám sát (supervised), hoặc (𝑠, 𝑎, 𝑠′) – lần lượt là tập *trạng thái
(state)*, *hành động (action)* và *hành động tiếp theo (next action)* đối với các phương pháp RL. 𝑦 là *biến mục tiêu
(target variable)*, có thể là *độ trễ truy vấn*, *chi phí*, hoặc *thứ hạng* tùy theo mô hình ML được dùng.

Trong tiểu mục này, chúng tôi thảo luận vì sao cả hai loại biến đều có thể mất tính bất biến trong quá trình sinh dữ
liệu huấn luyện.

#### 3.3.1 Biến đặc trưng: Tối ưu động (Dynamic Optimization)

Đại đa số LQO dùng extension pg_hint_plan [27] để *buộc PostgreSQL thực thi một kế hoạch truy vấn tường minh* thay vì
dùng kế hoạch do bộ tối ưu truy vấn tích hợp sẵn dự đoán.

Tuy nhiên, không nên kỳ vọng rằng kế hoạch kèm hint của nó thực sự được thực thi. Lý do là kế hoạch được cập nhật động
trong khi thực thi [1], gọi là *tối ưu động*. Tất cả các LQO mà chúng tôi đánh giá đều buộc DBMS thực thi kế hoạch của
chúng trong giai đoạn mã hóa kế hoạch, do đó có khả năng huấn luyện trên dữ liệu không chính xác.

Tối ưu động cũng có thể là nguyên nhân gây ra sự khác biệt giữa kế hoạch thực sự được thực thi và kết quả do `EXPLAIN`
trả về. Điều này có nghĩa là các LQO dựa vào ước lượng cardinality từ `EXPLAIN` có thể đưa vào những ước lượng sai lệch
đáng kể.

*Khuyến nghị:* Vấn đề này có thể được giảm thiểu bằng *cách tiếp cận RL trực tiếp (direct RL approach)*, trong đó DBMS
được xem như một "hộp đen". Hàm mục tiêu được tối đa hóa trực tiếp bằng gradient descent mà không cần học xác suất
chuyển trạng thái (tức là hành vi ngẫu nhiên của DBMS) và không cần giải các phương trình Bellman [8].

#### 3.3.2 Biến phụ thuộc: Cache lạnh và cache nóng (Cold vs. Hot Cache)

Nếu một truy vấn được thực thi nhiều lần, thời gian thực thi sẽ giảm do đọc thông tin đã được tính trước từ các lần
chạy trước (cache nóng) thay vì tạo mọi thứ từ đầu (cache lạnh). Chúng tôi muốn tạo ra một tình huống cho kết quả có
thể so sánh và nhất quán với mọi truy vấn. Vì vậy, trạng thái cache nên là hoàn toàn lạnh hoặc hoàn toàn nóng, tức là
khi mọi khả năng cache đã được thực hiện. Không nên cho phép trạng thái cache "ấm" ở giữa.

Tuy nhiên, không hợp lý khi kỳ vọng một tình huống cache hoàn toàn lạnh [19]. Hơn nữa, việc chạy truy vấn với cache
lạnh có công bằng hay không là một câu hỏi mang tính đạo đức, vì nó vô hiệu hóa mọi kỹ thuật tối ưu mà DBMS có dựa trên
bộ đệm cache.

*Khuyến nghị:* Xét đến khả năng tương quan giữa các truy vấn trong các workload như JOB do dùng các template/mẫu gốc,
chúng tôi tin rằng *buộc dùng cache nóng là công bằng hơn*, vì nó giảm ảnh hưởng của các truy vấn đã thực thi trước đó
lên thời gian thực thi của một truy vấn bất kỳ. Cách đạt được cache nóng được thảo luận chi tiết trong Mục 7.3; về mặt
khái niệm, đó là chạy liên tiếp cùng một truy vấn cho đến khi độ trễ hội tụ.

---

## 4. MÃ HÓA TRUY VẤN & KẾ HOẠCH

Trong mục này, chúng tôi thảo luận những thông tin nào có thể được trích xuất từ các truy vấn SQL và kế hoạch vật lý
của chúng để làm đầu vào cho mô hình ML. Hơn nữa, chúng tôi giải thích những nguyên tắc cần tuân theo để các mô hình
LQO được huấn luyện suôn sẻ.

Theo hiểu biết của chúng tôi, các LQO gần đây đều là *phương pháp hướng truy vấn (query-driven)*, trái ngược với các
phương pháp hướng dữ liệu (data-driven) dùng cho ước lượng cardinality [12, 40]. Nói cách khác, LQO dùng truy vấn như
một đại diện không thể thiếu cho dữ liệu nằm bên dưới DBMS. Điều này có nghĩa là lược đồ mã hóa cho một truy vấn cần
vừa giàu biểu đạt vừa bền vững. Bây giờ chúng tôi sẽ thảo luận các *nguyên tắc về tính bền vững và tính biểu đạt của
mã hóa* và cách đạt được chúng.

### 4.1 Tính bền vững của mã hóa (Encoding Robustness)

Bảng 1 tổng hợp các thành phần mã hóa chính được dùng bởi các LQO. Lưu ý rằng chúng tôi phân biệt giữa *mã hóa truy
vấn* (thông tin không phụ thuộc vào cách truy vấn được thực thi) và *mã hóa kế hoạch* (thông tin dựa trên kế hoạch vật
lý). Ví dụ, các thuộc tính văn bản của truy vấn có thể được mã hóa dựa trên cardinality của chúng, hoặc dùng chẳng hạn
word2vec để sinh dạng vector. Hơn nữa, các mã hóa có thể được tổng hợp bằng cách xếp chồng (stacking) hoặc gộp
(pooling), đôi khi kèm thêm các phép biến đổi hậu kỳ.

Chúng tôi nhận thấy Bao [22] và Lero [44] không dùng mã hóa truy vấn mà chỉ dùng mã hóa kế hoạch. Chẳng hạn, Bao không
xác định bảng nào được dùng trong một nút cụ thể của kế hoạch truy vấn, mà chỉ dùng cardinality và chi phí của bảng.
Cách biểu diễn như vậy có lợi thế là ít phụ thuộc lược đồ (schema-agnostic) hơn và dễ huấn luyện lại khi lược đồ CSDL
thay đổi, nhưng nó vi phạm *nguyên tắc bất biến* [17].

Hãy xét các thí nghiệm tưởng tượng sau. Áp dụng các bộ lọc khác nhau trong một truy vấn có thể cho ra cùng một
cardinality cho cùng một bảng. Tương tự, các bảng có cùng cardinality có thể có cùng mã hóa. Trong điều kiện lý tưởng,
chúng ta muốn có một ánh xạ 1-1 duy nhất giữa các biến đặc trưng 𝐷 và độ trễ hoặc chi phí 𝑦 của một truy vấn cùng kế
hoạch của nó. Tuy nhiên, độ trễ truy vấn lại biến động và khác nhau giữa nhiều lần thực thi, nên mã hóa kế hoạch sẽ
dẫn đến ánh xạ 1-nhiều của các cặp (𝐷, 𝑦).

Hơn nữa, ngay cả khi có thêm mã hóa truy vấn làm đầu vào bổ sung, vẫn không thể bảo đảm tính bất biến nếu các thuộc
tính chỉ được mã hóa bằng một giá trị cardinality duy nhất. Như đã thảo luận trong ví dụ trên, áp dụng các bộ lọc khác
nhau cho một cột có thể cho ra cùng một ước lượng cardinality, tức là dẫn đến mất tính bất biến.

*Khuyến nghị:* Để tránh làm hỏng quá trình huấn luyện do không có ánh xạ 1-1 cho các cặp dữ liệu (𝐷, 𝑦), có thể *dùng
embedding thay vì biểu diễn bằng một giá trị đơn lẻ*, ví dụ embedding cho các thuộc tính văn bản như trong Neo (xem
Hình 12 và 13 trong bài báo gốc [23]), và vector hóa tường minh các bộ lọc như trong RTOS [42].

### 4.2 Tính biểu đạt của mã hóa (Encoding Expressiveness)

Tập đặc trưng cuối cùng cần phản ánh rõ cả ngữ cảnh toàn cục lẫn ngữ cảnh cục bộ. Trong tối ưu truy vấn, ngữ cảnh toàn
cục là *truy vấn* (vì nó không thay đổi trong suốt quá trình tìm kiếm trong không gian kế hoạch vật lý), còn ngữ cảnh
cục bộ là *kế hoạch truy vấn*. Khái niệm này bắt nguồn từ Graph CNN [14]. Ý tưởng cơ bản là áp dụng càng nhiều vòng
tích chập (convolution) trong kiến trúc nơ-ron thì embedding của nút đồ thị càng chứa nhiều ngữ cảnh toàn cục của đồ
thị và ít ngữ cảnh cục bộ hơn.

Tiếp nối ý tưởng dùng mạng nơ-ron đồ thị, graph transformer [5] được dùng trong LOGER [3] trong một ngữ cảnh liên quan
để tổng hợp mã hóa truy vấn. Mặt khác, các phương pháp như Bao [22] và Lero [44] thiếu phần mã hóa truy vấn, điều này
làm tăng xác suất hội tụ về một cực tiểu cục bộ [9].

*Khuyến nghị:* Chúng tôi đề xuất *dùng cả mã hóa truy vấn lẫn mã hóa kế hoạch*, điều này sẽ giúp hội tụ tốt hơn.

---

## 5. HUẤN LUYỆN BỘ TỐI ƯU TRUY VẤN HỌC MÁY

Trong mục này, chúng tôi thảo luận cách "bộ não" của LQO hoạt động và những điều kiện cần đáp ứng để chúng hoạt động
như mong đợi. Đặc điểm then chốt của các LQO gần đây là khả năng học toàn bộ quá trình tối ưu truy vấn nhờ các mô hình
ML. Từ Bảng 1 có thể thấy pipeline huấn luyện của các LQO khác nhau đến mức nào. Ví dụ, một kế hoạch truy vấn có cấu
trúc biểu diễn dạng cây dẫn đến hai khả năng xử lý: một số phương pháp xem nó như một ảnh và áp dụng Tree Convolution
[26], số khác xem nó như một chuỗi các cặp nút (tức là văn bản) và áp dụng Tree-LSTM [33]. Tuy nhiên, vẫn chưa có
điểm chung, chẳng hạn về việc phân tích hiệu năng trong khi huấn luyện mô hình hay lựa chọn phương pháp huấn luyện.
Trong mục này, chúng tôi thảo luận các vấn đề phổ biến nhất của LQO ở giai đoạn huấn luyện.

### 5.1 Tránh quá khớp (Overfitting) mô hình ML

Quá khớp là một vấn đề ML điển hình, xảy ra khi hiệu năng của mô hình cải thiện trên dữ liệu huấn luyện nhưng đồng thời
giảm sút trên dữ liệu validation [38]. Từ định nghĩa, rõ ràng các phương pháp dựa trên RL không gặp vấn đề này, vì
chúng học một chính sách (policy) tối ưu bằng cách cực đại hóa hoặc cực tiểu hóa một hàm mục tiêu không dừng
(non-stationary) phụ thuộc vào chính chính sách hành động. Tuy nhiên, các phương pháp RL có thể mắc kẹt ở một chính
sách dưới tối ưu nếu không khám phá đủ [32]. Ngược lại, các phương pháp có giám sát cổ điển dễ hội tụ về một nghiệm dưới
tối ưu.

Để tránh quá khớp, người ta thường áp dụng *tinh chỉnh siêu tham số thông qua kiểm định chéo (cross-validation – CV)*,
*dừng sớm (early stopping)* và *chính quy hóa (regularization)*. Các kỹ thuật chính quy hóa như dropout [36] rất đơn
giản và
làm tăng số lượng siêu tham số cần tinh chỉnh, trong khi các kỹ thuật khác khó điều chỉnh hơn. Trong số các LQO gần
đây, chỉ RTOS áp dụng CV để đo các chỉ số hiệu năng tổng hợp cuối cùng, dù điều này không giúp chọn ra mô hình cuối
cùng. Balsa dùng dừng sớm dựa trên mức cải thiện hiệu năng trên một tập validation không cố định. LEON thực hiện một
quy trình dừng sớm tương tự, nhưng dùng độ chính xác (accuracy) làm chỉ số mục tiêu. Bao dùng kiểm thử liên tục kiểu
"chuỗi thời gian" (time series) của mô hình trên các truy vấn chưa từng thấy.

*Khuyến nghị:* Với các phương pháp RL, vẫn có thể *dùng tinh chỉnh siêu tham số* vì nó cũng giúp cải thiện hiệu năng
chung của mô hình. Với QOP, độ chính xác cho cả chi phí lẫn độ trễ là một chỉ số chất lượng dưới tối ưu, vì chúng ta
không biết trước kế hoạch tối ưu (ít nhất là với các join bậc cao). Do đó, không nên dùng độ chính xác làm tiêu chí
dừng sớm hoặc tiêu chí kiểm định chéo. Dữ liệu giữ lại (holdout) nên cố định (không dùng CV, không dùng "chuỗi thời
gian"), vì phép đo trên đó cần có thể so sánh được [7].

### 5.2 Thay đổi biến mục tiêu trong khi huấn luyện (On-the-Fly)

Tối ưu truy vấn có những đặc thù thú vị về mục tiêu cần tối ưu, có thể là chi phí hoặc độ trễ. Điều này dẫn đến việc
tìm *sự đánh đổi giữa tốc độ* (vì chi phí có thể được ước lượng nhanh bằng một mô hình chi phí tùy ý) *và độ chính xác*
(vì độ trễ cho giá trị chính xác về thời gian thực thi truy vấn). Một số phương pháp như HybridQO tận dụng cả hai bằng
cách trước tiên huấn luyện mô hình gợi ý các kế hoạch dựa trên chi phí, rồi huấn luyện một mô hình khác chọn giữa các
ứng viên dựa trên độ trễ. Đồng thời, các phương pháp như RTOS, Balsa, Lero và LEON cố gắng dùng một mô hình dự đoán duy
nhất, trước tiên tiền huấn luyện bằng chi phí rồi tiếp tục huấn luyện bằng độ trễ. Một vấn đề then chốt của cách tiếp
cận này là độ trễ và chi phí có các tính chất số học rất khác nhau, và mọi tiến bộ đạt được trong giai đoạn tiền huấn
luyện đều bị mất, vì mô hình cần thích nghi với một thang đo và phương sai (tức là độ lệch so với trung bình) hoàn toàn
mới của các giá trị mục tiêu [2].

*Khuyến nghị:* Có thể *thay đổi chi phí và độ trễ ngay trong khi huấn luyện khi dùng mô hình học xếp hạng*, vì các giá
trị thực được chuyển thành thứ hạng tương đối để làm biến mục tiêu [20]. Một cách khác là *dùng kiến trúc nối chuỗi các
mô hình ML* như trong HybridQO, trong đó các biến mục tiêu khác nhau được đưa cho các mô hình khác nhau trong ML
pipeline.

---

**Bảng 1: Các thành phần mã hóa chính của các LQO.** Chúng tôi phân biệt giữa *mã hóa truy vấn* và *mã hóa kế hoạch*.
Cả Bao và LOGER đều đưa ra hint về những loại join không nên dùng. Bao còn đưa ra hint cho loại scan.

| LQO | Ma trận kề¹ | Thuộc tính số² | Thuộc tính văn bản | Tổng hợp mã hóa* | Loại join | Loại scan | Định danh bảng³ | Data+⁴ | Mô hình ML* | Xử lý kế hoạch | Đầu ra mô hình | Kiểm thử* | Tích hợp DBMS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Neo [23] | ✓ | cardinality | word2vec | stacking | ✓ | ✓ | ✓ | - | Regression | Tree-CNN | Plan | Static | - |
| RTOS [42] | ✓ | filters | cardinality | FC + pooling | - | - | ✓ | - | Regression | Tree-LSTM | Plan | CV | - |
| Bao [22] | - | - | - | - | ✓ | ✓ | - | ✓ | Regression | Tree-CNN | Hint set | Time Series | ✓ |
| Balsa [39] | ✓ | cardinality | cardinality | stacking | ✓ | ✓ | ✓ | - | Regression | Tree-CNN | Plan | Static | - |
| Lero [44] | - | - | - | - | ✓ | ✓ | ✓ | ✓ | LTR | Tree-CNN | Plan | Static | ✓ |
| LEON [4] | ✓ | cardinality | cardinality | stacking | ✓ | ✓ | ✓ | - | LTR | Tree-CNN | Plan | Static | - |
| LOGER [3] | ✓ | filters | cardinality | FC + pooling + GT | ✓ | - | ✓ | - | Regression | Tree-LSTM | Hint | Static | - |
| HybridQO [41] | ✓ | cardinality | cardinality | stacking + FC | ✓ | ✓ | ✓ | ✓ | Regression | Tree-LSTM | Plan | Static | - |

*(4 cột đầu sau tên LQO thuộc nhóm **Mã hóa truy vấn**; 3 cột tiếp theo thuộc nhóm **Mã hóa kế hoạch**; 6 cột cuối
thuộc nhóm **Đặc điểm huấn luyện**.)*

¹ Mã hóa one-hot của đồ thị con join cho một truy vấn (con) cụ thể.
² `filters`: mã hóa tường minh các ký hiệu >, =, < cùng giá trị bộ lọc được chuẩn hóa min-max.
³ Mã hóa one-hot các bảng trong lược đồ DBMS.
⁴ Phương pháp có dùng thêm truy vấn (ngoài các truy vấn của benchmark) để sinh dữ liệu huấn luyện hay không.
\* Stacking: ghép nhiều đặc trưng hoặc vector thành một vector duy nhất; Pooling: giảm mẫu theo các chiều không gian
của dữ liệu đầu vào; CV: kiểm định chéo trên JOB; FC: tầng kết nối đầy đủ (fully-connected) trong mạng nơ-ron; GT:
biến đổi đồ thị (graph transformation); LTR: học xếp hạng; Static: cách chia cố định của JOB; Time Series: kiểm thử
liên tục tuần tự trên các truy vấn chưa từng thấy.

---

## 6. ĐÁNH GIÁ BỘ TỐI ƯU TRUY VẤN HỌC MÁY

Trong mục này, chúng tôi trình bày tầm quan trọng của việc chọn đúng tập test, quyết định này ảnh hưởng thế nào đến
hiệu năng đo được của mô hình, và khái niệm dịch chuyển hiệp biến (covariate shift).

### 6.1 Lựa chọn tập test

*Cách chia train/test* là nền tảng của mọi phương pháp có giám sát. Cách chia này được dùng để phân biệt phần dữ liệu
nào mô hình ML được phép thấy trong khi huấn luyện và phần nào được dùng để kiểm tra khả năng hoạt động trên dữ liệu
chưa từng thấy, tức là đo khả năng tổng quát hóa của mô hình.

Workload JOB mở rộng (Ext-JOB) do Neo [23] giới thiệu là nỗ lực đầu tiên nhằm kiểm tra khả năng của mô hình khi xử lý
các truy vấn chưa từng thấy, khác biệt với các truy vấn JOB gốc. Các truy vấn được thêm vào Ext-JOB có thêm những toán
tử không có trong JOB (như GROUP BY hay ORDER BY). Do bản chất của merge join [13], vốn ưa thích phương thức join này,
các LQO có xu hướng được lợi khi có thêm toán tử ORDER BY. Kết quả là việc so sánh giữa các phương pháp khác nhau bị
lệch một cách không công bằng.

Balsa giới thiệu JOB-Slow, trong đó 19 truy vấn chậm nhất tạo thành tập test, còn tất cả các truy vấn khác là tập
train. Cách chia train/test trực quan, dễ hiểu này tập trung vào những truy vấn có ảnh hưởng lớn nhất đến tổng thời
gian thực thi của toàn bộ workload. Tuy nhiên, tất cả 19 truy vấn của tập test JOB-Slow đều có 11 join trở xuống, trong
đó 11 truy vấn chỉ có 6 join trở xuống. Hình 2 là biểu đồ phân tán thời gian thực thi theo số lượng join. Chúng tôi
quan sát thấy các truy vấn có từ 6 đến 11 join có thời gian thực thi lớn nhất và do đó có tiềm năng được tối ưu cao
nhất. Đồng thời, đây cũng là khoảng mà các bộ tối ưu không vét cạn thường bị tắt (ví dụ, GEQO của PostgreSQL mặc định
chỉ được bật cho 12 bảng trở lên). Vì vậy, các phương pháp vét cạn vẫn có thể khám phá đầy đủ không gian các kế hoạch
có thể có.

Một cách khác để chia truy vấn được giới thiệu trong [43], trong đó các tác giả xây dựng các cách chia train/test dựa
trên số lượng join. Ví dụ, tất cả truy vấn có 3 hoặc 4 join tạo thành tập test, và tất cả các truy vấn khác tạo thành
tập train. Từ Hình 2 có thể thấy rõ số lượng join là một đại diện không phù hợp cho thời gian thực thi, theo phân tích
hồi quy với 𝑅² = −0,11. Do đó, chia truy vấn như vậy tạo ra các nhóm không khớp với mục tiêu tối ưu thực sự, tức là
thời gian thực thi.

*Khuyến nghị:* Chúng tôi đề xuất một số *trường hợp biên cho các cách chia train/test để bao phủ các vùng tổng quát
hóa khác nhau*, cụ thể là khoảng cách tổng quát hóa (generalization gap) và lấy mẫu ngoài phân phối (out-of-distribution)
(xem Mục 7.2).

> **Hình 2: Biểu đồ phân tán thời gian thực thi theo số lượng join cho tất cả truy vấn trong JOB.**
> *(Mô tả: trục hoành là số join (khoảng 3–16), trục tung là thời gian thực thi (giây, 0–15). Phần lớn truy vấn chạy
> dưới 2,5 giây; các truy vấn chậm nhất (đến ~15 giây) tập trung ở khoảng 6–11 join. Đường hồi quy gần như nằm ngang
> và hơi dốc xuống, R-Squared = −0,11.)*

### 6.2 Dịch chuyển hiệp biến (Covariate Shift)

Một chủ đề liên quan khác khi đánh giá LQO là khái niệm *dịch chuyển hiệp biến*, tức là sự thay đổi nội dung CSDL so
với lúc phương pháp được huấn luyện. Các DBMS giải quyết thách thức này bằng cách liên tục cập nhật thống kê nội bộ.
Tuy nhiên, với LQO, sự thay đổi nội dung CSDL ảnh hưởng đến cách truy vấn được mã hóa và do đó ảnh hưởng đến dự đoán
của nó. Ví dụ, một truy vấn về các bộ phim có ngày phát hành lớn hơn năm 2022 sẽ liên tục tăng kích thước tập kết quả
khi các phim mới phát hành được thêm vào DBMS.

Dù chủ đề này thường được nhắc tới như một hướng nghiên cứu tương lai đầy kỳ vọng, các phương pháp như Bao đã bắt đầu
nghĩ đến việc thiết kế mã hóa của họ để có thể xử lý dịch chuyển hiệp biến bằng cách bỏ định danh bảng và cột khỏi mã
hóa (xem Mục 4 để biết thêm chi tiết). Tuy nhiên, như chúng tôi chỉ ra trong một thí nghiệm ở Mục 8.3, chỉ cập nhật ước
lượng cardinality trong mã hóa là không đủ để theo kịp sự thay đổi của nội dung CSDL.

*Khuyến nghị:* Chúng tôi đề xuất các phương pháp tương lai nên *đưa vào một thí nghiệm đơn giản để đo khả năng xử lý
dịch chuyển hiệp biến*, như chúng tôi đã làm trong Mục 8.3.

---

## 7. KHUNG BENCHMARK CHO BỘ TỐI ƯU TRUY VẤN HỌC MÁY

Trong mục này, chúng tôi giới thiệu khung benchmark của mình, nhằm đánh giá toàn diện hơn các LQO. Mục tiêu là thực
hiện benchmark một cách tổng thể, bảo đảm so sánh công bằng các phương pháp trong bối cảnh đầu-cuối.

Để làm được điều này, benchmark của chúng tôi giả định một thiết lập có thể tái lập, đặc biệt về mặt kỹ thuật, bao gồm
nhưng không giới hạn ở: (a) nội dung CSDL nằm dưới workload benchmark, (b) toàn bộ mã nguồn của LQO, (c) phiên bản
ngôn ngữ lập trình, như Python, và tất cả thư viện được dùng, (d) cấu hình chi tiết của DBMS (trừ khi mọi tham số được
để mặc định), và (e) tất cả truy vấn cùng việc phân chúng vào các tập train/test.

### 7.1 Cấu hình DBMS & tinh chỉnh cơ sở dữ liệu

Để phân tích thời gian thực thi truy vấn, cả phần cứng được dùng lẫn cấu hình DBMS đều ảnh hưởng lớn đến khả năng so
sánh các LQO. Bây giờ chúng tôi sẽ phân tích một cách có hệ thống các thiết lập tham số chính.

Bảng 2 tổng hợp các thiết lập tham số khác nhau được dùng trong các công bố, so với giá trị mặc định của PostgreSQL,
cũng như thiết lập được đề xuất cho Join Order Benchmark [18]. Lưu ý rằng cấu hình của Neo [23] và HybridQO [41] không
có trong Bảng 2, vì mã nguồn (Neo) và cấu hình CSDL (HybridQO) của chúng không được công bố. Một quan sát nữa là chỉ có
Balsa và LEON công bố toàn bộ file cấu hình DBMS trong artifact của họ. Chúng tôi phân loại các tham số thành các nhóm
sau:

*Thứ tự join (Join Order):* Thứ tự join thường được ép buộc thông qua các thư viện như pg_hint_plan [27], dù PostgreSQL
cũng có thể được thiết lập để tuân theo thứ tự tường minh trong câu lệnh SQL bằng cách đặt `join_collapse_limit` bằng
- [1] Thuật toán tối ưu truy vấn di truyền (GEQO) của PostgreSQL được dùng cho các truy vấn có số join lớn, mặc định là
12 trở lên. Có thể tắt nó bằng cách đặt `geqo_threshold` lớn hơn số join trong workload, hoặc tắt hoàn toàn bằng tham
số `geqo`.

*Bộ nhớ làm việc (Working Memory):* Các giá trị mặc định cho bộ nhớ của PostgreSQL rất nhỏ. Với dung lượng RAM hiện
nay, nên tăng kích thước bộ nhớ làm việc và bộ đệm. Balsa tăng mạnh bộ nhớ làm việc (`work_mem`) từ 4 MB lên 4 GB,
trong khi Bao và Neo giữ giá trị mặc định, dù [18] đề xuất 2 GB. Tương tự, với `shared_buffers`, Balsa dùng bộ đệm lớn
hơn nhiều, 32 GB, so với khuyến nghị 4 GB mà Bao và Neo dùng. LOGER còn tăng `shared_buffers` lên 64 GB, nhưng máy của
họ cũng có nhiều RAM hơn.

Lưu ý rằng lượng `work_mem` được cấp cho mọi worker khi thực thi truy vấn song song, nghĩa là với 𝑁 worker,
`shared_buffers` ít nhất phải bằng 𝑁 × `work_mem`. Hơn nữa, tất cả các phương pháp đều dùng kích thước cache mặc định
(`effective_cache_size`) là 4 GB, bỏ qua khuyến nghị tăng lên 32 GB của [18]. Việc tăng giá trị này trong cấu hình của
chúng tôi từ 4 lên 32 GB đã làm giảm đáng kể thời gian lập kế hoạch cho một số truy vấn ngoại lai (từ tối đa 3 giây
xuống dưới 100 mili giây).

*Song song hóa (Parallelization):* Các tham số này xác định số lượng worker và tiến trình được dùng khi thực thi truy
vấn. Để tận dụng đầy đủ hệ thống đa nhân, Balsa tăng số tiến trình worker `max_worker_processes` cho bằng
`max_parallel_workers`. Dù tăng số worker song song có thể tăng tốc thực thi truy vấn, lượng tài nguyên tính toán cần
thiết cũng tăng đáng kể. LOGER và Lero đi theo hướng khác, tắt hoàn toàn mọi thực thi truy vấn song song.

*Loại scan (Scan Types):* Các tham số này thay đổi trực tiếp các loại scan mà PostgreSQL dùng và làm thay đổi đáng kể
bộ công cụ có sẵn cho việc thực thi truy vấn. Chỉ Balsa và LEON thay đổi các giá trị này bằng cách tắt cả bitmap scan
lẫn tid scan, trong khi không bài báo nào giải thích lý do cho cách làm này.

---

**Bảng 2: Tổng hợp các cấu hình PostgreSQL khác nhau (tham số tinh chỉnh CSDL) được dùng trong các bài báo về LQO.**
*Các giá trị khác với mặc định của PostgreSQL được ghi* trong các cột tương ứng (ô trống = giữ mặc định). Lưu ý rằng
giá trị của Neo [23] và HybridQO [41] không có trong bảng vì tham số cấu hình của họ không được công bố.

| Tham số cấu hình PostgreSQL | Mặc định | JOB [18] | Bao [22] | Balsa [39], LEON [4] | LOGER [3] | Lero [44] | Khung của chúng tôi |
|---|---|---|---|---|---|---|---|
| Lượng RAM tác giả dùng | | 64 GB | 15 GB | 64 GB | 256 GB | 512 GB | 64 GB |
| ***Thứ tự join*** | | | | | | | |
| `geqo_threshold` | 12 | 18 | | | 2 hoặc 1.024 | | |
| `geqo` | on | | | off | off | off | off¹ |
| ***Bộ nhớ làm việc*** | | | | | | | |
| `work_mem` | 4 MB | 2 GB | | 4 GB | | | 4 GB |
| `shared_buffers` | 128 MB | 4 GB | 4 GB | 32 GB | 64 GB | | 32 GB |
| `temp_buffers` | 8 MB | | | 32 GB | | | 32 GB |
| `effective_cache_size` | 4 GB | 32 GB | | | | | 32 GB |
| ***Song song hóa*** | | | | | | | |
| `max_parallel_workers` | 8 | | | | 1 | 0 | |
| `max_parallel_workers_per_gather` | 8 | | | | 1 | 0 | |
| `max_worker_processes` | 2 | | | 8 | | | 8 |
| ***Loại scan*** | | | | | | | |
| `enable_bitmapscan` | on | | | off | | | |
| `enable_tidscan` | on | | | off | | | |

¹ GEQO chỉ được bật cho Bao và khi PostgreSQL toàn quyền điều khiển việc thực thi truy vấn.

> *Ghi chú của người dịch:* cột "Mặc định" của nhóm song song hóa được chép đúng như bài gốc. Trong tài liệu
> PostgreSQL 12, giá trị mặc định thực tế là `max_worker_processes = 8`, `max_parallel_workers = 8`,
> `max_parallel_workers_per_gather = 2`.

---

### 7.2 Chia tập dữ liệu (Dataset Split)

Cách chia tập dữ liệu thành tập train và tập test có ảnh hưởng đáng kể đến hiệu năng của mô hình được huấn luyện. Dù
nên để cả hai tập chứa dữ liệu từ một phân phối tương tự, chúng ta phải cẩn thận để tránh rò rỉ thông tin từ tập này
sang tập kia. Cụ thể hơn, các truy vấn của Join Order Benchmark được suy ra từ 33 truy vấn gốc (hay template) khác
nhau, và toàn bộ 113 truy vấn được tạo thành từ 2 đến 6 biến thể của mỗi truy vấn gốc (ký hiệu 1a, 1b, 1c, …). Các
biến thể của cùng một truy vấn gốc dùng chung các bảng và phép join nhưng khác nhau ở câu lệnh lọc. Sự khác biệt này có
thể là giá trị lọc khác nhau (ví dụ `production_year < 2000` so với `production_year = 2023`) hoặc áp dụng bộ lọc trên
các cột khác (ví dụ `genre = 'horror'` so với `name LIKE %an%`). Các truy vấn trong tập dữ liệu STACK [22] cũng theo
cùng mẫu này, gồm 16 truy vấn gốc trên tổng số 6.191 truy vấn (từ 100 đến 1.010 biến thể cho mỗi truy vấn gốc).

Sinh truy vấn từ template tạo ra sự tương quan mạnh trong cấu trúc của kế hoạch join tối ưu đối với một số – nhưng
không phải tất cả – truy vấn. Để đo ảnh hưởng của khả năng rò rỉ dữ liệu, chúng tôi đề xuất các kỹ thuật lấy mẫu sau
để sinh các cách chia tập dữ liệu (xem Hình 3 để có ví dụ trực quan về việc phân vào tập train và tập test):

(1) **Lấy mẫu Leave One Out (Leave One Out Sampling)** lấy đúng một biến thể của mỗi truy vấn gốc đưa vào tập test.
Tất cả các biến thể khác của truy vấn gốc nằm trong tập train. Cách chia này tối đa hóa lượng thông tin có thể tận dụng
từ tập train sang tập test. Chúng tôi kỳ vọng đây là cách chia *dễ học nhất*.

(2) **Lấy mẫu ngẫu nhiên (Random Sampling)** phân bổ ngẫu nhiên mọi truy vấn vào tập train và tập test, bỏ qua mọi
liên hệ với truy vấn gốc hay template. Đây là cách lấy mẫu *độ khó trung bình*, và có thể áp dụng cho mọi workload, vì
không đòi hỏi phải tồn tại các *họ truy vấn gốc*.

(3) **Lấy mẫu theo truy vấn gốc (Base Query Sampling)** giữ mọi truy vấn của cùng một truy vấn gốc hoặc cùng ở tập
train, hoặc cùng ở tập test. Điều này bảo đảm sự tương đồng trong cấu trúc truy vấn của cùng một họ không bị rò rỉ từ
tập train sang tập test. Chúng tôi tin đây là cách chia *khó nhất*, vì mô hình không thể áp dụng cấu trúc join đã học
từ một biến thể sang một biến thể khác của cùng truy vấn gốc.

> **Hình 3: Tổng quan các kiểu lấy mẫu chia tập dữ liệu cho JOB:** Leave One Out (trên), Random (giữa) và Base Query
> (dưới). Ví dụ, Base Query 1 có 4 biến thể: 1a, 1b, 1c và 1d.
>
> | Truy vấn JOB | 1a | 1b | 1c | 1d | 2a | 2b | 2c | 2d | 3a | 3b | 3c | 4a | 4b | 4c | 5a | 5b | 5c |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
> | Leave One Out ("dễ") | Train | Test | Train | Train | Train | Train | Train | Test | Train | Test | Train | Test | Train | Train | Train | Train | Test |
> | Random ("trung bình") | Train | Train | Test | Train | Train | Test | Train | Test | Train | Train | Train | Test | Test | Train | Train | Train | Test |
> | Base Query ("khó") | Train | Train | Train | Train | Test | Test | Test | Test | Test | Test | Test | Train | Train | Train | Test | Test | Test |

### 7.3 Đo thời gian thực thi truy vấn

Vì mọi LQO đều được đánh giá bằng thời gian chạy của các truy vấn trong workload, và một số LQO trực tiếp dự đoán thời
gian thực thi cho một kế hoạch vật lý cho trước, điều tối quan trọng là các phép đo thời gian chạy phải nhất quán nhất
có thể. Một trong những nguyên nhân chính gây ra phương sai lớn khi thực thi cùng một truy vấn là trạng thái bộ đệm
(buffer) và cache trong DBMS. Ví dụ, khi cùng một truy vấn được thực thi hai lần liên tiếp, lần chạy đầu thường lâu hơn
lần thứ hai. Khi buffer và cache chuyển từ lạnh sang nóng, thời gian chạy trở nên nhất quán hơn. Trong kịch bản lý
tưởng, chúng ta có thể thực thi mỗi truy vấn rất nhiều lần để có phép đo vững chắc. Tuy nhiên, mỗi lần thực thi thêm
sau lần đầu đều tốn thêm thời gian không dành cho việc thực thi các truy vấn khác, làm tốn tài nguyên tính toán quý
giá. Bằng thực nghiệm, chúng tôi xác định rằng *thực thi truy vấn 3 lần* và lấy lần thực thi thứ ba cho kết quả ổn định
nhất mà không phát sinh chi phí thực thi không cần thiết (xem Mục 8.6 để biết thêm chi tiết về thí nghiệm).

---

## 8. THÍ NGHIỆM

Trong mục này, chúng tôi trình bày đánh giá toàn diện các LQO trên Join Order Benchmark (JOB) và STACK. Đầu tiên,
chúng tôi tổng quan thiết lập và phần cứng được dùng; sau đó thảo luận các cách khác nhau để sinh cách chia train/test.
Cuối cùng, chúng tôi trình bày kết quả thí nghiệm cùng một số nghiên cứu loại bỏ (ablation study).

### 8.1 Thiết lập chung

#### 8.1.1 Phần mềm và phần cứng

Tất cả thí nghiệm được thực hiện bằng PostgreSQL phiên bản 12.5, đo thời gian thực thi truy vấn thông qua các lệnh
`EXPLAIN ANALYZE`, dùng cả thời gian thực thi lẫn thời gian lập kế hoạch. Ngoài ra, chúng tôi cũng tính cả thời gian
suy luận (inference time) của các LQO. Các phép đo được lấy bằng cách thực thi cùng một truy vấn ba lần và lấy lần thực
thi cuối cùng (cache nóng).

Phiên bản PostgreSQL của chúng tôi được cấu hình phần lớn theo hướng giữ tham số mặc định, bám sát cấu hình mà Balsa
[39] đã dùng. Khác với Balsa, chúng tôi bật lại cả bitmap scan lẫn tid scan và tăng `effective_cache_size` từ 4 lên 32
GB. Những khác biệt chính so với mặc định của PostgreSQL có thể xem trong Bảng 2, chủ yếu gồm thay đổi cấu hình bộ nhớ
và tăng số worker song song. Ngoài ra, chúng tôi tắt tính năng `AUTOVACUUM`, vì workload truy vấn ổn định và `ANALYZE`
được chạy một lần sau khi nạp toàn bộ dữ liệu vào PostgreSQL, mất 3 phút với IMDB (JOB) và 16,5 phút với STACK.

Chúng tôi quyết định theo cấu hình của các thí nghiệm Balsa, vì chúng bao gồm các thiết lập bộ nhớ tuân thủ chặt chẽ
hướng dẫn thực hành tốt nhất do PostgreSQL đề xuất [31] và các gợi ý của Leis và cộng sự [18]. Hơn nữa, Balsa là phương
pháp đầu tiên tăng số tiến trình worker khả dụng từ 2 lên 8, phù hợp với các máy điển hình có nhiều nhân CPU. Chúng tôi
còn thay đổi tham số `effective_cache_size` theo hướng dẫn thực hành tốt nhất của PostgreSQL và bật lại cả bitmap scan
lẫn tid scan.

Với Join Order Benchmark, các tác giả của Balsa đã thêm hai chỉ mục trên các cột `subject_id` và `status_id` của bảng
`complete_cast`, so với các chỉ mục do [18] cung cấp. Chúng tôi cũng đưa hai chỉ mục bổ sung này vào thí nghiệm. Các
thí nghiệm được chạy bên trong các container Docker, dùng GPU Tesla T4, 64 GB RAM và 16 nhân CPU.

#### 8.1.2 Workload truy vấn

Chúng tôi đánh giá các LQO trên các workload JOB và STACK. Cả hai workload đều rất phù hợp với các nghiên cứu gần đây
và đã được dùng trong hầu hết các phương pháp LQO được đánh giá. Với JOB [18], chúng tôi dùng 113 truy vấn được cung
cấp. Workload STACK [22] gồm 6.191 truy vấn thuộc 16 truy vấn gốc, chúng tôi lấy mẫu xuống còn 14 truy vấn gốc⁴, mỗi
truy vấn gốc có 8 biến thể được lấy mẫu ngẫu nhiên. Điều này cho phép các phương pháp được huấn luyện và đánh giá với
lượng dữ liệu tương đương cho JOB và STACK, giúp các mô hình có mức sức mạnh thống kê (statistical power) tương tự.

#### 8.1.3 Chia tập dữ liệu

Trong các thí nghiệm, chúng tôi sinh các cách chia train/test bằng cách lấy mẫu đồng đều trên toàn bộ truy vấn (Random
Sampling), trên các truy vấn gốc (Base Query Sampling), hoặc trên các biến thể của mỗi truy vấn gốc (Leave One Out
Sampling). Với các cách chia Random và Base Query, chúng tôi dùng tỷ lệ 80-20 giữa tập train và tập test. Các cách chia
tập dữ liệu được lấy mẫu một lần và dùng chung cho tất cả các phương pháp được đánh giá. Danh sách chi tiết các tập
train và test cho mọi cách chia có trong kho mã nguồn của chúng tôi⁵, cùng với siêu tham số của tất cả phương pháp.

#### 8.1.4 Các thay đổi đáng chú ý khác

Vì chúng tôi đánh giá các phương pháp LQO trong khung thống nhất của mình, có những khác biệt so với các thí nghiệm do
tác giả của các phương pháp đó thực hiện (xem các mục trước). Do đó, không thể so sánh trực tiếp với các kết quả trước
đây.

Ngoài ra, Bao ban đầu được huấn luyện trên 2.500 truy vấn mới sinh theo phong cách JOB. Trong các thí nghiệm của chúng
tôi, Bao chỉ được huấn luyện trên tập train của cách chia train/test tương ứng và đã thấy các truy vấn huấn luyện nhiều
lần. Với LEON, chúng tôi giới hạn lượng thời gian thực dành cho huấn luyện ở mức gấp đôi thời gian Balsa cần để hoàn tất
huấn luyện, tức là 120 giờ. Giới hạn thời gian này có thể làm giảm hiệu năng của LEON, nhưng như được chỉ ra trong Mục
8.2.2, thời gian suy luận chi phối nặng nề tổng thời gian chạy của nó, chứ không chỉ thời gian thực thi.

---

⁴ Template 9 và 10 bị loại theo Balsa [39], nơi các tác giả báo cáo một hạn chế của extension pg_hint_plan khi xử lý
view và truy vấn con.
⁵ Xem mã nguồn tại: https://github.com/edualc/lqo_ml_perspective
⁶ Vì mã nguồn của Neo không được công bố, chúng tôi dùng bản cài đặt lại trong Balsa. Các tác giả gốc của Neo đã kiểm
tra và xác nhận với chúng tôi rằng nó phù hợp để benchmark.

---

### 8.2 So sánh các bộ tối ưu truy vấn học máy tiên tiến hiện nay

Trong mục này, chúng tôi phân tích hiệu năng của các phương pháp LQO tiên tiến hiện nay (cụ thể là Neo⁶ [23], Bao
[22], Balsa [39], LEON [4] và HybridQO [41]) so với PostgreSQL làm mốc cơ sở (baseline). Chúng tôi không đưa RTOS
[42], Lero [44] và LOGER [3] vào thí nghiệm vì chúng hoặc (a) không có sẵn, (b) đòi hỏi tắt song song hóa khi thực thi
truy vấn vì nhiều truy vấn được chạy song song, hoặc (c) đòi hỏi đầu tư một lượng lớn công sức kỹ thuật để các phương
pháp này có thể phân tích cú pháp đầu ra của `EXPLAIN`.

#### 8.2.1 Hiệu năng đầu-cuối (End-to-End Performance)

Với mọi thuật toán, chúng tôi báo cáo nhiều phép đo thời gian được định nghĩa như sau:

(1) **Thời gian suy luận (Inference Time):** Phép đo này bao gồm toàn bộ thời gian một LQO dành để mã hóa truy vấn,
duyệt qua các biến thể của kế hoạch truy vấn, thu thập thông tin chi phí để định hướng các quyết định tiếp theo, và cuối
cùng dùng mô hình ML để sinh dự đoán. Sau khi hết thời gian suy luận, một truy vấn SQL đã sẵn sàng để gửi tới PostgreSQL
kèm các hint về loại scan hoặc join cần dùng và theo thứ tự nào.

(2) **Thời gian lập kế hoạch (Planning Time):** Khi PostgreSQL nhận được một truy vấn, nó dành một khoảng thời gian để
lập kế hoạch cho truy vấn trước khi một kế hoạch vật lý cuối cùng được sinh ra và gửi đi thực thi. Với các LQO có
extension chạy bên trong PostgreSQL, thời gian suy luận thường được báo cáo như một phần của thời gian lập kế hoạch.

(3) **Thời gian thực thi (Execution Time):** Bao gồm lượng thời gian PostgreSQL dành để thực thi truy vấn và thu thập
tập kết quả.

(4) **Thời gian thực thi đầu-cuối (End-to-end Execution Time):** Tổng hợp của ba phép đo trên, đo thời gian một phương
pháp cần để đưa ra kế hoạch truy vấn cần thực thi và thời gian PostgreSQL cần để lấy kết quả từ CSDL. Chúng tôi tin
rằng phép đo này nên là mục tiêu chính của việc tối ưu.

Chúng tôi không tính độ trễ mạng vào thời gian suy luận, lập kế hoạch và thực thi, vì LQO không thể ảnh hưởng trực tiếp
đến nó. Dù độ trễ mạng có thể chiếm một lượng thời gian đáng kể (đặc biệt với các truy vấn nhanh), việc tối ưu nó nằm
ngoài phạm vi của đánh giá này.

Chúng tôi tăng dần độ khó qua các thí nghiệm, bắt đầu với lấy mẫu leave one out, rồi lấy mẫu ngẫu nhiên và cuối cùng là
lấy mẫu theo truy vấn gốc để sinh các cách chia train/test. Mọi truy vấn được thực thi ba lần. Thời gian lập kế hoạch và
thời gian thực thi được lấy từ lần thực thi thứ ba.

> **Hình 4: Tổng quan so sánh hiệu năng của từng phương pháp trên *tập test* của các cách chia tập dữ liệu khác nhau
> trên Join Order Benchmark (JOB).** Hình bên trái thể hiện thời gian lập kế hoạch (màu đậm) và thời gian suy luận (màu
> nhạt). Lưu ý rằng Bao chạy bên trong PostgreSQL dưới dạng extension, nên thời gian suy luận của nó được cộng trực tiếp
> vào thời gian lập kế hoạch. Hình bên phải thể hiện thời gian thực thi trên cùng các cách chia train/test. Xin lưu ý
> trục hoành của cả hai hình đều bị ngắt quãng.
>
> *(Mô tả: 9 cách chia LOO-1/2/3, RND-1/2/3, BQ-1/2/3. Bên trái: PostgreSQL có thời gian lập kế hoạch gần 0; Neo, Bao,
> Balsa khoảng 5–15 giây; HybridQO khoảng 1–2 giây; LEON vượt ra ngoài trục, khoảng 10³–10⁵ giây. Bên phải: thời gian
> đầu-cuối của PostgreSQL, Bao và HybridQO thường ở mức 20–60 giây; Neo và Balsa thường cao hơn và có cách chia vượt
> trục (10²–10³ giây); LEON luôn vượt trục, 10³–10⁵ giây.)*

> **Hình 5: Tổng quan so sánh hiệu năng của từng phương pháp trên *tập test* của các cách chia tập dữ liệu khác nhau
> trên STACK.**
>
> *(Mô tả: 3 cách chia LOO, RND, BQ, cùng bố cục với Hình 4. Thời gian đầu-cuối của PostgreSQL khoảng 10–25 giây;
> Bao khoảng 15–35 giây; HybridQO tốt nhất ở LOO nhưng có truy vấn timeout ở RND; Neo, Balsa và LEON vượt trục,
> khoảng 10²–10³ giây.)*

Hình 4 và Hình 5 trình bày hiệu năng trên JOB và STACK theo cả ba phương pháp lấy mẫu và từng cách chia train/test của
chúng. Tóm lại, **PostgreSQL nhìn chung cho hiệu năng tốt nhất, tiếp theo là HybridQO, rồi đến Bao, Neo, Balsa và cuối
cùng là LEON.** Tuy nhiên, PostgreSQL không vượt trội tất cả phương pháp trên mọi cách chia với khoảng cách có ý nghĩa
thống kê. Cụ thể, HybridQO và Bao đạt kết quả tương đương trên hầu hết các cách chia train/test, và HybridQO vượt
PostgreSQL trên cách chia leave one out của STACK.

Trước hết, hãy xem kết quả trên JOB. Với *lấy mẫu leave one out*, mà chúng tôi coi là cách chia train/test dễ nhất,
PostgreSQL, Bao và HybridQO thực thi các truy vấn test trong khoảng 30 giây. Tuy nhiên, Bao tốn thêm 8,5 giây để lập kế
hoạch truy vấn, dẫn đến thời gian thực thi đầu-cuối chậm hơn 25%. Khoảng tin cậy lớn hơn của Bao là gợi ý đầu tiên cho
thấy nó đã tìm được các kế hoạch nhìn chung nhanh hơn PostgreSQL, nhưng chúng không tăng tốc thời gian thực thi đủ để
tạo ra lợi thế. Ngược lại, HybridQO tìm được các kế hoạch nhanh hơn 2,5 giây trong khi chỉ mất 1,4 giây cho suy luận,
cho phép nó vượt PostgreSQL một cách đáng kể trên cách chia thứ ba.

LEON là phương pháp nhanh thứ tư xét theo thời gian thực thi với 58 giây, nhưng thời gian suy luận của nó dài khoảng 9,6
giờ, khiến nó không thực tế cho truy vấn tương tác (các truy vấn phức tạp hơn đòi hỏi thời gian suy luận nhiều hơn tương
ứng).

Phương pháp nhanh thứ tư xét tổng thể là Neo với 93 giây, tiếp theo là Balsa với 134 giây, tức là thời gian thực thi
đầu-cuối chậm hơn PostgreSQL lần lượt 286% và 411%.

Với *lấy mẫu ngẫu nhiên*, tức là cách chia train/test có độ khó trung bình, PostgreSQL và Bao vẫn cạnh tranh ngang ngửa
nhau, với Bao thậm chí đạt thời gian thực thi thấp hơn: 25 giây so với 28 giây của PostgreSQL. Tuy nhiên, đây không phải
là khác biệt có ý nghĩa thống kê. Khi tính cả thời gian suy luận và lập kế hoạch, Bao lại hơi bất lợi. Tương tự cách chia
trước, HybridQO ngang bằng PostgreSQL và thậm chí vượt đáng kể cả PostgreSQL lẫn Bao trên cách chia thứ ba với 24 giây.
So với lấy mẫu leave one out, cả Neo và Balsa đều đạt thời gian thực thi đầu-cuối nhanh hơn 2–3 lần, đạt kết quả tương
đương PostgreSQL trên 2 trong 3 cách chia train/test dùng kiểu lấy mẫu này. LEON gặp khó khăn với các truy vấn này và
có hai truy vấn bị timeout (26b và 32b) ở hai cách chia khác nhau, dẫn đến thời gian thực thi tăng mạnh. Tuy nhiên, với
thời gian suy luận trung bình lớn tới 3,8 giờ, điều này ít ảnh hưởng đến thứ hạng chung của nó.

Cuối cùng, hãy xem *lấy mẫu theo truy vấn gốc*, tức là kỹ thuật lấy mẫu khó nhất. Lần đầu tiên, Bao chỉ đạt kết quả
tương đương PostgreSQL trên 1 cách chia, còn HybridQO đạt được trên cả 3 cách chia train/test, xác nhận độ khó tăng lên.
Neo và Balsa gặp khó khăn đặc biệt với base query split 1: 3 truy vấn của tập test bị timeout với Neo, và 15 truy vấn
trên cả tập train và tập test bị timeout với Balsa. Tuy nhiên, LEON có thể phần lớn ngang bằng thời gian thực thi trực
tiếp của PostgreSQL nếu phương pháp này khắc phục được thời gian suy luận.

Kết quả trên tập dữ liệu STACK (xem Hình 5) phần lớn xác nhận kết quả của JOB. Một khác biệt lớn là thời gian suy luận
của LEON, thấp hơn một bậc độ lớn do số join trong các truy vấn STACK nhìn chung ít hơn so với JOB. Neo, Balsa và LEON
đều chịu ảnh hưởng nặng nề từ một lượng lớn truy vấn bị timeout. Khác với JOB, Bao không theo kịp hiệu năng của
PostgreSQL trên STACK do các tính năng SQL phức tạp hơn trong các truy vấn STACK, dẫn đến thời gian suy luận dài hơn
nhiều. HybridQO vượt PostgreSQL trên cách chia leave one out, tương đương trên cách chia base query nhưng cũng bị ảnh
hưởng bởi các truy vấn timeout trên cách chia ngẫu nhiên, gợi ý về vấn đề tính bền vững.

Tóm lại, chúng tôi thấy *tác động đáng kể của thời gian suy luận lên tổng thời gian thực thi đầu-cuối*. Dù có những
phương pháp, trên một số cách chia train/test, đạt hiệu năng tương đương PostgreSQL hoặc thậm chí nhỉnh hơn một chút,
các kết quả này cho thấy *tầm quan trọng của cách chia truy vấn để huấn luyện*. Hơn nữa, điều tối quan trọng là việc
đánh giá phải tính cả thời gian suy luận, vì nó định hình mạnh mẽ thứ hạng giữa các phương pháp so với chỉ xét thời gian
thực thi.

> **Hình 6: So sánh thời gian huấn luyện đầu-cuối với tổng thời gian chạy của workload cho cả hai workload, trong đó
> mỗi điểm biểu diễn một mô hình từ một cách chia khác nhau.**
>
> *(Mô tả: trục hoành là thời gian huấn luyện đầu-cuối (giờ), trục tung là tổng thời gian chạy workload (giây, thang
> log). JOB: PostgreSQL và Bao gần 0 giờ, khoảng 10¹ giây; HybridQO khoảng 15–20 giờ; Neo khoảng 20–50 giờ; Balsa khoảng
> 40–90 giờ; LEON khoảng 105–125 giờ với thời gian chạy 10⁴–10⁵ giây. STACK: Bao, PostgreSQL và HybridQO gần 0; Neo và
> LEON khoảng 120–150 giờ; Balsa khoảng 170–290 giờ.)*

#### 8.2.2 Thời gian huấn luyện (Training Time)

Sau khi so sánh hiệu năng truy vấn, chúng tôi cũng xem xét lượng thời gian cần để huấn luyện một mô hình. Dù định nghĩa
thời gian huấn luyện đôi khi không rõ ràng, chúng tôi muốn có một cái nhìn tổng thể với *thời gian huấn luyện đầu-cuối*,
bao gồm (a) thời gian thu thập kết quả truy vấn từ DBMS, (b) mọi thời gian dành cho việc huấn luyện mô hình, (c) việc
đánh giá liên tục hiệu năng của mô hình hiện tại, và (d) mọi khâu tiền xử lý hoặc hậu xử lý, khởi tạo và sinh artifact.
Nói ngắn gọn, đó là *toàn bộ thời gian từ khi bắt đầu quy trình huấn luyện cho đến khi nó kết thúc*.

Chúng tôi phân biệt như vậy không phải để phạt việc ghi log bổ sung hay kiểm tra hiệu năng mô hình thường xuyên hơn, mà
để có một so sánh tổng thể công bằng hơn. Ví dụ, một phương pháp có thể có giai đoạn huấn luyện rất nhanh nhưng tốn
nhiều thời gian truy vấn dữ liệu huấn luyện từ DBMS, trong khi một phương pháp khác cần ít truy vấn CSDL hơn nhưng dùng
kiến trúc mạng nơ-ron phức tạp hơn, tốn nhiều thời gian hơn
cho việc cập nhật trọng số. Tổng lượng thời gian bỏ ra cũng cho biết một mô hình có thể được huấn luyện lại thường xuyên
đến mức nào với một ngân sách thời gian cho trước.

Trong Hình 6, chúng tôi so sánh thời gian huấn luyện đầu-cuối trên trục hoành với tổng thời gian chạy của workload
(tổng thời gian thực thi đầu-cuối của mọi truy vấn trong workload) trên trục tung. Mỗi điểm biểu diễn một cách chia
train/test. Ví dụ, một điểm màu cam có thể là phương pháp Neo trên random split 2.

Vì bộ tối ưu của PostgreSQL không cần bất kỳ quá trình huấn luyện nào và đóng vai trò mốc cơ sở, thời gian huấn luyện
đầu-cuối của nó được đặt bằng 0. Trong các phương pháp được đánh giá, Bao cần ít thời gian nhất trên JOB, khoảng 2 giờ;
HybridQO khoảng 20 giờ; Neo từ 20 đến 40 giờ; Balsa từ 40 đến 85 giờ; và LEON từ 110 đến 130 giờ. Với STACK, Bao huấn
luyện trong 2 giờ, HybridQO trong 12 đến 14 giờ, Neo và LEON từ 120 đến 140 giờ, và Balsa từ 170 đến 290 giờ.

Theo một giả định ngây thơ, người ta sẽ kỳ vọng hiệu năng tăng lên khi dành nhiều thời gian hơn cho huấn luyện, nhưng
chúng tôi quan sát thấy hành vi hoàn toàn ngược lại: Các phương pháp *dành nhiều thời gian hơn để xây dựng và huấn
luyện mô hình lại đạt kết quả kém hơn* so với các phương pháp kết thúc huấn luyện nhanh hơn. Chúng tôi chủ yếu cho rằng
sự khác biệt này giữa các phương pháp là do số lượng kế hoạch được xem xét.

Ví dụ, trong quá trình huấn luyện trên JOB, Neo đã thực thi từ 4.000 đến 8.000 kế hoạch trong PostgreSQL, Balsa từ
19.000 đến 21.000 kế hoạch. Ngay cả khi bỏ qua chất lượng của các kế hoạch được thực thi bởi mỗi phương pháp, rõ ràng
số kế hoạch nhiều gấp 2–3 lần cũng đòi hỏi nhiều thời gian xử lý hơn. Các tác giả của Balsa đã giải quyết riêng thách
thức này bằng cách cho phép mọi kế hoạch cần thiết được thực thi trên nhiều phiên bản DBMS song song và ngắt (timeout)
các truy vấn chạy lâu, điều mà Neo không làm. LEON không thực thi đầy đủ phần lớn các kế hoạch nó sinh ra; tuy nhiên, nó
gọi PostgreSQL để xin ước lượng chi phí cho tới hàng chục nghìn kế hoạch con, đến mức chỉ riêng việc dự đoán một kế
hoạch cho truy vấn 29a (truy vấn có 17 bảng được đặt bí danh, nhiều nhất trong toàn bộ JOB) đã mất khoảng 6,5 giờ⁷.

### 8.3 Nghiên cứu loại bỏ: Dịch chuyển hiệp biến

Một trong những thách thức đối với bộ tối ưu truy vấn nói chung là sự phụ thuộc vào thống kê cập nhật của nội dung CSDL.
Trong DBMS, thống kê được làm mới thường xuyên, nhưng LQO không có được sự tiện lợi là dễ dàng cập nhật trọng số của mô
hình đã huấn luyện, mà phải chọn giữa huấn luyện mô hình mới từ đầu hoặc tinh chỉnh (fine-tune) và tiếp tục huấn luyện,
để thích nghi với các thay đổi của CSDL bên dưới.

Để kiểm tra xem một cách mã hóa chỉ biểu diễn nội dung CSDL bằng cardinality (như Bao) có xử lý được dịch chuyển hiệp
biến hay không, chúng tôi tiến hành thí nghiệm sau. Chúng tôi tạo một bản sao nhỏ hơn của IMDB, gọi là IMDB-50%. Đúng
như tên gọi, chúng tôi giữ lại 50% số dòng trong bảng `title` bằng lấy mẫu Bernoulli, bảo đảm lượng dữ liệu có sẵn
giảm một nửa nhưng phân phối giá trị vẫn tương đương bản gốc. 50% số dòng còn lại bị xóa bằng CASCADE để bảo đảm toàn
vẹn tham chiếu. Chúng tôi chủ ý chọn thay đổi nội dung bảng `title` vì đây là bảng duy nhất trong IMDB xuất hiện trong
mọi truy vấn JOB.

Sau khi lấy mẫu, chúng tôi thấy số bản ghi giảm 50% ở tất cả các bảng liên quan đến phim (title, movie_companies,
movie_info, movie_info_idx, movie_keyword và movie_link) và các bảng liên quan đến diễn viên (cast_info và
complete_cast). Việc lấy mẫu trên `title` không ảnh hưởng đến tất cả các bảng khác. Sau khi thay đổi IMDB-50%, thống kê
nội bộ của PostgreSQL đã được cập nhật.

Thí nghiệm của chúng tôi nhằm chỉ ra rằng các phương pháp như Bao, vốn chỉ dùng cardinality trong mã hóa, bị suy giảm
hiệu năng khi thêm nhiều dữ liệu hơn (mô phỏng dịch chuyển hiệp biến). Chúng tôi huấn luyện một mô hình Bao trên IMDB
(gọi là Bao-Full) và một mô hình Bao thứ hai trên IMDB-50% có kích thước đã giảm (gọi là Bao-50), dùng cùng cách chia
train/test "base query split 1".

Truy vấn 16b là một ngoại lệ nổi bật, bị timeout ở 1 trong 4 mô hình Bao-50, trong khi 3 kế hoạch còn lại được sinh ra
chậm hơn Bao-Full 19 giây. Xét theo chênh lệch tương đối, truy vấn 31c chậm hơn 24 lần khi dùng Bao-50, với 8,4 giây
so với 350 mili giây của Bao-Full. Truy vấn 17a chậm hơn 4,5 lần, với 12,2 giây so với 2,7 giây của Bao-Full. Mặt khác,
các chế độ cardinality khác nhau mà Bao-50 thấy cũng giúp nó cải thiện một vài truy vấn so với Bao-Full, với hệ số
1,9 lần cho truy vấn 7c, 1,6 lần cho 26c và 1,3 lần cho 10c.

Các kết quả này cho thấy *việc hệ thống DBMS cập nhật thống kê (tức là ước lượng cardinality) là không đủ để theo kịp
một mô hình mới được huấn luyện*. Sự suy giảm hiệu năng này còn cho thấy những khó khăn trong việc tổng quát hóa, đặc
biệt khi các giá trị cardinality lớn hơn chưa từng được thấy trong quá trình huấn luyện và do đó nằm ngoài phân phối.
Hiện chưa có giải pháp nào cho vấn đề này ngoài việc huấn luyện lại hoặc tinh chỉnh mô hình với các truy vấn chạy trên
trạng thái CSDL mới. Vì vậy, các phương pháp có thể được cập nhật và huấn luyện lại liên tục là đáng ưu tiên hơn.

### 8.4 Nghiên cứu loại bỏ: Bitmap scan và Tid scan

Chúng tôi đã quan sát thấy nhiều công bố tắt bitmap scan và tid scan, cụ thể là Balsa [39], LEON [4] và một phân tích
được công bố gần đây [43], mà không đưa ra lý do. Thí nghiệm này nhằm xem việc thay đổi bộ công cụ của PostgreSQL có ảnh
hưởng đáng kể đến hiệu năng truy vấn của từng truy vấn hay không. Để so sánh, chúng tôi dùng hiệu năng PostgreSQL mốc
cơ sở từ thí nghiệm trước trong Mục 8.2, và chạy lại cùng 113 truy vấn JOB với bitmap scan và tid scan bị tắt.

Chênh lệch thời gian thực thi vượt quá 250 mili giây ở 28 truy vấn, trong đó 24 truy vấn có ý nghĩa thống kê. Với 24
truy vấn đó, tắt bitmap scan và tid scan **tăng tốc** các truy vấn 28a, 7c và 30a so với thời gian thực thi gốc lần
lượt 5,5 lần, 2,0 lần và 1,8 lần. Ngược lại, các truy vấn 30c, 28b và 15c **chậm đi** lần lượt 2,4 lần, 1,9 lần và 1,5
lần.

Những phát hiện này cho thấy *việc cho phép PostgreSQL dùng bitmap scan và tid scan ảnh hưởng đáng kể đến hiệu năng
truy vấn*, đặc biệt với các template truy vấn 7, 8, 28 và 30. Một quan sát thú vị ở đây là cùng một họ truy vấn có mức
lợi lớn nhất khi tắt các scan nói trên (truy vấn 28a tăng tốc 5,5 lần) cũng có mức chậm đi lớn (truy vấn 28b chậm đi
1,9 lần).

### 8.5 Nghiên cứu loại bỏ: Bộ tối ưu truy vấn di truyền

Tương tự việc tắt các loại scan, các công bố gần đây cũng khác nhau ở việc có dùng GEQO, tức là bộ tối ưu truy vấn di
truyền của PostgreSQL, hay không. Chúng tôi đã phân tích ảnh hưởng của việc tắt GEQO lên thời gian thực thi các truy vấn
JOB. Thí nghiệm cho thấy có 5 truy vấn có chênh lệch mang ý nghĩa thống kê. Tắt GEQO **tăng tốc** truy vấn 30a 1,6 lần,
trong khi bốn truy vấn còn lại **chậm đi** 9,9 lần (24b), 2,2 lần (26c), 2,1 lần (28a) và 1,7 lần (28b). Hệ số chậm đi
lớn của truy vấn 24b được giải thích bởi thời gian thực thi rất nhanh của nó, chỉ 28 mili giây, so với 272 mili giây khi
tắt GEQO. Dù ảnh hưởng của GEQO nhỏ hơn so với bitmap scan và tid scan, nó vẫn đáng kể, đặc biệt trong số các template
truy vấn chậm nhất.

Tóm lại, các kết quả này cho thấy *điều tối quan trọng là PostgreSQL phải hoạt động với đầy đủ năng lực* (tức là bật
GEQO), đặc biệt khi LQO không thay thế mà chỉ tăng cường hoặc định hướng bộ tối ưu hiện có (ví dụ, thông qua việc dùng
hint).

### 8.6 Tính bền vững của thời gian thực thi truy vấn

Mục tiêu của thí nghiệm này là xác định số lần thực thi lặp lại 𝑘 của cùng một truy vấn để đạt thời gian thực thi nhất
quán trong kịch bản cache nóng. Ví dụ, trong LEON [4], các tác giả dùng trung bình nhân với 𝑘 = 3, trong khi ở [43],
các tác giả thực thi truy vấn 𝑘 = 5 lần và lấy trung bình cộng.

Để so sánh công bằng, chúng tôi thực thi mọi truy vấn JOB bằng `EXPLAIN ANALYZE` 50 lần liên tiếp và theo thứ tự (tức
là 1a, 1a, 1a, …, 1a, 1b, 1b, …). Thời gian thực thi được lấy từ phản hồi `EXPLAIN` của PostgreSQL, loại bỏ độ trễ mạng
từ CSDL khỏi phép đo. Bằng cách đánh giá thực nghiệm phân phối thời gian thực thi cho lần lặp thứ 𝑘, chúng tôi có thể đề
xuất một giá trị 𝑘 cân bằng giữa chi phí và tính bền vững.

> **Hình 7: Chênh lệch thời gian thực thi đã chuẩn hóa giữa các lần thực thi truy vấn liên tiếp.** Ví dụ, 𝑘 = 1 thể
> hiện chênh lệch giữa lần thực thi thứ 1 và thứ 2.
>
> *(Mô tả: biểu đồ hộp (boxplot) cho 𝑘 = 1, 2, 3, 4; trục tung là chênh lệch thời gian thực thi đã chuẩn hóa (%). Ở
> 𝑘 = 1, trung vị khoảng −12% và có nhiều điểm ngoại lai đến khoảng −60%; từ 𝑘 = 2 trở đi, hộp tập trung quanh 0%.)*

Hình 7 thể hiện chênh lệch đã chuẩn hóa của thời gian thực thi truy vấn (chênh lệch tương đối so với truy vấn được thực
thi đầu tiên) khi so sánh các cặp lần thực thi thứ 𝑘 và thứ (𝑘 + 1). Chúng tôi quan sát thấy thời gian thực thi truy vấn
thay đổi đáng kể với phần lớn các truy vấn được thực thi ở 𝑘 = 1, với mức giảm trung bình 14,6% giữa lần thực thi thứ 1
và thứ 2, và thêm 1,03% từ lần thứ 2 sang lần thứ 3. Từ đó trở đi, các dao động không còn thể hiện xu hướng nào có thể
được lợi từ việc thực thi thêm.

Như vậy, chúng tôi thấy bằng thực nghiệm rằng để đo thời gian thực thi một cách bền vững, điều quan trọng là thực thi
một truy vấn ít nhất hai lần. Nếu thời gian và chi phí cho phép, lần thực thi thứ ba sẽ cải thiện thêm tính bền vững,
sau đó có thể dừng một cách an toàn. So với lựa chọn 𝑘 = 5 trong [43], lấy lần thực thi thứ ba nhanh hơn 40% và bền
vững hơn so với lấy trung bình ba phép đo (trong đó lần thực thi truy vấn đầu tiên thường chi phối như một phép đo ngoại
lai).

### 8.7 Phân tích các loại kế hoạch truy vấn

Do số lượng kế hoạch bushy lớn hơn so với kế hoạch left-deep và right-deep⁸, cần đặt câu hỏi liệu việc bỏ qua *kế hoạch
bushy* (như trong RTOS, LOGER và HybridQO) có phải là lựa chọn hợp lý. Trong [18], mức chậm đi do giới hạn hình dạng cây
đã được đo bằng cách so sánh với kế hoạch tối ưu. Kết quả của các tác giả cho thấy *cây left-deep kém hơn cây bushy*
nhưng vẫn cho hiệu năng hợp lý. Đáng chú ý là các thí nghiệm đó được thực hiện bằng cách đưa *cardinality thực
(true cardinalities)* vào mô hình chi phí của bộ tối ưu truy vấn. Hơn nữa, một số ràng buộc về lựa chọn phương thức
join theo [6] cũng được áp dụng.

Bằng cách ép buộc mọi tổ hợp, chúng tôi đã phân tích tất cả các kế hoạch có thể có cho các truy vấn JOB có ≤ 5 join
theo tinh thần của [18]. Tuy nhiên, thay vì dùng cardinality thực (vốn được xem là trường hợp tối ưu), chúng tôi chạy
thí nghiệm với *bộ ước lượng cardinality nội bộ của DBMS*. Hơn nữa, chúng tôi cho phép dùng mọi phương thức join.

Kết quả là, *kế hoạch bushy có hiệu năng trung bình như kế hoạch left-deep*. Chúng tôi xác nhận kết quả này với giá trị
nhỏ nhất *p-value = 0,285* của kiểm định Mann-Whitney U hai phía [21]⁹ cho trung bình thời gian thực thi. Tuy nhiên, ở
đuôi trái của phân phối gộp thời gian thực thi (tức là trong số các kế hoạch nhanh nhất), cây bushy vượt trội đáng kể
với *p-value bằng 0,015* cho giả thuyết đối. Điều đó có nghĩa là loại cây bushy khỏi phạm vi xem xét sẽ làm giảm mạnh
khả năng một mô hình tìm được kế hoạch tốt nhất.

---

⁷ LEON cache các ước lượng chi phí của kế hoạch và kế hoạch con, sinh ra các file trên ổ cứng có dung lượng lần lượt
lên tới 1,7 GB cho JOB và 120 MB cho STACK.
⁸ Từ đây trở đi, kế hoạch left-deep và right-deep chỉ được gọi chung là kế hoạch left-deep mà không làm mất tính tổng
quát.
⁹ Việc chọn kiểm định phi tham số thay vì kiểm định T xuất phát từ việc quan sát thấy giả định phân phối chuẩn không
hợp lý giữa các kế hoạch logic và vật lý khác nhau.

---

## 9. KẾT LUẬN

Trong bài báo này, chúng tôi chỉ ra các hạn chế của các phương pháp LQO hiện tại và nhấn mạnh những thách thức trước đây
ít được báo cáo. Chúng tôi cung cấp một khung giúp cân bằng nhiều tham số liên quan đến benchmark để thu được kết quả
ngày càng bền vững.

Chúng tôi thực hiện đánh giá các phương pháp LQO hiện tại trên Join Order Benchmark và chỉ ra rằng việc vượt trội
PostgreSQL một cách nhất quán khó hơn dự kiến, đặc biệt khi nhìn bài toán tối ưu truy vấn như một quá trình đầu-cuối.
Chúng tôi tin rằng bài báo của mình là bước đầu tiên hướng tới việc đánh giá benchmark có thể tái lập và nhất quán cho
LQO, và do đó mang lại những nhận định mới quan trọng về LQO từ góc nhìn ML.

## LỜI CẢM ƠN

Dự án nhận được tài trợ từ Quỹ Khoa học Quốc gia Thụy Sĩ (Swiss National Science Foundation) theo mã tài trợ 1921052.
Chúng tôi cũng cảm ơn các đồng nghiệp tại Đại học Konstanz, gồm Michael Grossniklaus, Mehmet Aytimur và Silvan Reiner,
cùng Dennis Gehrig tại Đại học Khoa học Ứng dụng Zurich, vì những thảo luận quý báu.

---

## TÀI LIỆU THAM KHẢO

*(Giữ nguyên bản gốc tiếng Anh.)*

- [1] Ron Avnur and Joseph M. Hellerstein. 2000. Eddies: Continuously Adaptive Query Processing. SIGMOD Rec. 29, 2 (may 2000), 261–272. https://doi.org/10.1145/335191.335420
- [2] Jason Brownlee. 2020. Data preparation for machine learning: data cleaning, feature selection, and data transforms in Python. Machine Learning Mastery.
- [3] Tianyi Chen, Jun Gao, Hedui Chen, and Yaofeng Tu. 2023. LOGER: A Learned Optimizer Towards Generating Efficient and Robust Query Execution Plans. Proceedings of the VLDB Endowment 16, 7 (2023), 1777–1789.
- [4] Xu Chen, Haitian Chen, Zibo Liang, Shuncheng Liu, Jinghong Wang, Kai Zeng, Han Su, and Kai Zheng. 2023. LEON: A New Framework for ML-Aided Query Optimization. Proc. VLDB Endow. 16, 9 (2023), 2261–2273.
- [5] Vijay Prakash Dwivedi and Xavier Bresson. 2021. A Generalization of Transformer Networks to Graphs. arXiv:2012.09699 [cs.LG]
- [6] Hector Garcia-Molina, Jeffrey D. Ullman, and Jennifer Widom. 2008. Database Systems: The Complete Book (2 ed.). Prentice Hall Press, USA.
- [7] Ian J. Goodfellow, Yoshua Bengio, and Aaron Courville. 2016. Deep Learning. MIT Press, Cambridge, MA, USA. http://www.deeplearningbook.org.
- [8] Yang Guan, Shengbo Eben Li, Jingliang Duan, Jie Li, Yangang Ren, Qi Sun, and Bo Cheng. 2021. Direct and indirect reinforcement learning. arXiv:1912.10600 [cs.LG]
- [9] Isabelle Guyon and André Elisseeff. 2006. An Introduction to Feature Extraction. Springer Berlin Heidelberg, Berlin, Heidelberg, 1–25. https://doi.org/10.1007/978-3-540-35488-8_1
- [10] Yuxing Han, Ziniu Wu, Peizhi Wu, Rong Zhu, Jingyi Yang, Tan Wei Liang, Kai Zeng, Gao Cong, Yanzhao Qin, Andreas Pfadler, Zhengping Qian, Jingren Zhou, Jiangneng Li, and Bin Cui. 2022. Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation. VLDB 15, 4 (2022).
- [11] Jonas Heitz and Kurt Stockinger. 2019. Join query optimization with deep reinforcement learning algorithms. arXiv preprint arXiv:1911.11689 (2019).
- [12] Benjamin Hilprecht, Andreas Schmidt, Moritz Kulessa, Alejandro Molina, Kristian Kersting, and Carsten Binnig. 2020. DeepDB: Learn from Data, Not from Queries! Proc. VLDB Endow. 13, 7 (mar 2020), 992–1005. https://doi.org/10.14778/3384345.3384349
- [13] Mouna Kacimi and Thomas Neumann. 2009. System R (R*) Optimizer. Springer US, Boston, MA, 2900–2905. https://doi.org/10.1007/978-0-387-39940-9_384
- [14] Thomas N. Kipf and Max Welling. 2017. Semi-Supervised Classification with Graph Convolutional Networks. In Proceedings of the 5th International Conference on Learning Representations (Palais des Congrès Neptune, Toulon, France) (ICLR ’17). https://openreview.net/forum?id=SJU4ayYgl
- [15] Sanjay Krishnan, Zongheng Yang, Kenneth Goldberg, Joseph Hellerstein, and Ion Stoica. 2018. Learning to Optimize Join Queries With Deep Reinforcement Learning. (08 2018).
- [16] Sanjay Krishnan, Zongheng Yang, Ken Goldberg, Joseph Hellerstein, and Ion Stoica. 2018. Learning to optimize join queries with deep reinforcement learning. arXiv preprint arXiv:1808.03196 (2018).
- [17] Joseph P La Salle. 1976. The stability of dynamical systems. SIAM.
- [18] Viktor Leis, Andrey Gubichev, Atanas Mirchev, Peter Boncz, Alfons Kemper, and Thomas Neumann. 2015. How good are query optimizers, really? Proceedings of the VLDB Endowment 9, 3 (2015), 204–215.
- [19] Justin J Levandoski, Per-Åke Larson, and Radu Stoica. 2013. Identifying hot and cold data in main-memory databases. In 2013 IEEE 29th International Conference on Data Engineering (ICDE). IEEE, 26–37.
- [20] Tie-Yan Liu. 2009. Learning to Rank for Information Retrieval. Foundations and Trends® in Information Retrieval 3, 3 (2009), 225–331. https://doi.org/10.1561/1500000016
- [21] H. B. Mann and D. R. Whitney. 1947. On a Test of Whether one of Two Random Variables is Stochastically Larger than the Other. The Annals of Mathematical Statistics 18, 1 (1947), 50–60. http://www.jstor.org/stable/2236101
- [22] Ryan Marcus, Parimarjan Negi, Hongzi Mao, Nesime Tatbul, Mohammad Alizadeh, and Tim Kraska. 2021. Bao: Making learned query optimization practical. In Proceedings of the 2021 International Conference on Management of Data. 1275–1288.
- [23] Ryan Marcus, Parimarjan Negi, Hongzi Mao, Chi Zhang, Mohammad Alizadeh, Tim Kraska, Olga Papaemmanouil, and Nesime Tatbul. 2019. Neo: A Learned Query Optimizer. Proceedings of the VLDB Endowment 12, 11 (2019).
- [24] Ryan Marcus and Olga Papaemmanouil. 2018. Deep Reinforcement Learning for Join Order Enumeration. In Proceedings of the First International Workshop on Exploiting Artificial Intelligence Techniques for Data Management (Houston, TX, USA) (aiDM’18). Association for Computing Machinery, New York, NY, USA, Article 3, 4 pages. https://doi.org/10.1145/3211954.3211957
- [25] Ryan Marcus and Olga Papaemmanouil. 2018. Towards a Hands-Free Query Optimizer through Deep Learning. (09 2018).
- [26] Lili Mou, Ge Li, Lu Zhang, Tao Wang, and Zhi Jin. 2016. Convolutional Neural Networks over Tree Structures for Programming Language Processing. In Proceedings of the Thirtieth AAAI Conference on Artificial Intelligence (Phoenix, Arizona) (AAAI’16). AAAI Press, 1287–1293.
- [27] Nippon Telegraph and Telephone Corporation. 2012. pg_hint_plan Documentation. https://pghintplan.osdn.jp/pg_hint_plan.html. [Online; accessed August, 2023].
- [28] Dušan Petković. 2011. Dynamic Programming Algorithm vs. Genetic Algorithm: Which is Faster?. In Research and Development in Intelligent Systems XXVII, Max Bramer, Miltos Petridis, and Adrian Hopgood (Eds.). Springer London, London, 483–488.
- [29] Egor Rogov. 2022. Queries in PostgreSQL: Sort and Merge. https://postgrespro.com/blog/pgsql/5969770. [Online; accessed August, 2023].
- [30] Stuart Russell and Peter Norvig. 2010. Artificial Intelligence: A Modern Approach (3 ed.). Prentice Hall.
- [31] Greg Smith, Robert Treat, and Christopher Browne. 2021. Tuning Your PostgreSQL Server. https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server. [Online; accessed August, 2023].
- [32] Richard S. Sutton and Andrew G. Barto. 2018. Reinforcement Learning: An Introduction (second ed.). The MIT Press. http://incompleteideas.net/book/the-book-2nd.html
- [33] Kai Sheng Tai, Richard Socher, and Christopher D. Manning. 2015. Improved Semantic Representations From Tree-Structured Long Short-Term Memory Networks. In Proceedings of the 53rd Annual Meeting of the Association for Computational Linguistics and the 7th International Joint Conference on Natural Language Processing (Volume 1: Long Papers). Association for Computational Linguistics, Beijing, China, 1556–1566. https://doi.org/10.3115/v1/P15-1150
- [34] The PostgreSQL Global Development Group. 2023. Genetic Query Optimization (GEQO) in PostgreSQL. https://www.postgresql.org/docs/current/geqo-pg-intro.html. [Online; accessed August, 2023].
- [35] Transaction Processing Performance Council. 2023. TPC Benchmarks Overview. https://www.tpc.org/information/benchmarks5.asp. [Online; accessed August, 2023].
- [36] Li Wan, Matthew Zeiler, Sixin Zhang, Yann Le Cun, and Rob Fergus. 2013. Regularization of Neural Networks using DropConnect. In Proceedings of the 30th International Conference on Machine Learning (Proceedings of Machine Learning Research), Sanjoy Dasgupta and David McAllester (Eds.), Vol. 28. PMLR, Atlanta, Georgia, USA, 1058–1066. https://proceedings.mlr.press/v28/wan13.html
- [37] Chihping Wang and Ming-Syan Chen. 1996. On the complexity of distributed query optimization. IEEE Transactions on Knowledge and Data Engineering 8, 4 (1996), 650–662.
- [38] Geoffrey I. Webb. 2010. Overfitting. Springer US, Boston, MA, 744–744. https://doi.org/10.1007/978-0-387-30164-8_623
- [39] Zongheng Yang, Wei Lin Chiang, Sifei Luan, Gautam Mittal, Michael Luo, and Ion Stoica. 2022. Balsa: Learning a Query Optimizer Without Expert Demonstrations. Proceedings of the ACM SIGMOD International Conference on Management of Data (6 2022), 931–944. https://doi.org/10.1145/3514221.3517885
- [40] Zongheng Yang, Amog Kamsetty, Sifei Luan, Eric Liang, Yan Duan, Xi Chen, and Ion Stoica. 2020. NeuroCard: One Cardinality Estimator for All Tables. Proc. VLDB Endow. 14, 1 (sep 2020), 61–73. https://doi.org/10.14778/3421424.3421432
- [41] Xiang Yu, Chengliang Chai, Guoliang Li, and Jiabin Liu. 2022. Cost-based or learning-based? A hybrid query optimizer for query plan selection. Proceedings of the VLDB Endowment 15, 13 (2022), 3924–3936.
- [42] Xiang Yu, Guoliang Li, Chengliang Chai, and Nan Tang. 2020. Reinforcement learning with tree-lstm for join order selection. In 2020 IEEE 36th International Conference on Data Engineering (ICDE). IEEE, 1297–1308.
- [43] Zhang Yunjia, Chronis Yannis, Patel Jignesh M., and Rekatsinas Theodoros. 2023. Simple Adaptive Query Processing vs. Learned Query Optimizers: Observations and Analysis. Proc. VLDB Endow. 16, 9 (2023), 2962–2975.
- [44] Rong Zhu, Wei Chen, Bolin Ding, Xingguang Chen, Andreas Pfadler, Ziniu Wu, and Jingren Zhou. 2023. Lero: A Learning-to-Rank Query Optimizer. arXiv preprint arXiv:2302.06873 (2023).
