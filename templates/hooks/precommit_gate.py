#!/usr/bin/env python3
"""precommit_gate — PreToolUse(Bash) "잠깐, 이것부터 확인" gate before `git commit`.

WHY: lint_guard catches a single just-saved file; this gate catches the WHOLE tree at the
commit boundary. When Claude runs `git commit`, the hook first runs the project gate — ruff
over the in-scope tree, plus the test suite if one exists — and on failure returns exit-2 with
the reason on stderr. The live runtime feeds that back to Claude, which fixes and re-commits.
Linter red light -> agent fixes itself -> no human, and a red tree never reaches history.

A1 boundary: ruff + the test runner are deterministic guardrails (block/measure only); the
actual fix is Claude's (the primitive). The gate never edits code.

Activation: `.lint-guard` toggle in the project root (shared with lint_guard; gradual rollout).
Scope: ruff honors the project's ruff.toml (exclude/select); only `git commit` is intercepted —
every other Bash command passes straight through.

Triggered by: PreToolUse with matcher "Bash".
Safety-first: non-commit command, toggle off, or ANY internal error -> exit 0 (never block).
"""

import json
import os
import re
import shutil
import subprocess
import sys

# git global options that consume a following value token (so we skip the value too when
# scanning for the subcommand): `git -c k=v commit`, `git -C path commit`, etc.
_GIT_OPTS_WITH_VALUE = ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path")


def is_git_commit(command):
    """True only when `commit` is git's SUBCOMMAND (global options skipped), checked per shell
    segment — so `git commit`, `git -c k=v commit`, and `git add -A && git commit` match, but
    `git status`, `git log --oneline commit`, and `echo committing` do not."""
    for seg in re.split(r"[|;&]+", command or ""):
        m = re.search(r"\bgit\s+(.+)", seg)
        if not m:
            continue
        toks = m.group(1).split()
        i = 0
        while i < len(toks) and toks[i].startswith("-"):
            i += 2 if toks[i] in _GIT_OPTS_WITH_VALUE else 1
        if i < len(toks) and toks[i] == "commit":
            return True
    return False


def _find_project_dir():
    d = os.environ.get("CLAUDE_PROJECT_DIR")
    if d and os.path.isdir(d):
        return d
    return os.getcwd()


def _last_line(text):
    lines = (text or "").strip().splitlines()
    return lines[-1] if lines else ""


def gate(project_dir):
    """Run the deterministic checks; return a list of human-readable failure strings (empty = pass)."""
    fails = []
    ruff = shutil.which("ruff")
    if ruff:
        p = subprocess.run([ruff, "check", "."], cwd=project_dir, capture_output=True, text=True)
        if p.returncode != 0:
            fails.append("ruff: " + (_last_line(p.stdout) or "violations remain"))
    if os.path.isdir(os.path.join(project_dir, "tests")):
        p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                           cwd=project_dir, capture_output=True, text=True)
        if p.returncode != 0:
            fails.append("tests: " + (_last_line(p.stderr) or _last_line(p.stdout) or "suite failed"))
    return fails


def run(stdin_text, project_dir=None):
    """Return the hook exit code (0 pass / 2 block) for a PreToolUse(Bash) payload string."""
    project_dir = project_dir or _find_project_dir()
    if not os.path.exists(os.path.join(project_dir, ".lint-guard")):
        return 0  # toggle off -> fast no-op (gradual rollout)
    try:
        payload = json.loads(stdin_text)
        command = (payload.get("tool_input") or {}).get("command", "")
    except Exception:
        return 0  # malformed payload never blocks
    if not is_git_commit(command):
        return 0  # only `git commit` is gated; everything else passes
    fails = gate(project_dir)
    if fails:
        body = "\n".join("  ✗ " + f for f in fails)
        print("PRECOMMIT GATE — 잠깐, 커밋 전에 이것부터 확인하세요:\n%s\n고친 뒤 다시 커밋하면 됩니다."
              % body, file=sys.stderr)
        return 2
    return 0


def main():
    try:
        sys.exit(run(sys.stdin.read()))
    except Exception:
        sys.exit(0)  # safety-first: never block Claude on the gate's own error


if __name__ == "__main__":
    main()
