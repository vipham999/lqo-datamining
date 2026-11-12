#!/bin/bash
# Chạy ablation 8.4 + 8.5 kiểu xen kẽ, phân tích, rồi (tuỳ chọn) chạy tiếp hàng đợi train Bao.
#   caffeinate -dis bash scripts/run_ablation_interleaved.sh [--then-bao]
# KHÔNG chạy song song với bất kỳ việc train/test nào khác trên cùng CSDL.
set -e
cd "$(dirname "$0")/.."
TAG=interleaved_$(date +%Y%m%d_%H%M)

n=$(docker exec pg_bao psql -U postgres -qAt -c \
  "SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend' AND pid<>pg_backend_pid();")
[ "$n" = "0" ] || { echo "Đang có $n kết nối khác vào PostgreSQL, dừng lại."; exit 1; }

docker exec pg_bao bash /app/scripts/warmup_imdb.sh imdbload
docker exec bao_server python3 -u /app/scripts/ablation_interleaved.py --tag "$TAG"
python3 scripts/ablation_analyze.py --tag "$TAG" | tee "analysis/output/ablation_${TAG}_tomtat.txt"

if [ "$1" = "--then-bao" ]; then
  echo "== $(date '+%F %T') Chạy tiếp hàng đợi train Bao"
  bash scripts/run_bao_remaining.sh
fi
