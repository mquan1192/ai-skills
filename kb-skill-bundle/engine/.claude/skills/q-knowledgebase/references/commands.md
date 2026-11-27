# CLI và workflow truy xuất

Chạy tại root repository. Trong PowerShell, đặt đường dẫn vào biến để lệnh gọn:

```powershell
$qkb = '.claude/skills/q-knowledgebase/scripts/qkb.py'
python $qkb --help
python $qkb doctor
python $qkb init --dry-run
python $qkb init
# Chỉnh .qkb/config.json để đúng kho tài liệu; không dùng root hoặc đường dẫn ngoài repo.
python $qkb build
python $qkb status
python $qkb search 'authentication audit' --top 5 --max-chars 5000
python $qkb explore 'Audit workflow' --top 3 --depth 2
python $qkb map --top 20
python $qkb update
python $qkb verify
```

`--root 'D:\My Project'` đặt **trước** tên command nếu gọi từ thư mục khác.
`build` cũng incremental khi index đã có. `build --full` reparse toàn bộ scope,
vẫn giữ history/approval; không sửa Markdown. `update` cần index đã tồn tại.
`doctor`, `status` khi chưa có index và `init --dry-run` không tạo index/config.

Từ `search`, lấy ID thực tế cho `read`; từ `map` hoặc kết quả graph lấy node ID
cho `related/path/impact`. Không tự ghép ID, không dùng basename nếu có trùng.
File path chính xác cũng resolve thành document/code-file node.

```powershell
python $qkb read $sectionId --format json --max-chars 8000
python $qkb related $nodeId --direction both --depth 2 --top 20
python $qkb path 'src/users.py' 'src/audit.py' --depth 2
python $qkb path $sourceId $targetId --direction both --depth 4
python $qkb impact $nodeId --depth 2 --top 20
python $qkb search '監査ログ' --format json --max-tokens 1500
```

`read` chấp nhận chunk ID, logical section ID, code-symbol/file node ID. Output
vẫn chịu ngân sách; `_output.truncated=true` nghĩa là cần thu hẹp hoặc tăng cap.
Trường start/end là span nguồn gốc, không phải cam kết rằng toàn bộ span còn nằm
trong payload bị cắt. Nếu output đã cắt, không dùng excerpt như bản sao toàn span.
Khi cần span nhỏ hơn, dùng chunk ID. Nếu CURRENT đổi giữa kiểm tra và đọc, CLI từ chối.

Mọi command hỗ trợ `--format json|text`, `--max-chars`, `--max-tokens`.
Text mode hiện là JSON có indentation; JSON mode compact, máy đọc được. Cap tính
toàn response, kể cả metadata/newline, không cắt giữa JSON. Mức nhỏ nhất 200.
Ước lượng token dùng số byte UTF-8 như upper heuristic; có thể khá bảo thủ với
tiếng Nhật. Không phải số token thực hoặc số tiền tiết kiệm.

Search/graph có `--top`; traversal có `--depth` (1–8), default 2. `--top` tối đa
1000; mặc định search/explore 5, graph/map/export 30. Output cap mặc định 5000 chars.
`query_top_k`, `query_max_chars`, `graph_default_depth`, `chunk_lines` cấu hình được.

```powershell
python $qkb export --kind html --node $nodeId --top 100 --depth 2
python $qkb export --kind json --top 100
python $qkb export --kind graphml --node $nodeId
python $qkb export --kind mermaid --node $nodeId
python $qkb backup
python $qkb benchmark 'questions.json' --max-chars 12000
```

Exports nằm `.qkb/exports/graph.*`; lần sau ghi đè cùng loại snapshot.
HTML mở local bằng trình duyệt, không server/CDN, filter node types, tìm tên/path,
xem directed relations, source/hash status và origin. File links không tự nhảy tới
dòng trong mọi editor; số dòng hiển thị riêng. Export mặc định có thể không bao phủ
module cần xem; dùng `--node` để lấy subsystem. Viewer không tự cập nhật source status.

