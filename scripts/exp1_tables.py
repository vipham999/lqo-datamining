"""Thí nghiệm 1 (Mục 4.2 báo cáo): gom kết quả kiểm chứng bài báo thành bảng, cạnh số của tác giả.

  python3 scripts/exp1_tables.py      → analysis/output/exp1/
Nguồn:
  Bao nhóm      : analysis/output/c1_Bao_job__<split>_fair*_summary.csv (Mac, baseline PG đo công bằng)
  HybridQO nhóm : analysis/output/c1_HybridQO_kaggle_9split_summary.csv (Kaggle, epoch 10, PG cùng lần chạy)
  Tác giả       : analysis/output/c1_authors_summary.csv (log công bố, Bao/HybridQO/Neo/Balsa/LEON)
  Ablation      : analysis/output/ablation_interleaved_*_tomtat.txt, c1_Bao_*_imdb50_*_summary.csv
"""
import glob
import os

import pandas as pd

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
O = os.path.join(R, "analysis/output")
OUT = os.environ.get("EXP1_OUT", os.path.join(O, "exp1"))
SPLITS = [f"{k}_split_{i}" for k in ("leave_one_out", "random", "base_query") for i in (1, 2, 3)]
SHORT = {"leave_one_out": "LOO", "random": "RND", "base_query": "BQ"}


def short(s):
    k, i = s.rsplit("_split_", 1)
    return f"{SHORT[k]}-{i}"


def wtl(r):
    return f"{int(r.thắng)}/{int(r.hòa)}/{int(r.thua)}"


def _load_bao_log(path):
    """Log run_test_queries.py: hint, lần chạy, thời điểm, file, planning ms, execution ms, PG/Bao → lấy lần thứ 3."""
    rows = []
    for line in open(path):
        x = [s.strip() for s in line.rsplit(",", 6)]
        if len(x) == 7:
            rows.append({"hint": x[0], "run": int(x[1]), "q": os.path.basename(x[3])[:-4],
                         "plan": float(x[4]), "exe": float(x[5])})
    d = pd.DataFrame(rows)
    return d[d.run == 2].set_index("q")


def _end2end(path):
    d = _load_bao_log(path)
    return d.plan + d.exe


def ablation_8_3_kaggle():
    """8.3 trên Kaggle: Bao-Full (train trên IMDB đầy đủ, notebook bao-job-base-query-1) và Bao-50 (train trên IMDB-50%)
    cùng chạy tập test BQ-1 trên IMDB-50%. Đối chiếu log tác giả cùng hướng: imdb_trained/imdb2_trained × imdb2_tested
    (imdb2 = IMDB-50%, 4 model mỗi loại → lấy trung vị theo câu)."""
    k = os.path.join(R, "bao_kaggle_log/ablation_8_3/ablation83_logs")
    s = "base_query_split_1"
    if not os.path.exists(os.path.join(k, f"test__bao_50__job__{s}__imdb50.txt")):
        return
    pg = _end2end(os.path.join(k, f"test__postgres__job__{s}__imdb50.txt"))
    full = _end2end(os.path.join(k, f"test__bao_full__job__{s}__imdb50.txt"))
    half = _end2end(os.path.join(k, f"test__bao_50__job__{s}__imdb50.txt"))
    L = os.path.join(R, "lqo_ml_perspective/bao/logs")
    au = {n: pd.concat([_end2end(f) for f in sorted(glob.glob(os.path.join(L, f"test__bao__{n}_trained__imdb2_tested__*.txt")))],
                       axis=1).median(axis=1)[pg.index] for n in ("imdb", "imdb2")}
    rows = []
    for name, x in (("Bao-Full", full), ("Bao-50", half)):
        sp = pg / x
        rows.append({"so_sánh": f"{name} so với PostgreSQL", "nguồn": "nhóm (Kaggle)",
                     "chậm_hơn": int((sp < 0.9).sum()), "nhanh_hơn": int((sp > 1.1).sum()),
                     "tổng_A_s": x.sum() / 1000, "tổng_B_s": pg.sum() / 1000})
    for src, f, h in (("nhóm (Kaggle)", full, half), ("tác giả (log công bố)", au["imdb"], au["imdb2"])):
        r = f / h
        rows.append({"so_sánh": "Bao-Full so với Bao-50", "nguồn": src, "chậm_hơn": int((r > 1.1).sum()),
                     "nhanh_hơn": int((r < 0.9).sum()), "tổng_A_s": f.sum() / 1000, "tổng_B_s": h.sum() / 1000})
    out = pd.DataFrame(rows)
    out["số_câu"] = len(pg)
    out.to_csv(os.path.join(OUT, "exp1_ablation_8_3_kaggle.csv"), index=False)
    pd.DataFrame({"PG_ms": pg, "Bao_Full_ms": full, "Bao_50_ms": half, "tác_giả_Full_ms": au["imdb"],
                  "tác_giả_50_ms": au["imdb2"]}).round(1).to_csv(os.path.join(OUT, "exp1_ablation_8_3_kaggle_per_query.csv"),
                                                              index_label="câu")


