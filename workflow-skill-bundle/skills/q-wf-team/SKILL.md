---
name: q-wf-team
description: "Quy trình làm việc nhóm cho mọi phiên AI trong dự án: vai trò, vùng ghi (mỗi file một người ghi), mức duyệt (tự động / trưởng nhóm / chủ dự án), khối xác nhận, bàn giao, báo cáo [DONE], mức QA, ngưỡng context, guard, ghi thời gian từng bước. Dùng khi bắt đầu một phiên nhóm, giao hoặc nhận việc, cần chủ dự án duyệt. Không dùng cho: điều phối sprint / INBOX của trưởng nhóm (q-wf-lead), luồng card / vé của code (q-wf-card). Keywords: bàn giao, handoff, quy trình nhóm, xác nhận, confirm, vùng ghi, context."
---

# Quy trình nhóm (mọi phiên)

Đọc `DOC-TRUOC.md` của dự án trước. Tên phiên, ID phiên, model, thư mục và cách gọi chủ dự án nằm trong `.workflow/workflow.config.json` (gọi tắt: *config*). Trong skill này, "chủ dự án" = giá trị `owner_name` của config. Quy tắc riêng của dự án (`CLAUDE.md`, `AGENTS.md`, file chính sách `policy_file`) luôn thắng skill này.

Skill liên quan: `q-wf-lead` (trưởng nhóm điều phối), `q-wf-card` (luồng card / vé cho code và script). Quy tắc chi tiết bổ sung từ bản 1.1 (biểu tượng, context, cỡ tệp, phát hành quy tắc, guard, văn phong): `references/quy-tac-bo-sung.md`.

## 1. Vai trò

| Vai trò (khóa trong config `roles`) | Việc | Chỉ ghi vào |
|---|---|---|
| LEAD | Chia việc, giao việc, theo dõi, gọi các phiên, quyết 🟡; cổng release duy nhất; dòng duyệt release / đường dẫn bảo vệ chỉ gõ trong phiên này | thư mục `paths.lead` (board, NOTICE, backlog, brief, sprint), `CARD.md`, `STATUS.md` |
| SECRETARY | Kênh với chủ dự án: nhận câu trả lời và `OK / NG CONFIRM-…` rồi chuyển **nguyên văn** cho LEAD; ghi INBOX; báo cáo gom mỗi giờ; dòng nhắc dọn phiên. Không có vai trò này trong config → LEAD làm | `paths.lead` / `INBOX.md`, tệp xác nhận |
| DOCS | Người ghi duy nhất của file dùng chung (quy tắc, khuôn, script quy trình) | các đường dẫn `shared_paths` |
| BUILD | Code, file có cấu trúc, sửa lỗi; **chia việc trước**: phần rõ ràng giao BUILD_M / BUILD_S, giữ phần khó; kiểm và gộp | `<task>/out/` (trừ `out/_m/`, `out/_s/`) |
| BUILD_M | Làm phần đã mô tả rõ do BUILD hoặc LEAD giao; không tự quyết thiết kế | `<task>/out/_m/<task>-<part>/` |
| BUILD_S | Làm phần thường lệ (chuyển dữ liệu, script nhỏ, sửa cơ học, dữ liệu test) do BUILD hoặc BUILD_M giao | `<task>/out/_s/<task>-<part>/` |
| REVIEW | Xem lại, kiểm, test độc lập (`FULL`); không tự sửa sản phẩm | `<task>/qa/` |
| REVIEW_S | QA nhẹ (`LIGHT`): chạy script kiểm có sẵn trên bản cuối, soát tài liệu nội bộ; cùng giới hạn như REVIEW | `<task>/qa/` |
| OPS | Kiểm cài đặt / môi trường (khi có) | `<task>/qa/install/` |

- Chuỗi giao việc: BUILD ← LEAD; BUILD_M ← BUILD hoặc LEAD; BUILD_S ← BUILD hoặc BUILD_M. Phần nào báo về đúng phiên đã giao phần đó.
- Phiên nhận việc thẳng từ chủ dự án vẫn gửi `[DONE]` ngắn cho LEAD để board đủ.
- Phiên nào cũng dùng biểu tượng theo bảng một nghĩa (`references/quy-tac-bo-sung.md` § 1), luôn kèm chữ.

## 2. Vùng ghi — mỗi file một người ghi

- Một việc = `TASK-YYYYMMDD-NN`: một dòng trong board và một brief, chỉ LEAD ghi.
- Thư mục việc `<paths.tasks>/YYYY-MM/DD_NN-<tên>/` (LEAD tạo): `in/` chỉ đọc · `research/` · `out/` · `qa/`.
- Không ai ghi vào thư mục con của vai trò khác; muốn đổi thì nhắn người ghi.
- **Write set**: mỗi dòng board ghi đường dẫn việc đó được ghi. Hai việc chỉ chạy song song khi write set không chồng nhau.
- File dùng chung (`shared_paths`): chỉ DOCS sửa; phiên khác gửi yêu cầu cho DOCS. Thay đổi quy tắc / skill / hook được phát hành theo đợt (`docs.publish_windows`), lịch sử quy tắc ghi ở tệp riêng (`references/quy-tac-bo-sung.md` § 4).

## 3. Mức duyệt

