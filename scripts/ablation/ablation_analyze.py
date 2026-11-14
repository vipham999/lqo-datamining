"""Phân tích ablation 8.4 / 8.5 theo tiêu chí của bài báo (Mục 8.4, 8.5).

Một câu được coi là "khác biệt": |Δ end-to-end ở lần chạy thứ 3| > 250 ms VÀ Welch t-test trên 3 lần chạy có p < 0,05.
Kèm "đối chứng âm" cho GEQO: các câu < geqo_threshold (12) bảng không dùng GEQO, nên tỉ lệ phải ≈ 1.

   analysis/.venv/bin/python scripts/ablation/ablation_analyze.py --tag interleaved_YYYYMMDD
"""
import argparse
import os
import re
import statistics as st

import pandas as pd
from scipy.stats import ttest_ind

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QDIR = os.path.join(R, 'lqo_ml_perspective/bao/queries/join-order-benchmark')
PAPER = {  # truy vấn bài báo nêu tên: (cấu hình, hệ số, hướng)
    'no_bitmap_tidscan': {'28a': 'nhanh 5,5×', '7c': 'nhanh 2,0×', '30a': 'nhanh 1,8×',
                          '30c': 'chậm 2,4×', '28b': 'chậm 1,9×', '15c': 'chậm 1,5×'},
    'no_geqo': {'30a': 'nhanh 1,6×', '24b': 'chậm 9,9×', '26c': 'chậm 2,2×',
                '28a': 'chậm 2,1×', '28b': 'chậm 1,7×'},
}


def load(path):
    d = {}
    for line in open(path):
        if not line.startswith('x,'):
            continue
        a = [s.strip() for s in line.split(',')]
        q = os.path.basename(a[3])[:-4]
        d.setdefault(q, []).append(float(a[4]) + float(a[5]))
    return d


def n_tables(q):
    s = open(os.path.join(QDIR, f'{q}.sql')).read()
    return re.search(r'FROM(.*?)WHERE', s, re.S | re.I).group(1).count(',') + 1


def main(a):
    log = lambda c: os.path.join(R, a.log_dir, f'test__postgres__job__{c}__{a.tag}.txt')
    base = load(log('default'))
    out_dir = os.path.join(R, 'analysis/output')
    for cfg in ['no_geqo', 'no_bitmap_tidscan']:
        cand = load(log(cfg))
        rows = []
        for q in sorted(base, key=lambda x: (int(re.match(r'\d+', x).group()), x)):
            b, c = base[q], cand[q]
            p = ttest_ind(b, c, equal_var=False).pvalue if len(set(b + c)) > 1 else 1.0
            rows.append(dict(query=q, n_bang=n_tables(q), default_ms=b[-1], ablation_ms=c[-1],
                             delta_ms=c[-1] - b[-1], ti_le=c[-1] / b[-1], p_welch=p,
                             khac_biet=abs(c[-1] - b[-1]) > 250 and p < 0.05,
                             bai_bao=PAPER[cfg].get(q, '')))
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(out_dir, f'ablation_{cfg}_{a.tag}.csv'), index=False)
        sig = df[df.khac_biet]
        print(f"\n===== {cfg}  (dương = chậm đi khi áp dụng ablation)")
        print(f"Workload: default {df.default_ms.sum() / 1e3:.1f} s → {cfg} {df.ablation_ms.sum() / 1e3:.1f} s "
              f"({df.default_ms.sum() / df.ablation_ms.sum():.2f}× speedup)")
        print(f"|Δ| > 250 ms: {(df.delta_ms.abs() > 250).sum()} câu; trong đó có ý nghĩa (p<0,05): {len(sig)} câu "
              f"→ nhanh hơn {int((sig.delta_ms < 0).sum())}, chậm hơn {int((sig.delta_ms > 0).sum())}")
        for lo, hi in [(0, 11), (12, 99)]:
            g = df[(df.n_bang >= lo) & (df.n_bang <= hi)]
            print(f"  câu {lo}–{hi} bảng: n={len(g)}, tỉ lệ thời gian trung vị = {st.median(g.ti_le):.2f}")
        cols = ['query', 'n_bang', 'default_ms', 'ablation_ms', 'ti_le', 'p_welch', 'bai_bao']
        print("Các câu khác biệt có ý nghĩa:")
        print(sig.sort_values('ti_le')[cols].to_string(index=False, float_format=lambda x: f'{x:.3g}'))
        print("Đối chiếu với các câu bài báo nêu:")
        print(df[df.bai_bao != ''][cols + ['khac_biet']].to_string(index=False, float_format=lambda x: f'{x:.3g}'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True)
    ap.add_argument('--log_dir', default='logs/mac/postgres',
                    help='Kaggle: logs/kaggle/ablation/8_4_8_5/lan_dau/ablation_logs (với --tag kaggle)')
    main(ap.parse_args())
