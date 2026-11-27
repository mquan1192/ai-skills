# Ví dụ trước / sau

Các cặp sửa tốt và sửa sai, mỗi cặp có lý do trong một dòng. Mọi ví dụ đều là nội dung bịa, trung tính (Công ty A, máy quét M1, phần mềm Lịch kho, chị Lan …); tên trong ví dụ chỉ là dữ liệu minh họa, không phải quy tắc. Mỗi ví dụ nêu điều nó dạy và chế độ áp dụng. Quy tắc gốc nằm ở `style-guide.md`; các mã W-1 … W-6 trỏ tới đó.

## 1. Rút gọn một câu (VI · Polish)

Trước: "Hiện tại phía Công ty A đang tiến hành việc thu thập các số liệu cần thiết từ tệp nhật ký để phục vụ cho công việc phân tích trong giai đoạn tiếp theo."

Sau: "Công ty A đang thu thập số liệu từ nhật ký để phục vụ phân tích."

Vì sao: bỏ phần đệm ("hiện tại phía", "tiến hành việc", "các … cần thiết"); giữ chủ thể, hành động, nguồn và mục đích.

## 2. Giữ đủ thông tin khi rút gọn (VI · Polish)

Trước: "Em xin thông báo là lô vật tư số 7 mà bên em đặt với bên chị gồm 120 cuộn cáp, hiện đã về kho nhưng chưa kiểm đếm xong, dự kiến chiều thứ Năm mới có kết quả, nếu thiếu thì em sẽ báo lại ngay trong ngày."

Sau: "Lô vật tư số 7 (120 cuộn cáp) đã về kho, chưa kiểm đếm xong; dự kiến chiều thứ Năm có kết quả. Nếu thiếu, em báo lại ngay trong ngày."

Sai: "Lô vật tư số 7 đã về kho và sẽ sớm có kết quả kiểm đếm."

Vì sao: bản sai làm mất số lượng, mốc "chiều thứ Năm" và điều kiện "nếu thiếu"; rút gọn là bỏ chữ thừa, không bỏ ý.

## 3. Số đo kèm cách đo (VI · Polish)

Trước: "Máy quét M1 cho kết quả rất ổn định, thời gian xử lý khoảng 4 giây."

Sau: "Máy quét M1: thời gian xử lý 3,8–4,3 giây qua 10 lần chạy (đo bằng đồng hồ của phần mềm Lịch kho, máy cấu hình tiêu chuẩn)." — chỉ viết khi nguồn có đủ các số này.

Nếu nguồn chỉ có "khoảng 4 giây": giữ nguyên "khoảng 4 giây (1 lần chạy)" và ghi chú "chưa đo lặp"; không thêm số lần chạy hay khoảng dao động.

Vì sao: số đo cần số lần chạy, khoảng dao động và cách đo; nhưng chỉ ghi những gì nguồn cho, không suy ra thêm (W-4).

## 4. Giới hạn của kết luận (VI · Polish)

Trước: "Phương án B nhanh hơn phương án A khoảng 20%, nên chọn phương án B cho toàn hệ thống."

Sau: "Trên 5 mẫu thử, phương án B nhanh hơn phương án A khoảng 20%. Mẫu còn ít và chưa thử trên hệ thống thật, nên chưa đủ căn cứ để chọn cho toàn hệ thống."

Vì sao: kết luận phải mang theo giới hạn (cỡ mẫu, điều kiện thử); một chỉ số trên mẫu nhỏ không chứng minh được hiệu quả chung.

## 5. Hướng dẫn thao tác (VI · Polish)

Trước: "Để có thể thực hiện việc xuất báo cáo, người dùng cần phải trước hết mở menu Tệp lên, sau đó thì chọn vào mục Xuất, rồi cuối cùng nhấn nút OK."

Sau:

```
Xuất báo cáo:
1. Mở menu Tệp.
2. Chọn Xuất.
3. Nhấn OK.
```

Vì sao: mỗi bước một dòng, động từ đứng đầu, thứ tự rõ; không đổi tên menu hay nút.

## 6. Câu tiếng Nhật dài dòng (JA · Polish)

Trước: 「お忙しいところ大変恐れ入りますが、先日お送りいたしました資料につきまして、ご確認のほどよろしくお願いできればと存じます。」

Sau: 「先日お送りした資料のご確認をお願いいたします。」

Vì sao: bỏ tầng kính ngữ lặp; vẫn giữ mức lịch sự với cấp trên (お願いいたします); không đổi việc được nhờ.

## 7. Giữ mức chắc chắn (JA · Polish)

Trước: 「原因は設定ミスの可能性があります。現在、担当者が確認中です。」

Sau: 「原因は設定ミスの可能性があります(確認中)。」

Sai: 「原因は設定ミスです。」

