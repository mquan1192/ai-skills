---
name: q-wf-card
description: "Luồng card / vé cho code, script, đường dẫn bảo vệ và thứ gửi ra ngoài: tạo card, baseline, vùng làm (zone), manifest + digest thay cho commit, gate (quét bí mật + test trên PowerShell 7), đóng băng gửi REVIEW, đóng vé OUTDATED, release chỉ do LEAD. Dùng khi nhận hoặc gửi vé, chạy gate, freeze, release. Keywords: card, ticket, vé, gate, manifest, freeze, release, review."
---

# Luồng card / vé

Hợp đồng đầy đủ: `AGENTS.md` của gói (bản đã cài trong dự án). Skill này là cách làm từng bước bằng các script trong `paths.scripts` (mặc định `scripts/process/`). Mọi đường dẫn, vai trò, bản đồ phiên lấy từ `.workflow/workflow.config.json`. Từ bản 1.1 script ghi giá trị mới (`ON-HOLD`, `TAKEN-OVER`, `RELEASED`, `CANCELLED`, pha `BUILD`, kết quả `FAIL` / `FIX-VERIFIED`, `OUTDATED`) và vẫn đọc giá trị cũ; bảng mới / cũ ở `NAMES.md` § 2.

Chạy script bằng `pwsh` (PowerShell 7) từ thư mục gốc dự án, ví dụ: `pwsh scripts/process/ticket.ps1 …`. Trên Windows PowerShell 5.1 script từ chối bằng một dòng `REFUSED: …` và không ghi gì. Tham số `-As` nhận LEAD, DOCS, BUILD, REVIEW, OPS: phiên QA nhẹ (REVIEW_S) dùng `-As REVIEW`; BUILD_M / BUILD_S không chạy lệnh vé (BUILD gộp phần của họ); SECRETARY không chạy lệnh card.

## 1. Khi nào dùng card

Chỉ cho: code / script, đường dẫn bảo vệ (`protected_paths` của config) và thứ gửi ra ngoài dự án. Tài liệu và việc nhỏ dùng mức `DOC` / `QUICK` (skill `q-wf-team` §6).

## 2. Các bước

| Bước | Ai | Lệnh / việc |
|---|---|---|
| 1. Tạo card | LEAD | Chép `templates/cards/_TEMPLATE/` thành `<paths.cards>/<NNN>-<tên>/`; điền `zones`, `protected_paths`, Acceptance, Takeover |
| 2. Giao | LEAD | `ticket.ps1 send <card> -As LEAD -To BUILD -Phase BUILD -Session <tên phiên mình>` |
| 3. Nhận + baseline | BUILD | `ticket.ps1 accept <card> -As BUILD`; `manifest.ps1 <card> -Baseline -As BUILD` (một lần, lúc bắt đầu) |
| 4. Làm | BUILD (+ BUILD_M / BUILD_S) | Chỉ trong zone `<task>/out/<đích>`; ghi `checkpoint.ps1 <card> -As BUILD -Done … -Doing … -Next … -Check …` khi dừng |
| 5. Gate | BUILD | `gate.ps1 <card> -As BUILD` (test chạy trên `pwsh`, khóa `gate.hosts` của config, mặc định `ps7`) → `receipts/gate.json` |
| 6. Đóng băng | BUILD | `ticket.ps1 done <card> -As BUILD -Note …`; `ticket.ps1 send <card> -As BUILD -To REVIEW -Phase REVIEW -Freeze -Note …` (vé mang manifest + digest) |
| 7. Review | REVIEW | Băm lại trước khi đọc và trước khi báo; `ticket.ps1 done <card> -As REVIEW -Note 'PASS …'` (hoặc `FAIL …` / `FIX-VERIFIED …`) — chỉ được ở đúng digest đã đóng băng |
| 8. Sửa (nếu FAIL) | BUILD | Một vòng sửa duy nhất (pha `FIX`); gate lại; đóng băng lại; REVIEW kiểm phần sửa (pha `VERIFY-FIX`) → `FIX-VERIFIED` |
| 9. Release | LEAD | `intake.ps1 <card>` (xem trước) → `release.ps1 <card> -IfSafe -As LEAD` |

