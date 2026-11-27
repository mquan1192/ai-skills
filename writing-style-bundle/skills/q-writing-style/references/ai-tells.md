# Dấu hiệu văn AI — nhận ra và sửa

Đọc khi chạy chế độ Humanize hoặc Check, và ở bước soát bản nháp của mọi chế độ. Danh mục nhóm, thứ tự độ mạnh và phần "Khi nào không sửa" phỏng theo skill `humanizer` (MIT, thông báo bản quyền ở `NOTICES.md` của skill); ví dụ tiếng Việt, tiếng Nhật viết mới cho skill này.

## Vì sao văn AI có những dấu hiệu này

Mô hình ngôn ngữ chọn cách viết hợp với nhiều người đọc nhất, nên câu chữ đều đều và chung chung. Người viết thật chọn cho một người đọc, một chủ đề, nên câu chữ không đều và cụ thể. Mọi dấu hiệu dưới đây là một dạng của lựa chọn "mặc định" đó:

- **Dàn dựng** — câu báo hiệu tầm quan trọng thay vì thêm sự thật.
- **Nhịp theo luật** — bộ ba, gạch ngang dài, câu mở giống nhau dùng khắp nơi, dù nghĩa không cần.
- **Thổi phồng** — chuyện bình thường được gọi là bước ngoặt, di sản, có chuyên gia đứng sau.
- **Trình bày theo luật** — in đậm, viết hoa, emoji gắn vào mọi mục.
- **Đồ thừa** — lời chào, lời mời của chatbot; ghi chú về cách soạn còn sót lại.
- **Sai người đọc** — trả lời trong luồng mà giảng lại bối cảnh người đọc đã biết.

Mỗi câu giữ lại phải đưa cho người đọc điều họ chưa có. Từ ngữ "kiểu AI" đổi theo từng thế hệ mô hình; thói quen cấu trúc thì ở lại, nên nhóm A–B đứng đầu.

## Độ mạnh: khi nào được sửa

- **Mạnh** (nhóm A, mục 1–5): thấy một lần là đủ lý do sửa.
- **Thường**: sửa khi rõ ràng câu không thêm thông tin.
- **Yếu** (ghi *yếu*): một mình chưa đủ; chỉ sửa khi cùng đoạn có thêm dấu hiệu khác.

Ở chế độ Humanize, chỉ đụng tới câu có dấu hiệu, và chỉ đổi phần gây ra dấu hiệu đó; câu không dính gì để y nguyên, khung bài (tiêu đề, thứ tự mục, danh sách, bảng) giữ nguyên. Chưa chắc là dấu hiệu thì coi như không phải. Các chế độ Rewrite / Voice được viết lại rộng hơn, nhưng vẫn theo quy tắc giữ nghĩa của `SKILL.md`.

## A. Dàn dựng thay vì nói thẳng (mạnh)

| # | Dấu hiệu | Dạng hay gặp | Sửa |
|---|---|---|---|
| 1 | Phủ định để nâng (không phải X mà là Y) | EN: "not X but Y", "it's not just X, it's Y", "X rather than Y", tách hai câu "This does not mean X. It means Y." · VI: "không phải… mà là…", "không chỉ… mà còn…" khi chỉ có một ý thật, "vấn đề không nằm ở… mà ở…", "tưởng là… hóa ra…" · JA: 「〜ではなく〜だ」「〜というより〜」「一見〜だが実は〜」 | Nói thẳng vế khẳng định. Giữ phép đối chỉ khi vế phủ định sửa một hiểu lầm người đọc thật sự có, hoặc cả hai vế đều mang thông tin |
| 2 | Câu chốt một dòng, mảnh câu kịch tính | Đoạn một câu nhắc lại đoạn trước; "Đó mới là điều quan trọng.", "Hãy đọc lại câu đó."; câu đặt tên cho điều ví dụ vừa cho thấy ("Điều này cho thấy tầm quan trọng của…"); chuỗi mảnh câu ("Không tiếng ồn. Không chờ đợi."); "Tóm lại" nhắc lại phán đoán đã nói | Bỏ câu chốt lặp ý. Giữ câu ngắn khi nó mang sự thật hay hệ quả mới. Gộp chuỗi mảnh câu thành một câu có ý cụ thể |
| 3 | Câu nghe sâu sắc | "Câu hỏi thực sự là…", "Suy cho cùng…", "Cốt lõi của vấn đề…", "X là ngôn ngữ của Y", "X không phải công cụ mà là tấm gương" · JA: 「本質的には」「結局のところ」 | Thay bằng nhận định cụ thể |
| 4 | Dạo đầu trước khi vào ý | "Hãy cùng tìm hiểu…", "Dưới đây là những gì bạn cần biết", "Nói thật nhé?", "Vấn đề là thế này:", "Phần khó nhất là…" (khi không gọi tên thứ đó) · EN: "Let's dive in", "Here's the thing" · JA: 「では見ていきましょう」 | Bỏ phần dạo đầu, nói luôn ý; "phần khó là X" → nói X |
| 5 | Cãi với người không có mặt | "Tôi không nói rằng…", "Nói cho rõ…", "Có thể bạn nghĩ… nhưng…", "Một cách làm hấp dẫn là… nhưng…" khi không ai nêu cách đó | Bỏ phần biện hộ; nếu có ý thật thì nói ý đó. Giữ phản biện có ghi nguồn hoặc phương án người đọc thật sự cân nhắc |

