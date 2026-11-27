"""Python parser (AST, coverage FULL for definitions and imports; calls are not extracted)."""
from __future__ import annotations

import ast
from pathlib import Path


def parse(path, text, options):
    result = {"language": "python", "coverage": "FULL", "parser": "python-ast", "symbols": [], "references": [],
              "meta": {"parse_status": "CURRENT", "calls": "not extracted"}}
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError:
        result.update(coverage="FILE_ONLY", meta={"parse_status": "BROKEN"})
        return result
    lines = text.splitlines()

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                label = ".".join(prefix + [child.name])
                result["symbols"].append({"name": label, "kind": type(child).__name__, "start": child.lineno,
                                          "end": child.end_lineno, "parent": ".".join(prefix) or None})
                walk(child, prefix + [child.name])
            else:
                walk(child, prefix)
    walk(tree, [])
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        modules = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module or ""]
        for module in modules:
            if isinstance(node, ast.ImportFrom) and node.level:
                base = Path(path).parent
                for _ in range(node.level - 1):
                    base = base.parent
                bases = [base / module.replace(".", "/")]
            else:
                bases = [Path(b) / module.replace(".", "/") for b in options["source_paths"]]
            candidates = [t.as_posix() for b in bases for t in (b.with_suffix(".py"), b / "__init__.py")]
            result["references"].append({"kind": "import", "candidates": candidates, "first_only": False,
                                         "start": node.lineno, "end": node.end_lineno, "written": module,
                                         "evidence": "\n".join(lines[node.lineno - 1:node.end_lineno])})
    return result
