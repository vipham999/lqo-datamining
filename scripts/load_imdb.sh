#!/bin/bash
# Nạp IMDB cho JOB như bài báo. Chạy TRONG container pg_bao:
#   docker exec -it pg_bao bash /app/scripts/load_imdb.sh
set -ex
DB=${1:-imdbload}
bash /app/lqo/balsa/load-postgres/load_job_postgres.sh /data/imdb "$DB"
# Hai index bổ sung trên complete_cast(subject_id, status_id) của Mục 8.1.1 đã có sẵn trong
# balsa/load-postgres/fkindexes.sql, và script của Balsa đã chạy ANALYZE (autovacuum tắt) nên không làm lại.
psql -d "$DB" -c "SELECT indexname FROM pg_indexes WHERE tablename = 'complete_cast';"
psql -d "$DB" -c "SELECT pg_size_pretty(pg_database_size('$DB')) AS db_size;"
