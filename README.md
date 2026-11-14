# Learned Query Optimizer – kiểm chứng bài báo và hướng phát triển của Nhóm 1

Đồ án môn **Hệ cơ sở dữ liệu tiên tiến**. Nhóm tái lập bài báo
*"Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective"*
(Lehmann, Sulimov, Stockinger, PVLDB 2024) trên benchmark **JOB / IMDB**, rồi thử hướng riêng:
một mô hình phân loại nhỏ chọn cách chạy cho PostgreSQL, và khai phá dữ liệu để hiểu vì sao mô hình thua.

- Repo của tác giả: [edualc/lqo_ml_perspective](https://github.com/edualc/lqo_ml_perspective), clone vào `lqo_ml_perspective/`.
- Kiến trúc hệ thống: [ARCHITECTURE.md](ARCHITECTURE.md).
- Ghi chú IMDB/JOB: [GHI_CHU_IMDB_JOB.md](GHI_CHU_IMDB_JOB.md), [GHI_CHU_113_TRUY_VAN_JOB.md](GHI_CHU_113_TRUY_VAN_JOB.md).
- Chạy HybridQO trên Kaggle: [HUONG_DAN_KAGGLE_HYBRIDQO.md](HUONG_DAN_KAGGLE_HYBRIDQO.md).

---

## 1. Kết quả chính

Quy ước chung: cache nóng, mỗi câu chạy 3 lần lấy lần thứ 3; **thắng/thua** khi nhanh/chậm hơn PostgreSQL quá **10%**;
speedup = tổng thời gian PostgreSQL / tổng thời gian phương pháp (> 1 là nhanh hơn). 9 split của bài báo
(Leave-one-out, Random, Base query × 3), tổng 233 câu test.

### Thí nghiệm 1 – Bài báo nói đúng không?

| Phương pháp | Bài báo (log tác giả) | Nhóm |
|---|---|---|
| Bao | 9 / 34 / 190 thắng/hòa/thua, **0,83×** | Mac: 28 / 28 / 177, **1,08×** · Kaggle: 8 / 46 / 179, **0,92×** |
| HybridQO | 34 / 82 / 117, **1,00×** | Kaggle: 0 / 124 / 109, **0,97×** |

- **Kết luận giống bài báo:** LQO chưa nhanh hơn PostgreSQL một cách ổn định; thua ở phần lớn câu.
- Bao thua chủ yếu ở câu nhỏ (chi phí gọi mô hình ~0,15 s/câu) và chọn sai plan ở vài câu lớn.
- **Ablation** (tắt từng thành phần, chạy xen kẽ, 8 lượt trên Kaggle):
  - Tắt GEQO: phần lớn không đổi, vài câu nhiều bảng chậm đi rõ (24b, 28a).
  - Tắt bitmap + TID scan: tác động **hai chiều** (có câu chậm đi, có câu nhanh lên) → một tham số không tốt cho mọi câu.
  - Dữ liệu thay đổi (train trên IMDB 50%, test trên IMDB đầy đủ): Bao-50 chọn sai hint ở một số câu.

Số liệu: `analysis/output/exp1/` (tổng hợp ở `exp1_tomtat.txt`).

### Thí nghiệm 2 – Mô hình nhỏ có giúp PostgreSQL nhanh hơn?

Mỗi câu chọn 1 trong **6 phương án**: `default`, `no_nestloop`, `no_hashjoin`, `no_mergejoin`, `no_seqscan`,
`no_indexscan`. Đặc trưng: 34 đặc trưng lấy từ SQL + `EXPLAIN` (không dùng gì có sau khi chạy). Nhãn: phương án
nhanh nhất, giữ `default` nếu không nhanh hơn ít nhất 5%.

| Phương pháp | Speedup tổng (233 câu) |
|---|---|
| Oracle (biết trước phương án nhanh nhất) | **1,53×** – còn nhiều chỗ để cải thiện |
| Decision Tree / Random Forest / LightGBM | 0,82× / 0,80× / 0,80× |
| **Random Forest + bỏ phiếu trắng (ngưỡng 0,6)** | **1,06×** – chỉ đổi 6/233 lần |

- Thua dồn vào vài câu: riêng 26a chiếm ~77% thời gian bị mất.
- Khoảng 65 câu "thua" là câu rất nhỏ, chậm đi do chi phí gọi `EXPLAIN`.

Số liệu: `analysis/output/exp2/` (tổng hợp ở `exp2_tomtat.txt`).

### Khai phá dữ liệu – Vì sao mô hình thua, và sửa thế nào?

1. **Tìm luật kết hợp** trên 113 câu (695 luật thử, giữ 37 luật qua kiểm định Fisher + Benjamini–Hochberg).
   Ví dụ: *"plan có ≥ 2 hash join → tắt hash join giúp"* đúng 13/28 câu (lift 2,8), nhưng khi sai thì sai rất nặng.
2. **Rút ra nguyên nhân:** mô hình đổi cách chạy **cả khi không chắc**; lợi nhỏ khi đúng, mất lớn khi sai.
3. **Sửa và đo lại:** chỉ đổi khi xác suất dự đoán ≥ ngưỡng (`exp2_abstain.py`) → Random Forest từ 0,80× lên 1,06×,
   ổn định trong khoảng ngưỡng 0,5–0,7. Lưu ý: ngưỡng 0,6 được chọn sau khi thử nhiều ngưỡng.

---

## 2. Cấu trúc thư mục

```
lqo-datamining/
├── app/                      ← dashboard Streamlit
│   ├── streamlit_app.py      ← khung 6 tab
│   ├── group_results.py      ← tab Thí nghiệm 1, Thí nghiệm 2, Khai phá dữ liệu
│   ├── prototype.py          ← tab "5. Demo mô hình" (chạy thật trên PostgreSQL)
│   ├── core.py, prepare_data.py
├── infra/                    ← Dockerfile PostgreSQL 12.5 + pg_hint_plan + pg_bao (ARM64), Bao server, compose
├── scripts/                  ← chi tiết: scripts/README.md
│   ├── setup/                ← nạp IMDB, tạo IMDB 50%, làm nóng cache, khởi động Bao server
│   ├── exp1/                 ← Thí nghiệm 1: đo PostgreSQL vs Bao, thắng/hòa/thua, bảng tổng hợp
│   ├── ablation/             ← tắt GEQO, bitmap/TID scan, số lần chạy, thứ tự join
│   ├── exp2/                 ← Thí nghiệm 2: đo 6 phương án, huấn luyện mô hình, khai phá dữ liệu, bỏ phiếu trắng
│   ├── demo/                 ← demo trực tiếp trên terminal
│   └── common/               ← thư viện dùng chung (đọc log, trích đặc trưng, chạy câu × hint set)
├── kaggle/                   ← sinh notebook Kaggle (Bao, HybridQO, ablation) và các lần chạy
├── kaggle_runs/, bao_kaggle_log/, hybridqo_log/   ← log tải về từ Kaggle
├── logs/                     ← log thô trên Mac (không sửa tay)
├── analysis/output/          ← bảng kết quả (exp1/, exp2/, c1_*.csv, ablation_*.csv)
└── lqo_ml_perspective/       ← repo tác giả (submodule)
```

---

## 3. Cài đặt

**Máy của nhóm:** MacBook Pro M1 Pro, 8 core, 16 GB RAM, không GPU. Cần trống **≥ 40 GB** ổ đĩa;
Docker (OrbStack/Docker Desktop) cấp **10–12 GB RAM, 8 CPU**.

### 3.1 PostgreSQL và Bao

```bash
cd infra
docker compose build            # pg_bao (PostgreSQL 12.5 ARM64) + bao_server (PyTorch 1.13 ARM64)
docker compose up -d
docker exec pg_bao psql -c "SHOW shared_preload_libraries;"   # phải có pg_bao
```

Cấu hình `infra/postgresql.lqo.conf` thu nhỏ so với bài báo: `shared_buffers` 4 GB (bài báo 32 GB),
`work_mem` 256 MB (4 GB), `geqo` bật, `autovacuum` tắt. Vì vậy nhóm so **xu hướng**, không so số tuyệt đối.

### 3.2 Dữ liệu IMDB

```bash
cd lqo_ml_perspective/data && mkdir -p imdb && cd imdb
wget -c https://event.cwi.nl/da/job/imdb.tgz && tar -xvzf imdb.tgz
cd .. && python prepend_imdb_headers.py
docker exec -it pg_bao bash /app/scripts/setup/load_imdb.sh        # ~15–30 phút: 21 bảng, ~12 GB
docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh          # làm nóng cache trước khi đo
```

### 3.3 Môi trường Python

Desktop đồng bộ iCloud có thể đẩy file của venv lên mây làm Python treo, nên đặt venv ngoài Desktop:

```bash
/opt/miniconda3/bin/python3 -m venv ~/.venvs/lqo_app
~/.venvs/lqo_app/bin/pip install pandas numpy scipy scikit-learn lightgbm altair psycopg2-binary streamlit
```

---

## 4. Chạy lại các thí nghiệm

```bash
# Thí nghiệm 1 – PostgreSQL và Bao cùng phiên, 9 split (Mac, mất nhiều giờ)
caffeinate -dis bash scripts/exp1/run_fair_comparison.sh
python3 scripts/exp1/exp1_tables.py                              # → analysis/output/exp1/

# HybridQO, Bao và ablation trên Kaggle: sinh notebook bằng kaggle/build_*_notebook.py,
# tải log về kaggle_runs/ rồi chạy lại exp1_tables.py

# Thí nghiệm 2 – 113 câu × 6 phương án × 3 lần, kèm EXPLAIN
bash scripts/exp2/exp2_collect.sh
~/.venvs/lqo_app/bin/python scripts/exp2/exp2_analyze.py         # → analysis/output/exp2/

# Khai phá dữ liệu (chỉ đọc lại log, không chạy thêm truy vấn)
~/.venvs/lqo_app/bin/python scripts/exp2/exp2_mining.py
~/.venvs/lqo_app/bin/python scripts/exp2/exp2_abstain.py
```

Các script chạy dài đều chạy tiếp được từ chỗ dừng. Log thô không sửa tay; mọi con số trên dashboard tính lại được từ log.

---

## 5. Dashboard

```bash
cd app && ~/.venvs/lqo_app/bin/streamlit run streamlit_app.py
# hoặc: bash scripts/demo/demo_start.sh   (kiểm tra container, làm nóng cache, mở dashboard tại http://localhost:8501)
```

Chạy lệnh `streamlit run streamlit_app.py` **từ trong thư mục `app/`**. Sau khi sửa code nên tắt và mở lại server.

| Tab | Nội dung |
|---|---|
| 0. Dữ liệu IMDB & JOB | CSDL IMDB (21 bảng), benchmark JOB 113 câu, vài câu đáng nhớ |
| 1. Bài báo vs Nhóm | So kết quả bài báo với nhóm theo từng split |
| 2. Nhóm: Thí nghiệm 1 | 3 phát hiện (Thấy gì / Vì sao / Rút ra), ablation, kết luận; bật "Hiện số liệu chi tiết" để xem bảng |
| 3. Nhóm: Thí nghiệm 2 | Thắng/hòa/thua của mô hình, thua dồn vào vài câu, kết luận |
| 4. Khai phá dữ liệu | Tìm luật → rút ra nguyên nhân → sửa bằng bỏ phiếu trắng và đo lại |
| 5. Demo mô hình | Chọn 1 trong 113 câu JOB → mô hình chọn phương án → chạy thật cả 6 phương án trên PostgreSQL |

Tab 0–4 chỉ đọc kết quả có sẵn trong `analysis/output/`, không cần Docker. Tab 5 cần container `pg_bao`
(localhost:5432, CSDL `imdbload`); câu lệnh chạy ở chế độ chỉ đọc và có timeout.

---

## 6. Demo trên terminal

| Lệnh | Nội dung | Thời gian |
|---|---|---|
| `bash scripts/demo/demo_26a.sh` | Câu 26a với 3 cách chạy, chênh nhau hàng chục lần | ~1,5 phút |
| `bash scripts/demo/demo_ablation.sh` | Tắt GEQO / bitmap + TID scan trên vài câu JOB | ~1–2 phút |
| `bash scripts/demo/demo_83.sh` | Bao-Full và Bao-50 chọn hint khác nhau trên IMDB đầy đủ | ~1 phút |

Nên chạy `warmup_imdb.sh` (hoặc `demo_start.sh`) trước để thời gian ổn định.

---

## 7. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `No space left on device` | Giải phóng ổ đĩa, `docker system prune`, xóa CSV IMDB sau khi nạp |
| Container bị kill (OOM) | Tăng RAM cho Docker hoặc giảm `work_mem`/`shared_buffers` |
| Bao không kết nối được server | `docker exec -it bao_server tmux attach -t bao`; IP `10.5.0.6`, port 9381 |
| Hint không có tác dụng | Chạy `LOAD 'pg_hint_plan';` trong cùng phiên |
| Streamlit báo `File does not exist` | Đang ở `app/` thì chạy `streamlit run streamlit_app.py` (không thêm `app/`) |
| Dashboard lỗi `AttributeError` sau khi sửa code | Server cũ còn chạy: tắt rồi mở lại |
| Tab 5 báo chưa kết nối | `docker compose -f infra/docker-compose.yml up -d` |
| Thời gian dao động lớn | Cắm sạc, đóng ứng dụng nặng, làm nóng cache, không chạy song song |
