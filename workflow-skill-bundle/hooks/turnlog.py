# turnlog.py - Claude Code hook: turn times for the process log (workflow skill bundle).
# Events: SessionStart, UserPromptSubmit (turn start), Stop (turn end), SubagentStop.
# Reads the hook JSON from stdin and appends ONE line to <root>/<paths.process_log>/turns/<yyyy-MM-dd>.jsonl:
#   {"at":"yyyy-MM-ddTHH:mm:ss","event":"...","session_id":"...","cwd":"..."}
# <root> = the nearest folder that holds .workflow/workflow.config.json, looked up from the hook's "cwd", else from
# this file's folder (--root <dir> for tests). No config found -> nothing is written.
# Never writes the prompt, transcript path / content or tool input. No network. Never prints anything (stdout of
# SessionStart / UserPromptSubmit hooks would go into the model context). Always exits 0; any error is swallowed.
# Python 3 standard library only; run with: python -I -S turnlog.py. ASCII only.
import sys

CONFIG = ('.workflow', 'workflow.config.json')


def find_root(start):
    import os
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, *CONFIG)):
            return d
        parent = os.path.dirname(d)
        if not parent or parent == d:
            return ''
        d = parent


def log_folder(root):
    """<root>/<paths.process_log>/turns; the config path must be plain and relative (else: no log)."""
    import json
    import os
    with open(os.path.join(root, *CONFIG), encoding='utf-8-sig') as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict) or cfg.get('schema') != 1:
        return ''
    rel = 'process-log'
    paths = cfg.get('paths')
    if isinstance(paths, dict) and isinstance(paths.get('process_log'), str) and paths['process_log'].strip():
        rel = paths['process_log']
    rel = rel.replace('\\', '/').strip().strip('/')
    parts = rel.split('/')
    if not rel or ':' in rel or any(p in ('', '.', '..') for p in parts):
        return ''
    return os.path.join(root, *parts, 'turns')


def main(argv):
    import json
    import os
    import re
    import time

    root = ''
    if len(argv) >= 3 and argv[1] == '--root':
        root = argv[2]
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').strip(chr(0xFEFF) + ' \r\n\t')
    data = json.loads(raw)
    if not isinstance(data, dict):
        return
    ev = data.get('hook_event_name')
    if ev not in ('SessionStart', 'UserPromptSubmit', 'Stop', 'SubagentStop'):
        return
    sid = data.get('session_id')
    if not isinstance(sid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', sid):
        sid = None
    cwd = data.get('cwd')
    if isinstance(cwd, str):
        cwd = re.sub(r'[\x00-\x1f\x7f]', '', cwd)[:400] or None
    else:
        cwd = None
    if root:
        root = root if os.path.isfile(os.path.join(root, *CONFIG)) else ''
    else:
        if cwd and os.path.isdir(cwd):
            root = find_root(cwd)
        if not root:
            root = find_root(os.path.dirname(os.path.abspath(__file__)))
    if not root:
        return
    folder = log_folder(root)
    if not folder:
        return
    os.makedirs(folder, exist_ok=True)
    now = time.localtime()   # local clock
    line = json.dumps({'at': time.strftime('%Y-%m-%dT%H:%M:%S', now), 'event': ev, 'session_id': sid, 'cwd': cwd},
                      ensure_ascii=False, separators=(',', ':')) + '\n'
    data_bytes = line.encode('utf-8')
    path = os.path.join(folder, time.strftime('%Y-%m-%d', now) + '.jsonl')
    with open(path, 'ab') as f:
        locked = False
        try:
            import msvcrt  # Windows: lock byte 0 so parallel sessions do not interleave lines
            for _ in range(50):
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError:
                    time.sleep(0.01)
        except ImportError:
            pass
        try:
            f.seek(0, 2)
            f.write(data_bytes)
            f.flush()
        finally:
            if locked:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except BaseException:
        pass
    try:
        sys.stdout.flush()
    except BaseException:
        pass
    sys.exit(0)
