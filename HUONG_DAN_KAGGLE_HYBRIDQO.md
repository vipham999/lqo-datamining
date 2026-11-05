# Hướng dẫn chạy HybridQO trên Kaggle

HybridQO cần GPU NVIDIA: code gọi cứng `torchfold.Fold(cuda=True)` trong `Hinter.py` và `NET.py`, nên không chạy được trên MacBook M1.
Kaggle cho dùng GPU miễn phí. Hướng dẫn này dựng lại môi trường giống container `pg_balsa` của tác giả nhưng không dùng Docker,
vì Kaggle không chạy được Docker.

| Thành phần | Tác giả (`docker/postgres_balsa`) | Trên Kaggle |
|---|---|---|
| PostgreSQL | 12.5 | 12.5, build từ mã nguồn |
| pg_hint_plan | `REL12_1_3_7` | Giống tác giả |
| Nạp IMDB | `balsa/load-postgres/load_job_postgres.sh` | Giống tác giả |
| Python | 3.10 (vì `psqlparse` không cài được trên 3.11) | 3.10, tạo bằng `uv` |
| PyTorch | 1.13.1 | 1.13.1 bản CUDA 11.7 |
| `shared_buffers` / `work_mem` | 32 GB / 4 GB | 8 GB / 512 MB (máy Kaggle chỉ có khoảng 30 GB RAM) |
| Số epoch | 50 (khoảng 20 giờ/split) | Dừng theo ngân sách thời gian (mặc định 8,5 giờ) vì mỗi phiên Kaggle tối đa 12 giờ |

> Hai dòng cuối là chỗ **khác bài báo**, cần ghi rõ trong báo cáo.

---

## Bước 0. Chuẩn bị tài khoản và notebook

1. Đăng ký Kaggle và **xác minh số điện thoại** (Settings → Phone verification). Chưa xác minh thì không bật được GPU và Internet.
2. Vào **Create → New Notebook**.
3. Ở khung bên phải, mục **Session options**:
   - **Accelerator:** `GPU T4 x2` (hoặc `GPU P100`)
   - **Internet:** bật **On**
4. Mỗi ô dưới đây là một cell trong notebook. Các ô bắt đầu bằng `%%bash` chạy lệnh shell.

Giới hạn cần nhớ:
- Mỗi phiên tối đa **12 giờ**. Hết giờ thì máy bị xóa sạch, kể cả CSDL đã nạp.
- Khoảng **30 giờ GPU mỗi tuần**.
- Chỉ thư mục `/kaggle/working` (tối đa 20 GB) được giữ lại sau phiên. Vì vậy CSDL và môi trường để ở `/tmp`, còn log thì ghi vào `/kaggle/working`.

---

## Ô 1. Kiểm tra máy

```bash
%%bash
nvidia-smi --query-gpu=name,memory.total --format=csv
nproc; free -g | head -2
df -h /tmp /kaggle/working
```

Cần thấy GPU (T4 hoặc P100), khoảng 30 GB RAM, và `/tmp` còn trống **ít nhất 25 GB** (12 GB cho CSDL, khoảng 5 GB cho CSV, phần còn lại cho môi trường Python).
Nếu `/tmp` không đủ thì thay `/tmp` bằng thư mục có nhiều chỗ trống nhất trong các ô sau.

---

## Ô 2. Build PostgreSQL 12.5 và pg_hint_plan (khoảng 10 phút)

