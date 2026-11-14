#!/bin/bash
# Đo lại PostgreSQL và Bao trong CÙNG điều kiện: cùng cấu hình, cùng phiên, cache đã nóng.
# Chạy trên Mac (không phải trong container), sau khi đã `docker compose up -d` trong infra/:
#   caffeinate -dis bash scripts/exp1/run_fair_comparison.sh
# Mất khoảng 1–1,5 giờ. Không train lại Bao: dùng model đã lưu trong logs/.
set -e
cd "$(dirname "$0")/../.."
TAG=fair_$(date +%Y%m%d_%H%M)
SPLITS=(job__leave_one_out_split_1 job__random_split_1)

echo "== Khởi động lại PostgreSQL để nạp cấu hình mới"
(cd infra && docker compose restart postgres)
until docker exec pg_bao pg_isready -q; do sleep 2; done
docker exec pg_bao psql -U postgres -qAt -c "SHOW shared_buffers;" -c "SHOW work_mem;"

docker exec pg_bao bash /app/scripts/setup/warmup_imdb.sh

echo "== Baseline PostgreSQL"
docker exec bao_server bash /app/scripts/exp1/run_baseline.sh imdbload "$TAG"

for s in "${SPLITS[@]}"; do
  model=$(ls -d logs/model__bao__${s}__* | tail -1)
  echo "== Bao $s với $model"
  docker exec bao_server bash /app/scripts/exp1/run_bao_test.sh "$s" "/app/$model" imdbload "$TAG"
done

echo "== So sánh"
pg=$(ls logs/test__postgres__job__${TAG}__*.txt | tail -1)
for s in "${SPLITS[@]}"; do
  python3 scripts/exp1/c1_win_loss.py --baseline "txt:$pg" \
    --candidate "txt:logs/test__bao__${s}__retest_${TAG}.txt" --name "Bao_${s}_${TAG}"
done
