"""Chọn lệnh gọi Python để ghi vào hook / quyền / config của dự án (chỉ thư viện chuẩn, không dùng mạng).

Vì sao cần: mỗi máy gọi Python bằng một tên khác nhau.
- Windows (bản python.org): `python` hoặc `py -3`; `python3` thường là lối tắt mở Microsoft Store, không chạy được.
- macOS / Linux: thường chỉ có `python3`; `python` không có, hoặc là Python 2 trên máy cũ.
Lệnh hook ghi cứng `python` vì vậy hỏng trên macOS / Linux. Bộ cài thử từng lệnh và ghi lệnh chạy được.

Thứ tự thử: lệnh đang dùng trong dự án (để máy khác trong nhóm không bị đổi qua đổi lại) → python → python3 → py -3.
Một lệnh được nhận khi nó chạy thật, đủ phiên bản tối thiểu, và (nếu cần) SQLite có FTS5.
Người cài chỉ định lệnh khác bằng --python (ví dụ đường dẫn python của một venv); dấu \\ được đổi thành /.
"""
import json
import os
import re
import shutil
import subprocess

CANDIDATES = ("python", "python3", "py -3")
_TOKEN = re.compile(r'"([^"]*)"|(\S+)')
_UNSAFE = re.compile(r"[;|&<>`$\r\n']")
_PREFIX = re.compile(r"^(.+?)\s+-(?:I -S|E -s -B)(?=\s)")
_PROBE = ("import sys,json\n"
          "fts=False\n"
          "try:\n"
          " import sqlite3\n"
          " c=sqlite3.connect(':memory:');c.execute('CREATE VIRTUAL TABLE t USING fts5(x)');c.close();fts=True\n"
          "except Exception:\n"
          " pass\n"
          "print(json.dumps({'version':list(sys.version_info[:3]),'fts5':fts,'executable':sys.executable}))\n")


class LauncherError(Exception):
    pass


def tokens(command):
    """['py', '-3'] for 'py -3'; a double-quoted part is one token (a path with spaces), on every OS."""
    return [a or b for a, b in _TOKEN.findall(command or "")]


def normalize(command):
    """Launcher text as it is written into a hook command: trimmed; an existing file path with spaces gets quotes."""
    command = (command or "").strip()
    if not command:
        raise LauncherError("lệnh Python rỗng")
    if _UNSAFE.search(command):
        raise LauncherError("lệnh Python có ký tự không dùng được trong lệnh hook: %s" % command)
    if '"' not in command and " " in command and os.path.isfile(command):
        command = '"%s"' % command
    return command.replace("\\", "/")      # hooks run through sh / Git Bash, where a bare backslash is dropped


def launcher_of(command):
    """Launcher part of a command written by a bundle ('python3' in 'python3 -I -S -c ...'), or None."""
    m = _PREFIX.match(command or "")
    return m.group(1).strip() if m else None


def swap(command, launcher):
    """The same command with its launcher part replaced; unchanged when it has no launcher part."""
    old = _PREFIX.match(command or "")
    return launcher + command[old.end(1):] if old else command


def probe(command, timeout=20):
    """{'version': [3, 14, 0], 'fts5': bool, 'executable': path} when the launcher really runs Python, else None.
    A name that is missing, a Microsoft Store shortcut, Python 2 and a launcher that hangs all give None."""
    parts = tokens(command)
    if not parts:
        return None
    exe = shutil.which(parts[0]) or (parts[0] if os.path.isfile(parts[0]) else None)
    if not exe:
        return None
    try:
        r = subprocess.run([exe] + parts[1:] + ["-I", "-S", "-c", _PROBE], capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        info = json.loads(r.stdout.decode("utf-8", "replace").strip().splitlines()[-1]) if r.returncode == 0 else None
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None
    ok = isinstance(info, dict) and isinstance(info.get("version"), list) and len(info["version"]) == 3
    return info if ok else None


def reason(info, minimum, need_fts5):
    """None when the probed interpreter is usable, else a short Vietnamese reason."""
    if info is None:
        return "không chạy được"
    if tuple(info["version"][:2]) < tuple(minimum):
        return "là Python %d.%d, cần %d.%d trở lên" % (info["version"][0], info["version"][1], minimum[0], minimum[1])
    if need_fts5 and not info.get("fts5"):
        return "SQLite không có FTS5"
    return None


def choose(minimum, need_fts5=False, explicit=None, existing=(), candidates=None, probe_fn=None):
    """(launcher, info, tried). explicit (from --python) is used alone; otherwise the first usable of
    existing + candidates. tried = [(launcher, reason)] of the ones refused. Raises LauncherError when none works."""
    probe_fn = probe_fn or probe
    order = [normalize(explicit)] if explicit else []
    for c in ([] if explicit else list(existing) + list(candidates or CANDIDATES)):
        if c and c not in order and not _UNSAFE.search(c):
            order.append(c)
    tried = []
    for c in order:
        info = probe_fn(c)
        why = reason(info, minimum, need_fts5)
        if why is None:
            return c, info, tried
        tried.append((c, why))
    raise LauncherError("; ".join("`%s` %s" % t for t in tried) or "không có lệnh nào để thử")


def has_modules(command, names, timeout=30):
    """True when the launcher can find every named package (site-packages on, as the engine runs it: -E -s)."""
    parts = tokens(command)
    exe = parts and (shutil.which(parts[0]) or (parts[0] if os.path.isfile(parts[0]) else None))
    if not exe:
        return False
    code = "import importlib.util as u,sys;sys.exit(0 if all(u.find_spec(n) for n in sys.argv[1:]) else 1)"
    try:
        return subprocess.run([exe] + parts[1:] + ["-E", "-s", "-c", code] + list(names), capture_output=True,
                              timeout=timeout, stdin=subprocess.DEVNULL).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def used_in(settings, scripts):
    """Launchers of the hook commands in a settings dict that name one of scripts, in order, no repeats."""
    found = []
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    for groups in (hooks.values() if isinstance(hooks, dict) else ()):
        for g in groups if isinstance(groups, list) else ():
            for h in (g.get("hooks") if isinstance(g, dict) else None) or ():
                cmd = str(h.get("command", "")) if isinstance(h, dict) else ""
                if any(s in cmd for s in scripts):
                    name = launcher_of(cmd)
                    if name and name not in found:
                        found.append(name)
    return found