Benchmark JSON: list object gồm `query`, tùy chọn `question`, và `relevant` là list
`{"path":"docs/auth.md","heading":"Audit workflow"}`. Tạo golden labels bằng
review thực tế. Engine từ chối labels không tồn tại. Dùng fixture benchmark có sẵn:

```powershell
python .claude/skills/q-knowledgebase/tests/run_benchmark_fixture.py
```

Lệnh trên tạo corpus **tạm**, xóa khi hoàn tất, in metrics; không nạp fixture vào
knowledge của repo thật. Recall/precision đo retrieval theo path+heading, không
đo trả lời đúng/đủ business logic. Report local có corpus/index bytes, output chars,
ước lượng token, traceability, search/build/update latency và text-baseline.

Exit codes: 0 thành công; 1 cho `verify` có vấn đề; 2 input/config/permission/DB
error. BROKEN links không làm build thất bại, nhưng `verify` liệt kê và exit 1.
Unresolved Python imports là coverage gap, có thể là dependency ngoài corpus.

Chi tiết proposal/approval: [semantic-workflow.md](semantic-workflow.md).

# Bổ sung 2.1.0-b0 (B0)

```powershell
python $qkb search 'timeout' --project <project>      # chỉ kết quả của 1 project
python $qkb map --project <project>                     # map + danh sách project và số file
python $qkb verify --links --top 50                     # tham chiếu theo cách phân giải; link hỏng kèm file, dòng
python $qkb migrate --dry-run                           # nâng chỉ mục 2.0.0 (schema 1): xem kế hoạch, không ghi
python $qkb migrate                                     # sao lưu → giữ proposals/reviews/history → dựng lại → kiểm tra
```

- `--project NAME` có ở `search`, `explore`, `map`, `related`, `impact`; mọi kết quả có trường `project`
  (đoạn đầu tiên dưới gốc project dài nhất trong `project_roots`; mặc định = `knowledge_paths`).
- Phân giải tham chiếu theo thứ tự: tương đối → từ gốc repo → từng thư mục cha tới gốc KB → từ gốc nguồn
  → tên file duy nhất trong cùng project. Nhiều file trùng tên → `AMBIGUOUS` (không đoán). File có thật
  nhưng ngoài chỉ mục → `OUTSIDE_INDEX` (không tạo cạnh). Chuỗi không phải đường dẫn (`*`, `<…>`,
  khoảng trắng trong backtick) bị bỏ qua.
- Từ 2.1.0-b1: bước "tên file duy nhất" không vượt project. File không thuộc project nào (nằm ngay
  dưới gốc KB, ví dụ `kb/CHANGELOG.md`) chỉ khớp file cũng không thuộc project nào, nên link viết tắt trong các file
  đó có thể thành `NOT_FOUND` sau khi nâng cấp từ 2.1.0-b0. Cách xử lý: khai báo changelog trong `history_paths`
  (không tạo cạnh) hoặc viết đủ đường dẫn. (Tham chiếu tới file code có quy tắc riêng, xem 2.1.0-c1.)
- Cấu hình mới (đều tùy chọn): `history_paths` (ví dụ `["**/CHANGELOG.md"]`: vẫn tìm được, xếp sau,
  không tạo cạnh), `project_roots` (ví dụ `["kb", "projects"]`).
- `benchmark`: thêm `p50_search_ms`, `p95_search_ms`, `precision_at_5`; câu hỏi có thể thêm
  `"category": "<loại>"` → báo cáo `by_category`.
- Chỉ mục 2.0.0 (schema 1) bị từ chối với gợi ý chạy `migrate`. Lùi lại: chép file sao lưu trong
  `.qkb/backups/` về `.qkb/cache/index.sqlite3`, chép lại thư mục skill cũ và `.qkb/config.json` cũ
  (bản 2.0.0 từ chối key cấu hình mới).

