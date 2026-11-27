"""Test stylewatch.py (unittest, chỉ thư mục tạm). Chạy: python -B test_stylewatch.py (trong thư mục này).
STYLEWATCH_HOOK=<đường dẫn> chạy cùng bộ test trên một bản hook khác (dùng cho red proof)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.environ.get('STYLEWATCH_HOOK') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stylewatch.py')


class StylewatchTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = os.path.join(self._t.name, 'du an mau')
        os.makedirs(os.path.join(self.root, 'out'))
        self.cfg({})

    def tearDown(self):
        self._t.cleanup()

    def cfg(self, extra, raw=None):
        body = {'schema': 1, 'enabled': True, 'skill_name': 'q-writing-style'}
        body.update(extra)
        path = os.path.join(self.root, '.writing-style', 'style.config.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(raw if raw is not None else json.dumps(body, ensure_ascii=False))

    def run_hook(self, payload, raw=None):
        payload = dict(payload)
        payload.setdefault('cwd', os.path.join(self.root, 'out'))
        data = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        r = subprocess.run([sys.executable, '-I', '-S', HOOK], input=data, capture_output=True, timeout=20)
        self.assertEqual(r.returncode, 0)
        out = r.stdout.decode('ascii')
        return json.loads(out)['hookSpecificOutput']['additionalContext'] if out else ''

    def prompt(self, text):
        return self.run_hook({'hook_event_name': 'UserPromptSubmit', 'prompt': text})

    def write(self, rel, tool='Write'):
        return self.run_hook({'hook_event_name': 'PostToolUse', 'tool_name': tool,
                              'tool_input': {'file_path': os.path.join(self.root, rel), 'content': 'x'}})

    # ---- lời nhắc khi nhận yêu cầu ----
    def test_prompt_with_keyword_reminds(self):
        line = self.prompt('Viết báo cáo tuần cho nhóm giúp tôi')
        self.assertTrue(line.startswith('[văn phong]'))
        self.assertIn('q-writing-style', line)

    def test_prompt_keyword_japanese(self):
        self.assertTrue(self.prompt('週次の報告書を作成してください'))

    def test_prompt_keyword_case_insensitive(self):
        self.assertTrue(self.prompt('Please draft the REPORT for Friday'))

    def test_prompt_without_keyword_silent(self):
        self.assertEqual(self.prompt('Chạy lại bộ test đơn vị giúp tôi'), '')

    def test_prompt_reminder_off_silent(self):
        self.cfg({'prompt_reminder': {'enabled': False}})
        self.assertEqual(self.prompt('Viết báo cáo tuần'), '')

    def test_custom_keywords(self):
        self.cfg({'prompt_reminder': {'keywords': ['bản tin']}})
        self.assertTrue(self.prompt('Soạn bản tin nội bộ'))
        self.assertEqual(self.prompt('Viết báo cáo tuần'), '')

    def test_whole_hook_off_silent(self):
        self.cfg({'enabled': False})
        self.assertEqual(self.prompt('Viết báo cáo tuần'), '')
        self.assertEqual(self.write('out/bao-cao.md'), '')

    def test_no_config_silent(self):
        os.remove(os.path.join(self.root, '.writing-style', 'style.config.json'))
        self.assertEqual(self.prompt('Viết báo cáo tuần'), '')

    def test_broken_config_silent(self):
        self.cfg({}, raw='{khong phai json')
        self.assertEqual(self.prompt('Viết báo cáo tuần'), '')

    def test_prompt_never_echoed(self):
        line = self.prompt('Viết báo cáo về MA-BI-MAT-123')
        self.assertNotIn('MA-BI-MAT-123', line)

    # ---- lời nhắc sau khi ghi file ----
    def test_write_doc_in_output_dir_reminds(self):
        line = self.write('out/bao-cao-tuan.md')
        self.assertIn('.md', line)
        self.assertIn('cổng tự soát', line)

    def test_edit_docx_reminds(self):
        self.assertTrue(self.write('out/sub/tai-lieu.docx', tool='Edit'))

    def test_code_file_silent(self):
        self.assertEqual(self.write('out/tool.py'), '')

    def test_doc_outside_output_dirs_silent(self):
        self.assertEqual(self.write('src/ghi-chu.md'), '')

    def test_file_outside_project_silent(self):
        other = os.path.join(self._t.name, 'khac', 'out', 'a.md')
        self.assertEqual(self.run_hook({'hook_event_name': 'PostToolUse', 'tool_name': 'Write',
                                        'tool_input': {'file_path': other}}), '')

    def test_other_tool_silent(self):
        self.assertEqual(self.write('out/bao-cao.md', tool='Read'), '')

    def test_file_reminder_off_silent(self):
        self.cfg({'file_reminder': {'enabled': False}})
        self.assertEqual(self.write('out/bao-cao.md'), '')

    def test_garbage_input_silent(self):
        self.assertEqual(self.run_hook({}, raw=b'\xff\xfe not json'), '')

    def test_writes_nothing(self):
        before = sorted(os.walk(self._t.name))
        self.prompt('Viết báo cáo tuần')
        self.write('out/bao-cao.md')
        self.assertEqual(sorted(os.walk(self._t.name)), before)


# ---- từ khóa của config mẫu v1.1 (9 từ mới: dịch thuật, slide, thiết kế, báo cáo) ----
# STYLEWATCH_EXAMPLE_CONFIG=<đường dẫn> chạy các ca này trên một bản config mẫu khác (dùng cho red proof: config v1.0.1 -> FAIL).
EXAMPLE_CONFIG = os.environ.get('STYLEWATCH_EXAMPLE_CONFIG') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'style.config.example.json')
OLD_KEYWORDS = ['báo cáo', 'report', 'tài liệu', 'biên bản', 'mail', 'chat', 'jira', 'ticket',
                '報告書', '資料', 'メール', '議事録']
NEW_KEYWORDS = ['dịch', '翻訳', '訳', 'translate', 'slide', 'pptx', 'powerpoint', '設計書', '報告']
# Mỗi câu chứa từ khóa mới của nó và không chứa từ khóa cũ nào (kiểm trong test), nên chỉ từ khóa mới kích hoạt
# ("翻訳" chứa luôn "訳", cả hai đều là từ khóa mới).
NEW_PROMPTS = {
    'dịch': 'Dịch đoạn này giúp tôi',
    '翻訳': 'この文書を翻訳してください',
    '訳': '英文を和訳してください',
    'translate': 'Please translate this paragraph',
    'slide': 'Make the slide shorter',
    'pptx': 'Open the pptx and fix the title',
    'powerpoint': 'Edit the powerpoint please',
    '設計書': '設計書を確認してください',
    '報告': '報告をまとめてください',
}

# ---- từ khóa thêm ở v1.2 (mọi loại viết: bài viết, giọng văn, humanize, blog, 文章 ...) ----
V12_KEYWORDS = ['bài viết', 'văn bản', 'viết lại', 'giọng văn', 'văn AI', 'humanize', 'blog', 'release note',
                'proofread', '文章', '記事']
V12_PROMPTS = {
    'bài viết': 'Sửa bài viết này cho gọn',
    'văn bản': 'Làm văn bản này tự nhiên hơn',
    'viết lại': 'Viết lại đoạn giới thiệu sản phẩm',
    'giọng văn': 'Giữ giọng văn của tôi khi sửa',
    'văn AI': 'Đoạn này nghe như văn AI quá',
    'humanize': 'Humanize this paragraph',
    'blog': 'Draft a blog post about caching',
    'release note': 'Write the release note for v2',
    'proofread': 'Proofread this README',
    '文章': 'この文章を直してください',
    '記事': '技術記事を書いてください',
}


class LegacySkillNameTests(StylewatchTests):
    """Dự án cài bản trước 1.2.0 còn ghi skill_name = q-doc-edit: hook nhắc tên mới."""

    def setUp(self):
        super().setUp()
        self.cfg({'skill_name': 'q-doc-edit'})

    def test_legacy_name_maps_to_new(self):
        line = self.prompt('Viết báo cáo tuần')
        self.assertIn('q-writing-style', line)
        self.assertNotIn('q-doc-edit', line)

    def test_custom_name_kept(self):
        self.cfg({'skill_name': 'my-style'})
        self.assertIn('my-style', self.prompt('Viết báo cáo tuần'))


class ExampleConfigKeywordTests(StylewatchTests):
    """Chạy cả bộ test trên config mẫu thật của gói, cộng các ca cho 9 từ khóa mới."""

    def setUp(self):
        super().setUp()
        with open(EXAMPLE_CONFIG, 'r', encoding='utf-8') as f:
            text = f.read()
        self.cfg({}, raw=text)

    def example_keywords(self):
        with open(EXAMPLE_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)['prompt_reminder']['keywords']

    def test_example_keywords_old_first_then_new(self):
        kw = self.example_keywords()
        self.assertEqual(kw[:len(OLD_KEYWORDS)], OLD_KEYWORDS)
        self.assertEqual(kw[len(OLD_KEYWORDS):len(OLD_KEYWORDS) + len(NEW_KEYWORDS)], NEW_KEYWORDS)
        self.assertEqual(kw[len(OLD_KEYWORDS) + len(NEW_KEYWORDS):], V12_KEYWORDS)

    def test_each_v12_keyword_reminds(self):
        for kw, text in V12_PROMPTS.items():
            with self.subTest(keyword=kw):
                low = text.lower()
                self.assertIn(kw.lower(), low)
                for old in OLD_KEYWORDS + NEW_KEYWORDS:
                    self.assertNotIn(old, low, kw)
                line = self.prompt(text)
                self.assertTrue(line.startswith('[văn phong]'), kw)
                self.assertIn('q-writing-style', line)

    def test_example_skill_name_is_q_writing_style(self):
        with open(EXAMPLE_CONFIG, 'r', encoding='utf-8') as f:
            self.assertEqual(json.load(f)['skill_name'], 'q-writing-style')

    def test_new_prompts_use_only_their_own_keyword(self):
        for kw, text in NEW_PROMPTS.items():
            low = text.lower()
            self.assertIn(kw, low)
            for old in OLD_KEYWORDS:
                self.assertNotIn(old, low, kw)

    def test_each_new_keyword_reminds(self):
        for kw, text in NEW_PROMPTS.items():
            with self.subTest(keyword=kw):
                line = self.prompt(text)
                self.assertTrue(line.startswith('[văn phong]'), kw)
                self.assertIn('q-writing-style', line)

    def test_old_keywords_still_remind(self):
        for text in ('Viết báo cáo tuần', 'Draft the report', '資料を作成して', 'メールを書いて'):
            with self.subTest(prompt=text):
                self.assertTrue(self.prompt(text))

    def test_unrelated_prompt_still_silent_with_example_config(self):
        self.assertEqual(self.prompt('Chạy lại bộ test đơn vị giúp tôi'), '')


if __name__ == '__main__':
    unittest.main()
