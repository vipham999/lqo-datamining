# Kịch bản lời thoại demo (10 phút)

Bản để **tập nói**. Mỗi màn hình gồm: **[Thao tác]** làm gì trên máy, sau đó là lời nói. Chữ **in đậm** trong lời nói là chỗ nên nhấn giọng.
Chuẩn bị môi trường và màn hình: [CHUAN_BI_DEMO.md](CHUAN_BI_DEMO.md) mục 1. Giải thích sâu khi bị hỏi: [HOI_DAP_DEMO.md](HOI_DAP_DEMO.md).

**Mạch:** chọn plan quan trọng thế nào → TN1: LQO có thắng PostgreSQL không → TN2: mô hình nhóm → Khai phá dữ liệu: vì sao thua, sửa thế nào → Chạy thật → Kết luận.

**Câu chốt:** *"Đúng nhiều lần chưa đủ, phải tránh được lần sai đắt."*

| # | Màn hình | Thời gian | Mốc |
|---|---|---|---|
| 1 | Terminal `demo_6cach.sh` + tab 0 | 1,5' | 0:00–1:30 |
| 2 | Tab 1. Bài báo vs Nhóm | 0,75' | 1:30–2:15 |
| 3 | Tab 2. Thí nghiệm 1 | 1,25' | 2:15–3:30 |
| 4 | Tab 3. Thí nghiệm 2 | 1,5' | 3:30–5:00 |
| 5 | **Tab 4. Khai phá dữ liệu** | **2,5'** | 5:00–7:30 |
| 6 | Tab 5. Demo mô hình | 1,5' | 7:30–9:00 |
| 7 | Kết luận | 1' | 9:00–10:00 |

---

## 1. Mở đầu: cùng một câu, chênh nhau 14 lần (0:00–1:30)

**[Thao tác]** Ở Terminal gõ `bash scripts/demo/demo_6cach.sh`, Enter. Script chạy khoảng 45 giây, trong lúc đó chuyển sang dashboard, **tab 0**.

> "Em chào cô. Nhóm em demo phần cài đặt và thực nghiệm cho bài báo *Is Your Learned Query Optimizer Behaving As You Expect?* Trong lúc script này chạy, em giới thiệu môi trường."

**[Tab 0]**

> "Nhóm dựng 2 container Docker. Một container là **PostgreSQL 12.5**, đúng phiên bản bài báo, có cài extension của Bao. Container còn lại là server chứa mô hình của Bao. Các lần chạy lớn của Bao và HybridQO thì chạy trên Kaggle.
> Dữ liệu giống bài báo: CSDL **IMDB**, **113 câu JOB** thuộc **33 họ**, và **9 cách chia train/test**.
> Máy nhóm ít bộ nhớ hơn máy tác giả nên nhóm **so tỉ lệ, không so số giây**. Số trên dashboard đo trên máy Mac của nhóm. Phần chạy trực tiếp hôm nay chạy trên máy này nên số giây sẽ khác."

**[Quay lại Terminal, chỉ vào 3 dòng: mặc định, tắt index scan, tắt nested loop]**

> "Đây là câu 7c. Em ép PostgreSQL chạy câu này theo 6 cách: giữ nguyên, hoặc tắt 1 trong 5 loại toán tử.
> Mặc định mất khoảng **1,5 giây**. Tắt index scan còn khoảng **0,8 giây**, nhanh gần gấp đôi. Nhưng tắt nested loop thì lên khoảng **11 giây**.
> Cùng một câu SQL mà chênh nhau khoảng **14 lần**. Learned query optimizer, gọi tắt là LQO, là mô hình học cách chọn như vậy.
> **Vậy nó có thắng được PostgreSQL không?**"

*Số giây mỗi lần chạy hơi khác nhau. Đọc số đang hiện trên màn hình.*

---

## 2. Tab 1 – Bài báo vs Nhóm (1:30–2:15)

**[Thao tác]** Chỉ vào bảng/biểu đồ tổng.

> "Nhóm chạy lại **Bao** và **HybridQO** trên cả 9 split, tổng **233 lần kiểm tra**. Neo, Balsa và LEON cần GPU mạnh nên nhóm dùng log của tác giả.
> Kết quả: Bao chỉ đạt **0,92 lần** tốc độ PostgreSQL, bài báo là 0,83. HybridQO đạt **0,97**, bài báo là 1,00. **Dưới 1 nghĩa là chậm hơn PostgreSQL.**
> Như vậy kết luận của bài báo lặp lại được trên máy nhóm: **LQO chưa thắng PostgreSQL.**"

---

## 3. Tab 2 – Thí nghiệm 1: vì sao LQO thua (2:15–3:30)

