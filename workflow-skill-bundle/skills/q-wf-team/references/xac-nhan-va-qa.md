# Mức duyệt, khối xác nhận, bàn giao và mức QA (chi tiết của `q-wf-team` § 3–6)

## 1. Khối xác nhận (🔴)

Phiên cần quyết định dừng đúng bước đó (việc 🟢 khác vẫn làm tiếp), gửi khối cho LEAD (việc card: chỉ gửi LEAD; việc khác: hiện trong chat của mình và gửi LEAD). LEAD ghi vào INBOX và đưa chủ dự án xem cùng lúc.

```text
🔴 CONFIRM-YYYYMMDD-NN · <phiên> · TASK-…
Việc cần duyệt: <một câu: chính xác điều gì sẽ xảy ra>
Lý do cần duyệt: <trường hợp ở §3>
Phạm vi: <file / người nhận / số lượng>
Phương án: A (đề xuất) — Ưu / Nhược · B — Ưu / Nhược
Nếu OK: <kết quả> · Nếu NG: <thay vào đó>
Trả lời — chép 1 dòng:
OK CONFIRM-YYYYMMDD-NN
NG CONFIRM-YYYYMMDD-NN <lý do>
```

- Không đưa dữ liệu nhạy cảm hay thông tin bí mật vào khối (`[MASKED]`); phát hiện chính sách thì chỉ ghi file + vị trí.
- Chỉ làm tiếp khi có `OK` đúng mã, do chủ dự án gõ (hoặc LEAD chuyển nguyên văn). Một khối = một quyết định.

## 2. Mức làm việc và mức QA

| Mức làm việc | Khi nào | Cách làm |
|---|---|---|
| `QUICK` | Sửa chữ, đổi tên, việc ≲ 30 phút | Không card; tự kiểm |
| `DOC` | Tài liệu / Excel | Thư mục việc + file có phiên bản `_vNN`; tự kiểm; chủ dự án xem bản preview |
| `CARD` | Code, script, đường dẫn bảo vệ, thứ gửi ra ngoài | Luồng card đầy đủ (`q-wf-card`) |

| Mức QA | Dùng cho |
|---|---|
| `NO-QA` | Nháp, preview, tài liệu nội bộ, sửa chữ, việc chủ dự án tự xem; người làm ghi "Tự kiểm: …" |
| `LIGHT` | Một sub-agent nhỏ chạy script kiểm có sẵn trên bản cuối |
| `FULL` | Thứ gửi ra ngoài, script dọn rác, đường dẫn bảo vệ, việc 🔴 — REVIEW xem độc lập |

- Mọi phát hiện của một lần review đi vào **một** vòng sửa; LEAD quyết từng điểm.
- Sau 2 vòng sửa cùng một vấn đề mà chưa xong → dừng vá, thu hẹp việc, chuyển vấn đề sang `HARD`.
- Dữ liệu test / mẫu do nhóm tạo phải nhận ra được (tiền tố `TEST-` hoặc chữ "Mẫu").

## 3. Mức duyệt

| Mức | Việc | Ai quyết |
|---|---|---|
| 🟢 AUTO | Đọc; viết, code, test trong vùng của mình; báo cáo QA; bàn giao; sửa sau QA NG (tối đa 2 vòng) | Phiên tự làm, báo sau |
| 🟡 LEAD | Thứ tự, giao việc, tách / gộp việc, đổi write set, chỉnh phạm vi trong yêu cầu, mức QA, model của sub-agent | LEAD quyết, ghi lên board |
| 🔴 chủ dự án | Phát hiện về chính sách; xóa / chuyển file không phải nháp của mình; quyền / cấu hình; gửi bất cứ thứ gì ra ngoài; mâu thuẫn nguồn hoặc đảo ngược quyết định đã có; vượt phạm vi; chi phí thêm | Chủ dự án, qua khối xác nhận (§4) |

Phân vân giữa 🟡 và 🔴 → chọn 🔴.

- Danh sách gửi chủ dự án đánh số `#1`, `#2` … kèm mã bên cạnh; chủ dự án trả lời gọn một dòng `#1 OK · #3 B`. Câu hỏi có phương án × Ưu / Nhược, phương án đề xuất đứng đầu và ghi "(đề xuất)".

## 4. Bàn giao và báo cáo

**Dòng đầu cố định** cho mọi chỉ thị và báo cáo: `[<TASK hoặc card> · PART-NN] <người gửi> → <người nhận>`.

**Brief giao việc** bắt đầu bằng 5 dòng:
1. TASK / card · PART
2. Được ghi vào: <đường dẫn>
3. Đầu vào và phiên bản: <file `_vNN`, commit, digest>
4. Xong khi: <điều kiện kiểm được, số lượng "n / tổng m">
5. Nhãn: `CLEAR` (rõ, làm luôn) · `DESIGN` (cần thiết kế trước) · `RESEARCH` (cần tìm hiểu bên ngoài) · `HARD` (hai phương án mà spec chưa chốt)

**Người nhận**: dòng đầu trả lời nhắc lại "nhận: ghi vào …, đọc … bản …" rồi mới chạy lệnh đầu tiên. Đọc brief và mọi file nó nêu; thiếu thì hỏi một câu, không đoán.

**Việc tài liệu**: người gửi viết `HANDOFF-<TASK>-to-<vai trò>.md` trong vùng của mình (mục tiêu bước tiếp, đã làm và cách kiểm, chưa làm, file, sự thật kèm nguồn, suy luận có đánh dấu, điểm mở, write set của người nhận) rồi gọi người nhận một dòng. **Việc card**: dùng vé (skill `q-wf-card`).

**Báo cáo** (ngắn, tối đa 6–8 dòng; chi tiết để trong file):
- `[DONE <TASK>] <kết quả> · <đường dẫn> · Tự kiểm: <gì> · Dọn: <đã chuyển gì vào thùng rác>`
- `[BLOCKED <TASK>] <lý do / CONFIRM-…>`
- BUILD (code / script) liệt kê "Lựa chọn đã tự quyết": `CHOICE-1`, `CHOICE-2` … (điều spec không nói và đã chọn gì).
- Không nhắn chỉ để báo "bắt đầu", báo tiến độ hay xác nhận đã nhận; không trả lời tin chỉ để cảm ơn.

**Context**: đo context trước khi giao việc và khi gửi `[DONE]`; vượt ngưỡng `context.warn_tokens` (mặc định 250 nghìn) thì dọn hoặc nén phiên theo `references/quy-tac-bo-sung.md` § 2. Hook `ctxwatch.py` (bật bằng `context.enabled`) nhắc khi vượt ngưỡng.

**Hàng đợi**: mỗi phiên BUILD / BUILD_M / BUILD_S (và nghiên cứu khi giữ > 1 việc) có `QUEUE_<ROLE>.md` trong `paths.roles_docs`, tự ghi. Một việc "đang làm" mỗi lúc; trước khi chuyển việc ghi checkpoint 3 dòng (đã xong gì, dừng ở đâu, bước tiếp); khi tiếp tục thì đọc lại brief.

**Thư mục phần**: `out/_m/<TASK|card>-<part>/`, `out/_s/<TASK|card>-<part>/`. BUILD gộp bằng cách **chép** vào `out/`, rồi báo người làm phần dọn thư mục phần của họ.
