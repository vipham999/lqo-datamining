# Review báo cáo giữa kỳ – Team1_GiuaKy_Final.pdf

## 0. Vi phạm yêu cầu hình thức (ưu tiên số 1)

- **0.1. Quá dài.** Thầy yêu cầu 5–7 trang A4, nhưng phần nội dung hiện chiếm khoảng 16,5 trang (tr.4–20), chưa tính bìa, bảng phân công và mục lục. Cần cắt còn khoảng 40%. Phân bổ gợi ý (tổng ~7 trang):

  | Mục | Hiện tại | Mục tiêu | Cách cắt |
  |---|---|---|---|
  | 1. Nội dung chính | ~5,5 tr | 2 tr | Bỏ 1.2.1; rút bảng LQO (1.2.2) còn 1 câu liệt kê; mỗi lỗ hổng chỉ giữ 1 bảng gộp 3 cột (Vấn đề – Bằng chứng – Khuyến nghị), tức 4 lỗ hổng = 1 bảng |
  | 2. Tính SOTA | ~1,5 tr | 1 tr | Gộp các đoạn trùng với Mục 1 (kết quả PostgreSQL thắng, LEON 9,6 giờ đã nói ở Mục 1) |
  | 3. What/How/Why | ~4,5 tr | 2 tr | What: 1 đoạn + 3 gạch đầu dòng mục tiêu. How: giữ bảng 3.2.1, bỏ 3.2.2–3.2.5 (đã có trong bảng) và bảng 3.2.6. Why: gộp 3.3.1–3.3.3 thành 3 gạch đầu dòng. Bỏ 3.4 |
  | 4. Cài đặt minh họa | ~6 tr | 2 tr | Giữ: link GitHub, bảng môi trường (4.2), **kết quả nhóm tự chạy**, bảng 4.8. Chuyển 4.4, 4.6, 4.7 (data mining, CEB) thành 3–4 dòng “hướng mở rộng” |

  Các mẹo khác để gọn trang: bỏ mục lục (báo cáo 7 trang không cần) hoặc gộp bảng phân công lên trang bìa; ảnh code/log dùng font nhỏ hơn hoặc đưa sang README trên GitHub; Tài liệu tham khảo dùng cỡ chữ 10–11.

- **0.2. Tên tập tin.** “Team1_GiuaKy_Final.pdf” cần đặt lại đúng quy định thầy nêu ở phần trước (mình chưa có nội dung quy định đó, cần xem lại để đặt cho khớp).
- **0.3. “Theo cách hiểu bài báo”.** Mục 1 hiện bám sát bài báo theo kiểu tóm tắt từng § một. Khi rút gọn, nên viết lại bằng lời của nhóm (ví dụ: “Theo nhóm, điểm cốt lõi là…”) thay vì liệt kê §.

## A. Đối chiếu 4 yêu cầu của thầy

| Yêu cầu | Mục | Đánh giá |
|---|---|---|
| Nội dung chính | 1 (tr.4–9) | ✅ Đạt, phân tích kỹ 4 lỗ hổng. Còn lỗi trích dẫn (B1–B3) |
| Tính SOTA | 2 (tr.9–10) | 🟡 Đạt nhưng mỏng, nên bổ sung (C1) |
| Phát triển từ bài báo (What, How, Why) | 3 (tr.10–15) | ✅ Đủ 3 phần. Chưa nối với Mục 4 (C2) |
| Cài đặt minh họa (mã nguồn trên GitHub) | 4 (tr.15–20) | ❌ **Chưa đạt**: không có link GitHub của nhóm, chưa có kết quả nhóm tự chạy (A1, A2) |

## A. Lỗi nghiêm trọng (phải sửa)

- **A1. Không có link GitHub của nhóm.** Báo cáo chỉ nêu repo của tác giả (`github.com/edualc/lqo_ml_perspective`, tr.15). Thư mục `database/` hiện chưa phải git repo.
  → Tạo repo (scripts/, infra/, analysis/, README.md), push lên GitHub, ghi link ở trang bìa hoặc đầu Mục 4. Không push dữ liệu IMDB 12 GB hay repo tác giả (dùng `.gitignore`/submodule).
- **A2. Mục 4 mới là kế hoạch, chưa có “cài đặt minh họa”.** Các mục 4.5 và 4.6 đều ở thì tương lai; ví dụ plan 1a ghi rõ “chưa phải kết quả đo”; còn 4.8 thì dùng log của tác giả.
  → Bổ sung ít nhất: (1) kết quả nhóm chạy PostgreSQL baseline 113 câu JOB (tổng thời gian, vài câu tiêu biểu); (2) plan thật của câu 1a ở chế độ default và no_nestloop kèm thời gian đo được; (3) ảnh chụp container chạy / output `EXPLAIN ANALYZE`. Đổi tên mục thành “4. Cài đặt minh họa và kế hoạch mở rộng”.
- **A3. Báo cáo không nêu tên bài báo được phân tích.** Cần ghi ngay ở 1.1: Lehmann, Sulimov, Stockinger, *“Is Your Learned Query Optimizer Behaving As You Expect? A Machine Learning Perspective”*, PVLDB 17(7): 1565–1577, 2024.

## B. Lỗi trích dẫn / nội dung

