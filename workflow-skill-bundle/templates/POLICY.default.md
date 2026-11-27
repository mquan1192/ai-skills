# Chính sách dữ liệu (mặc định, chung)

Bản mặc định ngắn của gói quy trình. Hãy thay bằng chính sách thật của tổ chức bạn và trỏ `policy_file` trong `.workflow/workflow.config.json` tới file đó.

## Dừng ngay (không xử lý, không chép vào đầu ra; báo file + vị trí, không nhắc lại giá trị; chờ chủ dự án)
- Dữ liệu cá nhân nhận dạng được (tên, số điện thoại, mã định danh người thật) hoặc dữ liệu nhạy cảm theo quy định của tổ chức.
- Bí mật: mật khẩu, khóa API, token, khóa riêng → không ghi ở đâu cả; dùng `[MASKED]`.
- Push / merge vào nhánh chính, deploy, ghi vào môi trường thật.

## Hỏi trước
- Gửi dữ liệu của dự án tới công cụ, dịch vụ hay AI bên ngoài.
- Log hoặc báo cáo có tên máy, địa chỉ IP, thông tin cá nhân chưa che.

## Ghi chú
- Không chắc một dữ liệu có nhạy cảm không → coi là nhạy cảm và hỏi.
- Dữ liệu test / mẫu do nhóm tạo phải nhận ra được (tiền tố `TEST-` hoặc chữ "Mẫu").
