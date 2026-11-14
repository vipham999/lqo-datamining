"""Khai phá dữ liệu trên kết quả Thí nghiệm 2 (không chạy thêm truy vấn, chỉ đọc lại log).

Dữ liệu vào:
  logs/exp2_hintsets_job.jsonl   113 câu JOB × 6 phương án × 3 lần chạy (thời gian thật)
  logs/exp2_explain_job.jsonl    plan mặc định (EXPLAIN) → 34 đặc trưng, như exp2_analyze.py
  analysis/output/exp2/exp2_per_query.csv   thời gian EXPLAIN đã đo (để đánh giá chính sách theo cụm)

Hai kỹ thuật:
  1. Luật kết hợp (dạng "điều kiện → kết quả"): đặc trưng rời rạc hoá thành điều kiện có/không; kết quả là
     "tắt X giúp ≥5%" hoặc "tắt X hại ≥2 lần", phải đúng ở CẢ lần chạy 2 và 3 (tránh nhiễu đo).
     Duyệt mọi tổ hợp 1–2 điều kiện; giữ luật có ≥6 câu khớp, ≥4 câu đúng, phủ ≥3 họ câu; kiểm định Fisher
     một phía + hiệu chỉnh Benjamini–Hochberg.
  2. Phân cụm KMeans trên 34 đặc trưng (log1p + chuẩn hoá), k = 2..8, chọn k theo silhouette; so cụm với
     nhãn bằng ARI; thử chính sách "mỗi cụm một phương án" trên 9 split của bài báo.

  <python có sklearn pandas scipy> scripts/exp2_mining.py
"""
import itertools
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import exp2_analyze as E  # noqa: E402
from extract_features import plan_signature  # noqa: E402

R = E.R
OUT = os.path.join(R, "analysis/output/exp2")
HINTS = E.HINTS
SEED = 42
MIN_MATCH, MIN_HIT, MIN_FAM = 6, 4, 3
KS = range(2, 9)


def times(run):
    """Thời gian (ms) theo câu × phương án ở một lần chạy; plan trùng default → dùng thời gian default."""
    rows, plans = [], {}
    with open(os.path.join(R, "logs/exp2_hintsets_job.jsonl")) as f:
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


def log_std(X, fit=None):
    Z = np.log1p(X.astype(float).clip(lower=0))
    sc = fit or StandardScaler().fit(Z)
    return sc.transform(Z), sc


