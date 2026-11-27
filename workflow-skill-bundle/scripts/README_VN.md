# scripts: bộ lệnh của luồng card và vé

Tài liệu tra cứu cho người vận hành và cho Claude. Người mới nên đọc phần "Thay đổi code: luồng card" trong [README_VN.md](../README_VN.md) trước.

Hai khái niệm dùng trong file này:

- **Card**: một yêu cầu thay đổi, có thư mục riêng (`<cards>/<card>/`) chứa mô tả, nhật ký, vé và biên nhận kiểm tra.
- **Vé** (ticket, file `H-NN.json`): bản ghi bàn giao card từ vai này sang vai khác, ví dụ từ BUILD sang REVIEW.

Các script dưới đây ghi vé, chạy kiểm tra, chốt danh sách file và đánh dấu phát hành. Script không push, merge hay deploy gì.

Chạy trên PowerShell 7 (`pwsh`), không cần cài thêm gì. Trên Windows PowerShell 5.1, mỗi lệnh dừng ngay với một dòng `REFUSED: <script> needs PowerShell 7 (pwsh) …`, mã thoát 1, không ghi gì. Mọi đường dẫn, danh sách và ngưỡng đọc từ file cấu hình `.workflow/workflow.config.json` ở thư mục gốc dự án (bản mẫu: `config/workflow.config.example.json`).

## 1. Thư mục gốc dự án

- Mọi lệnh nhận `-Root <thư mục dự án>`. Không có `-Root`: lệnh tìm từ thư mục đang đứng đi lên, rồi từ thư mục chứa script đi lên, tới thư mục đầu tiên có `.workflow/workflow.config.json`.
- Không tìm thấy, file hỏng, hoặc `schema` khác 1 → lệnh dừng với dòng `REFUSED: …` kèm gợi ý: chạy `install.py` hoặc chép `config/workflow.config.example.json` thành `.workflow/workflow.config.json`.
- Mã thoát: 0 = xong, 1 = từ chối / lỗi (một dòng `REFUSED: …` hoặc `ERROR: …`). `board` và `stale` luôn thoát 0.

## 2. Các lệnh

| Lệnh | Cách dùng | Việc làm |
|---|---|---|
| ticket | `.\ticket.ps1 send <card> -As <VAI> -To <VAI> -Phase <BUILD/TEST-GATE/REVIEW/FIX/VERIFY-FIX/RELEASE/RETRO> [-Note] [-Agent] [-Session <tên phiên>] [-Freeze]` · `accept / done / hold / takeover <card> -As <VAI> [-Note] [-Session]` | Ghi vé `<cards>/<card>/handoff/H-NN.json`, in 4 dòng "chuông" để báo phiên nhận |
| checkpoint | `.\checkpoint.ps1 <card> -As <VAI> -Done <t> -Doing <t> -Next <t> -Check <t>` | Thêm 1 dòng vào `<cards>/<card>/log.md` |
| manifest | `.\manifest.ps1 <card>` · `.\manifest.ps1 <card> -Baseline -As BUILD` | In manifest + mã digest; `-Baseline` ghi mốc ban đầu (1 lần, đầu pha BUILD) |
| gate | `.\gate.ps1 <card> [-As <VAI>] [-Hosts ps5,ps7]` | Quét bí mật + chạy `*.Tests.ps1` trong vùng card → `<cards>/<card>/receipts/gate.json`. Không có `-Hosts`: dùng `gate.hosts` (mặc định `["ps7"]`); `ps5` chỉ cho sản phẩm phải chạy trên 5.1 (§ 5) |
| release | `.\release.ps1 <card> -IfSafe -As LEAD [-DryRun]` | Kiểm toàn bộ điều kiện; đạt thì đóng vé cuối, card → `RELEASED` |
| intake | `.\intake.ps1 <card>` | Chỉ đọc: tình trạng card, lý do release bị từ chối, bước tiếp theo |
| board | `.\board.ps1` | Tạo lại `<process_docs>/PROGRESS.md` từ các card |
| stale | `.\stale.ps1` | Liệt kê vé chờ quá lâu (chỉ in trên máy; từ `STALE` ở đầu dòng nghĩa là "chờ quá lâu") |
| steplog | `.\steplog.ps1 start <task> -Step <MÃ> -As <phiên> [-Type] [-Model] [-Note]` · `end <task> -Step <MÃ> [-As] [-Result OK/NG/PARTIAL] [-Note]` · `wait <task> -Note <t>` / `resume <task>` · `report [-Task] [-Type] [-From] [-To] [-Csv <file>]` · `purge [-Days n] -As <phiên> [-DryRun]` | Nhật ký thời gian từng bước → `<process_log>/steps/<yyyy-MM>.jsonl`; `purge` chuyển dòng / file cũ hơn n ngày (mặc định 90) vào `<trash>/<yyyyMMdd>/<process_log>/` và ghi `<trash>/TRASH-LOG.md` |

