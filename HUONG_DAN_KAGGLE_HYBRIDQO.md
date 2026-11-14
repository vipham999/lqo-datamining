# Hướng dẫn chạy HybridQO trên Kaggle

Code gốc của HybridQO gọi cứng CUDA (`torchfold.py`, `mcts.py`), nên không chạy được trên MacBook M1. Ô 6 vá để chạy được cả trên máy không có GPU (chưa chạy thử thật trên CPU, xem mục "GPU hay CPU?").
Kaggle cho dùng máy (kể cả GPU) miễn phí. Hướng dẫn này dựng lại môi trường giống container `pg_balsa` của tác giả nhưng không dùng Docker,
vì Kaggle không chạy được Docker.

| Thành phần | Tác giả (`docker/postgres_balsa`) | Trên Kaggle |
|---|---|---|
| PostgreSQL | 12.5 | 12.5, build từ mã nguồn |
| pg_hint_plan | `REL12_1_3_7` | Giống tác giả |
| Nạp IMDB | `balsa/load-postgres/load_job_postgres.sh` | Giống tác giả |
| Python | 3.10 (vì `psqlparse` không cài được trên 3.11) | 3.10, tạo bằng `uv` |
| PyTorch | 1.13.1 | 1.13.1 bản CUDA 11.7 |
| `shared_buffers` / `work_mem` | 32 GB / 4 GB | 8 GB / 512 MB (máy Kaggle chỉ có khoảng 30 GB RAM) |
| `temp_buffers` / `effective_cache_size` | 32 GB / 32 GB | Giống tác giả (không chiếm RAM, xem ô 3) |
| Số epoch | 50, test ở epoch 0, 10, …, 40 và 49; mỗi split chạy 3 lần (`__0`, `__1`, `__2`) | 11, test ở epoch 0 và 10 (khoảng 7–10 giờ/split); mỗi split chạy 1 lần (`__0`) vì mỗi phiên Kaggle tối đa 12 giờ |

> Dòng `shared_buffers` / `work_mem` và dòng số epoch là chỗ **khác bài báo**, cần ghi rõ trong báo cáo.

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
nvidia-smi --query-gpu=name,memory.total --format=csv 2> /dev/null || echo "Không có GPU: chạy bằng CPU"
nproc; free -g | head -2
df -h /tmp /kaggle/working
```

Có GPU (T4 hoặc P100) hoặc không đều được: HybridQO gần như không dùng GPU (xem mục chọn split ở cuối). Cần khoảng 30 GB RAM và `/tmp` còn trống **ít nhất 25 GB** (12 GB cho CSDL, khoảng 5 GB cho CSV, phần còn lại cho môi trường Python).
Nếu `/tmp` không đủ thì thay `/tmp` bằng thư mục có nhiều chỗ trống nhất trong các ô sau.

---

## Ô 2. Build PostgreSQL 12.5 và pg_hint_plan (khoảng 10 phút)

```bash
%%bash
set -e
LOG=/tmp/pg_build.log; : > $LOG
# Toàn bộ output (kể cả warning) ghi vào $LOG; chỉ khi lỗi mới in 30 dòng cuối
run() { "$@" >> $LOG 2>&1 || { echo "LỖI khi chạy: $*"; tail -30 $LOG; exit 1; }; }

if [ -x /opt/pg12/bin/pg_config ] && [ -f "$(/opt/pg12/bin/pg_config --pkglibdir)/pg_hint_plan.so" ]; then
  echo "Đã build từ trước, bỏ qua."
else
  run apt-get update -qq
  run apt-get install -y -qq build-essential libreadline-dev zlib1g-dev

  # Xóa mã nguồn còn lại từ lần chạy trước (nếu không, git clone báo "already exists")
  cd /tmp
  rm -rf postgresql-12.5 postgresql-12.5.tar.gz pg_hint_plan
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
fi

