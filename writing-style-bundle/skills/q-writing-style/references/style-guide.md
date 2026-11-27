# Hướng dẫn văn phong — ngôn ngữ, số liệu và lỗi hay gặp

Chi tiết cho các nguyên tắc chính của `SKILL.md`. Glossary và quy tắc riêng của dự án (khóa `project_rules`, `glossary` trong `.writing-style/style.config.json`) được ưu tiên hơn file này.

## 0. Nguyên tắc chung (mọi ngôn ngữ)

Áp dụng cho văn bản VI / JA / EN và mọi ngôn ngữ khác, khi viết, sửa và sau khi dịch. Mục của từng ngôn ngữ (§ 1–3) ghi cách áp dụng riêng. Mọi chỗ "thay bằng con số / điều kiện / chủ thể / cơ chế" trong file này và các file `ng-vocab-*` chỉ dùng điều nguồn có; nguồn không có thì giữ cách nói chung và ghi chú "cần xác nhận", không bịa.

1. **Lập luận chặt — đứng đầu khi các quy tắc xung đột.** Giữ mức không chắc chắn có thật: không đoán, không khẳng định khi chưa có căn cứ. Không đánh đồng hai thứ khác nhau. Không quy nhiều nguyên nhân về một. Khi nói A dẫn tới B, nói cơ chế: vì sao A dẫn tới B.
2. **Chủ thể rõ.** Viết thể chủ động khi nguồn cho biết ai làm; người hoặc thành phần thực hiện làm chủ ngữ ("mô-đun nhập liệu ghi log lỗi", không viết "log lỗi được ghi"). Nguồn không nói ai làm thì giữ bị động, không đoán. Trong tài liệu (thiết kế, đặc tả, báo cáo) không gọi người đọc là "bạn", "you", "あなた"; dùng tên vai trò (người dùng, người vận hành, lập trình viên). Hướng dẫn người dùng cuối, README, chữ trên giao diện theo quy ước của sản phẩm (tiếng Việt: `vietnamese-register.md` § 1). Không dùng từ mơ hồ "AI", "công cụ", "hệ thống" khi đã có tên cụ thể (tên sản phẩm, mô-đun, lớp, màn hình).
3. **Một thuật ngữ, một từ** suốt tài liệu (§ 4, W-2). Glossary dự án quyết trước, sau đó là từ quen dùng trong ngành.
4. **Một đoạn, một chủ đề.** Câu đầu đoạn nói đoạn đó bàn về gì; mạch lập luận đi một chiều; kết luận nói một lần.
5. **Không cường điệu.** Không câu hỏi tu từ, không dẫn dắt vòng vo, không câu "chốt" kịch tính, không từ gây hoảng khi nói về rủi ro. In đậm chỉ cho kết luận và chỗ dễ hiểu sai.
6. **Không lặp.** Không nói lại cùng một ý bằng chữ khác; không tóm tắt ngay sau đoạn vừa mô tả; không viết câu chỉ để nối khi câu đó không thêm thông tin.
7. **Văn thể theo loại tài liệu.** Thiết kế, đặc tả (spec), slide viết khác báo cáo, mail, chat. Cách áp dụng cho từng ngôn ngữ ghi ở § 1 (VI), § 2 (JA), § 3 (EN).
8. **Sửa hoặc dịch file có sẵn: giữ quy ước của file đó** — văn thể, khoảng trắng, cách viết số, tên và ký hiệu. Quy tắc dành cho tài liệu mới (văn thể theo loại tài liệu ở mục 7, khoảng trắng tiếng Nhật ở § 2) không áp ngược vào file có sẵn; chỉ đổi khi người dùng yêu cầu.
9. **Từ và cụm rỗng.** Soát theo `references/ng-vocab-<lang>.md` của ngôn ngữ đang viết (`ng-vocab-vi.md`, `ng-vocab-ja.md`, `ng-vocab-en.md`). Chỉ bỏ hoặc thay khi từ không mang thông tin; glossary dự án thắng danh sách này; từ nêu yêu cầu bắt buộc ("phải", "必ず", "must") giữ nguyên. Ngôn ngữ chưa có file riêng: áp các mục 1–8.
10. **Dấu vết AI.** Không dàn dựng, không nhịp theo luật, không thổi phồng, không trình bày trang trí, không lời chatbot: `references/ai-tells.md` (áp cho mọi ngôn ngữ; ví dụ có VI / JA / EN).

## 1. Tiếng Việt

