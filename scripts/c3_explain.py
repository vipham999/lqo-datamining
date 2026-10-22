"""C3 – Giải thích vì sao plan mới nhanh/chậm hơn plan cũ bằng data mining.

  python scripts/c3_explain.py --features analysis/output/features.csv \
      --labels analysis/output/labels.csv --log logs/job_hintsets.jsonl

1. Phân cụm K-means (k chọn theo silhouette) trên đặc trưng của plan mặc định:
   cụm nào có plan tốt hơn default, speedup bao nhiêu.
2. Luật kết hợp (Apriori): {đặc điểm truy vấn/plan} → best = <hint set>.
3. Độ quan trọng đặc trưng (permutation importance của Random Forest).
4. Cây quyết định độ sâu 3 → luật dễ đọc.
5. Tree edit distance giữa plan cũ và plan tốt nhất, tương quan Spearman với speedup.
"""
import argparse
import os
import sys
import warnings

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from lqo_common import read_plans  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 42


def load(a):
    feat = pd.read_csv(a.features, keep_default_na=False, na_values=[""])
    feat = feat[(feat.hint_set == "default") & (feat.tag.fillna("") == a.tag)]
    lab = pd.read_csv(a.labels)
    df = feat.merge(lab, on=["query_id", "template"], how="inner").reset_index(drop=True)
    xcols = [c for c in df.columns if c.startswith(("sql_", "plan_")) and c != "plan_signature"]
    xcols = [c for c in xcols if df[c].nunique() > 1]
    return df, xcols


def clustering(df, xcols, out):
    Xs = StandardScaler().fit_transform(df[xcols].astype(float))
    best_k, best_s = 2, -1
    for k in range(2, min(9, len(df) - 1)):
        s = silhouette_score(Xs, KMeans(k, n_init=10, random_state=SEED).fit_predict(Xs))
        if s > best_s:
            best_k, best_s = k, s
    df["cụm"] = KMeans(best_k, n_init=10, random_state=SEED).fit_predict(Xs)
    summ = df.groupby("cụm").agg(
        số_câu=("query_id", "size"),
        tỉ_lệ_có_plan_tốt_hơn=("best_hint_set", lambda s: (s != "default").mean()),
        speedup_trung_vị=("speedup_vs_default", "median"),
        speedup_max=("speedup_vs_default", "max"),
        hint_set_phổ_biến=("best_hint_set", lambda s: s.value_counts().index[0]),
        số_bảng_tb=("sql_n_tables", "mean"),
        nestloop_tb=("plan_n_nestloop", "mean"),
        ví_dụ=("query_id", lambda s: ", ".join(list(s)[:5])),
    )
    summ.to_csv(os.path.join(out, "c3_clusters.csv"))
    print(f"\n=== 1. K-means: k = {best_k} (silhouette = {best_s:.3f})\n{summ.round(3).to_string()}")

    xy = PCA(2, random_state=SEED).fit_transform(Xs)
    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(xy[:, 0], xy[:, 1], c=df["cụm"], cmap="tab10", s=20 + 30 * np.log2(df.speedup_vs_default))
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("Cụm truy vấn theo đặc trưng plan mặc định (kích thước ~ speedup)")
    fig.colorbar(sc, label="cụm")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "c3_clusters_pca.png"), dpi=150)


def to_items(df):
    q = lambda c: df[c].quantile(0.75)  # noqa: E731
    items = pd.DataFrame({
        f"nhiều_bảng(≥{int(q('sql_n_tables'))})": df.sql_n_tables >= q("sql_n_tables"),
        "có_LIKE": df.sql_n_like > 0,
        "có_IN": df.sql_n_in > 0,
        "có_OR": df.sql_n_or > 0,
        "có_BETWEEN": df.sql_n_between > 0,
        "PG_dùng_NestLoop": df.plan_n_nestloop > 0,
        "PG_dùng_HashJoin": df.plan_n_hashjoin > 0,
        "PG_dùng_MergeJoin": df.plan_n_mergejoin > 0,
        "PG_dùng_SeqScan": df.plan_n_seqscan > 0,
        "PG_plan_bushy": df.plan_is_bushy > 0,
        "sai_cardinality_lớn(q-error≥100)": df.plan_max_qerror >= 100,
        "cost_cao(top25%)": df.plan_total_cost >= q("plan_total_cost"),
    })
    for hs in df.best_hint_set.unique():
        items[f"best={hs}"] = df.best_hint_set == hs
    return items.astype(bool)