# ================================================================ đợt lặp giống tác giả (kaggle/run_repeat_queue.sh)
RUNS = os.environ.get("KAGGLE_RUNS", os.path.join(R, "kaggle_runs"))
AUTHORS_LOG = os.path.join(R, "lqo_ml_perspective/experiment_logs/20240103__combined.csv")
PAPER_84 = {"28a": "nhanh 5,5×", "7c": "nhanh 2,0×", "30a": "nhanh 1,8×", "30c": "chậm 2,4×", "28b": "chậm 1,9×",
            "15c": "chậm 1,5×"}
PAPER_85 = {"30a": "nhanh 1,6×", "24b": "chậm 9,9×", "26c": "chậm 2,2×", "28a": "chậm 2,1×", "28b": "chậm 1,7×"}
PAPER_83 = {"16b": "Bao-50 timeout 1/4 model, 3 model còn lại chậm hơn 19 s", "31c": "chậm 24× (8,4 s / 350 ms)",
            "17a": "chậm 4,5× (12,2 s / 2,7 s)", "7c": "nhanh 1,9×", "26c": "nhanh 1,6×", "10c": "nhanh 1,3×"}


def _q(s):
    return str(s).lstrip("0")


def _slug(s):
    return s.replace("_split_", "-").replace("_", "-")


def _authors():
    d = pd.read_csv(AUTHORS_LOG)
    d["q"] = d.query_ident.map(_q)
    return d


def _sig_table(base, cand, thr):
    """Cách của tác giả (FullEvaluation_JOB_ResultAnalysis.ipynb, create_df): base/cand là DataFrame (q, exec_ms) với
    nhiều lượt mỗi câu. Có ý nghĩa: |Δ trung bình| > thr và > 1.96·sqrt(SE1² + SE2²)."""
    b, c = base.groupby("q").exec_ms, cand.groupby("q").exec_ms
    d = pd.DataFrame({"default_ms": b.mean(), "ablation_ms": c.mean(), "n_default": b.count(), "n_ablation": c.count(),
                      "err_ms": 1.96 * ((b.std() / b.count() ** 0.5) ** 2 + (c.std() / c.count() ** 0.5) ** 2) ** 0.5})
    d["diff_ms"] = d.default_ms - d.ablation_ms                  # > 0: tắt tính năng thì nhanh hơn
    d["vuot_nguong"] = d.diff_ms.abs() > thr
    d["co_y_nghia"] = d.vuot_nguong & (d.diff_ms.abs() > d.err_ms)
    d["ti_le"] = d.ablation_ms / d.default_ms
    return d


