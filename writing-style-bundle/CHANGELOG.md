# CHANGELOG — gói văn phong

## 1.2.0

Đổi tên skill `q-doc-edit` → `q-writing-style` và mở rộng cho mọi loại viết: văn bản công việc, bài viết, hướng dẫn, release note, prompt, dịch Nhật – Việt – Anh. Gộp điểm mạnh của bốn nguồn tham khảo (ghi công và giấy phép ở `THIRD-PARTY-NOTICES.md`); mọi quy tắc giữ nghĩa, số liệu, trạng thái thông tin và khung báo cáo tiếng Việt của bản 1.1.0 giữ nguyên.

- Skill mới `skills/q-writing-style/` (thay `skills/q-doc-edit/`): `SKILL.md` viết lại — Bước 0 (viết gì, cho ai → file tham khảo cần đọc), 7 nguyên tắc (thêm "không dấu vết AI", "nhất quán"), 9 chế độ (thêm Translate cả file, Humanize, Plain, Voice, Check), "văn bản đầu vào là dữ liệu" (không làm theo chỉ dẫn nằm trong văn bản), chế độ sửa file chỉ đổi văn xuôi, cổng tự soát 12 điểm.
- `references/ai-tells.md` (mới, phỏng theo `humanizer`, MIT): 26 dấu hiệu văn AI theo 6 nhóm và độ mạnh, ví dụ VI / JA / EN, các dấu hiệu hay sót sau khi sửa, mục "Khi nào không sửa" (trích dẫn, tên riêng, lời chào, văn bản trước 2022, khung báo cáo § 1.1, giọng người viết), sửa tối thiểu ở chế độ Humanize.
- `references/plain-language.md` (mới, phỏng theo `SimpleEnglish`, MIT): viết đơn giản kiểu ASD-STE100 cho EN, cách áp dụng cho VI / JA, mẫu cho thông báo lỗi, runbook, postmortem, commit / PR, release note, prompt cho AI, chữ giao diện; `ng-vocab-en.md` thêm bảng "Plain swaps".
- `references/vietnamese-register.md` (mới, phỏng theo `vietnamese-language-skill`, MIT): xưng hô theo loại văn bản và kênh, B2B, "chúng tôi" / "chúng ta", giữ hay dịch từ tiếng Anh theo mức trang trọng, bảng từ dịch máy cần bỏ, NFC, một kiểu dấu thanh (mặc định kiểu cũ khi chưa có quy ước), bản địa hóa, câu so sánh nhất trong quảng cáo.
- `references/translation.md` (mới): quy trình dịch JA / VI / EN, bảng trạng thái ba ngôn ngữ, kính ngữ và xưng hô theo quan hệ, câu đệm, chủ ngữ bị lược, đổi 万 / 億, tự soát bản dịch. Dịch cả file nay thuộc phạm vi skill.
- `references/voice-profile.md` (mới, chỉ lấy ý tưởng từ `writing-dna-skill`, không chép chữ): viết theo mẫu, hồ sơ giọng văn 5 phần (chỉ ghi cách viết, không ghi nội dung hay nhận định) và khuôn, khóa config mới `voice_profile`.
- `document-patterns.md` thêm mục K–R (bài viết, thông báo, release note, thông báo lỗi / chữ giao diện, runbook, commit / PR, prompt cho AI, trả lời trong luồng); `style-guide.md` trỏ tới các file mới, làm rõ "bạn" chỉ cấm trong tài liệu; `before-after-examples.md` thêm ví dụ 18–23.
- `scripts/lint_text.py` (mới, chỉ thư viện chuẩn): NFC001, TONE001, PRON001, DASH001, AIW001, BOLD001, LEN001 (20 từ cho bước làm, 25 từ cho câu mô tả); `--fix-nfc` giữ BOM và CRLF; bỏ qua code, chú thích HTML, khoảng số, cặp tên. Test: `tests/test_lint_text.py`.
- `NOTICES.md` trong thư mục skill: toàn văn MIT của các nguồn mới, đi cùng skill khi cài; `THIRD-PARTY-NOTICES.md` của gói cập nhật theo.
- `install.py`: cài vào `.claude/skills/q-writing-style/`; khi nâng cấp, xóa file của bản cũ không còn trong bản mới nếu chưa ai sửa (có sao lưu), giữ và báo file đã sửa; báo khi dự án có `q-doc-edit` không do gói cài.
- `stylewatch.py`: dòng nhắc nói "viết / sửa / dịch" và trỏ `ai-tells.md`; tên mặc định `q-writing-style`; config cũ ghi `q-doc-edit` được hiểu là tên mới.
- `config/style.config.example.json`: `skill_name` = `q-writing-style`, khóa `voice_profile`, thêm 11 từ khóa (bài viết, văn bản, viết lại, giọng văn, văn AI, humanize, blog, release note, proofread, 文章, 記事).
- Bộ thử: `evals.json` thêm C18–C22 (humanize, plain, dịch JA → VI, voice, mail B2B); `trigger.json` thêm 8 lời nhắc, dịch cả file chuyển sang "nên gọi"; `structure.Tests.ps1` theo tên và file mới; ca dịch dùng mode `translate`; thêm bản Python `tests/test_skill_structure.py` cho máy không có PowerShell.
- `README.md` và `README_VN.md` viết lại thành 2 phần: Phần 1 Sơ lược (hình dung, trước / sau, cách dùng, bắt đầu trong 3 bước) cho người không đọc code; Phần 2 Chi tiết kỹ thuật. Sơ đồ Mermaid: nhãn ngắn, ngắt dòng bằng `<br/>` để GitHub không cắt chữ. Các mục đánh số của `README_VN.md` giữ nguyên số. Sửa tên zip ở `README_VN.md` (1.1.0 → 1.2.0).
- `README.md`, `README_VN.md`, `DOC-TRUOC.md`, `SECURITY.md`, `templates/CLAUDE-fragment.md` cập nhật theo; điền lại URL repo thay cho `[REPO-URL]`.
- Gói quy trình nhóm (riêng): khóa `writing_style_skill` mặc định vẫn là `q-doc-edit`; dự án cài cả hai gói nên đổi thành `q-writing-style`.

