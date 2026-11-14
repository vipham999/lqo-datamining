"""Ablation 8.6 – Cần chạy mỗi truy vấn bao nhiêu lần để thời gian ổn định (hot cache)?

Thu số liệu (trong bao_server):
  python3 /app/scripts/common/run_and_log.py --query_dir /app/bao/queries/join-order-benchmark \
      --hint_sets default --runs 10 --tag k_runs --out /app/logs/job_k_runs.jsonl
Phân tích (trên Mac):
  python scripts/ablation/ablation_k_runs.py --log logs/job_k_runs.jsonl

Với mỗi truy vấn: chênh lệch chuẩn hóa giữa lần k và k+1 = (t_{k+1} - t_k) / t_1 × 100%  (giống Hình 7 bài báo).
"""
import argparse
import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True)
    p.add_argument("--tag", default="k_runs")
    p.add_argument("--out_dir", default="analysis/output")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    df = pd.read_json(a.log, lines=True)
    if "tag" in df:
        df = df[df.tag == a.tag]
    df = df[~df.timeout]
    t = df.pivot_table(index="query_id", columns="run", values="execution_ms", aggfunc="first").dropna()
    diffs = {f"k={k + 1}": (t[k + 1] - t[k]) / t[0] * 100 for k in range(t.columns.max())}
    d = pd.DataFrame(diffs)
    summ = d.describe().T[["mean", "50%", "std", "min", "max"]].rename(columns={"50%": "median"})
    summ.to_csv(os.path.join(a.out_dir, "ablation_k_runs.csv"))
    print(f"{len(t)} truy vấn, {t.shape[1]} lần chạy mỗi câu")
    print("Chênh lệch (%) giữa lần k và k+1, chuẩn hóa theo lần 1:")
    print(summ.round(2).to_string())

    fig, ax = plt.subplots(figsize=(7, 4))
    d.boxplot(ax=ax)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_ylabel("Chênh lệch thời gian chuẩn hóa [%]")
    ax.set_xlabel("Giữa lần chạy thứ k và k+1")
    fig.tight_layout()
    fig.savefig(os.path.join(a.out_dir, "ablation_k_runs.png"), dpi=150)
    print(f"Đã lưu {a.out_dir}/ablation_k_runs.*")


if __name__ == "__main__":
    main()
