"""Tests of ctxwatch.py (stdlib unittest; temp folders only). Run: python -I -m unittest test_ctxwatch (in this folder).
CTXWATCH_HOOK=<path> runs the same tests against another copy of the hook (used for the red proof)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.environ.get('CTXWATCH_HOOK') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ctxwatch.py')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def assistant(tokens, sidechain=False):
    return json.dumps({'type': 'assistant', 'isSidechain': sidechain,
                       'message': {'role': 'assistant', 'usage': {'input_tokens': 10, 'cache_read_input_tokens': tokens - 10,
                                                                    'cache_creation_input_tokens': 0, 'output_tokens': 5}}})


class CtxwatchTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = os.path.join(self._t.name, 'du an')
        self.cfg(True)
        self.tr = os.path.join(self._t.name, 'session.jsonl')

    def tearDown(self):
        self._t.cleanup()

    def cfg(self, enabled, warn=250000, strong=500000, raw=None):
        body = raw if raw is not None else json.dumps(
            {'schema': 1, 'context': {'enabled': enabled, 'warn_tokens': warn, 'strong_tokens': strong}})
        write(os.path.join(self.root, '.workflow', 'workflow.config.json'), body)

    def transcript(self, *lines):
        write(self.tr, '\n'.join(lines) + '\n')

    def run_hook(self, payload=None, *args, raw=None):
        if payload is None:
            payload = {'hook_event_name': 'UserPromptSubmit', 'transcript_path': self.tr,
                       'cwd': os.path.join(self.root, 'sub')}
        os.makedirs(os.path.join(self.root, 'sub'), exist_ok=True)
        data = raw if raw is not None else json.dumps(payload).encode('utf-8')
        r = subprocess.run([sys.executable, '-I', '-S', HOOK] + list(args), input=data, capture_output=True, timeout=20)
        self.assertEqual(r.returncode, 0)
        return r.stdout.decode('ascii')

    def context(self, out):
        return json.loads(out)['hookSpecificOutput']['additionalContext']

    def test_below_warn_silent(self):
        self.transcript(assistant(249999))
        self.assertEqual(self.run_hook(), '')

    def test_at_warn_reminds(self):
        self.transcript(assistant(250000))
        line = self.context(self.run_hook())
        self.assertTrue(line.startswith('[context] 250 nghìn'))
        self.assertNotIn('rất lớn', line)

    def test_strong_marked(self):
        self.transcript(assistant(600000))
        self.assertIn('rất lớn', self.context(self.run_hook()))

    def test_thresholds_from_config(self):
        self.cfg(True, warn=1000, strong=5000)
        self.transcript(assistant(1500))
        self.assertIn('1 nghìn', self.context(self.run_hook()))

    def test_disabled_silent(self):
        self.cfg(False)
        self.transcript(assistant(900000))
        self.assertEqual(self.run_hook(), '')

    def test_no_config_silent(self):
        os.remove(os.path.join(self.root, '.workflow', 'workflow.config.json'))
        self.transcript(assistant(900000))
        self.assertEqual(self.run_hook(), '')

    def test_broken_config_silent(self):
        self.cfg(True, raw='{not json')
        self.transcript(assistant(900000))
        self.assertEqual(self.run_hook(), '')

    def test_compact_after_usage_silent(self):
        self.transcript(assistant(900000), json.dumps({'type': 'system', 'subtype': 'compact_boundary'}))
        self.assertEqual(self.run_hook(), '')

    def test_sidechain_ignored(self):
        self.transcript(assistant(100000), assistant(900000, sidechain=True))
        self.assertEqual(self.run_hook(), '')

    def test_broken_line_uses_previous(self):
        self.transcript(assistant(300000), '{"type": "assistant", "usage": broken')
        self.assertIn('300 nghìn', self.context(self.run_hook()))

    def test_huge_file_reads_tail_only(self):
        filler = json.dumps({'type': 'user', 'message': {'content': 'x' * 1000}})
        self.transcript(assistant(900000), *([filler] * 400), assistant(260000))
        self.assertIn('260 nghìn', self.context(self.run_hook()))

    def test_no_transcript_path_silent(self):
        self.assertEqual(self.run_hook({'hook_event_name': 'UserPromptSubmit', 'cwd': self.root}), '')

    def test_other_event_silent(self):
        self.transcript(assistant(900000))
        self.assertEqual(self.run_hook({'hook_event_name': 'Stop', 'transcript_path': self.tr, 'cwd': self.root}), '')

    def test_garbage_input_silent(self):
        self.assertEqual(self.run_hook(raw=b'\xff\xfe not json'), '')

    def test_writes_nothing(self):
        self.transcript(assistant(900000))
        before = sorted(os.listdir(self._t.name))
        self.run_hook()
        self.assertEqual(sorted(os.listdir(self._t.name)), before)


if __name__ == '__main__':
    unittest.main()
