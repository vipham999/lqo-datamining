# Chuẩn bị demo

Thời lượng **10 phút demo** và **5–7 phút đi qua code** (khi cô yêu cầu).
Giải thích chi tiết từng khái niệm nằm trong [HOI_DAP_DEMO.md](HOI_DAP_DEMO.md).

**Máy demo:** máy WSL (Linux trên Windows). Số trên dashboard đều đo trên máy Mac của nhóm; phần chạy trực tiếp
(`demo_6cach.sh`, tab 5) đo trên máy demo nên số giây khác. Cần nói rõ điều này với cô (xem màn hình 1).

**Mạch trình bày:** chọn plan quan trọng đến mức nào (7c) → TN1: LQO có thắng PostgreSQL không → TN2: mô hình của nhóm
→ Khai phá dữ liệu: vì sao thua, sửa thế nào → Demo chạy thật → Hạn chế, kết luận.

**Câu chốt cần nhớ:** *"Đúng nhiều lần chưa đủ, phải tránh được lần sai đắt."*

---

## 1. Chuẩn bị môi trường

### 1.1. Hôm trước
- [ ] Tập nói 1–2 lần theo mục 3, bấm giờ.
- [ ] Thuộc các con số ở mục 2.
- [ ] Đọc phần **"câu gọn để nói với cô"** trong [HOI_DAP_DEMO.md](HOI_DAP_DEMO.md).
- [ ] Chụp màn hình kết quả `demo_6cach.sh`, `demo_83.sh` và tab 5 (câu 23a, 16c) để dự phòng.

### 1.2. Trước giờ demo 30 phút
```bash
cd ~/workspace/personal/lqo-datamining

# 1. Kiểm tra 2 container
docker ps                                   # phải thấy pg_bao và bao_server
# nếu thiếu: docker compose -f infra/docker-compose.yml up -d

# 2. Làm nóng cache (5–10 phút) cho thời gian chạy ổn định
docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh

# 3. Mở dashboard (nếu chưa chạy) → http://localhost:8501
bash scripts/demo/demo_start.sh --no-warm

# 4. Chạy thử mỗi script 1 lần (vừa kiểm tra, vừa làm nóng các câu sẽ demo)
bash scripts/demo/demo_6cach.sh             # câu 7c, 6 cách: ~1,5 s / tắt index scan ~0,8 s / tắt nested loop ~11 s; ~45 giây
bash scripts/demo/demo_83.sh                # dự phòng khi cô hỏi; Bao-50 chọn tắt nested loop ở 3c, 11b
```
`demo_83.sh` nạp PyTorch lần đầu có thể mất hơn 30 giây. Script đã được sửa để chờ tối đa 2 phút. Chạy thử trước một lần thì lúc demo nạp model chỉ mất khoảng 4 giây.

### 1.3. Chuẩn bị màn hình
- [ ] **Dashboard** (zoom 125%):
  - Tab 5: chạy thử đủ 4 bước một lần với **16c** (để làm nóng), rồi chọn lại **23a**, bấm *Hỏi mô hình* rồi *Chạy trên PostgreSQL* một lần.
  - Tab 3: bật *Hiện số liệu chi tiết*, vào *Xem một câu*, chọn **26a**.
  - Tab 2: cuộn sẵn tới biểu đồ ablation (phát hiện 3).
  - Quay lại tab 0.
- [ ] **Terminal**: đã `cd` vào thư mục dự án, chữ to (`Ctrl +`).
- [ ] **VS Code**: mở sẵn các file ở mục 5, đúng thứ tự, mỗi file một tab.
- [ ] Bật *Không làm phiền*, tắt Zalo/Messenger, cắm sạc. Trong cài đặt nguồn của Windows, tắt chế độ ngủ và tắt màn hình tự động.

---

## 2. Con số cần thuộc

