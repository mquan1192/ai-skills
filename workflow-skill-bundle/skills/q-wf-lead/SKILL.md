---
name: q-wf-lead
description: "Việc của phiên trưởng nhóm (LEAD) và thư ký (SECRETARY): board, INBOX, backlog, báo cáo gom cho chủ dự án, phân loại và giao việc, chọn mức QA, sprint 1 tuần (lập kế hoạch, báo cáo tuần, retro), đo context và dọn phiên trước việc mới. Dùng khi là LEAD / SECRETARY, khi lập kế hoạch sprint, viết báo cáo tuần hoặc retro. Không dùng cho: quy tắc chung của mọi phiên (q-wf-team), các bước card / vé (q-wf-card). Keywords: điều phối, lead, thư ký, sprint, scrum, retro, INBOX, board, backlog."
---

# Việc của trưởng nhóm (LEAD) và thư ký (SECRETARY)

Đọc trước skill `q-wf-team`. Thư mục làm việc của LEAD là `paths.lead` trong `.workflow/workflow.config.json`; khuôn file nằm trong `templates/lead/` của gói. LEAD không tự làm việc chuyên môn của phiên khác và không sửa file dùng chung (gửi DOCS).

## 1. File của LEAD

| File | Nội dung |
|---|---|
| `board.md` | Khối "Sprint này" ở đầu; bảng `TASK · Việc · Người làm · Trạng thái · QA · Write set · Bước tiếp · Cập nhật`. Trạng thái chỉ dùng 6 giá trị: `todo / doing / waiting / review / done / blocked` |
| `INBOX.md` | SECRETARY ghi (không có SECRETARY: LEAD ghi). Chỉ những gì cần chủ dự án, 3 nhóm: chủ dự án tự làm · chủ dự án trả lời · để biết (quyết định 🟢 / 🟡 của LEAD). Mỗi dòng một mã `INBOX-NN`; xong chuyển sang "Đã xong hôm nay" |
| `backlog.md` | `BACKLOG-YYYYMMDD-NN`, chỉ từ chính lời chủ dự án (nguyên văn + ngày). Không ai tự làm việc trong backlog; chỉ khi chủ dự án yêu cầu mới lấy ra nghiên cứu hướng làm |
| `tasks/` | Brief từng việc (5 dòng đầu theo `q-wf-team` §5) |
| `sprint/` | `SPRINT-YYYY-Www.md` (báo cáo tuần), `RETRO-YYYY-Www.md` (retro) |

## 2. Nhận và giao việc

- **Một yêu cầu của chủ dự án = một TASK**; bước con là mốc bên trong, không mở TASK mới.
- **Đo context** của phiên nhận việc trước mỗi lần giao (`q-wf-team` references § 2): vượt `context.warn_tokens` và việc mới không liên quan → phiên đó ghi `QUEUE_<ROLE>.md`, xin dọn, giao sau khi dọn.
- Chọn mức làm việc (`QUICK` / `DOC` / `CARD`) và mức QA (`NO-QA` / `LIGHT` / `FULL`) cho từng việc, ghi lên board.
- Phân loại nhanh và ghi nhãn trong brief: `CLEAR` → BUILD hoặc model rẻ; `DESIGN` / `RESEARCH` → phiên nghiên cứu, chỉ ra tài liệu; `HARD` → phiên nghiên cứu mạnh nhất. Việc cơ học (đếm, quét, so sánh, chạy script kiểm) giao sub-agent model nhỏ.
- Phiên nghiên cứu dùng tiết kiệm: câu hỏi hẹp, đầu ra rõ, điểm dừng rõ; brief ghi phần nào cần model mạnh và vì sao.
- Trước khi giao cho QA, đối chiếu `[DONE]` / biên nhận của BUILD với brief (kiểm bắt buộc, số lượng, file); thiếu thì trả BUILD trước.
- Trước khi đưa bất cứ thứ gì cho chủ dự án: kiểm tên file, phiên bản, card trong `[DONE]` khớp file thật.
- Quyết định 🟡 tự làm (đặt tên, nguồn dữ liệu, bố cục nhỏ) và ghi vào INBOX "để biết". Chỉ hỏi chủ dự án khi đổi phạm vi, có rủi ro 🔴 hoặc gửi ra ngoài.
- Mọi câu hỏi cho chủ dự án có phương án × Ưu / Nhược, phương án đề xuất đứng đầu, ghi "(đề xuất)"; danh sách đánh số `#1`, `#2` kèm mã để chủ dự án trả lời `#1 OK · #3 B`; câu trả lời ghi lại kèm ngày.

## 3. Báo cáo cho chủ dự án

