"""Đánh giá workload STACK và thời gian chạy của từng LQO trên STACK (so với JOB), từ log của tác giả.

Không cần CSDL: chỉ đọc file truy vấn trong hybrid_qo/workload và log trong experiment_logs.

   python scripts/stack_analysis.py

Phần 1 – Workload: với mỗi truy vấn đếm số bảng, số join, số điều kiện lọc và kiểu lọc (IN, khoảng, LIKE, ...).
Phần 2 – Thời gian chạy (tập test, lần chạy cuối = cache nóng): suy luận, lập kế hoạch, thực thi, end-to-end,
         timeout, speedup so với PostgreSQL; theo từng split và so với JOB.
Phần 3 – Thời gian huấn luyện: lấy từ Mục 8.2.2 của bài báo (log không ghi thời gian train).

Kết quả ghi vào analysis/output/stack_*.csv
"""
import glob
import json
import os
import re

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from lqo_common import load_combined  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
WORKLOAD = os.path.join(ROOT, "lqo_ml_perspective/hybrid_qo/workload")
LOGS = os.path.join(ROOT, "lqo_ml_perspective/experiment_logs")
OUT = os.path.join(ROOT, "analysis/output")

METHODS = ["PostgreSQL", "HybridQO", "Bao", "Balsa", "Neo", "LEON"]
# Mục 8.2.2 của bài báo (giờ)
TRAIN_HOURS = {
    "JOB": {"PostgreSQL": "0", "Bao": "~2", "HybridQO": "~20", "Neo": "20–40", "Balsa": "40–85", "LEON": "110–130"},
    "STACK": {"PostgreSQL": "0", "Bao": "~2", "HybridQO": "12–14", "Neo": "120–140", "Balsa": "170–290",
              "LEON": "120–140"},
}


# ---------- Phần 1: workload ----------

def load_queries(bench):
    qs = {}
    for f in glob.glob(os.path.join(WORKLOAD, f"{bench}__*.json")):
        for sql, ident, *_ in json.load(open(f)):
            qs[ident] = sql
    return qs


def query_features(sql):
    s = re.sub(r"\s+", " ", sql.lower())
    from_part = re.search(r"\bfrom (.*?) where ", s).group(1)
    tables = [t.strip().split()[0] for t in from_part.split(",")]
    where = s.split(" where ", 1)[1]
    conds = [c.strip(" ();") for c in re.split(r"\band\b", where) if c.strip(" ();")]
    joins = [c for c in conds if re.fullmatch(r"[a-z0-9_]+\.[a-z_]+ ?= ?[a-z0-9_]+\.[a-z_]+", c)]
    filters = [c for c in conds if c not in joins]
    in_lists = re.findall(r"\bin \(([^)]*)\)", where)
    return {
        "số_bảng": len(tables),
        "số_join": len(joins),
        "join_qua_site_id": sum("site_id" in j for j in joins),
        "số_lọc": len(filters),
        "lọc_IN": len(in_lists),
        "phần_tử_IN_tb": np.mean([len(x.split(",")) for x in in_lists]) if in_lists else 0,
        "lọc_khoảng": sum(bool(re.search(r"[<>]=?", f)) for f in filters),
        "lọc_LIKE": sum(" like " in f for f in filters),
        "lọc_NOT/OR": sum(bool(re.search(r"\b(not|or)\b", f)) for f in filters),
        "aggregate": re.match(r"select (\w+)\(", s).group(1).upper() if re.match(r"select (\w+)\(", s) else "",
    }


def template(bench, ident):
    if bench == "STACK":
        return ident.split("__")[0]
    return re.match(r"\d+", ident).group()


def workload_summary():
    rows, per_query = [], []
    for bench in ["JOB", "STACK"]:
        qs = load_queries(bench)
        f = pd.DataFrame([{"benchmark": bench, "query_ident": k, "template": template(bench, k), **query_features(v)}
                          for k, v in qs.items()])
        per_query.append(f)
        rows.append({
            "benchmark": bench, "số_truy_vấn": len(f), "số_template": f.template.nunique(),
            "bảng_tb": f["số_bảng"].mean(), "bảng_min": f["số_bảng"].min(), "bảng_max": f["số_bảng"].max(),
            "join_tb": f["số_join"].mean(), "join_max": f["số_join"].max(),
            "tỉ_lệ_join_qua_site_id": f["join_qua_site_id"].sum() / f["số_join"].sum(),
            "lọc_tb": f["số_lọc"].mean(), "lọc_IN_tb": f["lọc_IN"].mean(),
            "phần_tử_IN_tb": f.loc[f["lọc_IN"] > 0, "phần_tử_IN_tb"].mean(),
            "lọc_khoảng_tb": f["lọc_khoảng"].mean(), "lọc_LIKE_tb": f["lọc_LIKE"].mean(),
            "lọc_NOT/OR_tb": f["lọc_NOT/OR"].mean(),
        })
    per_query = pd.concat(per_query)
    tables = per_query[per_query.benchmark == "STACK"].groupby("template").agg(
        số_bảng=("số_bảng", "first"), số_join=("số_join", "first"), lọc_tb=("số_lọc", "mean"))
    return pd.DataFrame(rows), per_query, tables


