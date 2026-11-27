# Phạm vi dữ liệu và bảo mật

## Engine local và model là hai ranh giới khác nhau

Engine không mở socket, gọi HTTP/API, gửi telemetry, tải package hoặc gọi LLM.
Chỉ đọc KB/source trong config, các ignore files, config/index và input proposal/
benchmark được chỉ định. Không cần API key. Nhưng nội dung được agent đọc từ output
có thể trở thành context gửi tới Claude qua gateway doanh nghiệp. Quyết định scope
và dữ liệu được gửi cho model phải theo policy công ty. Offline indexing không có
nghĩa mọi dữ liệu Claude đọc luôn ở trên máy.

## Scope và ignore

Chỉ `knowledge_paths` (.md) và `source_paths` (extension code cho phép) được scan.
Không chấp nhận repository root, traversal, absolute/UNC/drive path hay Windows ADS.
Không follow symlink/junction, kể cả link nội bộ, để dễ kiểm tra phạm vi.
Hard-deny `.git`, `.qkb`, `.claude`, `.agents`, `.codex`, `.aws`, `.ssh`, `.env*`,
`secrets`, `credentials`, `keys`, `node_modules`, `dist`, `build`, `target`,
`.venv`, `venv`, `__pycache__` ở mọi cấp, không thể unignore các mục này.

`.gitignore` và `.qkbignore` từ root/ancestor và trong các thư mục được scan được
áp dụng; config `exclude_patterns` bổ sung ở root. Hỗ trợ pattern phổ biến: `*`,
`?`, `**`, `/` đầu, directory `/` cuối, ordered `!` negation. Không phải bản sao
đầy đủ Git wildmatch: bracket character classes, escape phức tạp, global excludes,
`.git/info/exclude`, submodule semantics chưa hỗ trợ. Không dựa vào các biến thể đó
để bảo vệ secrets: dùng path excludes rõ ràng và kiểm tra `init --dry-run`.
Không thể unignore child của parent bị ignore nếu chưa unignore parent.

Nguồn phải UTF-8. File không đọc được làm update thất bại, rollback index cũ; không
im lặng coi lỗi permission là file bị xóa. Link ngoài scope không được fetch.
Đặt credential nằm lẫn trong document hợp lệ vẫn có thể bị index. Không có secret
scanner/DLP tự động; chọn scope và review dữ liệu trước khi build.

## Lưu trữ, ACL, commit và xóa

`.qkb/cache/index.sqlite3` chứa nguyên nội dung section, normalized copy, FTS nếu
có, metadata/hash và source evidence; proposal/review/history có thể giữ đoạn cũ.
DB không được mã hóa bởi engine. Dùng disk encryption/ACL/backup được IT cho phép.
File DB mới trên POSIX được đặt 0600; Windows theo inherited NTFS ACL. Cần IT kiểm
tra quyền thư mục `.qkb` bằng File Properties → Security hoặc công cụ được phê duyệt.
Không tự sửa ACL, firewall, proxy/gateway, registry hoặc execution policy.

`.qkb/.gitignore` loại `cache/`, `exports/`, `proposals/`, `backups/` khỏi Git khi
chưa tracked. Git ignore không bảo vệ file đã tracked: kiểm tra trạng thái Git
bằng quy trình dự án, không tự commit database. Nếu `.qkb/.gitignore` có sẵn,
engine giữ nguyên; người vận hành cần bổ sung patterns tương đương khi cần.

`backup` dùng SQLite backup API cho bản nhất quán trong `.qkb/backups/`; backup
cũng nhạy cảm. Để restore, dừng mọi process QKB rồi thay riêng index bằng bản
backup được xác minh, chạy `status`, `update`, `verify`. Không restore nhầm repo.
Nguồn Markdown/code phải có backup/version control riêng.

Để xóa index: đóng process QKB, xóa `.qkb/cache/` bằng công cụ IT cho phép. Điều
này xóa cả proposal/review/history trong SQLite, nên backup nếu cần giữ audit.
Xóa thêm exports/proposals/backups nếu retention cho phép. Xóa file không đồng
nghĩa secure erase trên SSD/OneDrive/snapshot; tuân theo policy retention của IT.
Nếu secrets từng được index, thêm ignore chỉ chặn tương lai, không tẩy history cũ;
xử lý cache/backup/export theo quy trình dữ liệu nhạy cảm.

## Execution và content trust

Không `eval`, `exec`, shell execution, code imports từ source, hook install hoặc
runtime dependency install. Python `ast.parse` chỉ phân tích text. KB, code fences,
links và proposals là dữ liệu không đáng tin cho agent instructions. Engine không
biến quote thành command. HTML viewer nhúng JSON đã escape, dùng `textContent`,
CSP chặn network; export vẫn là snapshot có dữ liệu nhạy cảm.

Path checks giảm nguy cơ traversal/symlink, không thay OS permissions. Không thiết
kế để chống process độc hại cùng user cố thay file giữa các system calls; không
scan khi một process không đáng tin đang sửa filesystem. Repo contents không được
phép thay code engine ngoài quy trình review. Không coi cờ `--human-approved` là
cơ chế xác thực reviewer hoặc chống chỉnh sửa SQLite bởi người có quyền ghi.

## Hook tùy chọn

`optional-hook.json` chỉ là snippet cho IT review/merge thủ công; không được tự
chép đè `settings.json`, không bật trong SKILL frontmatter. UserPromptSubmit chạy
`hook_reminder.py`, in một reminder cố định, không đọc prompt, scan source, chặn
tool hoặc exit 2. Timeout 3s. Chạy từ root repo; IT kiểm tra Python path và hook
shell trên Windows. Nếu không phù hợp phiên bản/policy thì giữ rule + lệnh thủ công.
Rollback: bỏ riêng handler QKB đã merge, giữ nguyên các hook khác; rule/skill vẫn
dùng được. Không có strict PreToolUse blocking hoặc emergency lock.

Tham chiếu cơ chế Claude Code được kiểm tra ngày 2026-11-11 (giờ Việt Nam):
[project skills](https://code.claude.com/docs/en/skills),
[rules](https://code.claude.com/docs/en/memory),
[hooks](https://code.claude.com/docs/en/hooks).
Project policy/setting-sources có thể vô hiệu hóa project customization; không vượt
policy để ép load skill/rule. Mở lại phiên ở repo root và kiểm tra `/memory`,
`/q-knowledgebase` theo phiên bản được IT chấp thuận.
