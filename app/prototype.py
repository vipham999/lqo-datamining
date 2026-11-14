"""Tab 5 – Prototype: người dùng chọn một câu JOB, mô hình của nhóm chọn phương án, rồi chạy thật trên PostgreSQL.

Quy trình giống hệt Thí nghiệm 2 (scripts/exp2/exp2_analyze.py), chỉ khác là làm trực tiếp cho MỘT câu:
  1. EXPLAIN (FORMAT JSON, không ANALYZE) câu SQL  → plan mặc định của PostgreSQL
  2. 34 đặc trưng (extract_features.sql_features + plan_features, bỏ q-error)
  3. Mô hình (DT / RF / LightGBM) học trên 113 câu JOB đã đo → chọn 1 trong 6 phương án
  4. SET enable_x = off (nếu cần) rồi chạy EXPLAIN ANALYZE để đo thời gian thật, so với PostgreSQL mặc định

Cần PostgreSQL có CSDL IMDB (mặc định localhost:5432, db imdbload – container pg_bao).
Mọi câu chạy ở chế độ chỉ đọc (read only) và có giới hạn thời gian (statement_timeout).
"""
import os
import re
import time

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import core  # noqa: F401  (thêm scripts/ vào sys.path)
import exp2_analyze as E
from extract_features import plan_features, sql_features

HINT_SQL = {
    "default": [],
    "no_nestloop": ["SET enable_nestloop = off"],
    "no_hashjoin": ["SET enable_hashjoin = off"],
    "no_mergejoin": ["SET enable_mergejoin = off"],
    "no_seqscan": ["SET enable_seqscan = off"],
    "no_indexscan": ["SET enable_indexscan = off", "SET enable_indexonlyscan = off"],
}
HINT_VI = {"default": "Giữ nguyên PostgreSQL", "no_nestloop": "Tắt nested loop", "no_hashjoin": "Tắt hash join",
           "no_mergejoin": "Tắt merge join", "no_seqscan": "Tắt seq scan", "no_indexscan": "Tắt index scan"}
MODEL_VI = {"DecisionTree": "Decision Tree", "RandomForest": "Random Forest", "LightGBM": "LightGBM"}
JOB_DIR = os.path.join(E.R, "lqo_ml_perspective/bao/queries/join-order-benchmark")
GREEN, RED, GREY, BLUE = "#1baf7a", "#e34948", "#898781", "#2a78d6"


# ---------------------------------------------------------------- dữ liệu & mô hình
@st.cache_data(show_spinner=False)
def job_queries():
    out = {}
    for fn in os.listdir(JOB_DIR):
        if fn.endswith(".sql"):
            out[E.qid_of(fn[:-4], "JOB")] = open(os.path.join(JOB_DIR, fn)).read().strip()
    key = lambda q: (int(re.match(r"\d+", q).group()), q)  # noqa: E731
    return dict(sorted(out.items(), key=lambda kv: key(kv[0])))


@st.cache_data(show_spinner=False)
def training_data():
    t, _, _ = E.load_times(os.path.join(E.R, "logs/exp2_hintsets_job.jsonl"), "JOB")
    y, best = E.labels(t)
    f = E.load_features(os.path.join(E.R, "logs/exp2_explain_job.jsonl"), JOB_DIR, "JOB")
    qs = [q for q in y.index if q in f.index]
    xcols = [c for c in f.columns if c != "explain_ms"]
    return f.loc[qs, xcols].astype(float), y.loc[qs], t.loc[qs], best.loc[qs]


@st.cache_resource(show_spinner=False)
def trained_model(name, exclude_family):
    X, y, _, _ = training_data()
    keep = [q for q in X.index if exclude_family is None or E.template_for(q, "JOB") != exclude_family]
    m = E.models()[name]
    m.fit(X.loc[keep].to_numpy(), y.loc[keep].to_numpy())
    return m, len(keep), list(X.columns)


# ---------------------------------------------------------------- PostgreSQL
def clean_sql(sql):
    s = re.sub(r"--[^\n]*", "", sql).strip().rstrip(";").strip()
    if not s:
        raise ValueError("Chưa nhập câu SQL.")
    if ";" in s:
        raise ValueError("Chỉ nhập MỘT câu SQL (không có dấu ';' ở giữa).")
    if not re.match(r"(?is)^\s*(select|with)\b", s):
        raise ValueError("Chỉ chấp nhận câu truy vấn đọc dữ liệu (bắt đầu bằng SELECT hoặc WITH).")
    return s


