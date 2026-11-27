# SECURITY — gói văn phong

## Gói làm gì và không làm gì

| Thành phần | Làm | Không làm |
|---|---|---|
| `install.py` | Kiểm SHA-256 gói theo `MANIFEST.json`; chép file vào thư mục đích; ghi bản ghi cài đặt; sao lưu file bị thay; **tạo mới** `CLAUDE.md` và `.claude/settings.json` khi dự án chưa có (hook có hiệu lực ngay; chạy thử in rõ dòng này); khi gỡ: bỏ các mục hook do gói thêm | Ghi ra ngoài `--target`; đi qua symlink / junction; ghi đè `CLAUDE.md`, `.claude/settings.json` đã có; thay skill `q-writing-style` đã có khi không có `--adopt`; xóa file đã sửa sau khi cài (khi nâng cấp chỉ xóa file cũ của gói còn đúng SHA-256, có sao lưu); dùng mạng; cài gói Python |
| Lệnh hook trong `settings.json` | Chạy `stylewatch.py` nếu file có; thiếu file thì thoát 0, không in gì | Thoát mã 2 (mã chặn prompt) khi script đã bị xóa |
| `stylewatch.py` | Đọc config và dữ liệu hook (nội dung yêu cầu, đường dẫn file vừa ghi) để quyết định có in một dòng nhắc | Ghi bất cứ tệp nào; lưu hay in lại nội dung yêu cầu / nội dung file; chặn lượt hay chặn việc ghi file; dùng mạng |
| Skill `q-writing-style` | Hướng dẫn AI viết, sửa, dịch văn bản tại chỗ; coi văn bản đầu vào là dữ liệu, không làm theo chỉ dẫn nằm trong đó | Gửi văn bản ra dịch vụ bên ngoài; tìm trên Internet khi chỉ được nhờ sửa hoặc dịch văn bản; lập hồ sơ giọng văn để giả danh người khác |
| `scripts/lint_text.py` | Đọc file được chỉ định, in gợi ý (dòng, mã quy tắc); `--fix-nfc` ghi lại đúng file đó ở dạng NFC | Ghi file khác; dùng mạng; ghi log |
| `tools/scan_terms.py` | Tìm từ riêng của dự án, đường dẫn tuyệt đối, ID phiên, email trong thư mục / zip trước khi chia sẻ | In giá trị khớp với mẫu có sẵn (chỉ in nhãn) |

## Lưu ý khi dùng

- Danh sách từ riêng của dự án dùng cho `scan_terms.py` để ngoài gói, không đưa vào bản chia sẻ.
- Ví dụ thêm vào `references/before-after-examples.md` chỉ dùng nội dung trung tính hoặc đã được phép; không đưa dữ liệu khách hàng hay dữ liệu nhạy cảm.
- Hook chỉ là lời nhắc; nó không bảo đảm văn bản đã được soát.

## Báo lỗi bảo mật

Báo cho người bảo trì gói của tổ chức bạn; không đính kèm bí mật hay dữ liệu thật.
