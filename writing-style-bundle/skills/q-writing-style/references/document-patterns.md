# Mẫu theo loại tài liệu

Thứ tự tham chiếu cho từng loại tài liệu. Chỉ dùng các phần mà nguồn có; không tạo mục rỗng, không ép đủ mọi mục. Ở chế độ `Polish`, giữ nguyên cấu trúc của người dùng.

## Bố cục (mọi báo cáo và loại tài liệu)
Áp dụng khi tái cấu trúc, viết lại hoặc dựng tài liệu; ở chế độ `Polish` chỉ áp dụng khi người dùng yêu cầu đổi bố cục. Bố cục đổi hình thức, không đổi độ dài: ở chế độ `Summarize`, kết quả vẫn ngắn hơn rõ rệt (tiêu đề ngắn, danh sách thay cho câu dài).
1. Tiêu đề và đề mục của báo cáo, tài liệu là câu khẳng định, không phải câu hỏi ("Kết quả kiểm thử", không phải "Kiểm thử thế nào?"). Bài viết: xem K.
2. Khi nội dung có thể thành danh sách (mục song song, bước, điều kiện, phát hiện), viết thành danh sách, mỗi mục một dòng, kể cả trong ô bảng tính, thay vì một câu dài liền mạch.
3. Tiêu đề nói rõ phần đó chứa gì. Với định dạng có cỡ chữ (bảng tính, văn bản, slide), tiêu đề và đầu cột bảng lớn hơn và đậm hơn nội dung; trong Markdown hoặc chat, dùng cấp đề mục.
4. Biểu đồ và hình: không chồng chữ (nhãn, chú giải, tên trục, nhãn dữ liệu). Kiểm tra bản đã dựng, không chỉ mã nguồn; sửa bằng cách đổi cỡ, dời chú giải, rút gọn nhãn hoặc đổi loại biểu đồ.
5. Báo cáo tiếng Việt theo trình tự: tiêu đề → mục đích / phạm vi → phương pháp → kết quả → điều kiện → kết luận chung. Mỗi bảng có một câu dẫn; sau bảng số liệu có "Nhận xét:" / "Kết luận:" nêu số chính; kết luận chung kèm "Định hướng:". Số theo định dạng Việt (1.234,5), ngày dd/mm/yyyy. Chi tiết: `style-guide.md` § 1.1.

## A. Chat / Slack
- Ngắn, tự nhiên, lịch sự; mục đích nằm ở dòng đầu.
- Đoạn ngắn, hoặc gạch đầu dòng khi có nhiều ý.
- Ít hoặc không mở đầu / kết thúc xã giao. Tin nhắn vẫn là tin nhắn, không thành thư chính thức.

## B. Email công việc
1. Mục đích liên hệ
2. Thông tin chính
3. Việc người nhận cần xác nhận hoặc thực hiện
4. Hạn chót, chỉ khi nguồn có

Giữ quan hệ cấp bậc giữa người gửi và người nhận. Không tự thêm hạn chót hay yêu cầu phản hồi.

## C. Báo cáo tiến độ
1. Tình trạng chung
2. Đã làm
3. Đang làm
4. Vấn đề / rủi ro
5. Kế hoạch tiếp theo

Tách rõ: đã làm / đang làm / dự kiến / chờ xác nhận.

## D. Báo cáo kỹ thuật / sự cố
1. Triệu chứng hoặc vấn đề
2. Điều kiện xảy ra
3. Phương pháp và phạm vi kiểm tra
4. Kết quả thực tế
5. Nguyên nhân đã xác nhận hoặc giả thuyết
6. Cách sửa / biện pháp
7. Kết quả kiểm thử lại hoặc vấn đề còn lại

Không phải báo cáo nào cũng cần đủ bảy mục. Giữ nguyên chính xác: log, mã lỗi, tham số; thuật toán, module, API, giao diện; môi trường và điều kiện kiểm thử; số lần chạy, tỷ lệ, thời gian xử lý; đạt / không đạt; trường hợp ngoại lệ. Giả thuyết không bao giờ được viết như nguyên nhân gốc đã xác nhận.

