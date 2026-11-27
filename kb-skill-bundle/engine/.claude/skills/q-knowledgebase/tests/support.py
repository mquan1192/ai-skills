from pathlib import Path
import json
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
# Names that must not appear in the engine (project / customer names of the installing team). The list is not
# shipped: set the environment variable QKB_FORBIDDEN_NAMES="name1,name2"; checks that need it skip when unset.
FORBIDDEN_NAMES = [n.strip().casefold() for n in __import__("os").environ.get("QKB_FORBIDDEN_NAMES", "").split(",") if n.strip()]
sys.path.insert(0, str(SKILL / "scripts"))
from core import DEFAULTS, Store, digest, ident
import engine

DOCUMENTS = {
    "docs/auth.md": '\ufeff---\ntitle: Authentication\nstatus: active\nauthority: approved\nowner: Product\nqkb_entities: [{"type":"SERVICE","name":"UserService"}]\n---\n# Authentication\nUserService owns authentication and user management.\n## Audit workflow\nDeleting a user requires an audit event. Xóa người dùng phải ghi lịch sử.\n認証サービスは監査ログを保存します。\n[Audit](audit.md#events) and `src/users.py`.\n| Action | Rule |\n| --- | --- |\n| Delete | Audit required |\n```python\n# Not a document heading\n## Also not a heading\nprint("untrusted; never execute")\n```\n### Constraints\nPreserve audit history.\n',
    "docs/audit.md": '---\ntitle: AuditLogging\nqkb_entities: [{"type":"SERVICE","name":"AuditLogging"}]\n---\n# AuditLogging\nAudit service records data changes.\n## Events\nAudit events persist in the audit_events database table.\nDo not discard deletion history.\n',
    "docs/legacy.md": '# Old policy\nLegacy audit policy is retained as history.\n',
    "docs/decision.md": '---\nstatus: active\nsupersedes: legacy.md\n---\n# ADR-002\nADR-002 supersedes the old audit policy.\n',
    "docs/second/auth.md": '# Authentication\nSecondary domain authentication with a separate identity provider.\n',
    "docs/api.md": '# User API\n## Delete endpoint\nDELETE /users writes to the audit_events database table via UserService.\nSee [workflow](auth.md#audit-workflow).\n',
    "docs/requirements.md": '# REQ-USER-01\n## Implementation\nUser deletion requires audit; implementation source is `../src/users.py`.\nSee [Authentication](auth.md).\n',
    "docs/conflict.md": '# Known conflict\n## Audit mismatch\nDocumentation requires audit on deletion. Fixture implementation currently returns without writing an event.\nVerify the implementation before changing approved requirements.\n',
    "src/audit.py": 'def record(event):\n    return event\n',
    "src/users.py": 'from audit import record\n\nclass UserService:\n    def delete_user(self, user_id):\n        return user_id\n',
    "src/client.ts": 'export function login() { return "ok"; }\n',
}

QUESTIONS = [
    {"question": "Module nào quản lý đăng nhập?", "query": "Authentication UserService", "relevant": [{"path":"docs/auth.md","heading":"Authentication"}]},
    {"question": "Rule nào điều khiển xóa user?", "query": "Audit workflow", "relevant": [{"path":"docs/auth.md","heading":"Audit workflow"}]},
    {"question": "API nào liên quan DB audit?", "query": "Delete endpoint audit_events", "relevant": [{"path":"docs/api.md","heading":"Delete endpoint"}]},
    {"question": "Đọc gì trước khi impact UserService?", "query": "UserService", "relevant": [{"path":"docs/auth.md","heading":"Authentication"},{"path":"docs/api.md","heading":"Delete endpoint"}]},
    {"question": "Decision mới thay thế cái cũ?", "query": "ADR-002 supersedes", "relevant": [{"path":"docs/decision.md","heading":"ADR-002"}]},
    {"question": "Source nào implement requirement?", "query": "REQ-USER-01 Implementation", "relevant": [{"path":"docs/requirements.md","heading":"Implementation"}]},
    {"question": "Có conflict tài liệu và code?", "query": "Audit mismatch", "relevant": [{"path":"docs/conflict.md","heading":"Audit mismatch"}]},
    {"question": "Đọc constraint nào trước khi sửa?", "query": "Constraints audit history", "relevant": [{"path":"docs/auth.md","heading":"Constraints"}]},
    {"question": "監査ログ", "query": "監査ログ", "relevant": [{"path":"docs/auth.md","heading":"Audit workflow"}]},
]


def populate(root):
    for path, content in DOCUMENTS.items():
        dest = root/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content.encode("utf-8"))
    (root/".qkb").mkdir(exist_ok=True)
    (root/".qkb/config.json").write_text(json.dumps(DEFAULTS), encoding="utf-8")
    (root/"questions.json").write_text(json.dumps(QUESTIONS, ensure_ascii=False), encoding="utf-8")


def package_fixture(dest):
    """Build the package layout in dest from package files only.

    The skill may run from a package folder (MANIFEST.json beside it) or from an installed repository,
    where SKILL.parents[2] is the whole repository. Copying that folder would copy the repository into
    the temp folder, so only these are taken: the skill folder itself, the rule file, and the root files
    a Q-KnowledgeBase MANIFEST.json lists. Returns True when the package root files (installer) exist."""
    import shutil
    dest = Path(dest)
    shutil.copytree(SKILL, dest / ".claude/skills/q-knowledgebase",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    package = SKILL.parents[2]
    rules = package / ".claude/rules/q-knowledgebase.md"
    if rules.is_file():
        (dest / ".claude/rules").mkdir(parents=True, exist_ok=True)
        shutil.copy2(rules, dest / ".claude/rules/q-knowledgebase.md")
    manifest = package / "MANIFEST.json"
    if not manifest.is_file():
        return False
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("product") != "Q-KnowledgeBase":
        return False
    for name in data.get("files", {}):
        if name.startswith(".claude/skills/") or name == ".claude/rules/q-knowledgebase.md":
            continue
        source = package / name
        if source.is_file():
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest / name)
    return (dest / "Q-KnowledgeBase-install.py").is_file()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qkb-test-")
        self.root = Path(self.temp.name)
        populate(self.root)
        self.store = Store(self.root, dict(DEFAULTS), create=True)
        engine.update(self.store)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def write(self, path, content):
        dest = self.root/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        self.store.hash_cache.clear()

    def proposal(self, relation="REQUIRES", reverse=False):
        source = self.store.rows("SELECT * FROM nodes WHERE label='UserService' AND type='SERVICE'")[0]
        target = self.store.rows("SELECT * FROM nodes WHERE label='AuditLogging' AND type='SERVICE'")[0]
        if reverse: source, target = target, source
        evidence = []
        for path, heading in (("docs/auth.md", "Audit workflow"), ("docs/audit.md", "Events")):
            sec = self.store.rows("SELECT * FROM sections WHERE path=? AND heading=?", (path, heading))[0]
            text, hash_, _ = self.store.scope.read(path)
            start = sec["start"]+1
            evidence.append({"path": path, "section_id": sec["section_id"], "start": start, "end": start,
                             "quote": text.splitlines()[start-1], "hash": hash_})
        return {"source": source["id"], "target": target["id"], "relation": relation,
                "rationale": "User deletion requires audit logging based on these two sections.", "evidence": evidence}

    def import_proposal(self, data=None):
        import semantic
        self.write(".qkb/proposals/input.json", json.dumps(data or self.proposal(), ensure_ascii=False))
        return semantic.import_proposals(self.store, ".qkb/proposals/input.json")["ids"][0]
