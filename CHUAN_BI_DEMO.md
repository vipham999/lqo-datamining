# Chuẩn bị demo

Thời lượng khoảng **12 phút demo** và **5–7 phút đi qua code** (khi cô yêu cầu).
Giải thích chi tiết từng khái niệm nằm trong [HOI_DAP_DEMO.md](HOI_DAP_DEMO.md).

**Mạch trình bày:** chọn plan quan trọng đến mức nào (26a) → TN1: LQO có thắng PostgreSQL không → TN2: mô hình của nhóm
→ Khai phá dữ liệu: vì sao thua, sửa thế nào → Demo chạy thật → Hạn chế, kết luận.

**Câu chốt cần nhớ:** *"Đúng nhiều lần chưa đủ, phải tránh được lần sai đắt."*

---

## 1. Chuẩn bị môi trường

### 1.1. Hôm trước
- [ ] Tập nói 1–2 lần theo mục 3, bấm giờ.
- [ ] Thuộc các con số ở mục 2.
- [ ] Đọc phần **"câu gọn để nói với cô"** trong [HOI_DAP_DEMO.md](HOI_DAP_DEMO.md).
- [ ] Chụp màn hình kết quả `demo_26a.sh`, `demo_83.sh` và tab 5 (câu 23a) để dự phòng.

### 1.2. Trước giờ demo 30 phút
```bash
cd ~/Desktop/lqo-datamining

# 1. Mở Docker Desktop, kiểm tra 2 container
docker ps                                   # phải thấy pg_bao và bao_server
# nếu thiếu: docker compose -f infra/docker-compose.yml up -d

# 2. Làm nóng cache (5–10 phút) cho thời gian chạy ổn định
docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh

# 3. Mở dashboard (nếu chưa chạy) → http://localhost:8501
bash scripts/demo/demo_start.sh --no-warm

# 4. Chạy thử mỗi script 1 lần (vừa kiểm tra, vừa làm nóng các câu sẽ demo)
bash scripts/demo/demo_26a.sh               # ~5,7 s / ~1 s / ~32 s, khoảng 1,5 phút
bash scripts/demo/demo_83.sh                # Bao-50 chọn tắt nested loop ở 3c, 11b, khoảng 1,5 phút
```
`demo_83.sh` nạp PyTorch lần đầu có thể mất hơn 30 giây. Script đã được sửa để chờ tối đa 2 phút. Chạy thử trước một lần thì lúc demo nạp model chỉ mất khoảng 4 giây.

### 1.3. Chuẩn bị màn hình
- [ ] **Dashboard** (zoom 125%):
  - Tab 5: chọn **23a**, bấm *Hỏi mô hình* rồi *Chạy trên PostgreSQL* một lần.
  - Tab 3: bật *Hiện số liệu chi tiết*, vào *Xem một câu*, chọn **26a**.
  - Tab 2: bật *Hiện số liệu chi tiết* sẵn.
  - Quay lại tab 0.
- [ ] **Terminal**: đã `cd` vào thư mục dự án, chữ to (`Cmd +`).
- [ ] **VS Code**: mở sẵn các file ở mục 5, đúng thứ tự, mỗi file một tab.
- [ ] Bật *Không làm phiền*, tắt Zalo/Messenger, cắm sạc. Chạy `caffeinate -d` trong một terminal riêng để máy không ngủ.

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
| Câu 26a | PostgreSQL 5,7 s; tắt index scan 0,95 s; **mô hình chọn tắt hash join 32 s** |
| Luật kết hợp | thử 695, giữ 37; luật "≥2 hash join" đúng 13/28, lift 2,8; được 1 s, mất 77 s |
| RF với ngưỡng tin 60% | **1,06×**, đổi 6/233 lần, đều ở họ 17 |
| Độ chính xác Base query (H2) | 0,44 (các split khác 0,54–0,64) |
| Dữ liệu | 113 câu, 33 họ, 9 split, 233 lần kiểm tra |

---

## 3. Kịch bản demo (khoảng 12 phút)

