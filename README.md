# Tái lập bài báo "Is Your Learned Query Optimizer Behaving As You Expect?" + mở rộng Data Mining

Hướng dẫn chạy lại thực nghiệm của bài báo (Lehmann, Sulimov, Stockinger, PVLDB 2024) trên
**MacBook Pro M1 Pro (8 core, 16 GB RAM, ARM64, không có GPU NVIDIA)**, rồi thêm phần **data mining**
để so sánh plan cũ (PostgreSQL) với plan mới (LQO).

Repo của tác giả: [edualc/lqo_ml_perspective](https://github.com/edualc/lqo_ml_perspective), đã clone vào `lqo_ml_perspective/`.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| Image `pg_lqo_arm64` (PostgreSQL 12.5 + `pg_hint_plan` + `pg_bao`, ARM64) | ✅ Đã build và chạy thử: cấu hình nạp đúng, hint `MergeJoin`/`Leading` có tác dụng |
| Image `bao_server_arm64` | ✅ Đã build (748 MB), PyTorch 1.13.0 import được |
| Script Phần B, C và ablation 8.6/8.7 | ✅ Đã chạy thử trọn pipeline trên một CSDL nhỏ tự sinh |
| C1 trên log của tác giả | ✅ Đã chạy, kết quả ở `analysis/output/c1_authors_*.csv` |
| Dữ liệu IMDB | ✅ Đã nạp vào `imdbload` (12 GB), `pg_hint_plan` hoạt động, đã chạy thử JOB 1a |
| Dữ liệu STACK | ❌ Không làm (dump quá lớn) |

---

## Mục lục

0. [Phạm vi](#0-phạm-vi)
1. [Chuẩn bị máy](#1-chuẩn-bị-máy)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Môi trường phân tích và dữ liệu](#3-môi-trường-phân-tích-và-dữ-liệu)
4. [Khởi động PostgreSQL và Bao](#4-khởi-động-postgresql-và-bao)
5. [Nạp CSDL IMDB](#5-nạp-csdl-imdb)
6. [Phần A – Tái lập thực nghiệm](#6-phần-a--tái-lập-thực-nghiệm)
7. [Phần B – Ghi log plan](#7-phần-b--ghi-log-plan)
8. [Phần C – Data mining](#8-phần-c--data-mining)
9. [Phần D – Thêm benchmark](#9-phần-d--thêm-benchmark)
10. [Lỗi thường gặp](#10-lỗi-thường-gặp)
11. [Checklist](#11-checklist)

---

## 0. Phạm vi

| Phần trong bài báo | Làm được? | Cách làm |
|---|---|---|
| Baseline PostgreSQL trên JOB | ✅ | `scripts/run_baseline.sh` |
| Bao trên JOB | 🟡 | `scripts/run_bao_split.sh`, train trên CPU, nên chạy 3 split: LOO-1, RND-1, BQ-1 |
| HybridQO | ❌ | Không chạy (~20 giờ/split) → dùng log của tác giả |
| Neo, Balsa, LEON | ❌ | Cần CUDA và 20–130 giờ/split → dùng log của tác giả `experiment_logs/*.csv` |
| STACK | ❌ (tạm) | Dump rất lớn, chỉ làm khi đủ ổ đĩa |
| Ablation 8.3–8.7 | ✅ | `make_imdb50.sh`, `run_and_log.py --tag`, `ablation_k_runs.py`, `join_orders.py` |
| Data mining C1–C3 | ✅ | `c1_win_loss.py`, `c2_classify.py`, `c3_explain.py` |
| Thêm benchmark CEB-IMDb | ✅ | Dùng lại CSDL IMDB |

Vì phần cứng và cấu hình khác bài báo, **số tuyệt đối sẽ khác**. Mục tiêu là kiểm tra **xu hướng**:
PostgreSQL có còn thắng Bao không, Base Query split có khó nhất không. Ghi rõ khác biệt này trong báo cáo.

---

## 1. Chuẩn bị máy

**Giải phóng ổ đĩa (bắt buộc):** máy hiện chỉ còn trống **~4 GB**. Cần **ít nhất 40–60 GB**:

| Thành phần | Dung lượng ước tính |
|---|---|
| `imdb.tgz` + CSV giải nén | ~5 GB (xóa được sau khi nạp) |
| CSDL IMDB trong PostgreSQL (kèm index) | ~10 GB |
| Bản sao IMDB-50% (ablation 8.3) | ~10 GB |
| Image `bao_server_arm64` (có PyTorch) | ~1.5 GB |
| Log, mô hình, dự phòng | ~10 GB |

```bash
df -h /System/Volumes/Data      # dung lượng trống
docker system df                # Docker đang chiếm bao nhiêu
```

**RAM cho Docker:** vào Docker Desktop → Settings → Resources, đặt Memory **10–12 GB** (hiện là 8 GB) và CPUs **8**.

---

## 2. Cấu trúc thư mục

```
lqo-datamining/
├── README.md
├── .dockerignore                 ← giới hạn build context của Docker
├── lqo_ml_perspective/           ← repo tác giả (bao.cfg đã sửa CSDL: so → imdbload)
├── infra/
│   ├── Dockerfile.pg             ← PostgreSQL 12.5 + pg_hint_plan (PG12) + pg_bao, build từ source
│   ├── Dockerfile.bao            ← Bao server + thư viện Python (ARM64)
│   ├── requirements.bao.txt      ← torch==1.13.0 thay cho 1.13.0+cpu (chỉ có trên x86)
│   ├── postgresql.lqo.conf       ← cấu hình đã thu nhỏ cho 16 GB RAM
│   ├── start.sh                  ← initdb lần đầu, chép conf, chạy postgres
│   └── docker-compose.yml        ← pg_bao (10.5.0.5) + bao_server (10.5.0.6), giống repo gốc
├── scripts/
│   ├── load_imdb.sh              ← nạp IMDB + index bổ sung + ANALYZE
│   ├── make_imdb50.sh            ← ablation 8.3: tạo imdbload50
│   ├── start_bao_server.sh       ← chạy Bao server trong tmux
│   ├── run_baseline.sh           ← baseline PostgreSQL (113 câu × 3 lần)
│   ├── run_bao_split.sh          ← train + test Bao trên 1 split, ghi thời gian train
│   ├── run_and_log.py            ← Phần B: chạy truy vấn × hint set, ghi JSONL kèm plan
│   ├── join_orders.py            ← ablation 8.7: bushy và left-deep
│   ├── ablation_k_runs.py        ← ablation 8.6: số lần chạy k
│   ├── extract_features.py       ← Phần C: đặc trưng SQL + plan
│   ├── label.py                  ← Phần C: nhãn "plan tốt nhất"
│   ├── c1_win_loss.py            ← C1: thắng/hòa/thua + Wilcoxon + sign test
│   ├── c2_classify.py            ← C2: phân loại với 3 kiểu chia của bài báo
│   ├── c3_explain.py             ← C3: K-means, Apriori, feature importance, cây quyết định, TED
│   └── lqo_common.py             ← đọc các loại log về cùng một định dạng
├── logs/                         ← log thô (mount vào cả hai container tại /app/logs)
└── analysis/
    ├── .venv/                    ← môi trường Python cho phân tích (đã tạo)
    ├── requirements.txt
    └── output/                   ← bảng CSV và hình PNG
```

Trong container: `/app/lqo` = repo tác giả, `/app/bao` = `lqo_ml_perspective/bao`, `/app/scripts`, `/app/logs`.

---

## 3. Môi trường phân tích và dữ liệu

### 3.1 Python trên Mac

`analysis/.venv` đã được tạo sẵn. Python mặc định của conda trên máy đang lỗi scipy, nên luôn dùng môi trường này.
Venv ghi cứng đường dẫn tuyệt đối, nên sau khi đổi tên hoặc chuyển thư mục project phải tạo lại:
`rm -rf analysis/.venv && /opt/miniconda3/bin/python3 -m venv analysis/.venv && analysis/.venv/bin/pip install -r analysis/requirements.txt`.

```bash
cd ~/Desktop/lqo-datamining
source analysis/.venv/bin/activate
# cài lại nếu cần: pip install -r analysis/requirements.txt
```

### 3.2 Chạy ngay: C1 trên log của tác giả (không cần CSDL)

```bash
python scripts/c1_win_loss.py --authors lqo_ml_perspective/experiment_logs/20240103__combined.csv
```

Kết quả đã chạy (tất cả split JOB, tập test, ngưỡng hòa ±10%):

| Phương pháp | Số câu | Thắng | Hòa | Thua | Workload PG (s) | Workload LQO (s) | Speedup |
|---|---|---|---|---|---|---|---|
| HybridQO | 233 | 34 | 82 | 117 | 264.2 | 263.9 | 1.00× |
| Bao | 233 | 9 | 34 | 190 | 264.2 | 320.1 | 0.83× |
| Balsa | 233 | 16 | 4 | 213 | 264.2 | 958.9 | 0.28× |
| Neo | 233 | 21 | 12 | 200 | 264.2 | 1665.4 | 0.16× |
| LEON | 233 | 0 | 0 | 233 | 264.2 | 265553.4 | 0.001× |

→ Khớp với kết luận của bài báo: PostgreSQL ≥ HybridQO > Bao > Balsa/Neo > LEON.
Chi tiết theo từng split và p-value nằm ở `analysis/output/c1_authors_summary.csv`.

Notebook vẽ lại các hình của tác giả: `lqo_ml_perspective/notebooks/FullEvaluation_JOB_ResultAnalysis.ipynb`.

### 3.3 Dữ liệu IMDB (sau khi đã giải phóng ổ đĩa)

```bash
cd ~/Desktop/lqo-datamining/lqo_ml_perspective/data
mkdir -p imdb && cd imdb
wget -c https://event.cwi.nl/da/job/imdb.tgz && tar -xvzf imdb.tgz   # link cũ homepages.cwi.nl/~boncz/job đã 404
cd .. && python prepend_imdb_headers.py   # thêm header cho các file CSV; cần absl-py (pip install absl-py)
```

STACK (tùy chọn, rất lớn): `wget https://www.dropbox.com/s/98u5ec6yb365913/so_pg12` vào `data/stack/`.

---

## 4. Khởi động PostgreSQL và Bao

```bash
cd ~/Desktop/lqo-datamining/infra
docker compose build bao        # lần đầu: cài PyTorch ARM64 (~1.5 GB), CHƯA chạy thử
docker compose up -d
docker exec pg_bao psql -c "SELECT version();"                 # PostgreSQL 12.5 ... aarch64
docker exec pg_bao psql -c "SHOW shared_preload_libraries;"    # pg_bao
```

Image `pg_lqo_arm64` đã được build sẵn. Nếu cần build lại: `docker compose build postgres` (~5 phút).

**Cấu hình** (`infra/postgresql.lqo.conf`, so với Bảng 2 của bài báo):

| Tham số | Bài báo | Ở đây |
|---|---|---|
| `shared_buffers` | 32 GB | 3 GB |
| `work_mem` | 4 GB | 128 MB |
| `temp_buffers` | 32 GB | 256 MB |
| `effective_cache_size` | 32 GB | 8 GB |
| `max_worker_processes` | 8 | 6 |
| `geqo` | on (Bao) / off | on, tắt theo phiên khi cần |
| `autovacuum` | off | off |
| bitmap/tid scan | on | on |
| Phần cứng | x86, 16 core, 64 GB, T4 | Apple M1 Pro, 8 core, 16 GB |

Sửa file conf rồi chạy `docker compose restart postgres` là áp dụng (start.sh chép lại conf mỗi lần khởi động).
`pg_hint_plan` không preload, mà được nạp theo phiên bằng `LOAD 'pg_hint_plan'` (`join_orders.py` tự làm việc này).

---

## 5. Nạp CSDL IMDB

```bash
docker exec -it pg_bao bash /app/scripts/load_imdb.sh     # ~15–30 phút
```

Script nạp schema và dữ liệu bằng script của Balsa. Script này đã tạo sẵn index `complete_cast(subject_id)` và
`(status_id)` (Mục 8.1.1) và chạy `ANALYZE` **một lần** ở cuối. Kết quả đã nạp: 21 bảng, CSDL 12 GB,
`cast_info` 36.244.344 dòng, `title` 2.528.312 dòng.

Kiểm tra hint:

```bash
docker exec pg_bao psql -d imdbload -c "LOAD 'pg_hint_plan';" \
  -c "/*+ MergeJoin(ml lt) */ EXPLAIN SELECT COUNT(*) FROM movie_link ml JOIN link_type lt ON ml.link_type_id = lt.id;"
# phải thấy "Merge Join"
```

---

## 6. Phần A – Tái lập thực nghiệm

Các lệnh dưới đây chạy **trong container `bao_server`**, nên dùng tmux vì có lệnh chạy hàng giờ:

```bash
docker exec -it bao_server bash
tmux new -s run          # thoát mà vẫn chạy: Ctrl+B rồi D; quay lại: tmux attach -t run
```

### 6.1 Baseline PostgreSQL

```bash
bash /app/scripts/run_baseline.sh                      # 113 câu × 3 lần → /app/logs/test__postgres__job__*.txt
bash /app/scripts/run_baseline.sh imdbload no_geqo     # ablation 8.5: tắt GEQO
```

### 6.2 Bao

```bash
bash /app/scripts/run_bao_split.sh job__random_split_1
bash /app/scripts/run_bao_split.sh job__leave_one_out_split_1
bash /app/scripts/run_bao_split.sh job__base_query_split_1
```

Mỗi lần chạy, script sẽ:
1. Xóa kinh nghiệm và model cũ, rồi khởi động Bao server.
2. Train trên `queries/<split>/train`; thời gian train ghi vào `logs/bao_training_times.csv`.
3. Lưu model và test trên `queries/<split>/test`.

### 6.3 So sánh với PostgreSQL (trên Mac)

```bash
python scripts/c1_win_loss.py --baseline txt:logs/test__postgres__job__<thời_gian>.txt \
    --candidate txt:logs/test__bao__job__random_split_1__<thời_gian>.txt --name Bao_RND1
```

So số của bạn với `analysis/output/c1_authors_summary.csv` (dòng `Bao | random_split_1`) để đánh giá mức độ tái lập.

### 6.4 Ablation

| Mục | Lệnh |
|---|---|
| **8.3 Covariate shift** | `docker exec -it pg_bao bash /app/scripts/make_imdb50.sh`, rồi chạy lại baseline/Bao với `imdbload50` |
| **8.4 Bitmap/Tid scan** | `python3 /app/scripts/run_and_log.py --query_dir /app/bao/queries/join-order-benchmark --hint_sets default --extra_set "SET enable_bitmapscan = off; SET enable_tidscan = off" --tag no_bitmap_tidscan --out /app/logs/job_ablation.jsonl` |
| **8.5 GEQO** | `bash /app/scripts/run_baseline.sh imdbload no_geqo` |
| **8.6 Số lần chạy k** | `python3 /app/scripts/run_and_log.py --query_dir /app/bao/queries/join-order-benchmark --hint_sets default --runs 10 --tag k_runs --out /app/logs/job_k_runs.jsonl`, rồi trên Mac: `python scripts/ablation_k_runs.py --log logs/job_k_runs.jsonl` |
| **8.7 Bushy và left-deep** | `python3 /app/scripts/join_orders.py run --query_dir /app/bao/queries/join-order-benchmark --out /app/logs/job_join_orders.jsonl`, rồi trên Mac: `python scripts/join_orders.py analyze --log logs/job_join_orders.jsonl` |

`join_orders.py` duyệt mọi cây join không có tích Descartes của các truy vấn ≤ 6 bảng (≤ 5 join). Mỗi truy vấn
lấy mẫu tối đa `--max_plans` cây (mặc định 300). Mỗi cây được ép bằng `Leading(...)` và kiểm định bằng Mann-Whitney U.

---

## 7. Phần B – Ghi log plan

Script của repo chỉ lưu thời gian. `scripts/run_and_log.py` lưu thêm **plan JSON** của mỗi lần chạy, với 6 hint set
kiểu Bao: `default`, `no_nestloop`, `no_hashjoin`, `no_mergejoin`, `no_seqscan`, `no_indexscan`.

```bash
# trong bao_server
python3 /app/scripts/run_and_log.py --query_dir /app/bao/queries/join-order-benchmark \
    --out /app/logs/job_hintsets.jsonl
```

- 113 câu × 6 hint set × 3 lần ≈ 2.000 lần chạy, mất vài giờ đến 1 ngày (timeout mặc định 3 phút).
- Có thể **chạy tiếp** sau khi bị ngắt: script tự bỏ qua các (truy vấn, hint set, tag) đã có trong file log.

Mỗi dòng log là một lần chạy:

```json
{"query_id": "1a", "benchmark": "JOB", "db": "imdbload", "hint_set": "no_nestloop", "tag": "",
 "run": 2, "planning_ms": 5.3, "execution_ms": 830.7, "timeout": false, "plan": {...}}
```

Quy ước:
- Phân tích dùng `run = 2` (lần chạy thứ 3, hot cache) như bài báo.
- **Plan cũ** = `default`. **Plan mới** = hint set nhanh nhất, hoặc plan Bao chọn (cột hint trong log của Bao).
- Câu bị timeout vẫn được giữ lại, gán thời gian = timeout và đánh dấu `timeout: true`.

---

## 8. Phần C – Data mining

Chạy trên Mac với `source analysis/.venv/bin/activate`. Kết quả ghi vào `analysis/output/`.

```bash
python scripts/extract_features.py --log logs/job_hintsets.jsonl \
    --query_dir lqo_ml_perspective/bao/queries/join-order-benchmark --out analysis/output/features.csv
python scripts/label.py   --log logs/job_hintsets.jsonl --out analysis/output/labels.csv
python scripts/c1_win_loss.py --baseline jsonl:logs/job_hintsets.jsonl:default \
                              --candidate jsonl:logs/job_hintsets.jsonl:no_nestloop --name no_nestloop
python scripts/c2_classify.py --features analysis/output/features.csv --labels analysis/output/labels.csv
python scripts/c3_explain.py  --features analysis/output/features.csv --labels analysis/output/labels.csv \
                              --log logs/job_hintsets.jsonl
```

### 8.1 Đặc trưng (`extract_features.py`)

| Nhóm | Đặc trưng |
|---|---|
| SQL | số bảng, số điều kiện join, số filter, số `LIKE`/`NOT LIKE`/`IN`/`BETWEEN`/`OR`/`IS NULL`/so sánh khoảng |
| Cấu trúc plan | số node, độ sâu, số join bushy, plan có bushy không |
| Toán tử | số Hash/Merge/Nested Loop join; Seq/Index/Index Only/Bitmap scan; Hash, Sort, Materialize, Gather... |
| Ước lượng | cost, số dòng ước lượng, **q-error** lớn nhất và trung bình (sai số cardinality) |

### 8.2 Nhãn (`label.py`)

- `best_hint_set` là hint set có thời gian end-to-end nhỏ nhất.
- Chỉ được tính là tốt hơn `default` nếu nhanh hơn **≥ 5%** (`--min_gain`).
- Hint set nào cho ra **cùng cây plan** với `default` thì được tính bằng thời gian của `default`, để nhiễu đo
  không bị gán nhầm thành "plan tốt hơn". Khi chạy thử, có 54/120 cặp (truy vấn, hint set) như vậy.

### 8.3 C1 – Thắng/hòa/thua (`c1_win_loss.py`)

- `speedup = thời gian PostgreSQL / thời gian LQO`. Thắng nếu > 1.1, thua nếu < 0.9, còn lại là hòa.
- Kiểm định **Wilcoxon signed-rank** (dữ liệu bắt cặp) và **sign test**.
- Định dạng nguồn log: `txt:<file>` (log repo), `jsonl:<file>:<hint_set>[:<tag>]`,
  `combined:<file>:<method>[:<experiment>]`.

### 8.4 C2 – Phân loại "truy vấn này nên dùng plan nào" (`c2_classify.py`)

- **X**: đặc trưng SQL + plan **mặc định**. Chỉ dùng thông tin có trước khi thử hint set khác, nên không rò rỉ nhãn.
- **y**: `best_hint_set`.
- **3 kiểu chia giống bài báo**: `leave_one_out` (mỗi fold lấy 1 biến thể của mỗi truy vấn gốc), `random` (KFold 5),
  `base_query` (GroupKFold theo truy vấn gốc).
- **Mô hình**: Decision Tree, Random Forest, Gradient Boosting, kNN, Naive Bayes, SVM, Logistic Regression,
  cùng hai mốc so sánh: **Luôn_PostgreSQL** và **Oracle**.
- **Chỉ số**: số câu đúng / tổng, accuracy, macro-F1, tổng thời gian workload so với PostgreSQL và Oracle,
  regret, số câu bị chậm đi > 10%, McNemar so với Luôn_PostgreSQL.
- Confusion matrix của mô hình tốt nhất ở mỗi kiểu chia: `c2_confusion__<kiểu_chia>__<mô_hình>.csv`.

### 8.5 C3 – Giải thích (`c3_explain.py`)

| Kĩ thuật | Đầu ra |
|---|---|
| K-means (k chọn theo silhouette) + PCA | `c3_clusters.csv`, `c3_clusters_pca.png` |
| Apriori: `{đặc điểm} → best=<hint set>` | `c3_rules.csv` (support, confidence, lift) |
| Permutation importance (Random Forest) | `c3_feature_importance.csv/.png` |
| Cây quyết định độ sâu 3 | `c3_decision_tree.txt` |
| Tree edit distance giữa plan cũ và plan tốt nhất, Spearman với speedup | `c3_tree_edit_distance.csv` |

Để minh họa trong báo cáo, chọn 2–3 truy vấn có speedup lớn nhất từ `labels.csv`, rồi in plan cũ cạnh plan mới:

```bash
docker exec pg_bao psql -d imdbload -c "EXPLAIN (ANALYZE) $(cat lqo_ml_perspective/bao/queries/join-order-benchmark/1a.sql)"
docker exec pg_bao psql -d imdbload -c "SET enable_nestloop = off;" -c "EXPLAIN (ANALYZE) $(cat ...)"
```

---

## 9. Phần D – Thêm benchmark

**Khuyến nghị: CEB-IMDb** ([github.com/learned-systems/CEB](https://github.com/learned-systems/CEB)).
Benchmark này chạy trên **cùng CSDL IMDB** và có hàng nghìn truy vấn sinh từ template, đủ để lấy mẫu **~1000 câu** cho C2.

1. Tải bộ truy vấn theo README của CEB, rồi chuyển mỗi truy vấn thành một file `.sql` trong
   `lqo_ml_perspective/data/ceb/`. Đặt tên dạng `<template><biến_thể>.sql` (ví dụ `1a.sql`, `1b.sql`) để
   `template_of()` nhận ra truy vấn gốc.
2. Chạy: `python3 /app/scripts/run_and_log.py --query_dir /app/data/ceb --benchmark CEB --timeout_ms 60000 --out /app/logs/ceb_hintsets.jsonl`
3. Lặp lại mục 8 với `logs/ceb_hintsets.jsonl` và so sánh với JOB.

Lựa chọn khác: **DSB** (dữ liệu lệch) ở scale factor nhỏ (SF 1–2).

---

## 9b. Ứng dụng demo: phân loại plan

Ứng dụng Streamlit trong `app/`: dự đoán mỗi câu nên dùng plan nào, đếm số câu đúng theo 3 kiểu chia của bài báo,
giải thích bằng data mining, và hiển thị kết quả của bài báo.

**Môi trường riêng ngoài Desktop.** Desktop đang được iCloud tối ưu dung lượng nên các file trong
`analysis/.venv` có thể bị đẩy lên mây (dataless), làm Python treo khi import. Ứng dụng dùng `~/.venvs/lqo_app`:

```bash
/opt/miniconda3/bin/python3 -m venv ~/.venvs/lqo_app
~/.venvs/lqo_app/bin/pip install pandas numpy scipy scikit-learn mlxtend zss matplotlib psycopg2-binary streamlit
```

**Chuẩn bị dữ liệu (một lần, cần container `pg_bao`):**

```bash
~/.venvs/lqo_app/bin/python app/prepare_data.py            # EXPLAIN, vài giây
~/.venvs/lqo_app/bin/python app/prepare_data.py --analyze  # EXPLAIN ANALYZE để có q-error, ~30 phút
```

Kết quả nằm ở `analysis/output/app/` (`dataset_a.csv`, `default_plans.json`). Sau bước này ứng dụng chạy không cần Docker.

**Chạy ứng dụng:**

```bash
cd ~/Desktop/lqo-datamining/app && ~/.venvs/lqo_app/bin/streamlit run streamlit_app.py
```

| Nguồn dữ liệu | Nhãn | Cần |
|---|---|---|
| A – log của tác giả | Phương pháp nhanh nhất cho mỗi câu (PostgreSQL, Bao, HybridQO, Neo, Balsa, LEON) | `prepare_data.py` |
| B – 6 hint set | Hint set nhanh nhất | `analysis/output/features.csv` và `labels.csv` (mục 8) |

---

## 10. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `No space left on device` | Giải phóng ổ đĩa; `docker system prune`; xóa CSV sau khi nạp |
| Container bị kill (OOM) | Tăng RAM Docker; giảm `work_mem` hoặc `shared_buffers` trong `infra/postgresql.lqo.conf` |
| `pip install torch` lỗi khi build `bao` | Sửa `infra/requirements.bao.txt` thành `torch==2.0.1` |
| Bao không kết nối được server | `tmux attach -t bao` trong `bao_server` để xem log; IP phải là `10.5.0.6`, port 9381 |
| `FileExistsError` ở script của repo | Script không ghi đè log; đổi `--output_file` hoặc xóa file cũ |
| Hint không có tác dụng | Chạy `LOAD 'pg_hint_plan';` trong cùng phiên trước câu truy vấn |
| `python` trên Mac báo lỗi scipy | Dùng `analysis/.venv/bin/python`, không dùng Python của conda |
| Thời gian dao động lớn | Cắm sạc, đóng ứng dụng nặng, không chạy song song nhiều thí nghiệm |

---

## 11. Checklist

**Tuần 1 – Môi trường**
- [x] Clone repo, build image PostgreSQL ARM64, tạo `analysis/.venv`
- [x] C1 trên log của tác giả
- [x] Giải phóng ≥ 40 GB ổ đĩa, Docker RAM 10–12 GB (OrbStack: 11 GB, 8 CPU)
- [x] `docker compose build bao`, tải IMDB, chạy `load_imdb.sh`

**Tuần 2 – Tái lập**
- [x] Baseline PostgreSQL (6.1): `logs/test__postgres__job__20261011_1743.txt`, 112/113 câu chạy được (25c timeout).
  So với log tác giả: trung vị từng câu 0.81× (M1 nhanh hơn), Spearman 0.965, nhưng tổng workload 2.95× do vài câu
  (18a, 18c, 06d, 23c, 08a, 25c) có plan nested loop nặng; đổi `work_mem`/`effective_cache_size` không làm plan thay đổi
- [ ] Bao trên LOO-1, RND-1, BQ-1 (6.2) và so với log của tác giả (6.3)

**Tuần 3 – Ablation và log plan**
- [ ] 8.4, 8.5, 8.6; tùy chọn 8.3, 8.7
- [ ] `run_and_log.py` cho JOB × 6 hint set (Phần B)

**Tuần 4 – Data mining trên JOB**
- [ ] `extract_features.py`, `label.py`
- [ ] C1, C2 (3 kiểu chia), C3

**Tuần 5 – Thêm benchmark**
- [ ] CEB-IMDb ~1000 câu, lặp lại C1–C3

**Tuần 6 – Báo cáo**
- [ ] Mục "Khác biệt môi trường so với bài báo" (bảng ở mục 4)
- [ ] Bảng, hình, ví dụ plan cũ và plan mới
- [ ] Kết luận: xu hướng có khớp bài báo không, data mining cho thấy thêm điều gì
