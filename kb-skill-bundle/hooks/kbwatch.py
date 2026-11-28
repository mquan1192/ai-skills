# kbwatch.py - SessionStart hook: one Vietnamese status line about the KB.
#   📚 KB v<version> · chỉ mục <mới | cũ (N file đổi) | chưa kiểm> · N nguồn mới chưa nạp (<p/sub>, …) → đã tạo REQ-… · M request đang mở
# New raw sources (files under <projects_root>/<p>/<sub>/docs/, trees under src/) not listed in the KB's _sources.md
# -> one sync-sources request per <p>/<sub> (mode "on" only; no duplicate: the request holds a hash of the path list,
#    and a path already named in an open / in-progress request of any author is not requested again (v2.0.3, K4)).
# Request files: kb.config.json "request_prefixes" (default ["REQ-", "KB-REQ-"]); every prefix is read, the first one is written (K2).
# Silent when the project has no .qkb/ or no kb.config.json. Never reads KB page content (only _sources.md path cells).
# Usage: python -I -S kbwatch.py [--root <dir>]   (stdin: hook JSON, ignored except for being read)
import os
import sys

sys.dont_write_bytecode = True   # -I -S hooks: never leave __pycache__ next to the hook
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hashlib  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402

import kbcommon as kc  # noqa: E402

PATH_CELL = re.compile(r'`([^`]+)`')
DEFAULT_PREFIXES = ['REQ-', 'KB-REQ-']
REQUEST_READ_MAX = 200000          # bytes read from one request file (path mentions may sit below a long Content list)


def request_prefixes(cfg):
    """File-name prefixes of request files: all are read; the first one is used for new files (K2)."""
    value = (cfg or {}).get('request_prefixes')
    if isinstance(value, list):
        out = [v.strip() for v in value if isinstance(v, str) and re.match(r'^[A-Za-z0-9_-]+$', v.strip())]
        if out:
            return out
    return list(DEFAULT_PREFIXES)


def unit_mention(value, projects):
    """True when a path named in a request is at the depth of a source unit (K4, ):
    <projects>/<p>/<sub>/docs/<file…> or <projects>/<p>/<sub>/src/<tree>[/…]. Project, part, docs/ and src/ folders are
    never a source unit, so a request that only names them as context covers nothing."""
    k = len(projects.strip('/').split('/'))
    segs = value.split('/')
    return len(segs) >= k + 4 and segs[k + 2] in ('docs', 'src')


def covering(path, mentioned):
    """Request names that already cover a new source unit: a docs file named itself, or a src tree named itself or by a
    path inside it (K4). mentioned = {unit path: {request names}}."""
    names = set()
    for x, reqs in mentioned.items():
        if path == x or x.startswith(path + '/'):
            names |= reqs
    return names


def covered_text(names):
    """'đã có yêu cầu <first>' (+ ' + n yêu cầu khác') ."""
    names = sorted(names)
    if not names:
        return 'đã có yêu cầu'
    return 'đã có yêu cầu %s%s' % (names[0], ' + %d yêu cầu khác' % (len(names) - 1) if len(names) > 1 else '')


def kb_version(root, cfg):
    try:
        with open(os.path.join(root, *(cfg.get('version_file') or 'kb/VERSION').split('/')), encoding='utf-8') as f:
            return f.readline().strip() or '?'
    except Exception:
        return '?'


def listed_sources(path, base):
    """Paths in the first column of _sources.md, as repository-relative prefixes."""
    out = set()
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                if not line.startswith('|') or line.startswith('|---') or line.startswith('| ---'):
                    continue
                cell = line.strip().strip('|').split('|')[0].strip()
                m = PATH_CELL.search(cell)
                value = (m.group(1) if m else cell).replace('\\', '/').strip().strip('/')
                if not value or value.lower() in ('path', 'source', 'file'):
                    continue
                out.add(value if value.startswith(base.split('/')[0] + '/') else base + '/' + value)
    except Exception:
        pass
    return out


def new_sources(root, cfg, hcfg, deadline):
    """{<p>/<sub>: [new paths]} for every project part that has raw sources."""
    projects = (cfg.get('projects_root') or 'projects').strip('/')
    kb_root = (cfg.get('kb_root') or 'kb').strip('/')
    result, seen = {}, 0
    top = os.path.join(root, projects)
    if not os.path.isdir(top):
        return result
    packs = os.path.join(root, '.qkb', 'packs')
    imported = {n.split('__')[0] for n in os.listdir(packs)} if os.path.isdir(packs) else set()
    for project in sorted(os.listdir(top)):
        pdir = os.path.join(top, project)
        if not os.path.isdir(pdir) or project in imported:   # imported from a data pack: no source scan here
            continue
        for sub in sorted(os.listdir(pdir)):
            if time.monotonic() > deadline or seen > hcfg['scan_limit']:
                return result
            sdir = os.path.join(pdir, sub)
            if not os.path.isdir(sdir):
                continue
            base = '%s/%s/%s' % (projects, project, sub)
            listed = listed_sources(os.path.join(root, kb_root, project, sub, '_sources.md'), base)
            found = []
            docs = os.path.join(sdir, 'docs')
            for folder, dirs, names in os.walk(docs):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
                for name in sorted(names):
                    seen += 1
                    found.append(kc.rel(root, os.path.join(folder, name)))
            src = os.path.join(sdir, 'src')
            if os.path.isdir(src):
                for tree in sorted(os.listdir(src)):
                    if os.path.isdir(os.path.join(src, tree)) and not tree.startswith('.'):
                        seen += 1
                        found.append(kc.rel(root, os.path.join(src, tree)))
            # known = listed itself, inside a listed folder, or a folder that holds listed entries (tree with modules)
            new = [p for p in found if p and not any(p == x or p.startswith(x + '/') or x.startswith(p + '/')
                                                     for x in listed)]
            if new:
                result['%s/%s' % (project, sub)] = new
    return result


