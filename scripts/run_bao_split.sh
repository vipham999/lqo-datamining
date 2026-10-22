#!/bin/bash
# Huấn luyện + test Bao trên một split (Mục 6.3 README). Chạy TRONG container bao_server, nên trong tmux:
#   docker exec -it bao_server bash
#   tmux new -s run
#   bash /app/scripts/run_bao_split.sh job__random_split_1
# Các split JOB: job__{leave_one_out,random,base_query}_split_{1,2,3}
set -e
SPLIT=${1:?Cần tên split, vd job__random_split_1}
DB=${2:-imdbload}
STAMP=$(date +%Y%m%d_%H%M)
cd /app/bao

echo "== [$SPLIT] Xóa kinh nghiệm và model cũ để không rò rỉ giữa các split"
(cd bao_server && python3 clear_experience.py && rm -rf bao_default_model)
bash /app/scripts/start_bao_server.sh

echo "== [$SPLIT] Huấn luyện"
T0=$(date +%s)
python3 run_queries.py --database_name "$DB" --query_dir "queries/$SPLIT/train" \
  --output_file "/app/logs/train__bao__${SPLIT}__${STAMP}.txt"
T1=$(date +%s)
echo "$SPLIT,train_seconds,$((T1 - T0))" >> /app/logs/bao_training_times.csv
cp -r bao_server/bao_default_model "/app/logs/model__bao__${SPLIT}__${STAMP}"

echo "== [$SPLIT] Test (lấy lần chạy thứ 3 khi phân tích)"
bash /app/scripts/start_bao_server.sh   # nạp lại model vừa train
python3 run_test_queries.py --use_bao --database_name "$DB" --query_dir "queries/$SPLIT/test" \
  --output_file "/app/logs/test__bao__${SPLIT}__${STAMP}.txt"
echo "== Xong. Thời gian train: $((T1 - T0)) giây"
