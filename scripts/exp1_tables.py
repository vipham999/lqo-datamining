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
OUT = os.path.join(O, "exp1")
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


def bao_kaggle(s):
    """Bao trên Kaggle (bao_kaggle_log/<split>): PG và Bao đo trong cùng notebook, cùng cấu hình với HybridQO."""
    b = os.path.join(R, "bao_kaggle_log", s, "bao_logs")
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

    with open(os.path.join(OUT, "exp1_tomtat.txt"), "w") as f:
        f.write("Bao và HybridQO theo từng split (nhóm cạnh tác giả)\n")
        f.write(per.round(2).to_string(index=False) + "\n\nTổng 233 lần kiểm tra (9 split)\n")
        f.write(tot.round(3).to_string(index=False) + "\n\nAblation 8.3\n")
        f.write(pd.DataFrame(abl).round(2).to_string(index=False) + "\n\nAblation 8.4/8.5: xem ")
        f.write(", ".join(os.path.basename(x) for x in glob.glob(os.path.join(O, "ablation_*_tomtat.txt"))) + "\n")
    print(open(os.path.join(OUT, "exp1_tomtat.txt")).read())


if __name__ == "__main__":
    main()