## E. Phân tích và thiết kế hệ thống
Giữ ba tầng tách biệt:
- **WHAT** (cái gì): yêu cầu / nghiệp vụ, hệ thống phải làm gì; đầu vào, đầu ra, quy tắc nghiệp vụ; phạm vi, điều kiện, tiêu chí nghiệm thu.
- **WHO / WHERE / WHEN** (ai / ở đâu / khi nào): ai thực hiện, ở bước nào, hệ thống hoặc nhóm nào chịu trách nhiệm, thứ tự và thời điểm.
- **HOW** (như thế nào): kiến trúc, module, giao diện; thuật toán, xử lý dữ liệu; công nghệ và cấu hình.

Không trộn yêu cầu đã xác nhận với phương án triển khai đề xuất; không thêm chức năng, không đổi phạm vi.

## F. Backlog / ticket (Jira hoặc công cụ tương tự)
Tiêu đề: ngắn, nêu rõ mục tiêu, theo dạng "động từ + đối tượng + kết quả mong đợi"; giữ mã công việc và tên chức năng.

Mô tả (chỉ các phần có nội dung):
1. Bối cảnh / mục đích
2. Phạm vi
3. Yêu cầu cụ thể
4. Kết quả mong đợi / tiêu chí nghiệm thu, chỉ khi nguồn có
5. Tham chiếu, giữ nguyên

Không tự bịa tiêu chí nghiệm thu, không biến đề xuất thành yêu cầu đã thống nhất.

## G. Biên bản họp
- Nhóm theo chủ đề thay vì chép lại theo thứ tự cuộc nói; giữ mọi chủ đề quan trọng, kể cả chủ đề chỉ nhắc ngắn.
- Tách riêng ý kiến từng bên, kết luận và việc còn mở.
- Không bịa quyết định hay việc cần làm; chỉ ghi người phụ trách và hạn khi nguồn nêu rõ.
- Bản ghi (transcript) không chính xác: không viết nội dung đoán như sự thật.
- Dùng gạch đầu dòng, dễ sao chép vào công cụ quản lý dự án.

## H. Hướng dẫn sử dụng / SOP
1. Mục đích và phạm vi
2. Điều kiện tiên quyết / chuẩn bị
3. Các bước theo thứ tự
4. Kết quả cần kiểm tra
5. Lưu ý quan trọng
6. Lỗi thường gặp và cách xử lý

Viết cụ thể: ai, khi nào, ở màn hình / sheet / chức năng nào, nhập giá trị gì, điều không được làm, kiểm tra kết quả ở đâu. Không đưa lý thuyết dài vào trong các bước.

## I. Báo cáo đánh giá / KPI / hiệu quả
1. Mục tiêu đánh giá
2. Phạm vi và nguồn dữ liệu
3. Phương pháp đo
4. Kết quả chính
5. Phân tích và hạn chế
6. Kết luận, đề xuất

Giữ các phân biệt về dữ liệu trong `style-guide.md` § 5–§ 6. Khi so sánh giữa các kỳ, giữ nguyên điều kiện đo và cách chuẩn hóa. Không khẳng định cải thiện chỉ dựa vào một chỉ số khi nguồn không đủ cơ sở. Mỗi bảng kết quả có câu dẫn và "Nhận xét:" nêu số chính; phần kết luận kèm "Định hướng:".

## J. Đề xuất hướng đi / phương án
1. Bối cảnh và vấn đề
2. Hiện trạng / dữ liệu sẵn có
3. Các phương án
4. Lợi ích, hạn chế, rủi ro
5. Điều kiện cần xác nhận
6. Khuyến nghị và bước tiếp theo

Tách việc đã làm với hướng đi tương lai; tính khả thi chưa kiểm chứng không phải lợi ích đã đạt.

## K. Bài viết, blog, bài chia sẻ kỹ thuật
1. Mở bằng điều cụ thể: một con số, một tình huống, hoặc kết luận chính — không mở bằng câu chung ("Trong thời đại số…") hay câu dạo đầu ("Hãy cùng tìm hiểu…").
2. Thân bài theo một mạch: vấn đề → cách làm / dữ liệu → kết quả → giới hạn.
3. Kết ở sự thật cụ thể cuối cùng hoặc việc tiếp theo; không đoạn "Tóm lại" nhắc lại, không câu chốt cảm thán.
4. Đề mục dạng câu hỏi được dùng khi đoạn dưới trả lời đúng câu hỏi đó (bài hỏi đáp, FAQ, bài hướng dẫn); không đặt câu hỏi chỉ để dẫn dắt.

