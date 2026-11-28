# ĐỌC TRƯỚC — gói văn phong (writing style bundle) v1.2

Gói này đưa skill văn phong `q-writing-style` vào một dự án bất kỳ, kèm đoạn chèn `CLAUDE.md` và hook nhắc, để AI tự áp dụng văn phong mỗi khi viết, sửa hoặc dịch văn bản: báo cáo, tài liệu, mail, biên bản, chat, ticket, bài viết, hướng dẫn, release note, prompt. Mọi hướng dẫn viết bằng tiếng Việt; mã lệnh, khóa cấu hình và tên file giữ nguyên dạng gốc.

## Gói gồm gì

| Phần | Nội dung |
|---|---|
| `skills/q-writing-style/` | Skill văn phong: `SKILL.md`, `references/style-guide.md` (§ 0 nguyên tắc chung mọi ngôn ngữ, § 1.1 báo cáo tiếng Việt), `references/ng-vocab-vi.md` / `ng-vocab-ja.md` / `ng-vocab-en.md` (từ rỗng và bảng tự soát theo ngôn ngữ), `references/document-patterns.md`, `references/ai-tells.md` (dấu vết văn AI), `references/plain-language.md` (viết đơn giản), `references/vietnamese-register.md` (xưng hô, từ tiếng Anh, NFC), `references/translation.md` (dịch JA / VI / EN), `references/voice-profile.md` (giọng văn), `references/before-after-examples.md`, `scripts/lint_text.py` (kiểm máy), `NOTICES.md`, bộ thử `evals/` |
| `templates/CLAUDE-fragment.md` | Đoạn chèn `CLAUDE.md`: viết báo cáo / tài liệu → skill loại tài liệu → `q-writing-style` → tự soát trước khi ghi file |
| `hooks/stylewatch.py` | Hook nhắc một dòng: khi yêu cầu có từ khóa báo cáo / tài liệu / dịch / slide, và sau khi ghi file tài liệu trong thư mục đầu ra |
| `config/style.config.example.json` | Bật / tắt, từ khóa, đuôi file, thư mục đầu ra, quy tắc và glossary riêng của dự án |
| `tools/` | `scan_terms.py` (tìm từ riêng của dự án trước khi chia sẻ), `make_manifest.py` |
| `install.py` | Cài / gỡ; mặc định chỉ chạy thử, cần `--apply` mới ghi |
| `THIRD-PARTY-NOTICES.md` | Thông báo bản quyền và giấy phép MIT của nội dung bên thứ ba được phỏng theo (không cài vào dự án; `ng-vocab-ja.md` mang sẵn thông báo này) |

## Hướng dẫn cho AI (khi được giao cài gói này)

1. Giải nén gói ra **ngoài** thư mục dự án (ví dụ một thư mục tạm), rồi đọc file này, `README_VN.md` và `SECURITY.md`. Gói nằm trong thư mục dự án thì `install.py` dừng.
2. Chạy thử: `python install.py --target <thư mục dự án>` (không ghi gì; máy không có lệnh `python` thì dùng `python3` hoặc `py -3`, bộ cài tự ghi lệnh chạy được vào lệnh hook). Đọc kế hoạch: file sẽ ghi, file bỏ qua, xung đột (kể cả skill `q-writing-style` đã có và số dòng khác), phần gộp, và dòng "chưa có → tạo từ gói" của `CLAUDE.md` / `.claude/settings.json`.
3. Trình chủ dự án kế hoạch đó và hỏi có cài không; nói rõ nếu installer sẽ **tạo mới** `CLAUDE.md` hoặc `.claude/settings.json` (khi dự án chưa có): đoạn văn phong và hook có hiệu lực ngay, không qua bước duyệt đoạn gộp. Không muốn hook → cài với `--components skills,docs`. Dự án đã có `q-writing-style` riêng → nêu rõ, đề xuất giữ bản của dự án hoặc thay bằng `--adopt` (có sao lưu). Nâng cấp từ bản trước 1.2.0: kế hoạch có dòng "- … q-doc-edit … → xóa, có sao lưu" (file cũ của gói chưa ai sửa) và "! … giữ nguyên" (file đã sửa); trình chủ dự án cả hai. Dự án có gói quy trình nhóm: nhắc đổi khóa `writing_style_skill` thành `q-writing-style`.
4. Chỉ khi chủ dự án đồng ý: `python install.py --target <thư mục dự án> --apply`.
5. Sau khi cài: trình chủ dự án hai đoạn trong `.writing-style/merge/` (đoạn `CLAUDE.md`, khối hook cho `.claude/settings.json`) nếu có; chỉ chèn vào tệp thật khi chủ dự án duyệt từng đoạn. Điền `project_rules`, `glossary`, `file_reminder.output_dirs` trong `.writing-style/style.config.json`.
6. Kiểm nhanh: gõ một yêu cầu có chữ "báo cáo" → AI nhận một dòng nhắc `[văn phong] …`.
7. Không tự sửa `CLAUDE.md`, `.claude/settings.json` đã có của dự án; không cài thêm gói nào khác.

## Thứ tự đọc

1. File này.
2. `README_VN.md` — cách cài, cấu hình, gỡ.
3. `skills/q-writing-style/SKILL.md` — skill văn phong.

## Giới hạn đã biết

- Hook chỉ chạy trên công cụ có hỗ trợ hook kiểu Claude Code; công cụ khác vẫn dùng được skill và đoạn chèn `CLAUDE.md`.
- Hook chỉ nhắc, không sửa văn bản và không chặn việc ghi file; việc áp dụng văn phong do AI làm theo skill.
- Từ khóa so khớp đơn giản (chứa chuỗi, không phân biệt hoa thường): yêu cầu như "đọc báo cáo này" cũng nhận dòng nhắc.
