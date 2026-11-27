# ctxwatch.py - Claude Code hook: context-size reminder (workflow skill bundle v1.1).
# Event: UserPromptSubmit. Reads the hook JSON from stdin, opens the session's own transcript (transcript_path, a
# .jsonl file), reads only its TAIL (<= TAIL_BYTES) and takes the last main-chain assistant entry with message.usage.
# Context ~= input_tokens + cache_read_input_tokens + cache_creation_input_tokens. A system compact_boundary line met
# before that entry (scanning back) means the session was compacted since -> prints nothing.
# Settings: <root>/.workflow/workflow.config.json, key "context": {"enabled", "warn_tokens", "strong_tokens"};
# <root> = nearest folder with that file, looked up from the hook's "cwd" (--root <dir> for tests). No config, or
# "enabled": false -> prints nothing.
#   below warn  -> prints nothing
#   >= warn     -> one reminder line as additionalContext (q-wf-team references/quy-tac-bo-sung.md section 2)
#   >= strong   -> the same line marked "very large"
# Never blocks, never fails the turn: any error, missing file or unknown format -> exit 0, no output. Writes nothing.
# Reads nothing but the config and the transcript named in the hook input. No network. Python 3 standard library
# only; run with: python -I -S ctxwatch.py. --warn N / --strong N override the thresholds (tests). Source is UTF-8
# (the Vietnamese text is written inline); the JSON output is ASCII-escaped.
import sys

CONFIG = ('.workflow', 'workflow.config.json')
WARN = 250000      # tokens: reminder from here on (default of context.warn_tokens)
STRONG = 500000    # tokens: reminder marked "very large" (default of context.strong_tokens)
TAIL_BYTES = 262144


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


def settings(root):
    """(enabled, warn, strong) from the config; bad values fall back to the defaults."""
    import json
    import os
    with open(os.path.join(root, *CONFIG), encoding='utf-8-sig') as f:
        cfg = json.load(f)
    ctx = cfg.get('context') if isinstance(cfg, dict) else None
    if not isinstance(ctx, dict):
        return True, WARN, STRONG
    num = lambda v, d: v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else d
    return ctx.get('enabled', True) is not False, num(ctx.get('warn_tokens'), WARN), num(ctx.get('strong_tokens'), STRONG)


def context_tokens(path, tail_bytes=TAIL_BYTES):
    import json
    import os
    size = os.path.getsize(path)
    start = size - tail_bytes if size > tail_bytes else 0
    with open(path, 'rb') as f:
        f.seek(start)
        buf = f.read(tail_bytes)
    lines = buf.split(b'\n')
    if start > 0:
        lines = lines[1:]          # first piece is a partial line
    for raw in reversed(lines):
        boundary = b'compact_boundary' in raw
        if not boundary and (b'"usage"' not in raw or b'"assistant"' not in raw):
            continue
        try:
            d = json.loads(raw.decode('utf-8', 'replace'))
        except ValueError:
            continue               # broken line: try the one before
        if boundary and isinstance(d, dict) and d.get('type') == 'system' and d.get('subtype') == 'compact_boundary':
            return None            # compacted after the last usage: that usage is stale -> silent
        if not isinstance(d, dict) or d.get('type') != 'assistant' or d.get('isSidechain') is True:
            continue
        m = d.get('message')
        u = m.get('usage') if isinstance(m, dict) else None
        if not isinstance(u, dict):
            continue
        total = 0
        for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
            v = u.get(k)
            if isinstance(v, int) and not isinstance(v, bool) and v > 0:
                total += v
        if total > 0:              # a synthetic entry carries zeros: keep looking
            return total
    return None


def reminder(total, warn=WARN, strong=STRONG):
    if total is None or total < warn:
        return ''
    k = lambda n: '%d nghìn' % (n // 1000)
    head = '⚠️ rất lớn: ' if total >= strong else ''
    return ('[context] ' + head + k(total) + ' ≥ ' + k(warn) +
            ' — q-wf-team (quy-tac-bo-sung § 2): không còn việc dở → ghi QUEUE_<ROLE>'
            ' (≤ 10 dòng) rồi xin dọn phiên; đang dở → ghi QUEUE'
            ' + xin nén phiên.')


def main(argv):
    import json
    import os
    warn = strong = None
    root = ''
    i = 1
    while i + 1 < len(argv):
        if argv[i] == '--warn':
            warn = int(argv[i + 1])
        elif argv[i] == '--strong':
            strong = int(argv[i + 1])
        elif argv[i] == '--root':
            root = argv[i + 1]
        i += 2
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').strip(chr(0xFEFF) + ' \r\n\t')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('hook_event_name') != 'UserPromptSubmit':
        return
    if not root:
        cwd = data.get('cwd')
        root = find_root(cwd if isinstance(cwd, str) and cwd else os.path.dirname(os.path.abspath(__file__)))
    if not root or not os.path.isfile(os.path.join(root, *CONFIG)):
        return
    enabled, cfg_warn, cfg_strong = settings(root)
    if not enabled:
        return
    path = data.get('transcript_path')
    if not isinstance(path, str) or not path.lower().endswith('.jsonl'):
        return
    line = reminder(context_tokens(path), warn or cfg_warn, strong or cfg_strong)
    if not line:
        return
    payload = {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': line}}
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))


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