def open_requests(folder, prefixes=None, projects='projects'):
    """(count of open / in-progress requests, {source-list hash: request name},
    {source-unit path named in an open / in-progress request: {request names}}). Only files <prefix>*.md are read (K2)."""
    count, hashes, mentioned = 0, {}, {}
    if not os.path.isdir(folder):
        return count, hashes, mentioned
    prefixes = prefixes or DEFAULT_PREFIXES
    root_word = projects.strip('/') + '/'
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.md') or not any(name.startswith(p) for p in prefixes):
            continue
        try:
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                text = f.read(REQUEST_READ_MAX)
        except Exception:
            continue
        req = name[:-3]
        head = text[:4000]
        for h in re.findall(r'^- Source-list hash:\s*([0-9a-f]{12,64})', head, re.M):
            hashes.setdefault(h, req)
        m = re.search(r'^- Status:\s*([\w-]+)', head, re.M)
        if m and m.group(1) in ('open', 'in-progress'):
            count += 1
            # K4: source units this open request already names (any author, e.g. a manual source-intake request);
            # project / part / docs / src folders named as context do not count 
            for cell in PATH_CELL.findall(text):
                value = cell.replace('\\', '/').strip().strip('/')
                if value.startswith(root_word) and unit_mention(value, projects):
                    mentioned.setdefault(value, set()).add(req)
    return count, hashes, mentioned


def write_request(folder, part, paths, digest, prefix='REQ-'):
    stamp = time.strftime('%Y%m%d-%H%M', time.localtime())
    req_id = '%s%s-sync-%s' % (prefix, stamp, re.sub(r'[^A-Za-z0-9-]+', '-', part).strip('-'))
    lines = ['# ' + req_id, '- Status: open', '- From: kbwatch hook (SessionStart) · ' + time.strftime('%Y-%m-%d %H:%M'),
             '- Target: ' + part, '- Type: sync-sources', '- Issue IDs: —', '- Source-list hash: ' + digest,
             '- Content: new raw sources not listed in _sources.md:']
    lines += ['  - [DOC] `%s`' % p for p in paths[:200]]
    if len(paths) > 200:
        lines.append('  - … %d more' % (len(paths) - 200))
    lines += ['- Policy check: paths only (no content read)', '- Result:', '']
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, req_id + '.md')
    if os.path.exists(path):
        return None
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    return req_id


def main(argv):
    t0 = time.monotonic()
    root = kc.project_root(argv)
    kc.read_stdin()
    if not kc.has_index(root):
        return 0
    cfg = kc.load_config(root)
    if cfg is None:
        return 0
    hcfg = kc.hooks_cfg(cfg)
    if hcfg['mode'] == 'off':
        return 0
    version = kb_version(root, cfg)
    if hcfg['index_check'] == 'status':
        status = kc.run_qkb(root, cfg, ['status', '--quick'], float(hcfg['qkb_timeout_s']))
    else:   # `status --quick` can take seconds on a large tree; the meta check needs no engine start
        fresh = kc.index_freshness(root, cfg)
        status = None if fresh is None else {'state': fresh[0], 'changed': [''] * fresh[1], 'deleted': []}
    if not status:
        index = 'chỉ mục chưa kiểm'
        codes = ['INDEX_UNCHECKED']
    elif status.get('state') == 'CURRENT':
        index = 'chỉ mục mới'
        codes = ['INDEX_CURRENT']
    else:
        n = len(status.get('changed') or []) + len(status.get('deleted') or [])
        index = 'chỉ mục cũ (%d file đổi)' % n
        codes = ['INDEX_STALE']
    requests = os.path.join(root, *(cfg.get('requests_folder') or '00_KB_Manager/requests').split('/'))
    prefixes = request_prefixes(cfg)
    count, hashes, mentioned = open_requests(requests, prefixes, cfg.get('projects_root') or 'projects')
    news = new_sources(root, cfg, hcfg, t0 + 1.6)
    parts = ['📚 KB v' + version, index]
    if news:
        total = sum(len(v) for v in news.values())
        made = []
        for part, paths in sorted(news.items()):
            names, kept = set(), []
            for p in paths:                                   # K4: drop units already named in an open request
                found = covering(p, mentioned)
                if found:
                    names |= found
                else:
                    kept.append(p)
            paths = kept
            if not paths:
                made.append(covered_text(names))
                continue
            digest = hashlib.sha256('\n'.join(sorted(paths)).encode('utf-8')).hexdigest()[:16]
            if digest in hashes:
                made.append(covered_text({hashes[digest]}))
                continue
            if hcfg['mode'] == 'on':
                req = write_request(requests, part, paths, digest, prefixes[0])
                if req:
                    made.append(req)
                    count += 1
            else:
                made.append('sẽ tạo yêu cầu')
        names = ', '.join(sorted(news)[:3]) + (', …' if len(news) > 3 else '')
        parts.append('%d nguồn mới chưa nạp (%s) → %s' % (total, names, ', '.join(sorted(set(made)))))
        codes.append('NEW_SOURCES')
    if count:
        parts.append('%d request đang mở' % count)
    line = ' · '.join(parts)
    model = ('[KB] ' + line + '. Project questions: look up the KB first (/q-kb-search or qkb query); '
             'new facts go through /q-kb-request.')
    kc.emit(root, hcfg, 'SessionStart', 'kbwatch', line, model, codes)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