| Nội dung | Số |
|---|---|
| Bao so với PostgreSQL (Kaggle) | **0,92×** (bài báo 0,83×); thắng 8 / hòa 46 / thua 179 |
| HybridQO | **0,97×** (bài báo 1,00×); chỉ đổi plan 8/233 lần |
| Thời gian Bao gọi mô hình | khoảng **0,15 s mỗi câu** |
| Oracle (luôn chọn đúng trong 6 phương án) | **1,53×** |
| Mô hình của nhóm (DT, RF, LightGBM) | **0,80–0,82×** |
| Thời gian mô hình nhóm ra quyết định | khoảng **25 ms** (EXPLAIN + suy luận) |
| Câu 26a (đo trên Mac, có trên dashboard) | PostgreSQL 5,7 s; tắt index scan 0,95 s; **mô hình chọn tắt hash join 32 s** |
| Câu 7c (live, máy demo) | mặc định ~1,5 s; tắt index scan ~0,8 s; tắt nested loop ~11 s (chênh ~14 lần) |
| Tab 5 live, máy demo | 23a: chọn tắt hash join (37%), 0,22 → 0,13 s, đúng. 16c: chọn tắt nested loop (48%), 1,3 → 2,9 s, **sai** |
| Luật kết hợp | thử 695, giữ 37; luật "≥2 hash join" đúng 13/28, lift 2,8; được 1 s, mất 77 s |
| RF với ngưỡng tin 60% | **1,06×**, đổi 6/233 lần, đều ở họ 17 |
| Độ chính xác Base query (H2) | 0,44 (các split khác 0,54–0,64) |
| Dữ liệu | 113 câu, 33 họ, 9 split, 233 lần kiểm tra |

---

## 3. Kịch bản demo (10 phút)

Bản lời thoại đầy đủ để tập nói, kèm bảng trả lời nhanh: [KICH_BAN_DEMO.md](KICH_BAN_DEMO.md).

| # | Màn hình | Nội dung | Thời gian | Mốc giờ |
|---|---|---|---|---|
| 1 | Terminal `demo_6cach.sh` + tab 0 | Mở đầu: chọn plan quan trọng đến mức nào | 1,5' | 0:00–1:30 |
| 2 | Tab 1. Bài báo vs Nhóm | TN1: kết quả tái lập | 0,75' | 1:30–2:15 |
| 3 | Tab 2. Nhóm: Thí nghiệm 1 | TN1: vì sao Bao thua | 1,25' | 2:15–3:30 |
| 4 | Tab 3. Nhóm: Thí nghiệm 2 | TN2: mô hình của nhóm, câu 26a | 1,5' | 3:30–5:00 |
| 5 | **Tab 4. Khai phá dữ liệu** | Vì sao thua, sửa thế nào | **2,5'** | 5:00–7:30 |
| 6 | Tab 5. Demo mô hình | Chạy thật 23a (đúng) và 16c (sai) | 1,5' | 7:30–9:00 |
| 7 | Giữ tab 5 (hoặc quay về tab 4) | Hạn chế và kết luận | 1' | 9:00–10:00 |

Không chạy `demo_83.sh` và không mở tab "Thiết kế & hạn chế". Ablation và hạn chế chỉ nói bằng lời.

### Màn hình 1: Terminal `demo_6cach.sh` → tab 0 → Terminal (1,5')
**Thao tác:** gõ `bash scripts/demo/demo_6cach.sh`, Enter. Trong lúc chờ (khoảng 45 giây) chuyển sang dashboard **tab 0** để giới thiệu.
Script chạy xong thì quay lại Terminal đọc 3 dòng: mặc định, tắt index scan, tắt nested loop.

*Vừa bấm chạy:*
> "Em xin demo phần cài đặt và thực nghiệm cho bài báo *Is Your Learned Query Optimizer Behaving As You Expect?*
> Trong lúc script chạy, em giới thiệu môi trường."

