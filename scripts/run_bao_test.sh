#!/bin/bash
# Chỉ test Bao bằng model đã train (không train lại). Chạy TRONG container bao_server:
#   bash /app/scripts/run_bao_test.sh job__random_split_1 /app/logs/model__bao__job__random_split_1__20261012_0602
set -e
SPLIT=${1:?Cần tên split, vd job__random_split_1}
MODEL=${2:?Cần thư mục model, vd /app/logs/model__bao__<split>__<thời_gian>}
DB=${3:-imdbload}
TAG=${4:-$(date +%Y%m%d_%H%M)}
cd /app/bao

[ -d "$MODEL" ] || { echo "Không thấy model $MODEL"; exit 1; }
N=$(wc -l < /app/logs/bao_server.log)
bash /app/scripts/start_bao_server.sh "$MODEL"
for _ in $(seq 90); do   # nạp model mất khoảng 15 s
  tail -n +"$((N + 1))" /app/logs/bao_server.log | grep -q "Accepted new model" && break
  sleep 1
done
tail -n +"$((N + 1))" /app/logs/bao_server.log | grep -q "Accepted new model" \
  || { echo "Bao server chưa nạp model, xem: tail /app/logs/bao_server.log"; exit 1; }

OUT=/app/logs/test__bao__${SPLIT}__retest_${TAG}.txt
python3 run_test_queries.py --use_bao --database_name "$DB" --query_dir "queries/$SPLIT/test" --output_file "$OUT"
echo "Log: $OUT"