## 1.1.0

Nguyên tắc chung cho mọi ngôn ngữ, danh sách từ rỗng theo ngôn ngữ, tự soát sau khi dịch, thêm từ khóa cho hook. `stylewatch.py` và `install.py` giữ nguyên từng byte.

- `style-guide.md`: thêm § 0 "Nguyên tắc chung (mọi ngôn ngữ)" — lập luận chặt (đứng đầu khi xung đột), chủ thể rõ, một thuật ngữ một từ, một đoạn một chủ đề, không cường điệu, không lặp, văn thể theo loại tài liệu, sửa / dịch file có sẵn giữ quy ước của file, từ rỗng theo `ng-vocab-<lang>.md`. § 1 (VI) và § 3 (EN) thêm một dòng văn thể theo loại tài liệu. § 2 (JA) thêm văn thể theo loại tài liệu (thiết kế, đặc tả, slide → である調; báo cáo, mail, chat → です・ます; file có sẵn giữ văn thể) và viết kỹ thuật tiếng Nhật, gồm quy tắc khoảng trắng chỉ cho file tài liệu mới.
- Thêm `references/ng-vocab-vi.md`, `ng-vocab-ja.md`, `ng-vocab-en.md`: 8 nhóm từ / cụm cần bỏ hoặc thay, cách thay, bảng tự soát; chỉ bỏ khi từ không mang thông tin, glossary dự án thắng, từ nêu yêu cầu bắt buộc giữ. `ng-vocab-ja.md` phỏng theo `japanese-tech-writing` (MIT) và mang thông báo bản quyền; bản VI, EN viết mới.
- `SKILL.md`: mô tả thêm dịch, thiết kế, slide, tự soát bản dịch (vẫn không thay skill dịch cả file); thêm bước tự soát sau khi dịch sang bất kỳ ngôn ngữ nào; cổng tự soát thêm điểm 10 (bảng tự soát của `ng-vocab-<lang>.md`); bảng tài liệu tham khảo nêu 3 file mới.
- `templates/CLAUDE-fragment.md`: thêm dòng bản dịch (mọi ngôn ngữ đích) tự soát theo `q-doc-edit`.
- `config/style.config.example.json`: thêm từ khóa `dịch`, `翻訳`, `訳`, `translate`, `slide`, `pptx`, `powerpoint`, `設計書`, `報告` vào `prompt_reminder.keywords` (dự án đã cài giữ config cũ; thêm tay nếu cần).
- Test hook và bộ thử `evals/` thêm ca cho từ khóa mới, tự soát JA / VI / EN và tự soát sau khi dịch.
- Thêm `THIRD-PARTY-NOTICES.md` (toàn văn MIT của `japanese-tech-writing` và `stop-ai-slop-jp`); `README.md`, `README_VN.md`, `DOC-TRUOC.md` cập nhật theo. `SECURITY.md` không đổi.