def assoc_rules(df, out, min_support, min_conf):
    try:
        from mlxtend.frequent_patterns import apriori, association_rules
    except ImportError:
        print("\n=== 2. Bỏ qua luật kết hợp (chưa cài mlxtend)")
        return
    items = to_items(df)
    freq = apriori(items, min_support=min_support, use_colnames=True, max_len=4)
    if freq.empty:
        print("\n=== 2. Không có tập phổ biến nào với min_support hiện tại")
        return
    rules = association_rules(freq, metric="confidence", min_threshold=min_conf)
    rules = rules[rules.consequents.map(lambda c: len(c) == 1 and next(iter(c)).startswith("best="))]
    rules = rules[~rules.antecedents.map(lambda c: any(x.startswith("best=") for x in c))]
    rules = rules.sort_values(["lift", "confidence"], ascending=False)
    rules["luật"] = rules.antecedents.map(lambda s: " ∧ ".join(sorted(s))) + "  →  " + \
        rules.consequents.map(lambda s: next(iter(s)))
    rules[["luật", "support", "confidence", "lift"]].to_csv(os.path.join(out, "c3_rules.csv"), index=False)
    print(f"\n=== 2. Luật kết hợp (top 15 theo lift, {len(rules)} luật):")
    print(rules[["luật", "support", "confidence", "lift"]].head(15).round(3).to_string(index=False))


def importance(df, xcols, out):
    X, y = df[xcols].astype(float), df.best_hint_set
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=SEED).fit(X, y)
    pi = permutation_importance(rf, X, y, n_repeats=20, random_state=SEED)
    imp = pd.DataFrame({"đặc_trưng": xcols, "importance": pi.importances_mean, "std": pi.importances_std})
    imp = imp.sort_values("importance", ascending=False)
    imp.to_csv(os.path.join(out, "c3_feature_importance.csv"), index=False)
    print("\n=== 3. Permutation importance (top 10):\n" + imp.head(10).round(4).to_string(index=False))

    top = imp.head(15)[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(top.đặc_trưng, top.importance, xerr=top["std"])
    ax.set_title("Đặc trưng quyết định plan tốt nhất")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "c3_feature_importance.png"), dpi=150)

    tree = DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=SEED).fit(X, y)
    rules = export_text(tree, feature_names=xcols)
    open(os.path.join(out, "c3_decision_tree.txt"), "w").write(rules)
    print("\n=== 4. Cây quyết định (độ sâu 3):\n" + rules)


def tree_edit_distance(df, log, out):
    try:
        from zss import Node, simple_distance
    except ImportError:
        print("\n=== 5. Bỏ qua tree edit distance (chưa cài zss)")
        return
    plans = read_plans(log)

    def to_zss(p):
        n = Node(p["Node Type"] + (f":{p['Alias']}" if "Alias" in p else ""))
        for c in p.get("Plans", []):
            n.addkid(to_zss(c))
        return n

    rows = []
    for _, r in df.iterrows():
        old = plans.get((r.query_id, "default", ""))
        new = plans.get((r.query_id, r.best_hint_set, ""))
        if old is None or new is None:
            continue
        rows.append({"query_id": r.query_id, "best_hint_set": r.best_hint_set,
                     "TED": simple_distance(to_zss(old), to_zss(new)), "speedup": r.speedup_vs_default})
    ted = pd.DataFrame(rows)
    if ted.empty:
        print("\n=== 5. Không đủ plan để tính tree edit distance")
        return
    ted.to_csv(os.path.join(out, "c3_tree_edit_distance.csv"), index=False)
    changed = ted[ted.TED > 0]
    rho, p = spearmanr(changed.TED, changed.speedup) if len(changed) > 2 else (float("nan"), float("nan"))
    print(f"\n=== 5. Tree edit distance: {len(changed)}/{len(ted)} truy vấn có plan tốt nhất khác plan cũ; "
          f"TED trung vị = {changed.TED.median() if len(changed) else 0:.1f}; "
          f"Spearman(TED, speedup) = {rho:.3f} (p = {p:.4f})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--features", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--log", help="JSONL để tính tree edit distance")
    p.add_argument("--tag", default="")
    p.add_argument("--min_support", type=float, default=0.05)
    p.add_argument("--min_conf", type=float, default=0.5)
    p.add_argument("--out_dir", default="analysis/output")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    df, xcols = load(a)
    print(f"{len(df)} truy vấn, {len(xcols)} đặc trưng")
    clustering(df, xcols, a.out_dir)
    assoc_rules(df, a.out_dir, a.min_support, a.min_conf)
    importance(df, xcols, a.out_dir)
    if a.log:
        tree_edit_distance(df, a.log, a.out_dir)
    print(f"\nĐã lưu vào {a.out_dir}/c3_*")


if __name__ == "__main__":
    main()