| # | Phần | Màn hình | Thời gian |
|---|---|---|---|
| 1 | Mở đầu và môi trường | `docker ps` → tab 0 | 1' |
| 2 | Chọn plan quan trọng đến mức nào | `demo_26a.sh` | 1' |
| 3 | TN1: LQO có thắng PostgreSQL không | Tab 1 → tab 2 → `demo_83.sh` | 3' |
| 4 | TN2: mô hình của nhóm | Tab 3 (câu 26a) | 2' |
| 5 | Khai phá dữ liệu | Tab 4 | 2' |
| 6 | Demo chạy thật | Tab 5 | 1,5' |
| 7 | Hạn chế và kết luận | Tab 2 → Thiết kế & hạn chế | 1' |

### Kịch bản 1: Mở đầu và môi trường (1')
**Màn hình:** Terminal `docker ps` → tab **0. Dữ liệu IMDB & JOB**
```bash
docker ps
docker exec pg_bao psql -U postgres -d imdbload -c "select version();"
```
> "Em xin demo phần cài đặt và thực nghiệm cho bài báo *Is Your Learned Query Optimizer Behaving As You Expect?*
> Nhóm dựng 2 container Docker: pg_bao là PostgreSQL 12.5 đúng phiên bản bài báo, gắn extension Bao và pg_hint_plan;
> bao_server chứa mô hình của Bao. HybridQO và các lần chạy chính của Bao chạy trên Kaggle.
> Dữ liệu giống bài báo: CSDL IMDB, 113 câu JOB thuộc 33 họ, 9 cách chia train/test. Base query khó nhất vì câu test
> thuộc họ mô hình chưa từng học. Máy nhóm ít bộ nhớ hơn bài báo nên nhóm so xu hướng, không so số giây."

### Kịch bản 2: Chọn plan quan trọng đến mức nào (1')
**Màn hình:** Terminal `bash scripts/demo/demo_26a.sh`. Bấm chạy rồi nói trong lúc chờ (khoảng 1,5 phút).
> "Cùng một câu 26a, em ép PostgreSQL chạy theo 3 cách. Tắt index scan nhanh gấp khoảng 5 lần, tắt hash join chậm gấp
> khoảng 6 lần. Hai cách chênh nhau hơn 30 lần. LQO học cách chọn như vậy. Vậy nó có thắng PostgreSQL không?"

### Kịch bản 3: Thí nghiệm 1 (3')
**Tab 1. Bài báo vs Nhóm**
> "Nhóm chạy lại Bao và HybridQO trên 9 split, 233 lần kiểm tra. Neo, Balsa, LEON cần GPU nên dùng log tác giả.
> Bao đạt 0,92 lần tốc độ PostgreSQL (bài báo 0,83), HybridQO 0,97 (bài báo 1,00). Dưới 1 là chậm hơn.
> Kết luận của bài báo lặp lại được trên máy nhóm."

**Tab 2. Nhóm: Thí nghiệm 1** (2 phát hiện ở đầu tab)
> "Bao thua vì hai lý do. Thứ nhất, mỗi câu Bao tốn thêm khoảng 0,15 giây để lập 5 plan và hỏi mô hình; với câu ngắn,
> phần này còn lâu hơn cả chạy câu. Thứ hai, khi Bao đổi plan thì đổi sai nhiều hơn đúng."

**Biểu đồ ablation ở tab 2, rồi Terminal `bash scripts/demo/demo_83.sh`** (khoảng 1,5 phút)
> "Nhóm lặp lại ablation như tác giả. Tắt GEQO hay bitmap scan thì tổng gần như không đổi, nhưng 10–12 câu thay đổi mạnh.
> Với 8.3, em nạp hai model Bao: một train trên IMDB đầy đủ, một train trên IMDB 50%, rồi chạy cả hai trên dữ liệu đầy đủ.
> Bao-50 chọn tắt nested loop ở 3c và 11b nên chậm hơn [đọc số trên màn hình]; Bao-Full giữ plan mặc định.
> Dữ liệu thay đổi thì mô hình chọn sai."