# ---------- Phần 2: thời gian chạy ----------

def load_log(path):
    """Tập test của mọi split: lần chạy cuối của LQO, trung vị các lần sau lần đầu của PostgreSQL (như C1)."""
    exps = sorted(e for e in pd.read_csv(path).experiment.dropna().unique() if "split" in e)
    pg = load_combined(path, "PostgreSQL").set_index("query_id")
    parts = []
    for m in METHODS[1:]:
        for e in exps:
            g = load_combined(path, m, experiment=e)
            g["pg_total"] = g.query_id.map(pg.total_ms)
            parts.append(g.assign(method=m, experiment=e))
            if m == "HybridQO":  # PostgreSQL trên đúng tập test của split này
                q = pg.loc[g.query_id].reset_index()
                parts.append(q.assign(method="PostgreSQL", experiment=e, pg_total=q.total_ms))
    d = pd.concat(parts, ignore_index=True)
    d["kiểu_split"] = d.experiment.str.replace(r"_split_\d", "", regex=True)
    return d


def runtime_summary(d, bench):
    rows = []
    for (m, kind), g in d.groupby(["method", "kiểu_split"]):
        rows.append(_row(bench, m, kind, g))
    for m, g in d.groupby("method"):
        rows.append(_row(bench, m, "tất cả", g))
    r = pd.DataFrame(rows)
    r["method"] = pd.Categorical(r.method, METHODS)
    return r.sort_values(["kiểu_split", "method"])


def _row(bench, m, kind, g):
    tot = g.total_ms.sum()
    return {
        "benchmark": bench, "method": m, "kiểu_split": kind, "số_câu": len(g),
        "suy_luận_s": g.inference_ms.sum() / 1000, "lập_kế_hoạch_s": g.planning_ms.sum() / 1000,
        "thực_thi_s": g.execution_ms.sum() / 1000, "end_to_end_s": tot / 1000,
        "suy_luận_%": 100 * g.inference_ms.sum() / tot,
        "suy_luận_tb_ms": g.inference_ms.mean(), "thực_thi_trung_vị_ms": g.execution_ms.median(),
        "timeout": int(g.timeout.sum()),
        "speedup": g.pg_total.sum() / tot,
        "thắng": int((g.pg_total / g.total_ms > 1.1).sum()), "thua": int((g.pg_total / g.total_ms < 0.9).sum()),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)

    wl, per_query, tables = workload_summary()
    wl.to_csv(os.path.join(OUT, "stack_workload_vs_job.csv"), index=False)
    per_query.to_csv(os.path.join(OUT, "stack_workload_per_query.csv"), index=False)
    print("== Phần 1: Workload ==")
    print(wl.round(2).T.to_string(header=False))
    print("\nSTACK theo template:")
    print(tables.round(1).T.to_string())

    print("\n== Phần 2: Thời gian chạy trên tập test (giây, lần chạy cuối) ==")
    res = []
    for bench, f in [("STACK", "20240103__STACK__combined.csv"), ("JOB", "20240103__combined.csv")]:
        res.append(runtime_summary(load_log(os.path.join(LOGS, f)), bench))
    res = pd.concat(res)
    res["huấn_luyện_giờ"] = [TRAIN_HOURS[b][m] for b, m in zip(res.benchmark, res.method)]
    res.to_csv(os.path.join(OUT, "stack_runtime_by_method.csv"), index=False)
    cols = ["method", "số_câu", "suy_luận_s", "lập_kế_hoạch_s", "thực_thi_s", "end_to_end_s", "suy_luận_%",
            "timeout", "thắng", "thua", "speedup", "huấn_luyện_giờ"]
    for bench in ["STACK", "JOB"]:
        for kind in ["tất cả", "leave_one_out", "random", "base_query"]:
            t = res[(res.benchmark == bench) & (res.kiểu_split == kind)]
            print(f"\n-- {bench} / {kind}")
            print(t[cols].round(2).to_string(index=False))
    print(f"\nĐã ghi: {OUT}/stack_workload_vs_job.csv, stack_workload_per_query.csv, stack_runtime_by_method.csv")


if __name__ == "__main__":
    main()