def ablation_845_repeat():
    """8.4 (tắt bitmap + tid scan, ngưỡng 250 ms) và 8.5 (tắt GEQO, ngưỡng 100 ms): nhóm (8 lượt xen kẽ trên Kaggle)
    cạnh tác giả (13 lượt default, 2 lượt no_bitmap_tidscan, 8 lượt no_geqo), cùng một công thức."""
    k = os.path.join(RUNS, "ablation-job-8-4-8-5-r8", "ablation_logs")
    if not glob.glob(os.path.join(k, "test__postgres__job__default__kaggle_p*.txt")):
        return None

    def load(cfg):
        rows = []
        for f in sorted(glob.glob(os.path.join(k, f"test__postgres__job__{cfg}__kaggle_p*.txt"))):
            p = int(f.rsplit("_p", 1)[1][:-4])
            for line in open(f):
                x = [s.strip() for s in line.split(",")]
                if len(x) >= 7 and x[1] == "2":
                    rows.append({"q": _q(os.path.basename(x[3])[:-4]), "lượt": p, "exec_ms": float(x[5])})
        return pd.DataFrame(rows)

    au = _authors()
    pg = au[au.method == "PostgreSQL"].rename(columns={"execution_time": "exec_ms"})
    summary, per_q = [], []
    g_base = load("default")
    for sec, cfg, thr, paper in (("8.4", "no_bitmap_tidscan", 250, PAPER_84), ("8.5", "no_geqo", 100, PAPER_85)):
        for src, base, cand in (("nhóm (Kaggle)", g_base, load(cfg)),
                                ("tác giả (log công bố)", pg[pg.run_type == "regular"], pg[pg.run_type == cfg])):
            t = _sig_table(base, cand, thr)
            s = t[t.co_y_nghia]
            summary.append({"mục": sec, "cấu_hình": cfg, "nguồn": src, "ngưỡng_ms": thr,
                            "số_lượt_default": int(t.n_default.min()), "số_lượt_ablation": int(t.n_ablation.min()),
                            "vượt_ngưỡng": int(t.vuot_nguong.sum()), "có_ý_nghĩa": len(s),
                            "nhanh_hơn": int((s.diff_ms > 0).sum()), "chậm_hơn": int((s.diff_ms < 0).sum()),
                            "workload_default_s": t.default_ms.sum() / 1000, "workload_ablation_s": t.ablation_ms.sum() / 1000})
            keep = t[t.co_y_nghia | t.index.isin(list(paper))]
            per_q.append(keep.assign(mục=sec, nguồn=src, bài_báo=keep.index.map(lambda q: paper.get(q, ""))))
    summary = pd.DataFrame(summary)
    summary.to_csv(os.path.join(OUT, "exp1_ablation_8_4_8_5.csv"), index=False)
    pq = pd.concat(per_q).reset_index().rename(columns={"index": "câu", "q": "câu"})
    pq[["mục", "nguồn", "câu", "default_ms", "ablation_ms", "ti_le", "diff_ms", "err_ms", "co_y_nghia", "bài_báo"]] \
        .round(2).to_csv(os.path.join(OUT, "exp1_ablation_8_4_8_5_per_query.csv"), index=False)
    return summary