Giữ quan điểm, trải nghiệm và chi tiết riêng của người viết; có mẫu hoặc hồ sơ giọng văn thì theo `voice-profile.md`. Soát kỹ nhóm A–C của `ai-tells.md` — bài viết là nơi các dấu hiệu đó dày nhất.

## L. Thông báo, thông cáo, tin nội bộ
1. Điều gì thay đổi / xảy ra
2. Ảnh hưởng tới ai, từ khi nào
3. Người đọc cần làm gì (nếu có), hạn
4. Liên hệ khi cần hỗ trợ

Một cách xưng hô suốt thông báo (`vietnamese-register.md` § 1). Không thổi phồng ("bước tiến quan trọng", "hành trình mới"); tiếng Việt gửi khách hàng: không câu so sánh nhất thiếu chứng cứ (§ 6 file đó).

## M. Release note, changelog
- Nhóm theo loại: Thêm mới · Thay đổi · Sửa lỗi · Thay đổi phá vỡ (breaking) · Ngừng hỗ trợ.
- Mỗi mục một thay đổi, một câu nếu được; tiếng Việt mở bằng "Đã thêm…", "Đã sửa…".
- Thay đổi phá vỡ: việc người đọc phải làm đứng trước, lý do sau (`plain-language.md` § 5).
- Giữ số phiên bản, mã ticket, tên API như nguồn. Không viết "cải thiện hiệu năng" khi không có số đo.

## N. Thông báo lỗi, chữ trên giao diện
- Thông báo lỗi: điều gì xảy ra → nguyên nhân nếu biết → người dùng làm gì để tiếp tục. Không đổ lỗi người dùng, không "Oops", không mã lỗi trơ trọi khi người đọc là người dùng cuối.
- Nút và nhãn: động từ ngắn ("Lưu", "Thử lại"); theo glossary giao diện của sản phẩm; tiếng Việt theo `vietnamese-register.md` § 3 và § 5 (chữ dài hơn tiếng Anh).

## O. Runbook, quy trình vận hành
1. Mục đích, khi nào dùng runbook này
2. Điều kiện trước (quyền, máy, công cụ)
3. Các bước — mỗi bước một lệnh, điều kiện trước lệnh, cảnh báo đứng trước bước của nó
4. Cách kiểm tra kết quả
5. Quay lui (rollback) khi thất bại
6. Báo cho ai

Theo `plain-language.md`. Lệnh trong khối code, chép chạy được.

## P. Commit message, mô tả PR
- Dòng tiêu đề commit: mệnh lệnh, tiếng Anh, ASCII, khoảng 50–72 ký tự, theo quy ước dự án (ví dụ Conventional Commits). Thân commit có thể bằng tiếng Việt nếu dự án cho phép.
- Mô tả PR: theo khuôn PR của repo nếu có; không có thì: thay đổi gì → vì sao → cách kiểm thử → rủi ro / việc còn lại. Không "PR này nhằm…".

## Q. Prompt, chỉ dẫn cho AI (AGENTS.md, CLAUDE.md, skill)
- Một chỉ dẫn một câu; điều kiện đặt trước; "phải" / "must" cho bắt buộc, không "nên" / "should".
- Một từ một nghĩa suốt prompt; định nghĩa từ riêng ở lần dùng đầu.
- Nói việc cần làm và tiêu chí đạt, không chỉ nói điều cần tránh; ví dụ đầu vào → đầu ra khi định dạng quan trọng.
- Theo `plain-language.md` § 5.

## R. Trả lời trong luồng (chat, comment, review)
- Câu đầu là câu trả lời hoặc quyết định.
- Người đọc đã có ngữ cảnh: không kể lại vấn đề và quá trình chẩn đoán; chỉ giữ lý do có thể đổi quyết định của họ và liên kết họ cần để làm (`ai-tells.md` mục 26).
- Chi tiết dài để cho ticket hay tài liệu, đưa liên kết.