Số mili giây mỗi lần chạy sẽ hơi khác nhau. Đọc số đang hiện trên màn hình.

### Kịch bản 4: Thí nghiệm 2 (2')
**Tab 3. Nhóm: Thí nghiệm 2**
> "Từ TN1, nhóm thử một mô hình phân loại nhẹ hơn: chỉ đọc plan EXPLAIN (vài mili giây), rút 34 đặc trưng, rồi chọn
> 1 trong 6 phương án: giữ nguyên hoặc tắt 1 trong 5 toán tử. Nhóm thử Decision Tree, Random Forest và LightGBM.
> Nếu luôn chọn đúng (Oracle) thì nhanh hơn 1,53 lần, nên dư địa có thật. Nhưng mô hình chỉ đạt 0,80–0,82 lần.
> Mô hình ít khi làm chậm hơn PostgreSQL so với Bao, nhưng vài lần chọn sai rất đắt."

**Mục Xem một câu → 26a**
> "Câu 26a: tốt nhất là tắt index scan, khoảng 1 giây, nhưng mô hình chọn tắt hash join, 32 giây, trong khi PostgreSQL
> chỉ 5,7 giây. Một lần sai như vậy xoá hết phần lợi ở các câu khác.
> H1 (mô hình nhanh hơn PostgreSQL) bị bác bỏ. H2 (kém nhất với câu chưa từng học) được chấp nhận: độ chính xác ở
> Base query 0,44, các split khác 0,54–0,64."

### Kịch bản 5: Khai phá dữ liệu (2')
**Tab 4. Khai phá dữ liệu.** Đây là phần riêng của nhóm, không có trong bài báo, nên cần nhấn mạnh.

*Ô "Vấn đề" và 3 bước:*
> "Mô hình đoán đúng khoảng một nửa nhưng tổng vẫn chậm hơn. Nhóm khai phá chính dữ liệu đã đo để tìm nguyên nhân,
> rồi sửa và đo lại."

*Phát hiện 1 (biểu đồ 2 thanh):*
> "Dùng luật kết hợp dạng 'NẾU câu có đặc điểm A THÌ tắt X có lợi'. Máy thử 695 luật, giữ lại 37 luật đáng tin.
> Luật nổi bật: có từ 2 hash join trở lên thì tắt hash join. Luật đúng 13/28 câu, gấp 2,8 lần đoán bừa.
> Nhưng áp cho cả 28 câu thì 13 câu nhanh hơn chỉ được khoảng 1 giây, còn 15 câu chậm hơn mất 77 giây.
> Bài học: chỉ đổi khi thật chắc chắn, còn không thì giữ nguyên PostgreSQL."

*Phát hiện 2 (biểu đồ cột xám và xanh):*
> "Nhóm sửa đúng theo bài học: mô hình chỉ đổi cách chạy khi độ tin từ 60% trở lên. Random Forest từ 0,80 lên 1,06 lần,
> nhanh hơn PostgreSQL. Kết quả giữ ổn định khi ngưỡng từ 50% đến 70%. Lúc này mô hình chỉ đổi 6/233 lần, đều là tắt
> nested loop ở họ 17, và lần nào cũng nhanh hơn."

*Kết luận:*
> "Khai phá dữ liệu chỉ ra đúng nguyên nhân: mô hình đổi cách chạy cả khi không chắc. Một sửa đổi đơn giản đã giúp mô hình
> thắng PostgreSQL. Phần lợi còn nhỏ vì mô hình hiếm khi đủ tự tin."

Nếu cô hỏi sâu thì bật *Hiện chi tiết kỹ thuật* để xem bảng luật, các ngưỡng và 28 câu cụ thể.

### Kịch bản 6: Demo chạy thật (1,5')
**Tab 5. Demo mô hình**

