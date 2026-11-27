# Nguồn tham khảo và quyết định áp dụng

Đã đọc upstream trực tiếp ngày **2026-11-11, giờ Việt Nam**. Engine QKB được viết
độc lập; không vendoring/copy code, không import hai package. Không áp dụng các
claim benchmark của upstream cho QKB.

## CodeGraph

Repository: https://github.com/colbymchenry/codegraph

Snapshot main tại commit `f72c9d2efb14454ff4f9fd7b8460abd82f19a287`.
Nguồn đã tham khảo:

- [README](https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/README.md)
- [SQLite schema](https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/src/db/schema.sql)

Áp dụng ở mức kiến trúc: SQLite lưu files/nodes/edges, index theo đường dẫn và
symbol, FTS, hash reconciliation, incoming-dependency impact, kết quả có source
location, và một lệnh `explore` gộp orientation có giới hạn. Không tái tạo Rust/TS
kernel, MCP, watcher, framework resolvers hoặc dynamic-dispatch graph.

README upstream phân biệt tổng token xử lý với context còn lưu sau nhiều lượt.
QKB vì vậy cap toàn payload, đọc nguồn có chọn lọc và không tuyên bố phần trăm
tiết kiệm khi chưa đo. Benchmark local chỉ đo kích thước retrieval theo ký tự/
ước lượng, không đo cost hoặc context resident của một phiên Claude thật.

## Graphify

Repository: https://github.com/Graphify-Labs/graphify

Snapshot branch `v8` tại commit `5eedffa87476a063a05bed96f17275ed63f05c1a`.
Nguồn đã tham khảo:

- [README](https://github.com/Graphify-Labs/graphify/blob/5eedffa87476a063a05bed96f17275ed63f05c1a/README.md)
- [Architecture](https://github.com/Graphify-Labs/graphify/blob/5eedffa87476a063a05bed96f17275ed63f05c1a/ARCHITECTURE.md)
- [Extractor models](https://github.com/Graphify-Labs/graphify/blob/5eedffa87476a063a05bed96f17275ed63f05c1a/graphify/extractors/models.py)
- [Incremental/dedup design](https://github.com/Graphify-Labs/graphify/blob/5eedffa87476a063a05bed96f17275ed63f05c1a/docs/superpowers/specs/2026-05-04-incremental-updates-dedup-design.md)

Áp dụng: node/edge pipeline, source provenance, EXTRACTED/INFERRED, path queries,
incremental invalidation, giải thích quan hệ và bounded offline view. QKB lưu graph
có hướng ngay trong schema, không suy hướng từ thứ tự node. Không dùng NetworkX,
Leiden, tree-sitter, external semantic backend hoặc fuzzy entity merge.

QKB thêm yêu cầu riêng từ prompt: inferred edge cần explicit human approval,
khớp quote/hash của cả hai endpoint và invalidation khi source đổi. Kiểm tra evidence
không đồng nghĩa suy luận đúng. Không khẳng định semantic graph ngang Graphify.

## Cơ chế tích hợp Claude Code

Đối chiếu với tài liệu chính thức:

- [Project skills](https://code.claude.com/docs/en/skills)
- [Project rules](https://code.claude.com/docs/en/memory)
- [Hooks reference](https://code.claude.com/docs/en/hooks)

`.claude/skills/q-knowledgebase/SKILL.md` và rule không path-scope là cấu trúc
project được hỗ trợ. Khả năng load vẫn phụ thuộc project trust, phiên bản và enterprise
policy; chỉ kiểm tra filesystem/engine không chứng minh runtime Claude đã load.
Hook reminder là optional snippet, merge thủ công sau IT approval, không tự bật.