/opt/pg12/bin/postgres --version
# Prefix không chứa "postgres"/"pgsql" nên PG đặt extension trong lib/postgresql/: hỏi đúng chỗ qua pg_config
PKG=$(/opt/pg12/bin/pg_config --pkglibdir)
[ -f "$PKG/pg_hint_plan.so" ] || { echo "Không thấy pg_hint_plan.so trong $PKG"; exit 1; }
echo "pg_hint_plan OK"
```

Nếu thành công, ô in `postgres (PostgreSQL) 12.5` và `pg_hint_plan OK` (chạy lại thì có thêm dòng `Đã build từ trước, bỏ qua.`).
Nếu có lỗi, ô in `LỖI khi chạy: ...` kèm 30 dòng cuối của log. Log đầy đủ nằm ở `/tmp/pg_build.log`.

> Trong log sẽ có các cảnh báo kiểu `Without Bison/Flex`, `warning: ... [-Wstringop-overflow]`, `detached HEAD`, `Skipping acquire ... r2u`. Đây là cảnh báo bình thường: bản tarball đã có sẵn file parser, còn GCC mới hay cảnh báo trên code PG 12.5. Các cảnh báo này **không** phải lỗi.

---

## Ô 3. Khởi tạo và bật PostgreSQL

PostgreSQL không cho chạy bằng tài khoản `root`, nên tạo user `postgres` riêng.
Ô này chạy lại được: nếu đã khởi tạo thì bỏ qua `initdb`, nếu server đang chạy thì không bật lại.

```bash
%%bash
set -e
id -u postgres > /dev/null 2>&1 || useradd -m -s /bin/bash postgres

if [ ! -f /tmp/pgdata/PG_VERSION ]; then
mkdir -p /tmp/pgdata && chown postgres /tmp/pgdata
su postgres -c "/opt/pg12/bin/initdb -D /tmp/pgdata -U postgres --auth=trust" > /dev/null

# Cấu hình theo conf/balsa-postgresql.conf của tác giả, giảm bộ nhớ cho vừa máy Kaggle
cat >> /tmp/pgdata/postgresql.conf <<'EOF'
listen_addresses = 'localhost'
shared_buffers = 8GB
temp_buffers = 32GB
work_mem = 512MB
effective_cache_size = 32GB
max_parallel_workers_per_gather = 4
max_parallel_maintenance_workers = 4
geqo = off
autovacuum = off
shared_preload_libraries = 'pg_hint_plan'
dynamic_shared_memory_type = mmap
EOF
fi

su postgres -c "/opt/pg12/bin/pg_ctl -D /tmp/pgdata status" > /dev/null \
  || su postgres -c "/opt/pg12/bin/pg_ctl -D /tmp/pgdata -l /tmp/pg.log start -w"
/opt/pg12/bin/psql -U postgres -h localhost -c "SHOW shared_buffers;"
```

- `dynamic_shared_memory_type = mmap` tránh lỗi `could not resize shared memory segment`. Lỗi này hay gặp khi `/dev/shm` nhỏ, như trên Kaggle.
- `work_mem` để 512 MB thay vì 4 GB như tác giả. Với 4 GB, một truy vấn nhiều phép nối chạy song song có thể dùng quá 30 GB RAM và làm notebook bị tắt.
- `temp_buffers` và `effective_cache_size` để **32 GB như bài báo** (Bảng 2, cột "Khung của chúng tôi"), dù máy chỉ có khoảng 30 GB RAM. Hai tham số này không giữ RAM: `temp_buffers` chỉ cấp khi dùng bảng tạm (JOB không dùng), còn `effective_cache_size` chỉ là con số khai báo cho optimizer khi ước lượng cost. Đặt đúng như bài báo để optimizer chọn plan giống máy tác giả. Riêng `shared_buffers` và `work_mem` thì chiếm RAM thật nên phải giảm.
- Split LOO-1 đầu tiên (`logs/kaggle/hybridqo/leave_one_out_split_1/`) chạy với cấu hình cũ (`temp_buffers = 1GB`, `effective_cache_size = 20GB`). Các split chạy sau dùng cấu hình mới này; khi viết báo cáo cần ghi chú khác biệt đó.

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

# Phiên Kaggle mới thì /opt và /tmp bị xóa sạch: phải chạy lại ô 2 và ô 3 trước
[ -x /opt/pg12/bin/psql ] || { echo "Chưa có PostgreSQL ở /opt/pg12 (phiên Kaggle mới?): chạy lại ô 2 rồi ô 3."; exit 1; }
pg_isready -q || { echo "PostgreSQL chưa chạy: chạy lại ô 3."; exit 1; }
# Lần chạy trước vẫn đang nạp (vd. trang bị tải lại giữa chừng): không được xóa CSDL đang nạp dở
if pgrep -f load_job_postgres.sh > /dev/null; then
  echo "Lần chạy trước vẫn đang nạp. Xem tiến độ: tail /tmp/load.log. Đợi xong rồi chạy lại ô 4."; exit 1
fi

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
  su postgres -c "PATH=/opt/pg12/bin:\$PATH PGHOST=localhost bash /tmp/lqo_ml_perspective/balsa/load-postgres/load_job_postgres.sh /tmp/imdb" > /tmp/load.log 2>&1 &
  PID=$!
  # In tiến độ mỗi phút: mỗi bảng nạp xong, psql ghi một dòng "COPY <số dòng>" vào log
  while kill -0 $PID 2> /dev/null; do
    sleep 60
    N=$(grep -c '^COPY ' /tmp/load.log || true)
    if grep -q 'ANALYZE VERBOSE' /tmp/load.log; then STEP="ANALYZE (bước cuối)"
    elif grep -q add_fks /tmp/load.log; then STEP="tạo khóa ngoại"
    else STEP="nạp CSV"; fi
    echo "$(date +%H:%M)  đã nạp $N/21 bảng, đang: $STEP"
  done
  wait $PID || { echo "Script nạp dừng vì lỗi:"; tail -20 /tmp/load.log; exit 1; }

  # Script chạy các lệnh \copy ở nền nên lỗi của chúng không làm dừng script: phải tự tìm trong log
  if grep -q ERROR /tmp/load.log; then
    echo "Có lỗi khi nạp:"; grep ERROR /tmp/load.log | head -10; exit 1
  fi
fi

# Đếm chính xác (count(*)) số dòng của cả 21 bảng, so với số chuẩn của IMDB bản JOB (khoảng 1–2 phút).
# ON_ERROR_STOP để lỗi SQL làm ô dừng thật (mặc định psql vẫn trả mã 0 khi câu lệnh lỗi).
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
if [ -n "$BAD" ]; then
  echo "Các bảng sau sai số dòng:"; echo "$BAD"; exit 1
fi
echo "Đủ 21 bảng, số dòng khớp."

touch /tmp/imdb_loaded
rm -rf /tmp/imdb /tmp/imdb.tgz   # xóa CSV và file nén cho đỡ tốn chỗ
```

