# Giọng văn — viết theo mẫu và hồ sơ giọng văn

Đọc khi chạy chế độ Voice: người dùng đưa văn bản mẫu và muốn viết "giống thế này", hoặc muốn lập hồ sơ giọng văn cho mình, cho một kênh, một ấn phẩm. Viết riêng cho skill này (ghi chú nguồn ý tưởng ở cuối file).

## 1. Ranh giới

- Hồ sơ giọng văn chỉ lập từ văn bản của chính người dùng, của tổ chức họ, hoặc văn bản người dùng có quyền dùng. Không lập hồ sơ để viết giả danh một người khác hay để làm văn bản như do người đó viết.
- Hồ sơ quyết cách viết (câu, dấu câu, cấu trúc, giọng), không quyết sự thật: mọi quy tắc giữ nghĩa, số liệu, trạng thái thông tin của `SKILL.md` vẫn đứng trên hồ sơ.
- Không đưa nội dung bí mật của mẫu vào hồ sơ; hồ sơ ghi quy luật, không chép đoạn dài của mẫu.

## 2. Có một mẫu ngắn (cách nhanh)

Đọc mẫu trước khi viết. Ghi nhận và bám theo: độ dài câu thường gặp, chọn từ (Hán Việt hay thuần Việt, thuật ngữ tiếng Anh nhiều hay ít), dấu câu (gạch ngang, ngoặc, chấm phẩy), cách mở đoạn, cách chuyển ý, cách xưng hô, mức trang trọng. Mẫu thắng các quy tắc phong cách của `ai-tells.md`: mẫu dùng gạch ngang thì giữ gạch ngang với tần suất tương đương; mẫu hay đặt câu hỏi thì không cắt câu hỏi.

Không có mẫu: theo loại văn bản. Bài viết cá nhân giữ quan điểm, sự lưỡng lự, sự hài hước, câu chen ngang của người viết; văn bản tham khảo, kỹ thuật, pháp lý thì trung tính.

## 3. Lập hồ sơ giọng văn (khi được yêu cầu)

**Tư liệu**: ít nhất 3 văn bản hoàn chỉnh cho hồ sơ nhẹ; 10 văn bản trở lên, thuộc nhiều loại và nhiều thời điểm, cho hồ sơ đủ. Ít tư liệu thì ghi rõ trong hồ sơ phần nào còn yếu.

**Hồ sơ chỉ ghi cách viết, không ghi nội dung.** Đề tài, quan điểm, nhận định quen thuộc của người viết không phải quy tắc của hồ sơ: không bao giờ thêm một nhận định vào văn bản mới chỉ vì người viết hay nói như vậy. Năm phần cần ghi, mỗi phần là quy tắc áp dụng được, kèm một ví dụ ngắn:

| Phần | Ghi gì | Ví dụ quy tắc |
|---|---|---|
| 1. Câu và từ | Độ dài câu thường gặp; từ hay dùng và từ tránh; dấu câu; tỉ lệ thuật ngữ tiếng Anh | "Câu 15–20 chữ; không dùng 'cực kỳ'; giữ tên công cụ bằng tiếng Anh" |
| 2. Bố cục | Cách mở, cách sắp thân bài, cách kết theo từng loại văn bản | "Mail: việc cần làm ở câu đầu; bài viết: kết ở bước tiếp theo, không đoạn 'tóm lại'" |
| 3. Dẫn chứng và mức chắc chắn | Cách người viết đặt số liệu, trích nguồn, nói điều chưa chắc | "Số liệu đứng ngay sau nhận định; điều chưa chắc ghi 'chưa xác nhận', không rào nhiều lớp" |
| 4. Trình bày | Tiêu đề, danh sách, bảng, in đậm, emoji | "Tiêu đề dạng danh từ; bảng chỉ để so sánh; không emoji" |
| 5. Xưng hô và văn thể theo kênh | Mail, chat, bài viết, slide dùng xưng hô và văn thể nào | "Mail cho cấp trên: em – anh/chị; slide: câu danh từ" |

Thêm một danh sách "không bao giờ" (những cách viết người đó không dùng).

**Ngôn ngữ của hồ sơ**: mặc định cùng ngôn ngữ với phần lớn tư liệu, trừ khi người dùng chọn khác. Một người viết cả tiếng Việt lẫn tiếng Nhật thì mỗi ngôn ngữ một bộ quy tắc, vì nhịp câu và mức lịch sự hai bên không giống nhau.

**Lưu**: `.writing-style/voice/<tên>.md` trong dự án (hoặc nơi người dùng chỉ định), rồi ghi đường dẫn vào khóa `voice_profile` của `.writing-style/style.config.json` nếu muốn dùng mặc định. Khuôn ở § 5.

## 4. Viết theo hồ sơ

1. Đọc hồ sơ. Nếu hồ sơ trỏ tới văn bản mẫu, xem nhanh một hai bài cùng loại để bắt nhịp câu.
2. Viết theo hồ sơ. Sự thật, số liệu, nhận định chỉ lấy từ nguồn của việc đang viết; văn bản mẫu chỉ cho cách viết.
3. Soát `ai-tells.md`, nhưng không sửa những thói quen hồ sơ ghi là của người viết.
4. Tự hỏi: người quen của người viết đọc có nhận ra giọng không? Có câu nào người viết "không bao giờ viết" không?

## 5. Khuôn hồ sơ giọng văn

```markdown
# Hồ sơ giọng văn: <tên người / kênh>

Lập ngày: <dd/mm/yyyy> · Tư liệu: <số văn bản, loại, khoảng thời gian> · Ngôn ngữ: <vi / ja / en>
Phần còn yếu (ít tư liệu): <…>

## 1. Câu và từ
- …
## 2. Bố cục (theo loại văn bản)
- Mail: …
- Bài viết: …
## 3. Dẫn chứng và mức chắc chắn
- …
## 4. Trình bày
- …
## 5. Xưng hô và văn thể theo kênh
| Kênh | Xưng hô | Văn thể |
|---|---|---|
## Không bao giờ
- …
## Văn bản mẫu (đường dẫn, tùy chọn)
- …
```

---

Ý tưởng "lập hồ sơ phong cách từ nhiều bài viết rồi viết theo hồ sơ" có ở nhiều nơi, trong đó có `writing-dna-skill` (https://github.com/larashero3-dotcom/writing-dna-skill, giấy phép PolyForm Noncommercial 1.0.0, không tương thích với Apache 2.0 của gói này). File này không dùng văn bản, khuôn hay tệp nào của repo đó; các phần, câu hỏi và khuôn ở đây viết riêng cho skill này.

Phần "Có một mẫu ngắn" phỏng theo mục "Voice" của `humanizer` (MIT, thông báo ở `NOTICES.md`).