*Tab 0:*
> "Nhóm dựng 2 container Docker: PostgreSQL 12.5 đúng phiên bản bài báo, có extension Bao, và một server chứa mô hình
> của Bao. Các lần chạy lớn của Bao và HybridQO chạy trên Kaggle. Dữ liệu giống bài báo: CSDL IMDB, 113 câu JOB
> thuộc 33 họ, 9 cách chia train/test. Máy nhóm ít bộ nhớ hơn bài báo nên nhóm so xu hướng, không so số giây.
> Số trên dashboard đo trên máy Mac của nhóm; phần chạy trực tiếp hôm nay chạy trên máy này nên số giây sẽ khác."

*Quay lại Terminal, chỉ vào 3 dòng kết quả:*
> "Cùng một câu 7c, em ép PostgreSQL chạy theo 6 cách: giữ nguyên, hoặc tắt 1 trong 5 toán tử. Mặc định khoảng 1,5 giây.
> Tắt index scan còn khoảng 0,8 giây, nhanh gấp gần 2 lần. Nhưng tắt nested loop lên khoảng 11 giây, chậm gấp 8 lần.
> Cùng một câu SQL mà chênh nhau khoảng 14 lần. Learned query optimizer học cách chọn như vậy.
> Vậy nó có thắng PostgreSQL không?"

Số giây mỗi lần chạy hơi khác nhau. Đọc số đang hiện trên màn hình.

### Màn hình 2: Tab 1. Bài báo vs Nhóm (0,75')
**Thao tác:** chỉ vào bảng/biểu đồ tổng.
> "Nhóm chạy lại Bao và HybridQO trên 9 split, tổng 233 lần kiểm tra. Neo, Balsa, LEON cần GPU nên dùng log của tác giả.
> Kết quả: Bao chỉ đạt 0,92 lần tốc độ PostgreSQL, bài báo là 0,83. HybridQO 0,97, bài báo 1,00. Dưới 1 nghĩa là
> chậm hơn PostgreSQL. Vậy kết luận của bài báo lặp lại được trên máy nhóm: LQO chưa thắng PostgreSQL."

### Màn hình 3: Tab 2. Nhóm: Thí nghiệm 1 (1,25')
**Thao tác:** chỉ vào 2 phát hiện ở đầu tab, rồi cuộn tới biểu đồ ablation (phát hiện 3).

*Phát hiện 1 và 2:*
> "Nhóm tìm ra hai lý do Bao thua. Thứ nhất, mỗi câu Bao tốn thêm khoảng 0,15 giây để lập 5 plan và hỏi mô hình.
> Với câu ngắn, phần này còn lâu hơn chạy câu. Bao thắng 8, hòa 46, thua 179 lần.
> Thứ hai, khi Bao đổi plan thì đổi sai nhiều hơn đổi đúng."

*Biểu đồ ablation:*
> "Nhóm cũng lặp lại ablation như tác giả. Tắt GEQO hay bitmap scan thì tổng gần như không đổi, nhưng 10–12 câu
> thay đổi mạnh. Mô hình Bao train trên IMDB 50% khi chạy trên dữ liệu đầy đủ thì chọn sai ở câu 3c và 11b.
> Tức là dữ liệu thay đổi một chút là mô hình chọn sai."

### Màn hình 4: Tab 3. Nhóm: Thí nghiệm 2 (1,5')
**Thao tác:** nói phần đầu tab, rồi cuộn xuống mục **Xem một câu** (đã chọn sẵn 26a). Số ở đây đo trên máy Mac.

*Phần đầu tab:*
> "Từ TN1, nhóm thử một hướng nhẹ hơn: chỉ đọc plan EXPLAIN của PostgreSQL, mất vài mili giây, rút 34 đặc trưng,
> rồi dùng mô hình phân loại chọn 1 trong 6 phương án: giữ nguyên, hoặc tắt 1 trong 5 toán tử. Nhóm thử Decision Tree,
> Random Forest và LightGBM. Nếu lần nào cũng chọn đúng, gọi là Oracle, thì nhanh hơn PostgreSQL 1,53 lần, nên dư địa
> là có thật. Nhưng mô hình chỉ đạt 0,80 đến 0,82 lần."

