#!/bin/bash
# Chạy ablation 8.4 + 8.5 kiểu xen kẽ rồi phân tích.
#   caffeinate -dis bash scripts/ablation/run_ablation_interleaved.sh
# KHÔNG chạy song song với bất kỳ việc train/test nào khác trên cùng CSDL.
set -e
cd "$(dirname "$0")/../.."
TAG=interleaved_$(date +%Y%m%d_%H%M)

n=$(docker exec pg_bao psql -U postgres -qAt -c \
  "SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend' AND pid<>pg_backend_pid();")
[ "$n" = "0" ] || { echo "Đang có $n kết nối khác vào PostgreSQL, dừng lại."; exit 1; }

docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh imdbload
docker exec bao_server python3 -u /app/scripts/ablation/ablation_interleaved.py --tag "$TAG"
python3 scripts/ablation/ablation_analyze.py --tag "$TAG" | tee "analysis/output/ablation_${TAG}_tomtat.txt"