def main():
    T1, T2 = times(1), times(2)
    f = E.load_features(os.path.join(R, "logs/exp2_explain_job.jsonl"),
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

    # ---------------- 2. phân cụm
    Z, _ = log_std(X)
    sil = []
    for k in KS:
        lab = KMeans(k, n_init=20, random_state=SEED).fit_predict(Z)
        sil.append({"k": k, "silhouette": silhouette_score(Z, lab), "ARI_với_nhãn": adjusted_rand_score(lab2, lab),
                    "ARI_với_họ": adjusted_rand_score(fam, lab)})
    sil = pd.DataFrame(sil)
    best_k = int(sil.loc[sil.silhouette.idxmax(), "k"])
    raw = KMeans(best_k, n_init=20, random_state=SEED).fit_predict(Z)
    order = pd.Series(T2.default.values, index=raw).groupby(level=0).sum().sort_values(ascending=False).index
    rename = {c: f"Cụm {i + 1}" for i, c in enumerate(order)}           # Cụm 1 = tốn thời gian nhất
    cl = pd.Series([rename[c] for c in raw], index=qs)
    xy = PCA(2, random_state=SEED).fit_transform(Z)
    pts = pd.DataFrame({"query_id": qs, "cụm": cl.values, "PC1": xy[:, 0], "PC2": xy[:, 1], "nhãn": lab2.values,
                        "PG_ms": T2.default.values, "oracle_ms": T2.min(axis=1).values, "họ": fam.values})
    pts.to_csv(os.path.join(OUT, "exp2_mining_clusters.csv"), index=False)
    prof = []
    for c, g in pts.groupby("cụm"):
        xs = X.loc[g.query_id]
        tot = T2.loc[g.query_id].sum()
        bh = tot.idxmin()
        prof.append({"cụm": c, "số_câu": len(g), "số_họ": g.họ.nunique(), "số_bảng_TB": xs.sql_n_tables.mean(),
                     "nested_loop_TB": xs.plan_n_nestloop.mean(), "hash_join_TB": xs.plan_n_hashjoin.mean(),
                     "cost_trung_vị": xs.plan_total_cost.median(), "PG_s": g.PG_ms.sum() / 1000,
                     "oracle_s": g.oracle_ms.sum() / 1000, "nhãn_phổ_biến": g.nhãn.value_counts().index[0],
                     "tỉ_lệ_nhãn_phổ_biến": g.nhãn.value_counts().iloc[0] / len(g),
                     "nhãn": ", ".join(f"{k} {v}" for k, v in g.nhãn.value_counts().items()),
                     "phương_án_chung_tốt_nhất": bh, "speedup_phương_án_chung": tot["default"] / tot[bh],
                     "ví_dụ": ", ".join(g.query_id.head(6))})
    pd.DataFrame(prof).to_csv(os.path.join(OUT, "exp2_mining_cluster_profile.csv"), index=False)

    # chính sách "mỗi cụm một phương án": fit trên train, áp lên test, 9 split (cộng thời gian EXPLAIN)
    ex = pd.read_csv(os.path.join(OUT, "exp2_per_query.csv")).drop_duplicates("query_id").set_index("query_id").explain_ms
    pol_rows = []
    for k in KS:
        pg_s = c_s = 0.0
        W = L = N = 0
        for sp in E.SPLITS:
            tr, te = E.split_lists(sp)
            tr, te = [q for q in tr if q in qs], [q for q in te if q in qs]
            Ztr, sc = log_std(X.loc[tr])
            km = KMeans(k, n_init=20, random_state=SEED).fit(Ztr)
            pol = {}
            for c in range(k):
                tot = T2.loc[np.array(tr)[km.labels_ == c]].sum()
                pol[c] = tot.idxmin() if tot.min() < .95 * tot["default"] else "default"
            cte = km.predict(log_std(X.loc[te], sc)[0])
            cand = np.array([T2.loc[q, pol[c]] for q, c in zip(te, cte)]) + ex.reindex(te).fillna(ex.median()).values
            pg = T2.loc[te, "default"].values
            s = pg / cand
            pg_s += pg.sum()
            c_s += cand.sum()
            W += int((s > 1 + E.EPS).sum())
            L += int((s < 1 - E.EPS).sum())
            N += len(te)
        pol_rows.append({"k": k, "speedup": pg_s / c_s, "thắng": W, "hòa": N - W - L, "thua": L, "số_lần": N})
    pd.DataFrame(pol_rows).to_csv(os.path.join(OUT, "exp2_mining_cluster_policy.csv"), index=False)
    sil.to_csv(os.path.join(OUT, "exp2_mining_silhouette.csv"), index=False)

    # ---------------- số liệu tóm tắt
    allnl = (X.plan_n_hashjoin == 0) & (X.plan_n_mergejoin == 0) & (X.sql_n_tables <= 8)
    gain = T2.default - T2.min(axis=1)
    summ = {
        "số_câu": len(qs), "số_họ": int(fam.nunique()), "số_điều_kiện": len(items), "số_luật_đã_thử": int(n_tests),
        "số_luật_giữ_lại": int(len(rules)), "k_tốt_nhất": best_k,
        "silhouette_tốt_nhất": float(sil.silhouette.max()),
        "ARI_nhãn_max": float(sil.ARI_với_nhãn.max()), "ARI_nhãn_lần2_vs_lần3": float(adjusted_rand_score(lab1, lab2)),
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
    print(pd.DataFrame(prof)[["cụm", "số_câu", "số_bảng_TB", "nested_loop_TB", "hash_join_TB", "PG_s", "oracle_s", "nhãn"]].round(1).to_string())
    print(pd.DataFrame(pol_rows).round(2).to_string())


if __name__ == "__main__":
    main()
