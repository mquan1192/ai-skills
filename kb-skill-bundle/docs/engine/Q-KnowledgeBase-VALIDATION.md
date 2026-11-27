# Kết quả xác minh Q-KnowledgeBase 2.0.0

Ngày ghi nhận: 2026-11-11 (giờ Việt Nam). Môi trường chạy thực tế:
Python 3.12.3, SQLite của Python, Linux/WSL2 x86_64. Kiểm tra cú pháp cả 19 file
Python với grammar Python 3.10: đạt. Đây không thay thế runtime test Python 3.10.

## Tests đã chạy

Lệnh `python3 -m unittest discover -s .claude/skills/q-knowledgebase/tests
-p 'test_*.py' -v` đã chạy **68 tests, tất cả đạt**, không có skipped test trong
lượt ghi nhận. Thời gian lượt cuối trên source: 9.382 giây.
Validator định dạng skill: `Skill is valid!`.

Nhóm kiểm tra gồm:

- Markdown H1–H6/nested, fences nhiều độ dài, BOM, Việt/Nhật, bảng, duplicate
  filenames/headings, chunk ordering và exact line reconstruction.
- Search exact path/heading/symbol, multi-term và partial fallback, CJK, tiếng Việt
  không dấu, valid-JSON output cap, UTF-8 byte budget, stale-source refusal.
- FTS5 có thật ở môi trường chạy; fallback đã được thử cả disabled config và
  mô phỏng SQLite trả lỗi `no such module: fts5` khi tạo virtual table.
- Graph direction, path/reverse path, incoming impact, Python local imports,
  explicit document/code references, Unicode/space paths, broken-link recovery,
  unresolved external imports, không bịa JS/TS call graph.
- Semantic evidence đúng/sai/thiếu, sai section/hash/range, cả hai endpoint,
  approval bắt buộc, rejected duplicate dedup, source invalidation và cảnh báo
  một số quan hệ mâu thuẫn. APPROVED vẫn là INFERRED.
- Incremental add/modify/delete/move/heading/anchor, hash khi timestamp không đổi,
  unchanged file không reparse, transaction rollback khi lỗi và history retention.
- Traversal/drive/UNC/ADS, symlink ra ngoài repo/cache, secrets/env exclusions,
  nested ignore/negation, không thực thi shell-like source, deny network/subprocess
  entry points trong test indexing/search, không sửa source hoặc cấu hình hiện có.
- Installer preview không ghi file, preflight collision/tampering/symlink,
  giữ nguyên config/rules/skills khác và idempotent install.
- ZIP root `.claude/` đúng, giải nén fixture mới có Unicode/space, chạy doctor,
  status/init dry-run không ghi file, build/query/read/path/explore/update/verify,
  backup/export; gỡ QKB vẫn giữ nguyên source và Claude settings.
- JSON/GraphML/Mermaid exports, HTML data escaping/CSP và benchmark có golden labels.

ZIP bàn giao có manifest từng file và checksum SHA256 ngoài ZIP. Kết quả kiểm tra
đúng artifact cuối, danh sách file và log chạy từ bản giải nén được ghi riêng trong
thư mục `delivery` của bộ bàn giao, tránh checksum tự tham chiếu trong ZIP.

## Benchmark mẫu đã đo

Nguồn số liệu đầy đủ: [benchmark-fixture.json](.claude/skills/q-knowledgebase/references/benchmark-fixture.json).
Corpus **giả lập**, 11 files, 17 sections, 41 nodes, 37 deterministic edges;
1802 raw bytes / 1752 decoded characters. 9 truy vấn có labels được định nghĩa trong
`tests/support.py`; một document được sửa để đo incremental update.

| Metric | QKB | Baseline text |
|---|---:|---:|
| Recall@5 theo path+heading | 1.000 | 1.000 |
| Relevant section precision trung bình | 0.878 | 0.404 |
| Current hash/line traceability | 1.000 | Không đo |
| Search latency trung bình | 0.621 ms | 0.025 ms |
| Rendered output trung bình | 1160.9 chars | Không đo output |
| Token estimate bảo thủ theo UTF-8 bytes | 1171.3 | Không đo |

Build 0.0198s; update một document 0.00744s; index 147456 bytes.
Output trung bình ít hơn việc đưa toàn corpus mẫu vào context khoảng 33.7% theo
**ký tự**, không phải token model hay cost. Đây không chứng minh tiết kiệm trên
KB thật; corpus rất nhỏ và self-contained. Trong quá trình đo, broad OR matches
ban đầu tạo output lớn hơn corpus; implementation đã được sửa để ưu tiên exact/
all-term hits trước khi fallback partial. Bộ test có kiểm tra hành vi này.

Labels hiện đánh giá section retrieval, không đo answer correctness, runtime impact
completeness hoặc automated conflict discovery. Các latency phụ thuộc filesystem,
cache và máy; không dùng các số này làm cam kết hiệu năng production.

## Chưa xác minh / chưa triển khai

- Chưa chạy native Windows Python, chưa xác nhận Claude Code runtime đã load
  skill/rule trong môi trường enterprise của người dùng. Tài liệu chính thức đã
  được đối chiếu; policy/trust/version vẫn cần kiểm tra tại nơi triển khai.
- Chưa browser-test UI của viewer; đã test output serialization, bounds, escaping,
  CSP và dữ liệu graph. Viewer là snapshot local, không CDN/network.
- Chưa benchmark KB thật hoặc hàng trăm nghìn file; graph query hiện nạp edges
  vào memory và reconcile references toàn graph.
- Chưa full multilingual AST/call graph, semantic auto-discovery, Leiden clustering,
  embeddings, tự phát hiện mâu thuẫn nghiệp vụ/code hoặc strict enforcement.
- YAML subset/Markdown link parsing và ignore wildmatch có giới hạn ghi trong
  architecture/security references. Không có DLP, encryption hay reviewer authentication.

Không tuyên bố tương đương Graphify/CodeGraph về độ đầy đủ code/semantic graph.
