# Tiếng Việt — xưng hô, từ tiếng Anh, chính tả máy

Đọc cho mọi văn bản tiếng Việt viết, sửa hay dịch sang (cùng `style-guide.md` § 1). Ma trận xưng hô, quy tắc giữ từ tiếng Anh, danh sách từ dịch sai, quy tắc Unicode và dấu thanh phỏng theo bộ skill `vietnamese-language-skill` (MIT, thông báo bản quyền ở `NOTICES.md` của skill); phần áp dụng cho văn bản công việc và ví dụ viết lại cho skill này. Quy ước của dự án (`project_rules`, `glossary`) và của file có sẵn được ưu tiên.

## 1. Chọn cách xưng hô theo loại văn bản và kênh

Tiếng Việt không có "you" trung tính. Sai đại từ không chỉ hơi lạ mà làm văn bản như của một tổ chức khác.

| Loại văn bản / kênh | Gọi người đọc | Tự xưng | Ghi chú |
|---|---|---|---|
| Thiết kế, đặc tả, RFC, báo cáo kỹ thuật, postmortem, runbook, biên bản | Không xưng hô; dùng tên vai trò ("người vận hành", "lập trình viên") | Tên nhóm / tổ chức, hoặc không xưng | "bạn" ở đây là lỗi; dùng câu không chủ ngữ: "Cần cấu hình biến môi trường", "Hệ thống tự retry 3 lần" |
| Báo cáo gửi cấp trên, khách hàng | Không xưng trong thân báo cáo; thư kèm theo theo dòng dưới | "nhóm dự án", tên đơn vị | Khung § 1.1 của `style-guide.md` |
| README, hướng dẫn người dùng cuối, chữ trên giao diện, release note công khai | Theo quy ước sản phẩm có sẵn; chưa có quy ước thì "bạn" trong câu mô tả. Bước làm luôn viết mệnh lệnh không chủ ngữ ("Mở Cài đặt"), không "bạn hãy" | "chúng tôi" | Đây là quy tắc chung về "bạn"; các file khác trỏ về đây |
| Mail / chat công việc nội bộ | Theo quan hệ thật: "anh / chị / em", tên riêng | "em", "tôi", "mình" | Giữ đúng thứ bậc của nguồn; không đổi xưng hô khi sửa |
| Mail B2B, báo giá, đề xuất gửi đối tác | "anh/chị" (chưa rõ giới tính), "Quý công ty" (văn bản trang trọng) | "em" nếu người viết trẻ hơn / cấp dưới; "tôi" khi ngang hàng hoặc chưa rõ; "chúng tôi", "bên em" khi nói thay công ty | "bạn" trong mail B2B đọc như thư hàng loạt. Tuổi và thâm niên thắng chức danh: người mua trẻ chức nhưng lớn tuổi vẫn là "anh/chị" |
| Thông báo dịch vụ, trạng thái gửi khách hàng | "Quý khách" | "chúng tôi" | Ngôn ngữ thường, không thuật ngữ |
| Thông báo trang trọng, thông cáo | "Quý vị" | "chúng tôi" | |

- **Một cách xưng hô cho cả văn bản.** "Quý khách" ở đầu và "bạn" ở cuối là lỗi dễ thấy nhất. Muốn thân hơn ở một phần thì đổi độ dài câu và từ, không đổi đại từ.
- **"chúng tôi" và "chúng ta".** "chúng tôi" (không gồm người đọc) cho văn bản của tổ chức; "chúng ta" chỉ khi thật sự gồm người đọc. "chúng ta" trên trang giới thiệu công ty là lỗi hay gặp của AI.
- **"em" không phải tự hạ mình.** Người trẻ hơn / cấp dưới viết "em xin gửi anh báo giá" là đúng mực. Người cấp cao xưng "em" với người cấp dưới thì lạ.
- **Danh từ ngôi thứ ba không phải lời gọi.** "khách hàng", "người dùng" dùng trong điều khoản, mô tả; không viết "Khách hàng hãy đăng ký" — viết "Quý khách vui lòng đăng ký".
- **Mở và kết thư theo mức quan hệ.** "Kính gửi anh/chị …" (lần đầu, trang trọng) · "Chào anh/chị …" (đã quen) · "Anh/chị ơi" (chat, không dùng trong mail). "Thân mến" chỉ với người đã quen.

