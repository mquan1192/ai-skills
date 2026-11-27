# Q-KnowledgeBase 2.0.0

Skill Claude Code và engine Python offline để tận dụng kho Markdown đang có:
tra cứu theo section, đọc đúng dòng nguồn, graph có evidence, phân tích dependency,
cập nhật tăng dần và phê duyệt quan hệ suy luận. Bảo toàn tài liệu gốc, chỉ đưa
phần cần thiết vào context. Không có package index mẫu trộn vào knowledge dự án.

## Bắt đầu trong 5 bước — Windows PowerShell

1. IT xác nhận Python 3.10+ và Claude Code đã được phép sử dụng. Chạy
   `python --version`. Không có Python: đề nghị IT cấp bộ cài offline đã kiểm
   checksum/chữ ký, triển khai theo chính sách công ty; công cụ không tự download.
2. Kiểm tra SHA256 của `Q-KnowledgeBase-offline-v2.0.0.zip` bằng
   `Get-FileHash .\Q-KnowledgeBase-offline-v2.0.0.zip -Algorithm SHA256` và đối chiếu
   file checksum đi kèm. Giải nén **nội dung** ZIP vào root repo. `.claude/` phải
   ở ngay root, không nằm trong thư mục bọc Q-KnowledgeBase. Nếu có file QKB cùng
   tên, dừng overwrite, dùng staging và công cụ cài không ghi đè bên dưới.
3. Tại root repo, kiểm tra máy và preview phạm vi:

   ```powershell
   $qkb = '.claude/skills/q-knowledgebase/scripts/qkb.py'
   python $qkb doctor
   python $qkb init --dry-run
   python $qkb init
   ```

   Chỉnh `.qkb/config.json` theo đúng thư mục tài liệu/code của bạn. Mặc định chỉ
   `docs`, `knowledge`, `requirements`, và `src`; không tự tìm KB ở chỗ khác.
   Chạy lại `init --dry-run` sau chỉnh scope để xác nhận. Preview có thể bị cắt
   output; dùng `--max-chars 20000` hoặc thu hẹp scope nếu cần xem đủ.
4. Lập index và kiểm tra:

   ```powershell
   python $qkb build
   python $qkb search 'authentication'
   python $qkb verify
   ```

   Exit 1 của `verify` có thể do link nguồn hỏng; xem `problems`. Không tự sửa docs.
5. Mở lại Claude Code tại root repo. Kiểm tra rule bằng `/memory` và gọi
   `/q-knowledgebase` hoặc yêu cầu xử lý một task repo. Project rules/skills phải
   được policy cho phép. Rule nhắc KB-first; đây là model instructions, không
   phải khóa bắt buộc tuyệt đối. Không cần sửa `CLAUDE.md` hoặc `settings.json`.

## Cài đặt giữ nguyên file hiện có

ZIP không chứa `CLAUDE.md`, `settings.json`, `.qkb/config.json` hay skills khác.
Không dùng `Expand-Archive -Force` lên repo có QKB cũ. Giải nén vào staging rỗng,
sau đó dùng công cụ preflight đi kèm, không cần Administrator:

```powershell
Expand-Archive -LiteralPath '.\Q-KnowledgeBase-offline-v2.0.0.zip' -DestinationPath '.\qkb-staging'
python '.\qkb-staging\Q-KnowledgeBase-install.py' --target 'D:\Projects\MyProject' --dry-run
python '.\qkb-staging\Q-KnowledgeBase-install.py' --target 'D:\Projects\MyProject'
```

Installer kiểm tra toàn bộ hash/đường dẫn trước khi chép. File đích giống hệt được
giữ; file khác nội dung bị báo collision, không ghi đè bất kỳ file nào. `.qkb/.gitignore`
có sẵn được giữ để không ảnh hưởng policy; người vận hành kiểm tra patterns cache/
exports/proposals/backups phù hợp. Nâng cấp QKB cũ cần backup và review diff trước,
không có auto-upgrade phá cấu hình. Không cài global, Marketplace, Node, MCP, hook
hoặc dependency. Không thay proxy, gateway, environment variables hay quyền hệ thống.

## Kiến trúc và dữ liệu

L0 rule ngắn → L1 project map → L2 SQLite searchable sections → L3 Markdown đầy
đủ → L4 graph → L5 semantic proposals từ phiên Claude được doanh nghiệp cho phép.
Index không thay thế tài liệu. Summary không thay business rules. Graph không
thay evidence. Giữ tài liệu lịch sử/deprecated; metadata thiếu là `unknown`.

SQLite ở `.qkb/cache/index.sqlite3`, gồm nội dung section đầy đủ, metadata, hashes,
graph evidence, proposals, review và history. FTS5 được dùng nếu Python SQLite hỗ
trợ; thiếu FTS5 có normalized local search fallback, có thể chậm trên corpus lớn.
Không có embedding/API ngoài, không gọi model bằng Python.

