"""So sánh baseline PostgreSQL của nhóm với PostgreSQL trong log của tác giả (mức độ tái lập),
và đo hiệu ứng cache theo số lần chạy k như ablation 8.6 (Hình 7 của bài báo).

    python scripts/exp1/compare_baseline.py --ours logs/test__postgres__job__<thời_gian>.txt \
        --authors lqo_ml_perspective/experiment_logs/20240103__combined.csv
"""
import argparse
import os
import sys

import pandas as pd
from scipy.stats import spearmanr

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common")]
from lqo_common import load_combined, load_repo_txt, norm_qid


def all_runs_repo_txt(path):
    """Mọi lần chạy (run 0, 1, 2) từ log của run_test_queries.py."""
    rows = []
    with open(path) as f:
        for line in f:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue
            rows.append({"query_id": norm_qid(parts[-4]), "run": int(parts[-6]),
                         "execution_ms": float(parts[-2])})
    return pd.DataFrame(rows)


def all_runs_authors(path):
    df = pd.read_csv(path)
    df = df[(df.run_type == "regular") & (df.method == "PostgreSQL")].copy()
    df["query_id"] = df.query_ident.map(norm_qid)
    df = df.sort_values("run_id")
    df["run"] = df.groupby("query_id").cumcount()
    return df.rename(columns={"execution_time": "execution_ms"})[["query_id", "run", "execution_ms"]]


def k_run_effect(runs, max_k):
    """Hình 7: chênh lệch giữa lần k và k+1, chuẩn hóa theo lần chạy đầu tiên (%)."""
    wide = runs.pivot_table(index="query_id", columns="run", values="execution_ms")
    out = []
    for k in range(min(max_k, wide.columns.max())):
        d = (wide[k + 1] - wide[k]) / wide[0] * 100
        out.append({"k": k + 1, "so_cau": int(d.notna().sum()),
                    "trung_binh_%": d.mean(), "trung_vi_%": d.median()})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", required=True)
    ap.add_argument("--authors", required=True)
    ap.add_argument("--out_dir", default="analysis/output")
    ap.add_argument("--band", type=float, default=0.25, help="ngưỡng 'khớp' theo tỉ lệ, mặc định ±25%")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    ours = load_repo_txt(a.ours)            # lần chạy thứ 3 (hot cache), như bài báo
    auth = load_combined(a.authors, "PostgreSQL")
    m = ours.merge(auth, on=["query_id", "template"], suffixes=("_nhom", "_tacgia"))
    m["ti_le"] = m.total_ms_nhom / m.total_ms_tacgia
    m.sort_values("query_id").to_csv(f"{a.out_dir}/baseline_vs_authors_per_query.csv", index=False)

    rho, p = spearmanr(m.total_ms_nhom, m.total_ms_tacgia)
    lo, hi = 1 - a.band, 1 + a.band
    summary = pd.DataFrame([{
        "so_cau": len(m),
        "workload_nhom_s": m.total_ms_nhom.sum() / 1000,
        "workload_tacgia_s": m.total_ms_tacgia.sum() / 1000,
        "ti_le_workload": m.total_ms_nhom.sum() / m.total_ms_tacgia.sum(),
        "ti_le_trung_vi": m.ti_le.median(),
        "spearman_rho": rho, "spearman_p": p,
        f"so_cau_khop_±{int(a.band * 100)}%": int(((m.ti_le >= lo) & (m.ti_le <= hi)).sum()),
        "so_cau_cham_hon": int((m.ti_le > hi).sum()),
        "so_cau_nhanh_hon": int((m.ti_le < lo).sum()),
        "timeout_nhom": int(m.timeout_nhom.sum()),
    }])
    summary.to_csv(f"{a.out_dir}/baseline_vs_authors_summary.csv", index=False)

    k_ours = k_run_effect(all_runs_repo_txt(a.ours), 2).assign(nguon="nhom")
    k_auth = k_run_effect(all_runs_authors(a.authors), 4).assign(nguon="tac_gia")
    k_df = pd.concat([k_ours, k_auth])
    k_df.to_csv(f"{a.out_dir}/baseline_k_runs.csv", index=False)

    pd.set_option("display.width", 200)
    print("== Tóm tắt baseline nhóm so với tác giả (lần chạy thứ 3, end-to-end)")
    print(summary.T.to_string(header=False))
    cols = ["query_id", "total_ms_nhom", "total_ms_tacgia", "ti_le"]
    print("\n== 5 câu chậm hơn tác giả nhiều nhất\n", m.nlargest(5, "ti_le")[cols].to_string(index=False))
    print("\n== 5 câu nhanh hơn tác giả nhiều nhất\n", m.nsmallest(5, "ti_le")[cols].to_string(index=False))
    print("\n== Hiệu ứng cache theo k (Hình 7: lần 1→2 giảm 14,6%, lần 2→3 giảm thêm 1,03%)")
    print(k_df.to_string(index=False))


if __name__ == "__main__":
    main()
