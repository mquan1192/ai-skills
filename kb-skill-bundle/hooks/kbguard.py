# kbguard.py - KB reminders on tool use and at the end of a turn. Never blocks, never changes a call.
#   pre   (PreToolUse Grep|Glob): search into kb_root or projects_root -> model line "dùng qkb query trước";
#         a search over the whole kb_root or a whole project (<kb_root>/<project>) -> a stronger line: Grep only
#         inside one sub-folder <kb_root>/<project>/<sub>/ (v2.0.4). Report only: never blocks, never checks rights.
#         Read is not covered: reading a page the index pointed to is the normal next step.
#   post  (PostToolUse Bash|PowerShell): a qkb command whose output shows stale / broken sources or broken links
#         -> one user line + model line (a problem).
#   stop  (Stop): the turn wrote a task output (hooks.task_output_pattern) and sent no KB request
#         -> one user line "nhớ gửi /q-kb-request". Reads only the tail of the transcript (tool names and paths).
# Tool input / output and the transcript are read in memory only; nothing of them is logged (codes only).
# Usage: python -I -S kbguard.py pre|post|stop [--root <dir>]
import os
import sys

sys.dont_write_bytecode = True   # -I -S hooks: never leave __pycache__ next to the hook
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json  # noqa: E402
import re  # noqa: E402

import kbcommon as kc  # noqa: E402

STALE = re.compile(r'"source_status"\s*:\s*"(STALE|BROKEN)"|"state"\s*:\s*"STALE"|\bSource is (STALE|BROKEN)\b')
BROKEN = re.compile(r'"broken"\s*:\s*(\d+)')   # 0 too: a drop must lower the stored baseline
TAIL_BYTES = 400000


def roots(cfg):
    return [(cfg.get('kb_root') or 'kb'), (cfg.get('projects_root') or 'projects')]


def pre(root, cfg, hcfg, data):
    tool = data.get('tool_name') or ''
    if tool not in ('Grep', 'Glob'):
        return
    ti = data.get('tool_input') or {}
    path = ti.get('path') or ''
    if not path and tool == 'Glob':
        path = (ti.get('pattern') or '').split('*')[0]
    target = kc.rel(root, path) if path else None
    if target is None or not any(kc.under(target, r) for r in roots(cfg)):
        return
    line = ('[KB] Tìm trong KB / nguồn: dùng qkb query (hoặc /q-kb-search) trước; Grep / Glob chỉ khi chỉ mục không '
            'tìm ra hoặc cần trích nguyên văn.')
    codes = ['SEARCH_WITHOUT_INDEX']
    kb = (cfg.get('kb_root') or 'kb').replace(chr(92), '/').strip('/')
    if kc.under(target, kb) and len([s for s in target[len(kb):].split('/') if s]) < 2:
        # v2.0.4: the whole KB or a whole project is too broad -> one project sub-folder only (report, never block)
        line = ('[KB] Tìm quá rộng (%s/): dùng qkb query (hoặc /q-kb-search) trước; nếu vẫn cần Grep / Glob thì chỉ '
                'trong một thư mục con %s/<dự án>/<phần>/, không quét cả %s/.' % (target or kb, kb, kb))
        codes.append('SEARCH_TOO_BROAD')
    kc.emit(root, hcfg, 'PreToolUse', 'kbguard', None, line, codes)


def strings(value, depth=0):
    """Every string inside the tool response (stdout of a shell tool may hold the JSON as text)."""
    if depth > 6:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings(v, depth + 1)]
    if isinstance(value, list):
        return [s for v in value for s in strings(v, depth + 1)]
    return []