## 2. Văn thể theo loại văn bản (bổ sung `style-guide.md` § 1)

- Release note: thì quá khứ, mở bằng việc đã làm: "Đã sửa lỗi…", "Đã thêm…".
- User story: "Là [vai trò], tôi muốn [việc], để [lợi ích]". Không "Như một [vai trò]" (dịch máy từ "As a").
- Thông báo lỗi cho lập trình viên: nói điều gì xảy ra và cần làm gì; không "Quý khách"; không đổ lỗi người dùng.
- Khảo sát mới: tránh thang "đồng ý / không đồng ý" (người trả lời có xu hướng đồng ý); hỏi trực tiếp về tính chất cần đo ("Mức độ dễ tìm thấy nút Lưu"). Khi sửa câu chữ một bảng hỏi đang dùng, không đổi thang đo; chỉ nêu ghi chú.

## 3. Từ tiếng Anh: giữ hay dịch

Văn kỹ thuật tiếng Việt vốn song ngữ: tiếng Việt mang ngữ pháp, tiếng Anh mang danh từ kỹ thuật. Dịch các từ người trong ngành giữ nguyên là dấu hiệu dịch máy rõ nhất. Trục quyết định là **mức trang trọng**, không phải đúng sai.

| Tình huống | Làm gì |
|---|---|
| Tên công cụ, lệnh, khái niệm Git / CI (commit, merge, rebase, deploy, rollback, pipeline, pull request) | Giữ tiếng Anh |
| Tên môi trường (production, staging, dev) | Giữ tiếng Anh; không "môi trường sản xuất" |
| Chat, mô tả PR, code review, standup | Thuật ngữ tiếng Anh, ngữ pháp tiếng Việt |
| Đặc tả, tài liệu phát hành chính thức | Từ tiếng Việt chấp nhận được và thường được ưa ("bộ nhớ đệm", "cơ sở dữ liệu") |
| Danh từ người dùng cuối thấy trên giao diện | Dịch theo quy ước ("Lưu", "Hủy", "Cài đặt", "Đăng nhập", "Thử lại", "Đang tải…") |
| Định danh, tên nhánh, tên file, dòng tiêu đề commit | Tiếng Anh, ASCII, không dấu |

Từ có cả hai dạng (server / máy chủ, database / cơ sở dữ liệu, cache / bộ nhớ đệm, patch / bản vá): chọn một cho mỗi văn bản và giữ nguyên; dự án đã dùng dạng nào thì theo dạng đó. Đừng sửa quá tay theo chiều ngược lại: văn bản 80% từ tiếng Anh với vài chữ nối tiếng Việt cũng không tự nhiên.

Bảng dưới đây áp dụng cho chat, PR, tài liệu kỹ thuật nội bộ. Đặc tả, tài liệu phát hành chính thức theo glossary dự án có thể dùng từ tiếng Việt chuẩn (ví dụ "hợp nhất", "triển khai lên môi trường production"); cột ❌ là các cách dịch sai nghĩa hoặc không ai dùng ở bất kỳ mức trang trọng nào.

### Từ dịch sai hay gặp (bỏ)

| Tiếng Anh | ❌ Dịch máy | ✅ Cách nói quen |
|---|---|---|
| commit | "cam kết" (nghĩa là hứa) | commit |
| deploy to production | "triển khai đến sản xuất" | deploy lên production |
| merge | "hợp nhất nhánh" | merge |
| pull request | "yêu cầu kéo" | pull request |
| sprint | "chạy nước rút" | sprint |
| backlog | "tồn đọng" | backlog |
| roadmap | "bản đồ đường" | lộ trình / roadmap |
| user story | "câu chuyện người dùng" | user story |
| stakeholder | "người nắm giữ cổ phần" | stakeholder / các bên liên quan |
| endpoint | "điểm cuối" | endpoint |
| rollback | "cuộn lại" | rollback |
| empty state | "trạng thái trống" | màn hình trống |
| refresh the page | "làm tươi trang" | tải lại trang |
| something went wrong | "cái gì đó đã đi sai" | đã có lỗi xảy ra |
| as a user | "như một người dùng" | là người dùng |

Glossary của dự án thắng bảng này.

## 4. Unicode, dấu thanh, chữ không dấu

