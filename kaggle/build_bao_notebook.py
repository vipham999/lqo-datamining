"""Sinh notebook Kaggle chạy Bao (train + test) cho từng split JOB, cùng môi trường với notebook HybridQO.

    python3 kaggle/build_bao_notebook.py --user vipham999 --all          # 9 split
    python3 kaggle/build_bao_notebook.py --user vipham999 --split base_query_split_1

Mỗi split tạo kaggle/bao-job-<split>/ gồm notebook .ipynb và kernel-metadata.json (CPU, có Internet).
Cấu hình PostgreSQL giống notebook HybridQO (shared_buffers 8GB, work_mem 512MB…) để so Bao với HybridQO trên
cùng môi trường; GEQO bật cho Bao và PostgreSQL (chú thích ¹ Bảng 2 bài báo).

Kết quả trong /kaggle/working/bao_logs/ (cùng tên và định dạng với logs/ trên Mac):
  test__postgres__job__<split>.txt   baseline PostgreSQL trên tập test (3 lần/câu, đo ngay trước Bao)
  train__bao__job__<split>.txt       log train (run_queries.py)
  test__bao__job__<split>.txt        Bao trên tập test (3 lần/câu)
  bao_training_times.csv             <split>,train_seconds,<giây>[,truncated]
  model__bao__job__<split>/          model đã train
  bao_server.log, tom_tat__<split>.txt
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL_SPLITS = [f"{k}_split_{i}" for k in ("leave_one_out", "random", "base_query") for i in (1, 2, 3)]

CELLS = [
# ---------------------------------------------------------------- 0. máy
r'''%%bash
nproc; free -g | head -2
df -h /tmp /kaggle/working''',

# ---------------------------------------------------------------- 1. build PostgreSQL 12.5 + pg_bao
r'''%%bash
set -e
LOG=/tmp/pg_build.log; : > $LOG
run() { "$@" >> $LOG 2>&1 || { echo "LỖI khi chạy: $*"; tail -30 $LOG; exit 1; }; }

# Mã nguồn của tác giả: Bao (server + extension), script nạp IMDB, các split
[ -d /tmp/lqo_ml_perspective ] || git clone -q https://github.com/edualc/lqo_ml_perspective.git /tmp/lqo_ml_perspective

PKG=""
[ -x /opt/pg12/bin/pg_config ] && PKG=$(/opt/pg12/bin/pg_config --pkglibdir)
if [ -n "$PKG" ] && [ -f "$PKG/pg_bao.so" ] && [ -f "$PKG/pg_prewarm.so" ]; then
  echo "Đã build từ trước, bỏ qua."
else
  run apt-get update -qq
  run apt-get install -y -qq build-essential libreadline-dev zlib1g-dev
  cd /tmp
  rm -rf postgresql-12.5 postgresql-12.5.tar.gz
  run wget -q https://ftp.postgresql.org/pub/source/v12.5/postgresql-12.5.tar.gz
  tar xzf postgresql-12.5.tar.gz && cd postgresql-12.5
  run ./configure --prefix=/opt/pg12
  run make -j"$(nproc)"
  run make install
  run make -C contrib/pg_prewarm install          # để làm nóng cache
  # Extension của Bao (giống infra/Dockerfile.pg trên Mac)
  rm -rf /tmp/pg_bao && cp -r /tmp/lqo_ml_perspective/bao/pg_extension /tmp/pg_bao
  run make -C /tmp/pg_bao USE_PGXS=1 PG_CONFIG=/opt/pg12/bin/pg_config install
fi
/opt/pg12/bin/postgres --version
PKG=$(/opt/pg12/bin/pg_config --pkglibdir)
[ -f "$PKG/pg_bao.so" ] || { echo "Không thấy pg_bao.so trong $PKG"; exit 1; }
echo "pg_bao OK"''',

# ---------------------------------------------------------------- 2. khởi tạo và cấu hình PostgreSQL
r'''%%bash
set -e
id -u postgres > /dev/null 2>&1 || useradd -m -s /bin/bash postgres
if [ ! -f /tmp/pgdata/PG_VERSION ]; then
mkdir -p /tmp/pgdata && chown postgres /tmp/pgdata
su postgres -c "/opt/pg12/bin/initdb -D /tmp/pgdata -U postgres --auth=trust" > /dev/null
# Bộ nhớ GIỐNG notebook HybridQO để so hai phương pháp trên cùng môi trường.
# Khác HybridQO: geqo = on (chú thích ¹ Bảng 2: GEQO bật cho Bao và PostgreSQL), nạp pg_bao.
cat >> /tmp/pgdata/postgresql.conf <<'EOF'
listen_addresses = 'localhost'
shared_buffers = 8GB
temp_buffers = 32GB
work_mem = 512MB
effective_cache_size = 32GB
max_parallel_workers_per_gather = 4
max_parallel_maintenance_workers = 4
geqo = on
autovacuum = off
shared_preload_libraries = 'pg_bao'
dynamic_shared_memory_type = mmap
EOF
fi
su postgres -c "/opt/pg12/bin/pg_ctl -D /tmp/pgdata status" > /dev/null \
  || su postgres -c "/opt/pg12/bin/pg_ctl -D /tmp/pgdata -l /tmp/pg.log start -w"
/opt/pg12/bin/psql -U postgres -h localhost -Atc "SELECT name, setting FROM pg_settings WHERE name IN ('shared_buffers','work_mem','geqo','shared_preload_libraries')"''',

# ---------------------------------------------------------------- 3. nạp IMDB (giống notebook HybridQO)
r'''%%bash
set -e
export PATH=/opt/pg12/bin:$PATH PGHOST=localhost PGUSER=postgres
[ -x /opt/pg12/bin/psql ] || { echo "Chưa có PostgreSQL (phiên Kaggle mới?): chạy lại ô 1 và 2."; exit 1; }
pg_isready -q || { echo "PostgreSQL chưa chạy: chạy lại ô 2."; exit 1; }
if pgrep -f load_job_postgres.sh > /dev/null; then
  echo "Lần chạy trước vẫn đang nạp. Xem: tail /tmp/load.log. Đợi xong rồi chạy lại ô này."; exit 1
fi
if [ -f /tmp/imdb_loaded ]; then
  echo "IMDB đã nạp từ trước, bỏ qua."
else
  dropdb --if-exists imdbload
  rm -rf /tmp/imdb && mkdir -p /tmp/imdb
  wget -q -c -O /tmp/imdb.tgz https://event.cwi.nl/da/job/imdb.tgz
  tar xzf /tmp/imdb.tgz -C /tmp/imdb
  pip install -q absl-py
  python /tmp/lqo_ml_perspective/data/prepend_imdb_headers.py --csv_dir /tmp/imdb 2> /dev/null
  chmod -R a+rX /tmp/imdb /tmp/lqo_ml_perspective
  echo "Đang nạp, khoảng 30–45 phút; log ở /tmp/load.log ..."
  su postgres -c "PATH=/opt/pg12/bin:\$PATH PGHOST=localhost bash /tmp/lqo_ml_perspective/balsa/load-postgres/load_job_postgres.sh /tmp/imdb" > /tmp/load.log 2>&1 &
  PID=$!
  while kill -0 $PID 2> /dev/null; do
    sleep 60
    N=$(grep -c '^COPY ' /tmp/load.log || true)
    if grep -q 'ANALYZE VERBOSE' /tmp/load.log; then STEP="ANALYZE (bước cuối)"
    elif grep -q add_fks /tmp/load.log; then STEP="tạo khóa ngoại"
    else STEP="nạp CSV"; fi
    echo "$(date +%H:%M)  đã nạp $N/21 bảng, đang: $STEP"
  done
  wait $PID || { echo "Script nạp dừng vì lỗi:"; tail -20 /tmp/load.log; exit 1; }
  if grep -q ERROR /tmp/load.log; then echo "Có lỗi khi nạp:"; grep ERROR /tmp/load.log | head -10; exit 1; fi
fi
BAD=""
while read -r t n; do
  c=$(psql -d imdbload -At -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM $t" < /dev/null) \
    || { echo "Không đếm được bảng $t"; exit 1; }
  [ "$c" = "$n" ] || BAD+="$t: có $c, cần $n"$'\n'
done <<'EOF'
aka_name 901343
aka_title 361472
cast_info 36244344
char_name 3140339
comp_cast_type 4
company_name 234997
company_type 4
complete_cast 135086
info_type 113
keyword 134170
kind_type 7
link_type 18
movie_companies 2609129
movie_info 14835720
movie_info_idx 1380035
movie_keyword 4523930
movie_link 29997
name 4167491
person_info 2963664
role_type 12
title 2528312
EOF
[ -z "$BAD" ] || { echo "Các bảng sau sai số dòng:"; echo "$BAD"; exit 1; }
echo "Đủ 21 bảng, số dòng khớp."
touch /tmp/imdb_loaded
rm -rf /tmp/imdb /tmp/imdb.tgz''',

# ---------------------------------------------------------------- 4. môi trường Python cho Bao server
r'''%%bash
set -e
pip install -q uv
[ -x /tmp/bao_env/bin/python ] || uv venv -q -p 3.10 /tmp/bao_env
# Giống lqo_ml_perspective/bao/requirements.txt (torch bản CPU)
uv pip install -q --python /tmp/bao_env/bin/python torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install -q --python /tmp/bao_env/bin/python numpy==1.23.5 scikit-learn==1.1.3 scipy==1.9.3 joblib==1.2.0 \
  threadpoolctl==3.1.0 psycopg2-binary==2.9.5
/tmp/bao_env/bin/python -c "import torch, sklearn, psycopg2; print('torch', torch.__version__, '| sklearn', sklearn.__version__)"''',

# ---------------------------------------------------------------- 5. chọn split, chép và vá code Bao
r'''import os, pathlib, re, shutil

SPLIT = "__SPLIT__"
TRAIN_LIMIT_HOURS = 8.5      # phiên Kaggle tối đa 12 giờ: train quá mốc này thì dừng, test bằng model mới nhất

src, run = pathlib.Path("/tmp/lqo_ml_perspective/bao"), pathlib.Path("/tmp/bao_run")
if not run.exists():
    shutil.copytree(src, run)
# Code gốc chạy trong Docker (host pg_bao, Bao server ở 10.5.0.6): trên Kaggle mọi thứ ở localhost
for f in ["run_queries.py", "run_test_queries.py"]:
    p = run / f
    s = p.read_text().replace("host=pg_bao", "host=localhost").replace("'10.5.0.6'", "'localhost'")
    p.write_text(s)
cfg = run / "bao_server/bao.cfg"
s = cfg.read_text()
s = re.sub(r"^ListenOn = .*$", "ListenOn = localhost", s, flags=re.M)
s = re.sub(r"^PostgreSQLConnectString = .*$",
           "PostgreSQLConnectString = dbname='imdbload' user='postgres' password='postgres' host='localhost'", s, flags=re.M)
cfg.write_text(s)
for f in ["run_queries.py", "run_test_queries.py"]:
    t = (run / f).read_text()
    assert "host=pg_bao" not in t and "10.5.0.6" not in t, f"chưa vá được {f}"

OUT = pathlib.Path("/kaggle/working/bao_logs"); OUT.mkdir(parents=True, exist_ok=True)
pathlib.Path("/tmp/bao_vars.sh").write_text(
    f"export SPLIT={SPLIT}\nexport TRAIN_LIMIT_S={int(TRAIN_LIMIT_HOURS * 3600)}\nexport OUT={OUT}\n"
    "export PATH=/tmp/bao_env/bin:/opt/pg12/bin:$PATH PGHOST=localhost PGUSER=postgres\n")
n_tr = len(list((run / f"queries/job__{SPLIT}/train").glob("*.sql")))
n_te = len(list((run / f"queries/job__{SPLIT}/test").glob("*.sql")))
print(f"Split {SPLIT}: {n_tr} câu train, {n_te} câu test → log ở {OUT}")''',

# ---------------------------------------------------------------- 6. làm nóng cache
r'''%%bash
set -e
source /tmp/bao_vars.sh
psql -d imdbload -qc "CREATE EXTENSION IF NOT EXISTS pg_prewarm"
psql -d imdbload -qAt -c "SELECT count(pg_prewarm(c.oid,'read')) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','i')" > /dev/null
T0=$(date +%s)
for f in /tmp/bao_run/queries/join-order-benchmark/*.sql; do
  psql -d imdbload -q -o /dev/null -c "SET statement_timeout = 300000;" -f "$f" || echo "  $(basename $f): lỗi/timeout"
done
echo "Đã làm nóng: chạy mỗi câu JOB một lần trong $(( $(date +%s) - T0 )) giây"''',

# ---------------------------------------------------------------- 7. train Bao
r'''%%bash
source /tmp/bao_vars.sh
cd /tmp/bao_run
start_server() {   # $1 = thư mục model (bỏ trống = chưa có model)
  pkill -f "python -u main.py" 2> /dev/null; sleep 2
  (cd bao_server && nohup python -u main.py $1 >> $OUT/bao_server.log 2>&1 &)
  for _ in $(seq 120); do (exec 3<>/dev/tcp/localhost/9381) 2> /dev/null && return 0; sleep 1; done
  echo "Bao server không lên, xem $OUT/bao_server.log"; tail $OUT/bao_server.log; return 1
}
echo "== Xóa kinh nghiệm và model cũ"
(cd bao_server && python clear_experience.py && rm -rf bao_default_model bao_previous_model)
start_server || exit 1
LOG=$OUT/train__bao__job__$SPLIT.txt; rm -f $LOG
echo "== Train trên queries/job__$SPLIT/train (tối đa $((TRAIN_LIMIT_S / 3600)) giờ); tiến độ: tail -f $OUT/train_console.log"
T0=$(date +%s)
timeout $TRAIN_LIMIT_S python -u run_queries.py --database_name imdbload --query_dir queries/job__$SPLIT/train \
  --output_file $LOG > $OUT/train_console.log 2>&1
RC=$?; T1=$(date +%s)
NOTE=""; [ $RC -eq 124 ] && NOTE=",truncated"
echo "job__$SPLIT,train_seconds,$((T1 - T0))$NOTE" >> $OUT/bao_training_times.csv
grep -o "\[[0-9]*/19\][[:space:]]*Retraining done" $OUT/train_console.log | tail -1
[ -d bao_server/bao_default_model ] || { echo "Không có model sau khi train"; tail -20 $OUT/train_console.log; exit 1; }
rm -rf $OUT/model__bao__job__$SPLIT && cp -r bao_server/bao_default_model $OUT/model__bao__job__$SPLIT
echo "== Train xong sau $(( (T1 - T0) / 60 )) phút${NOTE:+ (bị dừng ở mốc giới hạn thời gian)}"''',

# ---------------------------------------------------------------- 8. test: PostgreSQL rồi Bao, cùng trạng thái cache
r'''%%bash
source /tmp/bao_vars.sh
cd /tmp/bao_run
Q=queries/job__$SPLIT/test
echo "== Baseline PostgreSQL trên $Q (3 lần/câu)"
rm -f $OUT/test__postgres__job__$SPLIT.txt
python -u run_test_queries.py --use_postgres --database_name imdbload --query_dir $Q \
  --output_file $OUT/test__postgres__job__$SPLIT.txt > /dev/null
echo "== Nạp model vào Bao server"
N=$(wc -l < $OUT/bao_server.log)
pkill -f "python -u main.py" 2> /dev/null; sleep 2
(cd bao_server && nohup python -u main.py $OUT/model__bao__job__$SPLIT >> $OUT/bao_server.log 2>&1 &)
for _ in $(seq 120); do tail -n +$((N + 1)) $OUT/bao_server.log | grep -q "Accepted new model" && break; sleep 1; done
tail -n +$((N + 1)) $OUT/bao_server.log | grep -q "Accepted new model" || { echo "Bao server chưa nạp model"; exit 1; }
echo "== Bao trên $Q (3 lần/câu)"
rm -f $OUT/test__bao__job__$SPLIT.txt
python -u run_test_queries.py --use_bao --database_name imdbload --query_dir $Q \
  --output_file $OUT/test__bao__job__$SPLIT.txt > /dev/null
echo "== Xong test"''',

# ---------------------------------------------------------------- 9. tóm tắt
r'''import pandas as pd, re, os, pathlib
OUT = pathlib.Path("/kaggle/working/bao_logs")

def load(path):
    rows = []
    for line in open(path):
        p = [x.strip() for x in line.split(",")]
        if len(p) < 7:
            continue
        q = re.sub(r"^0*", "", os.path.splitext(os.path.basename(p[-4]))[0])
        rows.append({"query": q, "run": int(p[-6]), "ms": float(p[-3]) + float(p[-2])})
    d = pd.DataFrame(rows)
    return d[d.run == 2].set_index("query").ms        # lần chạy thứ 3, giống bài báo

pg = load(OUT / f"test__postgres__job__{SPLIT}.txt")
bao = load(OUT / f"test__bao__job__{SPLIT}.txt")
d = pd.DataFrame({"PG_ms": pg, "Bao_ms": bao}).dropna()
d["speedup"] = d.PG_ms / d.Bao_ms
w, l = int((d.speedup > 1.1).sum()), int((d.speedup < 0.9).sum())
lines = [f"Split {SPLIT}: {len(d)} câu test",
         f"Thắng/Hòa/Thua (±10%): {w}/{len(d) - w - l}/{l}",
         f"PostgreSQL {d.PG_ms.sum() / 1000:.1f} s → Bao {d.Bao_ms.sum() / 1000:.1f} s; "
         f"speedup tổng {d.PG_ms.sum() / d.Bao_ms.sum():.2f}×, trung vị {d.speedup.median():.2f}",
         "Thời gian train: " + open(OUT / "bao_training_times.csv").read().strip().splitlines()[-1]]
(OUT / f"tom_tat__{SPLIT}.txt").write_text("\n".join(lines) + "\n\n" + d.round(1).to_string())
print("\n".join(lines))
print(d.sort_values("speedup").round(2).to_string())''',
]


def build(user, split):
    slug = "bao-job-" + split.replace("_split_", "-").replace("_", "-")
    out = os.path.join(ROOT, "kaggle", slug)
    os.makedirs(out, exist_ok=True)
    cells = [c.replace("__SPLIT__", split) for c in CELLS]
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                       "language_info": {"name": "python"}},
          "cells": [{"id": f"cell-{i}", "cell_type": "code", "metadata": {}, "execution_count": None,
                     "outputs": [], "source": c.splitlines(keepends=True)} for i, c in enumerate(cells)]}
    json.dump(nb, open(os.path.join(out, f"{slug}.ipynb"), "w"), ensure_ascii=False, indent=1)
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": f"{slug}.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    json.dump(meta, open(os.path.join(out, "kernel-metadata.json"), "w"), indent=2)
    print(f"{len(cells)} ô → {os.path.relpath(out, ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--split", choices=ALL_SPLITS)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if not a.split and not a.all:
        ap.error("cần --split hoặc --all")
    for s in (ALL_SPLITS if a.all else [a.split]):
        build(a.user, s)


if __name__ == "__main__":
    main()
