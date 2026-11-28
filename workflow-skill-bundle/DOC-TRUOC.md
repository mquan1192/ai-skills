# ĐỌC TRƯỚC — gói quy trình nhóm (workflow skill bundle) v1.1

Gói này đưa một quy trình làm việc nhóm cho nhiều phiên AI (một trưởng nhóm, các phiên làm, một phiên kiểm) vào một dự án bất kỳ. Mọi hướng dẫn viết bằng tiếng Việt; mã lệnh, tên trạng thái và tên file giữ nguyên dạng gốc.

## Gói gồm gì

| Phần | Nội dung |
|---|---|
| `AGENTS.md` | Hợp đồng card / vé cho code và script (công cụ AI nào cũng đọc được) |
| `skills/q-wf-team` | Quy trình chung cho mọi phiên: vai trò (có thư ký, QA nhẹ), vùng ghi, mức duyệt, bàn giao, báo cáo, QA, context, guard (`references/`) |
| `skills/q-wf-lead` | Việc của trưởng nhóm: board, INBOX, backlog, sprint 1 tuần, retro |
| `skills/q-wf-card` | Luồng card / vé từng bước bằng script |
| `scripts/` | 10 script PowerShell 7 (`pwsh`) + test |
| `hooks/` | `turnlog.py`: ghi giờ bắt đầu / kết thúc mỗi lượt (không ghi nội dung) · `ctxwatch.py`: nhắc khi context vượt ngưỡng (không ghi gì) |
| `templates/` | Đoạn chèn `CLAUDE.md`, `ROLES`, `NAMES`, `RULES-HISTORY`, khuôn card, file của trưởng nhóm, hàng đợi / ghi chú vai trò, chính sách mặc định |
| `config/workflow.config.example.json` | Mọi giá trị riêng của dự án: đường dẫn, tên / ID / model phiên, cách gọi chủ dự án, file chính sách, ngưỡng context, giờ báo cáo / phát hành, bật / tắt quy tắc guard |
| `docs/` | Sơ đồ quy trình, ví dụ chạy trên dự án mẫu "demo" |
| `install.py` | Cài / gỡ; mặc định chỉ chạy thử, cần `--apply` mới ghi |

## Thứ tự đọc

1. File này.
2. `README_VN.md` — cách cài, cấu hình, gỡ.
3. `docs/quy-trinh.md` — sơ đồ quy trình (1 trang).
4. Theo vai trò: mọi phiên đọc `skills/q-wf-team/SKILL.md`; trưởng nhóm thêm `q-wf-lead`; ai làm code / script thêm `q-wf-card` và `AGENTS.md`.

## Hướng dẫn cho AI (khi được giao cài gói này)

1. Giải nén gói ra **ngoài** thư mục dự án, rồi đọc file này, `README_VN.md` và `SECURITY.md`. Gói nằm trong thư mục dự án thì `install.py` dừng.
2. Chạy thử: `python install.py --target <thư mục dự án>` (không ghi gì; máy không có lệnh `python` thì dùng `python3` hoặc `py -3`, bộ cài tự ghi lệnh chạy được vào lệnh hook). Đọc kế hoạch: file sẽ ghi, xung đột, phần gộp.
3. Trình chủ dự án kế hoạch đó (số file, xung đột, những gì đi vào `.workflow/merge/`, và việc **tạo mới** `CLAUDE.md` / `AGENTS.md` / `.claude/settings.json` khi dự án chưa có — có hiệu lực ngay) và hỏi có cài không.
4. Chỉ khi chủ dự án đồng ý: `python install.py --target <thư mục dự án> --apply`.
5. Sau khi cài: trình chủ dự án các đoạn trong `.workflow/merge/` (đoạn `CLAUDE.md`, `AGENTS.md`, khối hook); chỉ chèn vào tệp thật khi chủ dự án duyệt từng đoạn. Sửa `.workflow/workflow.config.json` theo dự án (tên phiên, ngưỡng, `guard_rule_enabled`).
6. Không tự sửa `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` đã có của dự án; không cài thêm gói nào khác.

## Nâng cấp từ bản 1.0

- Chạy lại `install.py` như trên. Tệp của gói chưa ai sửa được thay bằng bản mới (sao lưu bản cũ vào `.workflow/backup/`); tệp chủ dự án đã sửa được giữ nguyên và báo là xung đột.
- `CLAUDE.md` có đoạn của bản 1.0 → không sửa; đoạn mới nằm trong `.workflow/merge/CLAUDE-fragment.md` để thay bằng tay.
- Khối hook bản 1.0 đã gộp tay vào `.claude/settings.json` → installer báo `lệnh hook dạng cũ (v1.0)`. Thay các mục đó bằng khối trong `.workflow/merge/hooks.json` (lệnh cũ thoát mã 2 khi thiếu script, có thể chặn mọi prompt; lệnh mới thoát 0), rồi khởi động lại phiên. Chưa thay mà gỡ gói thì lệnh gỡ giữ script hook lại (README_VN.md § 6).
- Config cũ được giữ; thêm bằng tay các khóa mới của bản 1.1 (xem `CHANGELOG.md`).
- Vé, card, nhật ký cũ không cần sửa: script ghi tên mới và vẫn đọc tên cũ.

## Giới hạn đã biết

- Hook chỉ chạy được trên công cụ có hỗ trợ hook kiểu Claude Code; công cụ khác vẫn dùng được skill, `AGENTS.md` và script.
- Lệnh hook của bản 1.1 thoát 0 khi thiếu script (không chặn prompt); gỡ cài bỏ các mục hook do gói tạo, khối gộp tay chỉ được cảnh báo (README_VN.md § 6).
- Script cần PowerShell 7 (`pwsh`); Windows PowerShell 5.1 bị từ chối bằng một dòng `REFUSED: …`.
- Gói không kèm guard / plugin bảo vệ nào; chỉ có quy tắc chung khi một guard chặn (`AGENTS.md` § Guard, tắt bằng `guard_rule_enabled`).
- Gói không kèm chính sách AI của tổ chức nào: `policy_file` trong config trỏ tới file chính sách của bạn (mặc định `templates/POLICY.default.md`).
