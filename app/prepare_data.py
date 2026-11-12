"""Chuẩn bị dữ liệu cho ứng dụng demo (chạy MỘT lần, cần container pg_bao đang chạy).

    analysis/.venv/bin/python app/prepare_data.py            # EXPLAIN (nhanh, không có q-error)
    analysis/.venv/bin/python app/prepare_data.py --analyze  # EXPLAIN ANALYZE (có q-error, ~30 phút)

    analysis/.venv/bin/python app/prepare_data.py --db       # chỉ chụp thông tin CSDL IMDB, vài giây

Tạo trong analysis/output/app/:
  imdb_db.json       : bảng, cột, số dòng, dung lượng, dòng mẫu, quan hệ nối giữa các bảng, ví dụ một bộ phim
  default_plans.json : plan mặc định của PostgreSQL cho từng câu JOB
  dataset_a.csv      : nguồn A – mỗi câu JOB một dòng: đặc trưng SQL + plan mặc định,
                       thời gian end-to-end của từng phương pháp trong log tác giả, nhãn "phương pháp nhanh nhất".
Sau đó ứng dụng chỉ đọc file, không cần Docker.
"""
import argparse
import glob
import json
import os
import re
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


TABLE_COLS = """SELECT c.relname, c.reltuples::bigint, pg_total_relation_size(c.oid),
       (SELECT json_agg(json_build_object('name', a.attname, 'type', format_type(a.atttypid, a.atttypmod))
                        ORDER BY a.attnum)
        FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY c.reltuples DESC"""

# Một bộ phim xuyên qua các bảng, để minh họa cách dữ liệu được nối với nhau
MOVIE_EXAMPLE = {
    "title": "SELECT id, title, kind_id, production_year FROM title WHERE id = %(m)s",
    "cast_info": """SELECT n.name, n.gender, rt.role, chn.name AS nhan_vat, ci.nr_order, ci.note
        FROM cast_info ci JOIN name n ON n.id = ci.person_id JOIN role_type rt ON rt.id = ci.role_id
        LEFT JOIN char_name chn ON chn.id = ci.person_role_id
        WHERE ci.movie_id = %(m)s AND (ci.nr_order <= 3 OR ci.role_id = 8) ORDER BY ci.role_id, ci.nr_order""",
    "movie_info": """SELECT it.info AS info_type, mi.info FROM movie_info mi JOIN info_type it ON it.id = mi.info_type_id
        WHERE mi.movie_id = %(m)s AND it.info IN ('genres', 'languages', 'runtimes', 'release dates') LIMIT 6""",
    "movie_info_idx": """SELECT it.info AS info_type, mi.info FROM movie_info_idx mi
        JOIN info_type it ON it.id = mi.info_type_id WHERE mi.movie_id = %(m)s""",
    "movie_keyword": """SELECT k.keyword FROM movie_keyword mk JOIN keyword k ON k.id = mk.keyword_id
        WHERE mk.movie_id = %(m)s LIMIT 6""",
    "movie_companies": """SELECT cn.name, cn.country_code, ct.kind, mc.note FROM movie_companies mc
        JOIN company_name cn ON cn.id = mc.company_id JOIN company_type ct ON ct.id = mc.company_type_id
        WHERE mc.movie_id = %(m)s LIMIT 4""",
}


def _rows(cur, sql, params=None, max_len=60):
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    cut = lambda v: v if not isinstance(v, str) or len(v) <= max_len else v[:max_len] + "…"
    return [dict(zip(cols, map(cut, r))) for r in cur.fetchall()]


def join_edges():
    """Các cặp (bảng, cột) = (bảng, cột) xuất hiện trong điều kiện nối của 113 câu JOB, kèm số câu dùng."""
    edges, usage = {}, {}
    for fp in glob.glob(os.path.join(QUERY_DIR, "*.sql")):
        sql = open(fp).read()
        frm = re.search(r"\bFROM\b(.*?)\bWHERE\b", sql, re.S).group(1)
        alias = {}
        for t in frm.split(","):
            parts = re.sub(r"\s+AS\s+", " ", t.strip()).split()
            alias[parts[-1]] = parts[0]
        for tbl in set(alias.values()):
            usage[tbl] = usage.get(tbl, 0) + 1
        seen = set()
        for a1, c1, a2, c2 in re.findall(r"(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", sql):
            e = tuple(sorted([(alias[a1], c1), (alias[a2], c2)]))
            if e[0][0] != e[1][0] and e not in seen:
                seen.add(e)
                edges[e] = edges.get(e, 0) + 1
    return ([{"t1": a[0], "c1": a[1], "t2": b[0], "c2": b[1], "so_cau": n} for (a, b), n in edges.items()],
            usage)


def fetch_db():
    """Ảnh chụp CSDL imdbload cho tab "CSDL IMDB": bảng, cột, số dòng, dung lượng, dòng mẫu, quan hệ nối."""
    conn = psycopg2.connect(dbname="imdbload", user="postgres", password="postgres", host="localhost", port=5432)
    cur = conn.cursor()
    cur.execute("SELECT version(), pg_database_size('imdbload')")
    version, db_bytes = cur.fetchone()
    cur.execute(TABLE_COLS)
    tables = [{"name": n, "rows": r, "bytes": b, "columns": cols} for n, r, b, cols in cur.fetchall()]
    for t in tables:
        t["sample"] = _rows(cur, f"SELECT * FROM {t['name']} LIMIT 5")
    cur.execute("SELECT id FROM title WHERE title = 'The Matrix' AND production_year = 1999 AND kind_id = 1")
    movie_id = cur.fetchone()[0]
    example = {k: _rows(cur, q, {"m": movie_id}) for k, q in MOVIE_EXAMPLE.items()}
    conn.close()
    edges, usage = join_edges()
    for t in tables:
        t["so_cau_job"] = usage.get(t["name"], 0)
    return {"version": version, "bytes": db_bytes, "tables": tables, "edges": edges, "example": example}


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
    ap.add_argument("--db", action="store_true", help="chỉ chụp thông tin CSDL IMDB (imdb_db.json), vài giây")
    ap.add_argument("--timeout_ms", type=int, default=60_000)
    ap.add_argument("--min_gain", type=float, default=0.05,
                    help="phương pháp khác chỉ được coi là tốt hơn PostgreSQL nếu nhanh hơn ít nhất 5%%")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    json.dump(fetch_db(), open(os.path.join(OUT, "imdb_db.json"), "w"), default=str, ensure_ascii=False)
    print(f"Đã chụp CSDL → {OUT}/imdb_db.json")
    if a.db:
        return

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
