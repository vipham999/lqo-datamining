"""Hai tab kết quả của nhóm (Mục 4 báo cáo): Thí nghiệm 1 – kiểm chứng bài báo, Thí nghiệm 2 – mô hình phân loại.

Chỉ đọc các file kết quả đã tính sẵn, không chạy lại thí nghiệm:
  analysis/output/exp1/            ← scripts/exp1_tables.py
  analysis/output/ablation_*       ← scripts/ablation_analyze.py
  analysis/output/exp2/            ← scripts/exp2_analyze.py
"""
import glob
import os

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import core

E1 = os.path.join(core.OUT, "exp1")
E2 = os.path.join(core.OUT, "exp2")
GREY = "#898781"
MUTED = "#52514e"
SPLITS = [f"{k}-{i}" for k in ("LOO", "RND", "BQ") for i in "123"]
TYPES = ["LOO", "RND", "BQ"]
TYPE_NAME = {"LOO": "Leave One Out (dễ)", "RND": "Random", "BQ": "Base Query (khó)"}
# Màu cố định: PostgreSQL, Bao, HybridQO giữ màu như các tab khác; mô hình của nhóm dùng màu riêng
METHOD_COLOR = {"PostgreSQL": core.PALETTE[0], "Bao": core.PALETTE[1], "HybridQO": core.PALETTE[2],
                "Neo": core.PALETTE[3], "Balsa": core.PALETTE[4], "LEON": core.PALETTE[5],
                "DecisionTree": core.PALETTE[6], "RandomForest": core.PALETTE[7], "LightGBM": "#0a9396",
                "Oracle": GREY}
OUTCOME_COLOR = {"Thắng": "#1baf7a", "Hòa": "#c8c6c0", "Thua": "#e34948"}
MODELS = ["DecisionTree", "RandomForest", "LightGBM"]


def _scale(names):
    names = list(dict.fromkeys(names))
    return alt.Scale(domain=names, range=[METHOD_COLOR.get(n, GREY) for n in names])


def _missing(files, how):
    miss = [f for f in files if not os.path.exists(f)]
    if miss:
        st.warning(f"Chưa có {', '.join(os.path.relpath(f, core.ROOT) for f in miss)}. Chạy `{how}`.")
    return bool(miss)


def _wtl_bars(df, y, y_title, order):
    """Thanh ngang 100%: tỉ lệ thắng / hòa / thua so với PostgreSQL."""
    long = df[[y, "Thắng", "Hòa", "Thua"]].melt(id_vars=[y], value_vars=["Thắng", "Hòa", "Thua"], var_name="kết quả", value_name="số_câu")
    long["tỉ_lệ"] = long.số_câu / long.groupby(y).số_câu.transform("sum")
    long["thứ_tự"] = long["kết quả"].map({"Thắng": 0, "Hòa": 1, "Thua": 2})
    bars = alt.Chart(long).mark_bar(height=24).encode(
        y=alt.Y(f"{y}:N", sort=order, title=y_title),
        x=alt.X("tỉ_lệ:Q", stack="normalize", title="Tỉ lệ số lần kiểm tra", axis=alt.Axis(format="%")),
        color=alt.Color("kết quả:N", scale=alt.Scale(domain=list(OUTCOME_COLOR), range=list(OUTCOME_COLOR.values())),
                        sort=list(OUTCOME_COLOR), title=None, legend=alt.Legend(orient="top")),
        order=alt.Order("thứ_tự:Q"),
        tooltip=[y, "kết quả", "số_câu", alt.Tooltip("tỉ_lệ:Q", format=".0%")])
    return bars.properties(height=40 * df[y].nunique())