- Chuyên nghiệp và ngắn; dễ đọc, không hành chính; đúng thuật ngữ kỹ thuật; ưu tiên động từ và câu chủ động.
- Để ý các cụm sau khi chúng lặp hoặc không thêm nghĩa: "Hiện tại thì…", "Về phần…", "Nhằm mục đích…", "Tiến hành việc…", "Thực hiện công việc…", "Có thể thấy rằng…", "Điều quan trọng cần nhấn mạnh là…". Không xóa máy móc khi chúng mang nghĩa (ví dụ "hiện tại" là mốc thời gian thật).
- Dạng câu cần tránh (W-3): "không chỉ … mà còn …" khi không có hai ý thật · "đóng vai trò là" · "có thể nói rằng" · danh sách độn cho đủ ba mục · câu kết chỉ nhắc lại đoạn văn.
- Văn thể theo loại tài liệu (§ 0 mục 7): thiết kế, đặc tả, slide → câu ngắn, dòng liệt kê có thể ở dạng danh từ hoặc động từ không chủ ngữ ("Kiểm tra định dạng đầu vào trước khi lưu"); báo cáo, mail → câu đầy đủ, nêu chủ thể (§ 1.1); chat → câu ngắn, đủ ý. Từ và cụm rỗng tiếng Việt: `ng-vocab-vi.md`.
- Xưng hô theo loại văn bản và kênh, từ tiếng Anh giữ hay dịch, từ dịch máy cần bỏ, Unicode NFC và kiểu đặt dấu thanh: `vietnamese-register.md`.

### 1.1 Báo cáo và tài liệu tiếng Việt — văn phong và khung

Áp dụng cho mọi báo cáo / tài liệu tiếng Việt; chỉ là văn phong và cách trình bày, không có danh sách từ cố định. Đây là bản duy nhất; các file khác trỏ về đây.

- **Văn phong**: trung tính, khách quan, dựa trên số liệu ("ghi nhận", "cho thấy"); kết luận có chừng mực ("cần tiếp tục kiểm chứng …"); câu đầy đủ, nêu rõ chủ thể (tên tổ chức, tên sản phẩm đầy đủ); không dùng câu văn nói, không đánh giá cảm tính.
- **Cách báo cáo**: tiêu đề + thông tin đơn vị thực hiện → mục đích / phạm vi → phương pháp ghi nhận và đánh giá → kết quả (mỗi bảng có 1 câu dẫn nói mục đích; sau bảng số có "Nhận xét:" / "Kết luận:" nêu đúng con số chính) → điều kiện / bảo mật khi triển khai (nếu có) → kết luận chung, "Định hướng:". Mục đánh số 1. / 1.1.
- **Trình bày**: nhãn và tiêu đề ngắn, dạng danh từ, không dấu chấm cuối; nhãn khối kết cố định có dấu hai chấm; số kiểu Việt Nam (dấu phẩy thập phân, dấu chấm hàng nghìn: 1.234,5) cho số trong câu văn, còn phiên bản, mã, ID, code, dữ liệu máy đọc giữ nguyên, đơn vị viết bằng chữ; ngày dd/mm/yyyy.
- Quy tắc riêng của dự án (khóa `project_rules`) bổ sung cho mục này; tin chat ngắn hay ghi chú nội bộ không cần đủ khung báo cáo.

## 2. Tiếng Nhật

- Tiếng Nhật công việc tự nhiên: です・ます và 敬語 phù hợp; lịch sự nhưng không khiêm quá mức; câu ngắn, dễ đọc.
- Không dịch từng chữ từ tiếng Việt; giữ đúng chủ ngữ và thứ bậc; không nâng mức cam kết.
- Khi rút gọn tin gửi cấp trên hay khách hàng, giữ dạng khiêm nhường của động từ (ご報告します, 対応いたします), không đổi sang dạng thường.
- Không lặp ご確認 / ご対応 / いただけますでしょうか khi không cần.
- Các từ trạng thái không thay cho nhau được — giữ đúng từ nguồn muốn nói:

| Từ | Nghĩa |
|---|---|
| 予定 | dự kiến / theo kế hoạch |
| 検討中 | đang cân nhắc |
| 確認中 | đang xác nhận |
| 可能性があります | có thể, chưa xác nhận |
| 対応済み | đã xử lý xong |
| 対応中 | đang xử lý |

**Văn thể theo loại tài liệu** (§ 0 mục 7): thiết kế, đặc tả, slide → である調, dòng liệt kê có thể kết thúc bằng 体言止め; báo cáo, mail, chat gửi người → です・ます và các quy tắc ở trên. Sửa file tiếng Nhật có sẵn: giữ văn thể của file đó (§ 0 mục 8).