# Bổ sung 2.1.0-b1 (Phase B)

```powershell
python $qkb query 'how does order rollback work'               # định tuyến: explore (có "route", "reason")
python $qkb query 'nếu sửa docs/a.md thì ảnh hưởng gì'      # impact khi tìm được node docs/a.md
python $qkb query 'docs/a.md -> src/b.py'                    # path
python $qkb read <ID> --expand 2                             # thêm 2 đoạn kề trước / sau trong cùng file
python $qkb status --quick                                   # chỉ băm file đổi kích thước / thời gian sửa
python $qkb backup; python $qkb maintain prune-history --days 90 --apply   # dọn history sau khi sao lưu
```

- `query`: thứ tự định tuyến = `path` (2 node có thật, "từ A đến B" / "A -> B") → `impact` → `related`
  (từ khóa + 1 node có thật) → `explore` ("how does", "như thế nào", "仕組み") → `exact` (cả câu là 1
  định danh / tên file / đường dẫn / mã) → `text`. Không tìm được node → về `text`, lý do ghi trong `reason`.
  Từ khóa theo ngôn ngữ ở key `query_routes`.
- `search` mặc định `"ranking": "rrf"`: đoạn khớp nhiều khái niệm hơn đứng trước; cùng mức thì đoạn chứa
  đúng chữ đã gõ đứng trước bản dịch; sau đó gộp thứ hạng (RRF) của FTS từ, FTS trigram và khớp chính xác
  tiêu đề / đường dẫn. Kết quả thêm `query_terms`, `expanded`, `ranking_mode`, `trigram`. Nhiều đoạn của
  cùng 1 mục được gộp (trường `merged`).
- Cầu nối thuật ngữ: bảng Markdown có ≥ 2 cột ngôn ngữ (tên cột ở `glossary_columns`). File dự án khai báo ở
  `glossary_paths`; bảng từ chung `references/glossary-common.md` bật bằng `common_glossary` (mặc định bật).
  Câu gõ có dấu tiếng Việt được so có dấu ("bán" ≠ "bản").
- Từ hỏi bị bỏ theo `stopwords` (EN / VI / JA, sửa được trong cấu hình).
- Cấu hình mới (đều tùy chọn): `ranking`, `trigram_enabled`, `glossary_paths`, `common_glossary`,
  `glossary_columns`, `stopwords`, `query_routes`, `chunk_mode` (`structure` / `lines`), `text_formats`
  (`.json`, `.yaml`, `.yml`, `.toml`, `.txt` dưới `knowledge_paths`; mặc định rỗng).
- Chia đoạn `structure`: không cắt giữa bảng / khối code khi vừa `chunk_lines`; bảng dài cắt ở ranh giới
  hàng và lặp dòng tiêu đề; số dòng gốc và mã mục giữ nguyên.
- Ghi chỉ mục (`build`, `update`, `migrate`, `semantic import/approve/reject`, `maintain --apply`) giữ file
  khóa `.qkb/cache/writer.lock`; lệnh chỉ đọc mở SQLite ở chế độ chỉ đọc.
- Chỉ mục 2.1.0-b0 dùng tiếp được (schema 2); `update` đầu tiên tự tạo bảng trigram.
- Hành vi cũ: `"ranking": "classic", "chunk_mode": "lines", "trigram_enabled": false, "common_glossary": false`.

# Bổ sung 2.1.0-c1 (Phase C1 + E)

```powershell
python $qkb impact src/service/service.cpp      # đoạn KB nhắc file này + vấn đề (ISSUE) ảnh hưởng nó + file #include nó
python $qkb verify --links --top 50             # thêm "code", "includes", "issues", "parsers"
python $qkb status                              # thêm "parsers" (số file theo ngôn ngữ và mức phủ)
python $qkb search "OP-012"                      # node định nghĩa của mã đứng đầu
```

