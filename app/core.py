"""Lõi tính toán của ứng dụng: đọc dữ liệu, cross-validation theo 3 kiểu chia của bài báo, đánh giá, data mining.
Dùng lại hàm của scripts/ (extract_features, c2_classify, c3_explain) để kết quả khớp với các script dòng lệnh."""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import confusion_matrix, f1_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from c2_classify import SEED, folds, models  # noqa: E402
from c3_explain import to_items  # noqa: E402

OUT = os.path.join(ROOT, "analysis/output")
APP_OUT = os.path.join(OUT, "app")

# Màu cố định theo thực thể (palette mặc định của dataviz, thứ tự cố định, không xoay vòng)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
METHODS = ["PostgreSQL", "Bao", "HybridQO", "Neo", "Balsa", "LEON"]
HINT_SETS = ["default", "no_nestloop", "no_hashjoin", "no_mergejoin", "no_seqscan", "no_indexscan"]
ENTITY_ORDER = METHODS + HINT_SETS
COLOR = {**{m: PALETTE[i] for i, m in enumerate(METHODS)}, **{h: PALETTE[i] for i, h in enumerate(HINT_SETS)}}

SOURCES = {
    "A": {"ten": "A – Log của tác giả (nhãn = phương pháp nhanh nhất)", "baseline": "PostgreSQL",
          "files": [os.path.join(APP_OUT, "dataset_a.csv")]},
    "B": {"ten": "B – 6 hint set tự chạy (nhãn = hint set nhanh nhất)", "baseline": "default",
          "files": [os.path.join(OUT, "features.csv"), os.path.join(OUT, "labels.csv")]},
}
SCHEMES = {"leave_one_out": "Leave One Out (dễ)", "random": "Random (trung bình)",
           "base_query": "Base Query (khó)"}
TASKS = {"binary": "2 lớp: giữ PostgreSQL hay đổi plan", "multi": "Nhiều lớp: nên dùng plan nào"}
KEEP, SWITCH = "Giữ plan mặc định", "Đổi plan"
ALWAYS_PG, OPTIMAL = "Luôn PostgreSQL", "Mốc tối ưu"


def colors_for(names):
    """Màu cho một danh sách thực thể, mỗi thực thể luôn cùng một màu dù có lọc."""
    order = [n for n in ENTITY_ORDER if n in names] + [n for n in names if n not in ENTITY_ORDER]
    return order, [COLOR.get(n, "#898781") for n in order]


# ---------------------------------------------------------------- dữ liệu
def available(key):
    return all(os.path.exists(f) for f in SOURCES[key]["files"])


def load_source(key):
    """Trả về (df, xcols, baseline, classes). Mỗi dòng là một câu truy vấn."""
    if key == "A":
        df = pd.read_csv(SOURCES["A"]["files"][0])
    else:
        feat = pd.read_csv(SOURCES["B"]["files"][0], keep_default_na=False, na_values=[""])
        feat = feat[(feat.hint_set == "default") & (feat.tag.fillna("") == "")]
        lab = pd.read_csv(SOURCES["B"]["files"][1])
        df = feat.merge(lab, on=["query_id", "template"], how="inner")
    df["template"] = df.template.astype(str)
    df = df.sort_values(["template", "query_id"], key=lambda s: s.str.zfill(4)).reset_index(drop=True)
    xcols = [c for c in df.columns if c.startswith(("sql_", "plan_"))
             and c not in ("plan_signature", "plan_analyzed") and df[c].nunique() > 1]
    classes = [c[2:] for c in df.columns if c.startswith("t_")]
    return df, xcols, SOURCES[key]["baseline"], classes


