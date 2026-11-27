# Kiến trúc và hợp đồng dữ liệu

Q-KnowledgeBase 2.0.0 là implementation độc lập, chỉ Python Standard Library.
Không cần Graphify, CodeGraph, tree-sitter, embedding, MCP hoặc database server.

## Các tầng

| Tầng | Nơi lưu | Vai trò |
|---|---|---|
| L0 | `.claude/rules/q-knowledgebase.md` | Định tuyến KB-first ngắn, không chứa KB |
| L1 | `qkb.py map` | Bản đồ document, entity khai báo, grouping theo thư mục |
| L2 | `.qkb/cache/index.sqlite3` | Metadata và nội dung section/chunk để tìm kiếm |
| L3 | Markdown gốc | Toàn bộ tri thức; engine không viết vào nguồn |
| L4 | SQLite `nodes`, `edges`, `refs`, `proposals` | Graph có hướng, evidence, approval |
| L5 | Phiên Claude đang được doanh nghiệp cho phép | Suy luận có mục tiêu, xuất proposal cho người duyệt |

`core.py`: scope, ignore, parser, SQLite; `engine.py`: update/search/graph;
`semantic.py`: schema/evidence/review; `exports.py`: xuất dữ liệu/viewer;
`benchmark.py`: đo retrieval; `qkb.py`: giao diện lệnh và ngân sách output.

## Parser

Đọc UTF-8/UTF-8 BOM, giữ nguyên Unicode, bảng, lists, Mermaid và code blocks.
Không biến đổi file gốc. Section boundaries là ATX headings H1–H6 ngoài fenced
code blocks (backtick/tilde, độ dài closing fence đúng). Frontmatter được giữ
nguyên ở preamble; metadata parser hỗ trợ scalar một dòng và JSON literal cho
list/object. YAML multiline, aliases, tags hoặc nested YAML không được diễn giải;
nội dung của chúng vẫn nằm trong source/index. Đây không phải YAML parser đầy đủ.
Setext headings, HTML headings, reference-style Markdown links và mọi biến thể
anchor của từng Markdown renderer chưa được resolve tự động.

Các span section/chunk không chồng lặp, bao phủ từng dòng của document có nội dung.
Line numbers tính từ 1, inclusive. `content` giữ nguyên newline sau decode BOM.
Chunk tối đa `chunk_lines`, mặc định 100; bảng/fence có thể qua nhiều chunk.
Đọc bằng `section_id` trả các chunk cùng heading theo thứ tự (vẫn chịu output cap).
File rỗng vẫn có document node, không có section giả.

ID dùng SHA256 rút gọn 24 hex trên loại, đường dẫn và hierarchy/occurrence, không
dùng basename đơn lẻ. Đổi nội dung hoặc chèn dòng trước heading giữ section ID;
đổi hierarchy hoặc rename file tạo ID mới. Chunk ID thêm thứ tự chunk. Không cam
kết ID bất biến khi thay đổi cấu trúc. Rename được ghi nhận khi hash nội dung trùng;
rename đồng thời sửa nội dung được xử lý như delete+add, không suy đoán danh tính.

## SQLite

Schema version được kiểm tra khi mở database; không tự xóa DB không tương thích.

| Table | Nội dung |
|---|---|
| `files` | Path, raw-byte SHA256, byte count, category, metadata, indexed_at |
| `sections` | ID, section ID, path, heading/hierarchy, anchor, line spans, ordering, full text và text normalized |
| `search_fts` | FTS5 tùy SQLite; dữ liệu được đồng bộ trong transaction |
| `nodes` | Type, label, source path/span/hash, CONFIRMED/CANDIDATE, metadata |
| `edges` | Source → target, typed relation, EXTRACTED, source evidence/span/hash, target hash, state, timestamps |
| `refs` | Tham chiếu explicit để resolve lại khi file/anchor đích đổi |
| `proposals` | Immutable inferred payload, PENDING/APPROVED/REJECTED, validation, reviewer |
| `reviews` | Lịch sử approve/reject/invalidation |
| `history` | Snapshot metadata/node/edge bị thay đổi/xóa; không tự áp retention |
| `meta` | Version, config fingerprint, FTS status, durations |

History có thể chứa trích dẫn cũ và phải được bảo vệ như KB. Không tự xóa history
khi update. Đây không phải hệ thống version control đầy đủ của từng byte Markdown;
hãy duy trì Git/backup nguồn riêng.

## Graph

Schema chấp nhận PROJECT, DOMAIN, MODULE, COMPONENT, SERVICE, API, DATABASE, TABLE,
ENTITY, WORKFLOW, BUSINESS_RULE, REQUIREMENT, DECISION, DOCUMENT, SECTION, CODE_FILE,
CODE_SYMBOL. Mặc định tự trích DOCUMENT/SECTION/CODE_FILE/CODE_SYMBOL; MODULE chỉ là
directory grouping với CANDIDATE, không được gọi là domain nghiệp vụ đã xác minh.
Các loại khác có thể được khai báo explicit bằng JSON một dòng trong frontmatter:

