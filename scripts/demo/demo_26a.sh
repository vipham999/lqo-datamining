#!/bin/bash
# Demo khi báo cáo: cùng câu JOB 26a, chạy với 3 phương án → thời gian chênh nhau nhiều lần.
# Mỗi phương án chạy 2 lần trên cùng kết nối (lần đầu làm nóng cache), in thời gian lần thứ 2; khoảng 1,5 phút.
#   bash scripts/demo/demo_26a.sh [câu]     (container pg_bao phải đang chạy; nên làm nóng CSDL trước)
Q=${1:-26a}
F=/app/lqo/bao/queries/join-order-benchmark/$Q.sql
run() {
  local name=$1 set=$2 ms
  ms=$(printf '%s\n\\timing on\n\\o /dev/null\n\\i %s\n\\i %s\n' "$set" "$F" "$F" |
       docker exec -i pg_bao psql -U postgres -d imdbload -qAt 2>&1 | grep -o 'Time: [0-9.]*' | tail -1 | awk '{print $2}')
  [ -n "$ms" ] || { echo "  $name: lỗi (container pg_bao có đang chạy không?)"; return; }
  printf "  %-32s %7.2f giây\n" "$name" "$(echo "$ms / 1000" | bc -l)"
}
echo "Câu $Q – cùng một câu SQL, khác cách thực thi (cache nóng):"
run "PostgreSQL mặc định" ""
run "Tắt index scan (no_indexscan)" "SET enable_indexscan = off; SET enable_indexonlyscan = off;"
run "Tắt hash join (no_hashjoin)" "SET enable_hashjoin = off;"