```bash
%%bash
set -e
LOG=/tmp/pg_build.log; : > $LOG
# Toàn bộ output (kể cả warning) ghi vào $LOG; chỉ khi lỗi mới in 30 dòng cuối
run() { "$@" >> $LOG 2>&1 || { echo "LỖI khi chạy: $*"; tail -30 $LOG; exit 1; }; }

run apt-get update -qq
run apt-get install -y -qq build-essential libreadline-dev zlib1g-dev

cd /tmp
run wget -q https://ftp.postgresql.org/pub/source/v12.5/postgresql-12.5.tar.gz
tar xzf postgresql-12.5.tar.gz && cd postgresql-12.5
run ./configure --prefix=/opt/pg12
run make -j"$(nproc)"
run make install

cd /tmp
run git -c advice.detachedHead=false clone -q -b REL12_1_3_7 https://github.com/ossc-db/pg_hint_plan.git
cd pg_hint_plan
run make PG_CONFIG=/opt/pg12/bin/pg_config
run make PG_CONFIG=/opt/pg12/bin/pg_config install

/opt/pg12/bin/postgres --version
ls /opt/pg12/lib/pg_hint_plan.so > /dev/null && echo "pg_hint_plan OK"
```

Nếu thành công, ô chỉ in hai dòng là `postgres (PostgreSQL) 12.5` và `pg_hint_plan OK`.
Nếu có lỗi, ô in `LỖI khi chạy: ...` kèm 30 dòng cuối của log. Log đầy đủ nằm ở `/tmp/pg_build.log`.

> Trong log sẽ có các cảnh báo kiểu `Without Bison/Flex`, `warning: ... [-Wstringop-overflow]`, `detached HEAD`, `Skipping acquire ... r2u`. Đây là cảnh báo bình thường: bản tarball đã có sẵn file parser, còn GCC mới hay cảnh báo trên code PG 12.5. Các cảnh báo này **không** phải lỗi.

---

## Ô 3. Khởi tạo và bật PostgreSQL

PostgreSQL không cho chạy bằng tài khoản `root`, nên tạo user `postgres` riêng.

```bash
%%bash
set -e
id -u postgres > /dev/null 2>&1 || useradd -m -s /bin/bash postgres
mkdir -p /tmp/pgdata && chown postgres /tmp/pgdata
su postgres -c "/opt/pg12/bin/initdb -D /tmp/pgdata -U postgres --auth=trust" > /dev/null

# Cấu hình theo conf/balsa-postgresql.conf của tác giả, giảm bộ nhớ cho vừa máy Kaggle
cat >> /tmp/pgdata/postgresql.conf <<'EOF'
listen_addresses = 'localhost'
shared_buffers = 8GB
temp_buffers = 1GB
work_mem = 512MB
effective_cache_size = 20GB
max_parallel_workers_per_gather = 4
max_parallel_maintenance_workers = 4
geqo = off
autovacuum = off
shared_preload_libraries = 'pg_hint_plan'
dynamic_shared_memory_type = mmap
EOF
su postgres -c "/opt/pg12/bin/pg_ctl -D /tmp/pgdata -l /tmp/pg.log start -w"
/opt/pg12/bin/psql -U postgres -h localhost -c "SHOW shared_buffers;"
```

- `dynamic_shared_memory_type = mmap` tránh lỗi `could not resize shared memory segment`. Lỗi này hay gặp khi `/dev/shm` nhỏ, như trên Kaggle.
- `work_mem` để 512 MB thay vì 4 GB như tác giả. Với 4 GB, một truy vấn nhiều phép nối chạy song song có thể dùng quá 30 GB RAM và làm notebook bị tắt.

---

## Ô 4. Tải và nạp IMDB (khoảng 30–45 phút)

Ô này **chạy lại được nhiều lần**:
- Nếu lần trước đã nạp xong (có file đánh dấu `/tmp/imdb_loaded`), ô bỏ qua bước nạp.
- Nếu chưa, ô xóa CSDL và CSV còn dở, rồi nạp lại từ đầu.

Phải nạp lại từ đầu vì `prepend_imdb_headers.py` chạy lần hai sẽ chèn thêm một dòng tiêu đề nữa, và `createdb` sẽ báo lỗi nếu CSDL đã tồn tại.

