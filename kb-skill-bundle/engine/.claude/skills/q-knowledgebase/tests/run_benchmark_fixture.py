"""Measure a synthetic labeled corpus in a temporary repository only."""
import argparse
import json
import platform
import sys
import tempfile
from pathlib import Path

from support import DEFAULTS, Store, populate
import engine
from benchmark import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional path to save metrics (never corpus/index)")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="qkb-benchmark-") as temp:
        root = Path(temp)/"fixture repository"
        populate(root)
        with Store(root,dict(DEFAULTS),create=True) as store:
            engine.update(store)
            with (root/"docs/legacy.md").open("a",encoding="utf-8") as handle:
                handle.write("Historical note verified in this synthetic fixture.\n")
            update = engine.update(store)
            report = run(store,"questions.json")
            report.update({"dataset_kind":"synthetic fixture, not user project", "incremental_changed_documents":update["modified"],
                           "environment":{"python":sys.version.split()[0],"platform":platform.platform()}})
    rendered = json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(rendered,encoding="utf-8")
    print(rendered,end="")


if __name__ == "__main__": main()
