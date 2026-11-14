"""Sinh notebook Kaggle chạy HybridQO từ các ô lệnh trong HUONG_DAN_KAGGLE_HYBRIDQO.md.

    python kaggle/build_notebook.py --user <kaggle_username> --split random_split_1 [--rep 0] [--cpu]
    python kaggle/build_notebook.py --user <kaggle_username> --remaining [--cpu]   # 8 split còn lại (trừ LOO-1)

Mỗi split tạo kaggle/hybridqo-job-<split>/ gồm notebook .ipynb và kernel-metadata.json,
sẵn sàng cho `kaggle kernels push -p <thư mục>`. Notebook lưu kết quả thành
/kaggle/working/wandb_export/hybrid_qo__JOB__<split>__<rep>.csv như log của tác giả.
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL_SPLITS = [f"{k}_split_{i}" for k in ("leave_one_out", "random", "base_query") for i in (1, 2, 3)]
DONE = {"leave_one_out_split_1"}  # đã chạy xong, log ở logs/kaggle/hybridqo/leave_one_out_split_1/


def cells_from_guide(split, rep):
    text = open(os.path.join(ROOT, "HUONG_DAN_KAGGLE_HYBRIDQO.md")).read()
    blocks = re.findall(r"```(bash|python)\n(.*?)```", text, re.S)
    cells = []
    for lang, src in blocks:
        if lang == "bash" and not src.startswith("%%bash"):
            continue  # ví dụ lệnh trong phần chữ, không phải ô notebook
        if re.search(r'^SPLIT = ".*?"', src, re.M):
            src = re.sub(r'^SPLIT = ".*?"', f'SPLIT = "{split}"', src, count=1, flags=re.M)
            src = re.sub(r"^REP = \d+", f"REP = {rep}", src, count=1, flags=re.M)
        cells.append(src.rstrip("\n"))
    return cells


def build(user, split, rep, cpu):
    slug = "hybridqo-job-" + split.replace("_split_", "-").replace("_", "-") + (f"-rep{rep}" if rep else "")
    out = os.path.join(ROOT, "kaggle", slug)
    os.makedirs(out, exist_ok=True)
    cells = cells_from_guide(split, rep)
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                       "language_info": {"name": "python"}},
          "cells": [{"id": f"cell-{i}", "cell_type": "code", "metadata": {}, "execution_count": None,
                     "outputs": [], "source": c.splitlines(keepends=True)} for i, c in enumerate(cells)]}
    json.dump(nb, open(os.path.join(out, f"{slug}.ipynb"), "w"), ensure_ascii=False, indent=1)
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": f"{slug}.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": True, "enable_gpu": not cpu, "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    json.dump(meta, open(os.path.join(out, "kernel-metadata.json"), "w"), indent=2)
    print(f"{len(cells)} ô, {'CPU' if cpu else 'GPU'} → {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--split", choices=ALL_SPLITS)
    ap.add_argument("--remaining", action="store_true", help="sinh notebook cho mọi split chưa chạy")
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--cpu", action="store_true", help="tắt GPU (cần thử CPU trước, xem hướng dẫn)")
    a = ap.parse_args()
    if not a.split and not a.remaining:
        ap.error("cần --split hoặc --remaining")
    splits = [s for s in ALL_SPLITS if s not in DONE] if a.remaining else [a.split]
    for s in splits:
        build(a.user, s, a.rep, a.cpu)


if __name__ == "__main__":
    main()
