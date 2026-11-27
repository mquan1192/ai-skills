# Vietnamese (vi): words to drop or replace, and the self-check

Read for any Vietnamese text you write, edit or translate into (with `style-guide.md` § 1). The groups below follow the same frame as `ng-vocab-ja.md` and `ng-vocab-en.md`; the examples are written for this skill.

## How to use

- Do not delete by search-and-replace. Check each hit in its sentence: if the Vietnamese word adds no information, remove it or put the concrete fact (a condition, a number, a name) in its place; a precise technical term stays.
- **The concrete fact must come from the source.** A replacement number, condition, actor or mechanism is taken from the source text only. When the source has none, keep the general wording (or drop a word that is pure filler) and add "cần số liệu" / "cần xác nhận" at the end. Keep the passive when the source does not say who acted.
- **Project glossary first**: when the project glossary (`glossary` key of the config) fixes a Vietnamese term or a loanword, keep it, even if a group below lists a similar word.
- Words that state a requirement ("phải", "bắt buộc", "không được") stay in specifications, designs and procedures; drop them only when they are emphasis.
- Not sure whether a word carries meaning → leave it and mention the spot to the person who asked.
- Check groups 1, 2 and 6 first: in Vietnamese technical writing they most often hide the actor or the conclusion.

## Word groups

| # | Group | Examples | Replace with |
|---|---|---|---|
| 1 | Empty lead-in | "Có thể thấy rằng", "Điều đáng lưu ý là", "Nói một cách thẳng thắn", "Thực ra thì", "Về cơ bản thì", "Cần nhấn mạnh thêm rằng", "Trước hết cần hiểu rằng", "Như chúng ta đều biết" | Delete the lead-in; write the statement itself |
| 2 | Translation-style verbs that hide the actor | "được tiến hành bởi", "đóng vai trò là", "mang lại giá trị", "thể hiện sự", "cho thấy rõ việc", "góp phần làm nổi bật", "tạo nên một sự", "đặt ra vấn đề về" | Name who did what, active voice: "Nhóm kiểm thử chạy 48 ca", "Kết quả đo cho thấy lỗi xảy ra khi tải trên 200 yêu cầu mỗi giây" |
| 3 | Inflated words | "tuyệt vời", "hoàn hảo", "đột phá", "mang tính cách mạng", "bước ngoặt", "đỉnh cao", "vượt trội", "toàn diện" | State the fact: what changed, by how much, compared with what |
| 4 | IT words used as metaphors for people and habits | "nâng cấp tư duy", "cài đặt thói quen mới", "lập trình lại đội nhóm", "gỡ lỗi cuộc họp", "khởi động lại kế hoạch", "hack năng suất" | The literal action ("đổi cách làm", "tập thói quen ghi chép sau mỗi buổi họp"); IT words only for the IT thing |
| 5 | Unneeded loanwords and business jargon | "deep dive", "leverage nguồn lực", "align kỳ vọng", "scale hóa", "onboard nhân sự", "pivot hướng đi", "đồng bộ hóa góc nhìn", "touchpoint" | The plain Vietnamese word ("xem kỹ", "dùng", "thống nhất yêu cầu", "mở rộng quy mô", "đưa người mới vào việc") — **unless the project glossary fixes the term**; established technical words (API, pipeline, benchmark) stay |
| 6 | Avoiding a conclusion | "tùy từng trường hợp", "có cái lợi cũng có cái hại", "khó nói trước", "không thể khẳng định chắc chắn", "cần cân nhắc nhiều yếu tố", "còn tùy hoàn cảnh" | Which condition gives which result; if it is truly uncertain, say where the uncertainty is and why |
| 7 | Intensity adverbs | "rất", "cực kỳ", "vô cùng", "hết sức", "quá", "đáng kể", "nhanh chóng", "mạnh mẽ" (overused) | A number or a condition: "giảm từ 2,1 giây xuống 0,4 giây", "sau 3 lần chạy lại" |
| 8 | Connecting or summarising sentences that add nothing | "Tóm lại, như đã nói ở trên", "Nói cách khác", "Điều này có nghĩa là như vậy", "Từ đó có thể rút ra kết luận rằng", "Chúng ta hãy cùng tìm hiểu", "Sau đây là phần trình bày" | Delete; keep the sentence that holds the new fact |

## Vietnamese self-check (before handing over)

Read the whole text once, list the problems, then fix. Register and sentence shape for Vietnamese: `style-guide.md` § 1.

1. **Rigour** (`style-guide.md` § 0 item 1) — uncertainty kept where it is real ("chưa xác nhận", "cần kiểm chứng"); nothing stated as fact without a source; different things not merged; one cause not standing in for several; the mechanism of each cause given.
2. **Actor** — active voice with the actor as subject; role names, not "bạn"; no vague "hệ thống", "công cụ", "AI" where a name exists.
3. **Terms** — the same Vietnamese word (or the glossary loanword) for one thing from start to end; no switching between synonyms.
4. **Paragraphs** — each paragraph opens with its topic sentence and keeps to that topic; the argument does not double back; the conclusion appears once; a likely misreading is ruled out before the explanation.
5. **No dramatisation** — no question asked only for effect, no slow build-up, no punchline at the end; bold only for the conclusion or a likely misreading.
6. **Words** — no word from the groups above that carries no information; no filler used only for tone ("quan trọng", "then chốt", "sâu sắc", "tối ưu" without a measure).
7. **No redundancy** — the same point not said twice, no recap right after a description, linked facts in one sentence, no sentence that only links or comments.
8. **Format** — register fits the document type (specification and slides: short noun-style lines; reports: full sentences); numbers and dates in Vietnamese form (1.234,5; dd/mm/yyyy); code, logs and commands in code blocks.

Not taken as rules: one sentence per paragraph, a fixed word count, or avoiding proper names (project documents need module, file and ID names).