```yaml
qkb_entities: [{"type":"SERVICE","name":"UserService"}]
```

Đây là metadata tùy chọn; không yêu cầu sửa tài liệu hiện có để build index.
Khai báo trên tạo DOCUMENTS edge có evidence chính là dòng metadata. CONFIRMED
nghĩa là khai báo/structure được đọc trực tiếp, không chứng minh implementation đúng.

Các relation hỗ trợ: CONTAINS, REFERENCES, DOCUMENTS, IMPLEMENTS, DEPENDS_ON, CALLS,
IMPORTS, USES, AFFECTS, CONSTRAINS, REQUIRES, SUPERSEDES, CONFLICTS_WITH, RELATED_TO.
Không đổi REFERENCES/RELATED_TO thành dependency. Python `ast` tạo class/function
nodes và resolve local module imports; không thực thi source, không tạo call graph.
Import chưa resolve được giữ trong `refs` (có thể là stdlib/external), không tạo
file đích local giả. Không chứng minh imported symbol hoặc runtime binding chính xác.
JS/TS/Java/C#/các extension đã cho phép chỉ có file node, không suy đoán calls bằng regex.

Điểm mở rộng parser: nhánh `extract_code(store,path,text,hash_)` trong `core.py`.
Một parser do IT review có thể gọi `Store.node`, `Store.edge`, `Store.ref` và trả
metadata coverage. Giữ nguyên hợp đồng scope/evidence/hash và thêm fixture/test
cho ngôn ngữ. Không tải plugin từ nội dung repo hoặc tên module trong config.

Markdown link nội bộ, relative link, backtick path, và `supersedes: relative.md`
được resolve trong corpus đã cấu hình. Link URL ngoài không được truy cập. Anchor
được tạo theo heading lowercase, bỏ punctuation, khoảng trắng thành `-`, có suffix
cho duplicate heading; không hứa khớp mọi renderer. Link thiếu file/anchor = BROKEN.

## Freshness và update

Mỗi status/update hash các file trong scope; parsing/FTS chỉ cho file đổi. Đổi config
reparse phạm vi còn được cho phép. Reference layer được reconcile toàn graph để
bắt thay đổi đích dù file nguồn không đổi. Transaction SQLite commit index/graph/history
cùng lúc; lỗi giữa update rollback. Không có watcher, scheduled task hoặc autobuild.

CURRENT = hash khớp trong scope hiện tại; STALE = nội dung/config/evidence đã đổi;
BROKEN = file/link/node không tồn tại hoặc bị loại khỏi scope; UNVERIFIED = chưa
có index, chưa phê duyệt hoặc coverage chưa xác lập. CLI đọc nguồn kiểm tra lại hash.
Kết quả cũ bị che line spans và excerpts; proposal stale giữ lịch sử và không được
traverse. Chỉ approval mới sau kiểm tra nguồn mới có thể trở lại approved-current.

`impact` đi ngược incoming DEPENDS_ON/CALLS/IMPORTS/USES/REQUIRES/IMPLEMENTS.
Đây là ảnh hưởng đã biết trong graph, không đảm bảo đủ runtime dependencies.
`path` mặc định chỉ theo hướng outgoing; `--direction both` ghi rõ bước đi ngược.
Path có inferred edge giữ confidence INFERRED dù đã approved.

## Hiệu năng và giới hạn

FTS5 + normalized substring fallback (CJK, tiếng Việt không dấu, path/symbol).
Mỗi term lấy tối đa 400 section candidates; tối đa 16 term cho substring search.
Ranking ưu tiên exact heading/path, sau đó hit đủ từ (kể cả heading hierarchy),
chỉ dùng partial OR hits khi không có hit đủ. `match_mode` cho biết fallback.
Ranking là heuristic, không semantic embedding. Có thể miss khi truy vấn quá rộng;
hãy dùng module, path hoặc heading cụ thể. Token cap là ước lượng conservative theo
UTF-8 bytes, không có tokenizer và không cam kết token thực tế của mọi model.

Graph traversal hiện nạp edge layer vào bộ nhớ rồi giới hạn depth/node/output;
reference reconciliation cũng đi toàn bộ references. Chưa benchmark corpus doanh
nghiệp hàng trăm nghìn file. Không chạy đồng thời Windows và WSL trên một SQLite
cache/OneDrive sync đang hoạt động; dừng truy cập trước khi copy/restore DB.
Không có Leiden community detection, full AST cross-language, vector store, tự phát
hiện semantic conflict hay semantic equivalence với Graphify/CodeGraph.