- SECRETARY gom báo cáo mỗi giờ (phút `report.batch_minute`, từ `report.from` tới `report.to`), chỉ khi có điều mới, tối đa ~10 dòng; mỗi lần báo kèm một dòng cho mỗi phiên vượt ngưỡng context (`Cần dọn phiên: …` / `Cần nén phiên: …`). Báo ngay chỉ khi 🔴: phát hiện chính sách, việc bị chặn, cần dòng duyệt để release.
- SECRETARY nhận câu trả lời / `OK CONFIRM-…` của chủ dự án và chuyển **nguyên văn** cho LEAD; không tự quyết thay LEAD. Dòng duyệt release và đường dẫn bảo vệ chỉ được gõ trong phiên LEAD.
- Không quá `report.max_waiting_items` (mặc định 3) mục cùng chờ chủ dự án; mục mới xếp hàng trong INBOX.
- Nhiều card chờ release → chuẩn bị **một** dòng duyệt nêu mọi đường dẫn bảo vệ; chủ dự án gõ một lần; LEAD chép dòng đó vào phần Decisions của từng card.
- Báo cáo card kết thúc bằng khối NEXT:

```text
NEXT
- Lúc: <dd/mm HH:MM> · Đang chờ: <phiên> — <việc> (vé TICKET-NN)
- Bước: <pha — việc>
- Ai: <VAI> · <model>
- Prompt: #NN → CARD.md "Takeover"
- Quyền production: KHÔNG | <câu chủ dự án đã gõ + manifest digest>
```

## 4. Sprint 1 tuần (Scrum)

| Khi nào | LEAD làm |
|---|---|
| Thứ Hai, lần báo cáo đầu | Lập kế hoạch: khối "Sprint này" trên board (≤ 3 mục tiêu + danh sách TASK có mã `SPRINT-YYYY-Www`), việc hoãn; chủ dự án trả lời một lần |
| Hằng ngày | Báo cáo gom mỗi giờ + INBOX; việc chủ dự án giao giữa tuần nhận ngay, ghi "thêm giữa sprint" |
| Thứ Sáu ~15:00 | Gửi mỗi phiên đang chạy một dòng: "RETRO SPRINT-…: gửi ý trước 15:00" |
| Thứ Sáu ~17:30 | Viết `sprint/SPRINT-YYYY-Www.md` (≤ 1 trang: mục tiêu đạt / chưa, việc xong, việc chưa xong và lý do, đang chờ chủ dự án, số liệu, tuần sau) và `sprint/RETRO-YYYY-Www.md` (Tốt · Chưa tốt · ≤ 5 đề xuất có Ưu / Nhược · một dòng duyệt `IDEA-…`). Số liệu lấy bằng script hoặc sub-agent nhỏ |
| Sau khi chủ dự án chọn | Một card `retro-YYYY-Www` gom mọi thay đổi quy tắc / skill, một dòng duyệt chung; gửi DOCS cài. Tối đa một thay đổi quy trình mỗi tuần (trừ 🔴); lịch sử quyết định ghi vào `RULES-HISTORY.md` với `Đã loại:` / `Thay cho:` |

- Việc chưa xong chuyển sang sprint sau, giữ nguyên mã TASK.
- Đề xuất thêm phiên / nhóm mới khi một vai trò để việc chờ > 1 ngày trong 2 sprint liền, một loại việc lặp ≥ 3 lần mỗi sprint mà không có vai trò hợp, hoặc cần model khác — thử sub-agent hay đổi model trước. Phiên rảnh 2 sprint → đề xuất lưu trữ.

## 5. Dọn phiên trước việc mới

| Tình huống | Làm gì |
|---|---|
| Cùng TASK hoặc cùng nguồn | Giữ phiên |
| Không liên quan, mới 1–2 việc từ lần dọn trước | Giao luôn |
| Không liên quan, ≥ 3 việc khác nhau, ngữ cảnh đã bị tóm tắt, hoặc context vượt `context.warn_tokens` | Dọn trước |
| Phiên đang có việc `doing` / `waiting` | Không dọn; dùng phiên khác |
| Gấp hoặc 🔴 | Bỏ qua bước dọn, ghi "bỏ qua xóa (gấp)" lên board |

Trước khi dọn, phiên ghi ≤ 10 dòng vào `QUEUE_<ROLE>.md` (trạng thái từng việc, file kết quả + phiên bản, câu hỏi mở và đang chờ ai, yêu cầu đang mở, "đã xóa lúc …"); LEAD chỉ dọn sau khi phiên xác nhận ghi xong.

## 6. Mỗi ngày

- Lần đầu trong ngày: dọn thùng rác theo quy tắc dự án (nếu có công cụ), xóa phần "Đã xong hôm nay" của INBOX hôm trước.
- Việc không cập nhật một ngày làm việc → hỏi người làm.
- `stale.ps1` liệt kê vé đứng lâu (SENT > `stale.sent_minutes`, ACCEPTED không đổi file > `stale.accepted_hours`).
