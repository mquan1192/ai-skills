"""In đoạn cấu hình hook KB cho .claude/settings.json của dự án — CHỈ IN, KHÔNG GHI.

Cách dùng:
    python -E -s -B tools/settings_fragment.py                       # in đoạn cần thêm
    python -E -s -B tools/settings_fragment.py --settings <file>     # in bản ghép + diff so với file đang có
    python -E -s -B tools/settings_fragment.py --python python3      # máy gọi Python bằng tên khác (macOS / Linux)

Đoạn cần thêm = hooks/hooks.json (dạng plugin), mỗi lệnh đổi sang dạng an toàn cho dự án:
python kiểm có <dự án>/.claude/hooks/<script> rồi mới chạy (runpy); thiếu script → thoát 0, không chặn gì.
Mỗi khối được thêm vào SAU các khối đang có của cùng sự kiện; khối đang có giữ nguyên. Sự kiện đã có lệnh gọi cùng
script (kể cả khối người dùng đã sửa, ví dụ timeout) thì không thêm khối trùng.
"""
import argparse
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pylauncher  # noqa: E402

PLUGIN = os.path.normpath(os.path.join(HERE, "..", "hooks", "hooks.json"))
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}/hooks/"
HOOK_SCRIPTS = ("kbwatch.py", "kbroute.py", "kbguard.py")
_SCRIPT = re.compile(r"(kbwatch|kbroute|kbguard)\.py")
_LEGACY_ARG = re.compile(r"(?:kbwatch|kbroute|kbguard)\.py\"?\s+(\w+)")
_SAFE_ARG = re.compile(r"sys\.argv=\[p(?:,'(\w+)')?\]")


def safe_command(script, arg=None, launcher="python"):
    """Hook command that runs <project>/.claude/hooks/<script> only when the file exists; missing file -> exit 0.
    launcher: how this machine starts Python (python | python3 | py -3 | a path), chosen by the installer."""
    argv = "[p,'%s']" % arg if arg else "[p]"
    return (launcher + " -I -S -c \"import os,runpy,sys;p=os.path.join(os.environ.get('CLAUDE_PROJECT_DIR') or '.',"
            "'.claude','hooks','%s');sys.argv=%s;os.path.isfile(p) and runpy.run_path(p,run_name='__main__')\""
            % (script, argv))


def is_safe(command):
    return "runpy" in command and "isfile" in command


def hook_key(command):
    """(script, arg) of a KB hook command in any form, or None when the command calls no KB hook script."""
    m = _SCRIPT.search(command or "")
    if not m:
        return None
    a = (_SAFE_ARG if is_safe(command) else _LEGACY_ARG).search(command)
    return m.group(0), (a.group(1) if a and a.group(1) else None)


def _entries(settings):
    """(event, group, entry) for every hook entry of a settings dict."""
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    for event, groups in (hooks.items() if isinstance(hooks, dict) else ()):
        for g in groups if isinstance(groups, list) else ():
            for h in (g.get("hooks") if isinstance(g, dict) else None) or ():
                if isinstance(h, dict):
                    yield event, g, h


def fragment(launcher="python"):
    with open(PLUGIN, encoding="utf-8") as f:
        hooks = json.load(f)["hooks"]
    for blocks in hooks.values():
        for block in blocks:
            for h in block.get("hooks", []):
                key = hook_key(h.get("command", ""))
                if key:
                    h["command"] = safe_command(key[0], key[1], launcher)
    return hooks


def upgrade_commands(settings, launcher="python"):
    """Copy of settings with every old-form KB hook command (python -I -S ".../kbguard.py" pre) rewritten to the safe
    form in place (matcher, timeout and other keys kept), and every safe-form KB hook command that starts another
    Python launcher switched to this one; (new settings, old-form rewritten, launcher switched)."""
    out = json.loads(json.dumps(settings))
    n = switched = 0
    for _, _, h in _entries(out):
        cmd = str(h.get("command", ""))
        key = hook_key(cmd)
        if key and not is_safe(cmd):
            h["command"] = safe_command(key[0], key[1], launcher)
            n += 1
        elif key and pylauncher.launcher_of(cmd) not in (None, launcher):
            h["command"] = pylauncher.swap(cmd, launcher)
            switched += 1
    return out, n, switched


