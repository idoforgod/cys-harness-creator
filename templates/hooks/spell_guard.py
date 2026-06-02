#!/usr/bin/env python3
"""spell_guard — PostToolUse(Edit|Write) Korean-typo gate for prose docs (.md/.txt).

WHY: completes the auto-correction loop for the language layer. When Claude saves a Korean
doc, this hook scans for a small set of HIGH-CONFIDENCE typos (forms that are almost always
wrong, e.g. 됬→됐, 역활→역할) and, on a hit, returns exit-2 + a stderr suggestion so Claude
self-corrects — same loop as lint_guard, for prose.

A1 boundary: the dictionary is a DETERMINISTIC guardrail of near-unambiguous misspellings.
CONTEXT-dependent spelling (띄어쓰기, 로서/로써, 되/돼 in general) is left to Claude (the
primitive) — it is a judgment call, not a fixed string. Keeping the list conservative is what
makes the gate signal, not noise.

Activation: `.lint-guard` toggle in the project root (shared with lint_guard; gradual rollout).
Scope: `.md`/`.txt` only; vendored/emitted trees are skipped.

Triggered by: PostToolUse with matcher "Edit|Write".
Safety-first: toggle off, non-text/out-of-scope path, or ANY internal error -> exit 0.
"""

import json
import os
import re
import sys

TEXT_EXT = (".md", ".txt")

# A doc that DISCUSSES typos quotes them in code spans/blocks; sample code does the same. Strip
# fenced code blocks (``` … ```) and inline code (`…`) before scanning so the gate flags PROSE
# typos only — not the explanatory quotations or code examples that legitimately contain them.
_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")

# High-confidence Korean typos: each LHS is almost always a misspelling of its RHS, with no
# common correct usage as a substring (e.g. '왠지' is correct, so only '왠만'/'왠일' are listed,
# not bare '왠'). Add only forms that are wrong in virtually every context.
TYPOS = {
    "됬": "됐",
    "역활": "역할",
    "할께": "할게",
    "갈께": "갈게",
    "줄께": "줄게",
    "금새": "금세",
    "오랫만": "오랜만",
    "몇일": "며칠",
    "어떻해": "어떡해",
    "왠만": "웬만",
    "왠일": "웬일",
}

# Mirror lint_guard's scope exclusions (vendored upstream / emitted / contract trees).
SKIP_PARTS = ("/genome/", "/.harness/genome/", "/.claude/hooks/scripts/", "/examples/",
              "/__pycache__/", "/.pytest_cache/", "/_workspace/", "/_measurement/")


def _find_project_dir():
    d = os.environ.get("CLAUDE_PROJECT_DIR")
    if d and os.path.isdir(d):
        return d
    return os.getcwd()


def _out_of_scope(file_path, project_dir=None):
    # anchor the vendored-tree skip to the PROJECT ROOT (not a substring-anywhere match), so a user's own
    # src/examples/ is checked while the factory's top-level examples/ / genome/ are still skipped.
    norm = file_path.replace("\\", "/")
    proj = (project_dir or _find_project_dir()).replace("\\", "/").rstrip("/")
    rel = norm[len(proj) + 1:] if norm.startswith(proj + "/") else norm.lstrip("/")
    return any(rel == p.strip("/") or rel.startswith(p.strip("/") + "/") for p in SKIP_PARTS)


def spell_check(file_path):
    """Return a list of "'<wrong>' → '<right>'" findings for a text file (empty = clean)."""
    if not file_path.endswith(TEXT_EXT) or not os.path.isfile(file_path):
        return []
    try:
        text = open(file_path, encoding="utf-8").read()
    except Exception:
        return []
    text = _INLINE_CODE.sub(" ", _CODE_BLOCK.sub(" ", text))  # exclude quoted/sample code
    return ["'%s' → '%s'" % (wrong, right) for wrong, right in TYPOS.items() if wrong in text]


def run(stdin_text, project_dir=None):
    """Return the hook exit code (0 pass / 2 block) for a PostToolUse payload string."""
    project_dir = project_dir or _find_project_dir()
    if not os.path.exists(os.path.join(project_dir, ".lint-guard")):
        return 0  # toggle off -> fast no-op
    try:
        payload = json.loads(stdin_text)
        file_path = (payload.get("tool_input") or {}).get("file_path", "")
    except Exception:
        return 0
    if not file_path or not file_path.endswith(TEXT_EXT) or _out_of_scope(file_path, project_dir):
        return 0
    typos = spell_check(file_path)
    if typos:
        body = "\n".join("  - " + t for t in typos)
        print("SPELL BLOCK — 한국어 맞춤법 오타 %d건 in %s. 고친 뒤 계속하세요:\n%s"
              % (len(typos), os.path.basename(file_path), body), file=sys.stderr)
        return 2
    return 0


def main():
    try:
        sys.exit(run(sys.stdin.read()))
    except Exception:
        sys.exit(0)  # safety-first: never block Claude on the guard's own error


if __name__ == "__main__":
    main()
