"""Tests of turnlog.py (stdlib unittest; temp folders only). Run: python -I -m unittest test_turnlog (in this folder)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'turnlog.py')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def config(root, process_log='process-log', schema=1):
    write(os.path.join(root, '.workflow', 'workflow.config.json'),
          json.dumps({'schema': schema, 'paths': {'process_log': process_log}}))


def run(payload, *args, raw=None):
    data = raw if raw is not None else json.dumps(payload).encode('utf-8')
    r = subprocess.run([sys.executable, '-I', '-S', HOOK] + list(args), input=data, capture_output=True, timeout=20)
    return r.returncode, r.stdout


def lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


class TurnlogTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.t = os.path.join(self._t.name, 'proj a')
        os.makedirs(self.t)
        self.day = time.strftime('%Y-%m-%d')

    def tearDown(self):
        self._t.cleanup()

    def turns(self, rel='process-log'):
        return os.path.join(self.t, *rel.split('/'), 'turns', self.day + '.jsonl')

    def test_root_from_cwd_and_one_line_without_prompt(self):
        config(self.t)
        sub = os.path.join(self.t, 'a', 'b')
        os.makedirs(sub)
        marker = 'PROMPT-SECRET-TEXT'
        code, out = run({'hook_event_name': 'UserPromptSubmit', 'session_id': 'abc-123', 'cwd': sub, 'prompt': marker,
                         'transcript_path': 'C:/x/' + marker + '.jsonl'})
        self.assertEqual((code, out), (0, b''))
        got = lines(self.turns())
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]['event'], got[0]['session_id'], got[0]['cwd']), ('UserPromptSubmit', 'abc-123', sub))
        with open(self.turns(), encoding='utf-8') as f:
            self.assertNotIn(marker, f.read())

    def test_custom_process_log_path(self):
        config(self.t, 'logs/proc')
        run({'hook_event_name': 'Stop', 'session_id': 's1', 'cwd': self.t})
        self.assertEqual(len(lines(self.turns('logs/proc'))), 1)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'process-log')))

    def test_no_config_or_bad_config_writes_nothing(self):
        code, out = run({'hook_event_name': 'Stop', 'session_id': 's1', 'cwd': self.t}, '--root', self.t)
        self.assertEqual((code, out), (0, b''))
        self.assertEqual(os.listdir(self.t), [])
        for bad in ('../out', 'C:/x', 'a//b'):
            config(self.t, bad)
            run({'hook_event_name': 'Stop', 'session_id': 's1', 'cwd': self.t})
        config(self.t, schema=2)
        run({'hook_event_name': 'Stop', 'session_id': 's1', 'cwd': self.t})
        self.assertEqual(sorted(os.listdir(self.t)), ['.workflow'])

    def test_other_events_bad_json_and_bad_ids_exit_0(self):
        config(self.t)
        for raw in (b'not json', b'[1, 2]', b''):
            self.assertEqual(run(None, raw=raw), (0, b''))
        run({'hook_event_name': 'PreToolUse', 'session_id': 's1', 'cwd': self.t})
        self.assertEqual(lines(self.turns()), [])
        run({'hook_event_name': 'SessionStart', 'session_id': 'bad id with spaces', 'cwd': self.t})
        self.assertIsNone(lines(self.turns())[0]['session_id'])

    def test_log_folder_is_a_file_exit_0(self):
        config(self.t)
        write(os.path.join(self.t, 'process-log'), 'a file')
        self.assertEqual(run({'hook_event_name': 'Stop', 'session_id': 's1', 'cwd': self.t}), (0, b''))

    def test_source_ascii_only(self):
        with open(HOOK, 'rb') as f:
            self.assertFalse([b for b in f.read() if b > 127])


if __name__ == '__main__':
    unittest.main()
