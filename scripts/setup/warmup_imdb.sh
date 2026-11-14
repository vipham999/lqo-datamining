#!/bin/bash
# Làm nóng cache trước khi đo (bài báo đo ở trạng thái cache nóng).
# Chạy TRONG container pg_bao:  docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh
# 1) pg_prewarm đọc toàn bộ bảng + index của IMDB vào cache của hệ điều hành
# 2) chạy mỗi câu JOB một lần, không ghi kết quả, không giới hạn thời gian
# Không làm bước này thì lần chạy đầu của câu nặng (vd 25c) có thể vượt timeout 180 s,
# và run_test_queries.py sẽ ghi cả 3 lần của câu đó là timeout.
set -e
DB=${1:-imdbload}
QDIR=/app/lqo/bao/queries/join-order-benchmark

echo "== pg_prewarm $DB"
psql -U postgres -d "$DB" -qAt -c "CREATE EXTENSION IF NOT EXISTS pg_prewarm;"
psql -U postgres -d "$DB" -qAt -c "
  SELECT pg_size_pretty(sum(pg_prewarm(c.oid, 'read') * 8192))
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relkind IN ('r', 'i');"

echo "== Chạy mỗi câu JOB một lần"
T0=$(date +%s)
for f in "$QDIR"/*.sql; do
  S=$(date +%s)
  psql -U postgres -d "$DB" -qAt -o /dev/null -c "SET statement_timeout = 0;" -f "$f"
  echo "$(basename "$f" .sql): $(( $(date +%s) - S )) s"
done
echo "== Xong làm nóng sau $(( $(date +%s) - T0 )) s"
