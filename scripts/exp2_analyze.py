"""Thí nghiệm 2 (Mục 4.3 báo cáo): mô hình phân loại chọn 1 trong 6 phương án cho mỗi câu SQL.

Dữ liệu vào (từ scripts/exp2_collect.sh và exp2_collect_ceb.sh):
  logs/exp2_hintsets_job.jsonl   113 câu JOB × 6 phương án × 3 lần (run_and_log.py)
  logs/exp2_explain_job.jsonl    plan mặc định từ EXPLAIN (không ANALYZE) + thời gian gọi EXPLAIN
  logs/exp2_hintsets_ceb.jsonl, logs/exp2_explain_ceb.jsonl   (tùy chọn) khoảng 200 câu CEB-IMDb

Quy trình:
  Nhãn     : phương án có thời gian end-to-end (lập kế hoạch + thực thi, lần chạy thứ 3) nhỏ nhất; giữ default
             nếu không nhanh hơn default ít nhất 5%. Phương án cho ra cùng cây plan với default dùng thời gian
             của default (tránh gán nhãn theo nhiễu đo).
  Đặc trưng: câu SQL + plan mặc định từ EXPLAIN (chi phí, số dòng ước lượng, loại toán tử). Không dùng gì có
             được sau khi chạy (không q-error, không thời gian thực).
  Mô hình  : Decision Tree (mốc cơ sở), Random Forest (mô hình chính), LightGBM (cải tiến). Siêu tham số cố
             định, không tinh chỉnh trên tập test.
  Chia     : đúng 9 split JOB của bài báo (LOO/RND/BQ × 3, thư mục lqo_ml_perspective/bao/queries/job__*).
             CEB-IMDb (nếu có) chỉ được thêm vào tập train, không bao giờ vào tập test.
  Thời gian của mô hình = EXPLAIN + suy luận + thời gian của phương án được chọn.
  Mốc so sánh: PostgreSQL (default), Bao (log đo công bằng 08–10/11, analysis/output/c1_Bao_job__*_fair*),
               Oracle (biết trước phương án nhanh nhất, không tốn EXPLAIN/suy luận).

  <python có sklearn lightgbm pandas scipy> scripts/exp2_analyze.py
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.insert(0, os.path.dirname(__file__))
from extract_features import plan_features, plan_signature, sql_features  # noqa: E402
from lqo_common import norm_qid, template_of  # noqa: E402

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEED = 42
EPS = 0.10
HINTS = ["default", "no_nestloop", "no_hashjoin", "no_mergejoin", "no_seqscan", "no_indexscan"]
SPLITS = [f"{k}_split_{i}" for k in ("leave_one_out", "random", "base_query") for i in (1, 2, 3)]
SHORT = {"leave_one_out": "LOO", "random": "RND", "base_query": "BQ"}
DROP = {"plan_max_qerror", "plan_mean_log_qerror"}          # cần số dòng thực tế → không dùng


def short(split):
    k, i = split.rsplit("_split_", 1)
    return f"{SHORT[k]}-{i}"


def models():
    from lightgbm import LGBMClassifier
    return {
        "DecisionTree": DecisionTreeClassifier(max_depth=4, min_samples_leaf=3, random_state=SEED),
        "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=2, random_state=SEED,
                                               n_jobs=1),
        "LightGBM": LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=5,
                                   random_state=SEED, verbose=-1, n_jobs=1),
    }


def qid_of(raw, bench):
    return norm_qid(raw) if bench == "JOB" else raw


def template_for(qid, bench):
    return template_of(qid) if bench == "JOB" else "ceb_" + qid.split("_")[0].replace("ceb", "")


def load_times(path, bench):
    """Bảng thời gian (ms) theo (câu, phương án), lần chạy thứ 3; timeout = 180 s."""
    rows, plans = [], {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r["run"] != 2:
                continue
            q = qid_of(r["query_id"], bench)
            ms = (r["planning_ms"] or 0.0) + r["execution_ms"]
            rows.append((q, r["hint_set"], ms, bool(r["timeout"])))
            if r.get("plan") is not None:
                plans[(q, r["hint_set"])] = plan_signature(r["plan"])
    df = pd.DataFrame(rows, columns=["query_id", "hint_set", "ms", "timeout"])
    t = df.pivot_table(index="query_id", columns="hint_set", values="ms", aggfunc="first")
    t = t.reindex(columns=HINTS).dropna(subset=["default"])
    n_same = 0
    for q in t.index:
        base = plans.get((q, "default"))
        for h in HINTS[1:]:
            if base is not None and plans.get((q, h)) == base:
                t.loc[q, h] = t.loc[q, "default"]
                n_same += 1
    t = t.fillna(180_000.0)                                      # thiếu số đo → coi như timeout
    to = df[df.timeout].groupby("hint_set").size().to_dict()
    return t, n_same, to


def labels(t, min_gain=0.05):
    best = t.idxmin(axis=1)
    best_ms = t.min(axis=1)
    keep = best_ms > t["default"] * (1 - min_gain)
    best[keep] = "default"
    best_ms[keep] = t["default"][keep]
    return best, best_ms


def load_features(explain_path, sql_dir, bench):
    sqls = {qid_of(os.path.splitext(os.path.basename(fp))[0], bench): open(fp).read()
            for fp in glob.glob(os.path.join(sql_dir, "**/*.sql"), recursive=True)}
    rows = []
    with open(explain_path) as f:
        for line in f:
            r = json.loads(line)
            q = qid_of(r["query_id"], bench)
            x = {"query_id": q, "explain_ms": r["explain_ms"]}
            x.update(sql_features(sqls.get(q, "")))
            x.update({k: v for k, v in plan_features(r["plan"]).items() if k not in DROP})
            rows.append(x)
    return pd.DataFrame(rows).set_index("query_id")


def split_lists(split):
    d = os.path.join(R, "lqo_ml_perspective/bao/queries", f"job__{split}")
    get = lambda s: sorted(norm_qid(f) for f in glob.glob(os.path.join(d, s, "*.sql")))  # noqa: E731
    return get("train"), get("test")


def bao_per_query(split):
    fs = sorted(glob.glob(os.path.join(R, f"analysis/output/c1_Bao_job__{split}_fair*_per_query.csv")))
    fs = [f for f in fs if "imdb50" not in f]
    if not fs:
        return None
    b = pd.read_csv(fs[-1])
    b["query_id"] = b.query_id.map(norm_qid)
    return b.set_index("query_id")


def summarize(split, method, pg, cand, acc=None, train_src=""):
    sp = pg / cand
    w, l = int((sp > 1 + EPS).sum()), int((sp < 1 - EPS).sum())
    return {"split": short(split), "kiểu": short(split).split("-")[0], "phương_pháp": method,
            "train": train_src, "số_câu": len(sp), "thắng": w, "hòa": len(sp) - w - l, "thua": l,
            "PG_s": pg.sum() / 1000, "phương_pháp_s": cand.sum() / 1000, "speedup": pg.sum() / cand.sum(),
            "speedup_trung_vị": float(np.median(sp)), "chậm_đi_>10%": l, "accuracy": acc,
            "p_sign": binomtest(w, w + l).pvalue if w + l else 1.0,
            "p_wilcoxon": wilcoxon(pg, cand).pvalue if (pg != cand).any() else 1.0}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out_dir", default=os.path.join(R, "analysis/output/exp2"))
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    t_job, same_job, to_job = load_times(os.path.join(R, "logs/exp2_hintsets_job.jsonl"), "JOB")
    y_job, best_job = labels(t_job)
    f_job = load_features(os.path.join(R, "logs/exp2_explain_job.jsonl"),
                          os.path.join(R, "lqo_ml_perspective/bao/queries/join-order-benchmark"), "JOB")
    data = {"JOB": (t_job, y_job, best_job, f_job)}
    info = [f"JOB: {len(t_job)} câu, {same_job} cặp (câu, phương án) trùng plan với default, timeout: {to_job}",
            f"Nhãn JOB: {y_job.value_counts().to_dict()}"]

    ceb_log = os.path.join(R, "logs/exp2_hintsets_ceb.jsonl")
    if os.path.exists(ceb_log) and os.path.exists(os.path.join(R, "logs/exp2_explain_ceb.jsonl")):
        t_ceb, same_ceb, to_ceb = load_times(ceb_log, "CEB")
        y_ceb, best_ceb = labels(t_ceb)
        f_ceb = load_features(os.path.join(R, "logs/exp2_explain_ceb.jsonl"),
                              os.path.join(R, "lqo_ml_perspective/bao/queries/ceb_imdb"), "CEB")
        data["CEB"] = (t_ceb, y_ceb, best_ceb, f_ceb)
        info += [f"CEB: {len(t_ceb)} câu, {same_ceb} cặp trùng plan, timeout: {to_ceb}",
                 f"Nhãn CEB: {y_ceb.value_counts().to_dict()}"]

    # Bảng nhãn + thời gian mọi phương án (để trình bày "phân bố nhãn" và oracle)
    lab_rows = []
    for bench, (t, y, best, f) in data.items():
        d = t.copy()
        d.columns = [f"t_{c}_ms" for c in d.columns]
        d["nhãn"] = y
        d["best_ms"] = best
        d["benchmark"] = bench
        d["template"] = [template_for(q, bench) for q in d.index]
        lab_rows.append(d)
    pd.concat(lab_rows).to_csv(os.path.join(a.out_dir, "exp2_labels.csv"), index_label="query_id")

    xcols = [c for c in f_job.columns if c != "explain_ms"]
    sources = {"JOB": ["JOB"]}
    if "CEB" in data:
        sources["JOB+CEB"] = ["JOB", "CEB"]

    rows, perq = [], []
    for split in SPLITS:
        tr, te = split_lists(split)
        te = [q for q in te if q in t_job.index and q in f_job.index]
        pg = t_job.loc[te, "default"].to_numpy()
        rows.append(summarize(split, "PostgreSQL", pg, pg))
        rows.append(summarize(split, "Oracle", pg, best_job.loc[te].to_numpy(),
                              acc=1.0))
        b = bao_per_query(split)
        if b is not None:
            bb = b.loc[[q for q in te if q in b.index]]
            rows.append(summarize(split, "Bao", bb.total_ms_pg.to_numpy(), bb.total_ms_lqo.to_numpy()))
        for src, benches in sources.items():
            Xs, ys = [], []
            for bench in benches:
                t, y, _, f = data[bench]
                qs = [q for q in (tr if bench == "JOB" else t.index) if q in f.index and q in y.index]
                Xs.append(f.loc[qs, xcols].astype(float).to_numpy())
                ys.append(y.loc[qs].to_numpy())
            X, Y = np.vstack(Xs), np.concatenate(ys)
            Xte = f_job.loc[te, xcols].astype(float).to_numpy()
            for name, m in models().items():
                if len(set(Y)) == 1:
                    pred, inf_ms = np.array([Y[0]] * len(te)), np.zeros(len(te))
                else:
                    m.fit(X, Y)
                    pred = m.predict(Xte)
                    inf_ms = []
                    for i in range(len(te)):            # thời gian suy luận cho TỪNG câu (như khi dùng thật)
                        ts = []
                        for _ in range(5):
                            t0 = time.perf_counter()
                            m.predict(Xte[i:i + 1])
                            ts.append((time.perf_counter() - t0) * 1000)
                        inf_ms.append(np.median(ts))
                    inf_ms = np.array(inf_ms)
                chosen = np.array([t_job.loc[q, h] for q, h in zip(te, pred)])
                e2e = f_job.loc[te, "explain_ms"].to_numpy() + inf_ms + chosen
                acc = float((pred == y_job.loc[te].to_numpy()).mean())
                rows.append(summarize(split, name, pg, e2e, acc=acc, train_src=src))
                perq.append(pd.DataFrame({"split": short(split), "train": src, "mô_hình": name, "query_id": te,
                                          "nhãn_thật": y_job.loc[te].to_numpy(), "dự_đoán": pred,
                                          "PG_ms": pg, "explain_ms": f_job.loc[te, "explain_ms"].to_numpy(),
                                          "suy_luận_ms": inf_ms, "phương_án_ms": chosen, "e2e_ms": e2e,
                                          "oracle_ms": best_job.loc[te].to_numpy()}))

    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(a.out_dir, "exp2_summary_per_split.csv"), index=False)
    pq = pd.concat(perq)
    pq.to_csv(os.path.join(a.out_dir, "exp2_per_query.csv"), index=False)

    # Tổng theo kiểu chia và toàn bộ 233 lần kiểm tra
    agg = summ.groupby(["phương_pháp", "train", "kiểu"], dropna=False)[
        ["số_câu", "thắng", "hòa", "thua", "PG_s", "phương_pháp_s"]].sum().reset_index()
    tot = summ.groupby(["phương_pháp", "train"], dropna=False)[
        ["số_câu", "thắng", "hòa", "thua", "PG_s", "phương_pháp_s"]].sum().reset_index()
    tot["kiểu"] = "Tổng"
    agg = pd.concat([agg, tot])
    agg["speedup"] = agg.PG_s / agg.phương_pháp_s
    order = {"LOO": 0, "RND": 1, "BQ": 2, "Tổng": 3}
    agg = agg.sort_values(["phương_pháp", "train", "kiểu"], key=lambda s: s.map(order) if s.name == "kiểu" else s)
    agg.to_csv(os.path.join(a.out_dir, "exp2_summary_by_type.csv"), index=False)

    # Luật chọn phương án: cây quyết định train trên toàn bộ dữ liệu của nguồn lớn nhất
    src = list(sources)[-1]
    X = np.vstack([data[b][3].loc[data[b][1].index.intersection(data[b][3].index), xcols].astype(float).to_numpy()
                   for b in sources[src]])
    Y = np.concatenate([data[b][1].loc[data[b][1].index.intersection(data[b][3].index)].to_numpy()
                        for b in sources[src]])
    dt = models()["DecisionTree"].fit(X, Y)
    rf = models()["RandomForest"].fit(X, Y)
    with open(os.path.join(a.out_dir, "exp2_rules_decision_tree.txt"), "w") as f:
        f.write(f"Cây quyết định (độ sâu ≤ 4) train trên toàn bộ {src} ({len(Y)} câu)\n\n")
        f.write(export_text(dt, feature_names=xcols))
    imp = pd.Series(rf.feature_importances_, index=xcols).sort_values(ascending=False)
    imp.to_csv(os.path.join(a.out_dir, "exp2_feature_importance_rf.csv"), header=["importance"])

    with open(os.path.join(a.out_dir, "exp2_tomtat.txt"), "w") as f:
        f.write("\n".join(info) + "\n\n")
        cols = ["phương_pháp", "train", "kiểu", "số_câu", "thắng", "hòa", "thua", "PG_s", "phương_pháp_s", "speedup"]
        f.write(agg[cols].round(3).to_string(index=False) + "\n\n")
        f.write(summ.round(3).to_string(index=False) + "\n\n10 đặc trưng quan trọng nhất (Random Forest):\n")
        f.write(imp.head(10).round(3).to_string() + "\n")
    print(open(os.path.join(a.out_dir, "exp2_tomtat.txt")).read())


if __name__ == "__main__":
    main()