*Xem một câu → 26a:*
> "Vì sao? Ví dụ câu 26a, đo trên máy Mac của nhóm: tốt nhất là tắt index scan, khoảng 1 giây. Nhưng mô hình lại chọn tắt hash join,
> đúng phương án tệ nhất, 32 giây, trong khi PostgreSQL chỉ 5,7 giây. Một lần sai như vậy xoá hết phần lợi ở các câu khác.
> Nên giả thuyết H1, mô hình nhanh hơn PostgreSQL, bị bác bỏ. H2, mô hình kém nhất với câu chưa từng học, được chấp nhận:
> độ chính xác ở Base query 0,44, các split khác 0,54 đến 0,64."

### Màn hình 5: Tab 4. Khai phá dữ liệu (2,5', phần quan trọng nhất)
Đây là phần riêng của nhóm, không có trong bài báo. Nói chậm, nhấn mạnh.

*Ô "Vấn đề" và 3 bước:*
> "Đây là phần riêng của nhóm, không có trong bài báo. Mô hình đoán đúng khoảng một nửa mà tổng vẫn chậm hơn.
> Nhóm khai phá chính dữ liệu đã đo để tìm nguyên nhân, rồi sửa và đo lại."

*Phát hiện 1 (biểu đồ 2 thanh):*
> "Nhóm dùng luật kết hợp, dạng 'NẾU câu có đặc điểm A THÌ tắt X có lợi'. Máy thử 695 luật, giữ lại 37 luật đáng tin
> sau kiểm định thống kê. Luật nổi bật nhất: câu có từ 2 hash join trở lên thì tắt hash join. Luật này đúng 13 trên
> 28 câu, gấp 2,8 lần đoán bừa, nghe rất tốt.
> Nhưng nhìn biểu đồ: áp cho cả 28 câu thì 13 câu nhanh hơn chỉ được tổng khoảng 1 giây, còn 15 câu chậm hơn mất
> 77 giây. Bài học: đúng nhiều lần chưa đủ, phải tránh được lần sai đắt. Không chắc thì nên giữ nguyên PostgreSQL."

*Phát hiện 2 (biểu đồ cột xám và xanh):*
> "Nhóm sửa đúng theo bài học đó: mô hình chỉ đổi cách chạy khi độ tin từ 60% trở lên, còn lại giữ nguyên PostgreSQL.
> Random Forest từ 0,80 lên 1,06 lần, tức là đã nhanh hơn PostgreSQL. Kết quả ổn định khi ngưỡng từ 50% đến 70%.
> Lúc này mô hình chỉ đổi 6 trên 233 lần, đều là tắt nested loop ở họ 17, và lần nào cũng nhanh hơn."

*Kết luận tab:*
> "Khai phá dữ liệu chỉ ra đúng nguyên nhân: mô hình đổi cách chạy cả khi không chắc. Chỉ một sửa đổi đơn giản đã giúp
> mô hình thắng PostgreSQL."

Nếu cô hỏi sâu thì bật *Hiện chi tiết kỹ thuật* để xem bảng luật, các ngưỡng và 28 câu cụ thể.

### Màn hình 6: Tab 5. Demo mô hình (1,5')
**Thao tác:** chọn **23a**, mô hình **Random Forest**, giữ ô *"Không cho mô hình học các câu cùng họ"*.

*Bước 1 – chọn câu:*
> "Cuối cùng là prototype chạy thật. Ô này bỏ cả họ 23 khỏi dữ liệu huấn luyện, để mô hình gặp câu này như câu mới."

