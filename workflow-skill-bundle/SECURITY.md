# SECURITY — gói quy trình nhóm

## Gói làm gì và không làm gì

| Thành phần | Làm | Không làm |
|---|---|---|
| `install.py` | Kiểm SHA-256 gói theo `MANIFEST.json`; chép file vào thư mục đích; ghi bản ghi cài đặt; sao lưu file bị thay | Ghi ra ngoài `--target`; đi qua symlink / junction; ghi đè `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` đã có; dùng mạng; cài gói Python |
| Script PowerShell | Đọc / ghi trong thư mục dự án (card, vé, biên nhận, nhật ký); chạy test của card trong `gate` | Dùng mạng; push / merge / deploy; chép file khi release; chấp nhận ghi chú giống bí mật hay ID phiên trong vé / nhật ký |
| Script PowerShell (bản 1.1) | Chỉ chạy trên PowerShell 7; trên 5.1 từ chối bằng một dòng, không ghi gì | Chạy nửa chừng trên bản PowerShell không được hỗ trợ |
| `gate` | Quét bí mật trong file của zone (chỉ in file + dòng + luật, không in giá trị) | Bỏ qua bước kiểm; cho `PASS` khi chưa chạy đủ các bản trong `gate.hosts` |
| `turnlog.py` | Ghi một dòng (giờ, sự kiện, ID phiên, thư mục) mỗi lượt vào `paths.process_log/turns/` | Ghi nội dung prompt, transcript hay đầu vào công cụ; in ra màn hình; dùng mạng |
| Lệnh hook trong `settings.json` | Chạy hook nếu file có; thiếu file thì thoát 0, không in gì | Thoát mã 2 (mã chặn prompt) khi script đã bị xóa |
| Lệnh hook dạng cũ (v1.0) còn trong `settings.json` / `settings.local.json` | Nâng cấp và gỡ báo `lệnh hook dạng cũ (v1.0)`; gỡ giữ script mà lệnh đó gọi | Xóa script trong khi lệnh cũ còn gọi nó (lệnh cũ thoát mã 2, chặn mọi prompt) |
| `ctxwatch.py` | Mỗi lượt đọc config và phần cuối (≤ 256 KB) bản ghi hội thoại của chính phiên đó để lấy số token; vượt ngưỡng thì in một dòng nhắc | Ghi bất cứ tệp nào; đọc nội dung prompt hay tệp khác; chặn lượt; dùng mạng |
| Quy tắc guard (`AGENTS.md` § Guard) | Hướng dẫn phiên dừng, cảnh báo, chờ chủ dự án tự gõ mã xác nhận | Gói không kèm guard / plugin bảo vệ nào và không thay guard của tổ chức bạn |

## Lưu ý khi dùng

- `session_map_file` chứa ID phiên trên máy: giữ trong dự án, không đưa vào gói chia sẻ hay kho mã công khai.
- `process_log/` chứa giờ làm việc và ID phiên: không chia sẻ ra ngoài.
- Gói không kèm chính sách dữ liệu của tổ chức nào; đặt `policy_file` trỏ tới chính sách thật của bạn.
- Lệnh `-As <vai trò>` của script chỉ được ghi lại, không chứng minh được phiên nào gọi; quy trình dựa vào kỷ luật vai trò và vé, không phải cơ chế phân quyền.

## Báo lỗi bảo mật

Báo cho người bảo trì gói của tổ chức bạn; không đính kèm bí mật hay dữ liệu thật.
