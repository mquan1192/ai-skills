# kbcommon.py - shared helpers of the KB hooks (kbwatch, kbroute, kbguard) and kbscope.
# Python 3 stdlib only, offline, no model calls. Fail-open: callers catch everything and exit 0.
# Writes only: the hook log (<log_dir or observe_log_dir>/<yyyy-MM-dd>.jsonl; modes observe and on), sync-sources request files (kbwatch, mode "on"),
# .qkb/local/scope.json (kbscope). Never logs prompt text, tool input / output or KB content: log lines hold the hook
# name, event, rule codes and the would-be note (built from counts, versions and scope names only).
import datetime
import json
import os
import re
import subprocess
import sys
import time

_T0 = time.perf_counter()                    # hook process start (this module is imported first): latency in the log
MODES = ('observe', 'on', 'off')
DEFAULT_HOOKS = {
    'mode': 'observe',                       # observe (log only) | on (show notes) | off (silent, no log)
    'observe_log_dir': '.qkb/local/observe',    # per machine; a project may set its own (e.g. a process-log folder)
    'log': True,                             # log in modes observe and on (v2.0.2; off = hooks do nothing, no log)
    'log_dir': '',                           # log folder; empty = observe_log_dir (older configs keep working)
    'qkb_timeout_s': 1.2,                    # budget for `qkb status --quick` (only when index_check = "status")
    'index_check': 'meta',                   # meta: index time vs KB file times (cheap, default) | status: run qkb
    'stop_notice': 'off',                    # Stop reminder: off (log only, default; owner choice) | once (once per session)
    'scan_limit': 3000,                      # max source entries kbwatch looks at per session start
    'route_keywords': [],                    # extra words that mark a project question (kbroute)
    'route_id_patterns': [],                 # extra ID regexes (document IDs, file-name forms) for kbroute
    'route_min_chars': 8,                    # shorter prompts are ignored
    'task_output_pattern': r'(^|/)out/',     # kbguard Stop: a write whose path matches this = task output
}
CONFIG_NAMES = ('kb.config.json', '00_KB_Manager/kb.config.json', '00_UpdateDocs/kb.config.json')


def project_root(argv=None):
    """--root <dir> (tests) > CLAUDE_PROJECT_DIR > current directory."""
    argv = argv if argv is not None else sys.argv[1:]
    if '--root' in argv:
        i = argv.index('--root')
        if i + 1 < len(argv):
            return os.path.abspath(argv[i + 1])
    return os.path.abspath(os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd())


def read_stdin():
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', 'replace').strip('﻿ \r\n\t')
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def config_names(root):
    """kb.config.json at the root, in the manager folder named by the install record (.qkb/install/installed.json),
    then the default manager folder 00_KB_Manager/ (00_UpdateDocs/ = default name up to 2.0.5)."""
    names = [CONFIG_NAMES[0]]
    try:
        with open(os.path.join(root, '.qkb', 'install', 'installed.json'), encoding='utf-8') as f:
            folder = json.load(f).get('options', {}).get('manager_folder')
        if isinstance(folder, str) and folder and '..' not in folder.replace('\\', '/').split('/'):
            names.append(folder.replace('\\', '/').strip('/') + '/kb.config.json')
    except Exception:
        pass
    names += [n for n in CONFIG_NAMES[1:] if n not in names]
    return names


def load_config(root):
    """First readable kb.config.json of config_names(root). None when absent or unreadable."""
    for name in config_names(root):
        path = os.path.join(root, *name.split('/'))
        if os.path.isfile(path):
            try:
                with open(path, encoding='utf-8') as f:
                    cfg = json.load(f)
                return cfg if isinstance(cfg, dict) else None
            except Exception:
                return None
    return None


def hooks_cfg(cfg):
    out = dict(DEFAULT_HOOKS)
    user = (cfg or {}).get('hooks')
    if isinstance(user, dict):
        out.update({k: v for k, v in user.items() if k in DEFAULT_HOOKS})
    if out['mode'] not in MODES:
        out['mode'] = 'observe'
    return out


def has_index(root):
    return os.path.isdir(os.path.join(root, '.qkb'))


def rel(root, path):
    """Repository-relative POSIX path, or None when outside the root."""
    if not path:
        return None
    p = path if os.path.isabs(path) else os.path.join(root, path)
    try:
        r = os.path.relpath(os.path.normpath(p), root).replace('\\', '/')
    except ValueError:
        return None
    return None if r == '..' or r.startswith('../') else ('' if r == '.' else r)


def under(path_rel, prefix):
    prefix = prefix.replace('\\', '/').strip('/')
    return path_rel is not None and prefix != '' and (path_rel == prefix or path_rel.startswith(prefix + '/'))


def saved_scope(root):
    try:
        with open(os.path.join(root, '.qkb', 'local', 'scope.json'), encoding='utf-8') as f:
            value = json.load(f).get('scope')
        return value if isinstance(value, str) and value else None
    except Exception:
        return None


