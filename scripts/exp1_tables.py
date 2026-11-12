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


def main():
    os.makedirs(OUT, exist_ok=True)
    au = pd.read_csv(os.path.join(O, "c1_authors_summary.csv"))
    hq = pd.read_csv(os.path.join(O, "c1_HybridQO_kaggle_9split_summary.csv")).set_index("split")

    rows = []
    for s in SPLITS:
        f = [x for x in sorted(glob.glob(os.path.join(O, f"c1_Bao_job__{s}_fair*_summary.csv")))]
        b = pd.read_csv(f[-1]).iloc[0]
        ab = au[(au.phương_pháp_gốc == "Bao") & (au.split == s)].iloc[0]
        ah = au[(au.phương_pháp_gốc == "HybridQO") & (au.split == s)].iloc[0]
        h = hq.loc[s]
        rows.append({
            "split": short(s), "số_câu": int(b.số_câu),
            "Bao_nhóm_T/H/Th": wtl(b), "Bao_nhóm_speedup": b.speedup_workload,
            "Bao_nhóm_trung_vị": b.speedup_trung_vị,
            "Bao_tác_giả_T/H/Th": wtl(ab), "Bao_tác_giả_speedup": ab.speedup_workload,
            "Bao_tác_giả_trung_vị": ab.speedup_trung_vị,
            "HQO_nhóm_T/H/Th": f"{int(h.thang)}/{int(h.hoa)}/{int(h.thua)}", "HQO_nhóm_speedup": h.speedup,
            "HQO_nhóm_trung_vị": h.trung_vi,
            "HQO_tác_giả_T/H/Th": wtl(ah), "HQO_tác_giả_speedup": ah.speedup_workload,
            "HQO_tác_giả_trung_vị": ah.speedup_trung_vị,
        })
    per = pd.DataFrame(rows)
    per.to_csv(os.path.join(OUT, "exp1_bao_hybridqo_per_split.csv"), index=False)

    # Tổng 233 lần kiểm tra cho mọi phương pháp
    tot = []
    for m in ["Bao", "HybridQO", "Neo", "Balsa", "LEON"]:
        a = au[au.phương_pháp_gốc == m]
        tot.append({"phương_pháp": m, "nguồn": "tác giả (log công bố)", "thắng": a.thắng.sum(), "hòa": a.hòa.sum(),
                    "thua": a.thua.sum(), "PG_s": a.PG_workload_s.sum(), "LQO_s": a.LQO_workload_s.sum()})
    bsum = pd.concat([pd.read_csv(sorted(glob.glob(os.path.join(O, f"c1_Bao_job__{s}_fair*_summary.csv")))[-1])
                      for s in SPLITS])
    tot.insert(0, {"phương_pháp": "Bao", "nguồn": "nhóm (Mac)", "thắng": bsum.thắng.sum(), "hòa": bsum.hòa.sum(),
                   "thua": bsum.thua.sum(), "PG_s": bsum.PG_workload_s.sum(), "LQO_s": bsum.LQO_workload_s.sum()})
    tot.insert(2, {"phương_pháp": "HybridQO", "nguồn": "nhóm (Kaggle, epoch 10)", "thắng": hq.thang.sum(),
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

    with open(os.path.join(OUT, "exp1_tomtat.txt"), "w") as f:
        f.write("Bao và HybridQO theo từng split (nhóm cạnh tác giả)\n")
        f.write(per.round(2).to_string(index=False) + "\n\nTổng 233 lần kiểm tra (9 split)\n")
        f.write(tot.round(3).to_string(index=False) + "\n\nAblation 8.3\n")
        f.write(pd.DataFrame(abl).round(2).to_string(index=False) + "\n\nAblation 8.4/8.5: xem ")
        f.write(", ".join(os.path.basename(x) for x in glob.glob(os.path.join(O, "ablation_*_tomtat.txt"))) + "\n")
    print(open(os.path.join(OUT, "exp1_tomtat.txt")).read())


if __name__ == "__main__":
    main()
