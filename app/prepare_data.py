"""Chuẩn bị dữ liệu cho ứng dụng demo (chạy MỘT lần, cần container pg_bao đang chạy).

    analysis/.venv/bin/python app/prepare_data.py            # EXPLAIN (nhanh, không có q-error)
    analysis/.venv/bin/python app/prepare_data.py --analyze  # EXPLAIN ANALYZE (có q-error, ~30 phút)

Tạo trong analysis/output/app/:
  default_plans.json : plan mặc định của PostgreSQL cho từng câu JOB
  dataset_a.csv      : nguồn A – mỗi câu JOB một dòng: đặc trưng SQL + plan mặc định,
                       thời gian end-to-end của từng phương pháp trong log tác giả, nhãn "phương pháp nhanh nhất".
Sau đó ứng dụng chỉ đọc file, không cần Docker.
"""
import argparse
import glob
import json
import os
import sys

import pandas as pd
import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from extract_features import plan_features, plan_signature, sql_features  # noqa: E402
from lqo_common import load_combined, norm_qid, template_of  # noqa: E402

QUERY_DIR = os.path.join(ROOT, "lqo_ml_perspective/bao/queries/join-order-benchmark")
AUTHORS = os.path.join(ROOT, "lqo_ml_perspective/experiment_logs/20240103__combined.csv")
OUT = os.path.join(ROOT, "analysis/output/app")
METHODS = ["PostgreSQL", "Bao", "HybridQO", "Neo", "Balsa", "LEON"]
JOB_SPLITS = [f"{s}_split_{i}" for s in ("leave_one_out", "random", "base_query") for i in (1, 2, 3)]


def fetch_plans(analyze, timeout_ms):
    conn = psycopg2.connect(dbname="imdbload", user="postgres", password="postgres", host="localhost", port=5432)
    conn.autocommit = True
    cur = conn.cursor()
    plans = {}
    for fp in sorted(glob.glob(os.path.join(QUERY_DIR, "*.sql"))):
        qid = norm_qid(fp)
        sql = open(fp).read().strip().rstrip(";")
        rec = {"sql": sql, "analyzed": False}
        if analyze:
            cur.execute(f"SET statement_timeout = {timeout_ms}")
            try:
                cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}")
                r = cur.fetchone()[0][0]
                rec.update(plan=r["Plan"], analyzed=True,
                           planning_ms=r["Planning Time"], execution_ms=r["Execution Time"])
            except psycopg2.errors.QueryCanceled:
                pass
            cur.execute("SET statement_timeout = 0")
        if "plan" not in rec:
            cur.execute(f"EXPLAIN (FORMAT JSON) {sql}")
            rec["plan"] = cur.fetchone()[0][0]["Plan"]
        plans[qid] = rec
        print(f"{qid:>5} {'ANALYZE' if rec['analyzed'] else 'EXPLAIN'}")
    conn.close()
    return plans


def method_times():
    """Thời gian end-to-end (ms) của mỗi phương pháp cho mỗi câu: trung vị qua các split có câu đó trong tập test."""
    parts = []
    for m in METHODS[1:]:
        for exp in JOB_SPLITS:
            d = load_combined(AUTHORS, m, exp)
            parts.append(d.assign(method=m)[["query_id", "method", "total_ms", "timeout"]])
    lqo = pd.concat(parts)
    t = lqo.pivot_table(index="query_id", columns="method", values="total_ms", aggfunc="median")
    to = lqo.groupby("query_id").timeout.sum().rename("so_lan_timeout_LQO")
    pg = load_combined(AUTHORS, "PostgreSQL").set_index("query_id").total_ms.rename("PostgreSQL")
    t = t.join(pg, how="inner").join(to)
    n_splits = lqo[lqo.method == "Bao"].groupby("query_id").size().rename("so_split_test")
    return t.join(n_splits).dropna(subset=METHODS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analyze", action="store_true", help="dùng EXPLAIN ANALYZE để có q-error")
    ap.add_argument("--timeout_ms", type=int, default=60_000)
    ap.add_argument("--min_gain", type=float, default=0.05,
                    help="phương pháp khác chỉ được coi là tốt hơn PostgreSQL nếu nhanh hơn ít nhất 5%%")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    plans = fetch_plans(a.analyze, a.timeout_ms)
    json.dump(plans, open(os.path.join(OUT, "default_plans.json"), "w"))

    t = method_times()
    best = t[METHODS].idxmin(axis=1)
    best_ms = t[METHODS].min(axis=1)
    keep = best_ms > t.PostgreSQL * (1 - a.min_gain)
    best[keep], best_ms[keep] = "PostgreSQL", t.PostgreSQL[keep]

    rows = []
    for qid in t.index:
        rec = plans[qid]
        r = {"query_id": qid, "template": template_of(qid), "best_hint_set": best[qid],
             "default_ms": t.PostgreSQL[qid], "best_ms": best_ms[qid],
             "plan_signature": plan_signature(rec["plan"]), "plan_analyzed": rec["analyzed"],
             "so_split_test": int(t.so_split_test[qid]), "so_lan_timeout_LQO": int(t.so_lan_timeout_LQO[qid])}
        r.update({f"t_{m}": t[m][qid] for m in METHODS})
        r.update(sql_features(rec["sql"]))
        r.update(plan_features(rec["plan"]))
        rows.append(r)
    df = pd.DataFrame(rows)
    df["speedup_vs_default"] = df.default_ms / df.best_ms
    df.to_csv(os.path.join(OUT, "dataset_a.csv"), index=False)
    print(f"\n{len(df)} câu → {OUT}/dataset_a.csv")
    print("Phân bố nhãn:", df.best_hint_set.value_counts().to_dict())


if __name__ == "__main__":
    main()
