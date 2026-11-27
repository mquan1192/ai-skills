# Semantic proposals và phê duyệt

Không chạy LLM trong script. Claude dùng phiên hiện tại qua gateway đã được công
ty phê duyệt để đọc một nhóm section liên quan và đề xuất ý nghĩa quan hệ. Engine
chỉ kiểm tra JSON schema, scope, endpoint, hash, section và trích dẫn chính xác.
Các kiểm tra này không chứng minh inference đúng. Người review chịu trách nhiệm
ý nghĩa, hướng quan hệ, authority/status tài liệu và đối chiếu implementation.

## Lấy dữ liệu thật, không đoán ID/hash

1. `search` và `read` phần liên quan, giữ `section_id`, `path`, `hash`, line range.
2. Dùng ID node đã CONFIRMED từ graph/map; có thể là document/section/code symbol.
   Không cần tạo entity mới trong Markdown. Entity rõ ràng có thể khai báo bằng
   frontmatter `qkb_entities`, nhưng đây là thay đổi tài liệu cần đúng phạm vi task.
3. Tạo `.qkb/proposals/ten-task.json` chứa một object hoặc list, hoặc JSONL một
   proposal mỗi dòng. Format cố định:

```json
{
  "source": "confirmed node ID returned by engine",
  "target": "another confirmed node ID returned by engine",
  "relation": "REQUIRES",
  "rationale": "Giải thích suy luận; phân biệt bằng chứng explicit với kết luận của người phân tích.",
  "evidence": [
    {
      "path": "docs/users.md",
      "section_id": "logical section ID returned by read",
      "start": 12,
      "end": 12,
      "quote": "Một dòng nguyên văn lấy từ file hiện tại.",
      "hash": "full SHA256 returned by engine"
    },
    {
      "path": "docs/audit.md",
      "section_id": "logical section ID for the target evidence",
      "start": 6,
      "end": 6,
      "quote": "Dòng bằng chứng của tài liệu đích.",
      "hash": "full current target source SHA256"
    }
  ]
}
```

Đây là mô tả format, không phải proposal để import trực tiếp. Không có sample
proposal nào tự động được approve. Fixtures/tests tạo payload hợp lệ từ file thật.
Quote phải bằng chính xác các dòng start..end, nối bằng `\n`, không newline cuối.
Với code evidence, `section_id` là null; với Markdown bắt buộc logical section ID.
Cần ít nhất một evidence hợp lệ cho file nguồn của **cả hai endpoint**. 1–16 span.
Engine không chấp nhận field thừa, endpoint candidate, self-edge hoặc CONTAINS
semantic. Type/direction do người phân tích lựa chọn, không được suy ra từ co-occurrence.

## Import, review, approve/reject

```powershell
$qkb = '.claude/skills/q-knowledgebase/scripts/qkb.py'
python $qkb semantic import '.qkb/proposals/ten-task.json'
python $qkb semantic list
python $qkb semantic show $proposalId --max-chars 12000
python $qkb semantic validate $proposalId --max-chars 12000
# Chỉ chạy sau khi con người thực sự đồng ý với quan hệ cụ thể đã trình bày.
python $qkb semantic approve $proposalId --reviewer 'Tên người duyệt' --reason 'Lý do phê duyệt' --human-approved
# Hoặc từ chối và lưu lý do để tránh lặp lại:
python $qkb semantic reject $proposalId --reviewer 'Tên người duyệt' --reason 'Chưa đủ bằng chứng về dependency'
```

Import lưu PENDING, chưa thêm approved graph. Duplicate payload giữ nguyên quyết
định cũ (kể cả REJECTED). APPROVED vẫn giữ origin INFERRED. `--human-approved` là
xác nhận do người vận hành khai báo, không xác thực danh tính hoặc chữ ký điện tử;
agent không được tự dùng cờ này để thay quyết định của người dùng.

Engine cảnh báo một số cặp mâu thuẫn: CONFLICTS_WITH chồng dependency, SUPERSEDES
ngược chiều. Nếu cảnh báo cần được con người giải quyết trước; chỉ sau đó dùng
`--ack-conflicts` kèm lý do. Không có automated deep contradiction detection và
không đảm bảo phát hiện mọi conflict. Không xóa một phía để ép graph nhất quán.

Nếu source/evidence/endpoint đổi, quan hệ lập tức không đủ điều kiện traversal;
`update` đánh dấu STALE và ghi audit event. Không tự khôi phục approved-current
chỉ vì nguồn được đổi lại. Lấy evidence mới, tạo proposal mới hoặc yêu cầu re-review
rõ ràng. Source bị xóa/move cũng làm quan hệ cần kiểm tra lại. Lịch sử giữ nguyên.
