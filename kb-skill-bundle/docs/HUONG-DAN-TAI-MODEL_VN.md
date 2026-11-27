# Hướng dẫn tải model cho bộ phận IT

## 1. Tải gì

| File | Dung lượng (theo trang nguồn, cần đối chiếu) | Bắt buộc |
|---|---|---|
| `onnx/model.onnx` | khoảng 470 MB | Có |
| `tokenizer.json` | khoảng 17,1 MB | Có |
| `config.json` | dưới 1 MB | Nên có |
| `tokenizer_config.json` | dưới 1 MB | Nên có |

- Model: `multilingual-e5-small`.
- Trang nguồn: `https://huggingface.co/intfloat/multilingual-e5-small`.
- Giấy phép: MIT (theo thẻ model; IT xem lại trên trang nguồn).
- Tổng cộng khoảng 0,5 GB.

## 2. Để làm gì

- Model biến câu hỏi và đoạn tài liệu thành vector, để tìm theo nghĩa (diễn đạt khác chữ, Việt ↔ Anh ↔ Nhật).
- Bộ skill KB bản 2.0 dùng model khi đã đặt model và máy có `onnxruntime` + `numpy` (thử nghiệm; mặc định tắt).
- Chạy hoàn toàn offline trên CPU, không cần GPU, không gửi dữ liệu ra ngoài.

## 3. Trước khi chạy script

1. Mở trang nguồn, ghi lại mã commit của kho đang xem.
2. Với từng file ở mục 1: lấy SHA256 hiển thị trên trang file, và dung lượng chính xác (byte) nếu có.
3. Điền vào `tools/models.manifest.json`: `sha256` của từng file; `bytes` nếu biết; `revision` = mã commit.
4. Còn file nào chưa có `sha256` thì script dừng, không tải.

## 4. Chạy script

Cách nhanh nhất (máy có mạng → máy dự án):

- Máy có mạng: `download-models.ps1 -Zip "E:\KB-Model_multilingual-e5-small_<ngày>.zip" -Apply` (sha256 trong manifest có thể để trống; script in mã đã tính, IT đối chiếu với trang nguồn).
- Chép file zip sang máy dự án.
- Máy dự án: `download-models.ps1 -Target "D:\work\demo" -FromZip "<file zip>" -Apply`, hoặc `install.py --model local --model-zip "<file zip>"`.

Các cách khác:

Windows (PowerShell 7 — `pwsh`; Windows PowerShell 5.1 bị từ chối từ 2.0.4):

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\download-models.ps1 -Target "D:\work\demo"
```

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\download-models.ps1 -Target "D:\work\demo" -Apply
```

macOS / Linux (cần `python3`, `curl`):

```bash
sh tools/download-models.sh --target /work/demo --apply
```

- Lệnh đầu chỉ in kế hoạch, không tải gì.
- Cần đi qua proxy: thêm `-Proxy http://<proxy>:<port>` (PowerShell) hoặc `--proxy http://<proxy>:<port>` (sh).
- Đã tải ở máy khác: chép cả thư mục sang, rồi dùng `-FromFolder <thư mục>` (PowerShell) hoặc `--from <thư mục>` (sh). Script kiểm y như khi tải.
- Nơi đặt: `<dự án>\.qkb\models\multilingual-e5-small\` (chỗ đặt do `install.py --model local` tạo). Thư mục này không đưa lên kho mã.

## 5. Script kiểm gì

- Chỉ nhận file `.onnx` và `.json`; chỉ nhận địa chỉ `https://`.
- Tải vào file tạm `.partial`; kiểm dung lượng và SHA256; đạt mới đổi tên. Không đạt thì xóa file tạm.
- Xong thì ghi `MODEL.txt` (tên model, nguồn, commit, giấy phép, ngày tải, SHA256 từng file).

| Mã thoát | Nghĩa |
|---|---|
| 0 | Xong, hoặc chỉ in kế hoạch |
| 1 | Có file không đạt dung lượng hoặc SHA256 |
| 2 | Sai tham số, hoặc manifest chưa điền đủ SHA256 |

## 6. Tự kiểm sau khi tải

```powershell
Get-FileHash ".qkb\models\multilingual-e5-small\onnx\model.onnx" -Algorithm SHA256
```

- So với mã trên trang nguồn và trong `MODEL.txt`: phải giống nhau.

## 7. Giới hạn

- Bản `.ps1` đã thử offline (lấy file từ thư mục, đóng zip, đặt từ zip). Bản `.sh` mới kiểm cú pháp, chưa chạy thử trên macOS / Linux.
- Chưa thử tải thật qua mạng của công ty.