Vì sao: 可能性があります = chưa xác nhận; bản sai nâng thành khẳng định. Từ trạng thái (確認中, 対応済み …) không thay thế cho nhau.

## 8. Đề xuất không phải quyết định (EN · Polish)

Before: "We would like to propose moving the weekly review to Tuesday, if that works for everyone."

Good: "Proposal: move the weekly review to Tuesday. Please reply if you object."

Bad: "The weekly review is moved to Tuesday."

Why: a proposal stays a proposal; the bad version turns it into a decision nobody made.

## 9. Không bịa hạn chót (EN · email)

Before: "Could you please check the attached file when you have time?"

Good: "Could you please check the attached file?"

Bad: "Could you please check the attached file by Friday?"

Why: the source gives no deadline; shortening must not add one (nor an owner).

## 10. Số 0 khác không có dữ liệu (EN · KPI)

Before: "Defects found: 0. Retests: (blank). Coverage: not measured yet."

Good: "Defects found: 0 (none). Retests: no data. Coverage: not measured yet."

Bad: "Defects found: 0. Retests: 0. Coverage: 0%."

Why: 0 = really zero; blank = no data; "not measured yet" = no result. Never swap one for another.

## 11. Viết tắt với người đọc ngoài nhóm (VI · Restructure)

Trước: "TC-12 NG trên STG, đã báo QA. Chi tiết hỏi chị Hoa."

Sau: "Ca kiểm thử TC-12 không đạt trên môi trường STG (cần xác nhận dạng đầy đủ của STG); đã báo bộ phận kiểm thử. Cần xác nhận: dạng đầy đủ của STG — chị Hoa trả lời."

Vì sao: viết tắt phổ biến (TC, NG) được mở ra; viết tắt riêng của nhóm mà nguồn không định nghĩa thì không đoán, đánh dấu và hỏi một lần.

## 12. Câu chung chung → cơ chế và số liệu (VI · Polish; W-1, W-3, W-4)

Trước: "Giải pháp mới không chỉ nhanh mà còn ổn định, đóng vai trò quan trọng trong việc nâng cao hiệu quả vận hành. Có thể nói rằng đây là một bước tiến đáng kể."

Sau (nguồn có số): "Giải pháp mới tra cứu từ chỉ mục thay vì quét toàn bộ bảng; thời gian tra cứu giảm từ 2,1 giây xuống 0,4 giây (50 lần chạy)."

Sau (nguồn không có số): "Giải pháp mới tra cứu từ chỉ mục thay vì quét toàn bộ bảng. Chưa đo thời gian." — và đánh dấu từ "ổn định", "đáng kể" là chưa có số đo, không tự bịa số.

Vì sao: câu đúng ở mọi dự án thì không nói gì (W-1); "không chỉ … mà còn …", "đóng vai trò", "có thể nói rằng" chỉ là đệm (W-3); từ mơ hồ cần số hoặc "chưa đo" (W-4).

## 13. Một bước không quyết định điều gì (VI · Restructure; W-5)

Trước (ghi chú đi kèm: chị Lan nắm phần ngoại lệ; khi số lượng nhập lớn hơn tồn kho, hệ thống báo lỗi E-12): "Bước 4: Xử lý các trường hợp ngoại lệ. Bước 5: Sẽ xem xét sau."

Sau:

```
Bước 4: Nếu số lượng nhập lớn hơn tồn kho, hệ thống báo lỗi E-12.
Bước 5: Cần xác nhận: cách xử lý sau lỗi E-12 — chị Lan trả lời.
```

Vì sao: "ngoại lệ" nào, ai làm gì? Chỉ nêu điều nguồn nói (lỗi E-12, chị Lan); phần nguồn không nói thì thành câu hỏi mở kèm người trả lời, không bịa cách xử lý, chủ trách nhiệm hay hạn.

## 14. Một tên, các số khớp nhau (VI · Polish; W-2, W-6)

Trước: "Gói cập nhật gồm 12 mục. Sau khi cài bản cập nhật, bạn khởi động lại. Tệp gửi lên có 11 mục được áp dụng."

Sau: "Gói cập nhật gồm 12 mục. Sau khi cài gói cập nhật, khởi động lại. Nguồn nêu 11 mục được áp dụng, lệch với 12 mục của gói — cần xác nhận mục còn lại."

Vì sao: một vật một tên (W-2: "gói cập nhật" không đổi thành "bản cập nhật", "tệp gửi lên"); số trong văn bản phải khớp nhau (W-6); chênh 12 và 11 thì nêu rõ, không tự làm tròn cho khớp.

## 15. Báo cáo tiếng Việt theo cấu trúc báo cáo — kết quả kiểm thử (VI · Rewrite)

Trước (ghi chú rời): "kiểm thử xong rồi nha, 48 ca, đạt 45, hỏng 3 cái, hai cái do dữ liệu mẫu sai, 1 cái là lỗi thật, sẽ sửa tuần sau, chạy trên máy test ngày 12/11/2026"

