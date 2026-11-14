#!/bin/bash
# Demo trực tiếp ablation 8.3 của bài báo bằng Bao thật trên Mac: CSDL IMDB đầy đủ, cùng câu SQL, hai model Bao
#   Bao-Full : train trên IMDB đầy đủ   (Kaggle, ablation-job-8-3-rep4, split base_query_split_1)
#   Bao-50   : train trên IMDB 50%      (cùng notebook) → dùng trên IMDB đầy đủ = dữ liệu đã thay đổi so với lúc train
# Với mỗi model: nạp vào Bao server, Bao tự chọn bộ gợi ý (hint) cho từng câu, chạy 3 lần lấy lần thứ 3.
# Kết quả đo ngày 14/11 trên Mac: Bao-50 chọn "SET enable_nestloop TO off" cho 16c/3c/11b, Bao-Full giữ plan mặc định.
#   bash scripts/demo/demo_83.sh [câu ...]        (mặc định 3c 11b 16c; khoảng 1 phút)
# Cần: container pg_bao và bao_server đang chạy; model đã chép vào logs/demo_83/ (xem cuối file).
R=$(cd "$(dirname "$0")/../.." && pwd)
QS=${*:-3c 11b 16c}
M=/app/logs/demo_83
[ -d "$R/logs/demo_83/full_rep4" ] || {
  mkdir -p "$R/logs/demo_83"
  K="$R/kaggle_runs/ablation-job-8-3-rep4/ablation83_logs"
  cp -R "$K/model__bao__job__base_query_split_1" "$R/logs/demo_83/full_rep4" &&
  cp -R "$K/model__bao__job__base_query_split_1__imdb50" "$R/logs/demo_83/50_rep4" || { echo "Thiếu model trong $K"; exit 1; }
}
BAO="SET bao_host TO '10.5.0.6'; SET enable_bao TO on; SET enable_bao_selection TO on; SET enable_bao_rewards TO off;"

load_model() {   # nạp model vào Bao server, chờ "Accepted new model"
  docker exec bao_server bash /app/scripts/setup/start_bao_server.sh "$M/$1" > /dev/null 2>&1
  for _ in $(seq 30); do
    docker exec bao_server tail -1 /app/logs/bao_server.log 2>/dev/null | grep -q "Accepted new model" && return 0
    sleep 1
  done
  echo "  Bao server chưa nạp được model $1"; exit 1
}
hint() {         # bộ gợi ý Bao chọn cho câu $1
  local sql; sql=$(cat "$R/lqo_ml_perspective/bao/queries/join-order-benchmark/$1.sql")
  printf '%s\nEXPLAIN %s\n' "$BAO" "$sql" | docker exec -i pg_bao psql -U postgres -d imdbload -qAt 2>&1 |
    sed -n 's/^Bao recommended hint: *//p' | sed 's/ *$//'
}
ms() {           # thời gian lần thứ 3 khi Bao chọn plan
  local f=/app/lqo/bao/queries/join-order-benchmark/$1.sql
  printf '%s\n\\timing on\n\\o /dev/null\n\\i %s\n\\i %s\n\\i %s\n' "$BAO" "$f" "$f" "$f" |
    docker exec -i pg_bao psql -U postgres -d imdbload -qAt 2>&1 | grep -o 'Time: [0-9.]*' | tail -1 | awk '{print $2}'
}

for m in full_rep4 50_rep4; do
  case $m in full*) name="Bao-Full (train trên IMDB đầy đủ)";; *) name="Bao-50   (train trên IMDB 50%)";; esac
  echo "== $name, chạy trên IMDB đầy đủ"
  load_model $m
  for q in $QS; do
    h=$(hint $q); t=$(ms $q); eval "T_${m}_$q=$t"
    printf "  %-4s %8.0f ms   hint: %s\n" "$q" "${t:-0}" "${h:-?}"
  done
  echo
done
echo "== So sánh Bao-50 với Bao-Full"
for q in $QS; do
  eval "a=\$T_full_rep4_$q; b=\$T_50_rep4_$q"
  awk -v q="$q" -v a="$a" -v b="$b" 'BEGIN{ if (a>0 && b>0) {
    r=b/a; if (r>=1.1) s=sprintf("Bao-50 chậm hơn %.1f×", r); else if (r<=0.91) s=sprintf("Bao-50 nhanh hơn %.1f×", 1/r); else s="như nhau";
    printf "  %-4s %s\n", q, s } }'
done
docker exec bao_server tmux kill-session -t bao 2> /dev/null   # tắt Bao server như trước khi demo
