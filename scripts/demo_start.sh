#!/bin/bash
# Chuẩn bị mọi thứ trước khi quay demo (chạy 1 lần, ~5-10 phút do làm nóng cache):
#   bash scripts/demo_start.sh            # đầy đủ: kiểm tra Docker, làm nóng cache, mở dashboard
#   bash scripts/demo_start.sh --no-warm  # bỏ qua làm nóng (khi vừa làm nóng xong)
cd "$(dirname "$0")/.." || exit 1

echo "== 1. Container"
for c in pg_bao bao_server; do
  if [ "$(docker inspect -f '{{.State.Running}}' $c 2>/dev/null)" != "true" ]; then
    echo "  $c chưa chạy → khởi động"; docker compose -f infra/docker-compose.yml up -d
    sleep 5; break
  fi
done
docker exec pg_bao psql -U postgres -d imdbload -qAt -c "select 'IMDB ok: ' || count(*) || ' bảng' from pg_tables where schemaname='public';" \
  || { echo "  Không kết nối được pg_bao"; exit 1; }

if [ "$1" != "--no-warm" ]; then
  echo "== 2. Làm nóng cache (để thời gian demo ổn định)"
  docker exec pg_bao bash /app/scripts/warmup_imdb.sh > /tmp/demo_warmup.log 2>&1 && echo "  xong (log: /tmp/demo_warmup.log)"
fi

echo "== 3. Dashboard tại http://localhost:8501"
exec ~/.venvs/lqo_app/bin/streamlit run app/streamlit_app.py --server.headless true --theme.base light