`<VAI>` = LEAD, DOCS, BUILD, REVIEW, OPS. Tên file vé `H-NN.json` giữ như cũ.

**Tên giá trị (v1.1).** Script ghi tên mới và vẫn đọc tên cũ trong vé, `CARD.md` và tham số; bản ghi cũ không bị viết lại.

| Loại | Tên cũ (vẫn đọc) | Tên mới (script ghi) |
|---|---|---|
| Trạng thái card | `CANDIDATE` · `FIXES` · `MERGED` · `CLOSED` | `IN-REVIEW` · `FIXING` · `RELEASED` · `CANCELLED` |
| Pha của vé | `P1` · `GATE` · `FIXES` · `VERIFY` | `BUILD` · `TEST-GATE` · `FIX` · `VERIFY-FIX` |
| Trạng thái vé | `HOLD` · `TAKEOVER` | `ON-HOLD` · `TAKEN-OVER` |
| Kết luận REVIEW (từ đầu `-Note`) | `NG` · `FIXES_VERIFIED` | `FAIL` · `FIX-VERIFIED` |
| Biên nhận / vé đóng vì vùng đã đổi | `STALE` | `OUTDATED` |

Các giá trị không đổi: `DRAFT`, `READY`, `BUILDING`; `REVIEW`, `RELEASE`, `RETRO`; `SENT`, `ACCEPTED`, `DONE`; `PASS`; `PARTIAL`.

## 3. Khóa cấu hình mà script đọc

| Khóa | Dùng ở | Mặc định khi thiếu |
|---|---|---|
| `schema` | mọi lệnh (phải là 1) | — (bắt buộc) |
| `paths.cards` | thư mục card | `docs/cards` |
| `paths.process_docs` | `PROGRESS.md` (board) | `docs/process` |
| `paths.lead` | `steplog`: đọc `<lead>/board.md` để nối tên card / thư mục task với mã task | `lead` |
| `paths.scripts` | `gate`, `release`: test của chính bộ script này (xem § 5) | `scripts/process` |
| `paths.process_log` | `steplog` (`steps/`, `turns/`), hook `turnlog.py` (`turns/`) | `process-log` |
| `paths.trash` | `steplog purge` | `_trash` |
| `session_map_file` | `ticket send`: dòng "Ring" (tên + mã phiên nhận); file chỉ để trên máy, không lưu vào vé | không có → chỉ in 4 dòng chuông |
| `protected_paths` | `release`: thay đổi ở đây cần dòng duyệt của chủ dự án | — |
| `shared_paths`, `shared_paths_except` | `release`: đường dẫn dùng chung (không được miễn review) | — |
| `approval_name` | `release`: tên đứng đầu dòng duyệt / dòng miễn review | `owner` |
| `gate.hosts` | `gate`: bản PowerShell chạy test khi không có `-Hosts`, và bản mỗi file test phải PASS (§ 5) | `ps7` |
| `stale.sent_minutes`, `stale.accepted_hours` | `stale` | 30 phút, 3 giờ |
| `steplog.purge_enabled`, `steplog.purge_days` | `steplog purge` | bật, 90 ngày |

