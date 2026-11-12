#!/bin/bash
# Train + test Bao lần lượt trên các split JOB còn thiếu, so sánh mỗi split với baseline PostgreSQL đo lại.
# Chạy trên Mac (container đã bật):  caffeinate -dis bash scripts/run_bao_remaining.sh
# Khoảng 3–4 giờ mỗi split. Split nào đã có dòng trong logs/bao_training_times.csv thì bỏ qua.
R=$(cd "$(dirname "$0")/.." && pwd)
PG=${PG:-$(ls "$R"/logs/test__postgres__job__fair_*.txt | tail -1)}
SPLITS=(job__base_query_split_1 job__leave_one_out_split_2 job__random_split_2 job__base_query_split_2
        job__leave_one_out_split_3 job__random_split_3 job__base_query_split_3)

echo "Baseline: $PG"
for s in "${SPLITS[@]}"; do
  grep -q "^$s," "$R/logs/bao_training_times.csv" && { echo "== Bỏ qua $s (đã train)"; continue; }
  echo "== $(date '+%F %T') Bắt đầu $s"
  if ! docker exec bao_server bash /app/scripts/run_bao_split.sh "$s"; then
    echo "== LỖI ở $s, chuyển sang split tiếp"; continue
  fi
  test_log=$(ls "$R"/logs/test__bao__${s}__2*.txt | tail -1)
  python3 "$R/scripts/c1_win_loss.py" --out_dir "$R/analysis/output" --baseline "txt:$PG" \
    --candidate "txt:$test_log" --name "Bao_${s}_fair"
  echo "== $(date '+%F %T') Xong $s"
done
echo "== Hết"
