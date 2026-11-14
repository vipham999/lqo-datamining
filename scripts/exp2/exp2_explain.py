"""Thí nghiệm 2 – bước lấy đặc trưng: chạy EXPLAIN (không ANALYZE) cho plan mặc định của mỗi câu.

Chỉ dùng thông tin có TRƯỚC khi chạy truy vấn (chi phí, số dòng ước lượng, loại toán tử), đồng thời đo
thời gian gọi EXPLAIN để cộng vào thời gian end-to-end của mô hình (Mục 3.2 báo cáo).
Mỗi câu gọi EXPLAIN 3 lần trên cùng kết nối, lấy lần thứ 3.

  python3 /app/scripts/exp2/exp2_explain.py --query_dir /app/bao/queries/join-order-benchmark \
      --out /app/logs/exp2_explain_job.jsonl
"""
import argparse
import glob
import json
import os
import time

import psycopg2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query_dir", required=True)
    p.add_argument("--db", default="imdbload")
    p.add_argument("--host", default="pg_bao")
    p.add_argument("--benchmark", default="JOB")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    files = sorted(glob.glob(os.path.join(a.query_dir, "**/*.sql"), recursive=True))
    with open(a.out, "w") as f:
        for fp in files:
            qid = os.path.splitext(os.path.basename(fp))[0]
            sql = open(fp).read().strip().rstrip(";")
            conn = psycopg2.connect(dbname=a.db, user="postgres", password="postgres", host=a.host)
            conn.autocommit = True
            cur = conn.cursor()
            for i in range(a.runs):
                t0 = time.perf_counter()
                cur.execute(f"EXPLAIN (FORMAT JSON) {sql}")
                plan = cur.fetchone()[0][0]["Plan"]
                ms = (time.perf_counter() - t0) * 1000
            conn.close()
            f.write(json.dumps({"query_id": qid, "benchmark": a.benchmark, "explain_ms": ms,
                                "plan": plan}) + "\n")
    print(f"{len(files)} câu → {a.out}")


if __name__ == "__main__":
    main()
