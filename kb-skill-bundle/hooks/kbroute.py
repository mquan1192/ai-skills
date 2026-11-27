# kbroute.py - UserPromptSubmit hook: deterministic "is this a project question?" check (no model call).
# Match -> one line for the MODEL only (no user line; user notes only at session start and on problems):
#   [KB] tra KB trước · phạm vi = <scope> · cách tìm = /q-kb-search (qkb query "<câu hỏi>" --project <p>)
# Signals (from kb.config.json, never hard-coded): project scope names and their path segments, issue_id_patterns,
# hooks.route_keywords, hooks.route_id_patterns. Prompts starting with "/" (commands) and short prompts stay silent.
# The prompt text is read in memory only; it is never stored or logged (the observe log keeps rule codes only).
# Usage: python -I -S kbroute.py [--root <dir>]
import os
import sys

sys.dont_write_bytecode = True   # -I -S hooks: never leave __pycache__ next to the hook
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re  # noqa: E402

import kbcommon as kc  # noqa: E402


def scope_words(cfg):
    """{scope: set of lower-case words naming it} from project_scopes keys and their kb path segments."""
    kb_root = (cfg.get('kb_root') or 'kb').strip('/')
    out = {}
    for scope, prefixes in kc.project_scopes(cfg).items():
        words = {w for w in re.split(r'[/\\]', scope.lower()) if len(w) >= 3}
        for prefix in prefixes:
            segs = [s for s in prefix.lower().strip('/').split('/') if s and s != kb_root.lower()]
            words.update(s for s in segs if len(s) >= 3 and s not in ('shared', 'rules', 'common'))
        out[scope] = words
    return out


def match(prompt, cfg, hcfg):
    """(codes, scope or None) for a project question; ([], None) otherwise."""
    text = prompt.lower()
    codes, best, best_hits = [], None, 0
    for scope, words in scope_words(cfg).items():
        hits = sum(1 for w in words if re.search(r'(?<![\w-])' + re.escape(w) + r'(?![\w])', text))
        if hits > best_hits:
            best, best_hits = scope, hits
    if best:
        codes.append('SCOPE_NAME')
    if any(p.search(prompt) for p in kc.compile_patterns(cfg.get('issue_id_patterns'))):
        codes.append('ISSUE_ID')
    if any(p.search(prompt) for p in kc.compile_patterns(hcfg['route_id_patterns'])):
        codes.append('DOC_ID')
    words = [w.lower() for w in hcfg['route_keywords'] if isinstance(w, str) and w.strip()]
    if any(re.search(r'(?<![\w-])' + re.escape(w) + r'(?![\w])', text) for w in words):
        codes.append('KEYWORD')
    return codes, best


def main(argv):
    root = kc.project_root(argv)
    data = kc.read_stdin()
    if not kc.has_index(root):
        return 0
    cfg = kc.load_config(root)
    if cfg is None:
        return 0
    hcfg = kc.hooks_cfg(cfg)
    if hcfg['mode'] == 'off':
        return 0
    prompt = data.get('prompt') if isinstance(data.get('prompt'), str) else ''
    stripped = prompt.strip()
    if len(stripped) < int(hcfg['route_min_chars']) or stripped.startswith('/'):
        return 0
    codes, guessed = match(stripped, cfg, hcfg)
    if not codes:
        return 0
    saved = kc.saved_scope(root)
    scope = saved or guessed or cfg.get('default_scope') or 'all'
    origin = 'đã lưu' if saved else ('đoán' if guessed else 'mặc định')
    project = '' if scope == 'all' else ' --project ' + scope.split('/')[0]
    line = ('[KB] tra KB trước · phạm vi = %s (%s) · cách tìm = /q-kb-search hoặc qkb query "<câu hỏi>"%s'
            % (scope, origin, project))
    kc.emit(root, hcfg, 'UserPromptSubmit', 'kbroute', None, line, codes)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
