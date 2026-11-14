"""Chuyển <run_name>__query_log.csv của HybridQO sang đúng định dạng file wandb_export của tác giả.

    python kaggle/to_wandb_export.py logs/kaggle/hybridqo/leave_one_out_split_1/hqo_logs/2026_11_07__065424__query_log.csv \
        --split leave_one_out_split_1 --rep 0 --out_dir logs/kaggle/hybridqo/wandb_export

Tạo hybrid_qo__JOB__<split>__<rep>.csv giống lqo_ml_perspective/hybrid_qo/logs/wandb_export/:
cột "Step" rồi "<run_name> - <metric>", "__MIN", "__MAX" cho từng metric, giữ nguyên lỗi chính tả
"pg_lateny" của tác giả. Notebook FullEvaluation_JOB_MergeResultFiles.ipynb của tác giả đọc được file
này mà không cần sửa (nó lấy epoch <= 50 lớn nhất có đúng 113 dòng).
Ô 7 trong HUONG_DAN_KAGGLE_HYBRIDQO.md chứa cùng đoạn code này để chạy ngay trên Kaggle.
"""
import argparse
import csv
import os

# Thứ tự cột như file export của tác giả: (tên cột trong export, tên cột trong query_log)
METRICS = [("hinter_latency", "hinter_latency"), ("test_query", "test_query"), ("epoch", "epoch"),
           ("pg_lateny", "pg_latency"), ("pg_plan_time", "pg_plan_time"), ("mcts_time", "mcts_time"),
           ("hinter_plan_time", "hinter_plan_time"), ("MPHE_time", "MPHE_time")]


def to_wandb_export(query_log, split, rep, out_dir):
    run = os.path.basename(query_log).replace("__query_log.csv", "")
    rows = list(csv.DictReader(open(query_log)))
    header = ["Step"] + [f"{run} - {m}{s}" for m, _ in METRICS for s in ("", "__MIN", "__MAX")]
    out = os.path.join(out_dir, f"hybrid_qo__JOB__{split}__{rep}.csv")
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(header)
        for step, r in enumerate(rows):
            w.writerow([step] + [r[c] for _, c in METRICS for _ in range(3)])
    per_epoch = {}
    for r in rows:
        per_epoch[int(r["epoch"])] = per_epoch.get(int(r["epoch"]), 0) + 1
    full = [e for e, n in per_epoch.items() if n == 113 and e <= 50]
    print(f"{out}: {len(rows)} dòng; epoch tác giả sẽ chọn (đủ 113 dòng): {max(full) if full else 'KHÔNG CÓ'}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query_log")
    ap.add_argument("--split", required=True)
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--out_dir", default=".")
    a = ap.parse_args()
    to_wandb_export(a.query_log, a.split, a.rep, a.out_dir)