Trong lúc nạp, cứ mỗi phút ô in một dòng tiến độ, ví dụ `14:05  đã nạp 12/21 bảng, đang: nạp CSV`.
Nếu thành công, dòng cuối là `Đủ 21 bảng, số dòng khớp.`

> Trong phiên tương tác, notebook chỉ chạy **một ô một lúc**. Ô mới tạo trong lúc ô 4 đang chạy sẽ phải xếp hàng chờ, nên không dùng được để xem log. Hãy xem dòng tiến độ ngay trong output của ô 4, hoặc xem biểu đồ CPU/RAM/Disk ở khung bên phải.

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
[ -x /tmp/hqo_env/bin/python ] || uv venv -q -p 3.10 /tmp/hqo_env   # chạy lại thì giữ môi trường cũ
uv pip install -q --python /tmp/hqo_env/bin/python torch==1.13.1 --index-url https://download.pytorch.org/whl/cu117
uv pip install -q --python /tmp/hqo_env/bin/python "numpy<2" psqlparse==1.0rc7 torchfold psycopg2-binary wandb tqdm
/tmp/hqo_env/bin/python -c "import torch, psqlparse, torchfold; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'chay bang CPU')"
```

Phải in ra `CUDA: True Tesla T4` (máy GPU) hoặc `CUDA: False chay bang CPU` (máy CPU).

- `numpy<2` là bắt buộc vì PyTorch 1.13 không chạy với NumPy 2.
- Nếu `psqlparse` báo lỗi khi build, chạy `apt-get install -y python3-dev` rồi cài lại.

---

## Ô 6. Cấu hình HybridQO cho JOB

Trong repo, `ImportantConfig.py` đang để **STACK**. Ô này bật lại khối cấu hình JOB của tác giả, chọn split và trỏ tới PostgreSQL trên máy.
Mọi siêu tham số khác (`max_time_out` 3 phút, `try_hint_num`, `mcts_v`, `searchFactor`, seed 113, …) giữ nguyên như tác giả.
Ô cũng vá thêm:

- `run_mcts.py`: **tự dừng train khi hết ngân sách thời gian**, sau đó vẫn chạy bước test cuối, nên phiên 12 giờ không bị cắt ngang làm mất kết quả.
- `run_mcts.py`: **bỏ lần test cuối nếu epoch cuối vừa được test** (epoch 10 khi `N_EPOCHS = 11`). Nếu không bỏ, epoch 10 sẽ có 80 + 33 + 33 dòng thay vì 113, và notebook `FullEvaluation_JOB_MergeResultFiles.ipynb` của tác giả (chỉ lấy epoch có **đúng 113 dòng**) sẽ chọn nhầm epoch 0.
- `torchfold.py`, `mcts.py`: chỉ dùng CUDA khi máy có GPU. Code gốc gọi cứng `torch.cuda.LongTensor` và `predictionNet.cuda()`, nên máy CPU sẽ lỗi. Trên máy GPU, bản vá này không đổi gì.

Ô này chạy lại được (ví dụ để đổi split): mỗi lần chạy, các file được khôi phục về bản gốc rồi mới vá.

```python
import pathlib, re, subprocess