def load_plans():
    p = os.path.join(APP_OUT, "default_plans.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def targets(df, baseline, task):
    best = df.best_hint_set.to_numpy()
    return best if task == "multi" else np.where(best == baseline, KEEP, SWITCH)


# ---------------------------------------------------------------- phân loại
def _switch_target(best, baseline):
    """Khi mô hình 2 lớp nói "Đổi plan": đổi sang plan thắng nhiều nhất trong tập train."""
    other = pd.Series(best[best != baseline])
    return other.mode().iloc[0] if len(other) else baseline


def predict_cv(df, xcols, baseline, scheme, task, model_name):
    """Dự đoán out-of-fold. Trả về (y, pred, chosen): chosen là plan thực sự được chạy cho từng câu."""
    X = df[xcols].astype(float).to_numpy()
    best = df.best_hint_set.to_numpy()
    y = targets(df, baseline, task)
    keep_label = baseline if task == "multi" else KEEP
    pred = np.empty(len(y), dtype=object)
    chosen = np.empty(len(y), dtype=object)
    for tr, te in folds(scheme, df):
        if model_name == ALWAYS_PG:
            pred[te] = keep_label
        elif model_name == OPTIMAL:
            pred[te] = y[te]
        elif len(set(y[tr])) == 1:
            pred[te] = y[tr][0]
        else:
            m = models()[model_name]
            m.fit(X[tr], y[tr])
            pred[te] = m.predict(X[te])
        if task == "multi":
            chosen[te] = pred[te]
        elif model_name == OPTIMAL:
            chosen[te] = best[te]
        else:
            target = _switch_target(best[tr], baseline)
            chosen[te] = np.where(pred[te] == SWITCH, target, baseline)
    return y, pred, chosen


def evaluate(df, baseline, task, y, pred, chosen):
    t = np.array([df.iloc[i].get(f"t_{c}", np.nan) for i, c in enumerate(chosen)], dtype=float)
    t = np.where(np.isnan(t), df.default_ms, t)
    correct = pred == y
    base_correct = y == (baseline if task == "multi" else KEEP)
    b, c = int((correct & ~base_correct).sum()), int((~correct & base_correct).sum())
    return {
        "số_câu_đúng": int(correct.sum()), "số_câu": len(y), "accuracy": correct.mean(),
        "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
        "workload_mô_hình_s": t.sum() / 1000, "workload_PG_s": df.default_ms.sum() / 1000,
        "workload_tối_ưu_s": df.best_ms.sum() / 1000,
        "speedup_vs_PG": df.default_ms.sum() / t.sum(),
        "regret_s": (t - df.best_ms).sum() / 1000,
        "số_câu_chậm_đi_>10%": int((t > 1.1 * df.default_ms).sum()),
        "số_câu_nhanh_hơn_>10%": int((t < 0.9 * df.default_ms).sum()),
        "p_mcnemar": binomtest(b, b + c, 0.5).pvalue if b + c else 1.0,
    }


def model_names():
    return [ALWAYS_PG] + list(models()) + [OPTIMAL]


def compare_models(df, xcols, baseline, scheme, task):
    rows, preds = [], {}
    for name in model_names():
        y, pred, chosen = predict_cv(df, xcols, baseline, scheme, task, name)
        rows.append({"mô_hình": name, **evaluate(df, baseline, task, y, pred, chosen)})
        preds[name] = pd.DataFrame({"query_id": df.query_id, "nhãn_thật": y, "dự_đoán": pred,
                                    "plan_được_chạy": chosen, "đúng": pred == y})
    return pd.DataFrame(rows), preds


def confusion(y, pred):
    labels = sorted(set(y) | set(pred))
    cm = confusion_matrix(y, pred, labels=labels)
    return pd.DataFrame([{"thật": labels[i], "dự_đoán": labels[j], "số_câu": int(cm[i, j])}
                         for i in range(len(labels)) for j in range(len(labels))])


# ---------------------------------------------------------------- data mining (giải thích)
def importance(df, xcols, baseline, task):
    X, y = df[xcols].astype(float), targets(df, baseline, task)
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=SEED).fit(X, y)
    pi = permutation_importance(rf, X, y, n_repeats=20, random_state=SEED)
    return pd.DataFrame({"đặc_trưng": xcols, "importance": pi.importances_mean,
                         "std": pi.importances_std}).sort_values("importance", ascending=False)