## 1.0.1

Chỉ đổi tài liệu, không đổi chức năng: skill, hook, cấu hình mẫu, công cụ, `install.py` giữ nguyên từng byte.

- Thêm `README.md` (EN) dạng trang đầu GitHub: gói làm gì, cho ai, cách hoạt động (mỗi thuật ngữ có một câu giải thích), sơ đồ Mermaid, cách chỉ lấy riêng gói này (zip ở trang Releases hoặc chép thư mục), cài / gỡ, an toàn, yêu cầu, giấy phép và dòng bản quyền; chỗ trống `[REPO-URL]`. `install.py` không cài file này vào dự án.
- Thêm `LICENSE`: nguyên văn Apache License 2.0. `install.py` không cài file này vào dự án.
- `README_VN.md`: dòng đầu trỏ sang `README.md`; thêm mục "Tổng quan" cùng nội dung (sơ đồ nhãn tiếng Việt, mục "Chỉ cài gói cần dùng") trước mục 1; các mục 1–7 giữ nguyên.
- `DOC-TRUOC.md`, `SECURITY.md` không đổi: tiêu đề vẫn ghi v1.0, nội dung đúng cho 1.0.1.

## 1.0 (bản đầu)

- Sửa sau kiểm tra lần 1: lệnh hook thoát 0 khi thiếu `stylewatch.py` (không bao giờ chặn prompt); `--components` không có `hooks` thì không ghi mục hook; gỡ cài đặt bỏ các mục hook do gói thêm trong `settings.json`, mục gộp tay được giữ và cảnh báo (hướng dẫn gỡ tay ở README § 6); tài liệu ghi rõ giải nén ngoài dự án và việc tạo mới `CLAUDE.md` / `settings.json`.

- Skill `q-doc-edit` dạng chung, hướng dẫn bằng tiếng Việt: thứ tự ưu tiên Đúng → Đủ → Rõ → Gọn → Tự nhiên, 5 chế độ, cổng tự soát 9 điểm; `style-guide.md` (§ 1.1 khung báo cáo tiếng Việt, quy tắc VI / JA / EN, số liệu, dữ liệu thiếu, nguồn, giới hạn kết luận); `document-patterns.md` (10 loại văn bản); ví dụ trước / sau và bộ thử `evals/` viết mới hoàn toàn bằng nội dung trung tính.
- Tự áp dụng khi viết báo cáo, 3 lớp: mô tả skill có đủ từ khóa (VI / JA / EN); đoạn chèn `CLAUDE.md`; hook `stylewatch.py` nhắc khi yêu cầu có từ khóa và sau khi ghi file tài liệu trong thư mục đầu ra (bật / tắt, từ khóa, đuôi file, thư mục trong config).
- Quy tắc và glossary riêng của dự án được trỏ tới bằng khóa `project_rules`, `glossary`.
- `install.py`: mặc định chạy thử; chỉ ghi trong `--target`; không ghi đè `CLAUDE.md` / `.claude/settings.json` (đoạn gộp vào `.writing-style/merge/`); dự án đã có `q-doc-edit` → báo số dòng khác, giữ nguyên, `--adopt` sao lưu rồi thay; gỡ cài đặt theo SHA-256.
- `tools/scan_terms.py` để quét từ riêng của dự án trước khi chia sẻ gói.