SPLIT = "leave_one_out_split_2"   # leave_one_out_split_1 đã chạy xong (logs/kaggle/hybridqo/leave_one_out_split_1/)
REP = 0                           # lần chạy thứ mấy; tên file kết quả là hybrid_qo__JOB__<SPLIT>__<REP>.csv như tác giả
N_EPOCHS = 11                     # epoch 0..10: test ở epoch 0 và 10, so được với mốc epoch 10 của tác giả (xem "Vì sao 11 epoch")

hq = pathlib.Path("/tmp/lqo_ml_perspective/hybrid_qo")
PATCHED = ["ImportantConfig.py", "run_mcts.py", "torchfold.py", "mcts.py"]

# 0) Khôi phục bản gốc để không vá chồng lên lần chạy trước
subprocess.run(["git", "-C", str(hq.parent), "checkout", "--"] + [f"hybrid_qo/{f}" for f in PATCHED], check=True)

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

# 3) Không test lại nếu epoch cuối vừa test (giữ epoch 10 đúng 113 dòng như log tác giả)
in_loop = "            test_epoch(hinter, test_queries, epoch, query_log_file_path)\n"
final = "    # Final eval\n    test_epoch(hinter, test_queries, epoch, query_log_file_path)\n"
assert in_loop in s and final in s
s = s.replace(loop, "    _last_test = None\n" + loop, 1)
s = s.replace(in_loop, in_loop + "            _last_test = epoch\n", 1)
s = s.replace(final, "    # Final eval\n    if _last_test != epoch:\n"
                     "        test_epoch(hinter, test_queries, epoch, query_log_file_path)\n", 1)
run.write_text(s)

# 4) Chỉ dùng CUDA khi có GPU (code gốc gọi cứng cuda, máy CPU sẽ lỗi)
tf = hq / "torchfold.py"
t = tf.read_text()
assert t.count("        self._cuda = cuda\n") == 2
tf.write_text(t.replace("        self._cuda = cuda\n", "        self._cuda = cuda and torch.cuda.is_available()\n")
               .replace("        self._cuda = True\n", "        self._cuda = torch.cuda.is_available()\n"))
mc = hq / "mcts.py"
m = mc.read_text()
assert m.count("        predictionNet.cuda()\n") == 2
mc.write_text(m.replace("        predictionNet.cuda()\n", "        predictionNet.to(config.device)\n"))

# Cho các ô %%bash phía sau biết split và lần chạy
import os
os.environ["HQO_SPLIT"], os.environ["HQO_REP"] = SPLIT, str(REP)

print("\n".join(extra))
print("Kết quả sẽ lưu thành:", f"hybrid_qo__JOB__{SPLIT}__{REP}.csv")
```

---

## Ô 7. Chạy HybridQO, xem log trực tiếp và lưu kết quả

Ô này làm ba việc:

1. Chạy `run_mcts.py` ở nền. Output đầy đủ ghi vào `/kaggle/working/run_mcts__<SPLIT>__<REP>.out`.
2. **In log trực tiếp:** mỗi câu chạy xong in một dòng (epoch, train/test, tên câu, thời gian PostgreSQL, thời gian HybridQO, tỉ lệ). Hết mỗi lượt train hoặc test của một epoch thì in một dòng tổng kết: tổng thời gian, speedup, thắng/hòa/thua với ngưỡng ±10%.
3. Khi chạy xong, **lưu kết quả theo tên file của tác giả**: `/kaggle/working/wandb_export/hybrid_qo__JOB__<SPLIT>__<REP>.csv`.

```bash
%%bash
[ -x /tmp/hqo_env/bin/python ] || { echo "Chưa có môi trường Python: notebook thiếu ô 5 hoặc ô 5 lỗi"; exit 1; }
[ -n "$HQO_SPLIT" ] || { echo "Chưa chạy ô 6"; exit 1; }
cd /tmp/lqo_ml_perspective/hybrid_qo
mkdir -p model /kaggle/working/hqo_logs
rm -rf logs && ln -s /kaggle/working/hqo_logs logs   # log ghi thẳng vào thư mục được giữ lại
OUT="/kaggle/working/run_mcts__${HQO_SPLIT}__${HQO_REP}.out"