- **B1. Số [1] mâu thuẫn.** Danh mục tài liệu: [1] = Neo. Nhưng Mục 3 và 3.x viết “Lehmann và cộng sự [1]”, “[1, Mục 4]”…, tức là dùng [1] cho bài báo gốc.
- **B2. Có 3 hệ thống trích dẫn lẫn nhau.** Mục 1 dùng số của bài báo gốc ([23], [22], [37], [30], [17], [18]…, tối đa [44]), trong khi danh mục chỉ có 6 mục. Mục 2 dùng [1]–[6], Mục 3 dùng [1] = bài báo gốc.
  → Đề xuất: [1] = bài báo gốc, đánh số lại toàn bộ và bổ sung đủ các tài liệu được nhắc (Lero, LOGER, RTOS, JOB, STACK, CEB, DSB, pg_hint_plan, Zhang et al.…).
- **B3. Ký hiệu § và “Hình 1/2/3”, “Bảng 1/2” trỏ tới bài báo gốc nhưng không giải thích.** Thêm 1 câu ở 1.1: “Ký hiệu §x, Hình x, Bảng x trong báo cáo chỉ mục/hình/bảng của bài báo [1]”. Nếu có thể thì chèn lại Hình 1 (pipeline) vì 1.2.1 và 1.2.2 dựa vào nó.
- **B4. Sai khái niệm (tr.6, 1.2.3):** “ánh xạ D → y phải là 1-1”. Nguyên tắc bất biến (§1, chú thích 3) chỉ yêu cầu *cùng đầu vào → cùng đầu ra*, tức D → y là **hàm** (nhiều-một vẫn hợp lệ), không phải song ánh/1-1.
  → Sửa: “ánh xạ D → y phải là một hàm (mỗi D chỉ ứng với một y)”.
- **B5. Tr.15, 4.2:** “Phải dùng đúng PostgreSQL 12.5 vì pg_hint_plan và pg_bao chỉ hỗ trợ phiên bản này” là chưa chính xác, vì pg_hint_plan có bản cho nhiều phiên bản PostgreSQL.
  → Sửa: “dùng PostgreSQL 12.5 để khớp với bài báo và với bản pg_bao/pg_hint_plan trong repo của tác giả”.
- **B6. Ngưỡng không thống nhất:** 4.3 lấy ±10% để tính thắng/thua, còn 4.6 lấy 5% để gán nhãn. Nên thống nhất một ngưỡng hoặc giải thích lý do dùng hai ngưỡng.
- **B7. Bảng 4.8:** nên ghi rõ 233 = tổng số câu test trên 9 split, và giải thích “Speedup tổng” (= tổng thời gian PG / tổng thời gian LQO, end-to-end?). Đã kiểm tra: tổng mỗi dòng đều bằng 233, khớp nhau.

## C. Nội dung nên bổ sung

- **C1. Mục SOTA quá ngắn** và không có nguồn cho các so sánh. Gợi ý thêm một bảng so sánh với các công trình đánh giá LQO trước đó (Zhang et al. [6], các bài benchmark LQO khác), theo các cột: số LQO được đánh giá, có đo end-to-end không, cách chia split, có công bố mã nguồn không. Nêu thêm venue (PVLDB 2024) để thể hiện mức độ cập nhật.
- **C2. Mục 3 và Mục 4 không ăn khớp.** Mục 3 đề xuất query+plan encoding cùng Learning-to-Rank, nhưng Mục 4 cài đặt phân loại hint set bằng Decision Tree/RF/…. Thêm 1 đoạn đầu Mục 4 giải thích Mục 4 là bước nguyên mẫu đơn giản hóa (6 hint set, đặc trưng tĩnh) để kiểm chứng giả thuyết của Mục 3 trước khi làm LTR. Hoặc thêm LTR (ví dụ LightGBM LambdaRank) vào danh sách mô hình ở 4.6.
- **C3. 4.6:** chỉ có 113 câu chia cho 6 lớp, mất cân bằng nặng (đa số là default). Nên nói rõ cách xử lý (class_weight, gộp lớp) và nhắc lại rằng chọn mô hình theo tổng thời gian workload chứ không theo accuracy.

## D. Trình bày / định dạng

- **D1. Mục lục:** số trang lệch 1–2 trang (ví dụ Mục 1 ghi tr.3 nhưng thực tế là tr.4; Mục 2 ghi tr.8 nhưng là tr.9; Mục 4 ghi tr.13 nhưng là tr.15). Mục lục còn thiếu 4.9 và phần Tài liệu tham khảo. → Trong Word chọn References → Update Table → Update entire table.
- **D2.** Dòng thừa “BÁO CÁO GIỮA KỲ……1” ở cuối trang 2 (heading trang bìa lọt vào mục lục) → bỏ style Heading của tiêu đề bìa.
- **D3.** Trang 21 trắng → xóa.
- **D4.** Bảng ở 4.8 bị tách: header ở tr.19, dữ liệu ở tr.20 → bật “Repeat as header row” / “Keep with next”. Bảng 1.3.4 cũng bị tách tương tự (tr.8–9).
- **D5.** Định dạng không đồng nhất giữa các phần: bảng Mục 1 và 4 viền đen trơn, bảng Mục 3 có header nền xanh; Mục 2 và 3 căn đều, Mục 1 và 4 căn trái; cỡ chữ cũng khác nhau. → Dùng chung một style.
- **D6. Lỗi nhỏ:** “pipeline ml” → “pipeline ML” (heading 1.3); “1.3.3.  Lỗ hổng” thừa dấu cách; “1.2.3 Khái niệm” thiếu dấu chấm sau số; Tài liệu tham khảo bị căn đều tạo khoảng trắng lớn → chuyển sang căn trái.
- **D7.** Trang bìa: “PGS.TS NGUYỄN ĐÌNH / THUẬN” bị ngắt dòng giữa tên → để cùng một dòng.