def ablation_8_3_repeat():
    """8.3 đủ 4 hướng × 4 bản (kaggle_runs/ablation-job-8-3-rep*/), 113 câu, cạnh log tác giả cùng hướng.
    Tên hướng theo log tác giả: <CSDL train>_trained__<CSDL test>_tested (imdb = đầy đủ, imdb50 = IMDB-50%)."""
    s = "base_query_split_1"
    reps = sorted(glob.glob(os.path.join(RUNS, "ablation-job-8-3-rep*", "ablation83_logs")))
    reps = [k for k in reps if os.path.exists(os.path.join(k, f"test__bao_50__job__{s}__imdbload50.txt"))]
    if not reps:
        return None

    def load(path):
        rows = []
        for line in open(path):
            x = [v.strip() for v in line.rsplit(",", 6)]
            if len(x) == 7 and int(x[1]) == 2:
                rows.append({"q": _q(os.path.basename(x[3])[:-4]), "tập": x[3].split("/")[-2],
                             "ms": float(x[4]) + float(x[5])})
        return pd.DataFrame(rows).set_index("q")

    HUONG = {("full", "imdbload"): "imdb_trained__imdb_tested", ("50", "imdbload"): "imdb50_trained__imdb_tested",
             ("full", "imdbload50"): "imdb_trained__imdb50_tested", ("50", "imdbload50"): "imdb50_trained__imdb50_tested"}
    g = []                                            # nhóm: (bản, hướng, q, tập, ms) và PG
    for i, k in enumerate(reps, 1):
        for db in ("imdbload", "imdbload50"):
            pg = load(os.path.join(k, f"test__postgres__job__{s}__{db}.txt"))
            g.append(pg.assign(bản=i, hướng="PostgreSQL__" + db.replace("load", "")))
            for m in ("full", "50"):
                g.append(load(os.path.join(k, f"test__bao_{m}__job__{s}__{db}.txt")).assign(bản=i, hướng=HUONG[(m, db)]))
    g = pd.concat(g).reset_index()

    au = _authors()
    a = au[(au.method == "Bao") & ((au.experiment == s) | au.experiment.str.contains("imdb50_", na=False))].copy()
    a["hướng"] = a.experiment.replace({s: "imdb_trained__imdb_tested"})
    a = a[["q", "split", "run_id", "hướng", "total_time"]].rename(columns={"split": "tập", "run_id": "bản", "total_time": "ms"})
    ap = au[(au.method == "PostgreSQL") & au.run_type.isin(["regular", "imdb50"])].copy()
    ap["hướng"] = ap.run_type.map({"regular": "PostgreSQL__imdb", "imdb50": "PostgreSQL__imdb50"})
    sets = {_q(os.path.basename(f)[:-4]): t for t in ("train", "test")
            for f in glob.glob(os.path.join(R, f"lqo_ml_perspective/bao/queries/job__{s}/{t}/*.sql"))}
    ap["tập"] = ap.q.map(sets)
    a = pd.concat([a, ap[["q", "tập", "run_id", "hướng", "total_time"]].rename(columns={"run_id": "bản", "total_time": "ms"})])

    rows = []
    for src, d in (("nhóm (Kaggle)", g), ("tác giả (log công bố)", a)):
        for h, x in d.groupby("hướng"):
            for tap in ("tất cả", "test"):
                y = x if tap == "tất cả" else x[x["tập"] == "test"]
                tot = y.groupby("bản").ms.sum() / 1000                   # tổng workload của từng bản
                rows.append({"hướng": h, "nguồn": src, "tập": tap, "số_bản": tot.size, "số_câu": y.q.nunique(),
                             "tổng_s_trung_vị": tot.median(), "tổng_s_min": tot.min(), "tổng_s_max": tot.max()})
    summ = pd.DataFrame(rows).sort_values(["hướng", "tập", "nguồn"])
    summ.to_csv(os.path.join(OUT, "exp1_ablation_8_3_3huong.csv"), index=False)

    # Câu then chốt của bài báo: Bao-50 so với Bao-Full khi test trên IMDB đầy đủ (trung vị theo câu qua các bản)
    per = {}
    for src, d in (("nhóm", g), ("tác_giả", a)):
        m = d.groupby(["hướng", "q"]).ms.median().unstack(0)
        per[f"{src}_Full_ms"] = m["imdb_trained__imdb_tested"]
        per[f"{src}_50_ms"] = m["imdb50_trained__imdb_tested"]
    per = pd.DataFrame(per)
    per["tập"] = per.index.map(sets)
    for src in ("nhóm", "tác_giả"):
        per[f"{src}_50_chia_Full"] = per[f"{src}_50_ms"] / per[f"{src}_Full_ms"]
    per["bài_báo"] = per.index.map(lambda q: PAPER_83.get(q, ""))
    per.round(2).sort_values("nhóm_50_chia_Full", ascending=False) \
       .to_csv(os.path.join(OUT, "exp1_ablation_8_3_per_query.csv"), index_label="câu")
    cnt = pd.DataFrame([{"nguồn": src, "số_câu": int(per[f"{src}_50_chia_Full"].notna().sum()),
                         "Bao50_chậm_hơn_>10%": int((per[f"{src}_50_chia_Full"] > 1.1).sum()),
                         "Bao50_nhanh_hơn_>10%": int((per[f"{src}_50_chia_Full"] < 0.9).sum())}
                        for src in ("nhóm", "tác_giả")])
    return summ, cnt, per


def _hqo_run(path, s):
    """Một lần chạy HybridQO (query_log của run_mcts.py), epoch 10, câu test của split: giống bảng c1_HybridQO_kaggle."""
    d = pd.read_csv(path)
    d = d[d.epoch == 10].copy()
    test = {_q(os.path.basename(f)[:-4]) for f in glob.glob(os.path.join(R, f"lqo_ml_perspective/bao/queries/job__{s}/test/*.sql"))}
    d = d[d.query_ident.map(_q).isin(test)]
    pg = d.pg_plan_time + d.pg_latency
    h = d.hinter_plan_time + d.hinter_latency + d.mcts_time + d.MPHE_time
    sp = pg / h
    return {"n": len(d), "thắng": int((sp > 1.1).sum()), "hòa": int(((sp >= 0.9) & (sp <= 1.1)).sum()),
            "thua": int((sp < 0.9).sum()), "PG_s": pg.sum(), "LQO_s": h.sum(), "speedup": pg.sum() / h.sum(),
            "trung_vị": sp.median()}