*Bấm **Hỏi mô hình** – bước 2 và 3:*
> "Mô hình chưa chạy câu, chỉ hỏi PostgreSQL định chạy thế nào bằng EXPLAIN rồi trích 34 đặc trưng. Mô hình chọn tắt
> hash join, tin 37%. Toàn bộ ra quyết định khoảng 25 mili giây, Bao cần khoảng 150."

*Bấm **Chạy trên PostgreSQL** – bước 4 (khoảng 10 giây):*
> "Chạy thật cả 6 phương án để kiểm tra: phương án nhanh nhất đúng là tắt hash join."

*Đổi sang **16c**, bấm **Hỏi mô hình** rồi **Chạy trên PostgreSQL** (khoảng 30 giây):*
> "Còn câu 16c, mô hình chọn tắt nested loop, chỉ tin 48%. Chạy thật thì PostgreSQL mặc định khoảng 1,3 giây,
> còn theo mô hình lên khoảng 2,9 giây, chậm hơn gấp đôi. Đây đúng là kiểu đổi khi không chắc mà tab 4 đã chỉ ra.
> Áp luật dưới 60% thì giữ nguyên là tránh được lần sai này."

Trong lúc chờ 16c chạy, nói câu chốt bên dưới. Số mỗi lần chạy hơi khác nhau, đọc số đang hiện trên màn hình.

### Màn hình 7: Hạn chế và kết luận (1')
**Thao tác:** giữ nguyên màn hình (hoặc quay về tab 4 nếu muốn chỉ lại con số 1,06×).
> "Về hạn chế: máy nhóm ít bộ nhớ hơn bài báo nên chỉ so xu hướng. HybridQO chỉ train được 11 epoch so với 50 của
> tác giả vì giới hạn 12 giờ của Kaggle. Oracle chỉ là tốt nhất trong 6 cách thử. Và ngưỡng 60% mới giúp ở 6 trên
> 233 lần, đều thuộc họ 17.
> Tóm lại, nhóm tái lập được kết luận của bài báo: LQO chưa thắng PostgreSQL ổn định. Khai phá dữ liệu cho thấy nguyên
> nhân là đổi plan cả khi không chắc. Với luật đơn giản 'không chắc thì giữ nguyên', mô hình của nhóm đã nhanh hơn
> PostgreSQL 1,06 lần. Em cảm ơn cô."

### Nếu bị lố giờ
Cắt theo thứ tự: (1) bỏ bấm *Chạy trên PostgreSQL* ở tab 5, chỉ hỏi mô hình; (2) bỏ tab 1, nói số bằng lời ở đầu tab 2;
(3) bỏ biểu đồ ablation. **Không cắt** `demo_6cach.sh` và tab 4.

### Nếu cô hỏi thêm
- *Về 16b (một lần mô hình thắng):* mô hình chọn tắt nested loop, tin 54%. Trên máy demo: 15 s → 4,3 s, nhanh 3,5 lần.
  Nhưng 54% dưới 60%, áp ngưỡng thì mất lần thắng này, đó là cái giá của việc chơi an toàn. Không chạy (mất khoảng 4–5 phút).
- *Muốn xem lại 26a như trên Mac:* trên máy demo, plan của 26a khác Mac (thống kê ANALYZE lấy mẫu ngẫu nhiên), mặc định
  chỉ khoảng 1,3 s và mô hình chọn giữ nguyên. Đây cũng là ví dụ cho việc dữ liệu/thống kê đổi một chút là plan đổi.
- *Muốn xem Bao chọn sai chạy thật:* chạy `bash scripts/demo/demo_83.sh` (khoảng 1,5 phút).

---

## 4. Nếu có sự cố