## B. Nhịp theo luật

| # | Dấu hiệu | Sửa |
|---|---|---|
| 6 | Bộ ba gượng: ba danh từ, ba ví dụ song song, ba câu ngắn rồi một bài học ("đổi mới, cảm hứng và tầm nhìn") | Mỗi mục phải là một ý khác nhau; không thì gộp hoặc phát triển mục mạnh nhất. Nghĩa cần ba thì giữ ba |
| 7 | Nhiều câu liền nhau mở bằng cùng chủ ngữ ("Hệ thống… Hệ thống… Hệ thống…") | Gộp câu, đổi chủ ngữ, hoặc mở bằng hành động; không cấm hẳn từ đó |
| 8 | Gạch ngang dài (—, –, ` -- `) dùng làm dấu nối giữa hai mệnh đề, lặp lại nhiều lần | Từ hai gạch nối mệnh đề trong một đoạn: thay bằng dấu chấm, phẩy, hai chấm, ngoặc, hoặc viết lại câu. Một gạch là *yếu*. Không tính: gạch trong code, lệnh, đường dẫn, URL; khoảng số ("5–10"); cặp tên ("Nhật – Việt – Anh", "Hà Nội – Tokyo"); dòng nhãn kiểu "1. Đúng — …" và tiêu đề đã có quy ước; mẫu giọng văn / quy ước file có dùng gạch (khi đó giữ tần suất tương đương) |
| 9 | Rào đón chồng lớp: "có lẽ có thể phần nào", "could potentially", 「〜かもしれない可能性がある」 | Giữ một mức không chắc chắn đúng như nguồn; bỏ phần chồng. "có lẽ", "thường" đứng một mình là thói quen người, không phải dấu hiệu. *Yếu* |
| 10 | (EN) Gạch nối ghép sau danh từ: "the report is high-quality" | Giữ gạch nối trước danh từ, bỏ sau danh từ. *Yếu* |
| 11 | Bị động, mất chủ thể: "Kết quả được lưu tự động" | Thể chủ động khi làm rõ ai làm gì (`style-guide.md` § 0 mục 2). *Yếu* |

## C. Thổi phồng và mượn uy tín

Sự thật bên dưới thường đúng: giữ sự thật, bỏ phần trang trí.