🟢 AUTO: việc trong vùng của mình, báo sau · 🟡 LEAD: thứ tự, giao việc, phạm vi trong yêu cầu, mức QA · 🔴 chủ dự án: phát hiện chính sách, xóa / chuyển file không phải nháp của mình, quyền / cấu hình, gửi ra ngoài, mâu thuẫn hoặc đảo ngược quyết định đã có, vượt phạm vi, chi phí thêm. Bảng đầy đủ: `references/xac-nhan-va-qa.md` § 3. Phân vân giữa 🟡 và 🔴 → chọn 🔴.

- Danh sách gửi chủ dự án đánh số `#1`, `#2` … kèm mã bên cạnh; chủ dự án trả lời gọn một dòng `#1 OK · #3 B`. Câu hỏi có phương án × Ưu / Nhược, phương án đề xuất đứng đầu và ghi "(đề xuất)".

## 4. Khối xác nhận (🔴)

Phiên cần quyết định 🔴 dừng đúng bước đó (việc 🟢 khác vẫn làm tiếp) và gửi khối `CONFIRM-YYYYMMDD-NN` cho LEAD (mẫu khối và luật trả lời: `references/xac-nhan-va-qa.md` § 1). Chỉ làm tiếp khi có `OK CONFIRM-…` đúng mã do chủ dự án gõ (hoặc LEAD chuyển nguyên văn). Không đưa dữ liệu nhạy cảm vào khối (`[MASKED]`).

## 5. Bàn giao và báo cáo

Chi tiết (brief, HANDOFF, hàng đợi, thư mục phần): `references/xac-nhan-va-qa.md` § 4.

- Dòng đầu mọi chỉ thị / báo cáo: `[<TASK hoặc card> · PART-NN] <người gửi> → <người nhận>`. Brief mở đầu bằng 5 dòng: TASK / card · PART, được ghi vào, đầu vào và phiên bản, xong khi, nhãn `CLEAR / DESIGN / RESEARCH / HARD`.
- Người nhận trả lời dòng đầu "nhận: ghi vào …, đọc … bản …" rồi mới làm; thiếu thì hỏi một câu, không đoán.
- Báo cáo tối đa 6–8 dòng: `[DONE <TASK>] <kết quả> · <đường dẫn> · Tự kiểm: <gì> · Dọn: <gì>` hoặc `[BLOCKED <TASK>] <lý do>`; BUILD liệt kê `CHOICE-n`. Không nhắn chỉ để báo bắt đầu / tiến độ / cảm ơn.
- Một việc "đang làm" mỗi phiên; `QUEUE_<ROLE>.md` trong `paths.roles_docs` do phiên tự ghi.

**Context**: đo context trước khi giao việc và khi gửi `[DONE]`; vượt ngưỡng `context.warn_tokens` (mặc định 250 nghìn) thì dọn hoặc nén phiên theo `references/quy-tac-bo-sung.md` § 2. Hook `ctxwatch.py` (bật bằng `context.enabled`) nhắc khi vượt ngưỡng.

## 6. Mức làm việc và mức QA

Mức làm việc `QUICK` / `DOC` / `CARD` và mức QA `NO-QA` / `LIGHT` / `FULL`: bảng ở `references/xac-nhan-va-qa.md` § 2. Mọi phát hiện của một lần review đi vào **một** vòng sửa; sau 2 vòng cùng một vấn đề → dừng vá, chuyển sang `HARD`. Dữ liệu test do nhóm tạo phải nhận ra được (tiền tố `TEST-` hoặc chữ "Mẫu").

## 7. Bắt đầu phiên

1. Đọc `DOC-TRUOC.md`, `CLAUDE.md` / `AGENTS.md` của dự án, skill này và skill của vai trò mình.
2. Đọc `QUEUE_<ROLE>.md` của mình; có việc "chờ" thì làm việc đó.
3. Ghi thời gian từng bước:
   `pwsh <paths.scripts>/steplog.ps1 start <task> -Step <CODE> -As <tên phiên> [-Type <loại>] [-Model <model>]` và `end <task> -Step <CODE> [-Result OK|NG|PARTIAL]`; `wait` / `resume` khi chờ chủ dự án.
   Mã bước: `INTAKE POLICY READ PLAN CONFIRM BUILD SELFCHECK QA FIX KB DELIVER CLEANUP OTHER`. Ghi chú một dòng, không chứa nội dung prompt, bí mật hay ID phiên.
4. Ý tưởng cải tiến quy trình: gửi DOCS (loại `improvement`), LEAD đưa vào buổi retro hằng tuần; không tự áp dụng.

## 8. Chính sách dữ liệu

Trước khi xử lý file hay chữ được dán vào, đối chiếu file chính sách `policy_file` của config. Không bao giờ ghi mật khẩu, khóa API, token hay khóa riêng vào bất kỳ file, vé, nhật ký hay tin nhắn nào (`[MASKED]`).

- Guard / hook bảo vệ chặn một việc (khi `guard_rule_enabled` = true): cảnh báo đỏ, dừng, không lách, chỉ qua khi chủ dự án tự gõ `GUARD-OK <HHMM> "<lý do>"` trong phiên đó — `AGENTS.md` § Guard.
- Viết báo cáo / tài liệu: dùng skill loại tài liệu trước, sau đó skill văn phong nếu dự án đã cài (khóa `writing_style_skill`, mặc định `q-doc-edit`); không có thì tự soát theo `references/quy-tac-bo-sung.md` § 6.
