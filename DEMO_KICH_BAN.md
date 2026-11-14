# Kịch bản demo – Mục 4 "Cài đặt minh họa và kế hoạch thực nghiệm"

Thời lượng: **khoảng 10 phút**. Mạch: chọn plan quan trọng (26a) → LQO có thắng PostgreSQL không (TN1) →
mô hình gọn nhẹ thì sao (TN2) → hạn chế, kết luận. Câu **26a** quay lại ở TN2 để nối hai thí nghiệm.

## 1. Nội dung sẽ demo

| # | Mục | Nội dung | Màn hình | Thông điệp |
|---|---|---|---|---|
| 1 | 4.1 | Môi trường, IMDB/JOB, 9 split | `docker ps`, tab 0 | Giống bài báo trừ bộ nhớ → so xu hướng |
| 2 | 4.2 | Câu 26a chạy 3 cách *(chạy trực tiếp)* | `demo_26a.sh` | Chọn plan đúng/sai chênh hơn 30× |
| 3 | 4.2 | Bao, HybridQO so với PostgreSQL và bài báo | Tab 1 | LQO chưa thắng PostgreSQL – khớp bài báo |
| 4 | 4.2 | Vì sao thua: chi phí, chọn sai plan | Tab 2 | Bao thêm 100–190 ms/câu, đổi plan sai nhiều hơn đúng |
| 5 | 4.2 | Ablation 8.3–8.5 + Bao-Full/Bao-50 *(chạy trực tiếp)* | Tab 2, `demo_83.sh` | Đổi dữ liệu/cấu hình → lựa chọn đổi theo |
| 6 | 4.3 | Mô hình phân loại, Oracle, H1/H2, câu 26a | Tab 3 | Oracle 1,53× nhưng mô hình 0,80–0,82× |
| 7 | 4.3 | Prototype câu 23a *(chạy trực tiếp)* | Tab 5 | Chi phí mô hình gọn nhẹ chỉ ~40 ms |
| 8 | 4.4 | Hạn chế, kết luận | Tab 2 | Tái lập được bài báo; cần tránh chọn sai |

## 2. Kịch bản demo

**Mở đầu (0:30) · GitHub repo**

> "Em là Thúy Vi, nhóm 1, demo mục 4 cho bài báo *Is Your Learned Query Optimizer Behaving As You Expect?*
> Thí nghiệm 1 kiểm chứng kết luận của bài báo trên máy nhóm; Thí nghiệm 2 thử một hướng gọn nhẹ hơn."

**4.1 Môi trường (1:00) · `docker ps` → tab "0. Dữ liệu IMDB & JOB"**

> "Nhóm dựng PostgreSQL 12.5, pg_hint_plan và Bao trong Docker trên Mac; HybridQO và kết quả chính của Bao chạy
> trên Kaggle. Khác biệt lớn nhất là bộ nhớ – bài báo 32 GB / 4 GB, Kaggle 8 GB / 512 MB – nên nhóm chỉ so xu hướng.
> Dữ liệu giống bài báo: IMDB, 113 câu JOB, 9 split; Base Query khó nhất vì câu test thuộc họ chưa từng học."

**Chọn plan quan trọng đến mức nào? (1:15) · `bash scripts/demo_26a.sh`**

> "Cùng câu 26a, em ép PostgreSQL chạy 3 cách… Tắt index scan nhanh gấp 5, tắt hash join chậm gấp 6 –
> chênh hơn 30 lần. LQO học cách chọn như vậy. Vậy nó có thắng PostgreSQL không?"

**4.2 Thí nghiệm 1 (3:30)**

*Tab "1. Bài báo vs Nhóm":*

> "Nhóm chạy lại Bao và HybridQO trên 9 split, 233 lần kiểm tra; Neo, Balsa, LEON dùng log tác giả.
> Bảng gần như toàn màu cam – chậm hơn PostgreSQL. Bao 0,92× (bài báo 0,83×), HybridQO 0,97× (bài báo 1,00×),
> HybridQO thua ít câu hơn Bao. Hai kết luận chính của bài báo khớp với nhóm."

*Tab "2. Nhóm: Thí nghiệm 1" → "Khai phá: Bao thua ở đâu?":*

> "Hai lý do: Bao tốn thêm 100–190 ms mỗi câu, trong khi nửa số câu chạy dưới 0,5 giây; và Bao đổi plan ở 66 câu
> nhưng chọn sai nhiều hơn đúng. HybridQO gần như giữ plan PostgreSQL nên không thua nhiều, cũng không thắng."

