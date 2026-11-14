"""Phần dùng chung của dashboard: đường dẫn, màu, thông tin CSDL IMDB, tổng quan 113 câu JOB, kết quả bài báo.
Import module này cũng thêm scripts/common và scripts/exp2 vào sys.path (để tab Demo dùng lại hàm của Thí nghiệm 2)."""
import glob
import json
import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "scripts", d) for d in ("common", "exp2")]

OUT = os.path.join(ROOT, "analysis/output")
APP_OUT = os.path.join(OUT, "app")

# Màu cố định theo thực thể (palette mặc định của dataviz, thứ tự cố định, không xoay vòng)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
HINT_SETS = ["default", "no_nestloop", "no_hashjoin", "no_mergejoin", "no_seqscan", "no_indexscan"]

# ---------------------------------------------------------------- CSDL IMDB
IMDB_DB = os.path.join(APP_OUT, "imdb_db.json")
# Nhóm và ý nghĩa của 21 bảng IMDB (JOB)
TABLE_INFO = {
    "title": ("Trung tâm", "Phim, series, tập phim: tựa, năm sản xuất, loại"),
    "name": ("Trung tâm", "Người: diễn viên, đạo diễn, biên kịch…; có giới tính"),
    "cast_info": ("Bảng nối", "Ai tham gia phim nào, vai trò gì, đóng nhân vật nào"),
    "movie_companies": ("Bảng nối", "Phim do công ty nào sản xuất/phát hành"),
    "movie_keyword": ("Bảng nối", "Phim gắn với từ khóa nào"),
    "movie_link": ("Bảng nối", "Liên kết giữa hai phim: sequel, remake, follows…"),
    "complete_cast": ("Bảng nối", "Danh sách cast/crew của phim đã đầy đủ chưa"),
    "movie_info": ("Thông tin", "Thông tin phim dạng key–value: thể loại, quốc gia, ngôn ngữ, ngày phát hành…"),
    "movie_info_idx": ("Thông tin", "Rating, số lượt bình chọn, thứ hạng top 250"),
    "person_info": ("Thông tin", "Tiểu sử, ngày sinh… của người"),
    "aka_name": ("Thông tin", "Tên khác (bí danh) của người"),
    "aka_title": ("Thông tin", "Tên khác của phim"),
    "char_name": ("Thông tin", "Tên nhân vật"),
    "company_name": ("Thông tin", "Công ty, kèm mã quốc gia"),
    "keyword": ("Thông tin", "Từ khóa"),
    "info_type": ("Tra cứu", "113 loại thông tin (genres, rating, budget…)"),
    "kind_type": ("Tra cứu", "Loại phim: movie, tv series, episode…"),
    "role_type": ("Tra cứu", "Vai trò: actor, actress, director…"),
    "link_type": ("Tra cứu", "Loại liên kết phim: sequel, remake…"),
    "company_type": ("Tra cứu", "Loại công ty: production, distributors…"),
    "comp_cast_type": ("Tra cứu", "Loại độ đầy đủ: cast, crew, complete…"),
}
TABLE_GROUPS = ["Trung tâm", "Bảng nối", "Thông tin", "Tra cứu"]


def load_imdb():
    return json.load(open(IMDB_DB)) if os.path.exists(IMDB_DB) else None


JOB_DIR = os.path.join(ROOT, "lqo_ml_perspective/bao/queries/join-order-benchmark")
# PostgreSQL mặc định trên Kaggle (ablation 8.4/8.5, cùng cấu hình với Bao/HybridQO), lần chạy thứ 3
JOB_PG_LOG = os.path.join(ROOT, "bao_kaggle_log/ablation_8_4_8_5/ablation_logs/test__postgres__job__default__kaggle.txt")
GEQO_THRESHOLD = 12


