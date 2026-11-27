---
card: NNN-slug
title: <một dòng>
task: TASK-YYYYMMDD-NN
zones: [<task>/out/<đường dẫn>]     # thay cho "branches" (không dùng git)
state: DRAFT                        # DRAFT READY BUILDING IN-REVIEW FIXING RELEASED CANCELLED (giá trị cũ CANDIDATE FIXES MERGED CLOSED vẫn được đọc)
risk_class: low                     # low | medium | critical
protected_paths: []                 # mỗi đường dẫn cần câu duyệt chủ dự án gõ tay trong Decisions; liên kết tượng trưng → ghi cả đích
inputs: []                          # đường dẫn chỉ đọc
acceptance: []                      # ngắn, kiểm được
depends_on: []
---

# <tiêu đề>

## Scope
- Làm:
- Không làm:

## Decisions
- <ngày> <ai>: <quyết định> (câu chủ dự án gõ, nguyên văn, cho đường dẫn được bảo vệ / phát hành)

## Rules
- Quy tắc chung của dự án (`AGENTS.md`, `CLAUDE.md`). Quy tắc riêng của thẻ ghi ở đây.
- Thẻ sửa lỗi script: test FAIL trên lỗi **trước khi sửa** (red proof). Thẻ đổi script / hook / định dạng tệp dùng chung: mục "Ai đọc tệp / định dạng này" dưới đây.

## Ai đọc tệp / định dạng này
- <bộ đọc tìm bằng grep> — biên nhận có một lần chạy trên bản mới (bỏ mục này nếu thẻ không đổi script / hook / định dạng)

## Acceptance
- [ ] …

## Review
- Mức: LIGHT | FULL · Người review: REVIEW · Mã băm đã review: <mã>
- Kết quả: PASS | FAIL (danh sách) | FIX-VERIFIED

## Takeover
Người nhận việc tiếp theo chỉ đọc mục này:
- Pha hiện tại / vé đang mở: TICKET-NN (tệp `handoff/H-NN.json`; tên pha / trạng thái xem `docs/process/NAMES.md`)
- Việc kế tiếp: <một bước>
- Tệp cần đọc: <đường dẫn>
- Không làm: <giới hạn>

## State log
- <dd/mm HH:MM> DRAFT — LEAD

## NEXT
(Khối NEXT của LEAD: gồm thời điểm, phiên đang chờ, bước, vai trò, số prompt, quyền phát hành)
