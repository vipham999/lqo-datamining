#!/bin/bash
# Demo trực tiếp một phần ablation của bài báo (mục 8.4 và 8.5): cùng câu JOB, chỉ đổi một tham số PostgreSQL
# theo phiên (SET, không đổi cấu hình CSDL), thời gian thay đổi nhiều lần.
#   8.5 tắt GEQO              : 24b, 28a chậm đi (Mac 14/11: 3,8× và 8,2×; bài báo 9,9× và 2,1×)
#   8.4 tắt bitmap + tid scan : 15c chậm đi 3,5×, 30c nhanh lên 3,7× (Mac 14/11) → cùng một tham số, tác động hai chiều
# Thời gian đo bằng \timing của psql (gồm cả lập kế hoạch và thực thi).
# Mỗi cấu hình chạy 3 lần trên cùng kết nối, lấy lần thứ 3 (giống cách đo của tác giả); khoảng 1–2 phút.
#   bash scripts/demo_ablation.sh            (container pg_bao phải đang chạy; nên làm nóng CSDL trước)
#   bash scripts/demo_ablation.sh 28a 7c     (tự chọn câu: chạy cả 3 cấu hình cho từng câu)
D=/app/lqo/bao/queries/join-order-benchmark
run() {   # run <câu> <tên> <SET...>
  local q=$1 name=$2 set=$3 ms
  ms=$(printf 'SET enable_bao TO off;\n%s\n\\timing on\n\\o /dev/null\n\\i %s\n\\i %s\n\\i %s\n' \
         "$set" "$D/$q.sql" "$D/$q.sql" "$D/$q.sql" |
       docker exec -i pg_bao psql -U postgres -d imdbload -qAt 2>&1 | grep -o 'Time: [0-9.]*' | tail -1 | awk '{print $2}')
  [ -n "$ms" ] || { echo "    $name: lỗi (container pg_bao có đang chạy không?)"; return; }
  printf "    %8.0f ms   %s\n" "$ms" "$name"
  eval "T_${q}_$4=$ms"
}
ratio() {  # ratio <câu> <khóa cấu hình>
  local a b; eval "a=\$T_${1}_def; b=\$T_${1}_$2"
  [ -n "$a" ] && [ -n "$b" ] || return
  awk -v a="$a" -v b="$b" 'BEGIN{ r=b/a; if (r>=1) printf "      → chậm đi %.1f×\n", r; else printf "      → nhanh lên %.1f×\n", 1/r }'
}
GEQO="SET geqo TO off;"
BITMAP="SET enable_bitmapscan TO off; SET enable_tidscan TO off;"

if [ $# -gt 0 ]; then
  for q in "$@"; do
    echo "Câu $q:"
    run $q "PostgreSQL mặc định" "" def
    run $q "8.5 tắt GEQO" "$GEQO" geqo;            ratio $q geqo
    run $q "8.4 tắt bitmap + tid scan" "$BITMAP" bmp; ratio $q bmp
  done
  exit 0
fi

echo "== 8.5 Tắt GEQO (bộ tối ưu di truyền, PostgreSQL dùng khi câu nối từ 12 bảng trở lên)"
for q in 24b 28a; do
  echo "  Câu $q:"
  run $q "PostgreSQL mặc định (GEQO bật)" "" def
  run $q "geqo = off" "$GEQO" geqo; ratio $q geqo
done
echo
echo "== 8.4 Tắt bitmap scan + tid scan"
for q in 15c 30c; do
  echo "  Câu $q:"
  run $q "PostgreSQL mặc định" "" def
  run $q "enable_bitmapscan/tidscan = off" "$BITMAP" bmp; ratio $q bmp
done
