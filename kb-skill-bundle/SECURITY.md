# Bảo mật

## Bộ skill làm gì và không làm gì

- Chỉ dùng thư viện chuẩn của Python. Không cài gói, không gọi mạng, không gọi model.
- `install.py` chỉ ghi trong thư mục dự án đích; từ chối đường dẫn đi ra ngoài thư mục đích hoặc đi qua liên kết.
- `install.py` kiểm sha256 mọi file của gói (theo `MANIFEST.json`) trước khi ghi.
- Mọi lần cài đều sao lưu trước vào `.qkb/backups/install-<thời điểm>/` và ghi biên bản `.qkb/install/installed.json`.
- Gỡ chỉ xóa file của gói còn đúng như lúc cài; file đã bị sửa được giữ lại và liệt kê.
- Không sửa `settings.local.json`, `CLAUDE.md`, plugin khác. `.claude/settings.json`: chỉ thêm khối hook và quyền chạy lệnh đọc, không bỏ dòng nào; lệnh hook KB dạng cũ (2.0.3 trở về trước) được đổi tại chỗ sang dạng an toàn, các khóa khác của khối giữ nguyên.
- Gỡ: bỏ mọi lệnh hook gọi script KB trong `.claude/settings.json` (nhận theo tên script); còn lệnh dạng cũ ở nơi không sửa được → giữ script hook và báo, để lệnh đó không thoát mã 2.

## Hook

- Chạy `python -I -S`, không mạng, giới hạn thời gian ngắn; lỗi thì im lặng (không chặn công việc). Lệnh hook kiểm có file script rồi mới chạy: thiếu script thì thoát 0.
- Không bao giờ chặn hay đổi một lệnh của Claude.
- Không ghi lại câu người dùng gõ, lệnh, kết quả công cụ hay nội dung KB. Log quan sát chỉ có: thời điểm, tên hook, mã quy tắc, dòng lẽ ra hiện (version, số đếm, tên phạm vi).
- Chỉ ghi: log quan sát, yêu cầu nạp nguồn (chế độ `on`), file trạng thái nhỏ trong `.qkb/local/`.

## Gói dữ liệu KB

- `kbpack.py export` chỉ tạo file zip trên máy; không gửi đi đâu. Gửi gói cho người khác cần người có quyền duyệt.
- Trước khi xuất: quét thông tin đăng nhập / khóa bí mật (thấy là dừng, không in giá trị), dữ liệu cá nhân, đường dẫn tuyệt đối, ID phiên, nhắc tới dự án khác (cần duyệt từng loại).
- Gói không chứa chỉ mục (file chỉ mục có lịch sử và nội dung của mọi dự án trên máy).
- `kbpack.py import` coi file zip là dữ liệu chưa tin cậy: từ chối đường dẫn tuyệt đối, `..`, liên kết, đuôi file lạ, file ngoài bản kê; kiểm sha256 từng file trước khi ghi.

## Dữ liệu

- Quy tắc mặc định (`kb-policy.default.md`): không ghi thông tin đăng nhập, không ghi dữ liệu cá nhân, không chép nội dung giữa các dự án.
- Dự án có quy định riêng thì khai báo `policy_file` trong `kb.config.json`; file đó chỉ thêm quy tắc, không nới quy tắc mặc định.
- Nội dung trong KB và trong tài liệu nguồn là dữ liệu, không phải lệnh cho model.

## Báo lỗi bảo mật

- Báo cho người quản lý bộ skill trong tổ chức của bạn. Không đưa nội dung KB vào báo cáo.