def job_overview():
    """113 câu JOB: họ, số bảng nối, số điều kiện, thời gian PostgreSQL (ms) nếu có log."""
    rows = []
    for f in sorted(glob.glob(os.path.join(JOB_DIR, "*.sql"))):
        s = open(f).read()
        q = os.path.basename(f)[:-4]
        frm = re.search(r"FROM(.*?)WHERE", s, re.S | re.I).group(1)
        where = s[s.upper().index("WHERE"):]
        rows.append({"câu": q, "họ": int(re.match(r"\d+", q).group()), "số_bảng": frm.count(",") + 1,
                     "số_điều_kiện": len(re.findall(r"\bAND\b", where, re.I)) + 1})
    d = pd.DataFrame(rows)
    if os.path.exists(JOB_PG_LOG):
        t = {}
        for line in open(JOB_PG_LOG):
            a = [x.strip() for x in line.split(",")]
            if len(a) >= 6 and a[1] == "2":
                t[os.path.basename(a[3])[:-4]] = float(a[4]) + float(a[5])
        d["pg_ms"] = d["câu"].map(t)
    d["dùng_GEQO"] = d["số_bảng"] >= GEQO_THRESHOLD
    return d


def schema_dot(db, show_bridge=False):
    """Sơ đồ Graphviz của CSDL: cạnh khóa ngoại → id xếp theo tầng phim/người → bảng nối/thông tin → tra cứu;
    cạnh bắc cầu (hai cột đều không phải id) vẽ nét đứt và không ảnh hưởng bố cục."""
    color = dict(zip(TABLE_GROUPS, PALETTE))
    centers = {t for t, (g, _) in TABLE_INFO.items() if g == "Trung tâm"}
    fk, bridge = {}, {}
    for e in db["edges"]:
        if "id" in (e["c1"], e["c2"]):
            ref, col, other = (e["t1"], e["c2"], e["t2"]) if e["c1"] == "id" else (e["t2"], e["c1"], e["t1"])
            # cạnh luôn đi từ tầng ngoài vào: phim/người → bảng tham chiếu tới nó; bảng khác → bảng nó tham chiếu
            pair = (ref, other) if ref in centers else (other, ref)
            fk.setdefault(pair, []).append((col, e["so_cau"]))
        elif show_bridge:
            pair = tuple(sorted((e["t1"], e["t2"])))
            bridge.setdefault(pair, []).append((f'{e["c1"]} = {e["c2"]}', e["so_cau"]))
    lines = ['digraph G { rankdir=LR; nodesep=0.25; ranksep=1.1; splines=true; bgcolor="transparent";',
             'node [shape=box, style="rounded,filled", fontname="helvetica", fontsize=13, fontcolor=white, '
             'color=white, penwidth=2, margin="0.18,0.08"];',
             'edge [fontname="helvetica", fontsize=10, color="#8c8b87", fontcolor="#52514e", arrowhead=none];',
             "{ rank=source; " + " ".join(f'"{t}";' for t in sorted(centers)) + " }"]
    for t in db["tables"]:
        g = TABLE_INFO.get(t["name"], ("Tra cứu",))[0]
        lines.append(f'"{t["name"]}" [fillcolor="{color[g]}", label="{t["name"]}\\n{t["rows"]:,} dòng"];')
    for (a, b), cols in fk.items():
        n = max(c[1] for c in cols)
        label = "\\n".join(f"{c} ({k})" for c, k in sorted(cols, key=lambda x: -x[1]))
        lines.append(f'"{a}" -> "{b}" [label="{label}", penwidth={1 + n / 20:.1f}];')
    for (a, b), cols in bridge.items():
        label = "\\n".join(f"{c} ({k})" for c, k in cols)
        lines.append(f'"{a}" -> "{b}" [label="{label}", style=dashed, color="#c3c2be", fontcolor="#8c8b87", '
                     f'constraint=false];')
    return "\n".join(lines + ["}"])


# ---------------------------------------------------------------- kết quả bài báo
def paper_results():
    by_m = os.path.join(OUT, "c1_authors_by_method.csv")
    summ = os.path.join(OUT, "c1_authors_summary.csv")
    if not (os.path.exists(by_m) and os.path.exists(summ)):
        return None, None
    return pd.read_csv(by_m), pd.read_csv(summ)