**Engine offline và Claude context là hai việc khác nhau.** Dữ liệu truy vấn do
Claude đọc có thể được gửi qua corporate gateway tới model theo chính sách công
ty. Không được hiểu offline engine là đảm bảo mọi dữ liệu luôn ở trên máy.

## Các câu lệnh thường dùng

```powershell
python $qkb status
python $qkb search 'UserService audit' --top 5 --max-chars 5000 --format json
python $qkb explore 'Audit workflow' --top 3 --depth 2
python $qkb map --top 30
python $qkb read $sectionId
python $qkb related $nodeId --depth 2
python $qkb path $sourceId $targetId --direction out --depth 2
python $qkb impact $nodeId --depth 2
python $qkb update
python $qkb verify
python $qkb export --kind html --node $nodeId --top 100
python $qkb backup
python $qkb --help
```

Biến ID lấy từ kết quả thực tế, không phải dữ liệu mẫu cố định. Cần tra cứu từ thư
mục khác: đặt `--root 'D:\Projects\MyProject'` trước command. Chi tiết tùy chọn,
exit codes và benchmark trong [commands](.claude/skills/q-knowledgebase/references/commands.md).

## KB-first trong công việc hàng ngày

Claude kiểm tra status → tìm sections → xem dependency graph nếu cần → đọc evidence
đúng dòng → kiểm tra code hiện tại → xác định constraints/impact → implement/test.
Sau sửa đánh giá tài liệu cần cập nhật; chỉ cập nhật nội dung trong phạm vi được
phép rồi chạy `update`. Không tự ghi lại approved requirements để khớp code.

Không có index: preview/config/build hoặc tra nguồn trực tiếp và nói rõ hạn chế.
Index stale: không dùng số dòng cũ; update/đọc file hiện tại. Không tìm thấy KB:
báo coverage gap, tìm code trực tiếp, không bịa nghiệp vụ. KB khác code: báo conflict,
đối chiếu nguồn/authority và người có thẩm quyền, không tự chọn một phía làm chân lý.
Không index chỉ vì câu hỏi không liên quan repo.

## Semantic enrichment có người duyệt

Claude chỉ đọc nhóm section liên quan và xuất JSON/JSONL vào `.qkb/proposals/`.
Engine xác minh file, current hash, section, line range, quote và cả hai endpoint.
Import = PENDING; chưa vào graph approved. Người review cần xem chính xác quan hệ,
hướng, evidence, document status và implementation trước khi approve.

```powershell
python $qkb semantic import '.qkb/proposals/task.json'
python $qkb semantic list
python $qkb semantic show $proposalId --max-chars 12000
python $qkb semantic validate $proposalId
# Sau khi người review đã đồng ý với quan hệ này:
python $qkb semantic approve $proposalId --reviewer 'Reviewer' --reason 'Đã review ý nghĩa và evidence' --human-approved
# Hoặc:
python $qkb semantic reject $proposalId --reviewer 'Reviewer' --reason 'Quan hệ chưa được chứng minh'
```

`--human-approved` ghi nhận xác nhận của người vận hành, không xác thực danh tính.
Agent không được tự nhận approval. Quan hệ approved vẫn là INFERRED; nguồn đổi
thì stale, cần review lại. Rejected payload giữ quyết định để không đề xuất lại như
mới. Format và xử lý conflict trong [semantic workflow](.claude/skills/q-knowledgebase/references/semantic-workflow.md).

## Token và chất lượng retrieval

Mặc định chỉ 5 search hits, depth 2 và 5000 ký tự cho toàn response. `explore` gộp
search + graph orientation có giới hạn; đọc thêm source section khi thực sự cần.
`--max-tokens` dùng số byte UTF-8 như ước lượng bảo thủ, không dùng tokenizer online.
Output luôn hợp lệ; `_output.truncated=true` cho biết phải thu hẹp hoặc tăng cap.
Không coi excerpt bị cắt là bản sao đầy đủ của span. Không dump cả DB/graph/KB.

Benchmark đi kèm dùng corpus giả lập trong temporary directory, 9 truy vấn có
golden labels, so text baseline; đo recall@5, precision, traceability, output,
latency và storage. Không đánh đồng với answer accuracy, savings trên dự án thật
hoặc khả năng suy luận ngang Graphify. Chạy test/benchmark:

```powershell
python -m unittest discover -s '.claude/skills/q-knowledgebase/tests' -p 'test_*.py' -v
python '.claude/skills/q-knowledgebase/tests/run_benchmark_fixture.py'
```

## Security và vận hành

- Preview scope trước build; không chọn đường dẫn ngoài repo. Dùng `.qkbignore`
  và config excludes cho dữ liệu riêng. Các thư mục credentials/secrets/keys/.env*,
  .git, node_modules, build, dist, target, .venv... bị hard-exclude. Không follow
  symlink/junction. Ignore hỗ trợ các glob phổ biến, không toàn bộ Git wildmatch.
- Engine không thực thi Markdown/code, không shell commands từ docs, không tự cài
  package/hook/scheduled task, không thay execution policy hay vượt IT restrictions.