def qkb_command(cfg):
    cmd = (cfg or {}).get('qkb_command') or 'python -E -s -B .claude/skills/q-knowledgebase/scripts/qkb.py'
    parts = cmd.split()
    script = next((p for p in parts if p.endswith('.py')), None)
    return script


def run_qkb(root, cfg, args, timeout_s):
    """Run the index CLI with the current interpreter; returns parsed JSON or None (missing, error, timeout)."""
    script = qkb_command(cfg)
    if not script:
        return None
    path = script if os.path.isabs(script) else os.path.join(root, script)
    if not os.path.isfile(path):
        return None
    try:
        flags = 0x08000000 if os.name == 'nt' else 0   # CREATE_NO_WINDOW
        r = subprocess.run([sys.executable, '-E', '-s', '-B', path] + args + ['--format', 'json'], cwd=root,
                           capture_output=True, timeout=timeout_s, creationflags=flags)
        if r.returncode not in (0, 1):
            return None
        return json.loads(r.stdout.decode('utf-8', 'replace'))
    except Exception:
        return None


def emit(root, hcfg, event, hook, user_line=None, model_line=None, codes=()):
    """observe: log what would be shown; on: log it too (v2.0.2), then print the hook JSON; off: nothing."""
    if hcfg['mode'] == 'off' or not (user_line or model_line):
        return
    if hcfg['mode'] == 'observe':
        log(root, hcfg, {'hook': hook, 'event': event, 'codes': list(codes), 'would_show': user_line or '',
                         'would_tell_model': bool(model_line)})
        return
    log(root, hcfg, {'hook': hook, 'event': event, 'codes': list(codes), 'shown': user_line or '',
                     'told_model': bool(model_line)})
    payload = {}
    if user_line:
        payload['systemMessage'] = user_line
    if model_line and event in ('SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse'):
        payload['hookSpecificOutput'] = {'hookEventName': event, 'additionalContext': model_line}
    if payload:
        sys.stdout.write(json.dumps(payload, ensure_ascii=True))


def log(root, hcfg, entry):
    """One JSON line: time, mode, hook, event, codes, the note line (built from counts / versions / scope names only),
    model hint yes-no, latency ms. Never prompt text, tool input / output or KB content."""
    if hcfg.get('log', True) is False:
        return
    try:
        folder = os.path.join(root, *str(hcfg.get('log_dir') or hcfg['observe_log_dir']).replace('\\', '/').split('/'))
        if rel(root, folder) is None:
            return
        os.makedirs(folder, exist_ok=True)
        line = dict({'at': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime()), 'mode': hcfg.get('mode')}, **entry)
        line['ms'] = int((time.perf_counter() - _T0) * 1000)
        with open(os.path.join(folder, datetime.date.today().isoformat() + '.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(line, ensure_ascii=False) + '\n')
    except Exception:
        pass


def index_freshness(root, cfg, budget_s=0.8):
    """Cheap index check without starting the engine: (state, files newer than the last index run) or None.
    state CURRENT | STALE. Reads meta 'last_indexed' of .qkb/cache/index.sqlite3 read-only, compares KB file times."""
    import sqlite3
    db = os.path.join(root, '.qkb', 'cache', 'index.sqlite3')
    if not os.path.isfile(db):
        return None
    try:
        import pathlib
        con = sqlite3.connect(pathlib.Path(db).resolve().as_uri() + '?mode=ro', uri=True, timeout=0.5)
        try:
            row = con.execute("SELECT value FROM meta WHERE key='last_indexed'").fetchone()
        finally:
            con.close()
        stamp = datetime.datetime.fromisoformat(row[0]).timestamp() if row and row[0] else None
    except Exception:
        return None
    if stamp is None:
        return None
    kb_root = os.path.join(root, (cfg or {}).get('kb_root') or 'kb')
    newer, deadline = 0, time.monotonic() + budget_s
    for folder, dirs, names in os.walk(kb_root):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for name in names:
            try:
                if os.path.getmtime(os.path.join(folder, name)) > stamp + 1:
                    newer += 1
            except OSError:
                continue
        if time.monotonic() > deadline:
            return None
    return ('STALE' if newer else 'CURRENT'), newer


def local_state(root, name, value=None):
    """Per-machine state file .qkb/local/<name>.json: read when value is None, else write (fail-open)."""
    path = os.path.join(root, '.qkb', 'local', name + '.json')
    if value is None:
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(value, f)
    except Exception:
        pass
    return value


def project_scopes(cfg):
    scopes = (cfg or {}).get('project_scopes') or {}
    return {k: v for k, v in scopes.items() if not k.startswith('_') and isinstance(v, list)}


def compile_patterns(patterns):
    out = []
    for p in patterns or []:
        try:
            out.append(re.compile(r'(?<![\w-])' + p + r'(?![\w])'))
        except (re.error, TypeError):
            continue
    return out
