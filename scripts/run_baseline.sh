#!/bin/bash
# Baseline PostgreSQL: 113 truy vấn JOB, mỗi câu 3 lần (Mục 6.2 README).
# Chạy TRONG container bao_server:  docker exec -it bao_server bash /app/scripts/run_baseline.sh
set -e
DB=${1:-imdbload}
TAG=${2:-}
OUT=/app/logs/test__postgres__job${TAG:+__$TAG}__$(date +%Y%m%d_%H%M).txt
EXTRA=()
[ "$TAG" = "no_geqo" ] && EXTRA=(--disable_geqo)
cd /app/bao
python3 run_test_queries.py --use_postgres --database_name "$DB" "${EXTRA[@]}" \
  --query_dir queries/join-order-benchmark --output_file "$OUT"
echo "Log: $OUT"
