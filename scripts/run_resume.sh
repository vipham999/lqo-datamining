#!/bin/bash
# Chạy tiếp phần còn lại sau khi Mac khởi động lại (09/11 20:08):
#   1) Ablation 8.3: làm nóng imdbload50, đo lại baseline PG, test Bao LOO-1/RND-1 (model train trên IMDB đầy đủ)
#   2) Train + test Bao các split JOB còn thiếu (RND-2, LOO-3, RND-3, BQ-3)
#   nohup caffeinate -dis bash scripts/run_resume.sh > logs/run_resume.log 2>&1 &
R=$(cd "$(dirname "$0")/.." && pwd)

# Thử lại tối đa 3 lần nếu Bao server (tmux) chưa nạp được model
bao_test() {
  for k in 1 2 3; do
    docker exec bao_server bash /app/scripts/run_bao_test.sh "$@" && return 0
    echo "== Thử lại lần $((k + 1)) sau 20 s"; docker exec bao_server tmux kill-server 2>/dev/null; sleep 20
  done
  return 1
}

echo "== $(date '+%F %T') 1) Ablation 8.3 imdbload50"
TAG=imdb50_$(date +%Y%m%d_%H%M)
docker exec pg_bao bash /app/scripts/warmup_imdb.sh imdbload50
docker exec bao_server bash /app/scripts/run_baseline.sh imdbload50 "$TAG"
pg50=$(ls "$R"/logs/test__postgres__job__${TAG}__*.txt | tail -1)
for s in job__leave_one_out_split_1 job__random_split_1; do
  model=$(ls -d "$R"/logs/model__bao__${s}__2026101* | tail -1 | sed "s#$R/##")
  bao_test "$s" "/app/$model" imdbload50 "$TAG" &&
    python3 "$R/scripts/c1_win_loss.py" --out_dir "$R/analysis/output" --baseline "txt:$pg50" \
      --candidate "txt:$R/logs/test__bao__${s}__retest_${TAG}.txt" --name "Bao_${s}_${TAG}"
done

echo "== $(date '+%F %T') 2) Train Bao các split còn lại"
docker exec bao_server tmux kill-server 2>/dev/null
bash "$R/scripts/run_bao_remaining.sh"
echo "== $(date '+%F %T') Hết"