Sau:

```
Báo cáo kết quả kiểm thử phần mềm Lịch kho — Nhóm kiểm thử, Công ty A

1. Mục đích và phạm vi
Đánh giá chức năng nhập kho của phần mềm Lịch kho trên bộ 48 ca kiểm thử.

2. Phương pháp
Chạy 48 ca trên máy kiểm thử ngày 12/11/2026.

3. Kết quả
Bảng 1 nêu số ca theo kết quả.

| Kết quả | Số ca |
|---|---:|
| Đạt | 45 |
| Không đạt | 3 |

Nhận xét: 45 / 48 ca đạt. Trong 3 ca không đạt, 2 ca do dữ liệu mẫu sai, 1 ca là lỗi thật của phần mềm.

4. Kết luận chung
Chức năng nhập kho đạt phần lớn ca kiểm thử; còn 1 lỗi thật cần sửa.
Định hướng: sửa lỗi thật trong tuần sau.
```

Vì sao: đủ mục đích → phương pháp → kết quả (câu dẫn trước bảng, "Nhận xét:" nêu đúng con số chính) → kết luận, "Định hướng:"; ngày dd/mm/yyyy; không tính thêm phần trăm, không thêm việc cần làm hay thời hạn mà ghi chú không có ("tuần sau" giữ nguyên như nguồn).

## 16. Báo cáo tiếng Việt theo cấu trúc báo cáo — khảo sát đo đạc (VI · Restructure)

Trước: "Khảo sát nhiệt độ phòng máy: trung bình 24,5 độ, cao nhất 27,1 độ lúc 14:30. Theo chị Lan là hơi nóng. Nên mua thêm điều hòa. Điều kiện: chỉ đo 3 ngày."

Sau:

```
Báo cáo khảo sát nhiệt độ phòng máy — Công ty A

1. Mục đích và phạm vi
Ghi nhận nhiệt độ phòng máy trong 3 ngày.

2. Phương pháp
Đo nhiệt độ phòng máy trong 3 ngày; thiết bị đo, số điểm đo và chu kỳ đo chưa có trong nguồn (cần xác nhận).

3. Kết quả
Nhiệt độ đo được tóm tắt như sau.

| Chỉ tiêu | Giá trị |
|---|---|
| Trung bình | 24,5 °C |
| Cao nhất | 27,1 °C (14:30) |

Nhận xét: nhiệt độ trung bình là 24,5 °C, cao nhất 27,1 °C lúc 14:30. Ý kiến "hơi nóng" của chị Lan là nhận định cá nhân, chưa có ngưỡng so sánh.

4. Điều kiện
Chỉ đo trong 3 ngày; cần tiếp tục kiểm chứng trên khoảng thời gian dài hơn.

5. Kết luận chung
Số liệu 3 ngày chưa đủ để kết luận phòng máy quá nóng.
Định hướng: mua thêm điều hòa là đề xuất, chưa phải quyết định; cần tiếp tục kiểm chứng trên khoảng thời gian dài hơn.
```

Vì sao: tách số đo khỏi ý kiến, giữ giới hạn "chỉ đo 3 ngày", đề xuất không thành quyết định; giọng trung tính, tiêu đề dạng danh từ, không dấu chấm cuối.

## 17. Tin nhắn ngắn không cần cấu trúc báo cáo (VI · Polish)

Trước: "Chị Lan ơi, em gửi chị file kiểm kê rồi nhé, chị xem giúp em xem số lượng ở dòng 5 có đúng chưa ạ, em cảm ơn chị nhiều."

Sau: "Chị Lan ơi, em đã gửi file kiểm kê. Chị kiểm tra giúp em số lượng ở dòng 5 nhé. Em cảm ơn chị."

Sai: tiêu đề "Báo cáo kiểm kê", các mục "Mục đích / Phương pháp / Kết quả".

Vì sao: một tin nhắn hay ghi chú nội bộ không cần khung báo cáo; chỉ gọn lại câu chữ, giữ lời hỏi và lịch sự.

## 18. Bỏ dàn dựng và câu chốt (VI · Humanize)

Trước: "Bản cập nhật lần này không chỉ là một bản vá lỗi, mà là một bước ngoặt trong hành trình nâng tầm trải nghiệm người dùng. Thời gian tải trang giảm từ 3,2 giây xuống 1,1 giây. Đó mới là điều thực sự quan trọng."

Sau: "Bản cập nhật lần này giảm thời gian tải trang từ 3,2 giây xuống 1,1 giây."

Sai: "Bản cập nhật giúp trang tải nhanh hơn đáng kể." (mất con số)