- **Luôn xuất Unicode NFC** (ký tự dựng sẵn: "ế" là một mã U+1EBF). Dạng NFD (tổ hợp) nhìn giống hệt nhưng làm hỏng font, sai số ký tự, tìm kiếm và so khớp không ra. Văn bản chép từ PDF và tên file trên macOS hay ở dạng NFD. Kiểm bằng `scripts/lint_text.py --lang vi`.
- **Một kiểu đặt dấu thanh cho cả văn bản.** Với "oa", "oe", "uy" ở âm tiết mở có hai kiểu: kiểu cũ ("hòa", "khỏe", "thủy", "hóa") và kiểu mới ("hoà", "khoẻ", "thuỷ", "hoá"). Cả hai đều đúng; lỗi là trộn hai kiểu. File có sẵn và dự án theo kiểu nào thì giữ kiểu đó; file có sẵn đã trộn thì theo kiểu chiếm đa số và ghi chú; tài liệu mới không có quy ước thì dùng kiểu cũ (kiểu phổ biến trong văn bản công việc). Không đổi dấu trong tên riêng, tên địa danh, thương hiệu, trích dẫn và tên file (giữ đúng như nguồn: "Khánh Hoà", "Thanh Hóa"). Âm tiết có phụ âm cuối ("toàn", "hoàng", "thuyền") không có hai kiểu.
- **Không bỏ dấu trong văn bản hiển thị.** Chữ không dấu chỉ dùng cho slug, định danh, chỉ mục tìm kiếm. Không đổi tên người sang không dấu: "Nguyễn" là tên, "Nguyen" là slug.

## 5. Bản địa hóa (khi viết chữ cho phần mềm)

- Câu tiếng Việt dài hơn tiếng Anh khoảng 25–30%: nút, nhãn có độ rộng cố định dễ bị cắt chữ.
- Tin nhắn SMS có dấu dùng mã UCS-2: mỗi đoạn còn 70 ký tự thay vì 160.
- Tiếng Việt không có số nhiều ngữ pháp: chuỗi ICU chỉ cần nhánh `other` (`=0` vẫn dùng được).
- Tìm kiếm phải không phân biệt dấu ("ca phe" tìm ra "cà phê"); sắp xếp dùng collation tiếng Việt ("đ" sau "d", trước "e").

## 6. Câu so sánh nhất trong văn bản quảng cáo

Trang sản phẩm, mô tả trên kho ứng dụng và nội dung giới thiệu sản phẩm, dịch vụ có thể là quảng cáo theo Luật Quảng cáo (Luật số 16/2012/QH13 và các văn bản sửa đổi, bổ sung). Luật cấm dùng các từ "nhất", "duy nhất", "tốt nhất", "số một" hoặc từ ngữ có ý nghĩa tương tự (ví dụ "hàng đầu") khi không có tài liệu hợp pháp chứng minh. Khi **viết mới** hoặc **Rewrite**: không dùng các cụm đó, hoặc thay bằng sự thật đo được mà nguồn có. Khi **Polish / Humanize**: giữ nguyên và ghi chú ở cuối "cần chứng cứ cho '…' (Luật Quảng cáo)"; người dùng nói có chứng cứ thì giữ và ghi chú chứng cứ là gì. Skill này không tư vấn pháp lý: văn bản quảng cáo quan trọng cần người phụ trách pháp lý duyệt và đối chiếu văn bản luật hiện hành.

## 7. Tự soát tiếng Việt (bổ sung bảng của `ng-vocab-vi.md`)

1. Một cách xưng hô suốt văn bản, đúng loại văn bản và kênh (§ 1); tài liệu kỹ thuật không có "bạn"; không trộn "Quý khách" với "bạn".
2. Tự xưng đúng vị trí người viết so với người đọc ("em" / "tôi" / "chúng tôi" / "bên em").
3. Từ tiếng Anh giữ hay dịch theo mức trang trọng; một dạng cho một từ; không từ dịch máy ở § 3.
4. Định danh, nhánh, tiêu đề commit không dấu; văn bản hiển thị có dấu.
5. Một kiểu dấu thanh; Unicode NFC.
6. Văn bản quảng cáo: không câu so sánh nhất thiếu chứng cứ.

---

Thông báo bản quyền và toàn văn giấy phép MIT của `vietnamese-language-skill`: `NOTICES.md` (thư mục gốc của skill).
