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
def _src_short(src):
    if src.startswith("nhóm (Mac"):
        return "Nhóm (Mac)"
    if src.startswith("nhóm"):
        return "Nhóm (Kaggle)"
    return "Bài báo"


def render_exp1():
    st.header("Thí nghiệm 1 – Kiểm chứng kết luận của bài báo trên máy của nhóm")
    f_tot, f_split, f_83, f_why = (os.path.join(E1, f) for f in
                                   ("exp1_total_233.csv", "exp1_bao_hybridqo_per_split.csv",
                                    "exp1_ablation_8_3.csv", "exp1_nguyen_nhan.csv"))
    if _missing([f_tot, f_split], "python3 scripts/exp1_tables.py"):
        return
    st.markdown(
        "- **Chạy lại trên cùng môi trường Kaggle** (CPU, PostgreSQL 12.5, shared_buffers 8 GB, work_mem 512 MB, "
        "4 parallel workers): Bao (train 500 câu theo kịch bản tác giả) và HybridQO (11 epoch, so ở epoch 10). "
        "Bao cũng đã chạy trên MacBook M1 (Docker) – giữ lại để đối chiếu.\n"
        "- Neo, Balsa, LEON cần GPU và 20–130 giờ mỗi split → dùng log tác giả công bố.\n"
        "- **Cách đo theo khuyến nghị của bài báo:** đúng 9 split JOB (LOO / Random / Base Query × 3 = 233 lần kiểm tra), "
        "cache nóng, mỗi câu chạy 3 lần lấy lần thứ 3, thời gian end-to-end = suy luận + lập kế hoạch + thực thi; "
        "mỗi phương pháp so với PostgreSQL đo trong cùng notebook.\n"
        "- **Thắng / thua** khi nhanh / chậm hơn PostgreSQL quá 10% trên cùng câu.")
    with st.expander("Thiết kế thí nghiệm 1 (Bảng 5 – theo những gì nhóm đã chạy)"):
        st.table(pd.DataFrame([
            ("Câu hỏi nghiên cứu", "Kết luận của bài báo có còn đúng trên môi trường của nhóm không?"),
            ("Môi trường chính", "Kaggle (CPU, khoảng 30 GB RAM), PostgreSQL 12.5, shared_buffers 8 GB, work_mem 512 MB; "
                                 "bài báo: 32 GB / 4 GB"),
            ("Chạy lại", "PostgreSQL; Bao (9 split, Kaggle – kết quả chính; Mac – đối chiếu); "
                         "HybridQO (9 split, Kaggle, 11 epoch, so ở epoch 10)"),
            ("Dùng log tác giả", "Neo, Balsa, LEON (cần GPU, 20–130 giờ mỗi split)"),
            ("Ablation", "§8.3 dữ liệu thay đổi (IMDB-50%), §8.4 tắt bitmap/tid scan, §8.5 tắt GEQO, "
                         "§8.6 số lần chạy mỗi câu – đều trên Kaggle"),
            ("Kết quả trình bày", "Thắng/hòa/thua (±10%), speedup tổng và trung vị so với PostgreSQL theo từng split, "
                                  "cạnh số của bài báo"),
        ], columns=["mục", "mô tả"]).set_index("mục"))

    tot = pd.read_csv(f_tot)
    tot["nguồn_ngắn"] = tot.nguồn.map(_src_short)
    tot["dòng"] = tot.phương_pháp + " – " + tot.nguồn_ngắn
    g = tot.set_index(["phương_pháp", "nguồn_ngắn"])
    m = st.columns(4)
    for i, meth in enumerate(["Bao", "HybridQO"]):
        a, b = g.loc[(meth, "Nhóm (Kaggle)")], g.loc[(meth, "Bài báo")]
        m[2 * i].metric(f"{meth} – tỉ lệ thua (nhóm, Kaggle)", f"{a.tỉ_lệ_thua:.0%}",
                        f"bài báo {b.tỉ_lệ_thua:.0%}", delta_color="off", delta_arrow="off")
        m[2 * i + 1].metric(f"{meth} – speedup tổng (nhóm, Kaggle)", f"{a.speedup:.2f}×",
                            f"bài báo {b.speedup:.2f}×", delta_color="off", delta_arrow="off")

    st.subheader("Thắng / hòa / thua so với PostgreSQL trên 233 lần kiểm tra")
    order = ["Bao – Nhóm (Kaggle)", "Bao – Bài báo", "Bao – Nhóm (Mac)", "HybridQO – Nhóm (Kaggle)",
             "HybridQO – Bài báo", "Neo – Bài báo", "Balsa – Bài báo", "LEON – Bài báo"]
    w = tot.rename(columns={"thắng": "Thắng", "hòa": "Hòa", "thua": "Thua"})
    st.altair_chart(_wtl_bars(w, "dòng", None, order), width="stretch")
    bk, hk = g.loc[("Bao", "Nhóm (Kaggle)")], g.loc[("HybridQO", "Nhóm (Kaggle)")]
    bp, bm = g.loc[("Bao", "Bài báo")], g.loc[("Bao", "Nhóm (Mac)")]
    c1, c2 = st.columns(2)
    c1.success(f"**Khớp với bài báo:** trên cùng môi trường Kaggle, cả Bao ({bk.speedup:.2f}×) và HybridQO "
               f"({hk.speedup:.2f}×) đều chưa nhanh hơn PostgreSQL. HybridQO ổn định hơn Bao (thua {hk.tỉ_lệ_thua:.0%} "
               f"so với {bk.tỉ_lệ_thua:.0%} số câu). Bao trên Kaggle {int(bk.thắng)}/{int(bk.hòa)}/{int(bk.thua)} "
               f"sát với bài báo {int(bp.thắng)}/{int(bp.hòa)}/{int(bp.thua)}.")
    c2.info(f"**Khác bài báo:** HybridQO của nhóm thắng {int(hk.thắng)} câu (bài báo 34) vì chỉ train 10 epoch "
            "(tác giả 40–49, giới hạn 12 giờ/phiên Kaggle) nên gần như luôn giữ plan của PostgreSQL. "
            f"Bao trên Mac thắng {int(bm.thắng)} câu vì work_mem chỉ 256 MB làm PostgreSQL chậm bất thường ở các "
            "câu join lớn → dùng kết quả Kaggle làm kết quả chính.")

    st.subheader("Theo từng split: speedup trung vị theo câu (nhỏ hơn 1 = PostgreSQL nhanh hơn ở câu điển hình)")
    ps = pd.read_csv(f_split)
    rows = []
    for _, r in ps.iterrows():
        for meth, pre, suf, src in (("Bao", "Bao", "kaggle", "Nhóm (Kaggle)"), ("Bao", "Bao", "tác_giả", "Bài báo"),
                                    ("HybridQO", "HQO", "nhóm", "Nhóm (Kaggle)"),
                                    ("HybridQO", "HQO", "tác_giả", "Bài báo")):
            rows.append({"split": r.split.strip(), "phương_pháp": meth, "nguồn": src,
                         "trung_vị": r[f"{pre}_{suf}_trung_vị"], "speedup_tổng": r[f"{pre}_{suf}_speedup"],
                         "T/H/Th": r[f"{pre}_{suf}_T/H/Th"]})
    long = pd.DataFrame(rows)
    base = alt.Chart(long).encode(
        x=alt.X("split:N", sort=SPLITS, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("trung_vị:Q", title="Speedup trung vị", scale=alt.Scale(domain=[0, 1.2])),
        color=alt.Color("phương_pháp:N", scale=_scale(["Bao", "HybridQO"]), title=None),
        shape=alt.Shape("nguồn:N", scale=alt.Scale(domain=["Nhóm (Kaggle)", "Bài báo"], range=["circle", "triangle"]),
                        title=None),
        tooltip=["split", "phương_pháp", "nguồn", alt.Tooltip("trung_vị:Q", format=".2f"),
                 alt.Tooltip("speedup_tổng:Q", format=".2f"), "T/H/Th"])
    one = alt.Chart(pd.DataFrame({"y": [1]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((one + base.mark_point(size=110, filled=True, opacity=0.9)).properties(height=320),
                    width="stretch")
    st.caption("HybridQO nằm sát đường 1 ở mọi split (trung vị 0,85–0,94), Bao thấp hơn hẳn (0,51–0,68): "
               "HybridQO thắng Bao về trung vị ở cả 9/9 split, giống bài báo.")
    with st.expander("Bảng số liệu từng split (gồm Bao trên Mac)"):
        st.dataframe(ps.style.format({c: "{:.2f}" for c in ps.columns if "speedup" in c or "trung_vị" in c}),
                     hide_index=True, width="stretch")

    if os.path.exists(f_why):
        st.subheader("Vì sao cả hai chưa thắng PostgreSQL?")
        why = pd.read_csv(f_why)
        s = why.groupby("phương_pháp").agg(n=("số_câu", "sum"), doi=("câu_đổi_plan", "sum"),
                                           cp=("chi_phí_thêm_s", "sum"))
        k = st.columns(4)
        k[0].metric("Bao – câu chọn plan khác PostgreSQL", f"{int(s.loc['Bao', 'doi'])}/{int(s.loc['Bao', 'n'])}")
        k[1].metric("Bao – chi phí lập kế hoạch thêm", f"{s.loc['Bao', 'cp']:.1f} s")
        k[2].metric("HybridQO – câu chọn plan khác PostgreSQL",
                    f"{int(s.loc['HybridQO', 'doi'])}/{int(s.loc['HybridQO', 'n'])}")
        k[3].metric("HybridQO – thời gian suy luận", f"{s.loc['HybridQO', 'cp']:.1f} s")
        sp = why.melt(id_vars=["split", "phương_pháp"], value_vars=["speedup_chỉ_thực_thi", "speedup_end_to_end"],
                      var_name="cách_tính", value_name="speedup")
        sp["cách_tính"] = sp.cách_tính.map({"speedup_chỉ_thực_thi": "chỉ thực thi",
                                             "speedup_end_to_end": "end-to-end"})
        # data đặt ở lớp ngoài cùng (facet không cho lớp con có data riêng) → kiểu dữ liệu phải ghi rõ
        ch = alt.Chart().mark_bar().encode(
            x=alt.X("split:N", sort=SPLITS, title=None, axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("cách_tính:N", sort=["chỉ thực thi", "end-to-end"]),
            y=alt.Y("speedup:Q", title="Speedup tổng so với PostgreSQL"),
            color=alt.Color("cách_tính:N", scale=alt.Scale(domain=["chỉ thực thi", "end-to-end"],
                                                           range=[GREY, core.PALETTE[1]]), title=None,
                            legend=alt.Legend(orient="top")),
            tooltip=["split:N", "phương_pháp:N", "cách_tính:N", alt.Tooltip("speedup:Q", format=".2f")])
        rule = alt.Chart().mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y=alt.datum(1))
        st.altair_chart(alt.layer(ch, rule, data=sp).properties(height=220).facet(
            row=alt.Row("phương_pháp:N", title=None)), width="stretch")
        st.markdown(
            "- **Bao:** mỗi câu phải lập kế hoạch cho 5 tập hint rồi chạy model để chọn → thêm khoảng 100–190 ms mỗi câu, "
            "trong khi một nửa số câu JOB chạy dưới 0,5 s (với câu trung vị, phần cộng thêm này đã bằng 20–40% thời gian chạy). Model có đổi plan ở 66 câu nhưng chọn sai nhiều hơn chọn đúng, "
            "nên tính cả chi phí thì Bao thua 77% số câu.\n"
            "- **HybridQO:** sau 10 epoch gần như luôn giữ plan của PostgreSQL (225/233 câu) → phần thực thi bằng "
            "PostgreSQL (≈1,00×), chỉ thua phần thời gian suy luận. Không đổi plan thì không thể thắng; tác giả train "
            "40–49 epoch nên HybridQO mới dám đổi plan và thắng 34 câu.")

    st.subheader("Ablation")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**8.4 Tắt bitmap/tid scan và 8.5 tắt GEQO** (PostgreSQL, 113 câu JOB, chạy xen kẽ 3 cấu hình, "
                    "3 lần mỗi câu)")
        abl = []
        for env, pat in (("Kaggle", "ablation_{}_kaggle.csv"), ("Mac", "ablation_{}_interleaved_*.csv")):
            for name, label in (("no_geqo", "Tắt GEQO (8.5)"), ("no_bitmap_tidscan", "Tắt bitmap/tid scan (8.4)")):
                fs = sorted(glob.glob(os.path.join(core.OUT, pat.format(name))))
                if not fs:
                    continue
                d = pd.read_csv(fs[-1])
                sig = d[(d.p_welch < 0.05) & (d.delta_ms.abs() > 250)].sort_values("ti_le", ascending=False)
                abl.append({"môi trường": env, "cấu hình": label, "tổng (default → ablation)":
                            f"{d.default_ms.sum() / 1000:,.1f} s → {d.ablation_ms.sum() / 1000:,.1f} s",
                            "câu khác biệt có ý nghĩa": ", ".join(f"{q} ({t:.1f}×)" for q, t in zip(sig['query'], sig.ti_le)),
                            "tỉ lệ trung vị, câu ≥ 12 bảng": d[d.n_bang >= 12].ti_le.median()})
        if abl:
            st.dataframe(pd.DataFrame(abl).style.format({"tỉ lệ trung vị, câu ≥ 12 bảng": "{:.2f}×"}),
                         hide_index=True, width="stretch")
            st.caption("Tỉ lệ > 1 = chậm đi khi áp dụng ablation. Giống bài báo: tổng thời gian gần như không đổi "
                       "nhưng một số câu lẻ thay đổi mạnh theo cả hai hướng (vd. trên Kaggle tắt bitmap scan làm 28b "
                       "chậm 7,5× nhưng 28a nhanh 6×); tắt GEQO chỉ ảnh hưởng câu từ 12 bảng trở lên.")
        cmp_rows = []
        for name, label in (("no_bitmap_tidscan", "8.4 tắt bitmap/tid"), ("no_geqo", "8.5 tắt GEQO")):
            f = os.path.join(core.OUT, f"ablation_{name}_kaggle.csv")
            if not os.path.exists(f):
                continue
            d = pd.read_csv(f)
            for _, r in d[d.bai_bao.notna()].iterrows():
                paper_slow = str(r.bai_bao).startswith("chậm")
                ours = (f"chậm {r.ti_le:.1f}×" if r.ti_le > 1.1 else f"nhanh {1 / r.ti_le:.1f}×" if r.ti_le < 0.9
                        else f"không đổi ({r.ti_le:.2f}×)").replace(".", ",")
                same = (r.ti_le > 1.1 and paper_slow) or (r.ti_le < 0.9 and not paper_slow)
                cmp_rows.append({"ablation": label, "câu": r["query"], "bài báo": r.bai_bao, "nhóm (Kaggle)": ours,
                                 "cùng chiều": "✅" if same else "❌"})
        if cmp_rows:
            cmp = pd.DataFrame(cmp_rows)
            ok = cmp.groupby("ablation")["cùng chiều"].apply(lambda s: f"{(s == '✅').sum()}/{len(s)}")
            st.markdown("**Đối chiếu các câu bài báo nêu tên** – cùng chiều: "
                        + ", ".join(f"{k}: {v}" for k, v in ok.items()))
            st.table(cmp.set_index(["ablation", "câu"]))
            st.caption("Các câu lệch chiều (28a, 30a, 30c) đều nối ≥ 12 bảng: plan phụ thuộc cấu hình bộ nhớ (Kaggle "
                       "8 GB / 512 MB so với 32 GB / 4 GB của tác giả) và tính ngẫu nhiên của GEQO. Riêng 28a trên "
                       "Kaggle chạy chậm ở cấu hình mặc định (5,6 s) nên mọi ablation đều làm nó nhanh lên.")
    with a2:
        st.markdown("**8.3 Dữ liệu thay đổi (covariate shift):** Bao-Full (train trên IMDB đầy đủ) và Bao-50 (train "
                    "trên IMDB-50%, giữ 50% bảng `title` bằng lấy mẫu Bernoulli) cùng chạy tập test BQ-1 trên IMDB-50% "
                    "(Kaggle)")
        f83k = os.path.join(E1, "exp1_ablation_8_3_kaggle.csv")
        if os.path.exists(f83k):
            d = pd.read_csv(f83k)
            d["tổng"] = d.apply(lambda r: f"{r.tổng_A_s:.1f} s so với {r.tổng_B_s:.1f} s", axis=1)
            d["kết quả theo câu"] = d.apply(
                lambda r: f"chậm hơn {r.chậm_hơn} câu, nhanh hơn {r.nhanh_hơn} câu (trên {r.số_câu})", axis=1)
            st.dataframe(d[["so_sánh", "nguồn", "kết quả theo câu", "tổng"]], hide_index=True, width="stretch")
            st.caption("Ngưỡng ±10%. Log tác giả: 4 model mỗi loại (lấy trung vị), cùng hướng thử "
                       "(`test__bao__imdb*_trained__imdb2_tested`), lọc đúng 19 câu test BQ-1. Kết quả của nhóm sát "
                       "tác giả: model train trên dữ liệu khác (Bao-Full) chậm hơn model train đúng dữ liệu (Bao-50) "
                       "khoảng 10–14% tổng thời gian; riêng 7c Bao-Full chậm 1,9× (tác giả 1,6×). Cả hai đều vẫn "
                       "thua PostgreSQL ở đa số câu.")
        if os.path.exists(f_83):
            with st.expander("Bản chạy trước trên Mac (LOO-1, RND-1, chỉ Bao-Full)"):
                d = pd.read_csv(f_83)
                d["split"] = d.split.str.extract(r"job__(\w+?)_split_(\d)").apply(
                    lambda r: {"leave_one_out": "LOO", "random": "RND"}.get(r[0], r[0]) + "-" + r[1], axis=1)
                st.dataframe(d[["split", "T/H/Th", "speedup", "trung_vị"]].style.format(
                    {"speedup": "{:.2f}×", "trung_vị": "{:.2f}"}), hide_index=True, width="stretch")

    d86 = os.path.join(core.ROOT, "bao_kaggle_log", "ablation_8_6", "ablation86_logs")
    if os.path.exists(os.path.join(d86, "tom_tat_8_6.csv")):
        st.markdown("**8.6 Cần chạy mỗi câu bao nhiêu lần?** (Kaggle, PostgreSQL, 113 câu JOB × 50 lần liên tiếp "
                    "bằng `EXPLAIN ANALYZE`, đúng cách của tác giả; log `pg__imdb__50.txt`)")
        b1, b2 = st.columns([3, 2])
        t86 = pd.read_csv(os.path.join(d86, "tom_tat_8_6.csv"))
        b1.dataframe(t86.style.format({c: "{:.2f}" for c in t86.columns[1:]}), hide_index=True, width="stretch")
        first = t86.iloc[0]
        b1.markdown(
            f"- Lần 1 → lần 2: thời gian giảm trung bình **{-first['trung bình (%)']:.1f}%** (bài báo: 14,6%) – lần "
            "chạy đầu bị cache lạnh, là ngoại lai.\n"
            f"- Từ lần 2 trở đi: chênh lệch chỉ quanh 0% (trung bình {t86.iloc[1]['trung bình (%)']:.2f}%, "
            "bài báo 1,03%), không còn xu hướng.\n"
            "- **Kết luận giống bài báo:** chạy mỗi câu 3 lần và lấy lần thứ 3 là đủ bền vững – đúng cách nhóm đã đo "
            "ở mọi thí nghiệm.")
        png = os.path.join(d86, "hinh7_8_6.png")
        if os.path.exists(png):
            b2.image(png, caption="Hình 7 tái lập: chênh lệch thời gian chuẩn hóa giữa lần k và k+1")

    st.subheader("Hạn chế của Thí nghiệm 1")
    st.markdown(
        "- **Bộ nhớ thấp hơn bài báo** (Kaggle 8 GB / 512 MB so với 32 GB / 4 GB) → so sánh xu hướng và thứ hạng, "
        "không so số giây tuyệt đối.\n"
        "- **HybridQO chỉ train 10 epoch** (tác giả 50, lấy kết quả ở epoch 40–49) do giới hạn 12 giờ mỗi phiên Kaggle; "
        "mô hình gần như giữ plan của PostgreSQL (đổi plan 8/233 câu) nên không có câu thắng.\n"
        "- **Mỗi split chỉ train 1 lần** (tác giả lặp lại nhiều lần, vd. HybridQO 3 lần, Bao ở 8.3 có 4 model): "
        "kết quả từng split có thể dao động.\n"
        "- **8.3 mới chạy một hướng** (test trên IMDB-50%, 19 câu BQ-1); bài báo phân tích thêm hướng test trên IMDB "
        "đầy đủ với 113 câu.")


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
    st.info(
        "**Mục đích:** Thí nghiệm 1 cho thấy các LQO phức tạp (Bao, HybridQO) chưa thắng được PostgreSQL vì tốn chi phí "
        "lập kế hoạch/suy luận và hay chọn sai plan. Thí nghiệm 2 kiểm tra hướng phát triển của nhóm: thay vì học cả "
        "plan, dùng **một mô hình phân loại gọn nhẹ** (Decision Tree, Random Forest, LightGBM) chỉ chọn **có nên tắt "
        "một toán tử của PostgreSQL hay không** – ít chi phí, dễ giải thích bằng luật – và xem nó có giúp PostgreSQL "
        "nhanh hơn, có tốt hơn Bao hay không.")
    with st.expander("Thiết kế thí nghiệm 2 (Bảng 6 – theo những gì nhóm đã chạy)"):
        st.table(pd.DataFrame([
            ("Câu hỏi nghiên cứu", "Mô hình phân loại đơn giản có giúp PostgreSQL nhanh hơn không?"),
            ("Dữ liệu", "113 câu JOB × 6 phương án × 3 lần chạy (MacBook M1, PostgreSQL 12.5)"),
            ("Nhãn", "Phương án nhanh nhất; giữ default nếu không nhanh hơn ít nhất 5%"),
            ("Đặc trưng", "Câu SQL và plan mặc định từ EXPLAIN (có trước khi chạy, không dùng q-error)"),
            ("Mô hình", "Decision Tree, Random Forest, LightGBM (siêu tham số cố định)"),
            ("Mốc so sánh", "PostgreSQL mặc định; Bao (cùng máy Mac, cùng câu test); Oracle (biết trước phương án "
                            "nhanh nhất – giới hạn trên)"),
            ("Cách chia dữ liệu", "Đúng 9 split của bài báo: Leave One Out, Random, Base Query [§7.2]"),
            ("Kết quả trình bày", "Tổng thời gian; số câu nhanh lên / chậm đi; luật chọn phương án"),
            ("Giả thuyết", "H1: mô hình nhanh hơn PostgreSQL và không thua Bao. "
                           "H2: mô hình kém nhất với loại câu chưa từng học (Base Query)"),
        ], columns=["mục", "mô tả"]).set_index("mục"))
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
                delta_color="off", delta_arrow="off")
    best = agg.loc[MODELS].speedup.idxmax()
    m[1].metric(f"Mô hình tốt nhất ({best})", f"{agg.loc[best, 'speedup']:.2f}×",
                f"{agg.loc[best, 'speedup'] - 1:+.0%} so với PostgreSQL")
    m[2].metric("Tỉ lệ thua: mô hình", f"{agg.loc[MODELS, 'tỉ_lệ_thua'].min():.0%}–{agg.loc[MODELS, 'tỉ_lệ_thua'].max():.0%}",
                f"Bao {agg.loc['Bao', 'tỉ_lệ_thua']:.0%}", delta_color="off", delta_arrow="off")
    m[3].metric("Accuracy", f"{acc.min():.0%}–{acc.max():.0%}", "3 mô hình", delta_color="off", delta_arrow="off")

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


# ================================================================ Bài báo vs nhóm
PAPER_METHODS = ["HybridQO", "Bao", "Neo", "Balsa", "LEON"]
SRC_COLOR = {"Bài báo": GREY, "Nhóm (Kaggle)": core.PALETTE[0]}


def render_paper_vs_group():
    st.header("Kết quả bài báo và kết quả nhóm")
    by_m, summ = core.paper_results()
    f_tot, f_split = os.path.join(E1, "exp1_total_233.csv"), os.path.join(E1, "exp1_bao_hybridqo_per_split.csv")
    if by_m is None or _missing([f_tot, f_split], "python3 scripts/exp1_tables.py"):
        return
    st.markdown(
        "Bài báo (Lehmann và cộng sự, PVLDB 2024) so 5 learned query optimizer (LQO) với PostgreSQL trên "
        "**113 câu JOB, 9 split** (Leave One Out / Random / Base Query × 3 = **233 lần kiểm tra**). "
        "Nhóm chạy lại **Bao** và **HybridQO** trên Kaggle với cùng cách đo; Neo, Balsa, LEON cần GPU nên chỉ có số "
        "của bài báo. *Speedup = thời gian PostgreSQL / thời gian LQO: lớn hơn 1 là LQO nhanh hơn.*")

    tot = pd.read_csv(f_tot)
    tot = tot[~tot.nguồn.str.contains("Mac")].copy()
    tot["nguồn_ngắn"] = tot.nguồn.map(_src_short)
    g = tot.set_index(["phương_pháp", "nguồn_ngắn"])

    m = st.columns(4)
    for i, meth in enumerate(["Bao", "HybridQO"]):
        a, b = g.loc[(meth, "Nhóm (Kaggle)")], g.loc[(meth, "Bài báo")]
        m[2 * i].metric(f"{meth} – speedup (nhóm)", f"{a.speedup:.2f}×", f"bài báo {b.speedup:.2f}×",
                        delta_color="off", delta_arrow="off")
        m[2 * i + 1].metric(f"{meth} – tỉ lệ câu thua (nhóm)", f"{a.tỉ_lệ_thua:.0%}", f"bài báo {b.tỉ_lệ_thua:.0%}",
                            delta_color="off", delta_arrow="off")

    left, right = st.columns(2)
    with left:
        sp = tot[["phương_pháp", "nguồn_ngắn", "speedup"]].copy()
        sp["nhãn"] = sp.speedup.map(lambda v: f"{v:.2f}×" if v >= 0.01 else f"{v:.3f}×")
        y = alt.Y("phương_pháp:N", sort=PAPER_METHODS, title=None)
        yo = alt.YOffset("nguồn_ngắn:N", sort=list(SRC_COLOR))
        bars = alt.Chart(sp).mark_bar(cornerRadiusEnd=3).encode(
            y=y, yOffset=yo,
            x=alt.X("speedup:Q", title="Speedup tổng (thang log)",
                    scale=alt.Scale(type="log", domain=[0.0005, 2]),
                    axis=alt.Axis(values=[0.001, 0.01, 0.1, 1], format="~g")),
            color=alt.Color("nguồn_ngắn:N", title=None, legend=alt.Legend(orient="top"),
                            scale=alt.Scale(domain=list(SRC_COLOR), range=list(SRC_COLOR.values()))),
            tooltip=["phương_pháp", alt.Tooltip("nguồn_ngắn:N", title="nguồn"),
                     alt.Tooltip("speedup:Q", format=".3f")])
        text = alt.Chart(sp).mark_text(align="left", dx=4, fontSize=11, color=MUTED).encode(
            y=y, yOffset=yo, x="speedup:Q", text="nhãn:N")
        one = alt.Chart().mark_rule(color=MUTED, strokeDash=[4, 4]).encode(x=alt.datum(1))
        st.altair_chart(alt.layer(bars, text, one, title="Tổng thời gian 233 lần kiểm tra"), height=320,
                        width="stretch")
    with right:
        w = tot.rename(columns={"thắng": "Thắng", "hòa": "Hòa", "thua": "Thua"})
        w["dòng"] = w.phương_pháp + " – " + w.nguồn_ngắn
        order = [f"{p} – {s}" for p in PAPER_METHODS for s in ("Bài báo", "Nhóm (Kaggle)")]
        order = [o for o in order if o in set(w.dòng)]
        ch = _wtl_bars(w, "dòng", None, order)
        st.altair_chart(ch.properties(title="Số câu thắng / hòa / thua (±10%)"), width="stretch")

    # ---- heatmap theo split: 5 phương pháp của bài báo + 2 phương pháp nhóm chạy lại
    st.subheader("Speedup theo từng split")
    s = summ.copy()
    s["kiểu"] = s.split.str.replace(r"_split_\d", "", regex=True).map(
        {"leave_one_out": "LOO", "random": "RND", "base_query": "BQ"})
    s["split"] = s["kiểu"] + "-" + s.split.str[-1]
    s["dòng"] = s.phương_pháp_gốc + " – Bài báo"
    s = s[["dòng", "split", "speedup_workload", "thắng", "hòa", "thua"]]
    ps = pd.read_csv(f_split)
    ps["split"] = ps.split.str.strip()
    for meth, col in (("Bao", "Bao_kaggle"), ("HybridQO", "HQO_nhóm")):
        t = ps[f"{col}_T/H/Th"].str.split("/", expand=True).astype(int)
        s = pd.concat([s, pd.DataFrame({"dòng": f"{meth} – Nhóm", "split": ps.split,
                                        "speedup_workload": ps[f"{col}_speedup"],
                                        "thắng": t[0], "hòa": t[1], "thua": t[2]})])
    rows = ["HybridQO – Bài báo", "HybridQO – Nhóm", "Bao – Bài báo", "Bao – Nhóm",
            "Neo – Bài báo", "Balsa – Bài báo", "LEON – Bài báo"]
    s["log_speedup"] = np.log10(s.speedup_workload).clip(-1, 1)
    s["nhãn"] = s.speedup_workload.map(lambda v: f"{v:.2f}×" if v >= 0.01 else f"{v:.0e}×")
    enc = dict(x=alt.X("split:N", sort=SPLITS, title=None, axis=alt.Axis(labelAngle=0, orient="top")),
               y=alt.Y("dòng:N", sort=rows, title=None))
    heat = alt.Chart(s).mark_rect(stroke="white", strokeWidth=2, cornerRadius=3).encode(
        **enc, color=alt.Color("log_speedup:Q", title="Speedup",
                               scale=alt.Scale(domain=[-1, 0, 1], range=["#eb6834", "#f0efec", "#2a78d6"]),
                               legend=alt.Legend(values=[-1, 0, 1], labelExpr=
                                                 "datum.value == -1 ? '≤0,1× (chậm hơn PG)' : "
                                                 "datum.value == 0 ? '1× (ngang PG)' : '≥10× (nhanh hơn PG)'")),
        tooltip=[alt.Tooltip("dòng:N", title="Phương pháp"), "split:N",
                 alt.Tooltip("speedup_workload:Q", title="Speedup", format=".3f"), "thắng:Q", "hòa:Q", "thua:Q"])
    text = alt.Chart(s).mark_text(fontSize=12).encode(
        **enc, text="nhãn:N",
        color=alt.condition("abs(datum.log_speedup) > 0.6", alt.value("white"), alt.value("#0b0b0b")))
    st.altair_chart(heat + text, height=330, width="stretch")
    st.caption("Màu xanh = nhanh hơn PostgreSQL, cam = chậm hơn. Hai dòng “Nhóm” nằm ngay dưới dòng bài báo "
               "tương ứng để so trực tiếp. Riêng Bao nhóm ở RND-3 (1,61×) nhờ một câu được chọn plan rất tốt.")

    st.subheader("Kết luận của bài báo có đúng với nhóm không?")
    bk, bp = g.loc[("Bao", "Nhóm (Kaggle)")], g.loc[("Bao", "Bài báo")]
    hk, hp = g.loc[("HybridQO", "Nhóm (Kaggle)")], g.loc[("HybridQO", "Bài báo")]
    st.table(pd.DataFrame([
        ("Không LQO nào nhanh hơn PostgreSQL một cách ổn định",
         f"HybridQO {hp.speedup:.2f}×, Bao {bp.speedup:.2f}×, còn lại < 0,3×",
         f"HybridQO {hk.speedup:.2f}×, Bao {bk.speedup:.2f}×", "✅ Khớp"),
        ("HybridQO ổn định hơn Bao (thua ít câu hơn)",
         f"thua {hp.tỉ_lệ_thua:.0%} so với {bp.tỉ_lệ_thua:.0%}",
         f"thua {hk.tỉ_lệ_thua:.0%} so với {bk.tỉ_lệ_thua:.0%}", "✅ Khớp"),
        ("HybridQO vẫn thắng được một số câu",
         f"thắng {int(hp.thắng)} câu", f"thắng {int(hk.thắng)} câu",
         "❌ Khác – nhóm chỉ train 10 epoch (tác giả 40–49) nên HybridQO gần như luôn giữ plan PostgreSQL"),
        ("Neo, Balsa, LEON chậm hơn nhiều do thời gian suy luận",
         "0,001–0,28×", "không chạy lại (cần GPU, 20–130 giờ/split)", "– Chưa kiểm chứng"),
    ], columns=["Kết luận", "Bài báo", "Nhóm (Kaggle)", "Đánh giá"]).set_index("Kết luận"))
    st.caption("Chi tiết cách đo, nguyên nhân và ablation ở tab “Nhóm: Thí nghiệm 1”.")
