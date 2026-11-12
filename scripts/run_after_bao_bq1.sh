#!/bin/bash
# Đợi Bao BQ-1 train + test xong, dừng vòng run_bao_remaining.sh trước khi sang split tiếp,
# rồi chạy 4.5: 113 câu JOB × 6 hint set × 3 lần, ghi logs/job_hintsets.jsonl.
# Chạy trên Mac:  nohup caffeinate -dis bash scripts/run_after_bao_bq1.sh > logs/run_after_bao_bq1.log 2>&1 &
# Chạy lại được: run_and_log.py bỏ qua các cặp (câu, hint set) đã có trong JSONL.
R=$(cd "$(dirname "$0")/.." && pwd)
DONE="$R/analysis/output/c1_Bao_job__base_query_split_1_fair_summary.csv"

echo "== $(date '+%F %T') Đợi Bao BQ-1 xong (file $DONE)"
while pgrep -f run_bao_remaining.sh > /dev/null && [ ! -f "$DONE" ]; do sleep 60; done

if [ -f "$DONE" ]; then
  echo "== $(date '+%F %T') Bao BQ-1 xong:"; cat "$DONE"
else
  echo "== $(date '+%F %T') run_bao_remaining.sh đã dừng nhưng không thấy kết quả BQ-1, vẫn chạy tiếp 4.5"
fi

# Dừng vòng Bao (không train thêm LOO-2, RND-2, ...). Muốn chạy tiếp sau này: bash scripts/run_bao_remaining.sh
# (split đã train sẽ tự bỏ qua).
pkill -f run_bao_remaining.sh
docker exec bao_server pkill -f run_bao_split.sh
docker exec bao_server pkill -f "run_queries.py|train.py" 2> /dev/null
sleep 5

echo "== $(date '+%F %T') Bắt đầu 4.5: 6 hint set"
docker exec bao_server python3 /app/scripts/run_and_log.py \
  --query_dir /app/bao/queries/join-order-benchmark --out /app/logs/job_hintsets.jsonl
echo "== $(date '+%F %T') Xong 4.5"
