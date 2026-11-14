"""Hàm dùng chung: đọc các loại log (repo gốc, JSONL của run_and_log.py, CSV tổng hợp của tác giả)
về cùng một dạng bảng: query_id, planning_ms, execution_ms, inference_ms, total_ms, timeout."""
import json
import os
import re

import pandas as pd

QID_RE = re.compile(r"^0*(\d+)([a-z]?)$")


def norm_qid(name):
    """'queries/job/01a.sql' | '01a' | '1a' -> '1a'."""
    base = os.path.splitext(os.path.basename(str(name).strip()))[0]
    m = QID_RE.match(base)
    return f"{int(m.group(1))}{m.group(2)}" if m else base


def template_of(qid):
    """'17b' -> '17' (truy vấn gốc / base query)."""
    m = re.match(r"^(\d+)", qid)
    return m.group(1) if m else qid


def _finish(df):
    df["total_ms"] = df["inference_ms"] + df["planning_ms"] + df["execution_ms"]
    df["template"] = df["query_id"].map(template_of)
    return df.reset_index(drop=True)


def load_repo_txt(path, run=2):
    """Log của bao/run_test_queries.py:
    'hint, lần_chạy, timestamp, file, planning_ms, execution_ms, PG|Bao'.
    Với Bao, planning time đã bao gồm inference (Bao chạy trong PostgreSQL)."""
    rows = []
    with open(path) as f:
        for line in f:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue
            # hint có thể chứa dấu phẩy → đọc từ cuối dòng
            method, exe, plan, fp, _ts, i = parts[-1], parts[-2], parts[-3], parts[-4], parts[-5], parts[-6]
            hint = ",".join(parts[:-6])
            rows.append({"query_id": norm_qid(fp), "run": int(i), "hint": None if hint == "x" else hint,
                         "planning_ms": float(plan), "execution_ms": float(exe), "method": method})
    df = pd.DataFrame(rows)
    df = df[df.run == run].copy()
    df["inference_ms"] = 0.0
    # run_test_queries.py ghi 2 * TIMEOUT khi timeout (3 phút)
    df["timeout"] = df.execution_ms >= 2 * 3 * 60 * 1000
    return _finish(df)


def load_jsonl(path, run=2, hint_set=None, tag=None):
    """Log của scripts/common/run_and_log.py."""
    df = pd.read_json(path, lines=True)
    df = df[df.run == run]
    if hint_set is not None:
        df = df[df.hint_set == hint_set]
    if tag is not None and "tag" in df:
        df = df[df.tag == tag]
    df = df.copy()
    df["query_id"] = df.query_id.map(norm_qid)
    df["planning_ms"] = df.planning_ms.fillna(0.0)
    df["inference_ms"] = 0.0
    return _finish(df)


def load_combined(path, method, experiment=None, split="test", run_type="regular"):
    """experiment_logs/20240103__combined.csv của tác giả.
    Mỗi (experiment, method, query, split) có nhiều lần chạy; lấy lần cuối (hot cache, như bài báo).
    PostgreSQL không gắn experiment/split → lấy trung vị các lần chạy sau lần đầu."""
    df = pd.read_csv(path)
    df = df[(df.run_type == run_type) & (df.method == method)].copy()
    df["query_id"] = df.query_ident.map(norm_qid)
    if method == "PostgreSQL":
        df = df.sort_values("run_id")
        df["k"] = df.groupby("query_id").cumcount()
        df = df[df.k >= 1].groupby("query_id", as_index=False).agg(
            planning_ms=("planning_time", "median"), execution_ms=("execution_time", "median"),
            inference_ms=("inference_time", "median"), timeout=("timed_out", "max"))
    else:
        if experiment is not None:
            df = df[df.experiment == experiment]
        if split is not None:
            df = df[df.split == split]
        df = df.sort_values("run_id").groupby("query_id", as_index=False).last()
        df = df.rename(columns={"planning_time": "planning_ms", "execution_time": "execution_ms",
                                "inference_time": "inference_ms", "timed_out": "timeout"})
        df = df[["query_id", "planning_ms", "execution_ms", "inference_ms", "timeout"]]
    df["timeout"] = df.timeout.astype(str).str.lower() == "true"
    return _finish(df)


def load_spec(spec):
    """Đọc log theo chuỗi mô tả:
       txt:<file>                              (log repo gốc, run_test_queries.py)
       jsonl:<file>[:<hint_set>[:<tag>]]        (scripts/common/run_and_log.py)
       combined:<file>:<method>[:<experiment>]  (log tác giả)"""
    kind, rest = spec.split(":", 1)
    parts = rest.split(":")
    if kind == "txt":
        return load_repo_txt(parts[0])
    if kind == "jsonl":
        return load_jsonl(parts[0], hint_set=parts[1] if len(parts) > 1 and parts[1] else None,
                          tag=parts[2] if len(parts) > 2 else None)
    if kind == "combined":
        return load_combined(parts[0], parts[1], parts[2] if len(parts) > 2 else None)
    raise ValueError(f"Không hiểu spec: {spec}")


def read_plans(path, run=2):
    """{(query_id, hint_set, tag): plan_json} từ JSONL."""
    plans = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("run") == run and r.get("plan") is not None:
                plans[(norm_qid(r["query_id"]), r["hint_set"], r.get("tag", ""))] = r["plan"]
    return plans