def repeat_runs():
    """Mọi lần train của nhóm trên Kaggle (lần 0 + rep1, rep2) cho Bao và HybridQO: một dòng mỗi (phương pháp, split, lần)."""
    hq0 = pd.read_csv(os.path.join(O, "c1_HybridQO_kaggle_9split_summary.csv")).set_index("split")
    rows = []
    for s in SPLITS:
        bk = bao_kaggle(s)
        rows.append({"phương_pháp": "Bao", "split": short(s), "lần": 0, **{k: bk[k] for k in
                     ("n", "thắng", "hòa", "thua", "PG_s", "LQO_s", "speedup", "trung_vị")}})
        h = hq0.loc[s]
        rows.append({"phương_pháp": "HybridQO", "split": short(s), "lần": 0, "n": int(h.n), "thắng": int(h.thang),
                     "hòa": int(h.hoa), "thua": int(h.thua), "PG_s": h.PG_s, "LQO_s": h.HQO_s, "speedup": h.speedup,
                     "trung_vị": h.trung_vi})
        for r in (1, 2):
            b = os.path.join(RUNS, f"bao-job-{_slug(s)}-rep{r}", "bao_logs")
            if os.path.exists(os.path.join(b, f"test__bao__job__{s}.txt")):
                rows.append({"phương_pháp": "Bao", "split": short(s), "lần": r, **{k: v for k, v in bao_kaggle(s, b).items()
                             if k in ("n", "thắng", "hòa", "thua", "PG_s", "LQO_s", "speedup", "trung_vị")}})
            f = sorted(glob.glob(os.path.join(RUNS, f"hybridqo-job-{_slug(s)}-rep{r}", "hqo_logs", "*query_log.csv")))
            if f:
                rows.append({"phương_pháp": "HybridQO", "split": short(s), "lần": r, **_hqo_run(f[-1], s)})
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(OUT, "exp1_lan_lap_tung_lan.csv"), index=False)
    agg = d.groupby(["phương_pháp", "split"], sort=False).agg(
        số_lần=("lần", "size"), speedup_trung_vị=("speedup", "median"), speedup_min=("speedup", "min"),
        speedup_max=("speedup", "max"), thua_trung_vị=("thua", "median"), thua_min=("thua", "min"),
        thua_max=("thua", "max")).reset_index()
    agg.to_csv(os.path.join(OUT, "exp1_lan_lap_theo_split.csv"), index=False)
    tot = d.groupby(["phương_pháp", "lần"]).agg(số_split=("split", "size"), thắng=("thắng", "sum"), hòa=("hòa", "sum"),
                                                thua=("thua", "sum"), PG_s=("PG_s", "sum"), LQO_s=("LQO_s", "sum")).reset_index()
    tot["speedup"] = tot.PG_s / tot.LQO_s
    tot.to_csv(os.path.join(OUT, "exp1_lan_lap_tong.csv"), index=False)
    return d, agg, tot


def bao_kaggle(s, b=None):
    """Bao trên Kaggle (bao_kaggle_log/<split>): PG và Bao đo trong cùng notebook, cùng cấu hình với HybridQO."""
    b = b or os.path.join(R, "bao_kaggle_log", s, "bao_logs")
    d = _load_bao_log(os.path.join(b, f"test__postgres__job__{s}.txt")).join(
        _load_bao_log(os.path.join(b, f"test__bao__job__{s}.txt")), lsuffix="_pg", rsuffix="_b")
    t_pg, t_b = d.plan_pg + d.exe_pg, d.plan_b + d.exe_b
    sp = t_pg / t_b
    return {"n": len(d), "thắng": int((sp > 1.1).sum()), "hòa": int(((sp >= 0.9) & (sp <= 1.1)).sum()),
            "thua": int((sp < 0.9).sum()), "PG_s": t_pg.sum() / 1000, "LQO_s": t_b.sum() / 1000,
            "speedup": t_pg.sum() / t_b.sum(), "trung_vị": sp.median(),
            "exec_speedup": d.exe_pg.sum() / d.exe_b.sum(),
            "plan_khác": int((~d.hint_b.isin(["", "x", "(no hint)"])).sum()),
            "overhead_s": (d.plan_b - d.plan_pg).sum() / 1000}


