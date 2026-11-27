# Dịch Nhật – Việt – Anh

Đọc khi chạy chế độ Translate, hoặc khi người dùng nhờ dịch một câu, một thư, một file. Dịch ý định, sắc thái và mức lịch sự của nguồn, không dịch từng chữ. Sau khi dịch, soát theo ngôn ngữ đích như một văn bản viết mới.

## 1. Trước khi dịch

1. **Đọc hết nguồn một lần** trước khi dịch câu đầu: loại văn bản, người viết, người đọc, quan hệ giữa hai bên, mục đích (báo cáo, nhờ việc, từ chối, xin lỗi, thông báo).
2. **Chốt văn thể đích** theo loại văn bản (`style-guide.md` § 0 mục 7 và mục của ngôn ngữ đích) và cách xưng hô (`vietnamese-register.md` § 1 khi đích là tiếng Việt).
3. **Thuật ngữ**: glossary dự án trước; sau đó từ quen dùng trong ngành ở ngôn ngữ đích; tiếng Việt theo `vietnamese-register.md` § 3 (giữ deploy, commit, production…). Một thuật ngữ nguồn, một từ đích suốt bản dịch.
4. **Không dịch**: code, lệnh, định danh, đường dẫn, URL, tên biến, khóa cấu hình, mã lỗi, tên sản phẩm. Nhãn giao diện chưa được bản địa hóa: giữ nhãn gốc, thêm nghĩa trong ngoặc lần đầu ("「保存」(Lưu)").
5. **Dịch cả file**: giữ nguyên cấu trúc (tiêu đề, bảng, danh sách, khối code, liên kết); dịch văn bản thay thế của hình và chú thích bảng; không thêm, bớt mục.

## 2. Giữ đúng mức chắc chắn và trạng thái

Từ trạng thái không thay cho nhau được (bảng tiếng Nhật cùng ý ở `style-guide.md` § 2):

| JA | VI | EN |
|---|---|---|
| 予定です | dự kiến | is scheduled / planned |
| 検討中です | đang cân nhắc | under consideration |
| 確認中です | đang xác nhận | being confirmed |
| 〜の可能性があります | có thể (chưa xác nhận) | may / possibly (not confirmed) |
| 〜見込みです | dự kiến / ước tính | expected to |
| 対応済みです | đã xử lý xong | done / handled |
| 対応中です | đang xử lý | in progress |
| 〜と思われます | có vẻ / dường như | appears to / seems |

Không nâng "có thể" thành "đã"; không hạ yêu cầu bắt buộc (必須, must, "phải") thành lời khuyên; không biến lời nhờ thành mệnh lệnh hay ngược lại.

## 3. Lịch sự và xưng hô giữa ba ngôn ngữ

| Tình huống | JA | VI | EN |
|---|---|---|---|
| Cấp dưới gửi cấp trên / khách hàng | です・ます + 謙譲語 (ご報告します, 対応いたします), 尊敬語 cho hành động của người nhận (ご確認ください) | Biết người gửi ít tuổi hơn: em – anh/chị ("Em xin báo cáo…"); chưa biết: tôi / chúng tôi – anh/chị, ghi chú cần xác nhận xưng hô | Lịch sự, trực tiếp: "Could you please confirm…", không khúm núm |
| Công ty với công ty | 弊社; 貴社 (văn viết) / 御社 (lời nói) | chúng tôi / Quý công ty | we / your company |
| Ngang hàng, nội bộ | です・ます nhẹ, ít 敬語 | anh/chị/em theo tuổi, hoặc tên | Thân thiện, ngắn |
| Tài liệu (thiết kế, đặc tả) | である調, không kính ngữ | không xưng hô, câu không chủ ngữ | Không "you", câu mệnh lệnh cho bước làm |

- **Câu đệm lịch sự (クッション言葉)** như 恐れ入りますが, お手数ですが, 差し支えなければ: dịch theo chức năng — VI "Phiền anh/chị…", "Nếu được, …"; EN "If possible, …", "Sorry to trouble you, but…" — hoặc bỏ khi tiếng đích đã đủ lịch sự nhờ cách xưng hô. Ngược lại, dịch sang JA thì thêm khi văn cảnh cần, dù nguồn VI / EN không có.
- **よろしくお願いします và các câu kết**: dịch theo việc câu đó làm trong thư — nhờ việc: "Nhờ anh/chị hỗ trợ ạ" / "Thank you for your help"; kết thư thông thường: "Trân trọng." / "Best regards,"; mở đầu quan hệ: "Rất mong được hợp tác". Không dịch thành "Xin hãy đối xử tốt với tôi".
- **お世話になっております** đầu thư: VI thường bỏ hoặc "Cảm ơn anh/chị đã hỗ trợ"; EN bỏ hoặc "Thank you for your continued support" (thư trang trọng).
- **Không hạ dạng khiêm nhường** khi rút gọn thư tiếng Nhật gửi cấp trên hoặc khách hàng.