| # | Dấu hiệu | Sửa |
|---|---|---|
| 12 | Từ AI dùng quá nhiều — EN: delve, crucial, pivotal, robust (nghĩa bóng), seamless, showcase, underscore, testament, tapestry, landscape (nghĩa trừu tượng), vibrant, meticulous, intricate, enhance · VI: "then chốt", "vượt trội", "toàn diện", "đột phá", "mạnh mẽ", "nâng tầm", "khai phóng", "hành trình" (nghĩa bóng), "bức tranh toàn cảnh" · JA: 「不可欠」「重要な役割を果たす」「包括的」「シームレス」 | Thay bằng từ thường hoặc bỏ; xem thêm `ng-vocab-<lang>.md` |
| 13 | Thổi phồng ý nghĩa: "đánh dấu bước ngoặt", "góp phần định hình", "để lại dấu ấn", "mở ra kỷ nguyên mới", "tương lai đầy hứa hẹn"; mục khuôn "Thách thức và triển vọng" | Giữ sự thật, bỏ ý nghĩa gán thêm; kết ở sự thật cụ thể cuối cùng hoặc kế hoạch thật nếu nguồn có |
| 14 | Liên hệ mơ hồ: "gắn liền với", "liên quan đến", "associated with" | Gọi tên quan hệ (sáng lập, phụ trách, gây ra). Không biết quan hệ thì giữ cách nói cũ |
| 15 | Cụm phân từ gắn thêm cho "sâu": EN "…, highlighting / reflecting / ensuring…"; VI "…, qua đó khẳng định…", "…, góp phần thể hiện…" | Giữ sự thật; bỏ cụm gắn thêm trừ khi nguồn chứng minh điều nó nói |
| 16 | Giọng quảng cáo: "nằm giữa lòng", "điểm đến không thể bỏ lỡ", "trải nghiệm tuyệt vời", "renowned", "breathtaking" | Nói thứ đó là gì. Tiếng Việt: câu so sánh nhất có thể là quảng cáo phải có chứng cứ (`vietnamese-register.md` § 6) |
| 17 | Mượn uy tín: "các chuyên gia cho rằng", "nhiều nghiên cứu chỉ ra", danh sách báo đài đã nhắc tên | Nguồn (văn bản người dùng đưa) nêu tên nguồn thật thì dùng tên đó. Không có thì giữ nhận định và ghi chú "cần nguồn" ở cuối; chỉ bỏ ở chế độ Rewrite khi người dùng đồng ý. Thiếu trích dẫn một mình không phải dấu hiệu |
| 18 | Né "là / có": "đóng vai trò là", "đóng vai trò như", "serves as", "boasts", "features" | Dùng "là", "có" |

## D. Trình bày theo luật

| # | Dấu hiệu | Sửa |
|---|---|---|
| 19 | In đậm trang trí; danh sách mà mục nào cũng có nhãn đậm và dấu hai chấm | Bỏ in đậm; nhãn không mang thông tin riêng thì viết thành câu. Giữ in đậm cho kết luận hoặc chỗ dễ hiểu sai (`style-guide.md` § 0 mục 5) |
| 20 | Tiêu đề trang trí: Viết Hoa Mọi Chữ (EN), emoji hay mũi tên trong tiêu đề, đường kẻ ngang giữa mọi mục, tiêu đề cấp 1 lặp lại tên tài liệu, tiêu đề viết cho hay ("Quyết định, trên một màn hình") | Tiêu đề gọi tên nội dung, viết hoa kiểu câu; bỏ trang trí |
| 21 | Ngoặc kép cong “…” khi người viết / định dạng đích dùng ngoặc thẳng | Theo quy ước của file. *Yếu* |

## E. Đồ thừa của chat và của bản nháp (bỏ ngay)

| # | Dấu hiệu | Sửa |
|---|---|---|
| 22 | Lời chatbot: "Câu hỏi rất hay!", "Chắc chắn rồi!", "Hy vọng thông tin này hữu ích", "Bạn có muốn em…?", "Dưới đây là…" · JA: 「お役に立てれば幸いです」(trong văn bản độc lập) | Bỏ lớp bọc, giữ nội dung. Lời chào và ký tên của thư thật thì giữ |
| 23 | Rào về giới hạn hiểu biết của mô hình rồi đoán lấp chỗ trống: "chưa có nhiều tài liệu công khai… có lẽ ông ấy…", "tính đến lần cập nhật dữ liệu cuối…" | Bỏ phần đoán; nói rõ nguồn không cho biết điều gì. Mốc thời gian và phạm vi thật của số liệu ("theo số liệu đến 30/11", "theo khảo sát nội bộ") không phải dấu hiệu: giữ nguyên |
| 24 | Câu đầu lặp lại tiêu đề ngay bên trên | Bỏ câu lặp |
| 25 | Viết về chính tài liệu thay vì chủ đề: "hàm này được thêm để thay cách cũ…", "mọi điểm chưa xác nhận đều được đánh dấu thay vì đoán" (câu dẫn bảng và "Nhận xét:" của khung báo cáo § 1.1 không tính) | Nói về chủ đề. Lịch sử thay đổi chỉ để trong changelog, release note, hướng dẫn chuyển đổi. Giữ ghi chú nguồn người đọc theo được và lưu ý làm đổi việc người đọc phải làm. *Yếu* khi chỉ một câu |