**Quy tắc khớp đường dẫn** (`protected_paths`, `shared_paths`, `shared_paths_except`; không phân biệt hoa thường, `\` = `/`):

- mục kết thúc bằng `/` = thư mục: đường dẫn bắt đầu bằng nó, hoặc thư mục đó nằm ở bất kỳ cấp nào (ví dụ `.claude/`, `hooks/`, `.github/workflows/`);
- mục không có `/` = tên file: tên cuối của đường dẫn trùng (ví dụ `AGENTS.md` ở bất kỳ đâu);
- mục có `/` ở giữa = một file cụ thể: cả đường dẫn trùng.
- Đường dẫn có `..` luôn coi là được bảo vệ.

**Dòng duyệt** trong mục `## Decisions` của `CARD.md` (cả dòng, đúng một dạng; `<tên>` = `approval_name`):

```text
- <tên> <dd/MM HH:mm>: "<câu của chủ dự án>" -> approves <đường dẫn>[, <đường dẫn>]
- <tên> <dd/MM HH:mm>: "<câu của chủ dự án>" -> waives review
```

Mũi tên `->` hoặc `→`; dấu nháy `"` hoặc `“ ”`. Dòng miễn review chỉ dùng được cho card chỉ thêm sản phẩm mới (không có đích đang tồn tại, không đổi đường dẫn dùng chung / được bảo vệ).

## 4. Vùng card

`zones:` trong `CARD.md` có dạng `<YYYY-MM>/<DD_NN-task>/out/<đích>` (một thư mục hoặc một file). Đích là đường dẫn trong dự án sau khi phát hành. Thư mục phần việc `out/_m/…`, `out/_s/…` không phải vùng.

## 5. Kiểm thử và quy tắc bản PowerShell của gate

- `gate.hosts` mặc định `["ps7"]`: gate chỉ cần PowerShell 7. Thêm `ps5` chỉ khi sản phẩm của card phải chạy trên Windows PowerShell 5.1.
- Mỗi file test phải PASS trên mọi bản trong `gate.hosts`. Ngoại lệ: file test có đích nằm dưới `paths.scripts` **và** có dòng `#Requires -Version 7` trong 20 dòng đầu chỉ cần PASS trên `ps7` (bộ script này chỉ chạy trên PowerShell 7). File test ở nơi khác vẫn theo `gate.hosts` dù có dòng đó, để một sản phẩm cần chạy trên 5.1 không bỏ được lần chạy `ps5` chỉ bằng một dòng.
- Chạy thiếu bản cần thiết → `PARTIAL` (không phát hành được); `release -IfSafe` kiểm cùng quy tắc trên biên nhận.
- `tests\*.Tests.ps1` chạy được trên cả hai bản (không có dòng `#Requires`). Trên Windows PowerShell 5.1, mỗi test chỉ kiểm lệnh tương ứng bị từ chối (đúng một dòng `REFUSED`, mã thoát 1, cây giả không đổi) rồi in `RESULT`; `-RedProof` chạy bản sao tạm của lệnh đó đã bỏ dòng kiểm phiên bản → phải ra 1 FAIL.
- Trên PowerShell 7, test chạy đầy đủ: tạo dự án giả trong `%TEMP%\cardflow-tests\` (có `.workflow/workflow.config.json` chép từ `config/workflow.config.example.json`, `gate.hosts` đặt `ps5` + `ps7` để kiểm được quy tắc hai bản), xóa khi xong (`-Keep` để giữ). Chạy một file: `pwsh -NoProfile -File .\tests\ticket.Tests.ps1` hoặc `powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\ticket.Tests.ps1`.
- `tests\names.Tests.ps1`: bảng tên cũ → tên mới; script đọc tên cũ và chỉ ghi tên mới.
- `tests\ps7.Tests.ps1`: chạy từng lệnh bằng Windows PowerShell 5.1, mong đợi đúng một dòng `REFUSED`, mã thoát 1, không ghi gì. `-RedProof` chạy trên bản sao tạm của script trong đó `board.ps1` bị bỏ dòng chặn → phải ra 1 FAIL. Trên PowerShell 7 test này còn kiểm mọi file test không có `#Requires` và gọi `Test-Ps5Only` với lệnh có thật.
- `tests\config.Tests.ps1`: các trường hợp cấu hình (thiếu / hỏng / sai schema, đường dẫn tùy chỉnh, `approval_name`, ngưỡng, tắt purge, mặc định 90 ngày, session map).
- Hook `hooks/turnlog.py` có test riêng: `python -B -m unittest test_turnlog test_ctxwatch` trong thư mục `hooks/`.
