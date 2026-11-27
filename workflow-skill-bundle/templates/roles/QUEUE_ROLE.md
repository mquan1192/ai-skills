# QUEUE_<VAI_TRÒ> — <tên phiên>

Chỉ phiên này ghi tệp. Mỗi việc một dòng: thẻ / TASK + phần · ai giao · trạng thái (chờ / đang làm / xong) · bản giao việc hoặc vé. Mỗi lúc chỉ một việc "đang làm"; trước khi chuyển việc, ghi điểm dừng ở cuối tệp.

| Việc | Từ | Trạng thái | Bản giao việc / vé |
|---|---|---|---|
| <NNN> · <TICKET-NN> <tóm tắt> | <LEAD / phiên giao> | chờ | `docs/cards/<NNN-slug>/handoff/H-NN.json` |

## Phần đã giao đi (<NNN>)

| Phần | Giao cho | Trạng thái | Bản giao việc |
|---|---|---|---|
| <NNN> · PART-NN <tóm tắt> | <phiên phụ> | chờ / đang làm / xong + đã gộp | `<task>/out/HANDOFF-<NNN>-<phần>.md` |

## Điểm dừng <NNN> (<dd/mm HH:MM>, <lý do dừng>)
- Đã xong: <các bước + tệp>
- Đang dở: <việc đang chạy ở đâu>
- Kế tiếp: <bước kế tiếp>
- Câu hỏi còn mở và đang chờ ai: <câu hỏi / "không có">

## Trước khi dọn hoặc nén phiên (context vượt `context.warn_tokens`, việc mới không liên quan, cuối ngày)
Tối đa 10 dòng: trạng thái từng việc · tệp kết quả kèm phiên bản · câu hỏi còn mở · yêu cầu KB còn mở · "đã xóa lúc <HH:MM>". Bài học ghi vào `NOTES_<VAI_TRÒ>.md`; đóng nhật ký thời gian.