def connect(cfg, timeout_ms, setup=()):
    import psycopg2
    conn = psycopg2.connect(dbname=cfg["db"], user=cfg["user"], password=cfg["password"], host=cfg["host"],
                            port=int(cfg["port"]), connect_timeout=5)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")
    cur.execute(f"SET statement_timeout = {int(timeout_ms)}")
    try:
        cur.execute("SET enable_bao = off")                 # pg_bao: chắc chắn không để Bao can thiệp
    except Exception:
        pass
    for s in setup:
        cur.execute(s)
    return conn, cur


def check_connection(cfg):
    try:
        conn, cur = connect(cfg, 5000)
        cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
        n = cur.fetchone()[0]
        conn.close()
        return True, f"Đã kết nối {cfg['host']}:{cfg['port']}/{cfg['db']} ({n} bảng)."
    except Exception as e:
        return False, f"Không kết nối được PostgreSQL: {str(e).strip().splitlines()[0]}"


def explain(cfg, sql, timeout_ms):
    """Giống exp2_explain.py: gọi EXPLAIN 3 lần trên cùng kết nối, lấy thời gian lần thứ 3."""
    conn, cur = connect(cfg, timeout_ms)
    try:
        for _ in range(3):
            t0 = time.perf_counter()
            cur.execute(f"EXPLAIN (FORMAT JSON) {sql}")
            plan = cur.fetchone()[0][0]["Plan"]
            ms = (time.perf_counter() - t0) * 1000
    finally:
        conn.close()
    return plan, ms


def run_hint(cfg, sql, hint, timeout_ms, runs):
    """Chạy EXPLAIN ANALYZE `runs` lần với hint, lấy lần cuối (bộ nhớ đệm đã ấm)."""
    import psycopg2
    conn, cur = connect(cfg, timeout_ms, HINT_SQL[hint])
    res = None
    try:
        for _ in range(runs):
            try:
                cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}")
                r = cur.fetchone()[0][0]
                res = {"ms": r["Planning Time"] + r["Execution Time"], "timeout": False, "plan": r["Plan"]}
            except psycopg2.errors.QueryCanceled:
                res = {"ms": float(timeout_ms), "timeout": True, "plan": None}
                break
    finally:
        conn.close()
    return res


def features(sql, plan):
    f = sql_features(sql)
    f.update({k: v for k, v in plan_features(plan).items() if k not in E.DROP})
    return f


# ---------------------------------------------------------------- hiển thị plan
def plan_text(plan, max_lines=60):
    lines = []

    def visit(n, d):
        t = n["Node Type"]
        what = ""
        if n.get("Relation Name"):
            what = f" trên {n['Relation Name']}" + (f" ({n['Alias']})" if n.get("Alias") not in (None, n["Relation Name"]) else "")
        extra = f"  ~{int(n.get('Plan Rows', 0)):,} dòng ước lượng"
        if "Actual Rows" in n:
            extra += f", thực tế {int(n['Actual Rows'] * max(n.get('Actual Loops', 1), 1)):,}"
        lines.append("   " * d + ("└─ " if d else "") + t + what + extra)
        for c in n.get("Plans", []):
            visit(c, d + 1)
    visit(plan, 0)
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} dòng nữa)"]
    return "\n".join(lines)


def plan_summary(plan):
    f = plan_features(plan)
    parts = [f"{f['plan_n_joins']} phép join: {f['plan_n_nestloop']} nested loop, {f['plan_n_hashjoin']} hash join, "
             f"{f['plan_n_mergejoin']} merge join",
             f"cost ước lượng {plan.get('Total Cost', 0):,.0f}"]
    return " · ".join(parts)


def _fmt_ms(ms):
    return f"{ms / 1000:.2f} s" if ms >= 1000 else f"{ms:.0f} ms"


