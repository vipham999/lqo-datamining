"""Ứng dụng demo: phân loại plan bằng data mining + kết quả của bài báo.

    ~/.venvs/lqo_app/bin/streamlit run app/streamlit_app.py
"""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.tree import export_graphviz

import core
import group_results

st.set_page_config(page_title="Phân loại plan truy vấn", layout="wide")
TEXT_MUTED = "#52514e"


def entity_scale(names):
    order, colors = core.colors_for(list(names))
    return alt.Scale(domain=order, range=colors), order


@st.cache_data(show_spinner=False)
def load(key):
    return core.load_source(key)


@st.cache_data(show_spinner="Đang huấn luyện và đánh giá các mô hình…")
def run_all(key, scheme, task):
    df, xcols, baseline, _ = load(key)
    return core.compare_models(df, xcols, baseline, scheme, task)


@st.cache_data(show_spinner="Đang chạy thuật toán data mining…")
def explain(key, task):
    df, xcols, baseline, _ = load(key)
    imp = core.importance(df, xcols, baseline, task)
    _, tree_text = core.decision_tree(df, xcols, baseline, task)
    rules = core.assoc_rules(df, baseline, task)
    k, sil, pts, summ = core.clusters(df, xcols, baseline)
    return imp, tree_text, rules, k, sil, pts, summ


# ---------------------------------------------------------------- thanh bên: chọn nguồn dữ liệu
st.sidebar.title("Phân loại plan truy vấn")
src_keys = [k for k in core.SOURCES if core.available(k)]
if not src_keys:
    st.error("Chưa có dữ liệu. Chạy: `python app/prepare_data.py` (cần container pg_bao).")
    st.stop()
src = st.sidebar.radio("Nguồn dữ liệu", src_keys, format_func=lambda k: core.SOURCES[k]["ten"])
for k in core.SOURCES:
    if k not in src_keys:
        st.sidebar.caption(f"Nguồn {k} chưa có dữ liệu (cần {', '.join(f.split('/')[-1] for f in core.SOURCES[k]['files'])}).")
df, xcols, baseline, classes = load(src)
st.sidebar.markdown(f"**{len(df)} câu truy vấn** · {df.template.nunique()} truy vấn gốc · {len(xcols)} đặc trưng")
st.sidebar.caption("Bài báo: Lehmann, Sulimov, Stockinger. *Is Your Learned Query Optimizer Behaving As You Expect?* "
                   "PVLDB 17(7), 2024.")

tab0, tab1, tab_e1, tab_e2, tab2, tab3, tab4, tab5 = st.tabs(
    ["0. CSDL IMDB", "1. Kết quả bài báo", "Nhóm: Thí nghiệm 1", "Nhóm: Thí nghiệm 2", "2. Dữ liệu & nhãn",
     "3. Phân loại plan", "4. Giải thích (data mining)", "5. Xem một câu truy vấn"])

# ---------------------------------------------------------------- Kết quả của nhóm (Mục 4 báo cáo)
with tab_e1:
    group_results.render_exp1()
with tab_e2:
    group_results.render_exp2()

