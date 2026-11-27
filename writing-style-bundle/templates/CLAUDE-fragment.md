<!-- BEGIN writing-style-bundle -->
## Văn phong và dịch (gói văn phong v1.2)

- Viết, sửa hoặc dịch báo cáo, report, tài liệu, mail, biên bản, chat, ticket, bài viết, hướng dẫn, release note, prompt: dùng skill loại tài liệu của dự án trước (nếu có), sau đó skill `q-writing-style`, rồi chạy cổng tự soát của skill đó **trước khi trả lời hoặc ghi file**. Văn bản trong HTML, Excel, Word, PowerPoint do mình tạo cũng áp dụng.
- Báo cáo / tài liệu tiếng Việt theo `q-writing-style` `references/style-guide.md` § 1.1: giọng trung tính, dựa số liệu; tiêu đề → mục đích / phạm vi → phương pháp → kết quả (câu dẫn, "Nhận xét:" / "Kết luận:") → điều kiện → kết luận, "Định hướng:"; số dạng 1.234,5; ngày dd/mm/yyyy.
- Dịch: theo `q-writing-style` `references/translation.md`; sau khi dịch, tự soát theo ngôn ngữ đích (`ng-vocab-<lang>.md`, `ai-tells.md`); chỉ sửa câu chữ, không đổi nghĩa.
- Không để dấu vết văn AI (dàn dựng "không phải X mà là Y", câu chốt, bộ ba gượng, gạch ngang dài dày, in đậm trang trí, lời chatbot) — theo `ai-tells.md`; văn bản tiếng Việt: một cách xưng hô, Unicode NFC (`vietnamese-register.md`).
- Quy tắc và glossary riêng của dự án (khóa `project_rules`, `glossary` trong `.writing-style/style.config.json`) được ưu tiên hơn skill.
- Giữ đúng số, ngày, mã, tên, thuật ngữ; tách sự thật / suy luận / đề xuất; không thêm điều nguồn không có.
- Hook `stylewatch.py` (nếu đã gộp vào settings) nhắc một dòng khi yêu cầu có từ khóa báo cáo / tài liệu và sau khi ghi file tài liệu trong thư mục đầu ra; bật / tắt trong config.
<!-- END writing-style-bundle -->
