#!/bin/bash
# Chạy tuần tự toàn bộ phần còn lại trên Mac (KHÔNG chạy gì khác trên pg_bao trong lúc này):
#   1) Ablation 8.4 + 8.5 (xen kẽ, có baseline riêng)          ~1 giờ
#   2) Ablation 8.3: tạo imdbload50, baseline PG + test Bao (model train trên IMDB đầy đủ)   ~1,5–2 giờ
#   3) Train + test Bao trên các split JOB còn thiếu            ~3–4 giờ mỗi split
#   caffeinate -dis bash scripts/run_plan.sh
R=$(cd "$(dirname "$0")/.." && pwd)
free_gb() { df -g /System/Volumes/Data | awk 'NR==2{print $4}'; }

echo "== $(date '+%F %T') 1) Ablation 8.4 + 8.5"
bash "$R/scripts/run_ablation_interleaved.sh" || echo "== LỖI ở ablation 8.4/8.5, chạy tiếp"

echo "== $(date '+%F %T') 2) Ablation 8.3 imdbload50"
if [ "$(free_gb)" -lt 15 ]; then
  echo "== Bỏ qua 8.3: chỉ còn $(free_gb) GB trống, cần khoảng 15 GB"
elif docker exec pg_bao bash /app/scripts/make_imdb50.sh; then
  TAG=imdb50_$(date +%Y%m%d_%H%M)
  docker exec pg_bao bash /app/scripts/warmup_imdb.sh imdbload50
  docker exec bao_server bash /app/scripts/run_baseline.sh imdbload50 "$TAG"
  pg50=$(ls "$R"/logs/test__postgres__job__${TAG}__*.txt | tail -1)
  for s in job__leave_one_out_split_1 job__random_split_1; do
    model=$(ls -d "$R"/logs/model__bao__${s}__2026101* | tail -1 | sed "s#$R/##")
    docker exec bao_server bash /app/scripts/run_bao_test.sh "$s" "/app/$model" imdbload50 "$TAG" &&
      python3 "$R/scripts/c1_win_loss.py" --out_dir "$R/analysis/output" --baseline "txt:$pg50" \
        --candidate "txt:$R/logs/test__bao__${s}__retest_${TAG}.txt" --name "Bao_${s}_${TAG}"
  done
else
  echo "== LỖI khi tạo imdbload50, chạy tiếp"
fi

echo "== $(date '+%F %T') 3) Train Bao các split còn lại"
bash "$R/scripts/run_bao_remaining.sh"
echo "== $(date '+%F %T') Hết plan"
