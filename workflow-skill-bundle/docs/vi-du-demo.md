# Ví dụ: một card trên dự án mẫu "demo"

Dự án mẫu `demo` có một script `tools/hello.ps1` cần sửa. Các lệnh chạy từ thư mục gốc dự án sau khi cài gói (README_VN § 3). Tên phiên lấy theo config mẫu.

## 1. LEAD tạo card và giao

```powershell
Copy-Item -Recurse docs/cards/_TEMPLATE docs/cards/001-demo-hello
# sửa docs/cards/001-demo-hello/CARD.md: zones: [2026-01/05_01-demo-hello/out/tools], Acceptance, Takeover
pwsh scripts/process/ticket.ps1 send 001-demo-hello -As LEAD -To BUILD -Phase BUILD -Session "Điều phối" -Note "sửa lời chào"
```

## 2. BUILD nhận, làm, gate, đóng băng

```powershell
pwsh scripts/process/ticket.ps1 accept 001-demo-hello -As BUILD -Session "Dev chính"
pwsh scripts/process/manifest.ps1 001-demo-hello -Baseline -As BUILD
# chép tools/ vào zone 2026-01/05_01-demo-hello/out/tools, sửa hello.ps1, thêm tests/hello.Tests.ps1
pwsh scripts/process/gate.ps1 001-demo-hello -As BUILD          # test chạy trên pwsh (gate.hosts của config, mặc định ps7)
pwsh scripts/process/ticket.ps1 done 001-demo-hello -As BUILD -Note "xong, gate PASS"
pwsh scripts/process/ticket.ps1 send 001-demo-hello -As BUILD -To REVIEW -Phase REVIEW -Freeze -Note "review LIGHT"
```

## 3. REVIEW kết luận

```powershell
pwsh scripts/process/ticket.ps1 accept 001-demo-hello -As REVIEW
pwsh scripts/process/ticket.ps1 done 001-demo-hello -As REVIEW -Note "PASS 0 lỗi"
```

## 4. LEAD release

```powershell
pwsh scripts/process/intake.ps1 001-demo-hello
pwsh scripts/process/release.ps1 001-demo-hello -IfSafe -As LEAD
```

`tools/` không phải đường dẫn bảo vệ nên không cần dòng duyệt. Nếu card đổi `scripts/process/`, phần Decisions phải có dòng:

```text
- owner 05/01 10:30: "duyệt cài script mới" -> approves scripts/process/
```

## 5. Khi file đổi sau khi đóng băng

REVIEW thấy digest lệch: `ticket.ps1 done 001-demo-hello -As REVIEW -Note "OUTDATED file đổi sau freeze"`, rồi LEAD gửi vé đóng băng mới ở digest hiện tại.
