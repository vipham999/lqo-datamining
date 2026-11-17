"""Dashboard: CSDL IMDB & JOB, kết quả bài báo so với nhóm, Thí nghiệm 1 và 2 của nhóm.

    ~/.venvs/lqo_app/bin/streamlit run app/streamlit_app.py
"""
import os

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import core
import group_results
import prototype

st.set_page_config(page_title="Learned query optimizer – Nhóm 1", layout="wide")

st.sidebar.title("Learned query optimizer")
st.sidebar.caption("Bài báo: Lehmann, Sulimov, Stockinger. *Is Your Learned Query Optimizer Behaving As You Expect?* "
                   "PVLDB 17(7), 2024.")

tab0, tab1, tab_e1, tab_e2, tab_mine, tab_proto = st.tabs(
    ["0. Dữ liệu IMDB & JOB", "1. Bài báo vs Nhóm", "2. Nhóm: Thí nghiệm 1", "3. Nhóm: Thí nghiệm 2",
     "4. Khai phá dữ liệu", "5. Demo mô hình"])

with tab1:
    group_results.render_paper_vs_group()
with tab_e1:
    group_results.render_exp1()
with tab_e2:
    group_results.render_exp2()
with tab_mine:
    group_results.render_mining()
with tab_proto:
    prototype.render()

# ---------------------------------------------------------------- 0. CSDL IMDB
@st.cache_data(show_spinner=False)
def job_overview():
    return core.job_overview()


