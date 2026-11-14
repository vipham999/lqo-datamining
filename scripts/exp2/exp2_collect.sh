#!/bin/bash
# Thí nghiệm 2 – thu thập dữ liệu: 113 câu JOB × 6 phương án × 3 lần (lấy lần thứ 3), cùng cấu hình PostgreSQL
# đã dùng cho Bao. KHÔNG chạy việc gì khác trên pg_bao trong lúc này.
#   nohup caffeinate -dis bash scripts/exp2/exp2_collect.sh > logs/mac/exp2/exp2_collect.log 2>&1 &
R=$(cd "$(dirname "$0")/../.." && pwd)
Q=/app/bao/queries/join-order-benchmark
echo "== $(date '+%F %T') Làm nóng imdbload"
docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh imdbload
echo "== $(date '+%F %T') EXPLAIN plan mặc định (đặc trưng + thời gian EXPLAIN)"
docker exec bao_server python3 -u /app/scripts/exp2/exp2_explain.py --query_dir $Q --out /app/logs/mac/exp2/exp2_explain_job.jsonl
echo "== $(date '+%F %T') Chạy 6 phương án"
docker exec bao_server python3 -u /app/scripts/common/run_and_log.py --query_dir $Q --out /app/logs/mac/exp2/exp2_hintsets_job.jsonl
echo "== $(date '+%F %T') Xong"