- DB/backup/exports chứa dữ liệu nhạy cảm, không được mã hóa bởi QKB. Dùng ACL,
  disk encryption và retention của công ty. `.qkb/.gitignore` tránh commit các
  thư mục sinh ra khi chưa tracked; kiểm tra riêng nếu từng tracked dữ liệu.
- Dùng `backup` cho SQLite consistent snapshot. Backup code/Markdown riêng. Dừng
  QKB trước restore; thay cache bằng bản đúng repo rồi `status/update/verify`.
- Không chia sẻ cùng một SQLite cache đang mở giữa Windows/WSL hoặc nhiều máy
  qua OneDrive. Sync sau khi đóng engine; local cache ngoài sync là phương án vận
  hành IT có thể lựa chọn bằng checkout riêng.

Đọc [security policy](.claude/skills/q-knowledgebase/references/security-policy.md)
trước triển khai enterprise. Không có secret scanner/DLP tự động.

## Hook nhắc việc tùy chọn và rollback

Mặc định chỉ rule/skill. Snippet riêng ở
`.claude/skills/q-knowledgebase/references/optional-hook.json` cho IT review và
merge thủ công vào hook configuration hiện có. UserPromptSubmit chỉ in reminder
ngắn, không block thao tác. Không có hook tự bật hoặc strict PreToolUse.
Nếu policy/version không hỗ trợ, giữ rule + manual commands. Rollback: bỏ đúng
handler QKB đã merge, không xóa các hook khác. Sau đó đóng/mở lại phiên theo IT.

## Troubleshooting

| Triệu chứng | Xử lý |
|---|---|
| `python` không có/Store alias | IT triển khai interpreter offline; dùng đường dẫn Python được chấp thuận |
| Skill không xuất hiện | Kiểm tra `.claude` ở root, mở lại phiên, `/q-knowledgebase`, project customization được policy cho phép |
| Search rỗng | Xem scope, `init --dry-run`, `status`, `update`, heading/path chính xác; coverage gap không có nghĩa feature không tồn tại |
| Nhật/CJK tìm thiếu | Dùng substring cụ thể; fallback bổ sung FTS, không có semantic embedding |
| STALE/null line spans | `update` rồi query lại; không đọc line coordinates từ index cũ |
| BROKEN link | Xem file/anchor trong nguồn; sửa chỉ khi được phép rồi `update` |
| Node ambiguous | Dùng node ID/path chính xác, không chọn theo tên trùng |
| Semantic import invalid | Kiểm tra quote nguyên văn, hash, section ID, current index, evidence cả hai endpoint |
| DB locked/I/O | Đóng process khác; tránh cache chung Windows/WSL/OneDrive đồng thời; restore backup được kiểm tra nếu cần |
| Output truncated | Thu hẹp query/depth/top hoặc tăng cap; đọc bằng chunk ID |
| Schema incompatible | Giữ backup/history; không tự xóa DB; review migration/phiên bản |

## Gỡ cài đặt và phục hồi

Đóng process QKB. Nếu cần giữ lịch sử review, chạy `backup` trước. Xóa riêng
`.claude/rules/q-knowledgebase.md` và `.claude/skills/q-knowledgebase/`. Nếu đã bật
hook thủ công, bỏ handler QKB trước. Không xóa `.claude/` hoặc skills khác.

Xóa `.qkb/cache/`, `exports/`, `proposals/`, `backups/` khi retention cho phép;
chỉ xóa `.qkb/` toàn bộ nếu đó hoàn toàn là dữ liệu QKB. Xóa các file root do gói
này cung cấp dựa trên `MANIFEST.json`, giữ file bạn đã sửa hoặc đang dùng chung.
Gỡ QKB không yêu cầu sửa Markdown/source/CLAUDE.md/settings.json. Secure erase
và bản sao OneDrive/backup phải theo quy trình IT, không chỉ lệnh Delete.

## Phạm vi thực sự của phiên bản

Đã triển khai: deterministic Markdown graph, Python AST definitions/local module
imports, reviewed semantic graph, hash-based incremental update, FTS/fallback,
exact-line retrieval, bounded search/graph/export, offline HTML browser, backup,
tests và CLI. Tham khảo thiết kế từ [CodeGraph](https://github.com/colbymchenry/codegraph)
và [Graphify](https://github.com/Graphify-Labs/graphify), viết engine độc lập, không
copy code hay yêu cầu cài hai sản phẩm. Nguồn cụ thể và quyết định áp dụng nằm trong
[upstream-design](.claude/skills/q-knowledgebase/references/upstream-design.md).

Giới hạn: chưa full code AST graph cho nhiều ngôn ngữ, không automated deep semantic
discovery, không tự tìm mâu thuẫn nghiệp vụ/code, không clustering Leiden, không
vector embeddings, không strict enforcement, không production scale certification.
YAML/Markdown link parser có giới hạn nêu trong architecture. Viewer là snapshot.
Kiểm thử thực tế và môi trường chạy được ghi trong file validation đi kèm; không
coi Python Linux test là chứng nhận native Windows/enterprise deployment.
