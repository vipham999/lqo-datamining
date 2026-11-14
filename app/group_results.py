"""Hai tab kết quả của nhóm (Mục 4 báo cáo): Thí nghiệm 1 – kiểm chứng bài báo, Thí nghiệm 2 – mô hình phân loại.

Chỉ đọc các file kết quả đã tính sẵn, không chạy lại thí nghiệm:
  analysis/output/exp1/            ← scripts/exp1/exp1_tables.py
  analysis/output/ablation_*       ← scripts/ablation/ablation_analyze.py
  analysis/output/exp2/            ← scripts/exp2/exp2_analyze.py
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
        y=alt.Y(f"{y}:N", sort=order, title=y_title, axis=alt.Axis(labelLimit=220)),
        x=alt.X("tỉ_lệ:Q", stack="normalize", title="Tỉ lệ số lần kiểm tra", axis=alt.Axis(format="%")),
        color=alt.Color("kết quả:N", scale=alt.Scale(domain=list(OUTCOME_COLOR), range=list(OUTCOME_COLOR.values())),
                        sort=list(OUTCOME_COLOR), title=None, legend=alt.Legend(orient="top")),
        order=alt.Order("thứ_tự:Q"),
        tooltip=[y, "kết quả", "số_câu", alt.Tooltip("tỉ_lệ:Q", format=".0%")])
    return bars.properties(height=alt.Step(34))



# ================================================================ khung kể chuyện (data storytelling)
def _story_intro(context, question, approach):
    """Bối cảnh → Câu hỏi → Cách làm, ba ô cạnh nhau."""
    cols = st.columns([1, 1, 1.2])
    for c, (title, body) in zip(cols, [("1 · Bối cảnh", context), ("2 · Câu hỏi", question),
                                       ("3 · Cách làm", approach)]):
        with c.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(body)


def _finding(no, title, chart, obs, why, means, chart_ratio=(3, 2)):
    """Một phát hiện: biểu đồ bên trái, 3 tầng Quan sát → Vì sao → Ý nghĩa bên phải."""
    with st.container(border=True):
        st.markdown(f"#### Phát hiện {no}: {title}")
        left, right = st.columns(chart_ratio)
        with left:
            chart()
        with right:
            st.markdown(f"**Thấy gì:** {obs}")
            st.markdown(f"**Vì sao:** {why}")
            st.markdown(f"**Rút ra:** {means}")


def _story_legend():
    st.caption("Mỗi phát hiện đọc theo 3 tầng: **Quan sát** (số liệu) → **Vì sao** (giải thích) → **Ý nghĩa** "
               "(điều rút ra). Số liệu đầy đủ ở phần “Xem chi tiết” cuối trang.")


def _vn(v, nd=2):
    return f"{v:.{nd}f}".replace(".", ",")


def _speedup_bars(df, y, color_field, color_scale):
    """Thanh ngang speedup với đường 1× = bằng PostgreSQL."""
    df = df.assign(nhãn=df.speedup.map(lambda v: "< 0,01×" if v < 0.01 else _vn(v) + "×"))
    yy = alt.Y(f"{y}:N", sort=list(dict.fromkeys(df[y])), title=None, axis=alt.Axis(labelLimit=240))
    xmax = max(1.2, float(df.speedup.max()) * 1.18)
    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=3).encode(
        y=yy, x=alt.X("speedup:Q", title="Tốc độ so với PostgreSQL (1 = bằng nhau, > 1 = nhanh hơn)",
                      scale=alt.Scale(domain=[0, xmax])),
        color=alt.Color(f"{color_field}:N", scale=color_scale, title=None, legend=alt.Legend(orient="top")),
        tooltip=[y, color_field, alt.Tooltip("speedup:Q", format=".2f")])
    txt = alt.Chart(df).mark_text(align="left", dx=4, color=MUTED).encode(y=yy, x="speedup:Q", text="nhãn:N")
    one = alt.Chart(pd.DataFrame({"x": [1]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(x="x:Q")
    return (bars + txt + one).properties(height=alt.Step(30))


# ================================================================ Thí nghiệm 1
def _src_short(src):
    if src.startswith("nhóm (Mac"):
        return "Nhóm (Mac)"
    if src.startswith("nhóm"):
        return "Nhóm (Kaggle)"
    return "Bài báo"


def _repeat_limit():
    """Dòng hạn chế về số lần train, tự đổi theo số lần lặp đã có trong exp1_lan_lap_theo_split.csv."""
    f = os.path.join(E1, "exp1_lan_lap_theo_split.csv")
    n = {}
    if os.path.exists(f):
        d = pd.read_csv(f)
        n = d.groupby("phương_pháp")["số_lần"].min().to_dict()
    b, h = int(n.get("Bao", 1)), int(n.get("HybridQO", 1))
    if b >= 3 and h >= 3:
        return ("- **Bao và HybridQO đã train 3 lần mỗi split** như tác giả; kết quả từng split dao động giữa các lần "
                "kết luận dựa trên trung vị.")
    return (f"- **Số lần train mỗi split:** Bao {b} lần, HybridQO {h} lần (tác giả: 3 lần) do giới hạn thời gian "
            "(mỗi lần train lại cả 9 split mất khoảng 30 giờ trên Kaggle); kết quả từng split có thể dao động giữa các "
            "lần train. Phần ablation đã lặp lại đủ như tác giả.")


def render_exp1():
    st.header("Thí nghiệm 1 – Bài báo nói đúng không?")
    f_tot, f_split, f_83, f_why = (os.path.join(E1, f) for f in
                                   ("exp1_total_233.csv", "exp1_bao_hybridqo_per_split.csv",
                                    "exp1_ablation_8_3.csv", "exp1_nguyen_nhan.csv"))
    if _missing([f_tot, f_split], "python3 scripts/exp1/exp1_tables.py"):
        return
    tot = pd.read_csv(f_tot)
    tot["nguồn_ngắn"] = tot.nguồn.map(_src_short)
    _exp1_story(tot, f_why)

    st.divider()
    if not st.toggle("Hiện số liệu chi tiết (cho người muốn kiểm tra)", key="exp1_detail"):
        return
    t_split, t_why, t_abl, t_design = st.tabs(
        ["Theo từng cách chia dữ liệu", "Chi phí và kế hoạch", "Tắt từng thành phần (ablation)",
         "Thiết kế & hạn chế"])
    with t_split:
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
        st.dataframe(ps.style.format({c: "{:.2f}" for c in ps.columns if "speedup" in c or "trung_vị" in c}),
                     hide_index=True, width="stretch")
    with t_why:
        if os.path.exists(f_why):
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
    with t_abl:
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
    with t_design:
        st.table(pd.DataFrame([
            ("Câu hỏi nghiên cứu", "Kết luận của bài báo có còn đúng trên môi trường của nhóm không?"),
            ("Môi trường chính", "Kaggle (CPU, khoảng 30 GB RAM), PostgreSQL 12.5, shared_buffers 8 GB, work_mem 512 MB; "
                                 "bài báo: 32 GB / 4 GB"),
            ("Chạy lại", "PostgreSQL; Bao (9 split, Kaggle – kết quả chính; Mac – đối chiếu); "
                         "HybridQO (9 split, Kaggle, 11 epoch, so ở epoch 10)"),
            ("Dùng log tác giả", "Neo, Balsa, LEON (cần GPU, 20–130 giờ mỗi split)"),
            ("Ablation", "§8.3 dữ liệu thay đổi (IMDB-50%, 4 bản × 4 hướng train/test, 113 câu), §8.4 tắt bitmap/tid "
                         "scan và §8.5 tắt GEQO (8 lượt xen kẽ) – đều trên Kaggle"),
            ("Kết quả trình bày", "Thắng/hòa/thua (±10%), speedup tổng và trung vị so với PostgreSQL theo từng split, "
                                  "cạnh số của bài báo"),
        ], columns=["mục", "mô tả"]).set_index("mục"))
        st.markdown("**Hạn chế**")
        st.markdown(
            "- **Bộ nhớ thấp hơn bài báo** (Kaggle 8 GB / 512 MB so với 32 GB / 4 GB) → so sánh xu hướng và thứ hạng, "
            "không so số giây tuyệt đối.\n"
            "- **HybridQO chỉ train 10 epoch** (tác giả 50, lấy kết quả ở epoch 40–49) do giới hạn 12 giờ mỗi phiên Kaggle; "
            "mô hình gần như giữ plan của PostgreSQL (đổi plan 8/233 câu) nên không có câu thắng.\n"
            f"{_repeat_limit()}\n"
            "- **8.3 chỉ chạy trên split BQ-1** như tác giả, 4 bản mỗi model; các câu bài báo nêu tên không lặp lại, "
            "hiệu ứng có nhưng nhỏ hơn bài báo.")


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
    st.header("Thí nghiệm 2 – Một mô hình nhỏ có giúp PostgreSQL chạy nhanh hơn?")
    need = [os.path.join(E2, f) for f in ("exp2_summary_per_split.csv", "exp2_per_query.csv", "exp2_labels.csv",
                                          "exp2_feature_importance_rf.csv", "exp2_rules_decision_tree.txt")]
    if _missing(need, "~/.venvs/lqo-exp2/bin/python scripts/exp2/exp2_analyze.py"):
        return
    split, pq, lab, imp, rules = _load_exp2()
    agg = split.groupby("phương_pháp")[["số_câu", "thắng", "hòa", "thua", "PG_s", "phương_pháp_s"]].sum()
    agg["speedup"] = agg.PG_s / agg.phương_pháp_s
    agg["tỉ_lệ_thua"] = agg.thua / agg.số_câu
    _exp2_story(agg, pq, lab)

    st.divider()
    if not st.toggle("Hiện số liệu chi tiết (cho người muốn kiểm tra)", key="exp2_detail"):
        return
    t_hyp, t_model, t_one, t_design = st.tabs(
        ["Kiểm định giả thuyết", "Mô hình học được gì", "Xem một câu", "Thiết kế"])
    with t_hyp:
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
    with t_model:
        f_all = os.path.join(E2, "exp2_feature_importance_all.csv")
        if os.path.exists(f_all):
            ia = pd.read_csv(f_all).set_index("đặc_trưng")[MODELS]
            top = ia.mean(axis=1).sort_values(ascending=False).head(10).index
            long = ia.loc[top].reset_index().melt(id_vars="đặc_trưng", var_name="mô_hình", value_name="importance")
            st.markdown("**10 đặc trưng quan trọng nhất – cả 3 mô hình** (train trên cả 113 câu; mỗi mô hình chuẩn "
                        "hóa về tổng = 1; xếp theo trung bình 3 mô hình)")
            st.altair_chart(alt.Chart(long).mark_bar(cornerRadiusEnd=3).encode(
                y=alt.Y("đặc_trưng:N", sort=list(top), title=None, axis=alt.Axis(labelLimit=220)),
                yOffset=alt.YOffset("mô_hình:N", sort=MODELS),
                x=alt.X("importance:Q", title="Mức quan trọng (tỉ lệ)", axis=alt.Axis(format="%")),
                color=alt.Color("mô_hình:N", scale=_scale(MODELS), sort=MODELS, title=None,
                                legend=alt.Legend(orient="top")),
                tooltip=["đặc_trưng", "mô_hình", alt.Tooltip("importance:Q", format=".1%")]
            ).properties(height=alt.Step(11)), width="stretch")
            used = (ia > 0).sum()
            common = [c for c in top if (ia.loc[c] > 0).all()]
            st.markdown(
                f"- **Cả 3 mô hình cùng dựa vào** {', '.join(f'`{c}`' for c in common[:5])}: độ phức tạp của plan "
                "(số node, cost) và của câu SQL (độ dài, số điều kiện lọc) → câu càng phức tạp, plan mặc định càng "
                "dễ chưa tốt.\n"
                f"- **Decision Tree** chỉ dùng {used['DecisionTree']}/{len(ia)} đặc trưng (một cây, độ sâu 4) nên dồn "
                f"độ quan trọng vào vài đặc trưng; **Random Forest** ({used['RandomForest']} đặc trưng) và "
                f"**LightGBM** ({used['LightGBM']} đặc trưng) rải đều hơn.\n"
                "- Đặc trưng gần trùng thông tin (vd `plan_startup_cost` và `plan_total_cost`) thì mô hình chỉ cần "
                "chọn một → cùng đặc trưng có thể quan trọng với mô hình này nhưng bằng 0 với mô hình khác.\n"
                "- Cách đo: Decision Tree, Random Forest = mức giảm impurity; LightGBM = tổng gain. Đây là "
                "“mô hình dựa vào gì”, chưa phải quy luật chắc chắn (accuracy chỉ khoảng 52–55%).")
        else:
            st.info("Chưa có exp2_feature_importance_all.csv – chạy lại scripts/exp2/exp2_analyze.py.")
        st.markdown("**Luật chọn phương án của Decision Tree** (độ sâu 4, train trên cả 113 câu)")
        st.code(rules.split("\n\n", 1)[-1], language="text")
        dist = lab.nhãn.value_counts()
        st.caption("Phân bố nhãn (113 câu): " + ", ".join(f"{k} {v}" for k, v in dist.items()) + ".")
    with t_one:
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
    with t_design:
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

# ================================================================ khai phá trên dữ liệu đã chạy
FULL_SPLITS = [f"{k}_split_{i}" for k in ("leave_one_out", "random", "base_query") for i in (1, 2, 3)]
TIME_BINS = ["< 0,1 s", "0,1–0,5 s", "0,5–2 s", "> 2 s"]


def _bao_log(path):
    """Log run_test_queries.py của Bao: lấy lần chạy thứ 3 của mỗi câu."""
    rows = []
    for line in open(path):
        x = [s.strip() for s in line.rsplit(",", 6)]
        if len(x) == 7:
            rows.append({"hint": x[0], "run": int(x[1]), "q": os.path.basename(x[3])[:-4],
                         "plan": float(x[4]), "exe": float(x[5])})
    d = pd.DataFrame(rows)
    return d[d.run == 2].set_index("q")


@st.cache_data(show_spinner=False)
def _bao_per_query():
    """233 lần kiểm tra của Bao trên Kaggle, ghép với đặc điểm của câu."""
    rows = []
    for s in FULL_SPLITS:
        b = os.path.join(core.ROOT, "bao_kaggle_log", s, "bao_logs")
        f_pg, f_b = (os.path.join(b, f"test__{m}__job__{s}.txt") for m in ("postgres", "bao"))
        if os.path.exists(f_pg) and os.path.exists(f_b):
            d = _bao_log(f_pg).join(_bao_log(f_b), lsuffix="_pg", rsuffix="_b").reset_index()
            rows.append(d.assign(split=s))
    if not rows:
        return None
    d = pd.concat(rows, ignore_index=True)
    d["pg"], d["bao"] = d.plan_pg + d.exe_pg, d.plan_b + d.exe_b
    sp = d.pg / d.bao
    d["kết quả"] = np.select([sp > 1.1, sp < 0.9], ["Thắng", "Thua"], "Hòa")
    d["đổi_plan"] = ~d.hint_b.isin(["", "x", "(no hint)"])
    d["thời_gian_PG"] = pd.cut(d.pg, [0, 100, 500, 2000, np.inf], labels=TIME_BINS)
    job = core.job_overview()[["câu", "số_bảng"]]
    return d.merge(job, left_on="q", right_on="câu", how="left")


def _exp1_mining():
    d = _bao_per_query()
    if d is None:
        st.info("Chưa có log Bao trên Kaggle trong bao_kaggle_log/.")
        return
    st.markdown("Ghép 233 lần kiểm tra của Bao (Kaggle) với đặc điểm của từng câu: thời gian chạy trên PostgreSQL, "
                "số bảng nối, Bao có đổi plan hay không.")
    g = d.groupby("thời_gian_PG", observed=True).agg(pg=("pg", "sum"), bao=("bao", "sum"))
    lab = {k: f"{k}  ({g.loc[k, 'pg'] / g.loc[k, 'bao']:.2f}×)" for k in g.index}
    cnt = d.groupby(["thời_gian_PG", "kết quả"], observed=True).size().reset_index(name="số_câu")
    cnt["nhóm"] = cnt.thời_gian_PG.map(lab)
    cnt["thứ_tự"] = cnt["kết quả"].map({"Thắng": 0, "Hòa": 1, "Thua": 2})
    left, right = st.columns([3, 2])
    with left:
        ch = alt.Chart(cnt, title="Bao thắng / hòa / thua theo thời gian chạy của câu trên PostgreSQL").mark_bar().encode(
            y=alt.Y("nhóm:N", sort=[lab[k] for k in TIME_BINS if k in lab], title=None,
                    axis=alt.Axis(labelLimit=220)),
            x=alt.X("số_câu:Q", stack="zero", title="Số lần kiểm tra (trong ngoặc: speedup tổng của nhóm câu)"),
            color=alt.Color("kết quả:N", title=None, legend=alt.Legend(orient="top"), sort=list(OUTCOME_COLOR),
                            scale=alt.Scale(domain=list(OUTCOME_COLOR), range=list(OUTCOME_COLOR.values()))),
            order=alt.Order("thứ_tự:Q"), tooltip=["nhóm", "kết quả", "số_câu"]).properties(height=alt.Step(40))
        st.altair_chart(ch, width="stretch")
    short, long_ = d[d.pg < 500], d[d.pg >= 2000]
    chg = d[d.đổi_plan]
    ex = chg.exe_pg / chg.exe_b
    many = d.số_bảng >= core.GEQO_THRESHOLD
    sp_many, sp_few = d[many].pg.sum() / d[many].bao.sum(), d[~many].pg.sum() / d[~many].bao.sum()
    with right:
        st.metric("Chi phí Bao cộng thêm mỗi câu (trung vị)", f"{(d.plan_b - d.plan_pg).median():.0f} ms")
        st.metric("Câu chạy dưới 0,5 s: Bao thua", f"{(short['kết quả'] == 'Thua').sum()}/{len(short)}")
        st.metric("Câu chạy trên 2 s: speedup của Bao", f"{long_.pg.sum() / long_.bao.sum():.2f}×")
    st.markdown(
        f"**Phát hiện:**\n"
        f"1. **Câu càng ngắn, Bao càng thua.** Bao luôn cộng thêm khoảng {(d.plan_b - d.plan_pg).median():.0f} ms "
        f"(lập plan cho 5 tập hint + chạy model). Với câu dưới 0,5 s, khoản này lớn hơn mọi lợi ích nên Bao thua "
        f"{(short['kết quả'] == 'Thua').sum()}/{len(short)} lần. Với câu trên 2 s, Bao lại nhanh hơn PostgreSQL "
        f"({long_.pg.sum() / long_.bao.sum():.2f}×).\n"
        f"2. **Khi đổi plan, Bao chọn sai nhiều hơn đúng.** Bao đổi plan {len(chg)}/{len(d)} lần: phần thực thi "
        f"nhanh hơn ở {(ex > 1.1).sum()} lần nhưng chậm hơn ở {(ex < 0.9).sum()} lần.\n"
        f"3. **Câu nối từ {core.GEQO_THRESHOLD} bảng trở lên là nơi Bao có ích.** PostgreSQL dùng GEQO (heuristic) "
        f"nên plan mặc định dễ chưa tốt: Bao đổi plan {d[many].đổi_plan.mean():.0%} số lần (câu ít bảng "
        f"{d[~many].đổi_plan.mean():.0%}) và nhanh hơn PostgreSQL {sp_many:.2f}× (câu ít bảng {sp_few:.2f}×).\n\n"
        "**Gợi ý:** chỉ dùng LQO cho câu nối nhiều bảng hoặc có cost ước lượng lớn (biết được từ `EXPLAIN` trước "
        "khi chạy), còn câu ngắn để PostgreSQL tự chọn → tránh chi phí cộng thêm.")


def _exp2_mining(lab):
    hints = core.HINT_SETS[1:]
    rows = []
    for h in hints:
        r = lab.t_default_ms / lab[f"t_{h}_ms"]
        rows += [{"phương_án": h, "kết quả": "Nhanh hơn > 10%", "số_câu": int((r > 1.1).sum())},
                 {"phương_án": h, "kết quả": "Chậm hơn > 10%", "số_câu": -int((r < 0.9).sum())}]
    risk = pd.DataFrame(rows)
    tot = {h: lab[f"t_{h}_ms"].sum() / lab.t_default_ms.sum() for h in hints}
    risk["nhãn"] = risk.phương_án.map(lambda h: f"{h}  (tổng {tot[h]:.2f}× default)")
    gain = (lab.t_default_ms - lab.best_ms).clip(lower=0)
    top = lab.assign(gain_s=gain / 1000).sort_values("gain_s", ascending=False)
    share10 = top.gain_s.head(10).sum() / top.gain_s.sum()
    fam = lab.groupby("template").nhãn.agg(lambda x: x.value_counts().iloc[0] / len(x))
    left, right = st.columns(2)
    with left:
        ch = alt.Chart(risk, title="Tắt một toán tử: số câu có lợi và bị hại (113 câu)").mark_bar().encode(
            y=alt.Y("nhãn:N", title=None, axis=alt.Axis(labelLimit=260),
                    sort=[f"{h}  (tổng {tot[h]:.2f}× default)" for h in sorted(hints, key=tot.get)]),
            x=alt.X("số_câu:Q", title="← bị chậm đi      số câu      nhanh lên →"),
            color=alt.Color("kết quả:N", title=None, legend=alt.Legend(orient="top"),
                            scale=alt.Scale(domain=["Nhanh hơn > 10%", "Chậm hơn > 10%"],
                                            range=[OUTCOME_COLOR["Thắng"], OUTCOME_COLOR["Thua"]])),
            tooltip=["phương_án", "kết quả", alt.Tooltip("số_câu:Q", title="số câu (âm = chậm đi)")]
        ).properties(height=alt.Step(36))
        st.altair_chart(ch, width="stretch")
    with right:
        t10 = top.head(10)
        ch = alt.Chart(t10, title=f"10 câu chiếm {share10:.0%} thời gian Oracle tiết kiệm được").mark_bar(
            color=core.PALETTE[2], cornerRadiusEnd=3).encode(
            y=alt.Y("query_id:N", sort=list(t10.query_id), title=None),
            x=alt.X("gain_s:Q", title="Giây tiết kiệm nếu chọn đúng phương án"),
            tooltip=["query_id", "nhãn", alt.Tooltip("gain_s:Q", format=".1f")]).properties(height=alt.Step(22))
        st.altair_chart(ch, width="stretch")
    nl = lab.t_default_ms / lab.t_no_nestloop_ms
    safest = min(hints, key=tot.get)
    st.markdown(
        "**Phát hiện:**\n"
        f"1. **Rủi ro không đối xứng.** Tắt nested loop chỉ có lợi ở {(nl > 1.1).sum()} câu nhưng làm chậm "
        f"{(nl < 0.9).sum()} câu, tổng thời gian gấp {tot['no_nestloop']:.1f}× → chọn sai một lần có thể mất nhiều "
        f"hơn cả chục lần chọn đúng. `{safest}` an toàn nhất (tổng {tot[safest]:.2f}×).\n"
        f"2. **Lợi ích tập trung ở vài câu chạy lâu.** 10 câu ({', '.join(t10.query_id.head(5))}…) chiếm "
        f"{share10:.0%} tổng thời gian có thể tiết kiệm ({top.gain_s.sum():.0f} s) → chọn đúng vài câu lớn quan "
        "trọng hơn accuracy trên toàn bộ.\n"
        f"3. **Câu cùng họ chưa chắc cùng phương án tốt nhất.** Trung bình chỉ {fam.mean():.0%} số câu trong một họ "
        f"có cùng nhãn; chỉ {(fam == 1).sum()}/{len(fam)} họ nhất quán hoàn toàn → giải thích vì sao split Base Query "
        "(test trên họ chưa thấy) khó nhất.\n\n"
        "**Gợi ý:** mô hình nên có “quyền từ chối” – chỉ đổi phương án khi rất chắc và với câu có cost lớn, "
        "tránh các phương án rủi ro cao như `no_nestloop`.")


# ================================================================ Khai phá dữ liệu
MINING_FILES = ["exp2_mining_summary.json", "exp2_mining_rules.csv", "exp2_mining_hashjoin_risk.csv",
                "exp2_labels.csv"]


def render_mining():
    st.header("Khai phá dữ liệu – Vì sao mô hình thua, và sửa thế nào?")
    if _missing([os.path.join(E2, f) for f in MINING_FILES], "python3 scripts/exp2/exp2_mining.py"):
        return
    f_ab = os.path.join(E2, "exp2_abstain.csv")
    if _missing([f_ab], "~/.venvs/lqo_app/bin/python scripts/exp2/exp2_abstain.py"):
        return
    import json
    with open(os.path.join(E2, "exp2_mining_summary.json")) as fi:
        s = json.load(fi)
    ru = pd.read_csv(os.path.join(E2, "exp2_mining_rules.csv"))
    risk = pd.read_csv(os.path.join(E2, "exp2_mining_hashjoin_risk.csv"))
    ab = pd.read_csv(f_ab)
    sw = pd.read_csv(os.path.join(E2, "exp2_abstain_switches.csv"))
    TH = 0.6

    st.info("**Vấn đề:** ở Thí nghiệm 2, mô hình đoán đúng khoảng một nửa nhưng tổng thời gian vẫn **chậm hơn** "
            "PostgreSQL.  \n**Khai phá dữ liệu để làm gì:** đọc lại dữ liệu đã đo (113 câu × 6 cách chạy) để tìm "
            "**quy luật** giải thích vì sao – rồi dùng quy luật đó **sửa mô hình** và đo lại.")
    steps = st.columns(3)
    for c, (t, b_) in zip(steps, [
            ("① Tìm luật", "Máy tự thử hàng trăm luật dạng “NẾU câu có đặc điểm A THÌ tắt X có lợi”, chỉ giữ luật "
                           "đúng thật (kỹ thuật **luật kết hợp**)."),
            ("② Rút ra nguyên nhân", "Xem luật tốt nhất khi đem áp dụng thì được gì, mất gì."),
            ("③ Sửa và đo lại", "Sửa mô hình theo bài học vừa rút ra, đo lại đúng như Thí nghiệm 2.")]):
        with c.container(border=True):
            st.markdown(f"**{t}**  \n{b_}")

    # ---- ① + ②
    top = ru[ru.kết_quả.str.contains("giúp")].sort_values("p").iloc[0]
    base = ru[(ru.điều_kiện == "có ≥2 hash join") & (ru.kết_quả == "tắt hashjoin giúp")].iloc[0]
    up, down = risk[risk.chênh_s > 0], risk[risk.chênh_s < 0]
    d2 = pd.DataFrame([(f"{len(up)} câu nhanh hơn", up.chênh_s.sum(), "Nhanh hơn"),
                       (f"{len(down)} câu chậm hơn", down.chênh_s.sum(), "Chậm hơn")],
                      columns=["nhóm", "giây", "kết quả"])
    d2["nhãn"] = d2.giây.map(lambda v: f"{v:+.0f} giây")

    def c1():
        st.markdown(f"Áp luật **“NẾU kế hoạch có ≥ 2 hash join THÌ tắt hash join”** cho cả {len(risk)} câu khớp:")
        y = alt.Y("nhóm:N", title=None, sort=None)
        bars = alt.Chart(d2).mark_bar(cornerRadiusEnd=3).encode(
            y=y, x=alt.X("giây:Q", title="← mất thêm (giây)        tiết kiệm được (giây) →"),
            color=alt.Color("kết quả:N", legend=None, scale=alt.Scale(
                domain=["Nhanh hơn", "Chậm hơn"], range=[OUTCOME_COLOR["Thắng"], OUTCOME_COLOR["Thua"]])),
            tooltip=["nhóm", alt.Tooltip("giây:Q", format="+.1f")])
        txt = alt.Chart(d2).mark_text(align="left", dx=6, color=MUTED).encode(y=y, x=alt.datum(0), text="nhãn:N")
        st.altair_chart((bars + txt).properties(height=alt.Step(44)), width="stretch")
    _finding(1, "Luật “thường đúng” vẫn làm lỗ – vì sai một lần rất đắt", c1,
             f"Máy thử **{s['số_luật_đã_thử']} luật**, giữ lại **{s['số_luật_giữ_lại']}** luật đáng tin. Luật nổi bật "
             f"nhất đúng {int(base.số_câu_đúng)}/{int(base.số_câu_khớp)} câu – gấp **{_vn(base.lift, 1)} lần** đoán bừa. "
             f"Nhưng áp vào thì {len(up)} câu nhanh hơn chỉ được tổng **{up.chênh_s.sum():.0f} giây**, còn {len(down)} "
             f"câu chậm hơn mất **{-down.chênh_s.sum():.0f} giây**.",
             "Đúng thì chỉ lợi chút ít, sai thì có câu chậm gấp nhiều lần (26a: 5,7 → 32 giây). Mô hình ở Thí nghiệm 2 "
             "cũng vậy: nó đổi cách chạy cả khi **không chắc**, và vài lần sai đắt xóa hết phần lợi.",
             "Bài học: **chỉ đổi khi thật chắc chắn, còn không thì giữ nguyên PostgreSQL**.")

    # ---- ③
    rf = ab[ab.mô_hình == "RandomForest"].set_index("ngưỡng")
    cmp_ = []
    for m in MODELS:
        d = ab[ab.mô_hình == m].set_index("ngưỡng")
        cmp_ += [{"mô_hình": m, "cách": "Trước: luôn làm theo mô hình", "speedup": d.loc[0.0, "speedup"]},
                 {"mô_hình": m, "cách": f"Sau: chỉ đổi khi tin ≥ {TH:.0%}", "speedup": d.loc[TH, "speedup"]}]
    cmp_ = pd.DataFrame(cmp_)
    cmp_["nhãn"] = cmp_.speedup.map(lambda v: _vn(v) + "×")
    dom = ["Trước: luôn làm theo mô hình", f"Sau: chỉ đổi khi tin ≥ {TH:.0%}"]

    def c2():
        yy = alt.Y("mô_hình:N", sort=MODELS, title=None)
        bars = alt.Chart(cmp_).mark_bar(cornerRadiusEnd=3).encode(
            y=yy, yOffset=alt.YOffset("cách:N", sort=dom),
            x=alt.X("speedup:Q", title="Tốc độ so với PostgreSQL (1 = bằng nhau, > 1 = nhanh hơn)",
                    scale=alt.Scale(domain=[0, 1.2])),
            color=alt.Color("cách:N", title=None, sort=dom, legend=alt.Legend(orient="top", direction="vertical", labelLimit=400),
                            scale=alt.Scale(domain=dom, range=["#c8c6c0", "#0a9396"])),
            tooltip=["mô_hình", "cách", alt.Tooltip("speedup:Q", format=".2f")])
        txt = alt.Chart(cmp_).mark_text(align="left", dx=4, color=MUTED).encode(
            y=yy, yOffset=alt.YOffset("cách:N", sort=dom), x="speedup:Q", text="nhãn:N")
        one = alt.Chart(pd.DataFrame({"x": [1]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(x="x:Q")
        st.altair_chart((bars + txt + one).properties(height=alt.Step(24)), width="stretch")
    s_rf = sw[sw.mô_hình == "RandomForest"]
    fams = sorted(s_rf.query_id.unique())
    gain = (s_rf.PG_ms / s_rf.phương_án_ms)
    stable = [th for th in rf.index if th > 0 and rf.loc[th, "speedup"] >= 1.05]
    _finding(2, "Sửa theo bài học: “không chắc thì giữ nguyên” – mô hình chuyển từ chậm hơn sang nhanh hơn", c2,
             f"Random Forest từ **{_vn(rf.loc[0.0, 'speedup'])}** lên **{_vn(rf.loc[TH, 'speedup'])} lần** – nhanh hơn "
             f"PostgreSQL. Kết quả giữ nguyên khi đổi ngưỡng từ {min(stable):.0%} đến {max(stable):.0%}. Decision Tree "
             "và LightGBM cũng tốt lên nhưng chưa vượt 1.",
             f"Mô hình bỏ được các lần đổi “nửa tin nửa ngờ” – đúng những lần sai đắt. Random Forest chỉ còn đổi "
             f"**{int(rf.loc[TH, 'số_lần_đổi'])}/{int(rf.loc[TH, 'số_lần_kiểm_tra'])}** lần, đều là tắt nested loop ở "
             f"các câu họ 17 ({', '.join(fams)}) và lần nào cũng nhanh hơn ({_vn(gain.min(), 1)}–{_vn(gain.max(), 1)} lần).",
             "Khai phá dữ liệu đã **chỉ đúng nguyên nhân**, và một sửa đổi rất đơn giản đã giúp mô hình thắng "
             "PostgreSQL. Phần lợi còn nhỏ vì mô hình hiếm khi đủ chắc – muốn lợi nhiều hơn cần mô hình tự tin đúng "
             "ở nhiều câu hơn.")

    st.success(f"**Kết luận:** Khai phá dữ liệu cho thấy mô hình thua vì **đổi cách chạy cả khi không chắc**, và một lần "
               f"sai có thể mất bằng nhiều lần đúng. Sửa bằng luật “chỉ đổi khi tin ≥ {TH:.0%}” thì Random Forest đạt "
               f"**{_vn(rf.loc[TH, 'speedup'])} lần** PostgreSQL (trước đó {_vn(rf.loc[0.0, 'speedup'])}).")
    st.caption("Lưu ý: kết quả “chậm hơn” vẫn còn ở khoảng 65 lần kiểm tra – đó là các câu rất ngắn (vài chục ms), chỉ "
               "riêng thời gian EXPLAIN (~5 ms) đã vượt ngưỡng 10%. Tự giữ nguyên PostgreSQL ở mọi câu cũng bị y như vậy.")

    st.divider()
    if not st.toggle("Hiện chi tiết kỹ thuật (thiết lập, bảng luật, các ngưỡng)", key="mine_detail"):
        return
    _mining_method(s)
    st.divider()
    st.markdown("### Luật kết hợp")
    _mining_rules()
    st.divider()
    st.markdown("### Thử nhiều ngưỡng độ tin")
    t = ab.assign(ngưỡng=ab.ngưỡng.map(lambda v: "không lọc" if v == 0 else f"≥ {v:.0%}"))
    st.dataframe(t.pivot(index="ngưỡng", columns="mô_hình", values="speedup")[MODELS].style.format("{:.2f}×"),
                 width="stretch")
    st.caption("Cùng mô hình, cùng 9 cách chia train/test như Thí nghiệm 2; thời gian = EXPLAIN + phương án được chọn. "
               "`python scripts/exp2/exp2_abstain.py`. Ngưỡng 60% được chọn sau khi thử nhiều ngưỡng; với Random Forest các "
               "ngưỡng 50–70% cho cùng kết quả nên không phải nhờ chọn may một ngưỡng.")
    st.divider()
    st.markdown("### Tắt từng cách nối / đọc bảng: số câu có lợi và bị hại")
    _exp2_mining(pd.read_csv(os.path.join(E2, "exp2_labels.csv")))


def _mining_rules():
    ru = pd.read_csv(os.path.join(E2, "exp2_mining_rules.csv"))
    st.markdown("Một luật có dạng **NẾU plan có đặc điểm A THÌ tắt toán tử X có lợi / có hại**. "
                "Đọc luật bằng 3 con số:\n"
                "- **Confidence:** trong các câu khớp điều kiện, bao nhiêu % đúng kết quả.\n"
                "- **Lift:** confidence gấp mấy lần tỉ lệ chung (lift 3 = khả năng cao gấp 3 so với chọn bừa).\n"
                "- **Số họ:** luật đúng trên bao nhiêu họ câu khác nhau (càng nhiều càng không phải học thuộc).")
    top = ru.sort_values("p").groupby("kết_quả").head(2).sort_values(["kết_quả", "lift"], ascending=[True, False])
    show = top.assign(
        luật=top.điều_kiện + "  →  " + top.kết_quả,
        khớp=top.số_câu_khớp.astype(str) + " câu, đúng " + top.số_câu_đúng.astype(str))[
        ["luật", "khớp", "confidence", "lift", "số_họ", "ví_dụ"]].rename(
        columns={"luật": "luật (NẾU → THÌ)", "khớp": "số câu", "số_họ": "số họ", "ví_dụ": "ví dụ câu đúng luật"})
    st.dataframe(show.style.format({"confidence": "{:.0%}", "lift": "{:.1f}"}), hide_index=True, width="stretch")
    st.caption(f"Hiển thị 2 luật mạnh nhất cho mỗi kết quả; đủ {len(ru)} luật trong "
               "`analysis/output/exp2/exp2_mining_rules.csv`.")

    risk = pd.read_csv(os.path.join(E2, "exp2_mining_hashjoin_risk.csv"))
    risk["kết quả"] = np.where(risk.chênh_s >= 0, "Nhanh hơn", "Chậm hơn")
    st.subheader("Ví dụ: áp luật “có ≥2 hash join → tắt hash join” cho cả 28 câu")
    ch = alt.Chart(risk).mark_bar(cornerRadiusEnd=2).encode(
        y=alt.Y("query_id:N", sort=list(risk.query_id), title=None, axis=alt.Axis(labelOverlap=False)),
        x=alt.X("chênh_s:Q", title="← chậm đi (giây)        nhanh lên (giây) →"),
        color=alt.Color("kết quả:N", title=None, legend=alt.Legend(orient="top"),
                        scale=alt.Scale(domain=["Nhanh hơn", "Chậm hơn"],
                                        range=[OUTCOME_COLOR["Thắng"], OUTCOME_COLOR["Thua"]])),
        tooltip=["query_id", alt.Tooltip("PG_ms:Q", title="PostgreSQL (ms)", format=",.0f"),
                 alt.Tooltip("no_hashjoin_ms:Q", title="tắt hash join (ms)", format=",.0f"),
                 alt.Tooltip("chênh_s:Q", title="chênh (s)", format="+.1f")]).properties(height=alt.Step(20))
    st.altair_chart(ch, width="stretch")
    win, lose = risk[risk.chênh_s > 0].chênh_s.sum(), -risk[risk.chênh_s < 0].chênh_s.sum()
    st.markdown(f"Luật **đúng ở nhiều câu** (thanh xanh) nhưng mỗi câu chỉ lợi một ít – tổng **{win:.0f} s**. "
                f"Vài câu sai (thanh đỏ) mất tới **{lose:.0f} s**. → Đúng nhiều lần chưa chắc có lợi; "
                "**một lần sai trên câu chạy lâu đủ xoá hết phần lợi**.")


def _mining_method(s):
    st.markdown(
        "**Input:** 2 file log Thí nghiệm 2 – `logs/exp2_hintsets_job.jsonl` (thời gian thật 113 câu × 6 phương án × "
        "3 lần) và `logs/exp2_explain_job.jsonl` (plan mặc định → 34 đặc trưng).  \n"
        "**Output:** bảng luật – các file `analysis/output/exp2/exp2_mining_*`.  \n"
        "**Môi trường:** Mac M1 Pro, Python (pandas, scikit-learn, scipy), chạy vài giây, không cần PostgreSQL.  \n"
        "**Lệnh:** `python3 scripts/exp2/exp2_mining.py`")
    st.table(pd.DataFrame([
        ("“Tắt X giúp”", "nhanh hơn ≥5% ở **cả** lần chạy 2 và 3", "giống luật gán nhãn; đòi 2 lần để tránh nhiễu đo"),
        ("“Tắt X hại”", "chậm hơn ≥2 lần ở cả lần chạy 2 và 3", "chỉ quan tâm trường hợp hại nặng"),
        ("Điều kiện", f"{s['số_điều_kiện']} điều kiện có/không (vd. “có ≥2 hash join”, “số bảng ≥12”)",
         "đặc trưng số chia theo ngưỡng có nghĩa hoặc tam phân vị"),
        ("Độ dài luật", "1–2 điều kiện", "chỉ 113 câu, luật dài dễ khớp ngẫu nhiên"),
        ("Giữ luật khi", "≥6 câu khớp, ≥4 câu đúng, ≥3 họ câu, lift > 1,5, p (Fisher, hiệu chỉnh BH) < 0,05",
         "tránh luật dựa trên 1–2 câu hoặc học thuộc một họ"),
    ], columns=["thiết lập", "giá trị", "lý do"]).set_index("thiết lập"))
    st.warning(
        "**Hạn chế:** chỉ 113 câu trên một máy, nhãn có nhiễu → luật là **phát hiện cần kiểm chứng**, chưa phải "
        f"quy luật chắc chắn.  \n**Phát hiện phụ:** {len(s['đặc_trưng_hằng_số'])} đặc trưng luôn cùng một giá trị "
        f"({', '.join(s['đặc_trưng_hằng_số'])}) nên vô dụng. `plan_est_rows` lấy số dòng ở node gốc (luôn là "
        "Aggregate = 1 dòng); nên đổi thành số dòng ước lượng của phép nối trên cùng.")


# ================================================================ Bài báo vs nhóm
PAPER_METHODS = ["HybridQO", "Bao", "Neo", "Balsa", "LEON"]
SRC_COLOR = {"Bài báo": GREY, "Nhóm (Kaggle)": core.PALETTE[0]}


def render_paper_vs_group():
    st.header("Kết quả bài báo và kết quả nhóm")
    by_m, summ = core.paper_results()
    f_tot, f_split = os.path.join(E1, "exp1_total_233.csv"), os.path.join(E1, "exp1_bao_hybridqo_per_split.csv")
    if by_m is None or _missing([f_tot, f_split], "python3 scripts/exp1/exp1_tables.py"):
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
        sp["gốc"] = 0.0005                      # thang log không có 0 → cột bắt đầu từ mép trái trục
        y = alt.Y("phương_pháp:N", sort=PAPER_METHODS, title=None)
        yo = alt.YOffset("nguồn_ngắn:N", sort=list(SRC_COLOR))
        bars = alt.Chart(sp).mark_bar(cornerRadiusEnd=3).encode(
            y=y, yOffset=yo, x2="gốc:Q",
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
        w["dòng"] = w.phương_pháp + " – " + w.nguồn_ngắn.str.replace(" (Kaggle)", "", regex=False)
        order = [f"{p} – {s}" for p in PAPER_METHODS for s in ("Bài báo", "Nhóm")]
        order = [o for o in order if o in set(w.dòng)]
        long = w[["dòng", "Thắng", "Hòa", "Thua"]].melt(id_vars="dòng", var_name="kết quả", value_name="số_câu")
        long["thứ_tự"] = long["kết quả"].map({"Thắng": 0, "Hòa": 1, "Thua": 2})
        ch = alt.Chart(long, title="Số câu thắng / hòa / thua so với PostgreSQL (±10%)").mark_bar().encode(
            y=alt.Y("dòng:N", sort=order, title=None, scale=alt.Scale(paddingInner=0.25),
                    axis=alt.Axis(labelLimit=200)),
            x=alt.X("số_câu:Q", stack="zero", title="Số lần kiểm tra (tổng 233)", scale=alt.Scale(domain=[0, 233])),
            color=alt.Color("kết quả:N", title=None, legend=alt.Legend(orient="top"), sort=list(OUTCOME_COLOR),
                            scale=alt.Scale(domain=list(OUTCOME_COLOR), range=list(OUTCOME_COLOR.values()))),
            order=alt.Order("thứ_tự:Q"),
            tooltip=["dòng", "kết quả", "số_câu"]).properties(height=alt.Step(30))
        st.altair_chart(ch, width="stretch")

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
               "tương ứng để so trực tiếp. Bao chỉ vượt PostgreSQL ở một split (bài báo: RND-1, nhóm: RND-3).")

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


# ================================================================ câu chuyện Thí nghiệm 1
CMP_SCALE = alt.Scale(domain=["Nhóm", "Bài báo"], range=["#0a9396", "#c8c6c0"])


def _exp1_story(tot, f_why):
    g = tot[tot.nguồn_ngắn != "Nhóm (Mac)"].set_index(["phương_pháp", "nguồn_ngắn"])
    bk, bp = g.loc[("Bao", "Nhóm (Kaggle)")].speedup, g.loc[("Bao", "Bài báo")].speedup
    hk, hp = g.loc[("HybridQO", "Nhóm (Kaggle)")].speedup, g.loc[("HybridQO", "Bài báo")].speedup
    d = _bao_per_query()

    st.info("**Bài báo nói:** các mô hình AI tự chọn cách chạy câu truy vấn (gọi là *LQO*, ví dụ Bao, HybridQO) "
            "**chưa nhanh hơn PostgreSQL**.  \n**Nhóm làm:** chạy lại Bao và HybridQO trên 113 câu truy vấn của "
            "benchmark JOB, rồi **tắt từng thành phần** để xem cái gì thật sự ảnh hưởng tới tốc độ.")

    # ---- 1. kết quả chính
    def c1():
        rows = tot[tot.phương_pháp.isin(["Bao", "HybridQO"]) & (tot.nguồn_ngắn != "Nhóm (Mac)")].copy()
        rows["nguồn_ngắn"] = rows.nguồn_ngắn.replace({"Nhóm (Kaggle)": "Nhóm"})
        rows["dòng"] = rows.phương_pháp + " · " + rows.nguồn_ngắn
        rows = rows.sort_values(["phương_pháp", "nguồn_ngắn"], ascending=[True, False])
        st.altair_chart(_speedup_bars(rows, "dòng", "nguồn_ngắn", CMP_SCALE), width="stretch")
    _finding(1, "Bài báo nói đúng – AI chưa nhanh hơn PostgreSQL", c1,
             f"Bao chỉ bằng **{_vn(bk)}** lần tốc độ PostgreSQL, HybridQO **{_vn(hk)}** lần (bài báo: {_vn(bp)} và "
             f"{_vn(hp)}). Dưới 1 nghĩa là chậm hơn.",
             "Trước khi chạy, AI phải “suy nghĩ” thêm cho mỗi câu, mà cái lợi chưa bù được – xem phát hiện 2.",
             "Kết luận của bài báo lặp lại được trên máy khác.")

    # ---- 2. vì sao
    if d is not None:
        g2 = d.groupby("thời_gian_PG", observed=True).agg(pg=("pg", "sum"), bao=("bao", "sum"))
        lab2 = {k: f"Câu chạy {k}" for k in g2.index}
        cnt = d.groupby(["thời_gian_PG", "kết quả"], observed=True).size().reset_index(name="số_câu")
        cnt["nhóm"] = cnt.thời_gian_PG.map(lab2)
        cnt["thứ_tự"] = cnt["kết quả"].map({"Thắng": 0, "Hòa": 1, "Thua": 2})
        cnt["kết quả"] = cnt["kết quả"].map({"Thắng": "Bao nhanh hơn", "Hòa": "Ngang nhau", "Thua": "Bao chậm hơn"})
        dom = ["Bao nhanh hơn", "Ngang nhau", "Bao chậm hơn"]

        def c2():
            st.altair_chart(alt.Chart(cnt).mark_bar().encode(
                y=alt.Y("nhóm:N", sort=[lab2[k] for k in TIME_BINS if k in lab2], title=None),
                x=alt.X("số_câu:Q", title="Số lần chạy thử"),
                color=alt.Color("kết quả:N", title=None, legend=alt.Legend(orient="top"), sort=dom,
                                scale=alt.Scale(domain=dom, range=list(OUTCOME_COLOR.values()))),
                order=alt.Order("thứ_tự:Q"), tooltip=["nhóm", "kết quả", "số_câu"]).properties(height=alt.Step(36)),
                width="stretch")
        short, long_ = d[d.pg < 500], d[d.pg >= 2000]
        over = (d.plan_b - d.plan_pg).median()
        chg = d[d.đổi_plan]
        ex = chg.exe_pg / chg.exe_b
        _finding(2, "Vì sao AI thua: tốn “phí” cho mỗi câu, và đổi cách chạy thì hay đổi sai", c2,
                 f"Với câu chạy dưới 0,5 giây, Bao chậm hơn **{(short['kết quả'] == 'Thua').sum()}/{len(short)}** lần. "
                 f"Với câu chạy trên 2 giây, Bao lại nhanh hơn ({_vn(long_.pg.sum() / long_.bao.sum())} lần).",
                 f"Trước khi chạy, Bao phải tốn thêm khoảng **{over / 1000:.2f} giây**".replace(".", ",")
                 + " cho mỗi câu để suy nghĩ – với câu ngắn, “phí” này còn lâu hơn cả chạy câu đó. Khi Bao quyết định "
                 f"đổi cách chạy ({len(chg)} lần), có **{(ex < 0.9).sum()}** lần chậm hơn, chỉ "
                 f"{(ex > 1.1).sum()} lần nhanh hơn.",
                 "Muốn thắng PostgreSQL, AI phải **rất rẻ** và **biết khi nào nên để nguyên**.")

    # ---- 3. ablation
    f845 = os.path.join(E1, "exp1_ablation_8_4_8_5.csv")
    f83q = os.path.join(E1, "exp1_ablation_8_3_per_query.csv")
    f83 = os.path.join(E1, "exp1_ablation_8_3_3huong.csv")
    if os.path.exists(f845) and os.path.exists(f83q) and os.path.exists(f83):
        ab = pd.read_csv(f845)
        ab = ab[ab.nguồn.str.startswith("nhóm")].set_index("cấu_hình")
        q83 = pd.read_csv(f83q)
        r83 = q83.nhóm_50_chia_Full
        t83 = pd.read_csv(f83)
        t83 = t83[t83.nguồn.str.startswith("nhóm") & (t83.tập == "tất cả")].set_index("hướng").tổng_s_trung_vị
        d83 = t83["imdb50_trained__imdb_tested"] / t83["imdb_trained__imdb_tested"] - 1
        pq845 = pd.read_csv(os.path.join(E1, "exp1_ablation_8_4_8_5_per_query.csv"))
        pq845 = pq845[pq845.nguồn.str.startswith("nhóm") & pq845.co_y_nghia]
        geo = pq845[pq845["mục"].astype(str) == "8.5"].set_index("câu").ti_le
        bit = pq845[pq845["mục"].astype(str) == "8.4"].set_index("câu").ti_le

        def chg(cfg):
            r = ab.loc[cfg]
            return r.workload_ablation_s / r.workload_default_s - 1
        names = {"geqo": "Tắt GEQO", "bit": "Tắt bitmap scan & TID scan", "data": "Dữ liệu thay đổi"}
        rows = [(names["geqo"], int(ab.loc["no_geqo", "nhanh_hơn"]), int(ab.loc["no_geqo", "chậm_hơn"]),
                 chg("no_geqo")),
                (names["bit"], int(ab.loc["no_bitmap_tidscan", "nhanh_hơn"]),
                 int(ab.loc["no_bitmap_tidscan", "chậm_hơn"]), chg("no_bitmap_tidscan")),
                (names["data"], int((r83 < 0.9).sum()), int((r83 > 1.1).sum()), d83)]
        long = []
        for n, fast, slow, tchg in rows:
            lbl = f"{n}  (tổng {tchg:+.0%})".replace(".", ",")
            long += [{"thử nghiệm": lbl, "kết quả": "Số câu nhanh lên", "số_câu": fast},
                     {"thử nghiệm": lbl, "kết quả": "Số câu chậm đi", "số_câu": -slow}]
        long = pd.DataFrame(long)

        def c3():
            st.altair_chart(alt.Chart(long).mark_bar(cornerRadius=2).encode(
                y=alt.Y("thử nghiệm:N", sort=list(dict.fromkeys(long["thử nghiệm"])), title=None,
                        axis=alt.Axis(labelLimit=260)),
                x=alt.X("số_câu:Q", title="← số câu chậm đi    |    số câu nhanh lên →"),
                color=alt.Color("kết quả:N", title=None, legend=alt.Legend(orient="top"),
                                scale=alt.Scale(domain=["Số câu nhanh lên", "Số câu chậm đi"],
                                                range=[OUTCOME_COLOR["Thắng"], OUTCOME_COLOR["Thua"]])),
                tooltip=["thử nghiệm", "kết quả", alt.Tooltip("số_câu:Q", title="số câu (âm = chậm đi)")]
            ).properties(height=alt.Step(40)), width="stretch")
            st.caption("Chỉ đếm câu thay đổi rõ ràng (lặp lại nhiều lần, khác biệt có ý nghĩa thống kê). "
                       "Trong ngoặc: tổng thời gian của 113 câu thay đổi bao nhiêu.")

        with st.container(border=True):
            st.markdown("#### Phát hiện 3: Tắt từng thành phần (ablation) – cái gì thật sự ảnh hưởng?")
            st.markdown("**Ablation là gì?** Giống tháo từng bộ phận của máy ra xem máy còn chạy tốt không: "
                        "**chỉ tắt hoặc đổi đúng một thứ**, giữ nguyên mọi thứ khác, rồi đo lại. Nếu kết quả thay đổi "
                        "nhiều thì thứ đó quan trọng. Nhóm làm 3 lần thử giống bài báo:")
            left, right = st.columns([1.1, 1])
            with left:
                c3()
            with right:
                ex_g = ", ".join(f"{q} chậm {_vn(v, 1)} lần" for q, v in geo[geo > 3].sort_values(ascending=False)
                                 .head(2).items())
                ex_gf = ", ".join(f"{q} nhanh {_vn(1 / v, 1)} lần" for q, v in geo[geo < 0.5].sort_values().head(1)
                                  .items())
                ex_b = ", ".join(f"{q} nhanh {_vn(1 / v, 0)} lần" for q, v in bit.sort_values().head(1).items())
                ex_bs = ", ".join(f"{q} chậm {_vn(v, 1)} lần" for q, v in bit.sort_values(ascending=False).head(1)
                                  .items())
                top83 = q83.sort_values("nhóm_50_chia_Full", ascending=False).head(2)
                ex_d = ", ".join(f"{r.câu} chậm {_vn(r.nhóm_50_chia_Full, 1)} lần" for r in top83.itertuples())
                st.markdown(
                    f"**{names['geqo']}** – GEQO là “đường tắt” PostgreSQL dùng để lập kế hoạch nhanh cho câu nối từ "
                    f"12 bảng trở lên. Tắt đi thì PostgreSQL tìm kỹ hơn: vài câu nhanh hơn ({ex_gf}) nhưng nhiều câu "
                    f"chậm hẳn vì mất công tìm ({ex_g}).  \n"
                    f"**{names['bit']}** – hai trong các cách PostgreSQL đọc dữ liệu từ bảng. Tắt đi thì có câu nhanh "
                    f"hơn hẳn ({ex_b}), có câu chậm đi ({ex_bs}).  \n"
                    f"**{names['data']}** – cho Bao học trên bản IMDB chỉ còn một nửa dữ liệu, rồi dùng trên bản "
                    f"đầy đủ. Bao chọn sai ở nhiều câu ({ex_d}).")
            st.markdown(
                "**Rút ra (insight):**  \n"
                "1. **Tổng thời gian che giấu sự thật.** Tổng chỉ đổi vài phần trăm, nhưng hàng chục câu thay đổi "
                "mạnh theo cả hai chiều – câu nhanh lên bù cho câu chậm đi. → Phải xét **từng câu**, không chỉ nhìn tổng.\n"
                "2. **Không có thành phần nào luôn tốt hay luôn xấu.** Cùng một lần tắt, câu này lợi mà câu kia hại. "
                "→ Nếu **chọn đúng cái để tắt cho từng câu** thì sẽ nhanh hơn – đây chính là ý tưởng của Thí nghiệm 2.\n"
                "3. **Dữ liệu đổi thì AI chọn sai.** AI học thuộc dữ liệu cũ; khi dữ liệu đổi phải cho học lại, "
                "còn PostgreSQL thì tự cập nhật.")

    st.success(
        f"**Kết luận:** Bài báo nói đúng – AI chưa nhanh hơn PostgreSQL (Bao {_vn(bk)}, HybridQO {_vn(hk)} lần), vì "
        "tốn phí cho mỗi câu và hay đổi sai. Nhưng tắt đúng thành phần cho từng câu thì có thể nhanh hơn "
        "→ **Thí nghiệm 2** thử một mô hình rẻ chỉ làm đúng việc đó.")


# ================================================================ câu chuyện Thí nghiệm 2
def _exp2_story(agg, pq, lab):
    best_m = agg.loc[MODELS].speedup.idxmax()
    orc = agg.loc["Oracle", "speedup"]
    st.info("**Ý tưởng (từ Thí nghiệm 1):** tắt đúng thành phần cho từng câu thì PostgreSQL nhanh hơn, nhưng AI phải rẻ.  \n"
            "**Nhóm làm:** một mô hình nhỏ đọc kế hoạch của PostgreSQL (lệnh `EXPLAIN`, mất vài phần nghìn giây) rồi "
            "chọn 1 trong 6: **giữ nguyên**, hoặc **tắt 1 trong 5 cách nối / đọc bảng**. "
            f"Nếu lần nào cũng chọn đúng, PostgreSQL sẽ nhanh hơn **{_vn(orc)} lần**.")

    # ---- 1
    order = MODELS + ["Bao"]
    w = agg.loc[order].reset_index().rename(columns={"thắng": "Thắng", "hòa": "Hòa", "thua": "Thua"})
    w["phương_pháp"] = w.phương_pháp.map(lambda s: f"{s}  (chậm hơn ở {agg.loc[s, 'tỉ_lệ_thua']:.0%} số lần)")

    def c1():
        st.altair_chart(_wtl_bars(w, "phương_pháp", None, list(w.phương_pháp)), width="stretch")
        st.caption("Xanh = nhanh hơn PostgreSQL, xám = ngang nhau, đỏ = chậm hơn (lệch quá 10% mới tính).")
    _finding(1, "Mô hình rẻ nên ít khi làm chậm hơn PostgreSQL", c1,
             f"Mô hình chậm hơn PostgreSQL ở **{agg.loc[MODELS, 'tỉ_lệ_thua'].min():.0%}–"
             f"{agg.loc[MODELS, 'tỉ_lệ_thua'].max():.0%}** số lần, Bao **{agg.loc['Bao', 'tỉ_lệ_thua']:.0%}**.",
             f"“Phí” của mô hình chỉ khoảng **{pq.explain_ms.median():.0f} phần nghìn giây** mỗi câu, Bao tốn khoảng "
             "0,15 giây. Khi không chắc, mô hình hay chọn giữ nguyên nên kết quả ngang PostgreSQL.",
             "Đã giải quyết được vấn đề “phí cao” của Thí nghiệm 1.")

    # ---- 2
    p = pq[pq.mô_hình == best_m]
    lost = ((p.e2e_ms - p.PG_ms).clip(lower=0).groupby(p.query_id).sum() / 1000).sort_values(ascending=False)
    top = lost.head(6).reset_index(name="giây_mất")
    top3 = list(lost.index[:3])
    rest = p[~p.query_id.isin(top3)]
    sp_rest = rest.PG_ms.sum() / rest.e2e_ms.sum()
    q0 = lost.index[0]
    L = lab.set_index("query_id").loc[q0]
    pick = p[p.query_id == q0].dự_đoán.value_counts().idxmax()

    def c2():
        top["màu"] = np.where(top.query_id == q0, "a", "b")
        st.altair_chart(alt.Chart(top).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("query_id:N", sort=list(top.query_id), title="Câu truy vấn"),
            x=alt.X("giây_mất:Q", title="Số giây bị chậm hơn PostgreSQL vì chọn sai"),
            color=alt.Color("màu:N", legend=None, scale=alt.Scale(domain=["a", "b"], range=[OUTCOME_COLOR["Thua"],
                                                                                          "#c8c6c0"])),
            tooltip=["query_id", alt.Tooltip("giây_mất:Q", format=".1f")]).properties(height=alt.Step(26)),
            width="stretch")
    _finding(2, "Nhưng tổng thời gian vẫn chậm hơn – vì vài lần chọn sai rất đắt", c2,
             f"Tính tổng, mô hình tốt nhất ({best_m}) chỉ bằng **{_vn(agg.loc[best_m, 'speedup'])}** lần PostgreSQL. "
             f"Riêng câu **{q0}** gây ra **{lost.iloc[0] / lost.sum():.0%}** phần bị chậm.",
             f"Ở {q0}, PostgreSQL chạy {_vn(L.t_default_ms / 1000, 1)} giây. Chọn đúng (`{L.nhãn}`) thì còn "
             f"{_vn(L[f't_{L.nhãn}_ms'] / 1000, 1)} giây, nhưng mô hình chọn `{pick}` nên mất "
             f"**{L[f't_{pick}_ms'] / 1000:.0f} giây**.",
             f"Bỏ 3 câu chọn sai nặng nhất ({', '.join(top3)}) thì mô hình đã nhanh hơn PostgreSQL "
             f"(**{_vn(sp_rest)}** lần). → Đúng nhiều lần chưa đủ, phải **tránh được lần sai đắt**.")

    a = pq.assign(đúng=pq.nhãn_thật == pq.dự_đoán).groupby("kiểu").đúng.mean()
    st.success(
        f"**Kết luận:** Mô hình nhỏ **chưa** làm PostgreSQL nhanh hơn về tổng ({_vn(agg.loc[best_m, 'speedup'])} lần; "
        f"Bao {_vn(agg.loc['Bao', 'speedup'])} lần), nhưng **ít khi làm chậm hơn PostgreSQL** so với Bao. "
        "Điểm yếu là vài lần chọn sai rất đắt, nhất là với loại câu chưa từng gặp (chỉ đoán đúng "
        f"{a.get('BQ', float('nan')):.0%}).  \n"
        "**Bước tiếp theo:** khi không chắc thì giữ nguyên PostgreSQL – tab **4. Khai phá dữ liệu** cho thấy làm vậy "
        "giúp Random Forest nhanh hơn PostgreSQL. Tự thử mô hình ở tab **5. Demo mô hình**.")