```bash
%%bash
set -e
export PATH=/opt/pg12/bin:$PATH PGHOST=localhost PGUSER=postgres

# Mã nguồn của tác giả: script nạp IMDB, code HybridQO và các split
[ -d /tmp/lqo_ml_perspective ] || git clone -q https://github.com/edualc/lqo_ml_perspective.git /tmp/lqo_ml_perspective

if [ -f /tmp/imdb_loaded ]; then
  echo "IMDB đã nạp từ trước, bỏ qua."
else
  # Dọn phần dở dang của lần chạy trước
  dropdb --if-exists imdbload
  rm -rf /tmp/imdb && mkdir -p /tmp/imdb

  # Dữ liệu IMDB của JOB (link cũ homepages.cwi.nl/~boncz/job đã 404); giữ file nén để lần sau khỏi tải lại
  wget -q -c -O /tmp/imdb.tgz https://event.cwi.nl/da/job/imdb.tgz
  tar xzf /tmp/imdb.tgz -C /tmp/imdb

  # Thêm dòng tiêu đề cột vào các file CSV (script của tác giả)
  pip install -q absl-py
  python /tmp/lqo_ml_perspective/data/prepend_imdb_headers.py --csv_dir /tmp/imdb 2> /dev/null
  chmod -R a+rX /tmp/imdb /tmp/lqo_ml_perspective

  # Nạp vào PostgreSQL: tạo bảng, nạp CSV, tạo index, ANALYZE (script của tác giả)
  echo "Đang nạp, khoảng 30–45 phút; log ở /tmp/load.log ..."
  su postgres -c "PATH=/opt/pg12/bin:\$PATH PGHOST=localhost bash /tmp/lqo_ml_perspective/balsa/load-postgres/load_job_postgres.sh /tmp/imdb" > /tmp/load.log 2>&1

  # Script chạy các lệnh \copy ở nền nên lỗi của chúng không làm dừng script: phải tự tìm trong log
  if grep -q ERROR /tmp/load.log; then
    echo "Có lỗi khi nạp:"; grep ERROR /tmp/load.log | head -10; exit 1
  fi
fi

# Đếm chính xác (count(*)) số dòng của cả 21 bảng, so với số chuẩn của IMDB bản JOB (khoảng 1–2 phút)
BAD=$(psql -d imdbload -At <<'EOF'
WITH expected(t, n) AS (VALUES
 ('aka_name',901343),('aka_title',361472),('cast_info',36244344),('char_name',3140339),
 ('comp_cast_type',4),('company_name',234997),('company_type',4),('complete_cast',135086),
 ('info_type',113),('keyword',134170),('kind_type',7),('link_type',18),
 ('movie_companies',2609129),('movie_info',14835720),('movie_info_idx',1380035),
 ('movie_keyword',4523930),('movie_link',29997),('name',4167491),('person_info',2963664),
 ('role_type',12),('title',2528312))
, actual AS (
  SELECT t, n, (xpath('/row/c/text()',
           query_to_xml('SELECT count(*) AS c FROM ' || t, false, true, '')))[1]::text::bigint AS c
  FROM expected)
SELECT t || ': có ' || c || ', cần ' || n FROM actual WHERE c <> n;
EOF
)
if [ -n "$BAD" ]; then
  echo "Các bảng sau sai số dòng:"; echo "$BAD"; exit 1
fi
echo "Đủ 21 bảng, số dòng khớp."

touch /tmp/imdb_loaded
rm -rf /tmp/imdb /tmp/imdb.tgz   # xóa CSV và file nén cho đỡ tốn chỗ
```

Nếu thành công, dòng cuối là `Đủ 21 bảng, số dòng khớp.`

> Ô đếm bằng `count(*)`, không dùng `n_live_tup` trong `pg_stat_user_tables`. Lý do: với bảng lớn, `ANALYZE` chỉ lấy mẫu nên `n_live_tup` chỉ là số ước lượng, có thể lệch khoảng 0,1%.
> Nếu một bảng báo thiếu dòng thật, hãy xem lỗi trong `/tmp/load.log`.

Kiểm tra `pg_hint_plan` hoạt động:

```bash
%%bash
/opt/pg12/bin/psql -U postgres -h localhost -d imdbload -c "/*+ MergeJoin(t mc) */ EXPLAIN SELECT count(*) FROM title t, movie_companies mc WHERE t.id = mc.movie_id;" | grep -i "join"
```

Kết quả phải có **Merge Join**. Nếu có, nghĩa là hint của `pg_hint_plan` đã có tác dụng.

---

## Ô 5. Tạo môi trường Python 3.10 cho HybridQO (khoảng 5 phút)

```bash
%%bash
set -e
pip install -q uv
uv venv -q -p 3.10 /tmp/hqo_env
uv pip install -q --python /tmp/hqo_env/bin/python torch==1.13.1 --index-url https://download.pytorch.org/whl/cu117
uv pip install -q --python /tmp/hqo_env/bin/python "numpy<2" psqlparse==1.0rc7 torchfold psycopg2-binary wandb tqdm
/tmp/hqo_env/bin/python -c "import torch, psqlparse, torchfold; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Phải in ra `CUDA: True Tesla T4` (hoặc `Tesla P100…`).

- `numpy<2` là bắt buộc vì PyTorch 1.13 không chạy với NumPy 2.
- Nếu `psqlparse` báo lỗi khi build, chạy `apt-get install -y python3-dev` rồi cài lại.

---

## Ô 6. Cấu hình HybridQO cho JOB

Trong repo, `ImportantConfig.py` đang để **STACK**. Ô này bật lại khối cấu hình JOB của tác giả, chọn split và trỏ tới PostgreSQL trên máy.
Ô cũng vá `run_mcts.py` để **tự dừng train khi hết ngân sách thời gian**, sau đó vẫn chạy bước test cuối. Nhờ vậy phiên 12 giờ không bị cắt ngang giữa chừng làm mất kết quả.

```python
import pathlib, re

SPLIT = "leave_one_out_split_1"   # đổi thành base_query_split_1, random_split_1, ...
N_EPOCHS = 50                     # như tác giả; train sẽ dừng sớm nếu hết ngân sách thời gian

hq = pathlib.Path("/tmp/lqo_ml_perspective/hybrid_qo")

# 1) ImportantConfig.py: lấy 5 dòng cấu hình JOB đang bị comment, chèn trước dòng tính mcts_input_size
cfg = hq / "ImportantConfig.py"
lines = cfg.read_text().splitlines()
start = next(i for i, l in enumerate(lines) if l.strip() == "# JOB")
job = [l.strip().replace("# self.", "self.", 1) for l in lines[start:start + 8] if l.strip().startswith("# self.")]
assert len(job) == 5, job
extra = job + [f"self.n_epochs = {N_EPOCHS}",
               f"self.queries_file = 'workload/JOB__{SPLIT}__train.json'",
               "self.ip = 'localhost'"]
idx = next(i for i, l in enumerate(lines) if "self.mcts_input_size" in l)
indent = re.match(r"\s*", lines[idx]).group()
lines[idx:idx] = [indent + l for l in extra]
cfg.write_text("\n".join(lines) + "\n")

# 2) run_mcts.py: dừng train khi hết ngân sách thời gian (biến môi trường HQO_BUDGET_H, đơn vị giờ)
run = hq / "run_mcts.py"
s = run.read_text()
loop = "    for epoch in tqdm(range(config.n_epochs), total=config.n_epochs, desc='Iterating over epochs...'):\n"
guard = ("        if time.time() - _START > float(os.environ.get('HQO_BUDGET_H', '8.5')) * 3600:\n"
         "            print('Het ngan sach thoi gian, dung train o epoch', epoch, flush=True)\n"
         "            break\n")
assert loop in s
if guard not in s:
    s = s.replace("import random\n", "import random\nimport os, time\n_START = time.time()\n", 1)
    s = s.replace(loop, loop + guard, 1)
run.write_text(s)

