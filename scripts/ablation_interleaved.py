"""Ablation 8.4 (tắt bitmap + tid scan) và 8.5 (tắt GEQO), đo XEN KẼ để loại bỏ trôi môi trường.

Với mỗi câu JOB, chạy liền nhau cả 3 cấu hình (thứ tự xoay vòng theo câu để không cấu hình nào luôn chạy trước):
  default            : cấu hình mặc định (GEQO bật, bitmap/tid scan bật)
  no_geqo            : SET geqo TO off
  no_bitmap_tidscan  : SET enable_bitmapscan TO off; SET enable_tidscan TO off
Mỗi cấu hình: kết nối mới, SET theo phiên (không đổi cấu hình CSDL), EXPLAIN ANALYZE 3 lần, timeout 180 s,
giống run_test_queries.py của tác giả. Ghi ra 3 file txt cùng định dạng log của tác giả để dùng lại c1_win_loss.py.

Chạy TRONG container bao_server:
  python3 /app/scripts/ablation_interleaved.py --tag interleaved_YYYYMMDD
"""
import argparse
import datetime
import glob
import os
import sys

import psycopg2

TIMEOUT_MS = 3 * 60 * 1000
RUNS = 3
CONFIGS = {
    'default': [],
    'no_geqo': ["SET geqo TO off"],
    'no_bitmap_tidscan': ["SET enable_bitmapscan TO off", "SET enable_tidscan TO off"],
}
DSN = "dbname={db} user=postgres password=postgres host=pg_bao"


def other_connections(db):
    conn = psycopg2.connect(DSN.format(db=db))
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM pg_stat_activity "
                "WHERE backend_type = 'client backend' AND pid <> pg_backend_pid()")
    n = cur.fetchone()[0]
    conn.close()
    return n


def run(sql, db, sets):
    out = []
    conn = psycopg2.connect(DSN.format(db=db))
    try:
        cur = conn.cursor()
        cur.execute(f"SET statement_timeout TO {TIMEOUT_MS}")
        cur.execute("SET enable_bao TO off")
        for s in sets:
            cur.execute(s)
        for _ in range(RUNS):
            cur.execute(f"EXPLAIN (ANALYZE, VERBOSE, FORMAT JSON) {sql}")
            r = cur.fetchall()[0][0][-1]
            out.append((r['Planning Time'], r['Execution Time']))
    except Exception as e:  # timeout: ghi như tác giả (2 × timeout)
        print("  timeout/lỗi:", str(e).splitlines()[0], flush=True)
        out = [(2 * TIMEOUT_MS, 2 * TIMEOUT_MS)] * RUNS
    finally:
        conn.close()
    return out


def main(a):
    n = other_connections(a.db)
    if n and not a.force:
        sys.exit(f"Đang có {n} kết nối khác vào {a.db}. Dừng chúng trước (hoặc --force).")
    paths = sorted(glob.glob(os.path.join(a.query_dir, '*.sql')))
    print(f"{len(paths)} câu, cấu hình: {list(CONFIGS)}", flush=True)
    files = {c: open(os.path.join(a.out_dir, f"test__postgres__job__{c}__{a.tag}.txt"), 'w') for c in CONFIGS}
    names = list(CONFIGS)
    for qi, p in enumerate(paths):
        sql = open(p).read()
        rel = os.path.relpath(p, '/app/bao')
        k = (qi + a.offset) % 3
        order = names[k:] + names[:k]
        line = []
        for c in order:
            ms = run(sql, a.db, CONFIGS[c])
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            for i, (pt, et) in enumerate(ms):
                files[c].write(f"x, {i}, {ts}, {rel}, {pt}, {et}, PG\n")
            files[c].flush()
            line.append(f"{c}={ms[-1][0] + ms[-1][1]:.0f}ms")
        print(f"[{qi + 1}/{len(paths)}] {os.path.basename(p)}  " + "  ".join(line), flush=True)
    for f in files.values():
        f.close()
    print("Xong:", [f.name for f in files.values()])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='imdbload')
    ap.add_argument('--query_dir', default='/app/bao/queries/join-order-benchmark')
    ap.add_argument('--out_dir', default='/app/logs')
    ap.add_argument('--tag', required=True)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--offset', type=int, default=0, help='dịch thứ tự xoay vòng (đổi giữa các lượt lặp)')
    main(ap.parse_args())