def strip_kb_hooks(settings):
    """Copy of settings without hook entries that call a KB hook script (found by script name, whatever the other keys);
    empty groups / events are dropped. (new settings, entries removed, groups removed)."""
    out = json.loads(json.dumps(settings))
    hooks = out.get("hooks") if isinstance(out, dict) else None
    if not isinstance(hooks, dict):
        return out, 0, 0
    entries = groups_gone = 0
    for event in list(hooks):
        kept = []
        for g in hooks[event] if isinstance(hooks[event], list) else []:
            inner = g.get("hooks") if isinstance(g, dict) else None
            if not isinstance(inner, list):
                kept.append(g)
                continue
            keep = [h for h in inner if not (isinstance(h, dict) and hook_key(str(h.get("command", ""))))]
            entries += len(inner) - len(keep)
            if keep:
                kept.append(dict(g, hooks=keep) if len(keep) != len(inner) else g)
            elif inner:
                groups_gone += 1
            else:
                kept.append(g)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks:
        out.pop("hooks", None)
    return out, entries, groups_gone


def legacy_entries(settings):
    """[(event, script)] of old-form KB hook commands (exit 2 when the script is missing)."""
    return [(ev, hook_key(str(h.get("command", "")))[0]) for ev, _, h in _entries(settings)
            if hook_key(str(h.get("command", ""))) and not is_safe(str(h.get("command", "")))]


def merge(settings, frag):
    """New settings dict: KB blocks appended after existing blocks. A block is not added when the event already has
    commands calling the same KB scripts (identical block, or one the user edited, e.g. timeout)."""
    out = json.loads(json.dumps(settings))
    hooks = out.setdefault("hooks", {})
    for event, blocks in frag.items():
        current = hooks.setdefault(event, [])
        for block in blocks:
            have = {hook_key(str(h.get("command", ""))) for _, _, h in _entries({"hooks": {event: current}})}
            want = {hook_key(h.get("command", "")) for h in block.get("hooks", [])}
            if block not in current and not (want and want <= have):
                current.append(block)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="In đoạn cấu hình hook KB (không ghi file nào).")
    ap.add_argument("--settings", help="File settings.json đang dùng (chỉ đọc) để in bản ghép và diff")
    ap.add_argument("--python", default="python", help="Lệnh gọi Python trên máy dùng hook: python (mặc định), python3, \"py -3\"")
    args = ap.parse_args(argv)
    try:
        frag = fragment(pylauncher.normalize(args.python))
    except pylauncher.LauncherError as exc:
        print("LỖI: %s" % exc, file=sys.stderr)
        return 2
    if not args.settings:
        print(json.dumps({"hooks": frag}, ensure_ascii=False, indent=2))
        return 0
    try:
        with open(args.settings, encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, ValueError) as exc:
        print("LỖI: không đọc được %s (%s)" % (args.settings, exc.__class__.__name__), file=sys.stderr)
        return 2
    merged = merge(current, frag)
    old = json.dumps(current, ensure_ascii=False, indent=2).splitlines()
    new = json.dumps(merged, ensure_ascii=False, indent=2).splitlines()
    removed = [l for l in difflib.unified_diff(old, new, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
    print("# Bản ghép (chưa ghi). Dòng bị xoá so với bản đang có: %d" % len(removed))
    print("\n".join(difflib.unified_diff(old, new, "settings.json (đang có)", "settings.json (ghép)", lineterm="")))
    return 0 if not removed else 1


if __name__ == "__main__":
    sys.exit(main())
