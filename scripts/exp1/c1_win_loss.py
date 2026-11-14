"""C1 – So sánh plan cũ (PostgreSQL) và plan mới (LQO): đếm thắng/hòa/thua + kiểm định thống kê.

Hai cách dùng:

1) So sánh tất cả LQO trong log của tác giả với PostgreSQL (chạy được ngay, không cần CSDL):
   python scripts/exp1/c1_win_loss.py --authors lqo_ml_perspective/experiment_logs/20240103__combined.csv

2) So sánh hai log bất kỳ (log bạn tự chạy):
   python scripts/exp1/c1_win_loss.py --baseline txt:logs/mac/postgres/test__postgres__job.txt \
                                 --candidate txt:logs/mac/bao/test__bao__job__random_split_1.txt --name Bao_RND1
   python scripts/exp1/c1_win_loss.py --baseline jsonl:logs/mac/job_hintsets.jsonl:default \
                                 --candidate jsonl:logs/mac/job_hintsets.jsonl:no_nestloop --name no_nestloop

Định nghĩa: speedup = thời gian end-to-end của PostgreSQL / thời gian end-to-end của LQO
  Thắng: speedup > 1 + eps   Hòa: |speedup - 1| <= eps   Thua: speedup < 1 - eps   (eps mặc định 0.1)
Kiểm định: Wilcoxon signed-rank (bắt cặp theo truy vấn, không giả định phân phối chuẩn)
           + sign test (binomial trên số thắng/thua).
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common")]
from lqo_common import load_combined, load_spec  # noqa: E402


def compare(base, cand, name, eps):
    m = base[["query_id", "total_ms"]].merge(cand[["query_id", "total_ms"]], on="query_id",
                                             suffixes=("_pg", "_lqo"))
    if m.empty:
        return None, m
    m["speedup"] = m.total_ms_pg / m.total_ms_lqo
    m["result"] = np.where(m.speedup > 1 + eps, "Thắng", np.where(m.speedup < 1 - eps, "Thua", "Hòa"))
    win, tie, loss = (m.result == "Thắng").sum(), (m.result == "Hòa").sum(), (m.result == "Thua").sum()
    try:
        p_w = wilcoxon(m.total_ms_pg, m.total_ms_lqo).pvalue
    except ValueError:
        p_w = float("nan")
    p_s = binomtest(int(win), int(win + loss), 0.5).pvalue if win + loss > 0 else float("nan")
    row = {
        "phương_pháp": name, "số_câu": len(m), "thắng": win, "hòa": tie, "thua": loss,
        "PG_workload_s": m.total_ms_pg.sum() / 1000, "LQO_workload_s": m.total_ms_lqo.sum() / 1000,
        "speedup_workload": m.total_ms_pg.sum() / m.total_ms_lqo.sum(),
        "speedup_trung_vị": m.speedup.median(),
        "speedup_max": m.speedup.max(), "speedup_min": m.speedup.min(),
        "p_wilcoxon": p_w, "p_sign_test": p_s,
    }
    m.insert(0, "phương_pháp", name)
    return row, m


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--authors", help="experiment_logs/20240103__combined.csv")
    p.add_argument("--baseline")
    p.add_argument("--candidate")
    p.add_argument("--name", default="LQO")
    p.add_argument("--eps", type=float, default=0.1)
    p.add_argument("--out_dir", default="analysis/output")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    rows, details = [], []
    if a.authors:
        pg = load_combined(a.authors, "PostgreSQL")
        raw = pd.read_csv(a.authors)
        # Bỏ các thí nghiệm có imdb50 (ablation 8.3): chúng chạy trên CSDL khác, không so được với PG trên IMDB đầy đủ
        raw = raw[(raw.run_type == "regular") & (raw.split == "test") & ~raw.experiment.str.contains("imdb50")]
        for (method, exp), _ in raw.groupby(["method", "experiment"]):
            cand = load_combined(a.authors, method, exp)
            row, m = compare(pg, cand, f"{method} | {exp}", a.eps)
            if row:
                row["phương_pháp_gốc"], row["split"] = method, exp
                rows.append(row)
                details.append(m)
        prefix = "c1_authors"
    else:
        row, m = compare(load_spec(a.baseline), load_spec(a.candidate), a.name, a.eps)
        rows.append(row)
        details.append(m)
        prefix = f"c1_{a.name}"

    summary = pd.DataFrame(rows)
    pd.concat(details).to_csv(os.path.join(a.out_dir, f"{prefix}_per_query.csv"), index=False)
    summary.to_csv(os.path.join(a.out_dir, f"{prefix}_summary.csv"), index=False)

    pd.set_option("display.width", 200)
    cols = ["phương_pháp", "số_câu", "thắng", "hòa", "thua", "PG_workload_s", "LQO_workload_s",
            "speedup_workload", "p_wilcoxon", "p_sign_test"]
    print(summary[cols].round(4).to_string(index=False))

    if a.authors:
        agg = summary.groupby("phương_pháp_gốc")[["số_câu", "thắng", "hòa", "thua"]].sum()
        agg["PG_workload_s"] = summary.groupby("phương_pháp_gốc").PG_workload_s.sum()
        agg["LQO_workload_s"] = summary.groupby("phương_pháp_gốc").LQO_workload_s.sum()
        agg["speedup_workload"] = agg.PG_workload_s / agg.LQO_workload_s
        agg = agg.sort_values("speedup_workload", ascending=False)
        agg.to_csv(os.path.join(a.out_dir, f"{prefix}_by_method.csv"))
        print("\nGộp theo phương pháp (tất cả split JOB, tập test):")
        print(agg.round(3).to_string())
    print(f"\nĐã lưu vào {a.out_dir}/{prefix}_*.csv")


if __name__ == "__main__":
    main()
