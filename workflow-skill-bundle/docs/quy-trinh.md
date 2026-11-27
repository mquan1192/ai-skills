# Sơ đồ quy trình

## 1. Việc nhóm (mọi mức)

```mermaid
flowchart TD
    A["Chủ dự án giao việc"] --> B["LEAD tạo TASK:<br/>chọn mức, mức QA, nhãn"]
    B --> C{"Mức?"}
    C -->|"QUICK"| D["Phiên làm<br/>+ tự kiểm"]
    C -->|"DOC"| E["BUILD làm file _vNN<br/>có thể giao BUILD_M / S"]
    C -->|"CARD"| F["Luồng card / vé<br/>xem mục 2"]
    E --> G{"Cần QA?"}
    G -->|"NO-QA"| H["DONE<br/>báo LEAD"]
    G -->|"LIGHT / FULL"| I["REVIEW kiểm"]
    I --> H
    D --> H
    H --> J["Thư ký gom báo cáo<br/>mỗi giờ, INBOX"]
    J --> K{"Cần chủ dự án?"}
    K -->|"🔴"| L["Khối CONFIRM-…<br/>chủ dự án OK / NG"]
    K -->|"🟢 / 🟡"| M["Ghi INBOX<br/>để biết"]
```

## 2. Card / vé (code, script, đường dẫn bảo vệ)

```mermaid
sequenceDiagram
    participant L as LEAD
    participant B as BUILD
    participant R as REVIEW
    L->>B: vé SENT (pha BUILD)
    Note over B: accept, baseline,<br/>làm trong zone
    Note over B: gate: quét bí mật<br/>+ test pwsh 7 → PASS
    B->>R: vé đóng băng (manifest + digest)
    alt file đổi sau khi đóng băng
        Note over R: done -Note 'OUTDATED …'<br/>(không kết luận)
        L->>R: vé đóng băng mới ở digest hiện tại
    end
    R->>L: done PASS / FAIL (đúng digest)
    opt FAIL
        L->>B: một vòng sửa (pha FIX)
        B->>R: gate + đóng băng lại → FIX-VERIFIED
    end
    Note over L: release -IfSafe<br/>(đường dẫn bảo vệ: cần<br/>dòng duyệt của chủ dự án)
```

## 3. Sprint 1 tuần

| Ngày | Việc |
|---|---|
| Thứ Hai | Lập kế hoạch: ≤ 3 mục tiêu, danh sách TASK |
| Thứ Hai → Thứ Sáu | Làm việc; báo cáo gom mỗi giờ (chỉ khi có điều mới); INBOX |
| Thứ Sáu | Báo cáo tuần (`SPRINT-YYYY-Www.md`) + retro (`RETRO-YYYY-Www.md`) |
| Sau retro | Một card gom thay đổi quy tắc / skill, một dòng duyệt; tối đa một thay đổi quy trình mỗi tuần (trừ 🔴) |
