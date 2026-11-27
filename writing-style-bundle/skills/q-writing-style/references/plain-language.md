# Viết đơn giản (Plain) — hướng dẫn, runbook, thông báo lỗi, prompt

Đọc khi chạy chế độ Plain, và khi viết hướng dẫn, runbook, thông báo lỗi, release note, commit / PR, prompt cho AI, hoặc văn bản sẽ đem dịch máy. Quy tắc tiếng Anh phỏng theo skill `SimpleEnglish` (MIT, thông báo bản quyền ở `NOTICES.md` của skill), skill đó lại dựa trên tinh thần của chuẩn ASD-STE100 (Simplified Technical English). Phần áp dụng cho tiếng Việt và tiếng Nhật viết mới cho skill này.

Mục tiêu: một người đọc thông minh nhưng ngoài ngành hiểu đúng sau một lần đọc. Không dùng cho văn quảng cáo hay văn thương hiệu (Plain bỏ phần thuyết phục): khi đó nói rõ và đề xuất dùng Plain cho phần tài liệu đi kèm.

## 1. Quy tắc chung (mọi ngôn ngữ)

1. **Phân loại từng đoạn.** *Thủ tục* (bảo người đọc làm gì): câu mệnh lệnh, một lệnh một câu. *Mô tả* (giải thích): thì đơn giản, một chủ đề một đoạn, tối đa khoảng sáu câu một đoạn.
2. **Không đụng** code, định danh, lệnh, cờ, đường dẫn, thông báo lỗi trích nguyên văn, tên sản phẩm và sự thật. Nguồn không cho số hay nguyên nhân thì giữ câu chung. Viết đơn giản không được xóa mức không chắc chắn có thật, lời khuyên, hay phần còn mở của một danh sách.
3. **Điều kiện đặt trước lệnh**, có dấu phẩy: "Nếu build lỗi, đọc log." / "If the build fails, read the log." / 「ビルドが失敗した場合は、ログを確認する。」
4. **Nêu chủ thể, thể chủ động.** Bước làm viết mệnh lệnh không chủ ngữ ("Chạy migration"); mô tả nêu chủ thể khi nguồn cho biết. Không biết ai làm thì giữ bị động; không đoán chủ thể. Xưng hô với người đọc theo `vietnamese-register.md` § 1.
5. **Một từ, một nghĩa** suốt văn bản. Khi nhiều từ chỉ cùng một việc (ví dụ "kiểm tra" và "xác nhận" cho cùng một thao tác), chọn một từ và giữ nguyên; khi chúng là các việc khác nhau (kiểm tra định dạng khác xác minh chữ ký) thì giữ các từ khác nhau. Chuỗi danh từ dài hơn ba từ thì tách bằng giới từ ("giá trị timeout của connection pool").
6. **Đưa thuật ngữ và điều kiện trước bước cần nó.** Định nghĩa khái niệm ở lần dùng đầu, dưới mười từ ("idempotent (chạy hai lần vẫn an toàn)"). Không định nghĩa tên sản phẩm, tên chuẩn (Postgres, S3, HTTP) hay chính công cụ tài liệu nói về. Nêu máy, cờ hoặc bước trước mà lệnh phụ thuộc **khi nguồn hoặc ngữ cảnh cho biết**: "Khởi động lại service" → "Khởi động lại service `sync` trên máy chạy job". Nguồn không cho biết thì không đoán: ghi "Cần xác nhận: máy chạy lệnh này" ở cuối. Định nghĩa thuật ngữ cũng chỉ dùng nghĩa nguồn hoặc nghĩa chuẩn của ngành.
7. **Nói sự thật, không nói tầm quan trọng.** Bỏ từ không mang sự thật ("đơn giản", "dễ dàng", "mạnh mẽ", "toàn diện", "nhằm mục đích"); không "không chỉ X mà còn Y"; không bộ ba trang trí; không đoạn "Tóm lại".
8. **Trình bày chỉ khi có cấu trúc thật.** Không nhãn đậm mở đầu, không in đậm để nhấn, không emoji, không tiêu đề cho đoạn hai câu. Danh sách dọc cho từ ba mục song song hoặc các bước; câu dẫn kết bằng dấu hai chấm; mỗi mục một lệnh.
9. **Cảnh báo: lệnh hoặc điều kiện trước, rủi ro sau.** "Không chạy lệnh này trên production. Lệnh xóa các dòng không khớp nguồn."
10. **Câu đầy đủ, không kiểu điện tín.** Ngắn nhưng đủ ngữ pháp: "Bảo đảm file tồn tại trước khi chạy lệnh", không "Check file trước run".

