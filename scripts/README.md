# scripts/

Các script được chia theo bước thực hiện. Chạy mọi lệnh **từ thư mục gốc của repo**.
Thư mục này được mount vào cả hai container tại `/app/scripts`, nên trong container gọi bằng `/app/scripts/<thư_mục>/<file>`.

| Thư mục | Dùng khi | File chính |
|---|---|---|
| `setup/` | Chuẩn bị CSDL và Bao server (chạy **trong container**) | `load_imdb.sh` nạp IMDB · `make_imdb50.sh` tạo IMDB 50% · `warmup_imdb.sh` làm nóng cache · `start_bao_server.sh` |
| `exp1/` | Thí nghiệm 1: PostgreSQL vs Bao trên 9 split | `run_fair_comparison.sh` chạy cả quy trình · `run_baseline.sh`, `run_bao_split.sh`, `run_bao_test.sh` · `c1_win_loss.py` thắng/hòa/thua + kiểm định · `compare_baseline.py` so baseline nhóm với tác giả · `exp1_tables.py` gom bảng cho dashboard |
| `ablation/` | Tắt từng thành phần (8.3–8.7 trong bài báo) | `run_ablation_interleaved.sh` → `ablation_interleaved.py` + `ablation_analyze.py` (GEQO, bitmap/TID scan) · `ablation_k_runs.py` (số lần chạy) · `join_orders.py` (bushy/left-deep) |
| `exp2/` | Thí nghiệm 2 và khai phá dữ liệu | `exp2_collect.sh` đo 113 câu × 6 phương án · `exp2_analyze.py` huấn luyện 3 mô hình · `exp2_mining.py` tìm luật · `exp2_abstain.py` bỏ phiếu trắng theo ngưỡng |
| `demo/` | Demo khi báo cáo | `demo_start.sh` mở dashboard · `demo_26a.sh` · `demo_ablation.sh` · `demo_83.sh` |
| `common/` | Thư viện dùng chung, không chạy trực tiếp | `lqo_common.py` đọc log · `extract_features.py` đặc trưng SQL + plan · `run_and_log.py` chạy câu × hint set, ghi plan |

## Thứ tự chạy

```bash
# 1. Chuẩn bị
docker exec -it pg_bao bash /app/scripts/setup/load_imdb.sh
docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh

# 2. Thí nghiệm 1
caffeinate -dis bash scripts/exp1/run_fair_comparison.sh
python3 scripts/exp1/exp1_tables.py

# 3. Ablation
bash scripts/ablation/run_ablation_interleaved.sh

# 4. Thí nghiệm 2 + khai phá dữ liệu
bash scripts/exp2/exp2_collect.sh
~/.venvs/lqo_app/bin/python scripts/exp2/exp2_analyze.py
~/.venvs/lqo_app/bin/python scripts/exp2/exp2_mining.py
~/.venvs/lqo_app/bin/python scripts/exp2/exp2_abstain.py

# 5. Demo
bash scripts/demo/demo_start.sh
```

Script Python ngoài `common/` tự thêm `common/` vào `sys.path`, nên chạy được từ bất kỳ đâu.
