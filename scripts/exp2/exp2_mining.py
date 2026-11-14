"""Khai phá dữ liệu trên kết quả Thí nghiệm 2 (không chạy thêm truy vấn, chỉ đọc lại log).

Dữ liệu vào:
  logs/mac/exp2/exp2_hintsets_job.jsonl   113 câu JOB × 6 phương án × 3 lần chạy (thời gian thật)
  logs/mac/exp2/exp2_explain_job.jsonl    plan mặc định (EXPLAIN) → 34 đặc trưng, như exp2_analyze.py

Kỹ thuật: luật kết hợp (dạng "điều kiện → kết quả"): đặc trưng rời rạc hoá thành điều kiện có/không; kết quả là
     "tắt X giúp ≥5%" hoặc "tắt X hại ≥2 lần", phải đúng ở CẢ lần chạy 2 và 3 (tránh nhiễu đo).
     Duyệt mọi tổ hợp 1–2 điều kiện; giữ luật có ≥6 câu khớp, ≥4 câu đúng, phủ ≥3 họ câu; kiểm định Fisher
     một phía + hiệu chỉnh Benjamini–Hochberg.
Kết quả dùng cho tab "4. Khai phá dữ liệu"; bước sửa (bỏ phiếu trắng theo ngưỡng) nằm ở exp2_abstain.py.

  <python có sklearn pandas scipy> scripts/exp2/exp2_mining.py
"""
import itertools
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sklearn.metrics import adjusted_rand_score

warnings.filterwarnings("ignore")
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common")]
import exp2_analyze as E  # noqa: E402
from extract_features import plan_signature  # noqa: E402

R = E.R
OUT = os.path.join(R, "analysis/output/exp2")
HINTS = E.HINTS
MIN_MATCH, MIN_HIT, MIN_FAM = 6, 4, 3