def post(root, cfg, hcfg, data):
    if (data.get('tool_name') or '') not in ('Bash', 'PowerShell'):
        return
    command = str((data.get('tool_input') or {}).get('command') or '')
    if 'qkb.py' not in command:
        return
    text = '\n'.join(strings(data.get('tool_response')))
    codes, notes = [], []
    if STALE.search(text):
        codes.append('STALE_RESULT')
        notes.append('kết quả có đoạn đã cũ so với file gốc')
    m = BROKEN.search(text)
    if m:
        # warn only when the count rose against the last value seen on this machine
        count = int(m.group(1))
        last = kc.local_state(root, 'kb-links-baseline').get('broken')
        # keep the per-machine baseline in observe mode too (nothing shown), so the observe log can
        # count how often a rise would have warned
        kc.local_state(root, 'kb-links-baseline', {'broken': count})
        if isinstance(last, int) and count > last:
            codes.append('BROKEN_LINKS_ROSE')
            notes.append('liên kết hỏng tăng %d → %d' % (last, count))
    if not codes:
        return
    user = '🔸 KB: ' + ' · '.join(notes) + ' → báo phiên quản lý KB (/q-kb-request).'
    model = ('[KB] ' + '; '.join(notes) + '. Do not cite stale line numbers as current; say the KB may be out of date '
             'and suggest /q-kb-request.')
    kc.emit(root, hcfg, 'PostToolUse', 'kbguard', user, model, codes)


def tail_events(path):
    """Assistant tool calls after the last real user message: [(tool name, file path or '', skill name or '')]."""
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            raw = f.read().decode('utf-8', 'replace')
    except Exception:
        return []
    events = []
    for line in raw.splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        msg = obj.get('message') if isinstance(obj, dict) else None
        if not isinstance(msg, dict):
            continue
        content = msg.get('content')
        if obj.get('type') == 'user' and (isinstance(content, str) or
                                          (isinstance(content, list) and any(isinstance(c, dict) and
                                                                             c.get('type') == 'text' for c in content))):
            events = []          # a new user turn starts
            continue
        if obj.get('type') != 'assistant' or not isinstance(content, list):
            continue
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'tool_use':
                ti = c.get('input') if isinstance(c.get('input'), dict) else {}
                events.append((c.get('name') or '', str(ti.get('file_path') or ''), str(ti.get('skill') or '')))
    return events


def stop(root, cfg, hcfg, data):
    if data.get('stop_hook_active'):
        return
    events = tail_events(data.get('transcript_path') or '')
    if not events:
        return
    pattern = re.compile(str(hcfg['task_output_pattern']))
    requests = (cfg.get('requests_folder') or '00_UpdateDocs/requests')
    wrote_output = False
    for name, path, skill in events:
        if skill == 'q-kb-request':
            return
        target = kc.rel(root, path) if path else None
        if name in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit') and target:
            if kc.under(target, requests):
                return
            if pattern.search(target):
                wrote_output = True
    if not wrote_output:
        return
    user = '💡 KB: lượt này có kết quả mới trong out/ — nếu có thông tin đã kiểm chứng, gửi /q-kb-request.'
    #  (owner choice: user notes only at session start and on problems): stop_notice "off" = log only
    if hcfg['mode'] == 'on' and hcfg['stop_notice'] != 'once':
        kc.log(root, hcfg, {'hook': 'kbguard', 'event': 'Stop', 'codes': ['TASK_OUTPUT_NO_REQUEST'],
                            'would_show': user, 'would_tell_model': False})
        return
    if hcfg['mode'] == 'on':
        sid = str(data.get('session_id') or '')[:80]
        seen = kc.local_state(root, 'kbguard-stop').get('sessions') or []
        if sid in seen:
            return
        kc.local_state(root, 'kbguard-stop', {'sessions': (seen + [sid])[-50:]})
    kc.emit(root, hcfg, 'Stop', 'kbguard', user, None, ['TASK_OUTPUT_NO_REQUEST'])


def main(argv):
    mode = next((a for a in argv if a in ('pre', 'post', 'stop')), None)
    root = kc.project_root(argv)
    data = kc.read_stdin()
    if mode is None or not kc.has_index(root):
        return 0
    cfg = kc.load_config(root)
    if cfg is None:
        return 0
    hcfg = kc.hooks_cfg(cfg)
    if hcfg['mode'] == 'off':
        return 0
    {'pre': pre, 'post': post, 'stop': stop}[mode](root, cfg, hcfg, data)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
