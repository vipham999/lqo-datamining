"""Ablation 8.7 – Bushy và left-deep: duyệt mọi thứ tự join (không tích Descartes) của các truy vấn
có ≤ 5 join, ép từng cây bằng pg_hint_plan Leading(...), đo thời gian, rồi kiểm định Mann-Whitney U.

Chạy (trong bao_server):
  python3 /app/scripts/join_orders.py run --query_dir /app/bao/queries/join-order-benchmark \
      --max_tables 6 --max_plans 300 --timeout_ms 30000 --out /app/logs/job_join_orders.jsonl
Phân tích (trên Mac):
  python scripts/join_orders.py analyze --log logs/job_join_orders.jsonl

Bài báo dùng cardinality ước lượng của PostgreSQL và cho phép mọi kiểu join → ở đây chỉ ép THỨ TỰ/HÌNH DẠNG cây,
để PostgreSQL tự chọn thuật toán join.
"""
import argparse
import glob
import itertools
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))


# ---------------------------------------------------------------- phân tích SQL
def join_graph(sql):
    low = re.sub(r"\s+", " ", sql)
    m = re.search(r"\bFROM\b(.*?)\bWHERE\b", low, re.I)
    aliases = []
    for part in (m.group(1) if m else "").split(","):
        toks = part.strip().split()
        if toks:
            aliases.append(toks[-1])
    where = re.split(r"\bWHERE\b", low, flags=re.I)[-1]
    edges = set()
    for a, b in re.findall(r"\b(\w+)\.\w+\s*=\s*(\w+)\.\w+\b", where):
        if a != b and a in aliases and b in aliases:
            edges.add(frozenset((a, b)))
    return aliases, edges


def connected(S, edges):
    S = set(S)
    seen, stack = set(), [next(iter(S))]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack += [y for e in edges if x in e for y in e if y in S and y not in seen]
    return seen == S


def trees(S, edges, memo):
    """Mọi cây join (không thứ tự trái/phải) trên tập quan hệ S, không có tích Descartes."""
    S = frozenset(S)
    if S in memo:
        return memo[S]
    if len(S) == 1:
        return [next(iter(S))]
    out = []
    first = min(S)
    rest = sorted(S - {first})
    for r in range(0, len(rest)):
        for comb in itertools.combinations(rest, r):
            L = frozenset((first,) + comb)
            R = S - L
            if not R or not connected(L, edges) or not connected(R, edges):
                continue
            if not any(len(e & L) == 1 and len(e & R) == 1 for e in edges):
                continue
            for lt in trees(L, edges, memo):
                for rt in trees(R, edges, memo):
                    out.append((lt, rt))
    memo[S] = out
    return out


def to_leading(t):
    return t if isinstance(t, str) else f"({to_leading(t[0])} {to_leading(t[1])})"


def is_left_deep(t):
    """Left-deep (hoặc right-deep): mọi nút join đều có ít nhất một con là bảng."""
    if isinstance(t, str):
        return True
    a, b = t
    return (isinstance(a, str) or isinstance(b, str)) and is_left_deep(a) and is_left_deep(b)