**[Thao tác]** Chỉ vào 2 phát hiện ở đầu tab.

> "Nhóm tìm ra hai lý do.
> **Thứ nhất là chi phí suy nghĩ.** Mỗi câu Bao tốn thêm khoảng **0,15 giây** để lập 5 plan và hỏi mô hình. Với câu ngắn, phần này còn lâu hơn cả chạy câu. Kết quả Bao thắng 8, hòa 46, thua 179 lần.
> **Thứ hai là đổi sai.** Khi Bao đổi plan thì số lần đổi sai nhiều hơn số lần đổi đúng.
> HybridQO thì ngược lại, rất cẩn thận: chỉ đổi plan **8 trên 233** lần, còn lại giữ plan PostgreSQL. Nhưng nó vẫn tốn thời gian suy nghĩ nên tổng vẫn chậm hơn một chút."

**[Thao tác]** Cuộn tới biểu đồ ablation (phát hiện 3).

> "Nhóm cũng làm lại **ablation** như tác giả, tức là tắt từng thành phần cho cả workload. Tắt GEQO hay tắt bitmap scan thì tổng thời gian gần như không đổi, nhưng có **10 đến 12 câu thay đổi mạnh**, cả nhanh hơn lẫn chậm hơn.
> Ngoài ra, mô hình Bao train trên IMDB 50% mà chạy trên dữ liệu đầy đủ thì chọn sai ở câu 3c và 11b. Nghĩa là **dữ liệu thay đổi một chút là mô hình chọn sai.**"

---

## 4. Tab 3 – Thí nghiệm 2: mô hình của nhóm (3:30–5:00)

**[Thao tác]** Nói phần đầu tab.

> "Từ Thí nghiệm 1, nhóm thử một hướng nhẹ hơn.
> **Input** là 34 con số: 11 con số đếm trên câu SQL, như số bảng hay số điều kiện LIKE, và 23 con số lấy từ plan **EXPLAIN** của PostgreSQL, như số hash join, số nested loop, cost ước lượng. Tất cả có được **trước khi chạy câu**, chỉ mất vài mili giây.
> **Output** là 1 trong 6 phương án: giữ nguyên, hoặc tắt 1 trong 5 toán tử.
> Để có nhãn, nhóm **chạy thật cả 6 phương án** cho đủ 113 câu, rồi lấy phương án nhanh nhất. Nếu nó không nhanh hơn mặc định ít nhất 5% thì nhãn vẫn là giữ nguyên.
> Nhóm thử 3 mô hình: **Decision Tree, Random Forest và LightGBM**.
> Nếu lần nào cũng chọn đúng, gọi là **Oracle**, thì nhanh hơn PostgreSQL **1,53 lần**, nên dư địa là có thật. Nhưng mô hình chỉ đạt **0,80 đến 0,82 lần**."

**[Thao tác]** Cuộn xuống mục *Xem một câu* (đã chọn sẵn **26a**).

> "Vì sao lại chậm hơn? Ví dụ câu 26a, đo trên máy Mac: tốt nhất là tắt index scan, khoảng **1 giây**. Nhưng mô hình chọn tắt hash join, đúng phương án tệ nhất, mất **32 giây**, trong khi PostgreSQL chỉ **5,7 giây**.
> **Một lần sai như vậy xoá hết phần lợi ở hàng chục câu khác.**
> Vì vậy giả thuyết H1, mô hình nhanh hơn PostgreSQL, bị bác bỏ. Giả thuyết H2, mô hình kém nhất với câu chưa từng học, được chấp nhận: độ chính xác ở split Base query chỉ **0,44**, các split khác từ 0,54 đến 0,64."

---

## 5. Tab 4 – Khai phá dữ liệu: vì sao thua và sửa thế nào (5:00–7:30)

*Đây là phần riêng của nhóm và quan trọng nhất. Nói chậm.*

**[Thao tác]** Chỉ vào ô "Vấn đề" và 3 bước.

> "Đây là phần riêng của nhóm, **không có trong bài báo**. Mô hình đoán đúng khoảng một nửa mà tổng vẫn chậm hơn PostgreSQL. Nhóm khai phá chính dữ liệu đã đo để tìm nguyên nhân, rồi sửa và đo lại."

**[Thao tác]** Chỉ vào phát hiện 1 (biểu đồ 2 thanh).