| Sự cố | Cách xử lý |
|---|---|
| Script báo lỗi kết nối / container không chạy | `docker compose -f infra/docker-compose.yml up -d`, chờ 10 giây, chạy lại |
| `demo_83.sh` báo "Bao server chưa nạp được model" | Chạy lại lần nữa (lần đầu nạp PyTorch chậm); xem log: `docker exec bao_server tail -5 /app/logs/bao_server.log` |
| Dashboard không mở được | `bash scripts/demo/demo_start.sh --no-warm` |
| Tab 5 báo không kết nối được PostgreSQL | `docker start pg_bao` |
| Máy chạy chậm, số lệch nhiều | Mở ảnh chụp màn hình đã chuẩn bị |
| Lố giờ | Xem mục "Nếu bị lố giờ" ở cuối mục 3 |
| Dư giờ | `bash scripts/demo/demo_ablation.sh` (tắt GEQO và bitmap scan, khoảng 1–2 phút) |

---

## 5. Khi cô yêu cầu show code (5–7 phút)

**Nguyên tắc:** đi theo **dòng dữ liệu**: hạ tầng → chạy và đo → log → phân tích → dashboard. Mỗi tầng chỉ mở 1–2 file,
bôi đen vài dòng cốt lõi, nói 1–2 câu. Cô hỏi sâu file nào thì mới cuộn xuống.

> Mở đầu: "Em đi theo dòng dữ liệu: hạ tầng, chạy và đo, log, phân tích, dashboard."

### 5.0. Kiến trúc tổng thể
```
 ┌──────────── HẠ TẦNG (infra/) ────────────┐      ┌──── KAGGLE (kaggle/) ────┐
 │  bao_server (Bao, PyTorch)  10.5.0.6     │      │ Bao · HybridQO · ablation │
 │       │  5 plan → dự đoán → chọn arm      │      │ (notebook sinh tự động)   │
 │       ▼                                  │      └────────────┬─────────────┘
 │  pg_bao (PostgreSQL 12.5 + pg_bao        │                   │
 │          + pg_hint_plan, IMDB) 10.5.0.5  │                   │
 └──────────────┬───────────────────────────┘                   │
                ▼  scripts/ chạy và đo                          ▼
        ┌────────── LOG THÔ: logs/mac/, logs/kaggle/ (không sửa tay) ──────────┐
        └───────────────────────────────┬─────────────────────────────────────┘
                                        ▼
        PHÂN TÍCH: scripts/exp1, exp2, ablation  →  analysis/output/*.csv
                                        ▼
                  TRÌNH BÀY: app/ (dashboard Streamlit), scripts/demo/
```
> "Mọi số liệu trên dashboard đều tính lại được từ log thô."

### 5.1. Hạ tầng (1')

