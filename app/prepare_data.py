"""Chụp thông tin CSDL IMDB cho tab "0. Dữ liệu IMDB & JOB" (chạy MỘT lần, cần container pg_bao đang chạy).

    ~/.venvs/lqo_app/bin/python app/prepare_data.py

Tạo analysis/output/app/imdb_db.json: bảng, cột, số dòng, dung lượng, dòng mẫu, quan hệ nối giữa các bảng,
ví dụ một bộ phim. Sau đó dashboard chỉ đọc file, không cần Docker.
"""
import glob
import json
import os
import re

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERY_DIR = os.path.join(ROOT, "lqo_ml_perspective/bao/queries/join-order-benchmark")
OUT = os.path.join(ROOT, "analysis/output/app")

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


def main():
    os.makedirs(OUT, exist_ok=True)
    json.dump(fetch_db(), open(os.path.join(OUT, "imdb_db.json"), "w"), default=str, ensure_ascii=False)
    print(f"Đã chụp CSDL → {OUT}/imdb_db.json")


if __name__ == "__main__":
    main()
