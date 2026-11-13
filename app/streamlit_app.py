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

st.set_page_config(page_title="Learned query optimizer – Nhóm 1", layout="wide")

st.sidebar.title("Learned query optimizer")
st.sidebar.caption("Bài báo: Lehmann, Sulimov, Stockinger. *Is Your Learned Query Optimizer Behaving As You Expect?* "
                   "PVLDB 17(7), 2024.")

tab0, tab1, tab_e1, tab_e2 = st.tabs(
    ["0. Dữ liệu IMDB & JOB", "1. Bài báo vs Nhóm", "2. Nhóm: Thí nghiệm 1", "3. Nhóm: Thí nghiệm 2"])

with tab1:
    group_results.render_paper_vs_group()
with tab_e1:
    group_results.render_exp1()
with tab_e2:
    group_results.render_exp2()

# ---------------------------------------------------------------- 0. CSDL IMDB
@st.cache_data(show_spinner=False)
def job_overview():
    return core.job_overview()


with tab0:
    st.header("Dữ liệu: CSDL IMDB và benchmark JOB")
    db = core.load_imdb()
    st.subheader("Cơ sở dữ liệu IMDB")
    st.markdown(
        "- **Nguồn:** snapshot dữ liệu phim IMDB (`imdb.tgz`), công bố cùng benchmark JOB (Leis et al., VLDB 2015).\n"
        "- **Lưu trữ:** nạp vào **PostgreSQL 12.5** thành các bảng quan hệ có index, database `imdbload`.\n"
        "- **Đặc điểm khiến IMDB khó cho optimizer:** dữ liệu thật, phân phối lệch và các cột tương quan với nhau "
        "→ ước lượng số dòng (cardinality) của PostgreSQL thường sai, dễ chọn sai thứ tự nối.")
    if db is None:
        st.warning("Chưa có analysis/output/app/imdb_db.json. Chạy `python app/prepare_data.py --db` "
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
        st.markdown(
            "21 bảng chia 4 nhóm: **bảng trung tâm** (`title` – phim, `name` – người), **bảng nối** (`cast_info`, "
            "`movie_companies`, `movie_keyword`, …), **bảng thông tin** (`movie_info`, `company_name`, `keyword`, …) "
            "và **bảng tra cứu** nhỏ (`info_type`, `kind_type`, `role_type`, …).")
        st.dataframe(tables.sort_values("số dòng", ascending=False).style.format({"số dòng": "{:,}"}),
                     hide_index=True, width="stretch", height=280)
        with st.expander("Sơ đồ quan hệ giữa các bảng"):
            st.markdown(" ".join(f'<span style="background:{c};color:white;border-radius:6px;padding:2px 10px;'
                                 f'margin-right:6px">{g}</span>'
                                 for g, c in zip(core.TABLE_GROUPS, core.PALETTE)), unsafe_allow_html=True)
            st.graphviz_chart(core.schema_dot(db, False), width="stretch")
            st.caption("Mỗi đường là một khóa ngoại; nhãn ghi cột khóa ngoại và số câu JOB (trên 113) dùng phép nối đó.")

    st.subheader("Benchmark JOB (Join Order Benchmark)")
    job = job_overview()
    fam = job.groupby("họ").size()
    has_t = "pg_ms" in job and job.pg_ms.notna().all()
    k = st.columns(4)
    k[0].metric("Số câu truy vấn", len(job))
    k[1].metric("Số họ (truy vấn gốc)", job["họ"].nunique(), "1a … 33c", delta_color="off", delta_arrow="off")
    k[2].metric("Số bảng nối mỗi câu", f"{job['số_bảng'].min()}–{job['số_bảng'].max()}",
                f"trung vị {job['số_bảng'].median():.0f}", delta_color="off", delta_arrow="off")
    if has_t:
        k[3].metric("Tổng thời gian PostgreSQL", f"{job.pg_ms.sum() / 1000:,.0f} s",
                    f"trung vị {job.pg_ms.median() / 1000:.2f} s/câu".replace(".", ","),
                    delta_color="off", delta_arrow="off")
    st.markdown(
        f"- **113 câu SELECT** do Leis et al. viết tay để kiểm tra khả năng chọn **thứ tự nối**: mỗi câu nối nhiều bảng "
        "với các điều kiện lọc (`LIKE`, `IN`, so sánh…) và trả về `MIN(...)`.\n"
        f"- Các câu chia thành **{job['họ'].nunique()} họ** đánh số 1–33; các câu cùng họ (a, b, c…) có cùng cấu trúc "
        "nối, chỉ khác điều kiện lọc. Số câu mỗi họ: "
        + ", ".join(f"{v} họ có {n} câu" for n, v in fam.value_counts().sort_index().items()) + ".\n"
        f"- **{int(job['dùng_GEQO'].sum())} câu nối từ {core.GEQO_THRESHOLD} bảng trở lên** (họ "
        + ", ".join(str(f) for f in sorted(job[job['dùng_GEQO']]['họ'].unique()))
        + f"): vượt `geqo_threshold = {core.GEQO_THRESHOLD}` nên PostgreSQL không duyệt hết mà dùng thuật toán di "
        "truyền GEQO để chọn thứ tự nối.\n"
        "- **Chia train/test (Mục 7.2 bài báo):** LOO lấy 1 câu mỗi họ làm test (33 câu), Random chọn ngẫu nhiên "
        "(22 câu), Base Query để nguyên cả họ ra test (19–26 câu) → mô hình phải xử lý cấu trúc nối chưa từng thấy, "
        "khó nhất.")

    if has_t:
        # Theme Streamlit bỏ qua .properties(height/title) → đặt tiêu đề trong alt.Chart và chiều cao ở st.altair_chart
        c1, c2 = st.columns(2)
        geqo_lbl, dp_lbl = f"≥ {core.GEQO_THRESHOLD} bảng: GEQO", f"< {core.GEQO_THRESHOLD} bảng: duyệt đầy đủ"
        nhom_scale = alt.Scale(domain=[dp_lbl, geqo_lbl], range=[core.PALETTE[0], core.PALETTE[1]])
        jv = job.assign(nhóm=np.where(job["dùng_GEQO"], geqo_lbl, dp_lbl))
        hist = jv.groupby(["số_bảng", "nhóm"]).size().reset_index(name="số_câu")
        c1.altair_chart(alt.Chart(hist, title="Số bảng nối mỗi câu").mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X("số_bảng:O", title="Số bảng nối trong câu", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("số_câu:Q", title="Số câu"),
            color=alt.Color("nhóm:N", scale=nhom_scale, title=None, legend=alt.Legend(orient="top")),
            tooltip=["số_bảng", "số_câu", "nhóm"]), width="stretch", height=320)
        c2.altair_chart(alt.Chart(jv, title="Thời gian PostgreSQL theo số bảng (Kaggle, cache nóng)").mark_circle(
            size=70, opacity=0.8).encode(
            x=alt.X("số_bảng:Q", title="Số bảng nối", scale=alt.Scale(domain=[3, 18])),
            y=alt.Y("pg_ms:Q", title="Thời gian (ms, thang log)", scale=alt.Scale(type="log", domain=[10, 30000]),
                    axis=alt.Axis(values=[10, 100, 1000, 10000])),
            color=alt.Color("nhóm:N", scale=nhom_scale, title=None, legend=alt.Legend(orient="top")),
            tooltip=["câu", "số_bảng", alt.Tooltip("pg_ms:Q", format=",.0f", title="ms")]),
            width="stretch", height=320)
        top10 = job.pg_ms.nlargest(10).sum() / job.pg_ms.sum()
        st.caption(f"Thời gian chạy trải từ {job.pg_ms.min():.0f} ms đến {job.pg_ms.max() / 1000:.0f} s và không tỉ lệ "
                   f"với số bảng. {int((job.pg_ms > 1000).sum())} câu chạy quá 1 s; 10 câu chậm nhất chiếm "
                   f"{top10:.0%} tổng thời gian → speedup tổng của một phương pháp bị vài câu này chi phối, nên "
                   "bài báo đánh giá thêm theo từng câu (thắng/hòa/thua, trung vị).")

    st.subheader("Những câu đặc biệt")
    t = job.set_index("câu").pg_ms if has_t else None

    def ms(v):
        if v is None or not has_t:
            return "–"
        return f"{v / 1000:.1f} s".replace(".", ",") if v >= 1000 else f"{v:.0f} ms"

    f17 = t[[q for q in t.index if q.startswith("17")]] if has_t else None
    special = pd.DataFrame([
        ("16b", "Chậm nhất JOB", f"{ms(t['16b'] if has_t else None)}, chiếm "
         + (f"{t['16b'] / t.sum():.0%}" if has_t else "–") + " tổng thời gian của cả 113 câu"),
        ("17a–17f", "Ít bảng nhưng chậm", f"chỉ 7 bảng nhưng chạy {ms(f17.min() if has_t else None)}–"
         f"{ms(f17.max() if has_t else None)}: số bảng ít chưa chắc nhanh"),
        ("6c, 32a", "Nhanh nhất", f"PostgreSQL chỉ {ms(t['6c'] if has_t else None)} và {ms(t['32a'] if has_t else None)}; "
         "Bao mất ~130 ms chỉ để lập plan cho 5 tập hint nên chậm hơn PostgreSQL khoảng 10× ở các câu này (Kaggle)"),
        ("29a–29c", "Nhiều bảng nhất (17)", "PostgreSQL dùng GEQO; tắt GEQO làm các câu này chậm 15–23× (Mac)"),
        ("24b", "Bài báo nêu tên (8.5)", "tắt GEQO chậm 9,9× trong bài báo, 3,9× trên Kaggle"),
        ("28a, 28b", "Cùng họ, ngược chiều (8.4)", "tắt bitmap/tid scan: 28a nhanh hơn 6× nhưng 28b chậm 7,5× (Kaggle)"),
        ("26a", "Câu dùng để demo", "PostgreSQL mặc định 5,2 s; tắt index scan còn 0,75 s; tắt hash join 26,8 s "
         "→ cùng một câu, chọn plan khác nhau chênh nhau 35×"),
        ("33c", "Bao chọn sai plan", "trên Kaggle (LOO-1) Bao làm câu này chậm từ 80 ms lên 1,17 s"),
    ], columns=["câu", "đặc điểm", "vì sao đáng chú ý"])
    st.table(special.set_index("câu"))     # st.table tự xuống dòng, không cắt chữ như st.dataframe
    with st.expander("Xem toàn bộ 113 câu"):
        q = st.selectbox("Câu truy vấn", list(job["câu"]), index=list(job["câu"]).index("26a"))
        r = job.set_index("câu").loc[q]
        st.markdown(f"**{q}** · họ {r['họ']} · {r['số_bảng']} bảng · {r['số_điều_kiện']} điều kiện"
                    + (f" · PostgreSQL {ms(t[q])}" if has_t else ""))
        st.code(open(os.path.join(core.JOB_DIR, f"{q}.sql")).read(), language="sql")
        st.dataframe(job.style.format({"pg_ms": "{:,.0f}"}), hide_index=True, width="stretch", height=300)