print("\n".join(extra))
```

---

## Ô 7. Chạy HybridQO

```bash
%%bash
cd /tmp/lqo_ml_perspective/hybrid_qo
mkdir -p model /kaggle/working/hqo_logs
rm -rf logs && ln -s /kaggle/working/hqo_logs logs   # log ghi thẳng vào thư mục được giữ lại

export WANDB_MODE=disabled      # không cần tài khoản Weights & Biases
export HQO_BUDGET_H=8.5         # tổng thời gian tối đa cho phần train (giờ)
/tmp/hqo_env/bin/python run_mcts.py 2>&1 | tee /kaggle/working/run_mcts.out | grep -v "it/s"
```

`HQO_BUDGET_H` được tính từ lúc `run_mcts.py` bắt đầu. Các ô 1–6 mất khoảng 1–1,5 giờ, nên 8,5 giờ train cộng thời gian test cuối vẫn nằm trong 12 giờ.
Tăng giảm con số này tùy tốc độ thực tế.

---

## Bước cuối. Chạy thật bằng chế độ Commit

Không nên train trong phiên tương tác, vì phiên sẽ ngắt khi bạn đóng trình duyệt hoặc để máy rảnh lâu.

1. Chạy thử các ô 1–6 trong phiên tương tác để chắc không có lỗi. Có thể chạy thử ô 7 với `HQO_BUDGET_H=0.3` để xem vòng lặp chạy được.
2. Bấm **Save Version → Save & Run All (Commit)**. Kaggle chạy toàn bộ notebook từ đầu đến cuối ở chế độ nền, tối đa 12 giờ, bạn tắt máy cũng không sao.
3. Khi xong, vào tab **Output** của phiên bản đó và tải về:
   - `hqo_logs/<thời_gian>__query_log.csv`: log chính
   - `run_mcts.out`: toàn bộ output

---

## Đọc kết quả

Mỗi dòng của `query_log.csv` có các cột:

| Cột | Ý nghĩa |
|---|---|
| `epoch` | Epoch thứ mấy |
| `test_query` | 0 = truy vấn train, 1 = truy vấn test |
| `query_ident` | Tên truy vấn |
| `pg_latency` | Thời gian chạy với plan **PostgreSQL**, đo trên cùng máy Kaggle |
| `hinter_latency` | Thời gian chạy với plan **HybridQO** chọn |
| `mcts_time`, `hinter_plan_time`, `MPHE_time` | Thời gian HybridQO tìm kiếm và lập plan |
| `hinter_query_ratio` | `pg_latency / thời gian HybridQO`; lớn hơn 1 nghĩa là HybridQO nhanh hơn |

Vì log ghi cả thời gian PostgreSQL lẫn thời gian HybridQO **trên cùng một máy**, có thể so trực tiếp hai bên mà không cần chạy baseline riêng.
Lấy các dòng `test_query = 1` ở **epoch cuối**, tính thắng/hòa/thua với ngưỡng ±10% như phần Bao, rồi so với log của tác giả cho cùng split.

**Không so trực tiếp** thời gian đo trên Kaggle với thời gian đo trên máy Mac của nhóm. Hai máy khác nhau, và máy Kaggle dùng chung tài nguyên nên số đo dao động nhiều hơn.

---

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| Không bật được GPU/Internet | Chưa xác minh số điện thoại |
| `initdb: cannot be run as root` | Phải chạy qua `su postgres -c ...` như ô 3 |
| `could not resize shared memory segment` | Kiểm tra đã có `dynamic_shared_memory_type = mmap` |
| Notebook tự khởi động lại giữa chừng | Hết RAM: giảm `work_mem` hoặc `max_parallel_workers_per_gather` ở ô 3 |
| `psqlparse` không cài được | Kiểm tra môi trường đúng là Python 3.10 (`/tmp/hqo_env/bin/python --version`) |
| `RuntimeError: ... CUDA` | Chưa bật GPU trong Session options |
| Phiên hết 12 giờ trước khi xong | Giảm `HQO_BUDGET_H` |
