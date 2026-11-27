# Thẻ (cards)

Một thẻ = một đơn vị việc về code / script = một mã `TASK-…` trên bảng việc `lead/board.md` (dòng của bảng trỏ tới đây; chi tiết nằm trong thẻ).

## Thư mục
```
docs/cards/<NNN>-<slug>/
  CARD.md            LEAD ghi
  baseline.manifest  chỉ ghi một lần: các tệp đích đang chạy lúc bắt đầu pha BUILD (do script ghi)
  handoff/H-NN.json  các vé (mỗi thẻ chỉ một vé đang mở); tên tệp khác trong handoff/ sẽ chặn thẻ
  receipts/gate.json do gate ghi
  log.md             các điểm dừng, chỉ thêm dòng mới
```
Sao chép `_TEMPLATE/` để bắt đầu. `NNN` = số tự do kế tiếp. Cách dùng script: `scripts/process/README.md`.

## Trạng thái thẻ
`DRAFT → READY → BUILDING → IN-REVIEW → FIXING → IN-REVIEW → RELEASED` (hoặc `CANCELLED` khi bỏ). Script ghi các giá trị này và vẫn đọc giá trị cũ (xem `docs/process/NAMES.md` § 2): `CANDIDATE` → `IN-REVIEW`, `FIXES` → `FIXING`, `MERGED` → `RELEASED`, `CLOSED` → `CANCELLED`. Chỉ LEAD đổi trạng thái; mỗi lần đổi thêm một dòng vào "State log" của thẻ.

## Các pha
`BUILD` (cũ: `P1`) → `TEST-GATE` (cũ: `GATE`) → `REVIEW` (bản đóng băng) → `FIX` (cũ: `FIXES`; một vòng) → `VERIFY-FIX` (cũ: `VERIFY`; REVIEW kiểm các chỗ đã sửa: `FIX-VERIFIED`, cũ `FIXES_VERIFIED`) → `RELEASE` (LEAD) → `RETRO` (cùng ngày, bài học ghi vào `roles/NOTES_<VAI_TRÒ>.md`).

## Vé `handoff/H-NN.json`
- Trường: `card, n, from, to, phase, manifest_digest, state, agent, history[]`; mỗi mục history `{at, by, state, note}`. Vé đã đóng băng có thêm `manifest` (các dòng manifest).
- Trạng thái vé: `SENT → ACCEPTED → DONE` (`ON-HOLD` để tạm dừng, cũ `HOLD`; `TAKEN-OVER` khi phiên khác nhận cùng vai trò, cũ `TAKEOVER`). REVIEW ghi kết quả vào `note`: `PASS`, `FAIL` (cũ: `NG`), `FIX-VERIFIED` (cũ: `FIXES_VERIFIED`). Vé gọi là `TICKET-NN`; tên tệp là `handoff/H-NN.json`.
- Vé REVIEW ở trạng thái `OUTDATED` (cũ: `STALE`; manifest đã đóng băng không còn khớp vùng ghi) có thể được đóng bằng `ticket done -Note 'OUTDATED …'`. Việc đóng này không có kết quả review, không được `release` / `intake` tính, và vé kế tiếp theo quy tắc thường (ví dụ LEAD gửi vé REVIEW mới với mã băm hiện tại).
- Mỗi thẻ chỉ có một vé đang mở (chưa `DONE`). Vé là căn cứ; tin nhắn chỉ là tiếng chuông.
- Tiếng chuông (4 dòng, dán hoặc gửi theo tên phiên; không ghi mã phiên vào vé hay lời giao việc):
```
[TICKET <thẻ> H-NN] <TỪ> → <ĐẾN> · <pha>
Card: docs/cards/<thẻ>/CARD.md (Takeover)
Ticket: docs/cards/<thẻ>/handoff/H-NN.json · manifest <12 ký tự đầu của mã băm>
Sent <dd/mm HH:MM> by <tên phiên>
```
- Việc có thẻ dùng vé thay cho tệp `HANDOFF-*.md`.

## Biên nhận gate
`receipts/gate.json`: `manifest_digest, tests, secrets, skipped, result, by, at`. PASS cần chạy test trên mọi môi trường cấu hình trong `gate.hosts` (mặc định chỉ `ps7`); thiếu một môi trường → PARTIAL (lệnh phát hành từ chối). Mã băm khác manifest hiện tại → `OUTDATED` (cũ: `STALE`).

## Không dùng git
`branches` → **vùng ghi** (zone): các đường dẫn ghi của thẻ (`<task>/out/…`, vùng con `out/_m/`, `out/_s/`). Mã commit → **mã băm bản đóng băng** (manifest digest).
- **Vùng ghi là một thư mục hoặc một tệp**: một tệp lẻ dưới `<task>/out/` cũng được băm, kiểm gate và review như một thư mục; `<task>/out/` tự nó không bao giờ là vùng ghi. Thẻ mà vùng ghi duy nhất là một tệp không phải test thì không qua được gate (không có `*.Tests.ps1`) → thêm một vùng test.