*Tab con "Lặp lại như tác giả" → `bash scripts/demo_83.sh`:*

> "Nhóm lặp lại ablation như tác giả. Tắt GEQO hay bitmap scan: tổng gần như không đổi nhưng 10–12 câu đổi mạnh,
> 24b chậm 9,8 lần – bài báo 9,9. Với 8.3, em nạp hai model Bao: train trên IMDB đầy đủ và trên IMDB 50%, rồi chạy
> trên dữ liệu đầy đủ. Bao-50 chọn tắt nested loop, câu 3c chậm khoảng 15 lần – dữ liệu đổi thì mô hình chọn sai.
>
> Kết luận bài báo đúng trên máy nhóm. Vậy một mô hình gọn nhẹ, gần như không tốn chi phí, có làm tốt hơn không?"

**4.3 Thí nghiệm 2 (2:30) · Tab "3. Nhóm: Thí nghiệm 2"**

> "Mỗi câu chạy 6 phương án – mặc định và tắt một toán tử – nhãn là phương án nhanh nhất. Đặc trưng lấy từ SQL và
> EXPLAIN, có trước khi chạy; ba mô hình Decision Tree, Random Forest, LightGBM, chia theo 9 split.
> Oracle – luôn chọn đúng – đạt 1,53×: dư địa có thật. Nhưng mô hình chỉ 0,80–0,82×.
> H1 – nhanh hơn PostgreSQL – bị bác bỏ; mô hình thua ít câu hơn Bao nhưng tổng vẫn thua.
> H2 – kém nhất với câu chưa từng học – được chấp nhận: accuracy Base Query 0,44 so với 0,54–0,64."

*Tab con "Xem một câu" (26a):*

> "Quay lại 26a: tốt nhất là tắt index scan, khoảng 1 giây, nhưng mô hình hay chọn tắt hash join – 32 giây.
> Vài lần chọn sai như vậy xóa hết phần lợi ở các câu khác."

*Tab "5. Thử mô hình" (23a) → Hỏi mô hình → chạy:*

> "Đây là quy trình chạy thật: EXPLAIN, trích đặc trưng, mô hình chọn, SET rồi chạy. Toàn bộ chỉ khoảng 40 ms,
> ít hơn nhiều so với Bao. Hướng gọn nhẹ giải quyết được chi phí; vấn đề còn lại là chọn sai."

**4.4 Hạn chế và kết luận (1:00) · Tab 2 → "Thiết kế & hạn chế"**

> "Hạn chế: bộ nhớ thấp hơn bài báo; HybridQO chỉ train 10 epoch nên gần như không đổi plan; Bao và HybridQO train
> 1 lần mỗi split; Oracle chỉ tốt nhất trong 6 phương án.
> Tóm lại, nhóm tái lập được kết luận bài báo: LQO chưa thắng PostgreSQL ổn định. Mô hình gọn nhẹ có dư địa 1,53×
> nhưng chọn sai vài câu là mất hết lợi ích – hướng tiếp theo là không chắc thì giữ PostgreSQL mặc định.
> Em cảm ơn thầy và các bạn."

---

## Chuẩn bị

- `bash scripts/demo_start.sh` (làm nóng cache, mở dashboard http://localhost:8501); demo chạy ở terminal thứ hai.
- Chạy thử `demo_26a.sh` (≈ 5,7 s / 1,0 s / 32 s) và `demo_83.sh` (3c: 0,19 s → 3,1 s) một lần.
- Chọn sẵn 26a ở tab 3 "Xem một câu", 23a ở tab 5. Zoom 125%, bật Không làm phiền.
- Quay: `Cmd+Shift+5` → Record Entire Screen; nên quay từng phần rồi ghép.
- Dự phòng: `bash scripts/demo_ablation.sh` (tắt GEQO, bitmap scan) nếu còn thời gian.

## Khi bị hỏi

- **Sao không chạy Neo, Balsa, LEON?** Cần GPU và 20–130 giờ mỗi split; dùng log tác giả.
- **Sao HybridQO không thắng câu nào?** Chỉ 10 epoch (tác giả 40–49) nên đổi plan 8/233 câu.
- **Sao câu bài báo nêu ở 8.3 không lặp lại?** Model phụ thuộc lần train; nhóm thấy hiện tượng ở câu khác (28a, 3c), cùng chiều nhưng nhẹ hơn.
- **Sao TN2 không dùng CEB-IMDb?** Tập trung JOB để so trực tiếp với TN1 trên cùng 9 split.