> "Nhóm dùng **luật kết hợp**, có dạng 'NẾU câu có đặc điểm A THÌ tắt X có lợi'. Máy thử **695 luật**, giữ lại **37 luật** đáng tin sau kiểm định thống kê.
> Luật nổi bật nhất là: câu có từ 2 hash join trở lên thì tắt hash join. Luật này đúng **13 trên 28** câu, gấp **2,8 lần** đoán bừa. Nghe rất tốt.
> Nhưng cô nhìn biểu đồ: áp cho cả 28 câu thì 13 câu nhanh hơn chỉ được tổng khoảng **1 giây**, còn 15 câu chậm hơn mất tới **77 giây**.
> Bài học là: **đúng nhiều lần chưa đủ, phải tránh được lần sai đắt.** Không chắc thì nên giữ nguyên PostgreSQL."

**[Thao tác]** Chỉ vào phát hiện 2 (biểu đồ cột xám và xanh).

> "Nhóm sửa đúng theo bài học đó: mô hình chỉ đổi cách chạy khi **độ tin từ 60% trở lên**, còn lại giữ nguyên PostgreSQL.
> Random Forest từ 0,80 lên **1,06 lần**, tức là **đã nhanh hơn PostgreSQL**. Kết quả ổn định khi ngưỡng từ 50% đến 70%, nên không phải chọn may.
> Lúc này mô hình chỉ đổi **6 trên 233** lần, đều là tắt nested loop ở họ 17, và lần nào cũng nhanh hơn.
> Ý tưởng này cũng giống cơ chế an toàn của HybridQO, nhưng nhóm làm bằng **vài dòng code**."

**[Kết luận tab]**

> "Khai phá dữ liệu chỉ ra đúng nguyên nhân: mô hình đổi cách chạy **cả khi không chắc**. Chỉ một sửa đổi đơn giản đã giúp mô hình thắng PostgreSQL."

*Nếu cô hỏi sâu: bật "Hiện chi tiết kỹ thuật" để xem bảng luật, các ngưỡng và 28 câu cụ thể.*

---

## 6. Tab 5 – Demo mô hình chạy thật (7:30–9:00)

**[Thao tác]** Chọn câu **23a**, mô hình **Random Forest**, giữ tick ô *"Không cho mô hình học các câu cùng họ"*.

> "Cuối cùng là prototype chạy thật. Em chọn câu 23a.
> Ô này bỏ **cả họ 23**, tức là 23a, 23b, 23c, khỏi dữ liệu huấn luyện. Các câu cùng họ có cùng cấu trúc, chỉ khác hằng số lọc. Nếu cho mô hình học 23b, 23c thì gần như nó đã xem đáp án trước. **Bỏ cả họ thì 23a là câu mới thật.**"

**[Thao tác]** Bấm **Hỏi mô hình**. Chỉ vào Bước 2 rồi Bước 3.

> "Mô hình **chưa chạy câu**. Nó chỉ hỏi PostgreSQL định chạy thế nào bằng EXPLAIN, rồi trích 34 đặc trưng ở đây.
> Mô hình chọn **tắt hash join**, độ tin **37%**. Toàn bộ thời gian ra quyết định khoảng **25 mili giây**, còn Bao cần khoảng 150."

**[Thao tác]** Bấm **Chạy trên PostgreSQL** (khoảng 10 giây).

> "Bước 4 để **kiểm tra mô hình đúng hay sai**: chạy thật cả 6 phương án trên PostgreSQL. Cũng chính bằng cách này nhóm tạo nhãn cho Thí nghiệm 2.
> Kết quả: phương án nhanh nhất đúng là **tắt hash join**, nhanh hơn mặc định khoảng 1,5 lần. **Mô hình chọn đúng.**"

**[Thao tác]** Đổi sang **16c**, bấm **Hỏi mô hình** rồi **Chạy trên PostgreSQL** (khoảng 30 giây). *Trong lúc chờ, nói đoạn dưới.*

> "Còn câu 16c, mô hình chọn tắt nested loop, nhưng chỉ tin **48%**.
> Chạy thật thì PostgreSQL mặc định khoảng **1,3 giây**, còn theo mô hình lên khoảng **2,9 giây**, chậm hơn gấp đôi.
> Đây đúng là kiểu **đổi khi không chắc** mà tab 4 đã chỉ ra. Áp luật 'dưới 60% thì giữ nguyên' là tránh được lần sai này."

*Đọc số đang hiện trên màn hình; mỗi lần chạy hơi khác.*

---

## 7. Hạn chế và kết luận (9:00–10:00)

**[Thao tác]** Giữ nguyên màn hình, hoặc quay về tab 4 để chỉ lại con số 1,06×.

