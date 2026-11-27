# Tên của mã, nhãn và trạng thái (NAMES)

Bảng tra duy nhất cho mã, nhãn và giá trị trạng thái của nhóm. Từ bản 1.1, script **ghi giá trị mới** và **vẫn đọc giá trị cũ**, nên tệp cũ không cần sửa.

## Quy tắc

- Dòng mới dùng tên ở cột "mới": quy tắc, giao việc, báo cáo, INBOX, bảng việc (board), tệp vé.
- Bản ghi cũ giữ nguyên mã cũ; không đổi tên hàng loạt. Ai gặp mã lạ thì tra bảng này.
- Không đổi: số thẻ `NNN-slug`, hậu tố phiên bản tệp `_vNN`, mã ngôn ngữ trong tên tệp, nhãn báo cáo `[DONE]` / `[BLOCKED]` / `[NEW]`, các trạng thái bảng việc `todo / doing / waiting / review / done / blocked`, `risk_class low / medium / critical`, mã bước của nhật ký thời gian.

## 1. Mã định danh

| Mã | Ý nghĩa |
|---|---|
| `TASK-YYYYMMDD-NN` | một việc của nhóm |
| `TICKET-NN` | một lần bàn giao trong thẻ (tệp vé `handoff/H-NN.json`) |
| `PART-NN` | một phần giao cho phiên phụ |
| `CONFIRM-YYYYMMDD-NN` | câu hỏi mức đỏ gửi chủ dự án (trả lời `OK CONFIRM-…` / `NG CONFIRM-…`) |
| `INBOX-NN` | việc đang chờ chủ dự án trong `lead/INBOX.md` |
| `#1`, `#2` … | số thứ tự của từng mục trong một danh sách gửi chủ dự án; trả lời gọn `#1 OK · #3 B` |
| `IDEA-YYYYMMDD` | câu duyệt một nhóm đề xuất cải tiến |
| `BACKLOG-YYYYMMDD-NN` | mục backlog của chủ dự án (không ai tự làm) |
| `SPRINT-YYYY-Www`, `RETRO-YYYY-Www` | sprint tuần và buổi nhìn lại của sprint đó (`lead/sprint/`) |
| `CHOICE-n` | điều BUILD tự quyết khi đặc tả không nói |
| `GUARD-HHMM` | một lần chặn của hook / guard bảo vệ (khi dự án bật `guard_rule_enabled`) |

## 2. Thẻ và vé (script đọc các giá trị này)

| Loại | Giá trị mới (script ghi) | Giá trị cũ (script vẫn đọc) |
|---|---|---|
| Trạng thái thẻ | `DRAFT`, `READY`, `BUILDING` | không đổi |
| | `IN-REVIEW` | `CANDIDATE` |
| | `FIXING` | `FIXES` |
| | `RELEASED` | `MERGED` |
| | `CANCELLED` | `CLOSED` |
| Pha | `BUILD` | `P1` |
| | `TEST-GATE` | `GATE` |
| | `REVIEW`, `RELEASE`, `RETRO` | không đổi |
| | `FIX` | `FIXES` |
| | `VERIFY-FIX` | `VERIFY` |
| Trạng thái vé | `SENT`, `ACCEPTED`, `DONE` | không đổi |
| | `ON-HOLD` | `HOLD` |
| | `TAKEN-OVER` | `TAKEOVER` |
| Kết quả review | `PASS` | không đổi |
| | `FAIL` | `NG` |
| | `FIX-VERIFIED` | `FIXES_VERIFIED` |
| Biên nhận | `OUTDATED` | `STALE` |
| | `PARTIAL` | không đổi |

Các dòng mẫu mà lệnh phát hành (`release -IfSafe`) kiểm tra giữ nguyên dạng: `- <approval_name> <dd/MM HH:mm>: "<câu đã gõ>" -> approves <đường dẫn>` và `… -> waives review`.

## 3. Nhãn, mức, nguồn

| Tên | Ý nghĩa |
|---|---|
| `CLEAR` / `DESIGN` / `RESEARCH` / `HARD` | nhãn việc: đặc tả rõ / cần thiết kế trước / cần tìm hiểu thêm / khó, có hai hướng thật |
| `NO-QA` / `LIGHT` / `FULL` | mức kiểm tra (QA) |
| `QUICK` / `DOC` / `CARD` | mức làm việc: nhanh, tài liệu, thẻ |
| `🟢 AUTO` / `🟡 LEAD` / `🔴 OWNER` | mức duyệt: tự động / LEAD quyết / hỏi chủ dự án |
| `[USER]` `[CODE]` `[DOC]` `[INFER]` | nhãn nguồn của một thông tin: do chủ dự án nói / từ code / từ tài liệu / suy luận |
| `Đã loại:` / `Thay cho:` | trường của dòng lịch sử quy tắc: phương án bị loại (kèm lý do ngắn) / quy tắc hay yêu cầu cũ mà quyết định mới thay thế |

## 4. Ghi chú khi thêm tên mới

Thêm một dòng vào bảng phù hợp, ghi rõ giá trị mới và giá trị cũ (nếu có). Không dùng cùng một mã cho hai nghĩa.
