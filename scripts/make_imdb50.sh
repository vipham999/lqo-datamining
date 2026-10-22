#!/bin/bash
# Ablation 8.3 (covariate shift): tạo imdbload50 giữ ~50% bảng title (Bernoulli sampling),
# xóa các dòng phụ thuộc để giữ toàn vẹn tham chiếu (FK trong repo không có ON DELETE CASCADE).
# Chạy TRONG container pg_bao:  docker exec -it pg_bao bash /app/scripts/make_imdb50.sh
# Cần thêm ~10 GB ổ đĩa. Không được có kết nối nào khác tới imdbload khi chạy.
set -ex
psql -d postgres -c "DROP DATABASE IF EXISTS imdbload50;"
psql -d postgres -c "CREATE DATABASE imdbload50 TEMPLATE imdbload;"
psql -d imdbload50 -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE keep_title AS SELECT id FROM title TABLESAMPLE BERNOULLI (50) REPEATABLE (42);
CREATE UNIQUE INDEX ON keep_title(id);
DELETE FROM cast_info       c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id);
DELETE FROM complete_cast   c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id);
DELETE FROM movie_companies c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id);
DELETE FROM movie_info      c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id);
DELETE FROM movie_info_idx  c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id);
DELETE FROM movie_keyword   c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id);
DELETE FROM movie_link      c WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.movie_id)
                                 OR NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = c.linked_movie_id);
DELETE FROM title           t WHERE NOT EXISTS (SELECT 1 FROM keep_title k WHERE k.id = t.id);
DROP TABLE keep_title;
VACUUM FULL;
ANALYZE VERBOSE;
SELECT 'title' AS t, count(*) FROM title UNION ALL SELECT 'cast_info', count(*) FROM cast_info;
SQL
