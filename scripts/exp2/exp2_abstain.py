"""Thử cải tiến rút ra từ khai phá dữ liệu: "không chắc thì giữ nguyên PostgreSQL".

Mô hình của Thí nghiệm 2 (DT / RF / LightGBM, cùng siêu tham số, cùng 34 đặc trưng) chỉ được đổi cách chạy khi
độ tin của phương án nó chọn (predict_proba) ≥ ngưỡng; còn lại giữ nguyên PostgreSQL. Đánh giá đúng như
exp2_analyze.py: train/test trên 9 split của bài báo, thời gian = EXPLAIN + thời gian phương án được chọn
(chưa cộng thời gian suy luận, khoảng vài ms).

  ~/.venvs/lqo_app/bin/python scripts/exp2/exp2_abstain.py

Ra: analysis/output/exp2/exp2_abstain.csv        (mô hình × ngưỡng → speedup, thắng/hòa/thua, số lần đổi)
    analysis/output/exp2/exp2_abstain_switches.csv (những lần đổi ở ngưỡng 0,6)
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common")]
import exp2_analyze as E  # noqa: E402

THRESHOLDS = [0.0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]   # 0.0 = mô hình gốc (luôn làm theo dự đoán)
MAIN = 0.6


def main():
    t, _, _ = E.load_times(os.path.join(E.R, "logs/exp2_hintsets_job.jsonl"), "JOB")
    y, _ = E.labels(t)
    f = E.load_features(os.path.join(E.R, "logs/exp2_explain_job.jsonl"),
                        os.path.join(E.R, "lqo_ml_perspective/bao/queries/join-order-benchmark"), "JOB")
    xc = [c for c in f.columns if c != "explain_ms"]
    X = f[xc].astype(float)
    rows, sw = [], []
    for name in E.models():
        res = {th: [0.0, 0.0, 0, 0, 0, 0] for th in THRESHOLDS}      # pg, cand, thắng, thua, số câu, số lần đổi
        for sp in E.SPLITS:
            tr, te = E.split_lists(sp)
            tr = [q for q in tr if q in X.index and q in y.index]
            te = [q for q in te if q in X.index and q in t.index]
            m = E.models()[name]
            m.fit(X.loc[tr].to_numpy(), y.loc[tr].to_numpy())
            P = m.predict_proba(X.loc[te].to_numpy())
            pred, conf = m.classes_[P.argmax(1)], P.max(1)
            for th in THRESHOLDS:
                r = res[th]
                for q, h, c in zip(te, pred, conf):
                    h = h if (h == "default" or c >= th) else "default"
                    a, b = t.loc[q, "default"], t.loc[q, h] + f.loc[q, "explain_ms"]
                    r[0] += a
                    r[1] += b
                    r[2] += a / b > 1 + E.EPS
                    r[3] += a / b < 1 - E.EPS
                    r[4] += 1
                    r[5] += h != "default"
                    if th == MAIN and h != "default":
                        sw.append({"mô_hình": name, "split": E.short(sp), "query_id": q, "phương_án": h,
                                   "độ_tin": round(float(c), 2), "PG_ms": a, "phương_án_ms": t.loc[q, h]})
        for th, (pg, cand, w, l, n, k) in res.items():
            rows.append({"mô_hình": name, "ngưỡng": th, "speedup": pg / cand, "thắng": w, "thua": l,
                         "hòa": n - w - l, "số_lần_đổi": k, "số_lần_kiểm_tra": n})
    out = os.path.join(E.R, "analysis/output/exp2")
    pd.DataFrame(rows).to_csv(os.path.join(out, "exp2_abstain.csv"), index=False)
    pd.DataFrame(sw).to_csv(os.path.join(out, "exp2_abstain_switches.csv"), index=False)
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
