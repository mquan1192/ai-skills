"""Test skills/q-writing-style/scripts/lint_text.py (unittest, chỉ thư mục tạm). Chạy: python -B tests/test_lint_text.py"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unicodedata
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/q-writing-style/scripts/lint_text.py"
_spec = importlib.util.spec_from_file_location("lint_text", SCRIPT)
lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lint)


def codes(text, lang, **kw):
    return [f["code"] for f in lint.check(text, lang, **kw)]


class LintTextTests(unittest.TestCase):
    def test_clean_vietnamese_text(self):
        self.assertEqual(codes("Nhóm kiểm thử chạy 48 ca, 2 ca lỗi.\nQuý khách vui lòng đăng nhập lại.\n", "vi"), [])

    def test_nfd_is_error(self):
        self.assertIn("NFC001", codes(unicodedata.normalize("NFD", "Tiếng Việt"), "vi"))

    def test_tone_mark_mixing(self):
        self.assertIn("TONE001", codes("Hòa mạng xong, thuỷ điện chưa.", "vi"))
        self.assertNotIn("TONE001", codes("Hòa mạng xong, thủy điện chưa, khỏe.", "vi"))
        self.assertNotIn("TONE001", codes("Hoà mạng xong, thuỷ điện chưa, khoẻ.", "vi"))

    def test_qu_is_not_new_style(self):
        # "quý", "quỳ": u thuộc phụ âm "qu" nên không phải kiểu mới
        self.assertNotIn("TONE001", codes("Quý khách quỳ xuống, hòa bình.", "vi"))

    def test_dash_outside_code_only(self):
        self.assertIn("DASH001", codes("Bản cập nhật — đã xong — chạy tốt.", "vi"))
        self.assertNotIn("DASH001", codes("```\na — b\n```\nChạy `a -- b` xong.\nKhoảng 5–10 giây.", "vi"))

    def test_ai_phrases_per_language(self):
        self.assertIn("AIW001", codes("Không chỉ nhanh mà còn rẻ.", "vi"))
        self.assertIn("AIW001", codes("Let's dive in. This is a testament to the team.", "en"))
        self.assertIn("AIW001", codes("これは技術ではなく文化の問題だ。", "ja"))
        self.assertNotIn("AIW001", codes("The team ran 48 cases.", "en"))

    def test_bold_label_list(self):
        text = "- **Hiệu năng:** nhanh hơn\n- **Bảo mật:** mã hóa\n- **Giao diện:** mới\n"
        self.assertIn("BOLD001", codes(text, "vi"))
        self.assertNotIn("BOLD001", codes("- **Hiệu năng:** nhanh hơn\n- Bảo mật tốt\n", "vi"))

    def test_sentence_length_only_with_plain(self):
        long = " ".join(["word"] * 30) + "."
        self.assertNotIn("LEN001", codes(long, "en"))
        self.assertIn("LEN001", codes(long, "en", plain=True))

    def test_cli_exit_codes_and_fix_nfc(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.md"
            p.write_text(unicodedata.normalize("NFD", "Tiếng Việt — có gạch."), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(lint.main([str(p), "--lang", "vi"]), 1)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(lint.main([str(p), "--lang", "vi", "--fix-nfc"]), 0)
            text = p.read_text(encoding="utf-8")
            self.assertEqual(text, unicodedata.normalize("NFC", text))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(lint.main([str(p), "--lang", "vi", "--strict", "--json"]), 1)
            self.assertEqual(json.loads(out.getvalue())[str(p)][0]["code"], "DASH001")

    def test_dash_exemptions(self):
        for text in ("Khoảng 5 – 10 giây.", "Dịch Nhật – Việt – Anh.", "Xưng hô em – anh/chị.",
                     "| --- | --- |", "<!-- a — b -->", "Đoạn văn.\n\n    a — b\n", "~~~~\n```\na — b\n~~~~\nXong."):
            with self.subTest(text=text):
                self.assertNotIn("DASH001", codes(text, "vi"))
        self.assertIn("DASH001", codes("Hệ thống chạy ổn định ― nhóm đã kiểm.", "vi"))
        self.assertIn("DASH001", codes("Bản cập nhật đã xong – nhóm vận hành sẽ theo dõi thêm.", "vi"))

    def test_fence_closes_only_on_same_char(self):
        self.assertIn("DASH001", codes("```\ncode\n```\nBản cập nhật — đã xong.", "vi"))
        self.assertNotIn("DASH001", codes("````\n```\na — b\n````\n", "vi"))

    def test_ai_phrase_precision(self):
        self.assertIn("AIW001", codes("Đây không phải lỗi mà là tính năng.", "vi"))
        self.assertNotIn("AIW001", codes("Danh sách câu hỏi hay gặp về đăng nhập.", "vi"))
        self.assertIn("AIW001", codes("Câu hỏi rất hay!", "vi"))
        self.assertNotIn("AIW001", codes("この機能は必要不可欠です。手動ではなく自動で実行します。", "ja"))

    def test_bold_label_needs_colon(self):
        self.assertNotIn("BOLD001", codes("- **Hiệu năng** nhanh hơn\n- **Bảo mật** mã hóa\n- **Giao diện** mới\n", "vi"))
        self.assertIn("BOLD001", codes("- **A**: x\n- **B**: y\n- **C**: z\n", "vi"))

    def test_procedure_steps_use_20_words(self):
        step = "1. " + " ".join(["word"] * 22) + "."
        desc = " ".join(["word"] * 22) + "."
        self.assertIn("LEN001", codes(step, "en", plain=True))
        self.assertNotIn("LEN001", codes(desc, "en", plain=True))

    def test_pronoun_mix(self):
        self.assertIn("PRON001", codes("Quý khách vui lòng đăng nhập. Sau đó bạn chọn gói.", "vi"))
        self.assertNotIn("PRON001", codes("Quý khách vui lòng đăng nhập.", "vi"))

    def test_fix_nfc_keeps_bom_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.md"
            raw = "\ufeff" + unicodedata.normalize("NFD", "Dòng một\r\nDòng hai\r\n")
            p.write_bytes(raw.encode("utf-8"))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(lint.main([str(p), "--lang", "vi", "--fix-nfc"]), 0)
            data = p.read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(data.count(b"\r\n"), 2)
            self.assertEqual(data[3:].decode("utf-8"), unicodedata.normalize("NFC", "Dòng một\r\nDòng hai\r\n"))

    def test_missing_file_is_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lint.main(["/khong/co/file.md", "--lang", "vi"]), 2)


if __name__ == "__main__":
    unittest.main()