export WANDB_MODE=disabled      # không cần tài khoản Weights & Biases
export HQO_BUDGET_H=10          # chốt an toàn; bình thường 11 epoch xong trước (6,5–9,5 giờ)
touch /tmp/hqo_start
/tmp/hqo_env/bin/python run_mcts.py > "$OUT" 2>&1 &
PID=$!
echo "Bắt đầu $(date +%H:%M), split $HQO_SPLIT, lần chạy $HQO_REP. Output đầy đủ: $OUT"

# Đợi run_mcts.py tạo file query_log của lần chạy này
LOG=""
while [ -z "$LOG" ] && kill -0 $PID 2> /dev/null; do
  sleep 5
  LOG=$(find /kaggle/working/hqo_logs -name '*__query_log.csv' -newer /tmp/hqo_start | head -1)
done

# In từng dòng log khi được ghi; tail tự dừng khi run_mcts.py kết thúc
if [ -n "$LOG" ]; then
  tail -n +2 -f --pid=$PID "$LOG" | awk -F, '
    function summary() {
      if (n) printf "=== %s epoch %s xong lúc %s: %d câu | PG %.1fs | HybridQO %.1fs | speedup %.3f | thắng/hòa/thua %d/%d/%d ===\n",
                    kind, ep, now(), n, spg, sh, (sh > 0 ? spg / sh : 0), w, t, l
      n = spg = sh = w = t = l = 0
    }
    function now(  d) { "date +%H:%M" | getline d; close("date +%H:%M"); return d }
    {
      k = ($2 == "1") ? "test" : "train"
      if ($1 != ep || k != kind) { summary(); ep = $1; kind = k }
      r = ($9 > 0) ? $5 / $9 : 0
      n++; spg += $5; sh += $9
      if (r > 1.1) w++; else if (r < 0.9) l++; else t++
      printf "ep %2s %-5s %-4s  PG %8.3fs  HybridQO %8.3fs  x%.2f\n", $1, k, $3, $5, $9, r
      fflush()
    }
    END { summary() }'
fi

wait $PID; RC=$?
grep -h "Het ngan sach" "$OUT" || true
show_error() {
  echo "run_mcts.py dừng vì lỗi (mã $RC). 30 dòng cuối của $OUT:"
  tail -30 "$OUT" | tr '\r' '\n' | grep -v "it/s" | tail -30
  exit 1
}
[ -n "$LOG" ] || show_error

# Lưu kết quả theo định dạng wandb_export của tác giả (code giống kaggle/to_wandb_export.py).
# Nếu run_mcts.py lỗi giữa chừng thì vẫn lưu phần đã chạy, rồi mới báo lỗi.
/tmp/hqo_env/bin/python - "$LOG" <<'PY'
import csv, os, sys
METRICS = [("hinter_latency", "hinter_latency"), ("test_query", "test_query"), ("epoch", "epoch"),
           ("pg_lateny", "pg_latency"), ("pg_plan_time", "pg_plan_time"), ("mcts_time", "mcts_time"),
           ("hinter_plan_time", "hinter_plan_time"), ("MPHE_time", "MPHE_time")]
query_log, split, rep = sys.argv[1], os.environ["HQO_SPLIT"], os.environ["HQO_REP"]
run = os.path.basename(query_log).replace("__query_log.csv", "")
rows = list(csv.DictReader(open(query_log)))
out_dir = "/kaggle/working/wandb_export"
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f"hybrid_qo__JOB__{split}__{rep}.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["Step"] + [f"{run} - {m}{s}" for m, _ in METRICS for s in ("", "__MIN", "__MAX")])
    for step, r in enumerate(rows):
        w.writerow([step] + [r[c] for _, c in METRICS for _ in range(3)])
per_epoch = {}
for r in rows:
    per_epoch[int(r["epoch"])] = per_epoch.get(int(r["epoch"]), 0) + 1
