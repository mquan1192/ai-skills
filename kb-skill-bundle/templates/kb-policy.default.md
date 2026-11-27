# KB policy — default rules

Tóm tắt (cho người dùng):
- Không ghi thông tin đăng nhập (mật khẩu, khóa API, token, khóa riêng) vào KB, yêu cầu hay câu trả lời.
- Không ghi dữ liệu cá nhân.
- Không chép nội dung của dự án này sang tài liệu của dự án khác.
- Dự án có quy định riêng thì khai báo file chính sách trong `kb.config.json` (`policy_file`); file đó chỉ thêm quy tắc, không nới quy tắc mặc định.

## Rules for the model (always on, every KB skill)

1. **Credentials**: passwords, API keys, tokens, private keys, connection strings with secrets → never write them anywhere;
   write `[MASKED]` and report file + location without repeating the value.
2. **Personal data**: names linked to private information, contact details, IDs of real persons, health or financial data of
   persons → do not process or copy; report file + location; wait for the user.
3. **No cross-project copy**: content of one project goes only into that project's KB pages and deliverables. A fact from
   another project may be shown in an answer, labelled with its project, for reference only.
4. **Sending outside**: KB content is not sent to other AI tools, web services or external recipients by these skills.
5. **Unsure** whether data falls under rule 1 or 2 → treat it as forbidden and ask.
6. **Project policy file** (`policy_file`): read it after these rules; its rules add to them. A project rule that loosens one of
   the rules above is ignored and reported.

Markers in reports: `🚫 STOP (<rule>): …` · `⚠️ CHECK (<rule>): …`.
