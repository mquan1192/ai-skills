# Quy tắc bổ sung (bản 1.1)

Chi tiết cho `q-wf-team`. Giá trị riêng của dự án (ngưỡng, giờ phát hành, bật / tắt) nằm trong `.workflow/workflow.config.json`.

## 1. Biểu tượng — mỗi biểu tượng một nghĩa

Luôn kèm chữ, không dùng biểu tượng thay câu. Bản ghi cũ giữ biểu tượng cũ.

| Nhóm | Biểu tượng |
|---|---|
| Mức duyệt | 🟢 AUTO · 🟡 LEAD · 🔴 chủ dự án phải trả lời / duyệt |
| An toàn | 🚫 bị chặn / cấm · 🚨 lẽ ra bị chặn (nếu dự án có guard ở chế độ chỉ quan sát; việc đã chạy) · ⚠️ hỏi trước khi làm · 🔸 rủi ro nhỏ, chỉ để biết · 📌 ghi chú |
| Kết quả | ✅ đạt / xong · ❌ không đạt / vi phạm · ◐ một phần · ❓ cần kiểm · ➕ mới |
| Hệ thống | 📚 kho kiến thức · 🔎 phạm vi · 💡 gợi ý |
| Trạng thái việc (chỉ trong báo cáo cho chủ dự án) | 📝 chưa làm · 🔄 đang làm · ⏸️ đang chờ · 🔍 đang xem lại · ✅ xong · ⛔ bị chặn |

## 2. Context: đo, dọn, nén

- **Đo**: LEAD đo context của phiên nhận việc trước mỗi lần giao; mỗi phiên đo lại khi gửi `[DONE]`. Phiên rảnh không đo được thì đo ở tin nhắn kế tiếp.
- **Ngưỡng** `context.warn_tokens` (mặc định 250 nghìn token):
  - vượt ngưỡng, **không** còn việc `doing` / `waiting` → phiên ghi ghi chú hàng đợi rồi xin dọn (clear); SECRETARY (hoặc LEAD) đưa dòng `Cần dọn phiên: <phiên>` vào báo cáo gom, chủ dự án gõ lệnh dọn;
  - vượt ngưỡng, **còn** việc dở → ghi ghi chú hàng đợi, xin nén (compact).
  - vượt `context.strong_tokens` (mặc định 500 nghìn) → context "rất lớn": dọn / nén ngay khi xong bước đang làm, không nhận việc mới trước đó.
- **Dọn khi đủ cả hai**: (a) không còn việc `doing` / `waiting` của mình, `[DONE]` đã gửi, ghi chú hàng đợi đã ghi; (b) việc tiếp theo không liên quan, **hoặc** context vượt ngưỡng, **hoặc** cuối ngày.
- **Trước khi dọn**: ≤ 10 dòng vào `QUEUE_<ROLE>.md` (trạng thái từng việc, tệp kết quả + phiên bản, câu hỏi mở và đang chờ ai, yêu cầu đang mở, "đã dọn lúc …"); bài học vào `NOTES_<ROLE>.md`; đóng bước đang mở trong nhật ký thời gian.
- **Hook nhắc** `ctxwatch.py` (khi `context.enabled` = true): mỗi lượt đọc phần cuối bản ghi hội thoại của chính phiên đó, vượt `context.warn_tokens` thì chèn một dòng nhắc; vượt `context.strong_tokens` thì ghi "rất lớn". Hook không chặn, không ghi gì, không đọc tệp nào khác.

## 3. Cỡ tệp

- Tệp đọc khi bắt đầu việc (thông báo chung, `QUEUE_<ROLE>.md`, `STATUS.md`, brief) ≤ `limits.start_file_kb` (mặc định 10 KB) mỗi tệp; tệp skill không tính.
- Tệp quy tắc chính của dự án (`CLAUDE.md` hoặc tương đương) ≤ `limits.rules_file_kb` (mặc định 25 KB). Gần trần → chuyển chi tiết sang skill / tệp tham chiếu, không thêm vào tệp quy tắc chính.
- `SKILL.md` ≤ khoảng 8 KB; phần dư chuyển sang `references/` của skill.
- `NOTES_<ROLE>.md` được tỉa ≤ 10 KB ở buổi retro.

## 4. Phát hành quy tắc và lịch sử quy tắc

- **Theo đợt**: thay đổi tệp quy tắc, `AGENTS.md`, skill, hook, settings được DOCS phát hành tối đa 2 lần / ngày theo `docs.publish_windows` (mặc định 12:00 và 17:30) hoặc cùng card retro tuần. Việc 🔴 hay sửa gấp được phát hành ngay. Nội dung kho kiến thức của dự án phát hành như bình thường.
- **Một thay đổi quy trình mỗi tuần** (trừ 🔴): thay đổi quy tắc / skill từ retro gom vào **một** card với **một** dòng duyệt.
- **Lịch sử quy tắc ở tệp riêng** `<paths.process_docs>/RULES-HISTORY.md` (khuôn `templates/RULES-HISTORY.md`): ai quyết, khi nào, theo yêu cầu nào. Tệp quy tắc chính chỉ giữ quy tắc đang chạy, không giữ lịch sử. Tệp lịch sử không tự nạp; chỉ đọc khi cần nguồn gốc một quy tắc.
- **Dòng lịch sử mới**: quyết định đến từ một câu hỏi có phương án ghi thêm `Đã loại: <phương án> (<lý do ngắn>)`; quyết định thay một quyết định cũ ghi thêm `Thay cho: <quy tắc / mã yêu cầu cũ>`. Quyết định đã duyệt không sửa; quyết định sau thay nó bằng dòng mới. Dòng cũ không viết lại.

## 5. Guard

Khi `guard_rule_enabled` = true: làm theo `AGENTS.md` § Guard (cảnh báo đỏ, dừng, không lách, chỉ qua bằng `GUARD-OK <HHMM> "<lý do>"` do chủ dự án tự gõ trong phiên bị chặn). Gói không kèm guard nào; nếu dự án có guard ở chế độ chỉ quan sát, dòng `🚨 … lẽ ra bị chặn` là cảnh báo: việc đã chạy, phiên tự xét lại việc đó và báo LEAD khi có rủi ro dữ liệu thật.

## 6. Văn phong khi viết báo cáo / tài liệu

- Thứ tự: skill loại tài liệu (nếu có) → skill văn phong (`writing_style_skill`, mặc định `q-doc-edit`, gói văn phong riêng) → tự soát trước khi ghi tệp.
- Không cài skill văn phong: tự soát 5 điểm trước khi ghi tệp — giữ đúng số liệu, ngày, mã, tên; tách sự thật / suy luận / đề xuất; mỗi kết luận có nguồn; câu ngắn, một ý; người ngoài nhóm đọc hiểu được (viết đủ chữ lần đầu cho từ viết tắt).
- Kết quả kiểm trong `[DONE]` / báo cáo QA dùng 4 trạng thái: đã kiểm đạt · đã kiểm không đạt · chưa kiểm (lý do) · không kiểm được (lý do).
