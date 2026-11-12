#!/bin/bash
# Đẩy 2 notebook ablation lên Kaggle sau hàng đợi Bao (Kaggle cho tối đa 5 phiên CPU cùng lúc).
#   8.4 + 8.5, rồi 8.6 : khi hàng đợi Bao đã đẩy hết và có chỗ trống
#   8.3       : khi bao-job-base-query-1 đã CHẠY XONG (cần model Bao-Full của nó)
#   nohup bash kaggle/push_ablation_queue.sh > kaggle/push_ablation_queue.log 2>&1 &
R=$(cd "$(dirname "$0")/.." && pwd)
K=~/.venvs/kaggle/bin/kaggle
status() { $K kernels status "vipham999/$1" 2>&1 | grep -o 'KernelWorkerStatus\.[A-Z_]*' | sed 's/.*\.//'; }
push() {   # thử đến khi đẩy được
  until out=$($K kernels push -p "$R/kaggle/$1" 2>&1) && echo "$out" | grep -q "successfully pushed"; do
    echo "$(date '+%F %T') $1: chưa đẩy được ($(echo "$out" | tail -1 | cut -c1-80)), thử lại sau 10 phút"
    sleep 600
  done
  echo "$(date '+%F %T') $1: đã đẩy lên"
}

until grep -q "Đã đẩy hết" "$R/kaggle/push_bao_queue.log" 2>/dev/null; do sleep 600; done
push ablation-job-8-4-8-5
sleep 60
push ablation-job-8-6

until [ "$(status bao-job-base-query-1)" = COMPLETE ]; do
  for s in bao-job-base-query-1; do
    st=$(status $s); case "$st" in ERROR|CANCEL*) echo "$(date '+%F %T') $s kết thúc với $st: dừng, không chạy 8.3"; exit 1;; esac
  done
  sleep 600
done
push ablation-job-8-3
echo "$(date '+%F %T') Đã đẩy hết ablation"
