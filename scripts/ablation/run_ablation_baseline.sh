#!/bin/bash
# Ablation 8.5 (tắt GEQO) và 8.4 (tắt bitmap + tid scan) trên baseline PostgreSQL, JOB 113 câu × 3 lần.
# Dùng cùng công cụ đo (run_test_queries.py) và cùng điều kiện cache nóng với baseline của run_fair_comparison.sh,
# để so sánh trực tiếp với log test__postgres__job__fair_*.txt.
# Chạy trên Mac, sau khi `docker compose up -d` trong infra/:
#   caffeinate -dis bash scripts/ablation/run_ablation_baseline.sh [file_baseline_txt]
set -e
cd "$(dirname "$0")/../.."
DB=imdbload
BASE=${1:-$(ls logs/test__postgres__job__fair_*.txt | tail -1)}
echo "== Baseline dùng để so sánh: $BASE"

# Đảm bảo luôn trả CSDL về cấu hình mặc định, kể cả khi script bị dừng giữa chừng
reset_db() {
  docker exec pg_bao psql -U postgres -qAt \
    -c "ALTER DATABASE $DB RESET enable_bitmapscan;" \
    -c "ALTER DATABASE $DB RESET enable_tidscan;" || true
}
trap reset_db EXIT
reset_db

docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh "$DB"

echo "== 8.5: tắt GEQO (SET geqo TO off theo phiên)"
docker exec bao_server bash /app/scripts/exp1/run_baseline.sh "$DB" no_geqo

echo "== 8.4: tắt bitmap scan và tid scan (ALTER DATABASE, áp dụng cho mọi kết nối mới)"
docker exec pg_bao psql -U postgres -qAt \
  -c "ALTER DATABASE $DB SET enable_bitmapscan = off;" \
  -c "ALTER DATABASE $DB SET enable_tidscan = off;"
docker exec pg_bao psql -U postgres -d "$DB" -qAt -c "SHOW enable_bitmapscan;" -c "SHOW enable_tidscan;"
docker exec bao_server bash /app/scripts/exp1/run_baseline.sh "$DB" no_bitmap_tidscan
reset_db
docker exec pg_bao psql -U postgres -d "$DB" -qAt -c "SHOW enable_bitmapscan;" -c "SHOW enable_tidscan;"

echo "== So sánh với baseline"
for tag in no_geqo no_bitmap_tidscan; do
  f=$(ls logs/test__postgres__job__${tag}__*.txt | tail -1)
  python3 scripts/exp1/c1_win_loss.py --baseline "txt:$BASE" --candidate "txt:$f" --name "PG_${tag}"
done
echo "== Xong"