Vì sao: phủ định để nâng (`ai-tells.md` mục 1), thổi phồng (mục 13) và câu chốt (mục 2) không thêm sự thật; con số là thông tin duy nhất và phải giữ nguyên.

## 19. Humanize không đụng tin nhắn đã tự nhiên (VI · Humanize)

Trước: "a ơi build trên staging lại fail r, e đang xem log, chắc tầm 30p nữa e báo lại nhé"

Sau: (giữ nguyên)

Sai: "Anh ơi, bản build trên môi trường staging lại thất bại. Em đang kiểm tra log và sẽ báo lại sau khoảng 30 phút."

Vì sao: tin chat viết tắt, câu ngắn là văn người; không có dấu hiệu AI nào thì trả nguyên văn (`SKILL.md` § Quy tắc đầu ra).

## 20. Thông báo lỗi theo Plain (EN · Plain)

Trước: "Oops! Something went wrong while attempting to establish a connection. Please ensure your credentials are properly configured and try again."

Sau: "The connection to the database failed. The password for user `app` was not correct. Set `DB_PASSWORD` and connect again."

Sai: "Connection failed." (mất việc người dùng phải làm)

Vì sao: điều gì xảy ra → nguyên nhân → việc cần làm (`plain-language.md` § 5). Chỉ dùng nguyên nhân khi nguồn (log) cho biết; không biết thì bỏ câu nguyên nhân, không đoán.

## 21. Dịch thư báo trễ hạn sang tiếng Nhật (VI → JA · Translate)

Trước: "Chào anh Tanaka, em báo anh là bản thiết kế màn hình đăng nhập dự kiến trễ 2 ngày, từ 03/12 sang 05/12, vì bên em đang chờ khách xác nhận yêu cầu mật khẩu. Nhờ anh xem giúp lịch review có dời được không ạ."

Sau: "田中さん

ログイン画面の設計書についてご報告します。お客様によるパスワード要件の確認待ちのため、提出が2日遅れ、12/3から12/5になる見込みです。
恐れ入りますが、レビュー日程を変更していただけるかご確認いただけますでしょうか。
よろしくお願いいたします。"

Sai: "…12/5に提出します。" (bỏ mất "見込み", biến dự kiến thành cam kết); "レビュー日程を変更してください。" (lời nhờ thành mệnh lệnh)

Vì sao: giữ mức chắc chắn (ngày mới còn phụ thuộc việc khách xác nhận → 見込み), giữ lý do và hai mốc ngày; cấp dưới gửi người Nhật dùng です・ます, 謙譲語 và câu đệm (`translation.md` § 2–3). Thư không theo quy tắc khoảng trắng của tài liệu mới (`style-guide.md` § 2).

## 22. Câu trả lời trong luồng: quyết định lên đầu (VI · Rewrite)

Trước: "Em đã xem lại vấn đề anh nêu. Lỗi xảy ra do hàm tính thuế làm tròn trước khi cộng. Em đã chạy lại 120 hóa đơn mẫu, 4 hóa đơn lệch 1 đồng. Vì hàm này dùng chung cho cả module báo cáo nên em nghĩ không nên sửa trong PR này. Em đề xuất tách ticket riêng."

Sau: "Em đề xuất không sửa trong PR này mà tách ticket riêng: hàm tính thuế dùng chung với module báo cáo, sửa ở đây phải kiểm lại cả phần đó. Lỗi do làm tròn trước khi cộng; 4 / 120 hóa đơn mẫu lệch 1 đồng."

Vì sao: người đọc đã có ngữ cảnh (`ai-tells.md` mục 26); đề xuất vẫn là đề xuất, giữ đủ số 4 / 120 và nguyên nhân.

## 23. Giữ thuật ngữ tiếng Anh trong chat kỹ thuật (VI · Polish)

Trước: "Sau khi xem xét xong thì mình sẽ hợp nhất nhánh vào nhánh chính rồi triển khai lên môi trường sản xuất."

Sau: "Review xong thì mình merge vào main rồi deploy lên production."

Sai: giữ "hợp nhất nhánh", "môi trường sản xuất" trong tin chat của nhóm dev.

Vì sao: chat kỹ thuật dùng thuật ngữ tiếng Anh với ngữ pháp tiếng Việt (`vietnamese-register.md` § 3); tài liệu đặc tả chính thức thì có thể dùng từ tiếng Việt, theo glossary.

## Thêm ví dụ mới

Chỉ thêm ví dụ trung tính hoặc đã được duyệt dùng; không dữ liệu dự án, không tên thật. Khung mẫu:

```
## <n>. <điều ví dụ dạy> (<ngôn ngữ> · <chế độ>)

Trước: "<văn bản nguồn>"

Sau: "<văn bản đã sửa>"

Sai: "<cách sửa dễ gặp nhưng sai>"   (tùy chọn)

Vì sao: <một dòng - quy tắc mà ví dụ cho thấy>
```