**Viết kỹ thuật tiếng Nhật** (phỏng theo skill `japanese-tech-writing`, giấy phép MIT; thông báo bản quyền ở `THIRD-PARTY-NOTICES.md` của gói và cuối `ng-vocab-ja.md`). Các mục 1–6 của § 0 áp dụng nguyên; phần riêng cho tiếng Nhật:

- Lập luận: không 断定 khi chưa có căn cứ; điều chưa chắc thì ghi rõ chưa chắc ở chỗ nào và vì sao.
- Chủ thể: thay động từ kiểu dịch che chủ thể bằng câu nêu ai / cái gì làm gì (「この結果は X を示唆している」→「測定値が X であることから、Y と判断できる」). Không あなた — dùng 利用者, 担当者, 開発者. Không 「AI」「ツール」「システム」 mơ hồ khi đã có tên sản phẩm, mô-đun hay lớp.
- Thuật ngữ: glossary dự án (khóa `glossary`) trước, sau đó là từ dịch quen dùng trong ngành; katakana đã cố định trong glossary giữ nguyên.
- Không câu chỉ để nối như 「以上をまとめると」「ここまで見てきたように」 khi sau đó không có gì mới.
- **Khoảng trắng — chỉ ở file tài liệu mới** (thiết kế, đặc tả, slide, báo cáo): khoảng trắng nửa cỡ giữa chữ Nhật và chữ / số La-tinh (「Python で書く」「約 3 倍」), không đặt cạnh 約物 (「（API）」「API、」). Văn bản chat, mail, ticket theo glossary và ví dụ giao tiếp của dự án; dạng cố định trong glossary dự án giữ nguyên; dịch hoặc sửa file có sẵn giữ quy ước của file đó (§ 0 mục 8).
- Từ và cụm cần bỏ hoặc thay, bảng tự soát tiếng Nhật: `ng-vocab-ja.md`.

## 3. English (EN)

- Văn bản EN dùng ngôn ngữ công việc đơn giản: ngắn, rõ, chủ động; từ thông dụng; chỉ thuật ngữ ngành cần thiết; không biệt ngữ kinh doanh hay giọng quảng cáo. Hướng dẫn, runbook, thông báo lỗi, prompt cho AI và văn bản cho người đọc không phải bản ngữ: thêm `plain-language.md` (câu ngắn, can / will / must, điều kiện trước lệnh).
- Văn thể theo loại tài liệu (§ 0 mục 7): thiết kế, đặc tả, slide → câu ngắn, dòng liệt kê dạng cụm danh từ hoặc câu mệnh lệnh; yêu cầu bắt buộc viết "must" / "shall" theo quy ước sẵn có của tài liệu; báo cáo, mail → câu đầy đủ, chủ động, có chủ ngữ; hướng dẫn thao tác dùng câu mệnh lệnh thay cho "you". Từ và cụm rỗng EN: `ng-vocab-en.md`.

## 4. Thuật ngữ

- Giữ thuật ngữ dự án hoặc nguồn đã dùng (tên mô-đun, thuật toán, màn hình, sản phẩm, phiên bản; ví dụ API, GPU, Pipeline, Benchmark). Không đổi tên thuật toán, mô-đun hay phiên bản; không "chuẩn hóa" một thuật ngữ chưa được định nghĩa.
- Một thứ, một tên (W-2): khi một thứ đã có tên trong tài liệu ("gói cập nhật") thì giữ tên đó; không đổi sang "bản cập nhật", "file gửi lên" cho cùng thứ.
- Tài liệu chuyên ngành: chỉ thêm chú thích thuật ngữ EN / JA / VI khi được yêu cầu hoặc khi khái niệm cần giải thích; không thêm vào mọi văn bản.
- Viết tắt: dùng ít. Xử lý mỗi từ viết tắt ở lần dùng đầu — "dạng đầy đủ (VIẾT TẮT)" — hoặc trong một danh sách thuật ngữ của tài liệu, để người ngoài nhóm không gặp từ viết tắt chưa giải thích:
  - Từ phổ biến, không mơ hồ (ví dụ TC = test case, OK / NG = đạt / không đạt, SRS = đặc tả yêu cầu phần mềm) và từ nguồn hay glossary đã định nghĩa: viết đầy đủ.
  - Từ riêng của nhóm / dự án mà nguồn không định nghĩa (tên môi trường, vai trò, hệ thống, nhóm): không đoán dạng đầy đủ. Giữ nguyên và đánh dấu ở lần dùng đầu, ví dụ "STG (cần xác nhận dạng đầy đủ)"; nhiều từ chưa rõ thì thêm một yêu cầu ngắn ở cuối.

## 5. Số liệu và phép tính