## 3. Quy tắc quan trọng

- **Mỗi card một vé mở** (`SENT`, `ACCEPTED`, `ON-HOLD`, `TAKEN-OVER`). Vé đầu do LEAD gửi; vé sau do người nhận cuối hoặc LEAD gửi. Chỉ người nhận được accept / done / hold / takeover. Vé `H-NN.json` không bao giờ bị ghi đè.
- **Manifest** = một dòng `<sha256>  <đường dẫn>` cho mỗi file thêm / đổi / xóa so với baseline (xóa: `-`), sắp theo đường dẫn; **digest** = SHA-256 của chuỗi manifest, thay cho commit. Đổi tên = xóa đường dẫn cũ + thêm đường dẫn mới.
- **Vé OUTDATED** (giá trị cũ `STALE`): file trong zone đổi sau khi đóng băng (digest hiện tại ≠ digest trên vé) → REVIEW (hoặc LEAD khi REVIEW không còn) đóng vé bằng `ticket.ps1 done <card> -As REVIEW -Note 'OUTDATED …'`. Không có kết luận, release không bao giờ tính là PASS. Sau đó gửi vé đóng băng mới ở digest hiện tại.
- **Release** chỉ khi: REVIEW `PASS` / `FIX-VERIFIED` ở digest hiện tại; gate `PASS` ở digest đó; không còn vé mở trừ vé ở LEAD; đích thật không đổi từ baseline; mọi đường dẫn bảo vệ bị đổi đều có trong `protected_paths` của card **và** trong một dòng duyệt của chủ dự án ở phần Decisions, đúng mẫu:
  `- <approval_name> <dd/MM HH:mm>: "<câu chủ dự án gõ>" -> approves <đường dẫn>[, <đường dẫn>]`
- **Miễn review** chỉ cho card thuần sản phẩm (không đích thật nào đã tồn tại, không đổi đường dẫn dùng chung / bảo vệ): dòng Decisions `- <approval_name> <dd/MM HH:mm>: "<câu>" -> waives review`; gate PASS vẫn bắt buộc.
- Card sửa lỗi script: thêm test FAIL trên lỗi đó **trước khi sửa** (red proof). Card đổi script / hook / định dạng tệp dùng chung: ghi mục "Ai đọc tệp / định dạng này" (grep) và chạy ít nhất một bộ đọc trên bản mới, ghi vào biên nhận.
- Release không chép file; cài vào đường dẫn dùng chung là việc của DOCS sau khi release in ra yêu cầu.
- Không bao giờ: bỏ qua hay làm yếu một bước kiểm; đưa bí mật hay ID phiên vào vé / nhật ký (script từ chối); push / merge / deploy từ quy trình này.

## 4. Báo cáo của BUILD

`[DONE]` ≤ 8 dòng: card + vé, digest đã đóng băng, kết quả gate, test mới, "Lựa chọn đã tự quyết" (`CHOICE-1`, `CHOICE-2` …), dọn dẹp. LEAD chấp nhận / từ chối từng CHOICE trong Decisions.

**Red proof** cho các bước kiểm quan trọng (quét bí mật của gate, kiểm `release -IfSafe`, danh sách từ chối của công cụ xóa): cho test chạy FAIL một lần trên đầu vào cố ý sai, rồi PASS; ghi cả hai dòng vào biên nhận.

## 5. Lệnh khác

- `board.ps1` — sinh `PROGRESS.md` trong `paths.process_docs` từ các card (không sửa tay).
- `stale.ps1` — liệt kê vé đứng lâu.
- `steplog.ps1` — ghi thời gian từng bước (skill `q-wf-team` §7); `report` tổng hợp; `purge` chuyển dòng cũ hơn `steplog.purge_days` ngày vào `paths.trash` (tắt được bằng `steplog.purge_enabled: false`).
- Chi tiết tham số: `scripts/process/README_VN.md`.