## F. Sai người đọc

| # | Dấu hiệu | Sửa |
|---|---|---|
| 26 | Trả lời trong luồng mà kể lại vấn đề, quá trình chẩn đoán, bằng chứng, rồi mới tới quyết định ở dòng cuối | Quyết định lên đầu; chỉ giữ lý do có thể đổi việc người đọc đồng ý hay không (thường là một sự thật họ chưa có và liên kết cần để làm). Chẩn đoán đầy đủ để cho ticket / tài liệu. Chỉ áp dụng khi thấy được ngữ cảnh luồng |

## Hay sót sau khi sửa

Soát lại bản nháp tìm đúng các dấu hiệu này: 1 (phủ định để nâng), 2 (câu chốt), 6 (bộ ba), 8 (gạch ngang), 19 (nhãn đậm). Các mục 6, 9 và 19 là nơi bản sửa hay làm rơi sự thật, tên, số, ngày, trích dẫn: đối chiếu lại với nguồn.

## Khi nào không sửa

- Cụm từ nằm trong trích dẫn, tên riêng, tiêu đề tác phẩm, hoặc đoạn đang bàn về chính cụm đó.
- Lời chào, lời cảm ơn và ký tên của thư; "nhờ anh/chị xem giúp" trong tin nhắn thật. Những thứ này có từ trước chatbot.
- Văn bản viết trước cuối năm 2022 không phải văn AI.
- Câu chữ bắt buộc của khung báo cáo tiếng Việt (`style-guide.md` § 1.1): câu dẫn bảng, "Nhận xét:", "Kết luận:", "Định hướng:".
- Lặp lại tên đầy đủ của mô-đun, sản phẩm thay vì đại từ: văn kỹ thuật cần một tên cho một thứ (`style-guide.md` § 0 mục 3).
- Liệt kê, phép đối, câu hỏi khi nghĩa thật sự cần; tiêu đề dạng câu hỏi chỉ hợp ở bài viết (báo cáo, tài liệu theo `document-patterns.md`: tiêu đề là câu khẳng định).
- Dấu hiệu *yếu* đứng một mình. Người đọc đoán "văn AI" theo cảm giác thường sai, và văn người cũng nhiễm thói quen AI: cần nhiều dấu hiệu cùng lúc.
- **Văn bản thân mật** (tin chat, comment, bài than phiền): viết thường, viết tắt ("ko", "nhé", "lmk"), câu cụt, nhấn mạnh kiểu "Tệ. Thật. Sự." là giọng của thể loại. Một dấu hiệu chưa đủ (trừ lời chatbot, mục 22); cần hai dấu hiệu không liên quan mới viết lại. Giữ nguyên độ gắt của người viết: "tệ hại" vẫn là "tệ hại".

Nếu có hồ sơ giọng văn hoặc mẫu của người viết (`voice-profile.md`) cho thấy họ vốn viết như vậy (dùng gạch ngang, câu ngắn cụt, nhiều câu hỏi), thì đó là giọng của họ, không phải dấu vết AI.

## Giữ những chi tiết mang giọng người viết

Trừ khi làm hỏng nghĩa, giữ: chi tiết cụ thể và lạ (một địa chỉ thật, một câu nói thật); cảm xúc lẫn lộn, điều chưa giải quyết; từ lóng, liên tưởng gắn với một thời, một nhóm; lựa chọn ngôi thứ nhất người viết giải thích được; câu chen ngang, tự sửa lời thật. Bài viết cá nhân giữ quan điểm, sự không chắc chắn, sự hài hước của người viết; văn bản kỹ thuật, pháp lý, tham khảo thì trung tính.

---

Danh mục gốc của `humanizer` dựa trên trang Wikipedia "Signs of AI writing" (WikiProject AI Cleanup); mục "Khi nào không sửa" phỏng theo phần "When not to act" và "Voice" của `humanizer`, cộng các ngoại lệ riêng của skill này. Ý chung "chỉ sửa câu có dấu hiệu" cũng có trong `lieflat-less-ai-tone` (repo `writing-dna-skill`, PolyForm Noncommercial); file này không dùng văn bản, danh sách hay cấu trúc của skill đó.

Thông báo bản quyền và toàn văn giấy phép MIT của `humanizer`: `NOTICES.md` (thư mục gốc của skill).
