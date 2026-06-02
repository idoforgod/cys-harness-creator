#!/usr/bin/env python3
"""lint_guard — PostToolUse(Edit|Write) auto-correction loop for Python source.

WHY: the factory's first-class tools (and every emitted harness) gain a linter that fires
the moment Claude saves a `.py`. Mechanical violations (unused imports, etc.) are auto-fixed
IN PLACE — no human, no agent turn. Whatever REMAINS (semantic defects like F821 undefined
name) becomes an exit-2 + stderr block: the live Claude Code runtime feeds stderr back to the
model, which self-corrects and re-saves. Linter red light -> agent fixes itself -> no human.

A1 boundary: ruff is a deterministic guardrail (it never decides the domain answer). The
mechanical `--fix` is a safe rewrite; any *semantic* fix is left to Claude (the primitive).

Activation: create a `.lint-guard` file in the project root (gradual rollout / kill-switch).
Scope: `.py` only; vendored/emitted trees (genome/, .harness/genome/, examples/) are skipped
so the gate stays signal. Uses the project's ruff.toml when present (CYS rule selection).

Triggered by: PostToolUse with matcher "Edit|Write".
Contract: prints nothing on pass (exit 0); on a remaining violation prints to stderr + exit 2.
Safety-first: ruff missing, toggle off, out-of-scope path, or ANY internal error -> exit 0
(never block Claude on the guard's own failure).
"""

import json
import os
import shutil
import subprocess
import sys

# Vendored upstream / emitted artifacts: never lint these (editing them breaks sync; they are
# regenerable). Mirrors ruff.toml `exclude`, applied per-path so it holds even without a config.
# `.claude/hooks/scripts/` holds the transplanted genome hooks (carry their own upstream lint
# debt, e.g. F821) — out of scope so an emitted harness never blocks on vendored code.
SKIP_PARTS = ("/genome/", "/.harness/genome/", "/.claude/hooks/scripts/", "/examples/",
              "/__pycache__/", "/.pytest_cache/", "/_workspace/", "/_measurement/")


def _ruff():
    return shutil.which("ruff")


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


def lint_python(file_path, config=None):
    """Auto-fix mechanical issues in place, then return the REMAINING ruff violations
    (one '<row>:<CODE> <message>' string each). Empty list = clean (or ruff absent)."""
    ruff = _ruff()
    if not ruff or not file_path.endswith(".py") or not os.path.isfile(file_path):
        return []
    base = [ruff, "check", file_path]
    if config:
        base += ["--config", config]
    # 1) silently auto-fix the safe, mechanical violations (no block for those)
    subprocess.run(base + ["--fix"], capture_output=True, text=True)
    # 2) report whatever survives the fix
    proc = subprocess.run(base + ["--output-format", "json"], capture_output=True, text=True)
    try:
        items = json.loads(proc.stdout or "[]")
    except Exception:
        return []  # json unavailable -> stay advisory rather than guess
    out = []
    for it in items:
        code = it.get("code") or "?"
        msg = (it.get("message") or "").strip()
        row = (it.get("location") or {}).get("row")
        out.append("%s:%s %s" % (row, code, msg))
    return out


def run(stdin_text, project_dir=None):
    """Return the hook exit code (0 pass / 2 block) for a PostToolUse payload string."""
    project_dir = project_dir or _find_project_dir()
    # Gate: toggle off -> fast no-op (gradual rollout)
    if not os.path.exists(os.path.join(project_dir, ".lint-guard")):
        return 0
    try:
        payload = json.loads(stdin_text)
        file_path = (payload.get("tool_input") or {}).get("file_path", "")
    except Exception:
        return 0  # malformed payload never blocks
    if not file_path or not file_path.endswith(".py") or _out_of_scope(file_path, project_dir):
        return 0
    cfg = os.path.join(project_dir, "ruff.toml")
    cfg = cfg if os.path.isfile(cfg) else None
    violations = lint_python(file_path, cfg)
    if violations:
        body = "\n".join("  - " + v for v in violations[:50])
        print("LINT BLOCK — %d ruff violation(s) in %s. Fix these before continuing:\n%s"
              % (len(violations), os.path.basename(file_path), body), file=sys.stderr)
        return 2
    return 0


def main():
    try:
        sys.exit(run(sys.stdin.read()))
    except Exception:
        sys.exit(0)  # safety-first: never block Claude on the guard's own error


if __name__ == "__main__":
    main()