full = [e for e, n in per_epoch.items() if n == 113 and e <= 50]
print(f"Đã lưu {out}: {len(rows)} dòng; epoch tác giả sẽ chọn (đủ 113 dòng): {max(full) if full else 'KHÔNG CÓ'}")
PY
[ $RC -eq 0 ] || show_error
echo "Xong lúc $(date +%H:%M)."
```

Log in ra có dạng:

```
ep  3 train 12b   PG    0.120s  HybridQO    0.130s  x0.93
...
=== train epoch 3 xong lúc 09:41: 80 câu | PG 152.3s | HybridQO 160.1s | speedup 0.951 | thắng/hòa/thua 2/71/7 ===
```

`x` là `pg_latency / hinter_latency`: lớn hơn 1 nghĩa là plan HybridQO nhanh hơn PostgreSQL. Dòng tổng kết của một lượt chỉ in khi câu đầu của lượt kế tiếp chạy xong (hoặc khi kết thúc), nên có thể trễ vài giây đến vài phút.

**Thành công** khi dòng cuối là `epoch tác giả sẽ chọn (đủ 113 dòng): 10`.
Nếu in `0` hoặc `KHÔNG CÓ`, train đã dừng trước epoch 10 (chốt ngân sách hoặc lỗi), và split đó cần chạy lại.
Nếu `run_mcts.py` lỗi, ô vẫn lưu file kết quả với phần đã chạy, rồi in 30 dòng cuối của output và dừng.

Về file kết quả:
- `hybrid_qo__JOB__<SPLIT>__<REP>.csv` đúng định dạng các file trong `lqo_ml_perspective/hybrid_qo/logs/wandb_export/`: cột `Step`, rồi `<run_name> - <metric>`, `__MIN`, `__MAX` cho từng metric, giữ nguyên lỗi chính tả `pg_lateny` của tác giả. Chép file vào thư mục `wandb_export` là notebook `FullEvaluation_JOB_MergeResultFiles.ipynb` của tác giả đọc được.
- File `hqo_logs/<thời_gian>__query_log.csv` gốc vẫn được giữ, vì nó có thêm cột `query_ident` mà file của tác giả không có.
- Để chuyển log cũ trên máy (như LOO-1), dùng [kaggle/to_wandb_export.py](kaggle/to_wandb_export.py).

Test chạy ở epoch 0 và epoch 10, không có lần test cuối riêng (bản vá 3 ở ô 6), nên mỗi epoch test có đúng 113 dòng như mốc epoch 10 trong log tác giả.

Thời gian ước lượng cho 11 epoch, tách từ thời gian từng câu trong lần chạy LOO-1 trên GPU T4 (khoảng 39 phút/epoch với 80 câu train), đã cộng khoảng 17 phút cho các ô 1–6:

| Split | Train/Test | Cả phiên |
|---|---|---|
| `leave_one_out_split_2` / `_3` | 80/33 | 6,7 / 7,2 giờ |
| `random_split_1` / `_2` / `_3` | 91/22 | 8,9 / 9,2 / 7,2 giờ |
| `base_query_split_1` / `_2` / `_3` | 94/19, 90/23, 87/26 | 9,6 / 7,4 / 8,2 giờ |

Tổng 8 split còn lại khoảng **64 giờ máy**. Số đo trên máy dùng chung có thể lệch ±20%.
`HQO_BUDGET_H=10` chỉ là chốt an toàn khi máy chậm bất thường. Ngân sách được kiểm tra ở đầu mỗi epoch nên có thể vượt tối đa một epoch, vẫn nằm trong 12 giờ.

### Vì sao 11 epoch mà không phải 50

So log `wandb_export` của tác giả (3 lần chạy LOO-1, 50 epoch) với lần chạy Kaggle đầu tiên (`logs/kaggle/hybridqo/leave_one_out_split_1/hqo_logs/2026_11_07__065424__query_log.csv`).
Speedup tính bằng tổng `pg_latency` / tổng `hinter_latency` trên 33 câu test. Thắng/hòa/thua dùng ngưỡng ±10%.

| Epoch test | Tác giả (3 lần chạy) | Kaggle |
|---|---|---|
| 0 | 0,76–0,88 | 0,42 (0/28/5) |
| 10 | 0,995–1,003 (0–1 thắng, 0 thua) | **1,001 (3/30/0)** |
| 20–49 | 0,995–1,08, gần như toàn hòa | (chưa chạy tới) |

Speedup trên tập train của tác giả về khoảng 1,00 từ epoch 3 và đứng yên tới epoch 49.
Từ epoch 10, kết quả Kaggle đã giống tác giả: HybridQO hòa với PostgreSQL trên gần như mọi câu test, và các epoch sau không đổi kết quả.

Vì vậy mọi split đều chạy **11 epoch (0–10)** và so ở **epoch 10**:
- Mọi split dừng ở cùng một epoch, nên so giữa các split công bằng. Trước đây dùng 15 epoch kèm chốt 9 giờ thì mỗi split dừng ở một epoch khác nhau (11–15).
- LOO-1 (đã chạy, 12 epoch) cũng có test ở epoch 10 với đủ 113 dòng, nên dùng chung mốc này được.
- Log tác giả có test ở epoch 10 cho cả 27 lần chạy, nên so được trực tiếp. Nên nêu thêm kết quả epoch 49 của tác giả để cho thấy kết quả không đổi sau epoch 10.

Báo cáo cần ghi rõ việc giảm epoch và lý do này.

---

## Bước cuối. Chạy thật bằng chế độ Commit

Không nên train trong phiên tương tác, vì phiên sẽ ngắt khi bạn đóng trình duyệt hoặc để máy rảnh lâu.

1. Chạy thử các ô 1–6 trong phiên tương tác để chắc không có lỗi. Nếu muốn, chạy ô 7 vài phút để thấy các dòng log đầu tiên (vòng lặp chạy được), rồi bấm **Stop**. Không cần chạy hết ô 7 trong phiên tương tác.
2. Bấm **Save Version → Save & Run All (Commit)**. Kaggle chạy toàn bộ notebook từ đầu đến cuối ở chế độ nền, tối đa 12 giờ, bạn tắt máy cũng không sao.
3. Khi xong, vào tab **Output** của phiên bản đó và tải về:
   - `wandb_export/hybrid_qo__JOB__<split>__<rep>.csv`: kết quả theo định dạng của tác giả, chép vào `logs/kaggle/hybridqo/wandb_export/`
   - `hqo_logs/<thời_gian>__query_log.csv`: log gốc, có cột `query_ident`, chép vào `logs/kaggle/hybridqo/<split>/hqo_logs/`
   - `run_mcts__<split>__<rep>.out`: toàn bộ output

---

## Chạy các split còn lại

`leave_one_out_split_1` đã chạy xong: log ở [logs/kaggle/hybridqo/leave_one_out_split_1/](logs/kaggle/hybridqo/leave_one_out_split_1/), file theo định dạng tác giả ở `logs/kaggle/hybridqo/wandb_export/hybrid_qo__JOB__leave_one_out_split_1__0.csv` (tạo bằng `kaggle/to_wandb_export.py`).
Còn 8 split, mỗi split là một notebook và một lần Commit:

| Kiểu split | Tên trong `SPLIT` (ô 6) | Ý nghĩa |
|---|---|---|
| Leave-one-out | `leave_one_out_split_1`, `_2`, `_3` | Mỗi template giữ lại một câu cho test, nên câu test có "anh em" trong tập train |
| Random | `random_split_1`, `_2`, `_3` | Chia ngẫu nhiên |
| Base query | `base_query_split_1`, `_2`, `_3` | Giữ lại nguyên cả template cho test, khó nhất vì câu test có cấu trúc chưa từng thấy |

**Cách 1: sinh sẵn 8 notebook bằng script** (cần [Kaggle CLI](https://github.com/Kaggle/kaggle-api) và API token):

```
python kaggle/build_notebook.py --user <kaggle_username> --remaining            # GPU
python kaggle/build_notebook.py --user <kaggle_username> --remaining --cpu      # CPU, sau khi đã thử CPU (xem dưới)
kaggle kernels push -p kaggle/hybridqo-job-random-1                             # lặp lại cho từng thư mục
```

**Cách 2: làm tay trên web**, mỗi split:

1. Mở notebook, chọn **File → Copy** (hoặc **Copy & Edit**) để có một notebook riêng cho split đó.
2. Ở ô 6, đổi `SPLIT` (giữ `REP = 0`).
3. Chọn máy (xem dưới).
4. **Save Version → Save & Run All (Commit)**.

**GPU hay CPU?** GPU không làm HybridQO nhanh hơn: trong lần chạy LOO-1 trên T4, phần mạng neural (`mcts_time` + `MPHE_time`) chỉ chiếm khoảng 1 phút, còn thời gian chủ yếu là PostgreSQL chạy truy vấn. Khác biệt nằm ở quota:

| Máy | Điều kiện | 8 split (khoảng 64 giờ máy) |
|---|---|---|
| GPU (`GPU T4 x2`) | Quota khoảng 30 giờ/tuần, tức 3–4 split/tuần | Khoảng **2,5 tuần** |
| CPU (`Accelerator → None`) | Không tốn quota GPU; chạy song song được nhiều notebook (kiểm tra giới hạn số phiên cùng lúc của tài khoản) | Khoảng **1 ngày** nếu chạy 4–5 notebook cùng lúc |

Nên thử CPU trước: mở một notebook với `Accelerator → None`, chạy ô 1–6, rồi chạy ô 7 khoảng 5–10 phút. Nếu ô 7 in ra các dòng `ep  0 train ...` mà không báo lỗi `cuda`, bấm Stop và Commit các split trên CPU. Nếu lỗi, dùng GPU cho các split còn lại.
Chạy CPU, train mạng sẽ chậm hơn một chút, nên `random_split_1/2` và `base_query_split_1` (9–9,6 giờ trên GPU) sát giới hạn hơn. Theo dõi kỹ split đầu tiên chạy trên CPU.

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
Lấy các dòng `test_query = 1` ở **epoch 10**, tính thắng/hòa/thua với ngưỡng ±10% như phần Bao, rồi so với epoch 10 trong log của tác giả cho cùng split (`hybrid_qo__JOB__<split>__0/1/2.csv`).

File `hybrid_qo__JOB__*.csv` không có cột `query_ident`. Notebook của tác giả gán tên câu theo thứ tự trong file `workload/*.json`. Thứ tự này đúng cho các dòng test (`test_epoch` không xáo trộn câu), nhưng **sai cho các dòng train** vì `train_epoch` xáo trộn câu mỗi epoch. Khi cần tên câu train, dùng `query_log.csv`.

**Không so trực tiếp** thời gian đo trên Kaggle với thời gian đo trên máy Mac của nhóm. Hai máy khác nhau, và máy Kaggle dùng chung tài nguyên nên số đo dao động nhiều hơn.

---

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `ConcurrencyViolation Sequence number must match Draft record` | Lỗi lưu bản nháp của Kaggle khi notebook mở ở 2 tab/máy. Ô đang chạy **không** bị dừng. Đóng các tab khác, tải lại trang; đừng chạy lại ô 4 khi lần nạp trước chưa xong (ô 4 sẽ tự chặn) |
| Không bật được GPU/Internet | Chưa xác minh số điện thoại |
| Ô 2 in `postgres (PostgreSQL) 12.5` rồi báo `ls: cannot access '/opt/pg12/lib/pg_hint_plan.so'` | Build đã xong; bản hướng dẫn cũ kiểm tra sai chỗ (file thật ở `/opt/pg12/lib/postgresql/`). Không cần build lại, chạy tiếp ô 3 |
| `dropdb: command not found` / `Chưa có PostgreSQL ở /opt/pg12` | Phiên Kaggle đã khởi động lại (hết giờ, rảnh lâu, hoặc restart session) nên `/opt` và `/tmp` bị xóa. Chạy lại lần lượt ô 1 → 4 |
| `initdb: cannot be run as root` | Phải chạy qua `su postgres -c ...` như ô 3 |
| `could not resize shared memory segment` | Kiểm tra đã có `dynamic_shared_memory_type = mmap` |
| `unsupported XML feature ... --with-libxml` ở ô 4 | Bản hướng dẫn cũ đếm dòng bằng `query_to_xml`/`xpath`, mà PG build ở ô 2 không có libxml. Dùng đoạn đếm mới của ô 4 (vòng lặp `count(*)`) rồi chạy lại ô 4; ô sẽ bỏ qua bước nạp và chỉ kiểm tra |
| Notebook tự khởi động lại giữa chừng | Hết RAM: giảm `work_mem` hoặc `max_parallel_workers_per_gather` ở ô 3 |
| `psqlparse` không cài được | Kiểm tra môi trường đúng là Python 3.10 (`/tmp/hqo_env/bin/python --version`) |
| `RuntimeError: ... CUDA` / `Torch not compiled with CUDA` | Máy không có GPU mà bản vá CUDA ở ô 6 chưa đủ. Gửi output cho mình; trong lúc chờ, bật GPU trong Session options |
| Ô 7 in `epoch tác giả sẽ chọn ...: 0` hoặc `KHÔNG CÓ` | Train dừng trước epoch 10 (chốt ngân sách hoặc phiên bị cắt). Chạy lại split đó |
| Phiên hết 12 giờ trước khi xong | Giảm `HQO_BUDGET_H` |