- Parser theo ngôn ngữ, cùng 1 giao diện (`scripts/parsers.py`): Python = AST (`FULL`); C / C++ / Qt = thư viện chuẩn
  (`PARTIAL`: đồ thị `#include "…"`, khai báo namespace / class / struct / enum / hàm / macro dạng ứng viên; bỏ comment,
  chuỗi, khối `#if 0`); JS / TS = `FILE_ONLY`. **Không trích lời gọi hàm**, không đoán quan hệ.
- `#include "x.h"` tìm theo thứ tự: thư mục của file → `cpp_include_paths` → `source_paths`; `<x.h>` là header hệ thống
  (chỉ đếm). Không tìm được → `verify --links` → `includes.unresolved_items`.
- KB → code: backtick có đuôi code, có thể kèm `:dòng` / `:dòng-dòng` / `:a-b, c-d`. Bí danh: `code_aliases` trong cấu hình
  (`{"SV/": "service/", "svc.cpp": "service/service.cpp"}`) và dòng `` `X/` = `dir/` `` trong chính trang KB; bí danh
  được triển khai nhiều tầng. Tên file trần (`service.cpp`) chỉ nối khi duy nhất, trong cùng project hoặc trong file
  code không thuộc project nào; code của project khác chỉ nối qua `code_aliases`. Trùng tên → `AMBIGUOUS`, không có →
  `NOT_FOUND` — cả hai không tạo cạnh. `impact` / `related` nhận cả tên file hoặc đuôi đường dẫn duy nhất
  (`impact service.cpp`).
- Dòng viết trong KB được kiểm khi chạy `verify --links`: `STALE` (file code đổi kể từ lần `update` trang KB gần nhất),
  `LINE_OUT_OF_RANGE` (dòng vượt độ dài file hiện tại).
- Mã vấn đề / mã khác: `issue_id_patterns` (ví dụ `["OP-\\d+"]`), `id_patterns` (`{"requirement": ["REQ-\\d+"]}`); mặc định
  rỗng. Định nghĩa = dòng danh sách, hàng bảng hoặc heading bắt đầu bằng mã:
  `- **OP-012** · Status: open · Affects: `src/a.cpp`, `docs/api.md` · Source: REQ-012`. Nhãn trường đọc theo
  `issue_fields` (EN / VI / JA). Đường dẫn trên dòng định nghĩa → cạnh `AFFECTS`; mọi chỗ khác nhắc mã → `MENTIONS`;
  mã được nhắc mà chưa định nghĩa → `issues.undefined_ids`.
- File `CHANGELOG` theo `history_paths` không tạo cạnh code / mã.

# Bổ sung 2.1.0-d1 (tìm tiếng Việt và số)

```powershell
python $qkb search 'phi tre han'                      # không dấu vẫn tìm được "Phí trễ hạn"
python $qkb search 'phí 1234,5 nghìn'                 # số / ngày / đơn vị viết kiểu khác vẫn khớp
python $qkb search 'đường dẫn' --project demo,shared  # nhiều project (hoặc thư mục con: demo/sub)
python $qkb status --quick                            # chỉ stat file đã có trong chỉ mục (<= 1 s); không quét thư mục
```

- Chuẩn hóa: NFC và một vị trí dấu thanh (`hoà` = `hòa`, `thuỷ` = `thủy`) khi so có dấu; câu gõ có dấu → đoạn chứa
  đúng chữ có dấu đứng trên trong cùng mức.
- Từ hỏi tiếng Việt bị bỏ (`bao nhiêu`, `khi nào`, `làm thế nào`, `là gì`, `sau bao lâu`…; danh sách ở `stopwords.vi`);
  `query` chuyển "làm thế nào / làm sao / bằng cách nào / cơ chế" sang `explore`.
