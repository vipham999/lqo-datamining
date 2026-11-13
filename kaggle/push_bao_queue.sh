#!/bin/bash
# Đẩy lần lượt các notebook Bao còn lại lên Kaggle khi có chỗ trống (Kaggle cho tối đa 5 phiên CPU cùng lúc).
#   nohup bash kaggle/push_bao_queue.sh > kaggle/push_bao_queue.log 2>&1 &
R=$(cd "$(dirname "$0")/.." && pwd)
K=~/.venvs/kaggle/bin/kaggle
QUEUE=(random-1 base-query-2 random-2 random-3 base-query-3)    # BQ-2 trước: split có nguy cơ chạy lâu nhất
for s in "${QUEUE[@]}"; do
  until out=$($K kernels push -p "$R/kaggle/bao-job-$s" 2>&1) && echo "$out" | grep -q "successfully pushed"; do
    echo "$(date '+%F %T') $s: chưa có chỗ ($(echo "$out" | tail -1 | cut -c1-80)), thử lại sau 10 phút"
    sleep 600
  done
  echo "$(date '+%F %T') $s: đã đẩy lên"
  sleep 60
done
echo "$(date '+%F %T') Đã đẩy hết"
