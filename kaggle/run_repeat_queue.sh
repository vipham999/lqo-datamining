#!/bin/bash
# Đợt lặp giống tác giả: đẩy lần lượt 41 notebook lên Kaggle (tối đa 5 phiên CPU cùng lúc) và tự tải output về
# logs/kaggle/tai_ve/<slug>/ khi notebook chạy xong; sau đó chuyển vào logs/kaggle/<bao|hybridqo>/<split>/lap<N>/
# hoặc logs/kaggle/ablation/... để exp1_tables.py đọc được.
#   1 × ablation 8.4+8.5 (8 lượt) · 4 × ablation 8.3 · 18 × HybridQO (rep1, rep2) · 18 × Bao (rep1, rep2)
# HybridQO (~7 giờ/notebook) đẩy trước Bao (~2,5 giờ) để các notebook ngắn lấp chỗ trống cuối đợt.
#   nohup caffeinate -is bash kaggle/run_repeat_queue.sh >> kaggle/run_repeat_queue.log 2>&1 &
R=$(cd "$(dirname "$0")/.." && pwd)
K=~/.venvs/kaggle/bin/kaggle
U=vipham999
SPLITS=(leave-one-out-1 leave-one-out-2 leave-one-out-3 random-1 random-2 random-3 base-query-1 base-query-2 base-query-3)

QUEUE=(ablation-job-8-4-8-5-r8 ablation-job-8-3-rep1 ablation-job-8-3-rep2 ablation-job-8-3-rep3 ablation-job-8-3-rep4)
# Thứ tự: HybridQO rep1 → Bao rep1, rep2 → HybridQO rep2 (lần lặp thứ 3 của HybridQO để cuối vì tốn ~7 giờ/notebook,
# để Bao và HybridQO đều có ít nhất 2 lần train sớm nhất có thể).
for s in "${SPLITS[@]}"; do QUEUE+=("hybridqo-job-$s-rep1"); done
for r in 1 2; do for s in "${SPLITS[@]}"; do QUEUE+=("bao-job-$s-rep$r"); done; done
for s in "${SPLITS[@]}"; do QUEUE+=("hybridqo-job-$s-rep2"); done
LOG="$R/kaggle/run_repeat_queue.log"

log() { echo "$(date '+%F %T') $*"; }
status() { $K kernels status "$U/$1" 2>&1 | grep -o 'KernelWorkerStatus\.[A-Z_]*' | sed 's/.*\.//'; }

PENDING=()      # đã đẩy, chưa tải output
check_done() {
  local keep=() s st
  for s in "${PENDING[@]}"; do
    st=$(status "$s")
    case "$st" in
      COMPLETE|ERROR|CANCEL*)
        mkdir -p "$R/logs/kaggle/tai_ve/$s"
        if $K kernels output "$U/$s" -p "$R/logs/kaggle/tai_ve/$s" > /dev/null 2>&1; then
          log "$s: $st, đã tải output về logs/kaggle/tai_ve/$s"
        else
          log "$s: $st, tải output LỖI (thử lại lần sau)"; keep+=("$s"); continue
        fi
        [ "$st" = COMPLETE ] || log "$s: CẢNH BÁO kết thúc với $st, cần xem log";;
      *) keep+=("$s");;
    esac
  done
  PENDING=("${keep[@]}")
}

log "Bắt đầu, ${#QUEUE[@]} notebook"
# Chạy lại script: notebook đã đẩy (theo log) thì không đẩy lại; chưa tải output thì đưa vào PENDING.
for s in "${QUEUE[@]}"; do
  grep -q " $s: đã đẩy lên" "$LOG" 2>/dev/null || continue
  grep -q " $s: [A-Z_]*, đã tải output" "$LOG" || PENDING+=("$s")
done
[ ${#PENDING[@]} -gt 0 ] && log "Tiếp tục: đang chờ ${PENDING[*]}"
for s in "${QUEUE[@]}"; do
  grep -q " $s: đã đẩy lên" "$LOG" 2>/dev/null && continue
  [ -f "$R/kaggle/$s/kernel-metadata.json" ] || { log "$s: không có thư mục notebook, bỏ qua"; continue; }
  until out=$($K kernels push -p "$R/kaggle/$s" 2>&1) && echo "$out" | grep -q "successfully pushed"; do
    log "$s: chưa đẩy được ($(echo "$out" | tail -1 | cut -c1-90)), thử lại sau 10 phút"
    sleep 600
    check_done
  done
  log "$s: đã đẩy lên"
  PENDING+=("$s")
  sleep 90
  check_done
done
log "Đã đẩy hết, chờ ${#PENDING[@]} notebook chạy xong"
while [ ${#PENDING[@]} -gt 0 ]; do sleep 900; check_done; done
log "Xong toàn bộ"
