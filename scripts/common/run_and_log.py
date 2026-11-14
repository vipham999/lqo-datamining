"""Chạy mỗi truy vấn với nhiều hint set, mỗi hint set N lần, ghi JSONL kèm plan JSON (Phần B).

Ví dụ (trong container bao_server):
  python3 /app/scripts/common/run_and_log.py --query_dir /app/bao/queries/join-order-benchmark \
      --out /app/logs/job_hintsets.jsonl

  # Ablation 8.4: tắt bitmap/tid scan, chỉ chạy plan mặc định
  python3 /app/scripts/common/run_and_log.py --query_dir /app/bao/queries/join-order-benchmark \
      --hint_sets default --extra_set "SET enable_bitmapscan = off; SET enable_tidscan = off" \
      --tag no_bitmap_tidscan --out /app/logs/job_ablation.jsonl

  # Ablation 8.6: chạy mỗi câu 10 lần liên tiếp
  python3 /app/scripts/common/run_and_log.py --query_dir ... --hint_sets default --runs 10 \
      --tag k_runs --out /app/logs/job_k_runs.jsonl
"""
import argparse
import glob
import json
import os
import time

import psycopg2

# Hint set kiểu Bao: bật/tắt toán tử bằng GUC của PostgreSQL. "default" = plan cũ (PostgreSQL tự chọn).
HINT_SETS = {
    "default": [],
    "no_nestloop": ["SET enable_nestloop = off"],
    "no_hashjoin": ["SET enable_hashjoin = off"],
    "no_mergejoin": ["SET enable_mergejoin = off"],
    "no_seqscan": ["SET enable_seqscan = off"],
    "no_indexscan": ["SET enable_indexscan = off", "SET enable_indexonlyscan = off"],
}


def connect(args):
    conn = psycopg2.connect(dbname=args.db, user="postgres", password="postgres",
                            host=args.host, port=args.port)
    conn.autocommit = True
    return conn


def run_query(args, sql, setup):
    out = []
    conn = connect(args)
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {args.timeout_ms}")
    for s in setup:
        cur.execute(s)
    for i in range(args.runs):
        try:
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON) {sql}")
            r = cur.fetchone()[0][0]
            out.append({"run": i, "planning_ms": r["Planning Time"], "execution_ms": r["Execution Time"],
                        "timeout": False, "plan": r["Plan"]})
        except psycopg2.errors.QueryCanceled:
            # Đã timeout một lần thì các lần sau gần như chắc chắn cũng timeout: ghi timeout cho mọi lần
            # còn lại và dừng, giống run_test_queries.py của tác giả (một lần >180 s → cả 3 lần là timeout).
            # Tiết kiệm tới 2 × timeout_ms cho mỗi cặp (câu, hint set) bị timeout.
            out += [{"run": j, "planning_ms": None, "execution_ms": float(args.timeout_ms),
                     "timeout": True, "plan": None, "skipped": j > i} for j in range(i, args.runs)]
            break
    conn.close()
    return out


def list_queries(args):
    files = sorted(glob.glob(os.path.join(args.query_dir, "**/*.sql"), recursive=True))
    if args.only:
        keep = {q.strip() for q in open(args.only) if q.strip()}
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in keep]
    return files


def already_done(path):
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["query_id"], r["hint_set"], r.get("tag", "")))
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--query_dir", required=True)
    p.add_argument("--only", help="file chứa danh sách query_id cần chạy (mỗi dòng một tên, vd 1a)")
    p.add_argument("--benchmark", default="JOB")
    p.add_argument("--db", default="imdbload")
    p.add_argument("--host", default="pg_bao")
    p.add_argument("--port", type=int, default=5432)
    p.add_argument("--runs", type=int, default=3, help="số lần chạy mỗi câu; phân tích dùng lần thứ 3 (run=2)")
    p.add_argument("--timeout_ms", type=int, default=180_000, help="giống repo gốc: 3 phút")
    p.add_argument("--hint_sets", default=",".join(HINT_SETS))
    p.add_argument("--extra_set", default="", help="lệnh SET thêm cho mọi hint set, ngăn cách bằng ';'")
    p.add_argument("--tag", default="", help="nhãn thí nghiệm, vd no_geqo, imdb50")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    extra = [s.strip() for s in args.extra_set.split(";") if s.strip()]
    hint_sets = [h.strip() for h in args.hint_sets.split(",") if h.strip()]
    files = list_queries(args)
    done = already_done(args.out)
    print(f"{len(files)} truy vấn × {len(hint_sets)} hint set × {args.runs} lần chạy → {args.out}")

    with open(args.out, "a") as f:
        for fp in files:
            qid = os.path.splitext(os.path.basename(fp))[0]
            sql = open(fp).read().strip().rstrip(";")
            for hs in hint_sets:
                if (qid, hs, args.tag) in done:
                    continue
                t0 = time.time()
                for m in run_query(args, sql, extra + HINT_SETS[hs]):
                    f.write(json.dumps({"query_id": qid, "benchmark": args.benchmark, "db": args.db,
                                        "hint_set": hs, "tag": args.tag, "extra_set": args.extra_set,
                                        "pg_version": "12.5", "ts": time.time(), **m}) + "\n")
                f.flush()
                print(f"{qid:>6} {hs:<14} {time.time() - t0:7.1f}s")


if __name__ == "__main__":
    main()
