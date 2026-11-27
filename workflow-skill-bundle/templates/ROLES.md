# Vai trò (ROLES)

Bảng này cho biết mỗi vai trò làm gì và được ghi vào đâu. Mỗi vai trò gắn với một phiên làm việc (xem `workflow.config.json`, mục `roles`). Sửa tên phiên, mô hình và vùng ghi cho đúng dự án.

| Vai trò | Phiên | Việc làm | Chỉ được ghi | Gợi ý mô hình |
|---|---|---|---|---|
| DOCS | `<tên phiên DOCS>` | Viết tài liệu quy trình, đặc tả, mẫu; cài các tệp đã phát hành vào đường dẫn dùng chung / được bảo vệ | `AGENTS.md`, `CLAUDE.md`, `.claude/`, `docs/process/` (trừ `STATUS.md`, `PROGRESS.md`, `roles/`), `docs/cards/README.md`, `docs/cards/_TEMPLATE/`, `scripts/process/` | `<mô hình mạnh>`; thiết kế khó → mô hình mạnh nhất |
| LEAD | `<tên phiên LEAD>` | Viết thẻ (card), gửi vé (ticket), là cổng phát hành duy nhất; câu duyệt phát hành / đường dẫn được bảo vệ chỉ gõ trong phiên này; chạy sprint hằng tuần (lập kế hoạch, báo cáo tuần, retro) | `lead/`, `docs/process/STATUS.md`, `docs/process/PROGRESS.md` (do script tạo), `docs/cards/<thẻ>/` (CARD.md và các vé của thẻ) | `<mô hình mạnh>` |
| SECRETARY | `<tên phiên SECRETARY>` | Kênh với chủ dự án: nhận câu trả lời và `OK / NG CONFIRM-…`, chuyển nguyên văn cho LEAD; ghi INBOX; báo cáo gom mỗi giờ; dòng nhắc dọn phiên. Không có phiên này thì LEAD làm | `lead/INBOX.md`, tệp xác nhận | mô hình vừa |
| BUILD | `<tên phiên BUILD>` (+ các phiên phụ `BUILD_M`, `BUILD_S` nhận từng phần) | Làm đúng một thẻ | vùng ghi của thẻ trong `<task>/out/`; phiên phụ chỉ ghi `out/_m/<phần>/`, `out/_s/<phần>/` | việc quan trọng → mô hình mạnh; việc rõ ràng, lặp lại → mô hình nhỏ hơn |
| REVIEW | `<tên phiên REVIEW>` | Đọc đúng một bản đóng băng (manifest), không sửa gì | `<task>/qa/` | việc quan trọng → mô hình mạnh nhất; giao diện / vận hành → mô hình mạnh |
| REVIEW_S | `<tên phiên QA nhẹ>` | QA nhẹ (`LIGHT`): chạy script kiểm có sẵn trên bản cuối, soát tài liệu nội bộ; không sửa gì | `<task>/qa/` | mô hình vừa |
| OPS | `<tên phiên OPS>` | Chỉ chạy các bước vận hành đã có (kiểm tra cài đặt, script dọn rác, chạy gate) | ghi chú chạy trong `<task>/qa/ops/` | mô hình nhỏ |

## Quy tắc chung

- Phiên điều khiển chung (nếu có) nằm ngoài luồng thẻ.
- Các vai trò khác LEAD / SECRETARY không hỏi chủ dự án. Báo cáo gửi LEAD kết thúc bằng dòng `Đã báo LEAD lúc <HH:MM>`. Phiên phụ báo cáo từng phần cho phiên đã giao phần đó.
- Mỗi phiên nhận việc giữ danh sách việc riêng `roles/QUEUE_<VAI_TRÒ>.md` (chỉ phiên đó ghi).
- Mỗi vai trò ghi bài học của mình vào `roles/NOTES_<VAI_TRÒ>.md`. Bộ nhớ của công cụ chỉ giữ con trỏ tới tệp này.
- **Đổi phiên cho cùng một vai trò** (phiên khác nhận thay): phiên cũ dừng hẳn; phiên mới giữ nguyên thư mục, thẻ và vé, rồi ghi thêm vào `log.md`: `<phiên> as <VAI_TRÒ> took over <thẻ> at <mã băm bản đóng băng>`.
- **Làm song song**: người làm thứ hai dùng vùng con riêng (`out/_m/`, `out/_s/`); chủ thẻ chép kết quả về. Hai người không bao giờ ghi cùng một tệp. Vùng con không chạm vào đường dẫn được bảo vệ.
- Script card nhận `-As` LEAD, DOCS, BUILD, REVIEW, OPS; phiên QA nhẹ dùng `-As REVIEW`, SECRETARY không chạy lệnh card.
- Tên mô hình chỉ là gợi ý, không phải quyền hạn.
- Công cụ AI ngoài danh sách được phép: không dùng (xem tệp chính sách, khóa `policy_file`).
