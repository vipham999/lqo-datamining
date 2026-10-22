#!/bin/bash
# Khởi tạo cluster lần đầu, sau đó luôn chép cấu hình mới nhất rồi chạy PostgreSQL ở foreground.
set -e
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo postgres > /tmp/pw
  initdb -D "$PGDATA" -U postgres --pwfile=/tmp/pw --auth-local=trust --auth-host=md5 \
         --encoding=UTF8 --locale=C.UTF-8
  rm -f /tmp/pw
  echo "host all all 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
fi
cp /app/infra/postgresql.lqo.conf "$PGDATA/postgresql.conf"
exec postgres -D "$PGDATA"