def main():
    os.makedirs(OUT, exist_ok=True)
    au = pd.read_csv(os.path.join(O, "c1_authors_summary.csv"))
    hq = pd.read_csv(os.path.join(O, "c1_HybridQO_kaggle_9split_summary.csv")).set_index("split")

    rows, diag, bk_all = [], [], []
    for s in SPLITS:
        f = [x for x in sorted(glob.glob(os.path.join(O, f"c1_Bao_job__{s}_fair*_summary.csv")))]
        b = pd.read_csv(f[-1]).iloc[0]
        bk = bao_kaggle(s)
        bk_all.append(bk)
        ab = au[(au.phương_pháp_gốc == "Bao") & (au.split == s)].iloc[0]
        ah = au[(au.phương_pháp_gốc == "HybridQO") & (au.split == s)].iloc[0]
        h = hq.loc[s]
        diag += [{"split": short(s), "phương_pháp": "Bao", "số_câu": bk["n"], "câu_đổi_plan": bk["plan_khác"],
                  "chi_phí_thêm_s": bk["overhead_s"], "speedup_chỉ_thực_thi": bk["exec_speedup"],
                  "speedup_end_to_end": bk["speedup"]},
                 {"split": short(s), "phương_pháp": "HybridQO", "số_câu": int(h.n), "câu_đổi_plan": int(h.plan_khac),
                  "chi_phí_thêm_s": h.infer_s, "speedup_chỉ_thực_thi": h.exec_only_speedup,
                  "speedup_end_to_end": h.speedup}]
        rows.append({
            "split": short(s), "số_câu": int(b.số_câu),
            "Bao_kaggle_T/H/Th": f"{bk['thắng']}/{bk['hòa']}/{bk['thua']}", "Bao_kaggle_speedup": bk["speedup"],
            "Bao_kaggle_trung_vị": bk["trung_vị"],
            "Bao_mac_T/H/Th": wtl(b), "Bao_mac_speedup": b.speedup_workload,
            "Bao_mac_trung_vị": b.speedup_trung_vị,
            "Bao_tác_giả_T/H/Th": wtl(ab), "Bao_tác_giả_speedup": ab.speedup_workload,
            "Bao_tác_giả_trung_vị": ab.speedup_trung_vị,
            "HQO_nhóm_T/H/Th": f"{int(h.thang)}/{int(h.hoa)}/{int(h.thua)}", "HQO_nhóm_speedup": h.speedup,
            "HQO_nhóm_trung_vị": h.trung_vi,
            "HQO_tác_giả_T/H/Th": wtl(ah), "HQO_tác_giả_speedup": ah.speedup_workload,
            "HQO_tác_giả_trung_vị": ah.speedup_trung_vị,
        })
    per = pd.DataFrame(rows)
    per.to_csv(os.path.join(OUT, "exp1_bao_hybridqo_per_split.csv"), index=False)
    # Vì sao thua PostgreSQL: số câu đổi plan, chi phí thêm (Bao: lập kế hoạch 5 tập hint; HybridQO: suy luận)
    pd.DataFrame(diag).to_csv(os.path.join(OUT, "exp1_nguyen_nhan.csv"), index=False)

    # Tổng 233 lần kiểm tra cho mọi phương pháp
    tot = []
    for m in ["Bao", "HybridQO", "Neo", "Balsa", "LEON"]:
        a = au[au.phương_pháp_gốc == m]
        tot.append({"phương_pháp": m, "nguồn": "tác giả (log công bố)", "thắng": a.thắng.sum(), "hòa": a.hòa.sum(),
                    "thua": a.thua.sum(), "PG_s": a.PG_workload_s.sum(), "LQO_s": a.LQO_workload_s.sum()})
    bsum = pd.concat([pd.read_csv(sorted(glob.glob(os.path.join(O, f"c1_Bao_job__{s}_fair*_summary.csv")))[-1])
                      for s in SPLITS])
    bk = pd.DataFrame(bk_all)
    tot.insert(0, {"phương_pháp": "Bao", "nguồn": "nhóm (Kaggle)", "thắng": bk.thắng.sum(), "hòa": bk.hòa.sum(),
                   "thua": bk.thua.sum(), "PG_s": bk.PG_s.sum(), "LQO_s": bk.LQO_s.sum()})
    tot.insert(1, {"phương_pháp": "Bao", "nguồn": "nhóm (Mac)", "thắng": bsum.thắng.sum(), "hòa": bsum.hòa.sum(),
                   "thua": bsum.thua.sum(), "PG_s": bsum.PG_workload_s.sum(), "LQO_s": bsum.LQO_workload_s.sum()})
    tot.insert(3, {"phương_pháp": "HybridQO", "nguồn": "nhóm (Kaggle, epoch 10)", "thắng": hq.thang.sum(),
                   "hòa": hq.hoa.sum(), "thua": hq.thua.sum(), "PG_s": hq.PG_s.sum(), "LQO_s": hq.HQO_s.sum()})
    tot = pd.DataFrame(tot)
    tot["speedup"] = tot.PG_s / tot.LQO_s
    tot["tỉ_lệ_thua"] = tot["thua"] / (tot["thắng"] + tot["hòa"] + tot["thua"])
    tot.to_csv(os.path.join(OUT, "exp1_total_233.csv"), index=False)

    # Ablation 8.3 (IMDB 50%)
    abl = []
    for f in sorted(glob.glob(os.path.join(O, "c1_Bao_*imdb50*_summary.csv"))):
        r = pd.read_csv(f).iloc[0]
        abl.append({"ablation": "8.3 IMDB 50% (model train trên IMDB đầy đủ)", "split": r.phương_pháp,
                    "T/H/Th": wtl(r), "speedup": r.speedup_workload, "trung_vị": r.speedup_trung_vị})
    pd.DataFrame(abl).to_csv(os.path.join(OUT, "exp1_ablation_8_3.csv"), index=False)
    ablation_8_3_kaggle()
    r845, r83, rep = ablation_845_repeat(), ablation_8_3_repeat(), repeat_runs()

    with open(os.path.join(OUT, "exp1_tomtat.txt"), "w") as f:
        f.write("===== Đợt lặp giống tác giả (kaggle_runs/)\n")
        f.write("Bao/HybridQO: mọi lần train theo split (lần 0 = đợt đầu)\n")
        f.write(rep[1].round(3).to_string(index=False) + "\n\nTổng theo từng lần train\n")
        f.write(rep[2].round(3).to_string(index=False) + "\n\n")
        if r845 is not None:
            f.write("Ablation 8.4/8.5 (công thức của tác giả: trung bình qua các lượt, 1,96·SE)\n")
            f.write(r845.round(1).to_string(index=False) + "\n\n")
        else:
            f.write("Ablation 8.4/8.5 nhiều lượt: chưa có log trong kaggle_runs/\n\n")
        if r83 is not None:
            f.write("Ablation 8.3 theo hướng (tổng workload, trung vị qua các bản)\n")
            f.write(r83[0].round(1).to_string(index=False) + "\n\nBao-50 so với Bao-Full khi test trên IMDB đầy đủ\n")
            f.write(r83[1].to_string(index=False) + "\n")
            f.write(r83[2][r83[2].bài_báo != ""].round(2).to_string() + "\n\n")
        else:
            f.write("Ablation 8.3 bốn bản: chưa có log trong kaggle_runs/\n\n")
        f.write("===== Đợt đầu\n")
        f.write("Bao và HybridQO theo từng split (nhóm cạnh tác giả)\n")
        f.write(per.round(2).to_string(index=False) + "\n\nTổng 233 lần kiểm tra (9 split)\n")
        f.write(tot.round(3).to_string(index=False) + "\n\nAblation 8.3\n")
        f.write(pd.DataFrame(abl).round(2).to_string(index=False) + "\n\nAblation 8.4/8.5: xem ")
        f.write(", ".join(os.path.basename(x) for x in glob.glob(os.path.join(O, "ablation_*_tomtat.txt"))) + "\n")
    print(open(os.path.join(OUT, "exp1_tomtat.txt")).read())


if __name__ == "__main__":
    main()