| Câu | Mô hình chọn | Độ tin | Kết quả đã đo | Làm gì |
|---|---|---|---|---|
| **23a** | Tắt hash join | 37% | 0,17 → 0,12 s, đúng | **Chạy đủ 4 bước** (khoảng 10 s) |
| **26a** | Tắt hash join | 35% | 5,7 → 32 s, sai | **Chỉ bấm Hỏi mô hình**, không chạy (mất khoảng 4 phút) |
| 16b | Tắt nested loop | 54% | 24 → 9,4 s, thắng 2,5× | Chỉ khi cô hỏi về một lần thắng; không chạy (mất khoảng 6 phút) |

1. Chọn **23a**, mô hình **Random Forest**, giữ ô *"Không cho mô hình học các câu cùng họ"*.
   > "Ô này bỏ cả họ 23 khỏi dữ liệu huấn luyện, để mô hình gặp câu này như câu hoàn toàn mới."
2. Bấm **Hỏi mô hình**. Bước 2:
   > "Mô hình chưa chạy câu. Nó chỉ hỏi PostgreSQL định chạy thế nào (EXPLAIN), rồi nhóm trích 34 đặc trưng."
3. Bước 3:
   > "Mô hình chọn tắt hash join, tin 37%. Toàn bộ ra quyết định chỉ khoảng 25 ms, Bao cần khoảng 150 ms."
4. Bấm **Chạy trên PostgreSQL**. Bước 4:
   > "Chạy thật cả 6 phương án để kiểm tra: phương án nhanh nhất đúng là tắt hash join."
5. Đổi sang **26a**, chỉ bấm *Hỏi mô hình*:
   > "Câu 26a, mô hình cũng chọn tắt hash join nhưng chỉ tin 35%, ngang với giữ nguyên. Kết quả đã đo là 32 giây so với 5,7.
   > Áp luật ở tab 4 (dưới 60% thì giữ nguyên) thì tránh được lần sai này."

> Chốt: "Hướng của nhóm chạy được trong thực tế và ra quyết định rất nhanh. Điểm yếu là đổi cách chạy khi không chắc,
> nên nhóm thêm luật 'không chắc thì giữ nguyên'."

Nếu cô hỏi về 16b thì nói thật: mô hình chỉ tin 54%, dưới 60%. Áp ngưỡng thì mất lần thắng này, và đó là cái giá của
việc chơi an toàn.

### Kịch bản 7: Hạn chế và kết luận (1')
**Tab 2 → bật chi tiết → Thiết kế & hạn chế**
> "Hạn chế: máy ít bộ nhớ hơn bài báo nên chỉ so xu hướng. HybridQO chỉ train 11 epoch so với 50 của tác giả, do giới
> hạn 12 giờ của Kaggle, nên gần như giữ plan PostgreSQL. Oracle chỉ là tốt nhất trong 6 cách thử. Ngưỡng tin 60% mới
> giúp ở 6/233 lần, đều thuộc họ 17.
> Tóm lại, nhóm tái lập được kết luận của bài báo: LQO chưa thắng PostgreSQL ổn định. Khai phá dữ liệu cho thấy
> nguyên nhân là đổi plan cả khi không chắc, và với luật đơn giản 'không chắc thì giữ nguyên' thì mô hình đã nhanh hơn
> PostgreSQL 1,06 lần. Em cảm ơn cô."

---

## 4. Nếu có sự cố

| Sự cố | Cách xử lý |
|---|---|
| Script báo lỗi kết nối / container không chạy | `docker compose -f infra/docker-compose.yml up -d`, chờ 10 giây, chạy lại |
| `demo_83.sh` báo "Bao server chưa nạp được model" | Chạy lại lần nữa (lần đầu nạp PyTorch chậm); xem log: `docker exec bao_server tail -5 /app/logs/bao_server.log` |
| Dashboard không mở được | `bash scripts/demo/demo_start.sh --no-warm` |
| Tab 5 báo không kết nối được PostgreSQL | `docker start pg_bao` |
| Máy chạy chậm, số lệch nhiều | Mở ảnh chụp màn hình đã chuẩn bị |
| Hết giờ | Bỏ `demo_83.sh` và tab 5, chỉ nói số trên dashboard |
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