def times(run):
    """Thời gian (ms) theo câu × phương án ở một lần chạy; plan trùng default → dùng thời gian default."""
    rows, plans = [], {}
    with open(os.path.join(R, "logs/mac/exp2/exp2_hintsets_job.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if r["run"] != run:
                continue
            q = E.qid_of(r["query_id"], "JOB")
            rows.append((q, r["hint_set"], (r["planning_ms"] or 0) + r["execution_ms"]))
            if r.get("plan") is not None:
                plans[(q, r["hint_set"])] = plan_signature(r["plan"])
    t = pd.DataFrame(rows, columns=["q", "h", "ms"]).pivot_table(index="q", columns="h", values="ms", aggfunc="first")
    t = t.reindex(columns=HINTS)
    for q in t.index:
        for h in HINTS[1:]:
            if plans.get((q, h)) is not None and plans.get((q, h)) == plans.get((q, "default")):
                t.loc[q, h] = t.loc[q, "default"]
    return t.fillna(180_000.0)


def conditions(X, qs):
    items = {}

    def add(name, mask):
        m = pd.Series(np.asarray(mask), index=qs).astype(bool)
        if MIN_MATCH <= m.sum() <= len(qs) - MIN_MATCH:
            items[name] = m
    add("số bảng ≥12", X.sql_n_tables >= 12)
    add("số bảng ≤6", X.sql_n_tables <= 6)
    add("mọi phép nối là nested loop", X.plan_n_nestloop == X.plan_n_joins)
    add("không có hash join", X.plan_n_hashjoin == 0)
    add("có ≥2 hash join", X.plan_n_hashjoin >= 2)
    add("có merge join", X.plan_n_mergejoin >= 1)
    add("không có seq scan", X.plan_n_seqscan == 0)
    add("có ≥3 seq scan", X.plan_n_seqscan >= 3)
    add("có index-only scan", X.plan_n_indexonlyscan >= 1)
    add("có bitmap scan", X.plan_n_bitmapheapscan >= 1)
    add("có materialize", X.plan_n_materialize >= 1)
    add("có sort", X.plan_n_sort >= 1)
    add("chạy song song", X.plan_n_gather + X.plan_n_gathermerge >= 1)
    add("plan bushy", X.plan_is_bushy >= 1)
    add("có LIKE", X.sql_n_like >= 1)
    add("có IN", X.sql_n_in >= 1)
    add("có OR", X.sql_n_or >= 1)
    add("có BETWEEN/so sánh khoảng", X.sql_n_between + X.sql_n_range >= 1)
    for c, lbl in [("plan_total_cost", "cost ước lượng"), ("sql_n_filter_preds", "số điều kiện lọc"),
                   ("plan_n_nestloop", "số nested loop")]:
        lo, hi = X[c].quantile([1 / 3, 2 / 3])
        add(f"{lbl} thấp (≤{lo:g})", X[c] <= lo)
        add(f"{lbl} cao (>{hi:g})", X[c] > hi)
    return items


def mine_rules(items, tg, fam, qs):
    rows = []
    for k in (1, 2):
        for combo in itertools.combinations(items, k):
            m = np.logical_and.reduce([items[c] for c in combo])
            n = int(m.sum())
            if n < MIN_MATCH:
                continue
            for t in tg.columns:
                y = tg[t]
                ny, base = int(y.sum()), y.mean()
                hit = int((m & y).sum())
                if base == 0 or hit < MIN_HIT:
                    continue
                conf = hit / n
                p = fisher_exact([[hit, n - hit], [ny - hit, len(qs) - n - ny + hit]], alternative="greater")[1]
                rows.append({"điều_kiện": " VÀ ".join(combo), "kết_quả": t, "số_câu_khớp": n, "số_câu_đúng": hit,
                             "confidence": conf, "tỉ_lệ_nền": base, "lift": conf / base, "p": p,
                             "số_họ": fam[m & y].nunique(), "ví_dụ": ", ".join(list(y.index[m & y])[:6])})
    ru = pd.DataFrame(rows).sort_values("p").reset_index(drop=True)
    n_tests = len(ru)
    ru["p_hiệu_chỉnh"] = (ru.p * n_tests / np.arange(1, n_tests + 1))[::-1].cummin()[::-1].clip(upper=1)
    ru = ru[(ru.số_họ >= MIN_FAM) & (ru.lift > 1.5) & (ru.p_hiệu_chỉnh < 0.05)]
    # bỏ luật 2 điều kiện không tốt hơn luật 1 điều kiện chứa nó (cùng kết quả, cùng số câu đúng)
    single = {(r.điều_kiện, r.kết_quả): r.confidence for r in ru.itertuples() if " VÀ " not in r.điều_kiện}
    keep = []
    for r in ru.itertuples():
        parts = r.điều_kiện.split(" VÀ ")
        keep.append(len(parts) == 1 or all(r.confidence > single.get((p, r.kết_quả), 0) + 1e-9 for p in parts))
    return ru[keep].sort_values(["kết_quả", "p"]), n_tests


def main():
    T1, T2 = times(1), times(2)
    f = E.load_features(os.path.join(R, "logs/mac/exp2/exp2_explain_job.jsonl"),
                        os.path.join(R, "lqo_ml_perspective/bao/queries/join-order-benchmark"), "JOB")
    qs = sorted(set(T1.index) & set(T2.index) & set(f.index))
    T1, T2, f = T1.loc[qs], T2.loc[qs], f.loc[qs]
    X = f.drop(columns=["explain_ms"])
    fam = pd.Series({q: E.template_for(q, "JOB") for q in qs})
    lab1, _ = E.labels(T1)
    lab2, _ = E.labels(T2)

    # ---------------- 1. luật kết hợp
    tg = pd.DataFrame(index=qs)
    for h in HINTS[1:]:
        tg[f"tắt {h[3:]} giúp"] = (T1[h] < .95 * T1.default) & (T2[h] < .95 * T2.default)
        tg[f"tắt {h[3:]} hại ≥2×"] = (T1[h] > 2 * T1.default) & (T2[h] > 2 * T2.default)
    items = conditions(X, qs)
    rules, n_tests = mine_rules(items, tg, fam, qs)
    rules.to_csv(os.path.join(OUT, "exp2_mining_rules.csv"), index=False)
    pd.DataFrame({"kết_quả": tg.columns, "số_câu": tg.sum().values, "tỉ_lệ": tg.mean().values}).to_csv(
        os.path.join(OUT, "exp2_mining_targets.csv"), index=False)

    # ví dụ rủi ro bất đối xứng: áp "có ≥2 hash join → tắt hash join" cho mọi câu khớp
    m = X.plan_n_hashjoin >= 2
    risk = pd.DataFrame({"query_id": np.array(qs)[m.values], "PG_ms": T2.default[m].values,
                         "no_hashjoin_ms": T2.no_hashjoin[m].values})
    risk["chênh_s"] = (risk.PG_ms - risk.no_hashjoin_ms) / 1000
    risk.sort_values("chênh_s").to_csv(os.path.join(OUT, "exp2_mining_hashjoin_risk.csv"), index=False)

    # ---------------- số liệu tóm tắt
    allnl = (X.plan_n_hashjoin == 0) & (X.plan_n_mergejoin == 0) & (X.sql_n_tables <= 8)
    gain = T2.default - T2.min(axis=1)
    summ = {
        "số_câu": len(qs), "số_họ": int(fam.nunique()), "số_điều_kiện": len(items), "số_luật_đã_thử": int(n_tests),
        "số_luật_giữ_lại": int(len(rules)), "ARI_nhãn_lần2_vs_lần3": float(adjusted_rand_score(lab1, lab2)),
        "đặc_trưng_hằng_số": [c for c in X.columns if X[c].nunique() == 1],
        "nhóm_ít_bảng_toàn_NL": {"số_câu": int(allnl.sum()), "PG_s": float(T2.default[allnl].sum() / 1000),
                                 "PG_tổng_s": float(T2.default.sum() / 1000),
                                 "oracle_gain_s": float(gain[allnl].sum() / 1000),
                                 "oracle_gain_tổng_s": float(gain.sum() / 1000)},
        "hashjoin_rule": {"số_câu": int(m.sum()), "giúp": int(tg.loc[m, "tắt hashjoin giúp"].sum()),
                          "hại_2x": int(tg.loc[m, "tắt hashjoin hại ≥2×"].sum()),
                          "speedup_nếu_áp_hết": float(risk.PG_ms.sum() / risk.no_hashjoin_ms.sum())},
    }
    with open(os.path.join(OUT, "exp2_mining_summary.json"), "w") as fo:
        json.dump(summ, fo, ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    print(rules[["điều_kiện", "kết_quả", "số_câu_khớp", "số_câu_đúng", "confidence", "lift", "số_họ"]].round(2).to_string())


if __name__ == "__main__":
    main()