- Cụm 2–3 từ liền nhau có trong KB được cộng điểm (`phrases` trong kết quả); các từ vẫn tính riêng.
- Số: `1.234,5` = `1,234.5` = `1234.5`; `17/11/2026` = `2026-11-17`; `2,5 triệu` = `2500000`; `v2.1` = `phiên bản 2.1`
  = `version 2.1`; `5 %` = `5%`; `5 mm` = `5mm`. Đoạn khớp đủ số trong câu hỏi đứng trước. Số dính vào tên
  (`RS-485`, `6.9.1`) giữ nguyên là chữ.
- `languages.kb_content` (`vi` / `en` / `ja` / `mixed`, mặc định `mixed`): `ja` tắt cụm từ Latin; `vi` / `mixed` bật xếp
  đúng-dấu trước.
- `status --quick` báo `folders_changed` (thư mục có thể có file mới / bị xóa) thay vì quét; `status` vẫn là kiểm đầy đủ.
- Câu hỏi khó (diễn đạt khác hẳn): tìm thêm 2–3 cách hỏi (tiếng Việt có dấu, thuật ngữ tiếng Anh, chỉ từ khóa) và gộp
  kết quả; trên bộ câu hỏi đo tiếng Việt cách này nâng câu khó từ 0,80 lên 0,96.

# Bổ sung 2.1.0-d2 (gói dữ liệu KB)

- Gói nhập bằng `kbpack.py` nằm ở `.qkb/packs/<dự án>/PACK.json` (kèm `CHANGELOG.md` của gói); dữ liệu ở `kb/<dự án>/`.
  Engine chỉ đọc, không ghi vào đó.
- Thiết lập trong gói được ghép lúc nạp cấu hình: `glossary_files`, `history_paths` (tính từ `kb/<dự án>/`),
  `issue_id_patterns`, `id_patterns`, `issue_fields`, `query_routes`; `code_aliases` chỉ dùng cho trang của chính gói.
  Gói theo phần con: thư mục `.qkb/packs/<dự án>__<phần con>/`. Khóa sai kiểu trong `PACK.json` → gói bị bỏ qua kèm lý do.
  Giá trị trong `.qkb/config.json` luôn được giữ (danh sách được nối thêm, bảng chỉ thêm khóa còn thiếu).
  `qkb init` không bao giờ ghi thiết lập của gói vào `.qkb/config.json`.
- Gói không dùng được (sai định dạng, cần engine mới hơn `engine_min`, thiết lập lỗi) → trạng thái
  `IGNORED (<lý do>)` trong `status`, không ảnh hưởng phần còn lại.
- Từ 2.1.0-e2, gói là dữ liệu không tin cậy: mẫu mã (`issue_id_patterns`, `id_patterns`) dài quá 200 ký tự, có tham chiếu
  ngược, có lặp lồng nhau / lặp quanh `|` (kiểu `(a+)+`, `(a|aa)+`), không biên dịch được hoặc khớp chuỗi rỗng
  → `IGNORED (unsafe ID pattern (...))`; đường dẫn `glossary_files` / `history_paths` tuyệt đối, có `..` hoặc glossary
  không phải `.md` → `IGNORED (unsafe path ...)`. Trong `kb/<dự án>/` của mọi gói (kể cả gói bị bỏ qua) engine chỉ lập
  chỉ mục file `.md`, bất kể `text_formats` / `source_paths`; engine không bao giờ chạy file nào của gói.
- Gói không thêm `source_paths`: engine chỉ quét mã nguồn khai trong `.qkb/config.json`.
- Tham chiếu KB → code trong trang của gói mà mã nguồn không có trên máy (không thư mục nào trong
  `source_roots_expected` tồn tại) → `SOURCE_NOT_ON_MACHINE`, không tạo cạnh, đếm riêng ở `verify --links` → `code`.
- `status` và `verify --links` có thêm `packs`: dự án, `pack_id`, `kb_version`, ngày, bản trước, đường dẫn
  changelog, trạng thái.

# Bổ sung 2.1.0-e1 (tìm bằng model cục bộ — tùy chọn, mặc định TẮT)

