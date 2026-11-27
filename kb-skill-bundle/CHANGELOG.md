# Bộ skill KB — lịch sử thay đổi

## 2.0.5 (25/11/2026)

Engine không đổi: Q-KnowledgeBase 2.1.0-e3. File zip model không đổi. Chỉ đổi tài liệu, không đổi chức năng: skill, hook, engine, script, công cụ, `install.py` giữ nguyên từng byte.

- Thêm `README.md` (EN) dạng trang đầu GitHub: bộ skill làm gì, cho ai, cách hoạt động (mỗi thuật ngữ có một câu giải thích), sơ đồ Mermaid, cách chỉ lấy riêng gói này (zip ở trang Releases hoặc chép thư mục), cài / gỡ, an toàn, yêu cầu, giấy phép và dòng bản quyền; chỗ trống `[REPO-URL]`. `install.py` không cài file này vào dự án.
- Điền link kho mã thật (https://github.com/mquan1192/ai-skills) vào chỗ trống `[REPO-URL]` trong `README.md` và `README_VN.md`; `MANIFEST.json` cập nhật sha256 / bytes của các file này.
- `README.md` và `README_VN.md` viết lại thành 2 phần: Phần 1 Sơ lược (hình dung, trước / sau, cách dùng, bắt đầu trong 3 bước) cho người không đọc code; Phần 2 Chi tiết kỹ thuật. Sơ đồ Mermaid: nhãn ngắn, ngắt dòng bằng `<br/>`, tách thành nhiều sơ đồ nhỏ để GitHub không cắt chữ. Các mục đánh số của `README_VN.md` giữ nguyên số. `MANIFEST.json` cập nhật sha256 / bytes.
- Thêm `LICENSE`: nguyên văn Apache License 2.0. `install.py` không cài file này vào dự án.
- `README_VN.md`: dòng đầu trỏ sang `README.md`; thêm mục "Tổng quan" cùng nội dung (sơ đồ nhãn tiếng Việt, mục "Chỉ cài gói cần dùng") trước Mục lục; dòng "Gói:" và mẫu kết quả cài ghi bản 2.0.5; các mục 1–13 giữ nguyên.
- `MANIFEST.json` tạo lại bằng `tools/build_manifest.py --bundle-version 2.0.5`. Giá trị mặc định trong script vẫn là 2.0.4 (bản này không đổi script), nên lần tạo lại sau phải ghi rõ `--bundle-version`.

## 2.0.4 (25/11/2026)

Engine không đổi: Q-KnowledgeBase 2.1.0-e3. File zip model không đổi (dùng lại bản cũ).

- **Tìm trong KB**: tra bằng `qkb query` / `/q-kb-search` trước; `Grep` / `Glob` chỉ trong một thư mục con `<kb_root>/<dự án>/<phần>/`, không quét cả `<kb_root>/`. Hook `kbguard` thêm dòng nhắc riêng khi tìm quá rộng (cả `<kb_root>/` hoặc cả một dự án); hook chỉ báo, không chặn, không kiểm quyền.
- **Biểu tượng một nghĩa**: dòng báo của `kbguard` và các cảnh báo của `q-kb-search` dùng 🔸 (rủi ro nhỏ, chỉ để biết: chỉ mục / trang KB có thể đã cũ, KB đang cập nhật); kết luận "cần kiểm / mâu thuẫn" dùng ❓ thay cho ⚠️. Ký hiệu bên trong trang KB (`⚠️ Conflict:`, `Suy luận:`) giữ nguyên.
- **Tiền tố file yêu cầu**: `request_prefixes` mặc định `["REQ-", "KB-REQ-"]`: đọc cả hai, file mới vẫn dùng `REQ-`.
- **`/q-kb-request`**: dòng `[USER]` ghi thêm vị trí lượt của chính người dùng (ví dụ "lượt riêng của chủ dự án, ngay sau câu hỏi soạn sẵn lúc HH:MM", kèm vài chữ đầu khi khác câu soạn sẵn) để phiên quản lý kiểm trong một lần gọi.
- **Sản phẩm cho người ngoài nhóm**: không ghi version KB hay đường dẫn KB; chỉ ghi ngày và version / commit của tài liệu gốc (`q-kb-search`, khuôn README của phiên quản lý).
- **Phát hành quy tắc theo đợt**: khuôn README của phiên quản lý ghi thay đổi quy tắc / skill / hook phát hành tối đa 2 lần mỗi ngày (hoặc cùng thay đổi retro tuần), việc gấp / được chủ dự án duyệt phát hành ngay; nội dung KB phát hành như cũ.
- **Log giữ 90 ngày** (thay 14 ngày); bộ skill vẫn không tự xóa log.
- **Chỉ PowerShell 7**: `tools/download-models.ps1` từ chối Windows PowerShell 5.1 bằng một dòng `REFUSED: …`; `tests/bundle.Tests.ps1` chạy test Python trên `pwsh`, trên 5.1 chỉ kiểm việc từ chối đó. Lệnh mẫu trong tài liệu dùng `pwsh`.
- Chú thích trong code bỏ các mã review nội bộ.
- **Hook an toàn khi gỡ / nâng cấp**: lệnh hook ghi vào `.claude/settings.json` ở dạng `python -I -S -c "…isfile… runpy…"` — thiếu script thì thoát 0, không chặn prompt / tool. Gỡ bỏ mọi lệnh gọi `kbwatch.py` / `kbroute.py` / `kbguard.py` theo tên script (cả khối đã sửa `timeout`), in đúng số đã bỏ; còn lệnh dạng cũ ở `settings.local.json` thì giữ script hook và báo. Cài lại / nâng cấp đổi lệnh dạng cũ tại chỗ, không thêm khối trùng. `hooks/hooks.json` (dạng plugin) không đổi.
- **Nâng cấp từ 2.0.3**: installer giữ các khóa đã có trong `kb.config.json` (chỉ đặt lại `hooks.mode`, `search.model` như mọi lần cài) và không ghi đè `README.md` của phiên quản lý. Bản cài cũ có `"request_prefixes": ["REQ-"]` → thêm `"KB-REQ-"` bằng tay nếu muốn đọc cả hai; quy tắc mới của khuôn README (phát hành theo đợt, tìm KB, sản phẩm cho người ngoài nhóm) xem `templates/manager/README.md` và chép phần cần dùng.

## 2.0.3 (19/11/2026)

Engine không đổi: Q-KnowledgeBase 2.1.0-e3.

- **Tên dễ đọc** (K1): mẫu yêu cầu, quy ước KB và khuôn trang dùng nhãn nguồn `[USER] [CODE] [DOC] [INFER]` và mã điểm mở `OPEN-NNN`; nhãn cũ `[U] [C] [D] [I]` và mã `OP-NNN` vẫn được nhận. Cấu hình mặc định `issue_id_patterns` có cả `OPEN-\d+` và `OP-\d+`.
- **Tên file yêu cầu** (K2): khóa mới `request_prefixes` (mặc định `["REQ-"]`); hook `kbwatch` và `/q-kb-request` đọc mọi tiền tố trong danh sách, file mới dùng tiền tố đầu tiên. Mặc định không đổi gì.
- **Giờ trong KB** (K3): bước phát hành của phiên quản lý ghi giờ `HH:MM` vào mục CHANGELOG, tiêu đề `notes.md` mới và dòng "Last update" của INDEX.
- **Không báo trùng nguồn mới** (K4): `kbwatch` không tạo yêu cầu nạp nguồn cho nguồn đã có trong một yêu cầu đang mở (của bất kỳ ai, ví dụ yêu cầu nạp nguồn viết tay), chỉ khi yêu cầu ghi đúng mức nguồn (file trong `docs/`, cây `src/<tree>`); dòng trạng thái ghi mã yêu cầu đó.
- **Thời hạn giữ log** (K5): README ghi các thư mục log, thời hạn 14 ngày; bộ skill không tự xóa, việc xóa do quy trình dọn rác của nơi cài.

## 2.0.2 (18/11/2026)

Engine kèm theo: Q-KnowledgeBase 2.1.0-e3 (chi tiết: `docs/engine/CHANGELOG.md`).

- **Engine 2.1.0-e3**: nạp model 1 lần mỗi tiến trình, ngưỡng chọn dùng model 0,6, tên dạng PascalCase luôn tìm theo chữ, so vector nhanh hơn khi có numpy; log sử dụng `usage_log` — `install.py` bật sẵn (`process-log/kb-usage`, kèm câu tìm) khi dự án chưa tự đặt; muốn tắt: `"path": ""`.
- **Hook ghi log cả ở chế độ `on`** (`hooks.log`, mặc định bật): thời điểm, hook, sự kiện, mã quy tắc, dòng đã hiện, có nhắc model hay không, thời gian chạy (ms); không ghi câu gõ hay nội dung KB. Thư mục log: `hooks.log_dir` (trống = `hooks.observe_log_dir` như cũ).
- File zip model không đổi.

## 2.0.1 (18/11/2026)

Engine không đổi: Q-KnowledgeBase 2.1.0-e2.

- **Tự nhận file zip model**: đặt `KB-Model_*.zip` cạnh bộ skill (thư mục bộ skill, thư mục chứa nó, hoặc `models/` trong 2 chỗ đó) rồi chạy `install.py` không tham số → đúng 1 file hợp lệ thì dùng như `--model local --model-zip <file>` (ghi rõ tên file); file lỗi bị bỏ qua có ghi chú; từ 2 file hợp lệ → dừng và liệt kê; `--model none` luôn thắng.
- **File zip model riêng** `KB-Model_multilingual-e5-small_<ngày>.zip`: 4 file model + `MODEL.txt` + `LICENSE_NOTE.txt` (giấy phép MIT theo model card; giữ khi chia sẻ). Công cụ đặt model nhận thêm file `LICENSE_NOTE.txt` (văn bản nhỏ, engine không mở).

## 2.0 (18/11/2026)

Bản đầu tiên của bộ skill KB dùng chung (đặt tên 2.0; gồm cả gói dữ liệu KB). Engine kèm theo: Q-KnowledgeBase 2.1.0-e2.

### Có gì

- **Engine** `q-knowledgebase` 2.1.0-e2: tìm theo đoạn, đồ thị phụ thuộc, lệnh `query` tự chọn cách tìm, `--project`, `verify --links`, liên kết KB → code, mã vấn đề; tìm tiếng Việt có / không dấu, số / ngày / phiên bản / đơn vị, `status --quick` nhanh hơn; đọc thiết lập của gói dữ liệu đã nhập; tìm bằng model trên máy (tùy chọn, mặc định tắt, chế độ auto / on / off) (chi tiết: `docs/engine/CHANGELOG.md`).
- **Skill tra cứu, gửi yêu cầu**: `q-kb-search` (chỉ đọc, tra chỉ mục trước, tối đa 3 biến thể câu hỏi, nhãn dự án, dòng phạm vi `🔎`), `q-kb-request` (thêm trường "Mã vấn đề").
- **Skill của phiên quản lý KB**: `q-kb-sync`, `q-kb-add`, `q-kb-publish`.
  - Một quy ước đường dẫn chung.
  - Đánh dấu tài liệu đang dùng / đã cũ.
  - Dòng vấn đề `**ID** · Trạng thái · Ảnh hưởng · Nguồn`.
- **Phát hành an toàn**: `q-kb-publish` đếm liên kết hỏng trước, lưu bản đang chạy, chép, cập nhật chỉ mục, đếm lại. Số liên kết hỏng tăng → tự khôi phục bản cũ, **không** tăng version, không ghi changelog.
- **Hook** (mặc định chế độ quan sát, chỉ ghi log):
  - `kbwatch`: 1 dòng trạng thái KB khi mở phiên; nguồn mới → yêu cầu nạp nguồn (không trùng).
  - `kbroute`: nhắc model tra KB trước khi câu hỏi thuộc dự án.
  - `kbguard`: nhắc dùng chỉ mục khi tìm thẳng vào `kb/`; báo khi kết quả cũ hoặc liên kết hỏng **tăng**; lời nhắc cuối lượt tắt mặc định.
  - `kbscope`: lưu phạm vi tìm cho máy này.
- **Khuôn**: trang tài liệu, module, chủ đề, `INDEX.md`, `_sources.md`, `notes.md`, request, thư mục quản lý, `kb.config.example.json`, `kb-policy.default.md`.
- **`install.py`**: xem trước (mặc định), cài, gỡ, lùi lại, nâng cấp từ 2.0.0 / 2.1.x; câu hỏi có / không model (mặc định không); ghép `.claude/settings.json` sau các khối đang có; sao lưu và biên bản cài.

- **Tải model cho IT**: `tools/download-models.ps1` / `.sh` + `tools/models.manifest.json` (mặc định `multilingual-e5-small`); máy có mạng tải và đóng 1 zip (`-Zip`, in sha256 để IT đối chiếu); máy dự án đặt từ zip (`-FromZip` hoặc `install.py --model local --model-zip`), kiểm an toàn + sha256 theo `MODEL.txt`; hướng dẫn `docs/HUONG-DAN-TAI-MODEL_VN.md`. Gói không tự tải gì.

- **Gói dữ liệu KB** (`.claude/tools/kbpack.py`, `PACK.json`): xuất / nhập / kiểm / gỡ theo dự án hoặc theo phần; bản nhập chỉ đọc, cập nhật bằng gói mới hơn; quét thông tin đăng nhập, dữ liệu cá nhân, ranh giới dự án trước khi xuất; kiểm an toàn file zip khi nhập; chỉ mục không đi theo gói; file không phải Markdown / ảnh mặc định không vào gói. Khi nhập, luật an toàn do người nhập giữ: đuôi file khác chỉ qua `--allow-ext`, mẫu tìm mã trong gói được kiểm và chỉ dùng khi có `--accept-patterns`, từ chối tên file không an toàn trên Windows; mỗi phiên bản KB chỉ xuất 1 nội dung gói.
- **Cài dạng người đọc** (`install.py --profile reader`): engine, skill tra cứu, hook, công cụ gói dữ liệu; không có skill ghi KB.
- **Quy ước**: nhãn dự án trên mỗi dòng `kb/CHANGELOG.md`; liên kết sang dự án khác chỉ để tham khảo; skill ghi KB từ chối ghi vào dự án đã nhập.

### Giới hạn

- Tìm bằng model: chưa thử với model thật; cần `onnxruntime` + `numpy` (gói ngoài, IT cài).
- Chưa có dạng plugin (lý do ở `README_VN.md`).
- Chưa xác minh: phiên bản Claude Code tối thiểu; dòng `systemMessage` của hook có hiện trong app Desktop không; quyền chạy lệnh dạng PowerShell.
