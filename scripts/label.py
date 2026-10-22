"""Gán nhãn "plan tốt nhất" cho mỗi truy vấn (Phần C, bước 8.2).

  python scripts/label.py --log logs/job_hintsets.jsonl --out analysis/output/labels.csv

labels.csv gồm:
  query_id, template, best_hint_set, default_ms, best_ms, speedup_vs_default,
  t_<hint_set> (thời gian end-to-end của từng hint set, dùng để tính thời gian workload khi phân loại)
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from extract_features import plan_signature  # noqa: E402
from lqo_common import load_jsonl, read_plans, template_of  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True)
    p.add_argument("--run", type=int, default=2)
    p.add_argument("--tag", default=None)
    p.add_argument("--min_gain", type=float, default=0.05,
                   help="hint set chỉ được coi là tốt hơn default nếu nhanh hơn ít nhất 5%% "
                        "(tránh gán nhãn theo nhiễu đo)")
    p.add_argument("--out", required=True)
    a = p.parse_args()

    df = load_jsonl(a.log, run=a.run, tag=a.tag)
    t = df.pivot_table(index="query_id", columns="hint_set", values="total_ms", aggfunc="first")
    t = t.dropna(subset=["default"])
    # Hint set cho ra CÙNG cây plan với default thì không phải "plan mới": dùng thời gian của default,
    # để chênh lệch do nhiễu đo không bị gán nhãn nhầm.
    plans = read_plans(a.log, run=a.run)
    tag = a.tag or ""
    n_same = 0
    for q in t.index:
        base = plans.get((q, "default", tag))
        for hs in t.columns:
            other = plans.get((q, hs, tag))
            if hs != "default" and base and other and plan_signature(base) == plan_signature(other):
                t.loc[q, hs] = t.loc[q, "default"]
                n_same += 1
    best = t.idxmin(axis=1)
    best_ms = t.min(axis=1)
    # Nếu cải thiện quá nhỏ → giữ nhãn default
    keep_default = best_ms > t["default"] * (1 - a.min_gain)
    best[keep_default] = "default"
    best_ms[keep_default] = t["default"][keep_default]

    out = pd.DataFrame({
        "query_id": t.index,
        "template": [template_of(q) for q in t.index],
        "best_hint_set": best.values,
        "default_ms": t["default"].values,
        "best_ms": best_ms.values,
    })
    out["speedup_vs_default"] = out.default_ms / out.best_ms
    for hs in t.columns:
        out[f"t_{hs}"] = t[hs].values
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.to_csv(a.out, index=False)

    print(f"{len(out)} truy vấn → {a.out}  ({n_same} cặp (truy vấn, hint set) cho cùng plan với default)")
    print("\nPhân bố nhãn:")
    print(out.best_hint_set.value_counts().to_string())
    print(f"\nOracle (luôn chọn đúng): workload {out.default_ms.sum()/1000:.1f}s → {out.best_ms.sum()/1000:.1f}s "
          f"(nhanh hơn {out.default_ms.sum()/out.best_ms.sum():.2f}×)")


if __name__ == "__main__":
    main()
