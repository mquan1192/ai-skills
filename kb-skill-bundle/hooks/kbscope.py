# kbscope.py - remember the KB search scope on this machine (.qkb/local/scope.json; not shared, not part of the KB).
# /q-kb-search reads the saved scope. Messages in Vietnamese.
# Usage (repository root):
#   python -I -S .claude/hooks/kbscope.py set <phạm vi | all>
#   python -I -S .claude/hooks/kbscope.py get
#   python -I -S .claude/hooks/kbscope.py clear
#   [--root <dir>]
import os
import sys

sys.dont_write_bytecode = True   # -I -S hooks: never leave __pycache__ next to the hook
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json  # noqa: E402
import time  # noqa: E402

import kbcommon as kc  # noqa: E402

USAGE = 'Cách dùng: kbscope.py set <phạm vi | all> | get | clear'


def scope_file(root):
    return os.path.join(root, '.qkb', 'local', 'scope.json')


def valid_scopes(root, cfg):
    names = set(kc.project_scopes(cfg)) | {'all'}
    kb_root = os.path.join(root, (cfg or {}).get('kb_root') or 'kb')
    if os.path.isdir(kb_root):           # a project folder or <project>/<sub> below kb_root is also a scope
        for p in os.listdir(kb_root):
            if os.path.isdir(os.path.join(kb_root, p)):
                names.add(p)
                for s in os.listdir(os.path.join(kb_root, p)):
                    if os.path.isdir(os.path.join(kb_root, p, s)):
                        names.add(p + '/' + s)
    return sorted(names)


def main(argv):
    args = [a for i, a in enumerate(argv) if a != '--root' and (i == 0 or argv[i - 1] != '--root')]
    if not args or args[0] not in ('set', 'get', 'clear') or (args[0] == 'set' and len(args) != 2):
        print(USAGE, file=sys.stderr)
        return 2
    root = kc.project_root(argv)
    if not kc.has_index(root):
        print('LỖI: chưa có chỉ mục KB (.qkb/) trong thư mục này.', file=sys.stderr)
        return 2
    cfg = kc.load_config(root) or {}
    path = scope_file(root)
    if args[0] == 'get':
        saved = kc.saved_scope(root)
        default = cfg.get('default_scope') or 'all'
        print('Phạm vi KB: %s (%s)' % ((saved, 'đã lưu') if saved else (default, 'mặc định')))
        return 0
    if args[0] == 'clear':
        if os.path.isfile(path):
            os.remove(path)
        print('Đã bỏ phạm vi đã lưu. Dùng phạm vi mặc định: %s.' % (cfg.get('default_scope') or 'all'))
        return 0
    scope = args[1].strip().strip('/')
    allowed = valid_scopes(root, cfg)
    if scope not in allowed:
        print('LỖI: không có phạm vi "%s". Chọn một trong: %s.' % (scope, ', '.join(allowed)), file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'scope': scope, 'set_at': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}, f, ensure_ascii=False)
        f.write('\n')
    print('Đã lưu phạm vi KB: %s (máy này). Đổi: kbscope.py set <phạm vi | all>.' % scope)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