## 4. Chủ ngữ bị lược và câu mơ hồ

- Tiếng Nhật hay lược chủ ngữ. Dịch sang VI / EN: thêm chủ ngữ khi ngữ cảnh cho thấy rõ ai làm; không rõ thì dùng câu không chủ ngữ (VI) hoặc bị động / "we" theo quy ước (EN), và ghi chú cần xác nhận nếu chủ thể ảnh hưởng tới trách nhiệm.
- Từ nhiều nghĩa (「検討します」 có thể là cân nhắc thật hoặc từ chối khéo; 「難しいです」 hay được dùng để từ chối khéo): dịch theo ngữ cảnh; ngữ cảnh không đủ thì dịch sát nghĩa đen ("khó") và ghi chú ngắn cách hiểu thứ hai. Không tự đổi thành "không làm được".
- Không tự "làm rõ" bằng cách thêm thông tin nguồn không có.

## 5. Số, ngày, tên, đơn vị

| Mục | JA | VI | EN |
|---|---|---|---|
| Số thập phân, hàng nghìn | 1,234.5 | 1.234,5 | 1,234.5 |
| Ngày | 2026/11/26, 2026年11月26日 | 26/11/2026 | theo quy ước của dự án (ISO 2026-11-26 an toàn nhất) |
| Đơn vị lớn | 1万 = 10.000; 1億 = 100 triệu; 10億 = 1 tỷ; 1兆 = 1.000 tỷ | triệu, tỷ | million, billion, trillion |
| Tiền | 円 | yên (JPY) | JPY |

- Dấu phân cách chỉ đổi ở số trong câu văn; phiên bản, mã, ID, code, dữ liệu máy đọc, bảng số liệu xuất từ hệ thống giữ nguyên ("v1.2.0", "1,234" trong CSV).
- Đổi 万 / 億 sang hàng nghìn / triệu là chỗ hay sai nhất: tính lại từng con số và đối chiếu với nguồn ("3.5億円" = 350 triệu yên = 350 million yen).
- Tên người Nhật: giữ thứ tự họ – tên và hậu tố theo văn cảnh (Tanaka-san → "anh / chị Tanaka" trong thư VI; "Mr./Ms. Tanaka" trong thư EN khi biết giới tính, không thì "Tanaka-san" hoặc họ tên đầy đủ). Tên người Việt trong văn bản JA / EN: giữ chữ Latin có dấu như nguồn trừ khi hệ thống không nhận dấu.
- Ngày tương đối ("thứ Sáu tới", 来週) giữ như nguồn; không đổi sang ngày lịch trừ khi được yêu cầu.
- Mốc và ngưỡng: 以上 = từ … trở lên (≥), 以下 = từ … trở xuống (≤), 未満 = dưới (<), 超 = trên (>); まで = đến (hết) mốc, までに = hạn chót trước hoặc đúng mốc. Không gộp ≥ với >.
- 年度 là năm tài chính (thường 4 – 3 năm sau ở Nhật): "2026年度" → "năm tài chính 2026" / "FY2026", không phải "năm 2026".
- Tên người viết bằng kanji chưa rõ cách đọc: giữ kanji, không đoán romaji; ghi chú cần xác nhận cách đọc.

## 6. Đầu ra

- Mặc định chỉ đưa bản dịch. Có điểm mơ hồ quan trọng: một ghi chú ngắn ở cuối ("Cần xác nhận: 「検討します」 ở câu 3 là cân nhắc thật hay từ chối khéo").
- Khi người dùng muốn đối chiếu: bảng hai cột nguồn – bản dịch, mỗi dòng một câu hoặc một đoạn.
- Văn bản sẽ đem dịch máy hoặc gửi người đọc không phải bản ngữ: viết lại nguồn theo `plain-language.md` (Strict) trước khi dịch, nếu người dùng đồng ý sửa nguồn.

## 7. Tự soát bản dịch

1. **Nghĩa** — đọc lại từng câu quan trọng theo chiều ngược (dịch nhẩm về ngôn ngữ nguồn): ý, chủ thể, mức chắc chắn có giữ không?
2. **Số và tên** — mọi số, đơn vị, ngày, tên, mã khớp nguồn; 万 / 億 đã tính lại.
3. **Lịch sự** — văn thể và xưng hô đúng quan hệ; một văn thể suốt bản dịch.
4. **Thuật ngữ** — theo glossary, một từ một khái niệm; không từ dịch máy (`vietnamese-register.md` § 3).
5. **Tự nhiên** — đọc như văn viết thẳng bằng ngôn ngữ đích: soát theo `ng-vocab-<lang>.md` và `ai-tells.md` của ngôn ngữ đích; chỉ sửa câu chữ, không đổi nghĩa.
6. **Định dạng** — cấu trúc, code, liên kết, bảng giữ nguyên; tiếng Việt ở dạng NFC.
