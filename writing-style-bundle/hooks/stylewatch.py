# stylewatch.py - Claude Code hook: writing-style reminder (writing style bundle v1.2).
# Events:
#   UserPromptSubmit - the prompt contains a report / document keyword (config prompt_reminder.keywords)
#                      -> one reminder line as additionalContext: document-type skill -> q-writing-style -> self-check.
#   PostToolUse      - Write / Edit / MultiEdit of a file whose extension is in file_reminder.extensions and whose
#                      path is under one of file_reminder.output_dirs -> one reminder line: run the self-check gate.
# Settings: <root>/.writing-style/style.config.json; <root> = nearest folder with that file, looked up from the
# hook's "cwd" (--root <dir> for tests). No config, "enabled": false or the part switched off -> prints nothing.
# Never blocks, never fails the turn: any error -> exit 0, no output. Writes nothing, logs nothing, never prints the
# prompt or the file content. No network. Python 3 standard library only; run with: python -I -S stylewatch.py.
# Source is UTF-8 (the Vietnamese text is written inline); the JSON output is ASCII-escaped.
import sys

CONFIG = ('.writing-style', 'style.config.json')
DEFAULT_KEYWORDS = ['báo cáo', 'report', 'tài liệu', 'biên bản', 'mail', 'chat', 'jira',
                    'ticket', '報告書', '資料', 'メール', '議事録']
DEFAULT_EXT = ['.md', '.docx', '.xlsx', '.html', '.pptx']
DEFAULT_DIRS = ['out/', 'reports/', 'docs/']
EDIT_TOOLS = ('Write', 'Edit', 'MultiEdit')

PROMPT_LINE = ('[văn phong] Viết / sửa / dịch văn bản: skill loại tài liệu'
               ' (nếu có) → {skill} (báo cáo tiếng Việt: style-guide § 1.1;'
               ' soát dấu vết AI: ai-tells.md) → cổng tự soát trước khi trả lời hoặc ghi file.')
FILE_LINE = ('[văn phong] Vừa ghi file tài liệu ({ext}): chạy cổng tự soát của'
             ' {skill} (đúng số liệu, đủ ý, giữ trạng thái thông tin,'
             ' khớp sau khi sửa) trước khi báo xong.')


def norm(text):
    import unicodedata
    return unicodedata.normalize('NFC', text).casefold()


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


def load(root):
    import json
    import os
    with open(os.path.join(root, *CONFIG), encoding='utf-8-sig') as f:
        cfg = json.load(f)
    return cfg if isinstance(cfg, dict) else {}


def part(cfg, name):
    p = cfg.get(name)
    return p if isinstance(p, dict) else {}


def str_list(value, default):
    if isinstance(value, list):
        out = [v for v in value if isinstance(v, str) and v.strip()]
        return out
    return list(default)


SKILL_DEFAULT = 'q-writing-style'
LEGACY_NAMES = ('q-doc-edit',)     # tên skill trước 1.2.0; config cũ của dự án vẫn ghi tên này


def skill_name(cfg):
    s = cfg.get('skill_name')
    if not (isinstance(s, str) and s.strip() and len(s) <= 60) or s.strip() in LEGACY_NAMES:
        return SKILL_DEFAULT
    return s


def prompt_reminder(cfg, prompt):
    p = part(cfg, 'prompt_reminder')
    if p.get('enabled', True) is False or not isinstance(prompt, str) or not prompt:
        return ''
    text = norm(prompt)
    if any(norm(k) in text for k in str_list(p.get('keywords'), DEFAULT_KEYWORDS)):
        return PROMPT_LINE.format(skill=skill_name(cfg))
    return ''


def file_reminder(cfg, root, tool, tool_input):
    import os
    p = part(cfg, 'file_reminder')
    if p.get('enabled', True) is False or tool not in EDIT_TOOLS or not isinstance(tool_input, dict):
        return ''
    path = tool_input.get('file_path')
    if not isinstance(path, str) or not path:
        return ''
    full = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    try:
        if os.path.commonpath([os.path.abspath(root), full]) != os.path.abspath(root):
            return ''
    except ValueError:
        return ''                  # another drive
    rel = os.path.relpath(full, root).replace('\\', '/')
    ext = os.path.splitext(rel)[1].lower()
    if ext not in [e.lower() for e in str_list(p.get('extensions'), DEFAULT_EXT)]:
        return ''
    low = '/' + rel.lower()
    dirs = [d.replace('\\', '/').strip('/').lower() for d in str_list(p.get('output_dirs'), DEFAULT_DIRS)]
    if not any(d and ('/' + d + '/') in low for d in dirs):
        return ''
    return FILE_LINE.format(ext=ext, skill=skill_name(cfg))


def main(argv):
    import json
    import os
    root = argv[2] if len(argv) >= 3 and argv[1] == '--root' else ''
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').strip(chr(0xFEFF) + ' \r\n\t')
    data = json.loads(raw)
    if not isinstance(data, dict):
        return
    event = data.get('hook_event_name')
    if event not in ('UserPromptSubmit', 'PostToolUse'):
        return
    if not root:
        cwd = data.get('cwd')
        root = find_root(cwd if isinstance(cwd, str) and cwd else os.getcwd())
    if not root or not os.path.isfile(os.path.join(root, *CONFIG)):
        return
    cfg = load(root)
    if cfg.get('enabled', True) is False:
        return
    if event == 'UserPromptSubmit':
        line = prompt_reminder(cfg, data.get('prompt'))
    else:
        line = file_reminder(cfg, root, data.get('tool_name'), data.get('tool_input'))
    if not line:
        return
    payload = {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': line}}
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