## 2. Tiếng Anh

- Độ dài câu: thủ tục tối đa 20 từ, mô tả tối đa 25 từ. Code trong backtick, số kèm đơn vị, tên riêng tính là một từ.
- Thì đơn giản; không present perfect ("has completed" → "completed"); không cụm "-ing" sau dấu phẩy (", making it easy" → câu mới).
- Động từ khiếm khuyết: **can, will, must**. "should" bắt buộc → "must"; "should" khuyên → "We recommend …" hoặc nói lý do ("X is better because Y"), không xóa lời khuyên; "may / could" chỉ phép hoặc khả năng làm được → "can". **"may / might / could" chỉ sự không chắc chắn thì giữ ý không chắc chắn** ("It is possible that …", "not confirmed"); không đổi thành "can" hay câu khẳng định. "would" → viết lại thành điều kiện.
- Ngữ pháp đủ: không viết tắt kiểu "don't", giữ mạo từ, giữ "that".
- Không dấu chấm phẩy, không gạch ngang dài: viết hai câu hoặc gọi tên quan hệ ("because", "but", "for example").
- Từ quy ước: "make sure that" thay check / verify / confirm / validate / ensure **khi chúng cùng nghĩa** "bảo đảm điều X đúng"; giữ từ riêng khi là thao tác khác (validate input, verify a signature). Một tên cho tệp cấu hình ("configuration") suốt văn bản. "e.g." → "for example", "i.e." → "that is". "etc." chỉ được bỏ khi nguồn cho đủ danh sách; không thì giữ ý còn mở ("and other items").
- Động từ một chữ thay cụm động từ khi cùng nghĩa ("decrease", không "go down"; "start", không "kick off").
- Bảng đổi từ: `ng-vocab-en.md` § "Plain swaps".
- Strict (chỉ khi người dùng nêu STE, ASD-STE100 hay "compliance"): áp mọi quy tắc trên như giới hạn cứng (không ngoại lệ về độ dài câu, động từ khiếm khuyết, dấu chấm phẩy); mỗi từ dùng một nghĩa và một từ loại; nói một lần rằng không công cụ nào bảo đảm tuân thủ hoàn toàn và bộ từ điển chính thức tải miễn phí ở asd-ste100.org (skill này không chứa từ điển đó).

## 3. Tiếng Việt

- Câu ngắn: thủ tục khoảng 25 chữ, mô tả khoảng 35 chữ (tiếng Việt tính theo âm tiết, nên giới hạn dài hơn tiếng Anh; đây là mức gợi ý, không chấm điểm).
- Mệnh lệnh không chủ ngữ cho bước làm ("Mở màn hình Cài đặt"); không "bạn hãy", không "vui lòng" trong tài liệu nội bộ. Câu mô tả trong README / hướng dẫn người dùng cuối xưng hô theo `vietnamese-register.md` § 1.
- Mức bắt buộc: "phải" (bắt buộc), "có thể" (được phép), "không được" (cấm). Không dùng "nên" cho yêu cầu bắt buộc.
- Giữ thuật ngữ tiếng Anh theo `vietnamese-register.md` § 3; một khái niệm một từ.
- "vv.", "...": nguồn cho đủ danh sách thì liệt kê đủ ("gồm A, B và C"); không thì giữ ý còn mở ("gồm A, B và các mục khác").

## 4. Tiếng Nhật

- Thủ tục: 「〜する。」 hoặc 「〜してください。」 theo quy ước của tài liệu; một bước một thao tác.
- Mức bắt buộc: 「必須」「〜する必要がある」(bắt buộc), 「〜できる」(được phép), 「〜しないこと」「禁止」(cấm). Không dùng 「〜したほうがよい」 cho yêu cầu bắt buộc.
- Tách câu dài nhiều 「〜が、〜し、〜ので」 thành nhiều câu; một câu khoảng 50–60 ký tự là mức gợi ý.
- Không dùng 「など」「等」 khi liệt kê được đủ.

## 5. Mẫu theo loại văn bản