# ---------------------------------------------------------------- giao diện
def render():
    st.header("Demo mô hình – chọn một câu truy vấn, xem mô hình chọn cách chạy nào rồi chạy thật")
    st.info("Đây là bản chạy thử (prototype) đúng quy trình của nhóm: **EXPLAIN → 34 đặc trưng → mô hình chọn "
            "phương án → SET enable_x = off → chạy**. Khác các tab trước, tab này **chạy trực tiếp trên PostgreSQL**.")

    with st.expander("Kết nối PostgreSQL", expanded=False):
        c1, c2, c3 = st.columns(3)
        cfg = {"host": c1.text_input("Host", "localhost", key="pg_host"),
               "port": c2.text_input("Port", "5432", key="pg_port"),
               "db": c3.text_input("Database", "imdbload", key="pg_db"),
               "user": c1.text_input("User", "postgres", key="pg_user"),
               "password": c2.text_input("Password", "postgres", type="password", key="pg_pw")}
    ok, msg = check_connection(cfg)
    (st.caption if ok else st.error)(("✅ " if ok else "") + msg +
                                     ("" if ok else " Hãy bật container pg_bao (docker start pg_bao) hoặc sửa thông tin "
                                      "trong mục 'Kết nối PostgreSQL'."))

    # ---- Bước 1: input
    st.subheader("Bước 1 – Chọn câu truy vấn")
    qs = job_queries()
    qid = st.selectbox("Chọn một câu trong 113 câu JOB", list(qs),
                       index=list(qs).index("23a") if "23a" in qs else 0, key="proto_qid")
    st.caption("Gợi ý để demo: **23a** – mô hình chọn đúng, chạy nhanh (< 1 s) · **16b** – mô hình thắng lớn "
               "(PostgreSQL ~25 s) · **26a** – mô hình chọn sai, chậm hơn nhiều (cần giới hạn thời gian ≥ 40 s).")
    sql_in = qs[qid]
    with st.expander("Xem câu SQL", expanded=False):
        st.code(sql_in, language="sql")
    family = E.template_for(qid, "JOB")

    c1, c2, c3 = st.columns([1.4, 1, 1])
    model_name = c1.radio("Mô hình", list(MODEL_VI), index=1, format_func=MODEL_VI.get, horizontal=True,
                          key="proto_model")
    timeout_s = c2.number_input("Giới hạn thời gian mỗi lần chạy (giây)", 5, 180, 60, step=5, key="proto_to")
    runs = c3.number_input("Số lần chạy mỗi phương án (lấy lần cuối)", 1, 3, 3, key="proto_runs",
                           help="Lần đầu thường chậm vì dữ liệu chưa nằm trong bộ nhớ đệm; Thí nghiệm 2 lấy lần thứ 3.")
    fair = True
    if family is not None:
        fair = st.checkbox(f"Không cho mô hình học các câu cùng họ {family} (họ {family}a, {family}b, …) – để thử "
                           "công bằng như khi gặp câu mới", value=True, key="proto_fair")
    exclude = family if (family is not None and fair) else None

    if st.button("Hỏi mô hình", type="primary", disabled=not ok, key="proto_ask"):
        try:
            sql = clean_sql(sql_in)
            with st.spinner("Đang chạy EXPLAIN và hỏi mô hình…"):
                plan, ex_ms = explain(cfg, sql, timeout_s * 1000)
                m, n_train, xcols = trained_model(model_name, exclude)
                x = pd.DataFrame([features(sql, plan)]).reindex(columns=xcols, fill_value=0).astype(float).to_numpy()
                ts = []
                for _ in range(5):
                    t0 = time.perf_counter()
                    pred = m.predict(x)[0]
                    ts.append((time.perf_counter() - t0) * 1000)
                proba = dict(zip(m.classes_, m.predict_proba(x)[0]))
            st.session_state.proto = {"sql": sql, "qid": qid, "plan": plan, "explain_ms": ex_ms,
                                      "inf_ms": float(np.median(ts)), "pred": pred, "proba": proba,
                                      "model": model_name, "n_train": n_train, "exclude": exclude,
                                      "feat": features(sql, plan), "runs": None}
        except Exception as e:
            st.session_state.pop("proto", None)
            st.error(f"Lỗi: {str(e).strip().splitlines()[0]}")

    p = st.session_state.get("proto")
    if not p:
        st.caption("Bấm **Hỏi mô hình** để bắt đầu.")
        return
    if p["sql"] != clean_sql_safe(sql_in) or p["model"] != model_name or p["exclude"] != exclude:
        st.warning("Câu SQL hoặc thiết lập đã đổi – bấm **Hỏi mô hình** lại để cập nhật kết quả bên dưới.")

    # ---- Bước 2: plan + đặc trưng
    st.subheader("Bước 2 – PostgreSQL lập kế hoạch (EXPLAIN) và nhóm trích đặc trưng")
    st.markdown(f"Kế hoạch mặc định: **{plan_summary(p['plan'])}**. EXPLAIN mất **{p['explain_ms']:.1f} ms** "
                "(chưa chạy câu truy vấn).")
    f = p["feat"]
    key_feats = [("Số bảng", f["sql_n_tables"]), ("Số nested loop", f["plan_n_nestloop"]),
                 ("Số hash join", f["plan_n_hashjoin"]), ("Số merge join", f["plan_n_mergejoin"]),
                 ("Số seq scan", f["plan_n_seqscan"]), ("Số index scan", f["plan_n_indexscan"]),
                 ("Số LIKE", f["sql_n_like"]), ("Cost ước lượng", f"{f['plan_total_cost']:,.0f}")]
    cols = st.columns(len(key_feats))
    for c, (k, v) in zip(cols, key_feats):
        c.metric(k, v)
    with st.expander("Xem cây kế hoạch và đủ 34 đặc trưng"):
        st.code(plan_text(p["plan"]), language=None)
        st.dataframe(pd.DataFrame({"đặc trưng": list(f), "giá trị": [round(float(v), 2) for v in f.values()]}),
                     hide_index=True, use_container_width=True, height=300)

    # ---- Bước 3: mô hình chọn
    st.subheader("Bước 3 – Mô hình chọn phương án")
    pred = p["pred"]
    setup = HINT_SQL[pred]
    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.markdown(f"{MODEL_VI[p['model']]} (học trên **{p['n_train']} câu JOB** đã đo"
                    + (f", đã bỏ họ {p['exclude']}" if p["exclude"] else "") + f") chọn:")
        st.markdown(f"### {HINT_VI[pred]}")
        st.code(";\n".join(setup) + ";" if setup else "-- không SET gì, chạy như PostgreSQL bình thường",
                language="sql")
        st.caption(f"Mô hình suy luận mất {p['inf_ms']:.1f} ms. Chi phí thêm so với PostgreSQL ≈ "
                   f"{p['explain_ms'] + p['inf_ms']:.1f} ms (EXPLAIN + suy luận).")
    with c2:
        pr = pd.DataFrame({"phương án": [HINT_VI[h] for h in E.HINTS],
                           "độ tin": [float(p["proba"].get(h, 0.0)) for h in E.HINTS],
                           "chọn": [h == pred for h in E.HINTS]})
        ch = alt.Chart(pr).mark_bar().encode(
            x=alt.X("độ tin:Q", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1]), title="Mô hình tin bao nhiêu"),
            y=alt.Y("phương án:N", sort=[HINT_VI[h] for h in E.HINTS], title=None, axis=alt.Axis(labelLimit=200)),
            color=alt.condition("datum['chọn']", alt.value(BLUE), alt.value("#c8c6c0")),
            tooltip=["phương án", alt.Tooltip("độ tin:Q", format=".0%")])
        st.altair_chart(ch.properties(height=200), use_container_width=True)

    # ---- Bước 4: chạy thật
    st.subheader("Bước 4 – Chạy thật để kiểm tra mô hình đúng hay sai")
    todo = list(E.HINTS)
    st.caption(f"Chạy cả 6 phương án để biết phương án nào thật sự nhanh nhất – mỗi phương án {runs} lần, tối đa "
               f"{timeout_s} s/lần. Câu chạy lâu (như 16b, 26a) có thể mất vài phút.")
    if st.button("Chạy trên PostgreSQL", type="primary", disabled=not ok, key="proto_run"):
        res = {}
        bar = st.progress(0.0)
        for i, h in enumerate(todo):
            bar.progress(i / len(todo), text=f"Đang chạy: {HINT_VI[h]}…")
            try:
                res[h] = run_hint(cfg, p["sql"], h, timeout_s * 1000, int(runs))
            except Exception as e:
                st.error(f"Lỗi khi chạy {HINT_VI[h]}: {str(e).strip().splitlines()[0]}")
                res = None
                break
        bar.empty()
        p["runs"] = res
    if p.get("runs"):
        _show_runs(p, timeout_s)
    _show_recorded(p)


