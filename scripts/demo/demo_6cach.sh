#!/bin/bash
# Demo mở đầu: cùng một câu JOB, chạy theo cả 6 cách (giữ nguyên + tắt 1 trong 5 toán tử) → thời gian chênh nhau nhiều lần.
# Mỗi cách chạy 2 lần trên cùng kết nối (lần đầu làm nóng cache), in thời gian lần thứ 2 và tỉ lệ so với mặc định.
#   bash scripts/demo/demo_6cach.sh [câu]     (mặc định 7c, khoảng 40 giây; container pg_bao phải đang chạy)
# Đo ngày 17/11 trên máy WSL (cache nóng): 7c mặc định 1,9 s; tắt index scan 1,1 s; tắt nested loop 10 s.
# Lưu ý RAM: tắt nested loop → nhiều hash join, mỗi cái dùng tới work_mem (256 MB) trên mỗi worker song song.
# Nếu máy thiếu RAM, Linux sẽ kill PostgreSQL ("terminated by signal 9"), PostgreSQL tự khởi động lại và cache bị xoá.
# Script sẽ in lý do lỗi và chờ PostgreSQL sẵn sàng. Muốn tránh: tắt bớt container khác, rồi chạy lại warmup_imdb.sh.
Q=${1:-7c}
F=/app/lqo/bao/queries/join-order-benchmark/$Q.sql
[ -n "$(docker ps -q -f name=^pg_bao$)" ] || { echo "Container pg_bao chưa chạy (docker start pg_bao)"; exit 1; }
run_psql() {   # run_psql "<lệnh SET>" → toàn bộ output của psql (2 lần chạy câu)
  printf 'SET enable_bao TO off;\n%s\n\\timing on\n\\o /dev/null\n\\i %s\n\\i %s\n' "$1" "$F" "$F" |
    docker exec -i pg_bao psql -U postgres -d imdbload -qAt 2>&1
}
wait_ready() {   # PostgreSQL vừa bị khởi động lại (thường do hết RAM) → chờ hết "recovery mode"
  for _ in $(seq 60); do
    docker exec pg_bao pg_isready -U postgres -d imdbload -q 2>/dev/null &&
      docker exec pg_bao psql -U postgres -d imdbload -qAt -c "select 1" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}
NAMES=("Giữ nguyên PostgreSQL" "Tắt nested loop" "Tắt hash join" "Tắt merge join" "Tắt seq scan" "Tắt index scan")
SETS=("" "SET enable_nestloop = off;" "SET enable_hashjoin = off;" "SET enable_mergejoin = off;"
      "SET enable_seqscan = off;" "SET enable_indexscan = off; SET enable_indexonlyscan = off;")
echo "Câu $Q – cùng một câu SQL, 6 cách thực thi (cache nóng):"
BASE=""
for i in "${!NAMES[@]}"; do
  out=$(run_psql "${SETS[$i]}")
  ms=$(echo "$out" | grep -o 'Time: [0-9.]*' | tail -n 1 | awk '{print $2}')
  if [ -z "$ms" ] || echo "$out" | grep -qE 'server closed|terminated abnormally|recovery mode|connection to server'; then
    why=$(echo "$out" | grep -m1 -E 'ERROR|FATAL|server closed|terminated' | sed 's/^psql:[^:]*:[0-9]*: //')
    printf "  %-24s lỗi: %s\n" "${NAMES[$i]}" "${why:-không đọc được thời gian}"
    if echo "$out" | grep -qE 'server closed|terminated abnormally|recovery mode|connection to server'; then
      echo "  → PostgreSQL bị khởi động lại (thường do hết RAM). Chờ PostgreSQL sẵn sàng rồi chạy tiếp…"
      wait_ready || { echo "  PostgreSQL chưa sẵn sàng sau 60 giây, dừng."; exit 1; }
    fi
    continue
  fi
  [ -n "$BASE" ] || BASE=$ms
  awk -v n="${NAMES[$i]}" -v ms="$ms" -v b="$BASE" 'BEGIN {
    r = b / ms; note = (ms == b) ? "" : (r >= 1.1 ? sprintf("nhanh hơn %.1f lần", r) : (r <= 0.91 ? sprintf("chậm hơn %.1f lần", 1 / r) : "ngang"))
    printf "  %-24s %6.2f giây   %s\n", n, ms / 1000, note }'
done
