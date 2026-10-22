"""Trích đặc trưng từ plan JSON và câu SQL (Phần C, bước 8.1).

  python scripts/extract_features.py --log logs/job_hintsets.jsonl \
      --query_dir lqo_ml_perspective/bao/queries/join-order-benchmark --out analysis/output/features.csv

Mỗi dòng của features.csv là một (query_id, hint_set, tag) với cột:
  sql_*   : đặc trưng của câu truy vấn (không phụ thuộc plan)
  plan_*  : đặc trưng của cây plan (số node, độ sâu, loại join/scan, cost, q-error, bushy/left-deep)
"""
import argparse
import glob
import math
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from lqo_common import norm_qid, read_plans, template_of  # noqa: E402

JOIN_TYPES = {"Hash Join": "hashjoin", "Merge Join": "mergejoin", "Nested Loop": "nestloop"}
SCAN_TYPES = {"Seq Scan": "seqscan", "Index Scan": "indexscan", "Index Only Scan": "indexonlyscan",
              "Bitmap Heap Scan": "bitmapheapscan", "Bitmap Index Scan": "bitmapindexscan"}
OTHER_TYPES = {"Hash": "hash", "Sort": "sort", "Materialize": "materialize", "Aggregate": "aggregate",
               "Gather": "gather", "Gather Merge": "gathermerge", "Memoize": "memoize"}


# ---------------------------------------------------------------- SQL
def sql_features(sql):
    s = re.sub(r"\s+", " ", sql)
    low = s.lower()
    m = re.search(r"\bfrom\b(.*?)\bwhere\b", low)
    from_part = m.group(1) if m else ""
    where = low.split(" where ", 1)[1] if " where " in low else ""
    tables = [t for t in from_part.split(",") if t.strip()]
    join_preds = re.findall(r"\b\w+\.\w+\s*=\s*\w+\.\w+\b", where)
    n_preds = len(re.findall(r"\band\b", where)) + (1 if where else 0)
    return {
        "sql_n_tables": len(tables),
        "sql_n_join_preds": len(join_preds),
        "sql_n_filter_preds": max(n_preds - len(join_preds), 0),
        "sql_n_like": len(re.findall(r"\blike\b", where)),
        "sql_n_not_like": len(re.findall(r"\bnot like\b", where)),
        "sql_n_in": len(re.findall(r"\bin\s*\(", where)),
        "sql_n_between": len(re.findall(r"\bbetween\b", where)),
        "sql_n_or": len(re.findall(r"\bor\b", where)),
        "sql_n_is_null": len(re.findall(r"\bis (not )?null\b", where)),
        "sql_n_range": len(re.findall(r"[<>]=?", where)),
        "sql_len": len(s),
    }


# ---------------------------------------------------------------- PLAN
def _children(node):
    return node.get("Plans", [])


def _is_join(node):
    return node["Node Type"] in JOIN_TYPES


def _join_below(node):
    """Join gần nhất bên dưới (bỏ qua Hash/Sort/Materialize...), hoặc None nếu là nhánh scan."""
    while not _is_join(node):
        ch = [c for c in _children(node) if c.get("Parent Relationship") != "SubPlan"]
        if len(ch) != 1:
            return None
        node = ch[0]
    return node


def plan_features(plan):
    f = {f"plan_n_{v}": 0 for v in list(JOIN_TYPES.values()) + list(SCAN_TYPES.values()) + list(OTHER_TYPES.values())}
    stats = {"nodes": 0, "depth": 0, "max_qerr": 1.0, "sum_log_qerr": 0.0, "bushy_joins": 0, "joins": 0}

    def visit(node, d):
        stats["nodes"] += 1
        stats["depth"] = max(stats["depth"], d)
        t = node["Node Type"]
        key = JOIN_TYPES.get(t) or SCAN_TYPES.get(t) or OTHER_TYPES.get(t)
        if key:
            f[f"plan_n_{key}"] += 1
        if "Actual Rows" in node and node.get("Actual Loops", 0) > 0:
            est, act = max(node["Plan Rows"], 1), max(node["Actual Rows"], 1)
            q = max(est / act, act / est)
            stats["max_qerr"] = max(stats["max_qerr"], q)
            stats["sum_log_qerr"] += math.log10(q)
        if _is_join(node):
            stats["joins"] += 1
            sub = [_join_below(c) for c in _children(node)]
            if sum(s is not None for s in sub) >= 2:
                stats["bushy_joins"] += 1
        for c in _children(node):
            visit(c, d + 1)

    visit(plan, 1)
    f.update({
        "plan_nodes": stats["nodes"],
        "plan_depth": stats["depth"],
        "plan_n_joins": stats["joins"],
        "plan_bushy_joins": stats["bushy_joins"],
        "plan_is_bushy": int(stats["bushy_joins"] > 0),
        "plan_total_cost": plan.get("Total Cost", 0.0),
        "plan_startup_cost": plan.get("Startup Cost", 0.0),
        "plan_est_rows": plan.get("Plan Rows", 0),
        "plan_max_qerror": stats["max_qerr"],
        "plan_mean_log_qerror": stats["sum_log_qerr"] / max(stats["nodes"], 1),
    })
    return f


def plan_signature(plan):
    """Chuỗi ngắn mô tả plan: loại node theo thứ tự duyệt trước (dùng để đếm số plan khác nhau)."""
    out = []

    def visit(n):
        rel = n.get("Alias", "")
        out.append(n["Node Type"].replace(" ", "") + (f"[{rel}]" if rel else ""))
        for c in _children(n):
            visit(c)
    visit(plan)
    return "/".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True, help="JSONL từ run_and_log.py")
    p.add_argument("--query_dir", required=True)
    p.add_argument("--run", type=int, default=2, help="lần chạy dùng để phân tích (2 = lần thứ 3)")
    p.add_argument("--out", required=True)
    a = p.parse_args()

    sqls = {norm_qid(fp): open(fp).read()
            for fp in glob.glob(os.path.join(a.query_dir, "**/*.sql"), recursive=True)}
    rows = []
    for (qid, hs, tag), plan in read_plans(a.log, run=a.run).items():
        r = {"query_id": qid, "template": template_of(qid), "hint_set": hs, "tag": tag,
             "plan_signature": plan_signature(plan)}
        r.update(sql_features(sqls.get(qid, "")))
        r.update(plan_features(plan))
        rows.append(r)
    df = pd.DataFrame(rows).sort_values(["query_id", "hint_set"])
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} dòng, {df.query_id.nunique()} truy vấn → {a.out}")


if __name__ == "__main__":
    main()