| Loại | Kiểu | Mẫu |
|---|---|---|
| Thông báo lỗi, đầu ra CLI | Thủ tục | Điều gì xảy ra (quá khứ) → nguyên nhân nếu biết → lệnh hay điều kiện để sửa. "Kết nối database thất bại. Mật khẩu của user `app` không đúng. Đặt lại `DB_PASSWORD` rồi kết nối lại." Không đổ lỗi người dùng, không "Oops" |
| Runbook, SOP | Thủ tục | Mỗi bước một lệnh, điều kiện trước; cảnh báo đứng trước bước của nó |
| Báo cáo sự cố, postmortem | Mô tả, quá khứ | Mốc giờ và con số: "14:02–14:31 UTC, 12% request lỗi. Lần deploy lúc 14:00 bỏ bước làm nóng cache." Nói điều đã biết; điều chưa biết ghi "chưa rõ", điều nghi ngờ ghi "chưa xác nhận" — không thay bằng rào đón mơ hồ, cũng không khẳng định |
| Commit, mô tả PR | Dòng tiêu đề mệnh lệnh, thân mô tả | Không "PR này nhằm…"; thân theo giới hạn câu mô tả |
| Release note, changelog API | Mô tả | Một mục một thay đổi, một câu nếu được. Thay đổi phá vỡ: lệnh trước ("Cập nhật lời gọi `v2/users`. Trường `name` tách thành `first_name` và `last_name`.") |
| Prompt, AGENTS.md, skill cho AI | Thủ tục | Một chỉ dẫn một câu; một từ một nghĩa (mô hình coi "check", "verify", "validate" là ba việc); điều kiện đặt trước ("Nếu build lỗi, dừng lại"); không "nên" — mô hình hiểu "nên" là tùy chọn: viết "phải" / "must" hoặc bỏ |
| Thông báo trạng thái, macro hỗ trợ | Mô tả | Việc gì, bao lâu, dữ liệu ra sao. Không "Chúng tôi chân thành xin lỗi vì mọi bất tiện có thể đã gây ra" thay cho sự thật |
| Chuẩn bị văn bản để dịch máy | Plain | Một nghĩa một từ, ngữ pháp đủ (mạo từ, "that", chủ ngữ) bỏ bớt chỗ người dịch phải đoán |
| Chữ trên giao diện, trạng thái rỗng | Thủ tục, giới hạn độ dài | Nút, nhãn là tên kỹ thuật, không áp giới hạn câu. "Chưa có dự án. Tạo dự án để bắt đầu." |

## 6. Trả lời trong chat

1. Câu đầu là câu trả lời hoặc kết quả; không nhắc lại câu hỏi.
2. Mặc định viết văn xuôi; danh sách / bảng chỉ khi nội dung có hình dạng đó (các khối riêng, từ ba mục song song, các bước, so sánh theo thuộc tính). Khối code khi người đọc phải chép.
3. Không lời mở ("Chắc chắn rồi") và lời kết ("Hy vọng giúp được").
4. Không rút gọn thông báo lỗi trích nguyên văn, cảnh báo an toàn, hay câu xác nhận trước thao tác không hoàn tác được.

## 7. Tự soát (Plain)

1. Ba câu dài nhất: đếm từ; quá giới hạn thì tách.
2. Tìm và xử lý từng chỗ (EN): `'` (viết tắt), `has been`, `should`, `may`, `;`, `—`, `, making`, `**`, các từ đồng nghĩa của "check" và "config". VI: "nên" trong yêu cầu, "vv.", "bạn hãy", tiêu đề cho đoạn dưới ba câu.
3. Đọc từng bước: bước có nêu máy, cờ hay bước trước mà người đọc cần không? Không có mà nguồn cho biết thì thêm; nguồn không cho biết thì ghi "Cần xác nhận" ở cuối.
4. So với nguồn: mức không chắc chắn, lời khuyên, phần còn mở của danh sách còn nguyên.

Chế độ Check theo bộ quy tắc này: báo từng lỗi gồm số mục (file này), đoạn lỗi, câu sửa; không trích số quy tắc của chuẩn ASD-STE100 theo trí nhớ.

---

ASD-STE100 là chuẩn của ASD (Aerospace, Security and Defence Industries Association of Europe); skill này không chép nội dung hay từ điển của chuẩn.

Thông báo bản quyền và toàn văn giấy phép MIT của `SimpleEnglish`: `NOTICES.md` (thư mục gốc của skill).
