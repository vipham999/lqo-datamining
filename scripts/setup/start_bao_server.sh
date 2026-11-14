#!/bin/bash
# Khởi động Bao server trong tmux (session "bao"). Chạy TRONG container bao_server:
#   docker exec -it bao_server bash /app/scripts/setup/start_bao_server.sh [đường_dẫn_model]
# Xem log: tmux attach -t bao   (thoát: Ctrl+B rồi D)
tmux kill-session -t bao 2>/dev/null || true
tmux new-session -d -s bao "cd /app/bao/bao_server && python3 -u main.py $1 2>&1 | tee -a /app/logs/bao_server.log"
sleep 3
tmux ls
