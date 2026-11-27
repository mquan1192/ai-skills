<!-- BEGIN workflow-skill-bundle -->
## Quy trình nhóm (gói workflow v1.1)

- Cấu hình quy trình: `.workflow/workflow.config.json` (đường dẫn, vai trò và phiên, cách gọi chủ dự án, file chính sách, ngưỡng context, bật / tắt quy tắc guard). Đọc `.workflow/DOC-TRUOC.md` khi cần.
- Mọi phiên dùng skill `q-wf-team`; trưởng nhóm thêm `q-wf-lead`; code / script, đường dẫn bảo vệ và thứ gửi ra ngoài theo `AGENTS.md` + skill `q-wf-card`.
- Mỗi file một người ghi (bảng vai trò trong `q-wf-team` § 1). File dùng chung (`shared_paths` của config) chỉ phiên DOCS sửa, phát hành theo đợt (`docs.publish_windows`).
- Kênh với chủ dự án: SECRETARY (nếu có) nhận câu trả lời / xác nhận và ghi INBOX; dòng duyệt release và đường dẫn bảo vệ chỉ gõ trong phiên LEAD.
- Mức duyệt: 🟢 tự làm, báo sau · 🟡 trưởng nhóm quyết · 🔴 chủ dự án duyệt bằng khối `CONFIRM-…`. Danh sách gửi chủ dự án đánh số `#1`, `#2`; trả lời `#1 OK · #3 B`. Biểu tượng: mỗi cái một nghĩa, luôn kèm chữ.
- Báo cáo ngắn: `[DONE]` tối đa 6–8 dòng, chi tiết để trong file; BUILD liệt kê `CHOICE-n`.
- Context: đo trước khi giao việc và khi `[DONE]`; vượt `context.warn_tokens` → ghi `QUEUE_<ROLE>.md` (≤ 10 dòng) rồi dọn (hết việc) hoặc nén (còn việc dở); vượt `context.strong_tokens` ("rất lớn") → dọn / nén ngay sau bước đang làm. Tệp đọc đầu việc ≤ 10 KB; tệp quy tắc chính ≤ 25 KB.
- Guard / hook bảo vệ chặn (khi `guard_rule_enabled` = true): cảnh báo đỏ, dừng, không lách; chỉ qua khi chủ dự án tự gõ `GUARD-OK <HHMM> "<lý do>"` trong phiên đó (`AGENTS.md` § Guard).
- Viết báo cáo / tài liệu: skill loại tài liệu trước, rồi skill văn phong (`writing_style_skill`, nếu đã cài), tự soát trước khi ghi file.
- Ghi thời gian từng bước bằng `steplog.ps1` (PowerShell 7; mã bước trong `q-wf-team` § 7).
- Chính sách dữ liệu: theo file `policy_file` của config; không bao giờ ghi bí mật (mật khẩu, khóa API, token) vào bất kỳ đâu.
<!-- END workflow-skill-bundle -->
