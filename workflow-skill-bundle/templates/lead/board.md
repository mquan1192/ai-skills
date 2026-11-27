# Bảng việc của nhóm (board)

Chỉ LEAD ghi tệp này (thư mục `lead/`). Giao thức: quy tắc nhóm của dự án · tạo ngày <YYYY-MM-DD>.

Trạng thái (cột 4, chỉ dùng các giá trị này): `todo / doing / waiting / review / done / blocked` — chi tiết (tạm dừng, tiếp tục, đã phát hành …) ghi ở cột "Next". Mỗi việc có một bản giao việc `lead/tasks/TASK-YYYYMMDD-NN.md`, ghi nhãn việc `CLEAR / DESIGN / RESEARCH / HARD`.

## Sprint này — SPRINT-YYYY-Www (<dd/mm> → <dd/mm>)

- Mục tiêu (tối đa 3): chốt ở buổi lập kế hoạch sáng thứ Hai (báo cáo gom đầu tiên của tuần).
- Ứng viên (LEAD đề xuất): <việc> · <việc> · <việc>
- Thêm giữa sprint (chủ dự án giao giữa tuần): <việc>, ghi "thêm giữa sprint".

| TASK | Việc | Phụ trách | Trạng thái | QA | Vùng ghi | Next | Cập nhật |
|---|---|---|---|---|---|---|---|
| TASK-YYYYMMDD-01 | <tên việc một dòng> (bản giao việc: `lead/tasks/TASK-YYYYMMDD-01.md`) | <vai trò / phiên> → <vai trò> | todo | NO-QA | `<task>/out/` | <bước kế tiếp, ai đang chờ ai> | <dd/mm HH:MM> |