# ---------------------------------------------------------------- chạy
def cmd_run(a):
    import psycopg2
    files = sorted(glob.glob(os.path.join(a.query_dir, "**/*.sql"), recursive=True))
    rnd = random.Random(42)
    with open(a.out, "a") as f:
        for fp in files:
            qid = os.path.splitext(os.path.basename(fp))[0]
            sql = open(fp).read().strip().rstrip(";")
            aliases, edges = join_graph(sql)
            if not 2 <= len(aliases) <= a.max_tables or not connected(aliases, edges):
                continue
            all_trees = trees(aliases, edges, {})
            sample = all_trees if len(all_trees) <= a.max_plans else rnd.sample(all_trees, a.max_plans)
            n_ld = sum(is_left_deep(t) for t in all_trees)
            print(f"{qid}: {len(aliases)} bảng, {len(all_trees)} cây ({n_ld} left-deep), chạy {len(sample)}")
            conn = psycopg2.connect(dbname=a.db, user="postgres", password="postgres", host=a.host, port=a.port)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("LOAD 'pg_hint_plan'")
            cur.execute("SET geqo = off")
            cur.execute(f"SET statement_timeout = {a.timeout_ms}")
            for t in sample:
                hint = f"/*+ Leading({to_leading(t)}) */"
                rec = {"query_id": qid, "n_tables": len(aliases), "tree": to_leading(t),
                       "shape": "left_deep" if is_left_deep(t) else "bushy", "n_trees_total": len(all_trees)}
                for i in range(a.runs):
                    try:
                        cur.execute(f"{hint} EXPLAIN (ANALYZE, FORMAT JSON) {sql}")
                        r = cur.fetchone()[0][0]
                        rec.update(run=i, planning_ms=r["Planning Time"], execution_ms=r["Execution Time"],
                                   timeout=False)
                    except psycopg2.errors.QueryCanceled:
                        rec.update(run=i, planning_ms=None, execution_ms=float(a.timeout_ms), timeout=True)
                    rec["ts"] = time.time()
                    f.write(json.dumps(rec) + "\n")
                f.flush()
            conn.close()


# ---------------------------------------------------------------- phân tích
def cmd_analyze(a):
    import pandas as pd
    from scipy.stats import mannwhitneyu
    df = pd.read_json(a.log, lines=True)
    df = df[df.run == df.run.max()].copy()
    # Chuẩn hóa theo từng truy vấn để gộp được nhiều truy vấn (thời gian / plan nhanh nhất của truy vấn đó)
    df["norm"] = df.execution_ms / df.groupby("query_id").execution_ms.transform("min")
    bushy, ld = df[df["shape"] == "bushy"].norm, df[df["shape"] == "left_deep"].norm
    print(f"{df.query_id.nunique()} truy vấn, {len(bushy)} plan bushy, {len(ld)} plan left-deep")
    print(f"Trung bình (chuẩn hóa): bushy {bushy.mean():.3f}, left-deep {ld.mean():.3f}")
    p_two = mannwhitneyu(bushy, ld, alternative="two-sided").pvalue
    print(f"Mann-Whitney U hai phía (toàn bộ):            p = {p_two:.4f}")
    cut = df.norm.quantile(a.tail)
    tb, tl = bushy[bushy <= cut], ld[ld <= cut]
    if len(tb) and len(tl):
        p_tail = mannwhitneyu(tb, tl, alternative="less").pvalue
        print(f"Mann-Whitney U một phía (nhóm {a.tail:.0%} plan nhanh nhất, bushy < left-deep): p = {p_tail:.4f}")
    best = df.loc[df.groupby("query_id").execution_ms.idxmin()]
    print("\nHình dạng của plan nhanh nhất mỗi truy vấn:")
    print(best["shape"].value_counts().to_string())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--query_dir", required=True)
    r.add_argument("--db", default="imdbload")
    r.add_argument("--host", default="pg_bao")
    r.add_argument("--port", type=int, default=5432)
    r.add_argument("--max_tables", type=int, default=6, help="≤ 6 bảng = ≤ 5 join như bài báo")
    r.add_argument("--max_plans", type=int, default=300, help="lấy mẫu tối đa số cây mỗi truy vấn")
    r.add_argument("--runs", type=int, default=1)
    r.add_argument("--timeout_ms", type=int, default=30_000)
    r.add_argument("--out", required=True)
    an = sub.add_parser("analyze")
    an.add_argument("--log", required=True)
    an.add_argument("--tail", type=float, default=0.1)
    a = p.parse_args()
    cmd_run(a) if a.cmd == "run" else cmd_analyze(a)


if __name__ == "__main__":
    main()