with tab0:
    st.header("Dữ liệu: CSDL IMDB và 113 câu truy vấn JOB")
    db = core.load_imdb()
    job = job_overview()
    has_t = "pg_ms" in job and job.pg_ms.notna().all()

    # ---- IMDB
    st.subheader("Cơ sở dữ liệu IMDB")
    st.markdown("Dữ liệu **phim thật** của IMDB (phim, diễn viên, công ty, từ khóa…). Dữ liệu thật phân bố lệch nên "
                "PostgreSQL **hay đoán sai số dòng** và dễ chọn sai cách chạy. Vì vậy bài báo dùng IMDB.")
    if db is None:
        st.warning("Chưa có analysis/output/app/imdb_db.json. Chạy `python app/prepare_data.py` "
                   "(cần container pg_bao).")
    else:
        tables = pd.DataFrame([{"bảng": t["name"], "nhóm": core.TABLE_INFO.get(t["name"], ("", ""))[0],
                                "ý nghĩa": core.TABLE_INFO.get(t["name"], ("", ""))[1], "số dòng": t["rows"],
                                "số câu JOB dùng": t["so_cau_job"]} for t in db["tables"]])
        m = st.columns(4)
        m[0].metric("Số bảng", len(tables))
        m[1].metric("Tổng số dòng", f"{tables['số dòng'].sum() / 1e6:,.1f} triệu")
        m[2].metric("Dung lượng (kèm index)", f"{db['bytes'] / 2**30:,.1f} GB")
        m[3].metric("Bảng lớn nhất", "cast_info",
                    f"{tables.set_index('bảng').loc['cast_info', 'số dòng'] / 1e6:,.1f} triệu dòng",
                    delta_color="off", delta_arrow="off")
        with st.expander("Xem 21 bảng và sơ đồ quan hệ"):
            st.dataframe(tables.sort_values("số dòng", ascending=False).style.format({"số dòng": "{:,}"}),
                         hide_index=True, width="stretch", height=280)
            st.markdown(" ".join(f'<span style="background:{c};color:white;border-radius:6px;padding:2px 10px;'
                                 f'margin-right:6px">{g}</span>'
                                 for g, c in zip(core.TABLE_GROUPS, core.PALETTE)), unsafe_allow_html=True)
            st.graphviz_chart(core.schema_dot(db, False), width="stretch")
            st.caption("Mỗi đường là một khóa ngoại, ghi cột nối và số câu JOB dùng.")

    # ---- JOB
    st.subheader("Benchmark JOB")
    k = st.columns(4)
    k[0].metric("Số câu truy vấn", len(job))
    k[1].metric("Số họ câu", job["họ"].nunique(), "1a … 33c", delta_color="off", delta_arrow="off")
    k[2].metric("Số bảng nối mỗi câu", f"{job['số_bảng'].min()}–{job['số_bảng'].max()}",
                delta_color="off", delta_arrow="off")
    if has_t:
        k[3].metric("Tổng thời gian PostgreSQL", f"{job.pg_ms.sum() / 1000:,.0f} giây", delta_color="off")
    st.markdown(
        "- **113 câu SELECT**, mỗi câu nối nhiều bảng.\n"
        f"- Chia thành **{job['họ'].nunique()} họ**: câu cùng họ (16a, 16b, …) chỉ khác điều kiện lọc.\n"
        "- 3 cách chia train/test, khó dần: *Leave One Out* (mỗi họ 1 câu làm test), *Random* (ngẫu nhiên), "
        "*Base Query* (cả họ làm test – loại câu chưa từng gặp).")

    if has_t:
        top10 = job.pg_ms.nlargest(10).sum() / job.pg_ms.sum()
        c1, c2 = st.columns([3, 2])
        c1.altair_chart(alt.Chart(job, title="Thời gian chạy của từng câu trên PostgreSQL").mark_circle(
            size=70, opacity=0.8, color=core.PALETTE[0]).encode(
            x=alt.X("số_bảng:Q", title="Số bảng nối trong câu", scale=alt.Scale(domain=[3, 18])),
            y=alt.Y("pg_ms:Q", title="Thời gian (ms, thang log)", scale=alt.Scale(type="log", domain=[10, 30000]),
                    axis=alt.Axis(values=[10, 100, 1000, 10000])),
            tooltip=["câu", "số_bảng", alt.Tooltip("pg_ms:Q", format=",.0f", title="ms")]),
            width="stretch", height=300)
        with c2:
            st.markdown(
                f"**Thấy gì:** từ **{job.pg_ms.min():.0f} ms** tới **{job.pg_ms.max() / 1000:.0f} giây**, không "
                f"phụ thuộc số bảng. 10 câu chậm nhất chiếm **{top10:.0%}** tổng thời gian.\n\n"
                "**Rút ra:** vài câu chậm quyết định tổng → nhóm xét thêm **từng câu**.")

    t = job.set_index("câu").pg_ms if has_t else None

    def ms(v):
        if v is None or not has_t:
            return "–"
        return f"{v / 1000:.1f} giây".replace(".", ",") if v >= 1000 else f"{v:.0f} ms"

    st.subheader("Vài câu đáng nhớ")
    f17 = t[[q for q in t.index if q.startswith("17")]] if has_t else None
    special = pd.DataFrame([
        ("16b", "Chậm nhất", f"{ms(t['16b'] if has_t else None)}, chiếm "
         + (f"{t['16b'] / t.sum():.0%}" if has_t else "–") + " tổng thời gian 113 câu"),
        ("17a–17f", "Ít bảng mà chậm", f"7 bảng, chạy {ms(f17.min() if has_t else None)}–"
         f"{ms(f17.max() if has_t else None)}"),
        ("6c, 32a", "Nhanh nhất", f"{ms(t['6c'] if has_t else None)} và {ms(t['32a'] if has_t else None)} – "
         "LQO ra quyết định còn lâu hơn chạy câu"),
        ("26a", "Đổi cách chạy, chênh 35 lần", "mặc định 5,2 s; tắt index scan 0,75 s; tắt hash join 26,8 s"),
    ], columns=["câu", "đặc điểm", "ghi chú"])
    st.table(special.set_index("câu"))
    with st.expander("Xem toàn bộ 113 câu"):
        q = st.selectbox("Câu truy vấn", list(job["câu"]), index=list(job["câu"]).index("26a"))
        r = job.set_index("câu").loc[q]
        st.markdown(f"**{q}** · họ {r['họ']} · {r['số_bảng']} bảng · {r['số_điều_kiện']} điều kiện"
                    + (f" · PostgreSQL {ms(t[q])}" if has_t else ""))
        st.code(open(os.path.join(core.JOB_DIR, f"{q}.sql")).read(), language="sql")
        st.dataframe(job.style.format({"pg_ms": "{:,.0f}"}), hide_index=True, width="stretch", height=300)