| File | Chỉ vào | Nói |
|---|---|---|
| [infra/docker-compose.yml](infra/docker-compose.yml) | 2 service, IP 10.5.0.5 và 10.5.0.6; mount `../scripts`, `../logs` | "Hai container cùng mạng, IP giống repo tác giả. scripts và logs dùng chung với máy." |
| [infra/Dockerfile.pg:10-21](infra/Dockerfile.pg#L10-L21) | Biên dịch PostgreSQL 12.5, pg_hint_plan, pg_bao | "Tự biên dịch đúng bản 12.5 như bài báo, cho chip Apple." |
| [infra/postgresql.lqo.conf:11-24](infra/postgresql.lqo.conf#L11-L24) | shared_buffers, work_mem, geqo, có chú thích so với bài báo | "Mỗi tham số đều ghi rõ khác bài báo ở đâu và vì sao." |

### 5.2. Chạy thí nghiệm 1 (1')

| File | Chỉ vào | Nói |
|---|---|---|
| [scripts/exp1/run_fair_comparison.sh](scripts/exp1/run_fair_comparison.sh) | Khởi động lại → làm nóng → baseline → Bao → so sánh | "So sánh công bằng: cùng phiên, cùng cache nóng." |
| [scripts/exp1/run_bao_split.sh](scripts/exp1/run_bao_split.sh) | Xoá model cũ → `run_queries.py` → test | "Mỗi split train lại từ đầu, dùng nguyên script tác giả." |
| [kaggle/build_bao_notebook.py:178-191](kaggle/build_bao_notebook.py#L178-L191) | `host=pg_bao` thành `localhost` | "Trên Kaggle chỉ sửa địa chỉ kết nối, không đổi logic." |

### 5.3. Phân tích thí nghiệm 1 (1')

| File | Chỉ vào | Nói |
|---|---|---|
| [scripts/common/lqo_common.py:25-50](scripts/common/lqo_common.py#L25-L50) | `total_ms = inference + planning + execution`; `run=2` | "Mọi loại log đưa về một bảng chung; thời gian end-to-end, lấy lần thứ 3." |
| [scripts/exp1/c1_win_loss.py:32-51](scripts/exp1/c1_win_loss.py#L32-L51) | Ngưỡng ±10%, `wilcoxon`, `binomtest` | "Thắng/hòa/thua với ngưỡng 10%, kiểm định Wilcoxon và sign test." |

### 5.4. Thí nghiệm 2 (2', phần quan trọng nhất)

| File | Chỉ vào | Nói |
|---|---|---|
| [scripts/common/extract_features.py:30-52](scripts/common/extract_features.py#L30-L52), [73-110](scripts/common/extract_features.py#L73-L110) | `sql_features`, `plan_features` | "11 đặc trưng đếm trên SQL, 23 từ plan EXPLAIN, có trước khi chạy câu." |
| [scripts/exp2/exp2_analyze.py:103-109](scripts/exp2/exp2_analyze.py#L103-L109) | Hàm `labels`, `min_gain=0.05` | "Nhãn là phương án nhanh nhất, nhưng phải hơn PostgreSQL trên 5%, để không học theo nhiễu đo." |
| [scripts/exp2/exp2_analyze.py:48](scripts/exp2/exp2_analyze.py#L48) | `DROP = {q-error}` | "Bỏ q-error vì cần chạy câu mới có, tránh nhìn trước đáp án." |
| [scripts/exp2/exp2_analyze.py:195-235](scripts/exp2/exp2_analyze.py#L195-L235) | Vòng 9 split; `e2e = explain_ms + inf_ms + chosen` | "Train và test theo từng split như Bao. Thời gian mô hình đã cộng EXPLAIN và suy luận, nên so công bằng." |

### 5.5. Khai phá dữ liệu và ngưỡng tin (1')

| File | Chỉ vào | Nói |
|---|---|---|
| [scripts/exp2/exp2_mining.py:92-121](scripts/exp2/exp2_mining.py#L92-L121) | `confidence`, `lift`, `fisher_exact`, lọc `lift > 1.5`, `p_hiệu_chỉnh < 0.05` | "Luật kết hợp như Apriori, thêm kiểm định Fisher có hiệu chỉnh để loại luật ngẫu nhiên." |
| [scripts/exp2/exp2_abstain.py:45-52](scripts/exp2/exp2_abstain.py#L45-L52) | `predict_proba`; `h if c >= th else "default"` | "Toàn bộ luật 'không chắc thì giữ nguyên' chỉ vài dòng, mà đưa RF từ 0,80 lên 1,06 lần." |

### 5.6. Dashboard và prototype (1')

| File | Chỉ vào | Nói |
|---|---|---|
| [app/streamlit_app.py:22-24](app/streamlit_app.py#L22-L24) | 6 tab | "Dashboard chỉ đọc kết quả đã tính sẵn." |
| [app/prototype.py:25-31](app/prototype.py#L25-L31), [110-116](app/prototype.py#L110-L116) | `HINT_SQL` (6 phương án = lệnh SET); `EXPLAIN (FORMAT JSON)` | "Prototype đi đúng quy trình: EXPLAIN → đặc trưng → mô hình chọn → SET → chạy thật." |
