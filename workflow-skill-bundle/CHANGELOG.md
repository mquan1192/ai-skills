# CHANGELOG — gói quy trình nhóm

## 1.1.1

Chỉ đổi tài liệu, không đổi chức năng: skill, script, hook, khuôn, `AGENTS.md`, `install.py` giữ nguyên từng byte.

- Thêm `README.md` (EN) dạng trang đầu GitHub: gói làm gì, cho ai, cách hoạt động (mỗi thuật ngữ có một câu giải thích), sơ đồ Mermaid, cách chỉ lấy riêng gói này (zip ở trang Releases hoặc chép thư mục), cài / gỡ, an toàn, yêu cầu, giấy phép và dòng bản quyền; chỗ trống `[REPO-URL]`. `install.py` không cài file này vào dự án.
- Điền link kho mã thật (https://github.com/mquan1192/ai-skills) vào chỗ trống `[REPO-URL]` trong `README.md` và `README_VN.md`; `MANIFEST.json` cập nhật sha256 / bytes của các file này.
- `README.md` và `README_VN.md` viết lại thành 2 phần: Phần 1 Sơ lược (hình dung, trước / sau, cách dùng, bắt đầu trong 3 bước) cho người không đọc code; Phần 2 Chi tiết kỹ thuật. Sơ đồ Mermaid: nhãn ngắn, ngắt dòng bằng `<br/>`, tách thành nhiều sơ đồ nhỏ để GitHub không cắt chữ. Các mục đánh số của `README_VN.md` giữ nguyên số. `docs/quy-trinh.md`: nhãn sơ đồ ngắn lại, ngắt dòng; lời nhắn tự gửi dài đổi thành ghi chú. `MANIFEST.json` cập nhật sha256 / bytes.
- Thêm `LICENSE`: nguyên văn Apache License 2.0. `install.py` không cài file này vào dự án.
- `README_VN.md`: dòng đầu trỏ sang `README.md`; thêm mục "Tổng quan" cùng nội dung (sơ đồ nhãn tiếng Việt, mục "Chỉ cài gói cần dùng") trước mục 1; các mục 1–7 giữ nguyên.
- `DOC-TRUOC.md`, `SECURITY.md` không đổi: tiêu đề vẫn ghi v1.1, nội dung đúng cho 1.1.1.

## 1.1

- **Tên trạng thái mới**: script ghi `IN-REVIEW`, `FIXING`, `RELEASED`, `CANCELLED`, pha `BUILD` / `TEST-GATE` / `FIX` / `VERIFY-FIX`, vé `ON-HOLD` / `TAKEN-OVER`, kết quả `FAIL` / `FIX-VERIFIED`, biên nhận `OUTDATED`; vẫn đọc mọi giá trị cũ, nên card / vé / nhật ký cũ không cần sửa (`NAMES.md` § 2).
- **Chỉ PowerShell 7**: mọi script quy trình từ chối Windows PowerShell 5.1 bằng một dòng `REFUSED: …` và không ghi gì; `gate.hosts` mặc định `ps7`.
- **Vai trò mới**: SECRETARY (kênh với chủ dự án: câu trả lời, xác nhận, INBOX, báo cáo gom mỗi giờ) và REVIEW_S (QA nhẹ). Dòng duyệt release / đường dẫn bảo vệ chỉ gõ trong phiên LEAD.
- **Danh sách gửi chủ dự án** đánh số `#1`, `#2`; trả lời `#1 OK · #3 B`.
- **Context**: đo trước khi giao và khi `[DONE]`; ngưỡng dọn / nén (mặc định 250 nghìn token); hook mới `ctxwatch.py` nhắc khi vượt ngưỡng (bật / tắt bằng `context.enabled`).
- **Bộ biểu tượng một nghĩa**, cỡ tệp đầu việc ≤ 10 KB, tệp quy tắc chính ≤ 25 KB, phát hành quy tắc theo đợt (2 lần / ngày), tối đa một thay đổi quy trình mỗi tuần, lịch sử quy tắc ở tệp riêng `RULES-HISTORY.md` với trường `Đã loại:` / `Thay cho:`.
- **Card**: card sửa lỗi script có test FAIL trước khi sửa; card đổi script / hook / định dạng ghi "Ai đọc tệp / định dạng này" và chạy một bộ đọc trên bản mới.
- **Hook an toàn khi nâng cấp / gỡ**: lệnh hook thoát 0 khi thiếu script; nâng cấp và gỡ phát hiện lệnh hook dạng cũ của bản 1.0 (gộp tay vào `settings.json`) và báo cần thay; gỡ giữ script mà lệnh cũ còn gọi; `--components` không có `hooks` thì không ghi mục hook.
- **Guard**: quy tắc chung khi một guard / hook bảo vệ chặn việc (cảnh báo đỏ, dừng, không lách, chỉ qua bằng `GUARD-OK <HHMM> "<lý do>"` do chủ dự án tự gõ); bật / tắt bằng `guard_rule_enabled`. Gói không kèm guard nào.
- **Văn phong**: viết báo cáo / tài liệu dùng skill loại tài liệu rồi skill văn phong (`writing_style_skill`) nếu đã cài; không có thì tự soát 5 điểm.
- **Nhật ký thời gian**: `steplog purge` mặc định giữ 90 ngày.
- **install.py**: cài mọi hook trong `hooks/` (trừ tệp test); nâng cấp từ 1.0 thay tệp của gói chưa ai sửa (có sao lưu), giữ tệp đã sửa; `CLAUDE.md` có đoạn bản cũ → đoạn mới vào `.workflow/merge/`; khuôn mới `RULES-HISTORY.md`.
- **Khóa config mới**: `roles.SECRETARY`, `roles.REVIEW_S`, `report`, `docs.publish_windows`, `context`, `limits`, `guard_rule_enabled`, `writing_style_skill`; đổi mặc định `gate.hosts` = `["ps7"]`, `steplog.purge_days` = 90.
- **An toàn hook**: lệnh hook trong `settings.json` thoát 0 khi thiếu script (không bao giờ chặn prompt); `--components` không có `hooks` thì không ghi mục hook; gỡ cài đặt bỏ các mục hook do gói thêm, khối hook gộp tay được giữ và cảnh báo.
- `q-wf-team`: chi tiết chuyển sang `references/` (`quy-tac-bo-sung.md`, `xac-nhan-va-qa.md`) để `SKILL.md` gọn.

## 1.0 (bản đầu)

- Sửa sau kiểm tra lần 1: gỡ cài đặt chỉ xóa / khôi phục file còn đúng SHA-256 lúc cài (file đã sửa sau khi cài được giữ, không bị bản sao lưu chép đè); bản ghi cài đặt ghi từng bước để gỡ được sau một lần cài dở; config mẫu và ví dụ dùng tên vai trò trung tính.

- 3 skill tiếng Việt: `q-wf-team` (mọi phiên), `q-wf-lead` (trưởng nhóm, sprint, retro), `q-wf-card` (card / vé).
- `AGENTS.md` dạng chung, `DOC-TRUOC.md` làm điểm vào cho mọi công cụ AI.
- 10 script PowerShell (ticket, checkpoint, manifest, gate, release, intake, board, stale, steplog + module chung) đọc mọi đường dẫn, vai trò, bản đồ phiên, đường dẫn bảo vệ / dùng chung từ `.workflow/workflow.config.json`; có test chạy trên PowerShell 5.1 và 7. Có đóng vé REVIEW lỗi thời (`STALE`).
- Hook `turnlog.py` ghi giờ lượt vào `paths.process_log`.
- Khuôn: đoạn chèn `CLAUDE.md`, `ROLES`, `NAMES`, card, board / INBOX / backlog / sprint / retro, hàng đợi và ghi chú vai trò, chính sách mặc định.
- `install.py`: mặc định chạy thử, kiểm SHA-256 gói, không ghi đè `CLAUDE.md` / `AGENTS.md` / settings, sao lưu, gỡ cài đặt.
- Giá trị trạng thái script giữ tên hiện tại (`SENT`, `MERGED`, `CLOSED`, `H-NN.json`); tên dễ đọc ghi trong `templates/NAMES.md`. Bản 1.1 sẽ theo đợt đổi tên trong script.