# ================================================================ Thí nghiệm 1
def render_exp1():
    st.header("Thí nghiệm 1 – Kiểm chứng kết luận của bài báo trên máy của nhóm")
    f_tot, f_split, f_83 = (os.path.join(E1, f) for f in
                            ("exp1_total_233.csv", "exp1_bao_hybridqo_per_split.csv", "exp1_ablation_8_3.csv"))
    if _missing([f_tot, f_split], "python3 scripts/exp1_tables.py"):
        return
    st.markdown(
        "- **Chạy lại:** Bao trên MacBook M1 (PostgreSQL 12.5 trong Docker), HybridQO trên Kaggle (11 epoch, so ở epoch 10). "
        "Neo, Balsa, LEON cần GPU và 20–130 giờ mỗi split → dùng log tác giả công bố.\n"
        "- **Cách đo theo khuyến nghị của bài báo:** đúng 9 split JOB (LOO / Random / Base Query × 3 = 233 lần kiểm tra), "
        "cache nóng, mỗi câu chạy 3 lần lấy lần thứ 3, thời gian end-to-end = suy luận + lập kế hoạch + thực thi.\n"
        "- **Thắng / thua** khi nhanh / chậm hơn PostgreSQL quá 10% trên cùng câu.")

    tot = pd.read_csv(f_tot)
    tot["nguồn_ngắn"] = np.where(tot.nguồn.str.startswith("nhóm"), "Nhóm", "Bài báo")
    tot["dòng"] = tot.phương_pháp + " – " + tot.nguồn_ngắn
    g = tot.set_index(["phương_pháp", "nguồn_ngắn"])
    m = st.columns(4)
    for i, meth in enumerate(["Bao", "HybridQO"]):
        a, b = g.loc[(meth, "Nhóm")], g.loc[(meth, "Bài báo")]
        m[2 * i].metric(f"{meth} – tỉ lệ thua (nhóm)", f"{a.tỉ_lệ_thua:.0%}",
                        f"bài báo {b.tỉ_lệ_thua:.0%}", delta_color="off")
        m[2 * i + 1].metric(f"{meth} – speedup tổng (nhóm)", f"{a.speedup:.2f}×",
                            f"bài báo {b.speedup:.2f}×", delta_color="off")

    st.subheader("Thắng / hòa / thua so với PostgreSQL trên 233 lần kiểm tra")
    order = ["Bao – Nhóm", "Bao – Bài báo", "HybridQO – Nhóm", "HybridQO – Bài báo",
             "Neo – Bài báo", "Balsa – Bài báo", "LEON – Bài báo"]
    w = tot.rename(columns={"thắng": "Thắng", "hòa": "Hòa", "thua": "Thua"})
    st.altair_chart(_wtl_bars(w, "dòng", None, order), width="stretch")
    c1, c2 = st.columns(2)
    c1.success("**Khớp với bài báo:** không LQO nào thắng PostgreSQL ở đa số câu; thứ hạng theo từng câu "
               "PostgreSQL > HybridQO > Bao > Neo > Balsa > LEON giữ nguyên.")
    c2.info("**Khác bài báo:** Bao của nhóm thắng 28 câu (bài báo 9) vì Mac chỉ có work_mem 256 MB nên PostgreSQL "
            "chậm 2–3,5× ở các câu join lớn (họ 17, 25c, 18c). HybridQO của nhóm thắng 0 câu (bài báo 34) vì nhóm đo "
            "PostgreSQL trong cùng lần chạy, không bị nhiễu giữa hai lần đo.")

    st.subheader("Theo từng split: speedup trung vị theo câu (nhỏ hơn 1 = PostgreSQL nhanh hơn ở câu điển hình)")
    ps = pd.read_csv(f_split)
    rows = []
    for _, r in ps.iterrows():
        for meth, pre in (("Bao", "Bao"), ("HybridQO", "HQO")):
            for src, suf in (("Nhóm", "nhóm"), ("Bài báo", "tác_giả")):
                rows.append({"split": r.split.strip(), "phương_pháp": meth, "nguồn": src,
                             "trung_vị": r[f"{pre}_{suf}_trung_vị"], "speedup_tổng": r[f"{pre}_{suf}_speedup"],
                             "T/H/Th": r[f"{pre}_{suf}_T/H/Th"]})
    long = pd.DataFrame(rows)
    base = alt.Chart(long).encode(
        x=alt.X("split:N", sort=SPLITS, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("trung_vị:Q", title="Speedup trung vị", scale=alt.Scale(domain=[0, 1.2])),
        color=alt.Color("phương_pháp:N", scale=_scale(["Bao", "HybridQO"]), title=None),
        shape=alt.Shape("nguồn:N", scale=alt.Scale(domain=["Nhóm", "Bài báo"], range=["circle", "triangle"]),
                        title=None),
        tooltip=["split", "phương_pháp", "nguồn", alt.Tooltip("trung_vị:Q", format=".2f"),
                 alt.Tooltip("speedup_tổng:Q", format=".2f"), "T/H/Th"])
    one = alt.Chart(pd.DataFrame({"y": [1]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((one + base.mark_point(size=110, filled=True, opacity=0.9)).properties(height=320),
                    width="stretch")
    with st.expander("Bảng số liệu từng split"):
        st.dataframe(ps.style.format({c: "{:.2f}" for c in ps.columns if "speedup" in c or "trung_vị" in c}),
                     hide_index=True, width="stretch")

    st.subheader("Ablation")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**8.4 Tắt bitmap/tid scan và 8.5 tắt GEQO** (chạy xen kẽ 3 cấu hình, 3 lần mỗi câu)")
        abl = []
        for name, label in (("no_geqo", "Tắt GEQO (8.5)"), ("no_bitmap_tidscan", "Tắt bitmap/tid scan (8.4)")):
            fs = sorted(glob.glob(os.path.join(core.OUT, f"ablation_{name}_interleaved_*.csv")))
            if not fs:
                continue
            d = pd.read_csv(fs[-1])
            sig = d[(d.p_welch < 0.05) & (d.delta_ms.abs() > 250)].sort_values("ti_le", ascending=False)
            abl.append({"cấu hình": label, "tổng (default → ablation)":
                        f"{d.default_ms.sum() / 1000:,.1f} s → {d.ablation_ms.sum() / 1000:,.1f} s",
                        "câu khác biệt có ý nghĩa": ", ".join(f"{q} ({t:.1f}×)" for q, t in zip(sig['query'], sig.ti_le)),
                        "tỉ lệ trung vị, câu ≥ 12 bảng": d[d.n_bang >= 12].ti_le.median()})
        if abl:
            st.dataframe(pd.DataFrame(abl).style.format({"tỉ lệ trung vị, câu ≥ 12 bảng": "{:.2f}×"}),
                         hide_index=True, width="stretch")
            st.caption("Tỉ lệ > 1 = chậm đi khi áp dụng ablation. Tắt GEQO chỉ ảnh hưởng câu từ 12 bảng trở lên "
                       "(29a–c chậm 15–23×); tắt bitmap scan làm 15c chậm 9,3× (bài báo: chậm 1,5×).")
    with a2:
        st.markdown("**8.3 Dữ liệu thay đổi:** Bao dùng model train trên IMDB đầy đủ, chạy trên IMDB còn 50%")
        if os.path.exists(f_83):
            d = pd.read_csv(f_83)
            d["split"] = d.split.str.extract(r"job__(\w+?)_split_(\d)").apply(
                lambda r: {"leave_one_out": "LOO", "random": "RND"}.get(r[0], r[0]) + "-" + r[1], axis=1)
            st.dataframe(d[["split", "T/H/Th", "speedup", "trung_vị"]].style.format(
                {"speedup": "{:.2f}×", "trung_vị": "{:.2f}"}), hide_index=True, width="stretch")
            st.caption("Bao thua gần hết các câu (trung vị 0,43–0,50): model cũ chọn plan kém khi dữ liệu đổi. "
                       "Speedup tổng 2,30× của LOO-1 do một câu Bao nhanh hơn 11,5×.")


# ================================================================ Thí nghiệm 2
@st.cache_data(show_spinner=False)
def _load_exp2():
    split = pd.read_csv(os.path.join(E2, "exp2_summary_per_split.csv"))
    pq = pd.read_csv(os.path.join(E2, "exp2_per_query.csv"))
    lab = pd.read_csv(os.path.join(E2, "exp2_labels.csv"))
    imp = pd.read_csv(os.path.join(E2, "exp2_feature_importance_rf.csv"), index_col=0)
    with open(os.path.join(E2, "exp2_rules_decision_tree.txt")) as f:
        rules = f.read()
    split["split"] = split.split.str.strip()
    pq["kiểu"] = pq.split.str.split("-").str[0]
    return split, pq, lab, imp, rules


def render_exp2():
    st.header("Thí nghiệm 2 – Mô hình phân loại gọn nhẹ chọn phương án cho PostgreSQL")
    need = [os.path.join(E2, f) for f in ("exp2_summary_per_split.csv", "exp2_per_query.csv", "exp2_labels.csv",
                                          "exp2_feature_importance_rf.csv", "exp2_rules_decision_tree.txt")]
    if _missing(need, "~/.venvs/lqo-exp2/bin/python scripts/exp2_analyze.py"):
        return
    split, pq, lab, imp, rules = _load_exp2()
    st.markdown(
        "- **Bài toán:** với mỗi câu SQL, chọn 1 trong 6 phương án: `default` hoặc tắt một toán tử "
        "(`no_nestloop`, `no_hashjoin`, `no_mergejoin`, `no_seqscan`, `no_indexscan`).\n"
        "- **Dữ liệu:** 113 câu JOB × 6 phương án × 3 lần (lấy lần thứ 3). Nhãn = phương án nhanh nhất, "
        "giữ `default` nếu không nhanh hơn ít nhất 5%.\n"
        "- **Đặc trưng:** câu SQL + plan mặc định từ `EXPLAIN` (không ANALYZE) – chỉ thông tin có trước khi chạy.\n"
        "- **Đánh giá:** train/test trên đúng 9 split của bài báo; thời gian của mô hình = EXPLAIN + suy luận + "
        "thời gian của phương án được chọn.")

    # ---------------- tổng 233 lần kiểm tra
    agg = split.groupby("phương_pháp")[["số_câu", "thắng", "hòa", "thua", "PG_s", "phương_pháp_s"]].sum()
    agg["speedup"] = agg.PG_s / agg.phương_pháp_s
    agg["tỉ_lệ_thua"] = agg.thua / agg.số_câu
    acc = pq.assign(đúng=pq.nhãn_thật == pq.dự_đoán).groupby("mô_hình").đúng.mean()
    m = st.columns(4)
    m[0].metric("Oracle (giới hạn trên)", f"{agg.loc['Oracle', 'speedup']:.2f}×", "chọn đúng mọi câu",
                delta_color="off")
    best = agg.loc[MODELS].speedup.idxmax()
    m[1].metric(f"Mô hình tốt nhất ({best})", f"{agg.loc[best, 'speedup']:.2f}×",
                f"{agg.loc[best, 'speedup'] - 1:+.0%} so với PostgreSQL")
    m[2].metric("Tỉ lệ thua: mô hình", f"{agg.loc[MODELS, 'tỉ_lệ_thua'].min():.0%}–{agg.loc[MODELS, 'tỉ_lệ_thua'].max():.0%}",
                f"Bao {agg.loc['Bao', 'tỉ_lệ_thua']:.0%}", delta_color="off")
    m[3].metric("Accuracy", f"{acc.min():.0%}–{acc.max():.0%}", "3 mô hình", delta_color="off")

    st.subheader("Thắng / hòa / thua so với PostgreSQL (233 lần kiểm tra)")
    order = ["Oracle", "DecisionTree", "LightGBM", "RandomForest", "Bao"]
    w = agg.loc[order].reset_index().rename(columns={"thắng": "Thắng", "hòa": "Hòa", "thua": "Thua"})
    w["phương_pháp"] = w.phương_pháp.map(lambda s: f"{s}  ({agg.loc[s, 'speedup']:.2f}×)")
    st.altair_chart(_wtl_bars(w, "phương_pháp", None, list(w.phương_pháp)), width="stretch")
    st.caption("Trong ngoặc: speedup tổng = thời gian PostgreSQL / thời gian của phương pháp. "
               "Bao lấy từ Thí nghiệm 1 (cùng câu test, đo ở phiên khác nên so tỉ lệ, không so số giây).")

    st.subheader("Speedup tổng theo từng split")
    sp = split[split.phương_pháp.isin(["Oracle", "Bao"] + MODELS)]
    meths = ["Oracle"] + MODELS + ["Bao"]
    pts = alt.Chart(sp).mark_point(size=110, filled=True, opacity=0.9).encode(
        x=alt.X("split:N", sort=SPLITS, title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("phương_pháp:N", sort=meths),
        y=alt.Y("speedup:Q", title="Speedup so với PostgreSQL (thang log)", scale=alt.Scale(type="log")),
        color=alt.Color("phương_pháp:N", scale=_scale(meths), sort=meths, title=None),
        tooltip=["split", "phương_pháp", alt.Tooltip("speedup:Q", format=".2f"), "thắng", "hòa", "thua",
                 alt.Tooltip("accuracy:Q", format=".0%")])
    one = alt.Chart(pd.DataFrame({"y": [1]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((one + pts).properties(height=340), width="stretch")

    # ---------------- giả thuyết
    st.subheader("Kiểm định hai giả thuyết (Bảng 6)")
    h1, h2 = st.columns(2)
    with h1:
        faster = [mm for mm in MODELS if agg.loc[mm, "speedup"] > 1]
        fewer = [mm for mm in MODELS if agg.loc[mm, "tỉ_lệ_thua"] < agg.loc["Bao", "tỉ_lệ_thua"]]
        st.markdown("**H1: mô hình nhanh hơn PostgreSQL và không thua Bao**")
        st.markdown(
            f"- H1a – nhanh hơn PostgreSQL: **{'chấp nhận' if faster else 'bác bỏ'}**. Speedup tổng "
            + ", ".join(f"{mm} {agg.loc[mm, 'speedup']:.2f}×" for mm in MODELS)
            + f"; Oracle cho thấy còn {agg.loc['Oracle', 'speedup']:.2f}× để khai thác.\n"
            f"- H1b – không thua Bao: **đúng một nửa**. Theo từng câu, mô hình thua "
            f"{agg.loc[MODELS, 'tỉ_lệ_thua'].min():.0%}–{agg.loc[MODELS, 'tỉ_lệ_thua'].max():.0%} số câu, "
            f"ít hơn Bao ({agg.loc['Bao', 'tỉ_lệ_thua']:.0%}){' ✔' if len(fewer) == 3 else ''}; theo tổng thời gian "
            f"Bao vẫn hơn ({agg.loc['Bao', 'speedup']:.2f}×).")
        loss = pq[(pq.PG_ms / pq.e2e_ms) < 0.9]
        wrong = loss[loss.dự_đoán != "default"]
        st.caption(f"Vì sao thua: chọn sai phương án đắt đỏ (vd 26a + no_hashjoin: 5,7 s → 32 s) và chi phí EXPLAIN "
                   f"khoảng {pq.explain_ms.mean():.0f} ms mỗi câu. Trong {len(loss)} lần thua của 3 mô hình, "
                   f"{len(wrong)} lần do chọn sai phương án, {len(loss) - len(wrong)} lần chỉ do chi phí cộng thêm.")
    with h2:
        st.markdown("**H2: mô hình kém nhất với loại câu chưa từng học (Base Query)**")
        a = (pq.assign(đúng=pq.nhãn_thật == pq.dự_đoán).groupby(["mô_hình", "kiểu"]).đúng.mean()
             .rename("accuracy").reset_index())
        lowest_bq = all(a[a.mô_hình == mm].set_index("kiểu").accuracy.idxmin() == "BQ" for mm in MODELS)
        st.markdown(f"- Theo độ chính xác: **{'chấp nhận' if lowest_bq else 'chưa rõ'}** – accuracy thấp nhất ở "
                    "Base Query với cả 3 mô hình.\n- Theo thời gian: chưa rõ, vì vài câu chọn sai rất đắt rơi vào LOO.")
        st.altair_chart(alt.Chart(a).mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X("kiểu:N", sort=TYPES, title=None, axis=alt.Axis(labelAngle=0, labelExpr=
                    "datum.value == 'LOO' ? 'LOO (dễ)' : datum.value == 'BQ' ? 'BQ (khó)' : 'RND'")),
            xOffset=alt.XOffset("mô_hình:N", sort=MODELS),
            y=alt.Y("accuracy:Q", title="Accuracy", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("mô_hình:N", scale=_scale(MODELS), sort=MODELS, title=None,
                            legend=alt.Legend(orient="top")),
            tooltip=["mô_hình", "kiểu", alt.Tooltip("accuracy:Q", format=".0%")]).properties(height=260),
            width="stretch")

    # ---------------- mô hình học được gì
    st.subheader("Mô hình học được gì")
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Luật chọn phương án** (cây quyết định độ sâu 4, train trên cả 113 câu)")
        st.code(rules.split("\n\n", 1)[-1], language="text")
    with right:
        st.markdown("**10 đặc trưng quan trọng nhất** (Random Forest)")
        top = imp.head(10).reset_index().rename(columns={"index": "đặc_trưng"})
        top.columns = ["đặc_trưng", "importance"]
        st.altair_chart(alt.Chart(top).mark_bar(cornerRadiusEnd=4, height=16, color=core.PALETTE[0]).encode(
            y=alt.Y("đặc_trưng:N", sort="-x", title=None), x=alt.X("importance:Q", title="Mức quan trọng"),
            tooltip=["đặc_trưng", alt.Tooltip("importance:Q", format=".3f")]).properties(height=320),
            width="stretch")
        dist = lab.nhãn.value_counts()
        st.caption("Phân bố nhãn (113 câu): " + ", ".join(f"{k} {v}" for k, v in dist.items()) + ".")

    # ---------------- xem một câu
    st.subheader("Xem một câu: 6 phương án và lựa chọn của mô hình")
    qs = sorted(lab.query_id, key=lambda q: (int("".join(c for c in q if c.isdigit())), q))
    qid = st.selectbox("Câu truy vấn", qs, index=qs.index("26a") if "26a" in qs else 0, key="exp2_q")
    r = lab.set_index("query_id").loc[qid]
    hints = core.HINT_SETS
    t = pd.DataFrame({"phương_án": hints, "ms": [float(r[f"t_{h}_ms"]) for h in hints]})
    t["nhãn"] = t.ms.map(lambda v: f"{v:,.0f} ms" if v < 10_000 else f"{v / 1000:,.1f} s")
    t["gốc"] = t.ms.min() / 3
    c1, c2 = st.columns([3, 2])
    with c1:
        y = alt.Y("phương_án:N", sort=hints, title=None)
        bars = alt.Chart(t).mark_bar(cornerRadiusEnd=4, height=22).encode(
            y=y, x=alt.X("ms:Q", title="Thời gian lần chạy thứ 3 (ms, thang log)", scale=alt.Scale(type="log")),
            x2="gốc:Q", color=alt.condition(alt.datum.phương_án == r.nhãn, alt.value(core.PALETTE[2]),
                                           alt.value(GREY)),
            tooltip=["phương_án", alt.Tooltip("ms:Q", format=",.1f")])
        txt = alt.Chart(t).mark_text(align="left", dx=6, color=MUTED).encode(y=y, x="ms:Q", text="nhãn:N")
        st.altair_chart((bars + txt).properties(height=230), width="stretch")
        st.caption(f"Nhãn thật: **{r.nhãn}** (tô xanh lá). Oracle nhanh hơn PostgreSQL "
                   f"{r.t_default_ms / r.best_ms:.2f}×.")
    with c2:
        p = pq[(pq.query_id == qid)].copy()
        if p.empty:
            st.info("Câu này không nằm trong tập test của split nào.")
        else:
            p["speedup"] = p.PG_ms / p.e2e_ms
            st.dataframe(p[["split", "mô_hình", "dự_đoán", "speedup"]].rename(
                columns={"dự_đoán": "mô hình chọn"}).style.format({"speedup": "{:.2f}×"}).map(
                lambda v: "color: #e34948" if isinstance(v, float) and v < 0.9 else
                ("color: #1baf7a" if isinstance(v, float) and v > 1.1 else ""), subset=["speedup"]),
                hide_index=True, width="stretch", height=260)
            st.caption("Mỗi dòng: một split có câu này trong tập test. Speedup tính cả EXPLAIN và suy luận.")
