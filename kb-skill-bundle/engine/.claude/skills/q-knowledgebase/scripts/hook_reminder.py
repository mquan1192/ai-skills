"""Optional reminder only: no file reads, subprocesses, networking or blocking."""
import sys

if __name__ == "__main__":
    # UserPromptSubmit exit-0 stdout becomes context. No stdin content is echoed.
    sys.stdout.write("Q-KnowledgeBase: for repository technical work, check KB status, run a scoped search, read exact current evidence, and compare current code. Do not index for unrelated questions.\n")
