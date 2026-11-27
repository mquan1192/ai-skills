# INBOX — việc cần chủ dự án

Chỉ SECRETARY ghi tệp này (dự án không có SECRETARY: LEAD ghi). Mỗi việc một dòng, có mã `INBOX-NN`; danh sách gửi chủ dự án đánh số `#1`, `#2` … kèm mã. Chủ dự án trả lời gom một lần, ví dụ: `#1 OK · #3 B`; SECRETARY chuyển nguyên văn cho LEAD. Câu duyệt phát hành (mục 1b) chỉ gõ trong phiên LEAD. Việc xong chuyển xuống mục "Đã xong hôm nay"; cuối ngày xóa.
Báo cáo gom mỗi giờ (phút `<:30>`, từ `<giờ>` đến `<giờ>`), chỉ khi có điều mới; chỉ báo ngay khi 🔴 (vi phạm chính sách, bị chặn, cần câu duyệt phát hành). Tối đa 3 việc chờ chủ dự án cùng lúc; việc mới xếp hàng ở mục "Đang xếp hàng".

Cập nhật: <dd/mm HH:MM>

## 1. Chủ dự án tự làm (LEAD không làm thay được)
| Mã | Việc | Cách làm |
|---|---|---|
| INBOX-NN | <việc> | <các bước hoặc lệnh> |

## 1b. Câu duyệt phát hành (🔴)
| # · Mã | Thẻ | Câu duyệt chủ dự án gõ trong phiên LEAD |
|---|---|---|
| INBOX-NN | <NNN-slug> | `<câu duyệt có sẵn, ghi đường dẫn được bảo vệ và mã băm>` |

## 2. Cần chủ dự án trả lời
Mỗi câu hỏi liệt kê các lựa chọn với Ưu / Nhược; lựa chọn khuyến nghị ghi đầu tiên, đánh dấu "(đề xuất)". Chủ dự án có thể trả lời "theo khuyến nghị".
| Mã | Câu hỏi | LEAD đề xuất |
|---|---|---|
| INBOX-NN | <câu hỏi> | <lựa chọn đề xuất + lý do ngắn> |

## 3. Chỉ để biết (LEAD đã tự quyết 🟢 / 🟡 — chủ dự án gạch nếu không đồng ý)
- <quyết định của LEAD, một dòng>

## Đang xếp hàng / tạm dừng
- <việc đang chờ vì đã đủ 3 việc chờ chủ dự án, hoặc đã tạm dừng theo lời chủ dự án>

## Đã xong hôm nay
- <dd/mm HH:MM> — <việc>: <kết quả, kèm câu trả lời của chủ dự án và ngày>

## Lệnh
Các lệnh chủ dự án cần chạy, mỗi lệnh một khối mã, ghi rõ mã INBOX-NN của việc đó.