> "Về hạn chế, nhóm có 4 điểm.
> Một, máy nhóm ít bộ nhớ hơn bài báo nên chỉ so xu hướng.
> Hai, HybridQO chỉ train được **11 epoch** so với 50 của tác giả vì Kaggle giới hạn 12 giờ. Tuy vậy, log tác giả cho thấy từ epoch 10 kết quả đã ổn định.
> Ba, Oracle chỉ là tốt nhất trong 6 cách thử, chưa phải tối ưu tuyệt đối.
> Bốn, ngưỡng 60% mới giúp ở **6 trên 233** lần, đều thuộc họ 17.
>
> Tóm lại, nhóm **tái lập được kết luận của bài báo**: LQO chưa thắng PostgreSQL một cách ổn định. Khai phá dữ liệu cho thấy nguyên nhân là **đổi plan cả khi không chắc**. Với luật đơn giản 'không chắc thì giữ nguyên', mô hình của nhóm đã nhanh hơn PostgreSQL **1,06 lần**.
> Em cảm ơn cô ạ."

---

## Nếu bị lố giờ

Cắt theo thứ tự:
1. Bỏ câu 16c ở tab 5, chỉ chạy 23a. Nói kết quả 16c bằng lời.
2. Bỏ tab 1, nói số Bao/HybridQO bằng lời ở đầu tab 2.
3. Bỏ biểu đồ ablation ở tab 2.

**Không cắt** `demo_6cach.sh` và tab 4.

---

## Trả lời nhanh khi cô hỏi

Mỗi câu chỉ cần nói 1–2 câu. Muốn giải thích sâu thì xem mục tương ứng trong [HOI_DAP_DEMO.md](HOI_DAP_DEMO.md).

| Cô hỏi | Trả lời ngắn |
|---|---|
| Bước 4 có phải ablation không? | "Không ạ. Bước 4 chạy thật cả 6 phương án để có đáp án đúng rồi so với lựa chọn của mô hình. Ablation là tắt GEQO, bitmap scan cho cả workload ở Thí nghiệm 1." |
| "Giữ nguyên PostgreSQL" là gì? | "Là không SET gì, mọi cờ enable_* đều bật, PostgreSQL tự chọn plan rẻ nhất theo ước lượng. 5 phương án kia mỗi cái chỉ tắt đúng 1 loại toán tử." |
| Input, output của mô hình? | "Input là 34 con số từ câu SQL và plan EXPLAIN, có trước khi chạy. Output là 1 trong 6 phương án. Nhãn có được bằng cách chạy thật cả 6 phương án." |
| Mô hình dựa vào đặc trưng nào? (feature importance) | "Quan trọng nhất là cost ước lượng và độ phức tạp của câu: số node trong plan, độ dài SQL, số điều kiện lọc. Không phải số lượng từng loại toán tử." |
| Sao Decision Tree chọn sai 23a? | "Cây chỉ hỏi 3 câu rồi đưa 23a vào một lá chỉ có 4 câu train nên dễ sai, nhưng cũng chỉ chậm 4%, tính là hòa. Random Forest và LightGBM gộp nhiều cây nên chọn đúng." |
| Sao phải bỏ cả họ? | "Câu cùng họ có cùng cấu trúc. Không bỏ thì Random Forest đoán đúng 88%, nhưng đó là trí nhớ; bỏ cả họ thì còn 50%, đó mới là khả năng thật." |
| 6 phương án lấy từ đâu? | "Dùng đúng 6 cờ enable_* mà Bao dùng, nhưng cách chia là của nhóm: mỗi phương án tắt 1 toán tử. 'Tắt hash join' và 'tắt index scan' không có trong arm nào của Bao." |
| HybridQO hoạt động thế nào? | "Nó chọn 2 bảng nối đầu tiên rồi để PostgreSQL lập phần còn lại, ép bằng hint Leading. Dùng MCTS tìm ứng viên, mạng TreeLSTM đoán thời gian, KNN để biết khi nào không nên tin mô hình. Rất cẩn thận nên chỉ đổi 8/233 lần, nhưng tốn thời gian suy nghĩ nên chỉ đạt 0,97 lần." |
| Khác Bao thế nào? | "Bao chạy mạng neural trên cây plan của 5 arm và học kiểu bandit, chỉ chạy thật arm nó chọn. Nhóm đo thật đủ 6 phương án để có nhãn rồi dùng mô hình cây nhỏ, ra quyết định khoảng 25 ms so với 150 ms của Bao." |
| Câu 16b? | "Mô hình chọn tắt nested loop, tin 54%, nhanh 3,5 lần trên máy demo. Nhưng 54% dưới ngưỡng 60% nên áp ngưỡng thì mất lần thắng này. Đó là cái giá của việc chơi an toàn." (Không chạy, mất 4–5 phút.) |
| Xem Bao chọn sai chạy thật? | Chạy `bash scripts/demo/demo_83.sh` (khoảng 1,5 phút). |