- Giữ đúng giá trị, đơn vị và mốc thời gian. Không tự tính số mới trừ khi được yêu cầu; nếu được yêu cầu, dùng số có nguồn và kiểm công thức.
- Ngày tương đối ("hôm nay", "thứ Sáu tới", "tuần sau") giữ như nguồn; không đổi thành ngày lịch trừ khi được yêu cầu.
- Không làm tròn làm đổi nghĩa; không đổi mẫu số hay điều kiện so sánh.
- Giữ cỡ mẫu, bộ dữ liệu thử và điều kiện đánh giá khi nguồn có.
- Số đo (hiệu năng, thời gian, số lần chạy thử): ghi số lần chạy, độ dao động (min–max hoặc độ lệch), công cụ đo và yếu tố giới hạn khi biết; chạy một lần thì ghi "1 lần". Nguồn không có thì không thêm — giữ điều nguồn có, không ngụ ý nhiều hơn.
- Từ mơ hồ cần con số hay định nghĩa (W-4): "nhanh", "ổn định", "dễ dùng", "tối ưu", "đáng kể" → ghi giá trị đo; chưa đo thì viết "chưa đo" (khi sửa văn bản của người khác: giữ từ và đánh dấu, không bịa số).
- Tách bạch: mốc chuẩn và thực tế, giá trị tuyệt đối và tỉ lệ, dữ liệu quan sát và tự khai, số đo và ý kiến, tương quan và nhân quả.

## 6. Dữ liệu thiếu — giữ đúng trạng thái

| Ghi | Nghĩa |
|---|---|
| `0` | giá trị thật bằng không |
| để trống | chưa nhập / không có dữ liệu |
| N/A | không áp dụng |
| chưa đo | chưa có kết quả đánh giá |
| chưa xác nhận | có thông tin nhưng chưa được xác nhận |

Không đổi cái này thành cái kia.

## 7. Nguồn và tham chiếu

- Nhiều tài liệu: biết nguồn của từng câu; giữ đúng mã, phiên bản, ngày và dạng tham chiếu như `(Tài liệu - 3.5)`.
- Không gộp nội dung mâu thuẫn thành một kết luận: viết một dòng ngắn nêu điều cần xác nhận. Không bịa nguồn hay trích dẫn.

## 8. Giới hạn của kết luận

Giữ mọi giới hạn ảnh hưởng tới kết luận: thiếu dữ liệu, mẫu nhỏ, điều kiện thử khác, khách hàng chưa xác nhận, chưa thử trên môi trường thật, chỉ là kết quả thử nghiệm hay bản mẫu. Xu hướng của một chỉ số chưa phải bằng chứng cải thiện.

## 9. Những điều cần tránh

- Khen, chào hỏi hay câu rào đón nguồn không cần; nhắc lại yêu cầu của người dùng; giải thích thay đổi không ai hỏi.
- Nhiều tiêu đề cho nội dung đơn giản; bảng khi một đoạn văn hay gạch đầu dòng đã rõ.
- Rút ngắn bằng cách bỏ ý; giọng quảng cáo; câu chung chung kiểu tư vấn.
- Phép thử "dự án khác" (W-1): câu đặt vào tài liệu của dự án khác vẫn đúng y nguyên là câu không nói gì — bỏ đi, hoặc thay bằng cơ chế hay con số cụ thể mà nguồn có.
- Dòng không quyết gì (W-5): "xử lý các trường hợp ngoại lệ", "sẽ xem xét", "TBD" → nói ai làm gì, khi nào **nếu nguồn có**; nguồn không có thì đổi dòng đó thành câu hỏi mở kèm người phải trả lời ("Cần xác nhận: … — <ai trả lời>"). Không bịa người phụ trách hay ngày.
- Thêm giả thuyết, việc cần làm hay hạn chót; đổi kết luận hay trách nhiệm; biến đề xuất thành quyết định; kết luận vượt quá số liệu.

## 10. Lỗi hay gặp (soát nhanh)

| Lỗi | Ví dụ lệch nghĩa |
|---|---|
| Nâng trạng thái | "có thể cải thiện" → "đã cải thiện"; 可能性があります → です |
| Mất điều kiện | "sau khi nhận file X sẽ phân tích" → "sẽ phân tích sớm" |
| Bịa người / hạn | "nhờ kiểm tra" → "nhờ kiểm tra trước thứ Sáu" |
| Gộp nguồn | hai giá trị khác nhau → một giá trị |
| Mất ngoại lệ | "mọi trường hợp trừ B" → "mọi trường hợp" |
| Thừa cấu trúc | tin chat 3 dòng → tài liệu có tiêu đề và nhiều mục |