def clean_sql_safe(s):
    try:
        return clean_sql(s)
    except ValueError:
        return None


def _show_runs(p, timeout_s):
    res, pred = p["runs"], p["pred"]
    pg = res["default"]["ms"]
    model_ms = res[pred]["ms"] + p["explain_ms"] + p["inf_ms"]
    sp = pg / model_ms
    c1, c2, c3 = st.columns(3)
    c1.metric("PostgreSQL mặc định", _fmt_ms(pg) + (" (quá giờ)" if res["default"]["timeout"] else ""))
    c2.metric(f"Theo mô hình ({HINT_VI[pred]})", _fmt_ms(model_ms) + (" (quá giờ)" if res[pred]["timeout"] else ""),
              help="Đã cộng thời gian EXPLAIN và suy luận của mô hình.")
    c3.metric("Nhanh hơn", f"{sp:.2f}×")
    if pred == "default":
        st.info("Mô hình chọn **giữ nguyên PostgreSQL** → kết quả bằng PostgreSQL, chỉ tốn thêm vài ms để EXPLAIN và "
                "suy luận. Đây là lựa chọn an toàn.")
    elif sp > 1 + E.EPS:
        st.success(f"**Thắng:** nhanh hơn **{sp:.2f}×** so với để PostgreSQL tự chọn.")
    elif sp < 1 - E.EPS:
        st.error(f"**Thua:** chậm hơn **{1 / sp:.2f}×** so với để PostgreSQL tự chọn.")
    else:
        st.info("**Hòa:** chênh dưới 10% – coi như bằng PostgreSQL (nằm trong mức dao động khi đo).")
    st.caption("Quy ước giống bảng Thắng/Hòa/Thua của Thí nghiệm 2: nhanh hơn > 10% là thắng, chậm hơn > 10% là thua, còn lại là hòa. "
               "Thời gian của mô hình đã cộng EXPLAIN + suy luận.")

    rows = [{"phương án": HINT_VI[h], "thời gian (ms)": r["ms"], "quá giờ": r["timeout"], "mô hình chọn": h == pred}
            for h, r in res.items()]
    df = pd.DataFrame(rows)
    if len(res) > 2:
        best = min(res, key=lambda h: res[h]["ms"])
        st.markdown(f"Phương án nhanh nhất thật sự: **{HINT_VI[best]}** ({_fmt_ms(res[best]['ms'])})"
                    + (" – trùng với mô hình ✅" if best == pred else ""))
    df["màu"] = np.where(df["mô hình chọn"], "Mô hình chọn",
                         np.where(df["phương án"] == HINT_VI["default"], "PostgreSQL mặc định", "Phương án khác"))
    ch = alt.Chart(df).mark_bar().encode(
        x=alt.X("thời gian (ms):Q", title="Thời gian lập kế hoạch + chạy (ms, càng ngắn càng tốt)"),
        y=alt.Y("phương án:N", sort="x", title=None, axis=alt.Axis(labelLimit=200)),
        color=alt.Color("màu:N", scale=alt.Scale(domain=["PostgreSQL mặc định", "Mô hình chọn", "Phương án khác"],
                                                  range=[GREY, BLUE, "#c8c6c0"]), title=None,
                        legend=alt.Legend(orient="top")),
        tooltip=["phương án", alt.Tooltip("thời gian (ms):Q", format=",.1f"), "quá giờ"])
    st.altair_chart(ch.properties(height=alt.Step(34)), use_container_width=True)
    if any(r["timeout"] for r in res.values()):
        st.caption(f"'Quá giờ' = bị dừng sau {timeout_s} s; thời gian thật còn lâu hơn.")
    with st.expander("So sánh cây kế hoạch thực tế"):
        cols = st.columns(2)
        for c, h in zip(cols, list(dict.fromkeys(["default", pred]))):
            c.markdown(f"**{HINT_VI[h]}**")
            c.code(plan_text(res[h]["plan"]) if res[h]["plan"] else "(quá giờ – không có plan)", language=None)


def _show_recorded(p):
    """Với câu JOB nguyên bản: cho xem số đo trong Thí nghiệm 2 để đối chiếu."""
    qid = p.get("qid")
    if qid is None or p["sql"] != clean_sql_safe(job_queries().get(qid, "")):
        return
    _, y, t, _ = training_data()
    if qid not in t.index:
        return
    with st.expander(f"Đối chiếu với số đo câu {qid} trong Thí nghiệm 2 (lần chạy thứ 3)"):
        row = t.loc[qid]
        st.dataframe(pd.DataFrame({"phương án": [HINT_VI[h] for h in E.HINTS],
                                   "thời gian đã đo (ms)": [round(row[h], 1) for h in E.HINTS]}),
                     hide_index=True, use_container_width=True)
        st.caption(f"Nhãn đúng (phương án nhanh nhất, phải nhanh hơn PostgreSQL ≥ 5%): **{HINT_VI[y.loc[qid]]}**. "
                   "Số đo hôm nay có thể lệch một chút do máy và bộ nhớ đệm.")