```powershell
python $qkb embed                                  # xem số đoạn cần tính vector (không ghi)
python $qkb embed --apply                          # tính vector cho đoạn mới / đổi; file riêng .qkb/cache/vectors.sqlite3
python $qkb search 'làm sao sửa xe hơi' --semantic auto   # mặc định: chỉ dùng model khi bộ định tuyến cần
python $qkb search 'ERR500123' --semantic off      # không bao giờ dùng model
```

- Bật: `"embedding": {"backend": "onnx-local", "model": "<tên thư mục>"}` trong `.qkb/config.json`; model nằm ở
  `.qkb/models/<tên thư mục>/` (`onnx/model.onnx`, `tokenizer.json`, `MODEL.txt` do script tải model của bộ skill ghi).
  Engine chỉ mở file `.onnx` / `.json`, đối chiếu SHA256 với `MODEL.txt`, chạy `onnxruntime` với `CPUExecutionProvider`;
  `numpy` / `onnxruntime` chỉ được nạp khi dùng model.
- Khi nào dùng (`mode: auto`): câu hỏi ngôn ngữ tự nhiên (ít nhất `min_words` từ) **và** tìm theo chữ yếu (ít hơn số kết quả
  yêu cầu, hoặc đoạn tốt nhất phủ dưới `min_coverage` = 60 % khái niệm của câu; từ 2.1.0-e3, trước đó 50 %). Câu có số, ngày, mã, đường dẫn, tên hàm (cả dạng `MaxRetryCount` từ 2.1.0-e3),
  mã lỗi: luôn tìm theo chữ. Kết quả có `semantic: {used, reason}`.
- Kết quả model được gộp với kết quả chữ bằng RRF (`weight` = trọng số danh sách model).
- Vector tách khỏi chỉ mục thường; đổi model / hồ sơ → tính lại toàn bộ; chỉ đoạn đổi nội dung được tính lại. Xóa file
  vector hoặc đặt `backend: none` → trở lại như cũ, không cần `update`.
- Lỗi bất kỳ (thiếu model, sai SHA256, lỗi runtime, chưa có vector) → kết quả tìm theo chữ, `semantic.state: unavailable`.
- Từ 2.1.0-e2: `embed --apply` luôn tính lại SHA256 đầy đủ của model và tokenizer rồi ghi `.qkb/cache/model-hashes.json`;
  lệnh tìm chỉ đọc file này (khóa: đường dẫn, kích thước, thời gian sửa / đổi), không bao giờ ghi. Symlink / junction ở
  bất kỳ đâu trong thư mục model → không dùng model. Ngoài `.onnx` / `.json`, engine chỉ đọc `MODEL.txt` (bản ghi hash).
- Hồ sơ model tùy chọn `embedding-profile.json` cạnh model: `query_prefix`, `passage_prefix`, `max_tokens`, `pooling`,
  `normalize`, `batch`.
- Từ 2.1.0-e3, log sử dụng (tùy chọn, mặc định tắt): `"usage_log": {"path": "<thư mục tương đối>", "query_text": true,
  "miss_score": 0}`. Mỗi lệnh `search` / `query` / `explore` / `related` / `impact` ghi 1 dòng JSON vào
  `<path>/<yyyy-MM-dd>.jsonl`: `time`, `command`, `scope`, `route`, `reason`, `model`, `model_reason`, `ms` (gồm cả nạp
  model), `results`, `top_score`, `coverage` (đoạn tốt nhất / số khái niệm), `miss` (lỗi, 0 kết quả, hoặc điểm đầu dưới
  `miss_score`), `error`; `query` chỉ khi `query_text` là `true`. Không bao giờ ghi nội dung kết quả. Ghi lỗi (thư mục bị
  khóa, đầy đĩa) → bỏ qua, lệnh tìm không đổi. `path` phải nằm trong thư mục gốc (không `..`, ổ đĩa, link).