def decision_tree(df, xcols, baseline, task, depth=3):
    X, y = df[xcols].astype(float), targets(df, baseline, task)
    tree = DecisionTreeClassifier(max_depth=depth, class_weight="balanced", random_state=SEED).fit(X, y)
    return tree, export_text(tree, feature_names=list(xcols))


def assoc_rules(df, baseline, task, min_support=0.05, min_conf=0.5):
    from mlxtend.frequent_patterns import apriori, association_rules
    d = df.copy()
    d["best_hint_set"] = targets(df, baseline, task)
    items = to_items(d)
    freq = apriori(items, min_support=min_support, use_colnames=True, max_len=4)
    if freq.empty:
        return pd.DataFrame(columns=["luật", "support", "confidence", "lift"])
    rules = association_rules(freq, metric="confidence", min_threshold=min_conf)
    rules = rules[rules.consequents.map(lambda c: len(c) == 1 and next(iter(c)).startswith("best="))]
    rules = rules[~rules.antecedents.map(lambda c: any(x.startswith("best=") for x in c))]
    rules["luật"] = rules.antecedents.map(lambda s: " ∧ ".join(sorted(s))) + "  →  " + \
        rules.consequents.map(lambda s: next(iter(s)))
    return rules.sort_values(["lift", "confidence"], ascending=False)[["luật", "support", "confidence", "lift"]]


def clusters(df, xcols, baseline):
    Xs = StandardScaler().fit_transform(df[xcols].astype(float))
    best_k, best_s = 2, -1
    for k in range(2, 7):
        s = silhouette_score(Xs, KMeans(k, n_init=10, random_state=SEED).fit_predict(Xs))
        if s > best_s:
            best_k, best_s = k, s
    lab = KMeans(best_k, n_init=10, random_state=SEED).fit_predict(Xs)
    xy = PCA(2, random_state=SEED).fit_transform(Xs)
    pts = pd.DataFrame({"PC1": xy[:, 0], "PC2": xy[:, 1], "cụm": [f"Cụm {c + 1}" for c in lab],
                        "query_id": df.query_id, "plan_tốt_nhất": df.best_hint_set,
                        "speedup": df.speedup_vs_default.round(2)})
    summ = pts.assign(doi=df.best_hint_set != baseline, so_bang=df.sql_n_tables).groupby("cụm").agg(
        số_câu=("query_id", "size"), tỉ_lệ_nên_đổi_plan=("doi", "mean"),
        plan_tốt_nhất_phổ_biến=("plan_tốt_nhất", lambda s: s.value_counts().index[0]),
        speedup_trung_vị=("speedup", "median"), số_bảng_tb=("so_bang", "mean"),
        ví_dụ=("query_id", lambda s: ", ".join(list(s)[:6])))
    return best_k, best_s, pts, summ.reset_index()


# ---------------------------------------------------------------- kết quả bài báo
def paper_results():
    by_m = os.path.join(OUT, "c1_authors_by_method.csv")
    summ = os.path.join(OUT, "c1_authors_summary.csv")
    if not (os.path.exists(by_m) and os.path.exists(summ)):
        return None, None
    return pd.read_csv(by_m), pd.read_csv(summ)


def plan_lines(node, depth=0):
    """Cây plan dạng text thụt lề: toán tử, bảng, cost, số dòng ước lượng (và thực tế nếu có ANALYZE)."""
    rel = f" on {node['Relation Name']} {node.get('Alias', '')}".rstrip() if "Relation Name" in node else ""
    cond = node.get("Hash Cond") or node.get("Merge Cond") or node.get("Join Filter") or ""
    info = f"cost={node.get('Total Cost', 0):,.0f}  rows≈{node.get('Plan Rows', 0):,}"
    if "Actual Rows" in node:
        info += f"  thực tế={node['Actual Rows']:,}"
    line = "    " * depth + ("└─ " if depth else "") + node["Node Type"] + rel + (f"  {cond}" if cond else "")
    out = [f"{line}   [{info}]"]
    for c in node.get("Plans", []):
        out += plan_lines(c, depth + 1)
    return out