# ---------------------------------------------------------------- 0. CSDL IMDB
with tab0:
    st.header("Cơ sở dữ liệu IMDB (benchmark JOB)")
    db = core.load_imdb()
    if db is None:
        st.warning("Chưa có analysis/output/app/imdb_db.json. Chạy `python app/prepare_data.py --db` "
                   "(cần container pg_bao).")
    else:
        tables = pd.DataFrame([{"bảng": t["name"], "nhóm": core.TABLE_INFO.get(t["name"], ("", ""))[0],
                                "ý nghĩa": core.TABLE_INFO.get(t["name"], ("", ""))[1], "số dòng": t["rows"],
                                "dung lượng (MB)": t["bytes"] / 2**20, "số cột": len(t["columns"]),
                                "số câu JOB dùng": t["so_cau_job"]} for t in db["tables"]])
        st.markdown(
            "- **Dữ liệu gốc:** snapshot IMDB dạng CSV (`imdb.tgz`, công bố cùng benchmark JOB – Leis et al., VLDB 2015).\n"
            "- **Lưu trữ:** nạp vào **PostgreSQL 12.5** thành các **bảng quan hệ** (kèm index), "
            "chạy trong Docker container `pg_bao`, database `imdbload`.\n"
            "- **Input của thực nghiệm:** 113 câu SQL của JOB chạy trên CSDL này; mỗi câu nối 4–17 bảng.")
        m = st.columns(4)
        m[0].metric("Số bảng", len(tables))
        m[1].metric("Tổng số dòng", f"{tables['số dòng'].sum() / 1e6:,.1f} triệu")
        m[2].metric("Dung lượng (kèm index)", f"{db['bytes'] / 2**30:,.1f} GB")
        m[3].metric("Phiên bản", db["version"].split(" on ")[0])

        st.subheader("Các bảng")
        gscale = alt.Scale(domain=core.TABLE_GROUPS, range=core.PALETTE[:len(core.TABLE_GROUPS)])
        y = alt.Y("bảng:N", sort="-x", title=None)
        st.altair_chart(alt.Chart(tables).mark_bar(cornerRadiusEnd=4, height=16).encode(
            y=y, x=alt.X("số dòng:Q", title="Số dòng (thang log)", scale=alt.Scale(type="log")),
            color=alt.Color("nhóm:N", scale=gscale, title="Nhóm bảng"),
            tooltip=["bảng", "nhóm", "ý nghĩa", alt.Tooltip("số dòng:Q", format=","),
                     alt.Tooltip("dung lượng (MB):Q", format=",.0f"), "số câu JOB dùng"]
        ).properties(height=22 * len(tables)), use_container_width=True)
        st.dataframe(tables.style.format({"số dòng": "{:,}", "dung lượng (MB)": "{:,.0f}"}),
                     hide_index=True, use_container_width=True)

        st.subheader("Quan hệ giữa các bảng")
        st.markdown("Đọc từ trái sang phải: **phim/người** → **bảng nối và bảng thông tin** → **bảng tra cứu**. "
                    "Mỗi đường là một khóa ngoại trỏ tới cột `id` của bảng kia; nhãn ghi cột khóa ngoại và "
                    "số câu JOB (trên 113) dùng phép nối đó, đường càng đậm càng nhiều câu dùng.")
        st.markdown(" ".join(f'<span style="background:{c};color:white;border-radius:6px;padding:2px 10px;'
                             f'margin-right:6px">{g}</span>'
                             for g, c in zip(core.TABLE_GROUPS, core.PALETTE)), unsafe_allow_html=True)
        show_bridge = st.checkbox("Hiện cả cạnh bắc cầu (vd `movie_keyword.movie_id = movie_info.movie_id`)", False,
                                  help="Các câu JOB thường viết thêm điều kiện nối trực tiếp giữa hai bảng cùng trỏ "
                                       "tới title. Chúng làm optimizer có nhiều thứ tự nối hơn, nhưng làm sơ đồ rối.")
        st.graphviz_chart(core.schema_dot(db, show_bridge), use_container_width=True)

        st.subheader("Xem một bảng")
        name = st.selectbox("Bảng", [t["name"] for t in db["tables"]])
        t = next(t for t in db["tables"] if t["name"] == name)
        st.markdown(f"**{name}** – {core.TABLE_INFO.get(name, ('', ''))[1]} · {t['rows']:,} dòng · "
                    f"{t['bytes'] / 2**20:,.0f} MB · được {t['so_cau_job']}/113 câu JOB sử dụng")
        left, right = st.columns([1, 3])
        left.dataframe(pd.DataFrame(t["columns"]).rename(columns={"name": "cột", "type": "kiểu"}),
                       hide_index=True, use_container_width=True)
        right.dataframe(pd.DataFrame(t["sample"]), hide_index=True, use_container_width=True)
        right.caption("5 dòng đầu của bảng (chuỗi dài bị cắt ở 60 ký tự).")

        st.subheader("Ví dụ: The Matrix (1999) nằm trong các bảng như thế nào")
        st.caption("Mọi bảng `movie_*` và `cast_info` nối với `title` qua `movie_id`.")
        ex = db["example"]
        st.dataframe(pd.DataFrame(ex["title"]), hide_index=True, use_container_width=True)
        c1, c2 = st.columns(2)
        for col, key in ((c1, "cast_info"), (c2, "movie_info_idx"), (c1, "movie_info"),
                         (c2, "movie_companies"), (c1, "movie_keyword")):
            col.markdown(f"**{key}**")
            col.dataframe(pd.DataFrame(ex[key]), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- 1. Kết quả bài báo
with tab1:
    st.header("Kết quả của bài báo (tính lại từ log của tác giả)")
    by_m, summ = core.paper_results()
    if by_m is None:
        st.warning("Chưa có analysis/output/c1_authors_*.csv. Chạy `python scripts/c1_win_loss.py --authors ...`.")
    else:
        st.markdown("So sánh **từng câu** trên tập test của 9 split JOB với PostgreSQL. "
                    "Thắng/thua nếu nhanh/chậm hơn quá 10%. Thời gian end-to-end = suy luận + lập kế hoạch + thực thi.")
        t = by_m.rename(columns={"phương_pháp_gốc": "Phương pháp", "số_câu": "Số câu", "thắng": "Thắng",
                                 "hòa": "Hòa", "thua": "Thua", "PG_workload_s": "PostgreSQL (s)",
                                 "LQO_workload_s": "LQO (s)", "speedup_workload": "Speedup"})
        t = t.sort_values("Speedup", ascending=False)
        st.dataframe(t.style.format({"PostgreSQL (s)": "{:,.1f}", "LQO (s)": "{:,.1f}", "Speedup": "{:.3f}×"}),
                     hide_index=True, use_container_width=True)
        c1, c2 = st.columns(2)
        c1.info("**Thứ hạng theo bài báo (§8.2.1):** PostgreSQL > HybridQO > Bao > Neo > Balsa > LEON")
        c2.success("**Thứ hạng tính lại:** PostgreSQL ≈ " + " > ".join(t["Phương pháp"]))

        st.subheader("Speedup so với PostgreSQL theo từng split")
        s = summ.copy()
        s["kiểu chia"] = s.split.str.replace(r"_split_\d", "", regex=True).map(
            {"leave_one_out": "LOO", "random": "RND", "base_query": "BQ"})
        s["split"] = s["kiểu chia"] + "-" + s.split.str[-1]
        split_order = [f"{k}-{i}" for k in ("LOO", "RND", "BQ") for i in "123"]
        s["log_speedup"] = np.log10(s.speedup_workload).clip(-1, 1)
        s["nhãn"] = s.speedup_workload.map(lambda v: f"{v:.2f}×" if v >= 0.01 else f"{v:.0e}×")
        enc = dict(x=alt.X("split:N", sort=split_order, title=None, axis=alt.Axis(labelAngle=0, orient="top")),
                   y=alt.Y("phương_pháp_gốc:N", sort=list(t["Phương pháp"]), title=None))
        heat = alt.Chart(s).mark_rect(stroke="white", strokeWidth=2, cornerRadius=3).encode(
            **enc, color=alt.Color("log_speedup:Q", title="Speedup",
                                   scale=alt.Scale(domain=[-1, 0, 1], range=["#eb6834", "#f0efec", "#2a78d6"]),
                                   legend=alt.Legend(values=[-1, 0, 1], labelExpr=
                                                     "datum.value == -1 ? '≤0,1× (chậm hơn)' : "
                                                     "datum.value == 0 ? '1× (ngang PG)' : '≥10× (nhanh hơn)'")),
            tooltip=[alt.Tooltip("phương_pháp_gốc:N", title="Phương pháp"), alt.Tooltip("split:N"),
                     alt.Tooltip("speedup_workload:Q", title="Speedup", format=".4f"),
                     alt.Tooltip("thắng:Q"), alt.Tooltip("hòa:Q"), alt.Tooltip("thua:Q")])
        text = alt.Chart(s).mark_text(fontSize=12).encode(
            **enc, text="nhãn:N",
            color=alt.condition("abs(datum.log_speedup) > 0.6", alt.value("white"), alt.value("#0b0b0b")))
        st.altair_chart((heat + text).properties(height=260), use_container_width=True)
        st.caption("Speedup = tổng thời gian PostgreSQL / tổng thời gian LQO trên tập test của split. "
                   "HybridQO dao động quanh 1×, Bao chỉ vượt PostgreSQL ở RND-1, "
                   "LEON chậm hơn hàng nghìn lần do thời gian suy luận.")

# ---------------------------------------------------------------- 2. Dữ liệu & nhãn
with tab2:
    st.header("Dữ liệu và nhãn")
    if src == "A":
        st.markdown(
            "- **Mỗi dòng = một câu JOB** có trong tập test của ít nhất một split của tác giả.\n"
            "- **Thời gian của mỗi phương pháp** = trung vị thời gian end-to-end (lần chạy cuối, hot cache) "
            "qua các split có câu đó trong tập test.\n"
            "- **Nhãn** = phương pháp nhanh nhất; phương pháp khác chỉ thắng PostgreSQL nếu nhanh hơn ít nhất 5%.\n"
            "- **Đặc trưng** = metric của câu SQL + plan mặc định của PostgreSQL (lấy bằng `EXPLAIN`), "
            "tức thông tin có trước khi chạy → không rò rỉ nhãn.")
    else:
        st.markdown("- **Mỗi dòng = một câu JOB.** Nhãn = hint set nhanh nhất (nhanh hơn `default` ít nhất 5%).")
    c1, c2, c3 = st.columns(3)
    n_keep = int((df.best_hint_set == baseline).sum())
    c1.metric("Số câu", len(df))
    c2.metric(f"Giữ {baseline} là tốt nhất", f"{n_keep} câu")
    c3.metric("Nên đổi plan", f"{len(df) - n_keep} câu")

    dist = df.best_hint_set.value_counts().rename_axis("plan").reset_index(name="số_câu")
    scale, order = entity_scale(dist.plan)
    st.altair_chart(alt.Chart(dist).mark_bar(cornerRadiusEnd=4, height=22).encode(
        y=alt.Y("plan:N", sort=order, title=None), x=alt.X("số_câu:Q", title="Số câu có plan này nhanh nhất"),
        color=alt.Color("plan:N", scale=scale, legend=None),
        tooltip=["plan", "số_câu"]).properties(height=40 * len(dist)), use_container_width=True)

    st.subheader("Metric đo câu SQL và plan mặc định")
    show = ["query_id", "best_hint_set", "speedup_vs_default", "sql_n_tables", "sql_n_join_preds",
            "sql_n_filter_preds", "sql_n_like", "plan_n_joins", "plan_n_nestloop", "plan_n_hashjoin",
            "plan_n_mergejoin", "plan_is_bushy", "plan_total_cost", "plan_max_qerror"]
    st.dataframe(df[[c for c in show if c in df]].rename(columns={"best_hint_set": "nhãn",
                                                                  "speedup_vs_default": "speedup"}),
                 hide_index=True, use_container_width=True, height=360)
    if src == "A" and "plan_analyzed" in df and not df.plan_analyzed.any():
        st.caption("q-error chưa có (plan lấy bằng EXPLAIN). Chạy `prepare_data.py --analyze` để có q-error.")

# ---------------------------------------------------------------- 3. Phân loại plan
with tab3:
    st.header("Phân loại plan: mỗi câu nên dùng plan nào?")
    c1, c2, c3 = st.columns(3)
    scheme = c1.selectbox("Kiểu chia dữ liệu (§7.2)", list(core.SCHEMES), index=2,
                          format_func=core.SCHEMES.get)
    task = c2.selectbox("Bài toán", list(core.TASKS), format_func=core.TASKS.get)
    learn = [m for m in core.model_names() if m not in (core.ALWAYS_PG, core.OPTIMAL)]
    model = c3.selectbox("Mô hình", learn, index=learn.index("RandomForest"))

    summary, preds = run_all(src, scheme, task)
    st.session_state["preds"] = (src, scheme, task, model, preds[model])
    r = summary.set_index("mô_hình").loc[model]
    pg = summary.set_index("mô_hình").loc[core.ALWAYS_PG]

    st.markdown(f"### {model} dự đoán đúng **{int(r['số_câu_đúng'])} / {int(r['số_câu'])} câu** "
                f"({r['accuracy']:.0%})")
    st.caption(f"Mốc so sánh “{core.ALWAYS_PG}” đúng {int(pg['số_câu_đúng'])} / {int(pg['số_câu'])} câu. "
               f"Mỗi câu chỉ được dự đoán khi nằm ở tập test của fold (cross-validation theo kiểu chia đã chọn).")
    m = st.columns(5)
    m[0].metric("Macro-F1", f"{r['macro_f1']:.2f}", f"{r['macro_f1'] - pg['macro_f1']:+.2f} so với luôn PG")
    m[1].metric("Thời gian workload", f"{r['workload_mô_hình_s']:,.1f} s",
                f"{r['workload_mô_hình_s'] - r['workload_PG_s']:+,.1f} s so với PG", delta_color="inverse")
    m[2].metric("Speedup so với PostgreSQL", f"{r['speedup_vs_PG']:.3f}×")
    m[3].metric("Số câu bị chậm đi >10%", int(r["số_câu_chậm_đi_>10%"]),
                f"{int(r['số_câu_nhanh_hơn_>10%'])} câu nhanh hơn >10%", delta_color="off")
    m[4].metric("p-value McNemar (so với luôn PG)", f"{r['p_mcnemar']:.3f}")

    left, right = st.columns(2)
    with left:
        st.subheader("Ma trận nhầm lẫn")
        cm = core.confusion(preds[model].nhãn_thật.to_numpy(), preds[model].dự_đoán.to_numpy())
        heat = alt.Chart(cm).mark_rect(stroke="white", strokeWidth=2).encode(
            x=alt.X("dự_đoán:N", title="Dự đoán", axis=alt.Axis(labelAngle=0, labelLimit=140)),
            y=alt.Y("thật:N", title="Nhãn thật"),
            color=alt.Color("số_câu:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=["thật", "dự_đoán", "số_câu"])
        text = alt.Chart(cm).mark_text(fontSize=14).encode(
            x="dự_đoán:N", y="thật:N", text="số_câu:Q",
            color=alt.condition(alt.datum.số_câu > cm.số_câu.max() / 2, alt.value("white"), alt.value("#0b0b0b")))
        st.altair_chart((heat + text).properties(height=320), use_container_width=True)
    with right:
        st.subheader("Tổng thời gian workload")
        wl = pd.DataFrame({"cách chọn plan": [core.ALWAYS_PG, model, core.OPTIMAL],
                           "giây": [r["workload_PG_s"], r["workload_mô_hình_s"], r["workload_tối_ưu_s"]]})
        st.altair_chart(alt.Chart(wl).mark_bar(cornerRadiusEnd=4, height=34, color=core.PALETTE[0]).encode(
            y=alt.Y("cách chọn plan:N", sort=None, title=None), x=alt.X("giây:Q", title="Giây (càng thấp càng tốt)"),
            tooltip=["cách chọn plan", alt.Tooltip("giây:Q", format=",.1f")]).properties(height=200)
            + alt.Chart(wl).mark_text(align="left", dx=6, color=TEXT_MUTED).encode(
                y=alt.Y("cách chọn plan:N", sort=None), x="giây:Q", text=alt.Text("giây:Q", format=",.1f")),
            use_container_width=True)
        st.caption(f"“{core.OPTIMAL}” = luôn chọn đúng plan nhanh nhất (giới hạn trên). "
                   f"Regret của mô hình = {r['regret_s']:,.1f} s.")

    st.subheader(f"So sánh mọi mô hình – {core.SCHEMES[scheme]}")
    cols = {"mô_hình": "Mô hình", "số_câu_đúng": "Số câu đúng", "accuracy": "Accuracy", "macro_f1": "Macro-F1",
            "workload_mô_hình_s": "Workload (s)", "speedup_vs_PG": "Speedup vs PG",
            "số_câu_chậm_đi_>10%": "Chậm đi >10%", "số_câu_nhanh_hơn_>10%": "Nhanh hơn >10%",
            "p_mcnemar": "p McNemar"}
    st.dataframe(summary[list(cols)].rename(columns=cols).style.format(
        {"Accuracy": "{:.0%}", "Macro-F1": "{:.2f}", "Workload (s)": "{:,.1f}", "Speedup vs PG": "{:.3f}×",
         "p McNemar": "{:.3f}"}), hide_index=True, use_container_width=True)
    with st.expander("Dự đoán cho từng câu"):
        st.dataframe(preds[model], hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- 4. Giải thích
with tab4:
    st.header("Giải thích bằng data mining")
    task4 = st.radio("Bài toán", list(core.TASKS), format_func=core.TASKS.get, horizontal=True, key="task4")
    imp, tree_text, rules, k, sil, pts, csum = explain(src, task4)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Metric nào quyết định? (permutation importance)")
        top = imp.head(10)
        st.altair_chart(alt.Chart(top).mark_bar(cornerRadiusEnd=4, height=18, color=core.PALETTE[0]).encode(
            y=alt.Y("đặc_trưng:N", sort="-x", title=None), x=alt.X("importance:Q", title="Mức giảm accuracy khi xáo trộn"),
            tooltip=["đặc_trưng", alt.Tooltip("importance:Q", format=".4f"), alt.Tooltip("std:Q", format=".4f")]
        ).properties(height=320), use_container_width=True)
    with right:
        st.subheader("Đọc kết quả")
        st.markdown(
            f"- Metric quan trọng nhất: **{imp.iloc[0]['đặc_trưng']}**.\n"
            "- `plan_max_qerror` là sai số ước lượng số dòng lớn nhất trong plan PostgreSQL. q-error lớn nghĩa là "
            "optimizer ước lượng sai → plan mặc định dễ chưa tốt → đáng cân nhắc đổi plan.\n"
            "- Permutation importance = accuracy giảm bao nhiêu khi xáo trộn ngẫu nhiên metric đó.")

    st.subheader("Cây quyết định (độ sâu 3)")
    tree, _ = core.decision_tree(df, xcols, baseline, task4)
    dot = export_graphviz(tree, feature_names=list(xcols), class_names=list(tree.classes_), impurity=False,
                          rounded=True, label="root", precision=1)
    st.graphviz_chart(dot.replace("fontname=\"helvetica\"", "fontname=\"helvetica\", fontsize=16"),
                      use_container_width=True)
    with st.expander("Luật dạng văn bản"):
        st.code(tree_text)

    st.subheader("Luật kết hợp (Apriori)")
    if rules.empty:
        st.info("Không có luật nào đạt support ≥ 0,05 và confidence ≥ 0,5.")
    else:
        st.dataframe(rules.head(15).style.format({"support": "{:.2f}", "confidence": "{:.0%}", "lift": "{:.2f}"}),
                     hide_index=True, use_container_width=True)

    st.subheader(f"Phân cụm K-means (k = {k}, silhouette = {sil:.2f})")
    left, right = st.columns([3, 2])
    with left:
        cscale = alt.Scale(domain=sorted(pts["cụm"].unique()), range=core.PALETTE[:k])
        st.altair_chart(alt.Chart(pts).mark_circle(size=90, opacity=0.85, stroke="white", strokeWidth=1.5).encode(
            x=alt.X("PC1:Q"), y=alt.Y("PC2:Q"), color=alt.Color("cụm:N", scale=cscale, title="Cụm"),
            tooltip=["query_id", "cụm", "plan_tốt_nhất", "speedup"]).properties(height=360),
            use_container_width=True)
    with right:
        st.dataframe(csum.style.format({"tỉ_lệ_nên_đổi_plan": "{:.0%}", "speedup_trung_vị": "{:.2f}",
                                        "số_bảng_tb": "{:.1f}"}), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- 5. Xem một câu
with tab5:
    st.header("Xem một câu truy vấn")
    qid = st.selectbox("Câu truy vấn", list(df.query_id))
    row = df.set_index("query_id").loc[qid]
    plans = core.load_plans()

    c1, c2, c3 = st.columns(3)
    c1.metric("Plan nhanh nhất (nhãn thật)", row.best_hint_set)
    c2.metric("Speedup so với PostgreSQL", f"{row.speedup_vs_default:.2f}×")
    p = st.session_state.get("preds")
    if p and p[0] == src:
        pr = p[4].set_index("query_id").loc[qid]
        c3.metric(f"{p[3]} dự đoán ({core.SCHEMES[p[1]].split(' (')[0]})", pr.dự_đoán,
                  "đúng" if pr.đúng else "sai", delta_color="normal" if pr.đúng else "inverse")
    else:
        c3.caption("Mở tab 3 để huấn luyện mô hình trước.")

    times = pd.DataFrame({"plan": classes, "ms": [float(row[f"t_{c}"]) for c in classes]}).dropna()
    times["gốc"] = times.ms.min() / 3          # thang log không có 0 → cột bắt đầu từ một mốc dương
    times["nhãn"] = times.ms.map(lambda v: f"{v:,.0f} ms" if v < 60_000 else f"{v / 60_000:,.1f} phút")
    scale, order = entity_scale(times.plan)
    y = alt.Y("plan:N", sort=order, title=None)
    bars = alt.Chart(times).mark_bar(cornerRadiusEnd=4, height=22).encode(
        y=y, x=alt.X("ms:Q", title="Thời gian end-to-end (ms, thang log)", scale=alt.Scale(type="log")),
        x2="gốc:Q", color=alt.Color("plan:N", scale=scale, legend=None),
        tooltip=["plan", alt.Tooltip("ms:Q", format=",.1f", title="ms")])
    labels = alt.Chart(times).mark_text(align="left", dx=6, color=TEXT_MUTED).encode(y=y, x="ms:Q", text="nhãn:N")
    st.altair_chart((bars + labels).properties(height=40 * len(times)), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Câu SQL")
        st.code(plans.get(qid, {}).get("sql", "(không có)"), language="sql")
    with right:
        st.subheader("Plan mặc định của PostgreSQL")
        if qid in plans:
            st.code("\n".join(core.plan_lines(plans[qid]["plan"])), language="text")
        else:
            st.info("Chưa có plan (chạy prepare_data.py).")
