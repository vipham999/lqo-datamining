"""C2 – Bài toán phân loại: "truy vấn này nên chạy với plan (hint set) nào?"

  python scripts/c2_classify.py --features analysis/output/features.csv \
                                --labels analysis/output/labels.csv

X = đặc trưng SQL + đặc trưng plan MẶC ĐỊNH của PostgreSQL (chỉ dùng thông tin có trước khi chạy hint set khác
    → không rò rỉ nhãn).
y = best_hint_set (từ label.py).

Ba kiểu chia train/test giống bài báo (Mục 7.2):
  leave_one_out : mỗi fold lấy đúng 1 biến thể của mỗi truy vấn gốc vào test        (dễ)
  random        : KFold 5 fold ngẫu nhiên                                              (trung bình)
  base_query    : GroupKFold theo truy vấn gốc – cả họ truy vấn nằm trọn train/test  (khó)

Chỉ số: số câu đúng, accuracy, macro-F1, tổng thời gian workload khi chọn plan theo mô hình
(so với luôn dùng PostgreSQL và oracle), regret, số câu bị chậm đi (regression), McNemar so với baseline.
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")
SEED = 42


def models():
    return {
        "DecisionTree": DecisionTreeClassifier(max_depth=5, class_weight="balanced", random_state=SEED),
        "RandomForest": RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=SEED),
        "GradientBoosting": HistGradientBoostingClassifier(random_state=SEED),
        "kNN": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5)),
        "NaiveBayes": make_pipeline(StandardScaler(), GaussianNB()),
        "SVM": make_pipeline(StandardScaler(), SVC(class_weight="balanced", random_state=SEED)),
        "LogisticRegression": make_pipeline(StandardScaler(),
                                            LogisticRegression(max_iter=2000, class_weight="balanced")),
    }


def folds(scheme, df):
    idx = np.arange(len(df))
    if scheme == "random":
        return list(KFold(n_splits=5, shuffle=True, random_state=SEED).split(idx))
    if scheme == "base_query":
        n = min(5, df.template.nunique())
        return list(GroupKFold(n_splits=n).split(idx, groups=df.template))
    if scheme == "leave_one_out":
        rank = df.groupby("template").cumcount().to_numpy()
        return [(idx[rank != k], idx[rank == k]) for k in range(rank.max() + 1)]
    raise ValueError(scheme)


def evaluate(name, scheme, y, pred, lab):
    t_pred = np.array([lab.iloc[i][f"t_{p}"] for i, p in enumerate(pred)], dtype=float)
    t_pred = np.where(np.isnan(t_pred), lab.default_ms, t_pred)       # hint set thiếu số đo → coi như default
    correct = pred == y
    base_correct = y == "default"
    b, c = int((correct & ~base_correct).sum()), int((~correct & base_correct).sum())
    return {
        "kiểu_chia": scheme, "mô_hình": name, "số_câu": len(y),
        "số_câu_đúng": int(correct.sum()), "accuracy": correct.mean(),
        "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
        "workload_mô_hình_s": t_pred.sum() / 1000,
        "workload_PG_s": lab.default_ms.sum() / 1000,
        "workload_oracle_s": lab.best_ms.sum() / 1000,
        "speedup_vs_PG": lab.default_ms.sum() / t_pred.sum(),
        "regret_tb_ms": (t_pred - lab.best_ms).mean(),
        "số_câu_chậm_đi_>10%": int((t_pred > 1.1 * lab.default_ms).sum()),
        "p_mcnemar_vs_PG": binomtest(b, b + c, 0.5).pvalue if b + c else 1.0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--features", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--tag", default="")
    p.add_argument("--schemes", default="leave_one_out,random,base_query")
    p.add_argument("--out_dir", default="analysis/output")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    feat = pd.read_csv(a.features, keep_default_na=False, na_values=[""])
    feat = feat[(feat.hint_set == "default") & (feat.tag.fillna("") == a.tag)]
    lab = pd.read_csv(a.labels)
    df = feat.merge(lab, on=["query_id", "template"], how="inner")
    df["template"] = df.template.astype(str)
    df = df.sort_values(["template", "query_id"]).reset_index(drop=True)
    xcols = [c for c in df.columns if c.startswith(("sql_", "plan_")) and c != "plan_signature"]
    X, y = df[xcols].astype(float).to_numpy(), df.best_hint_set.to_numpy()
    print(f"{len(df)} truy vấn, {len(xcols)} đặc trưng, {df.template.nunique()} truy vấn gốc")
    print("Phân bố nhãn:", dict(pd.Series(y).value_counts()))

    rows, preds = [], []
    for scheme in a.schemes.split(","):
        fs = folds(scheme, df)
        # Baseline: luôn dùng plan mặc định của PostgreSQL
        rows.append(evaluate("Luôn_PostgreSQL", scheme, y, np.array(["default"] * len(y)), df))
        for name, model in models().items():
            pred = np.empty(len(y), dtype=object)
            for tr, te in fs:
                if len(set(y[tr])) == 1:
                    pred[te] = y[tr][0]
                    continue
                model.fit(X[tr], y[tr])
                pred[te] = model.predict(X[te])
            rows.append(evaluate(name, scheme, y, pred, df))
            preds.append(pd.DataFrame({"kiểu_chia": scheme, "mô_hình": name, "query_id": df.query_id,
                                       "template": df.template, "nhãn_thật": y, "dự_đoán": pred}))
        # Oracle: giới hạn trên
        rows.append(evaluate("Oracle", scheme, y, y.copy(), df))

    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(a.out_dir, "c2_summary.csv"), index=False)
    allp = pd.concat(preds)
    allp.to_csv(os.path.join(a.out_dir, "c2_predictions.csv"), index=False)

    # Confusion matrix của mô hình tốt nhất (theo workload) ở mỗi kiểu chia
    classes = sorted(set(y))
    for scheme in summary.kiểu_chia.unique():
        s = summary[(summary.kiểu_chia == scheme) & ~summary.mô_hình.isin(["Oracle", "Luôn_PostgreSQL"])]
        best = s.sort_values("workload_mô_hình_s").iloc[0].mô_hình
        pp = allp[(allp.kiểu_chia == scheme) & (allp.mô_hình == best)]
        cm = pd.DataFrame(confusion_matrix(pp.nhãn_thật, pp.dự_đoán, labels=classes),
                          index=[f"thật:{c}" for c in classes], columns=[f"đoán:{c}" for c in classes])
        cm.to_csv(os.path.join(a.out_dir, f"c2_confusion__{scheme}__{best}.csv"))
        print(f"\n[{scheme}] Confusion matrix – {best}:\n{cm.to_string()}")

    pd.set_option("display.width", 220)
    cols = ["kiểu_chia", "mô_hình", "số_câu_đúng", "số_câu", "accuracy", "macro_f1",
            "workload_mô_hình_s", "workload_PG_s", "workload_oracle_s", "speedup_vs_PG",
            "số_câu_chậm_đi_>10%", "p_mcnemar_vs_PG"]
    print("\n" + summary[cols].round(3).to_string(index=False))
    print(f"\nĐã lưu vào {a.out_dir}/c2_*.csv")


if __name__ == "__main__":
    main()
