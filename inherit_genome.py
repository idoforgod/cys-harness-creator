#!/usr/bin/env python3
"""CYS Harness Creator — Genome Inheritance Installer (전수/유전).

USER MANDATE: every harness built by cys-harness-creator must inherit the FULL
AgenticWorkflow functional machinery (the complete set of capabilities a long-running
harness needs to work perfectly) — self-contained, real code verbatim, every harness,
always. "통합만 되고 전수(유전)되지 않으면 무의미." So this installer TRANSPLANTS the
vendored genome into a child harness AND verifies it actually loads.

genome/  = a one-time vendored snapshot of AgenticWorkflow's functional machinery
           (AWF is READ-ONLY upstream; re-vendor manually when AWF changes).

What it does (idempotent):
  1. rsync genome/ -> <harness>/   (full machinery, self-contained)
        - keeps the child's domain README.md (genome README skipped)
        - settings.json merged separately (not clobbered)
  2. merge .claude/settings.json = genome's full AWF hook wiring + permissions.deny
        + CYS SubagentStop (cys_log_tokens) — idempotent
  3. install CYS-specific hook (cys_log_tokens.py) into .claude/hooks/scripts/
  4. append a CYS harness pointer to the inherited CLAUDE.md (child has BOTH the AWF
     operating genome AND the CYS Mode-A graph.json/workflow.js engine)
  5. create the runtime dirs the AWF machinery expects (context-snapshots, agent-memory,
     pacs-logs, verification-logs) so hooks don't fail on first run
  6. stamp .harness/GENOME.json provenance
  7. VERIFY: py_compile every transplanted hook + import _context_lib (the shared spine)
     -> proves the machinery is functionally present, not just copied. Returns ok/errors.

CLI: inherit_genome.py <harness_dir> [--verify-only]
"""
import json
import os
import py_compile
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_GENOME = os.path.join(_HERE, "genome")
sys.path.insert(0, os.path.join(_HERE, "lib"))
from atomic_write import atomic_write  # noqa: E402

_RUNTIME_DIRS = [".claude/context-snapshots", ".claude/agent-memory", "pacs-logs", "verification-logs"]
_CYS_LOG_HOOK = "cys_log_tokens.py"
_CLAUDE_PTR = """

---

## CYS Harness Engine (inherited alongside the AgenticWorkflow genome)

This harness carries the FULL AgenticWorkflow genome above AND a CYS deterministic
Mode-A engine. The two are complementary:
- **AWF genome** (this file + `.claude/`, `docs/`, `prompt-runner/`): operating constitution,
  context-preservation hooks, 4-layer quality gates, security, agents, skills.
- **CYS engine** (`.harness/`): `graph.json` (immutable contract) -> `workflow.js`
  (deterministic Workflow runtime, budget ceiling + resume), validated by
  `validate_harness.py`, cost-gated by `warrant.py`, measured by `lift_gate`/`h2h`.

### Runtime routing — ONE canonical, no ambiguity (see `.harness/RUNTIME.json`)
This harness inherits TWO runtimes. They never run the same task and do not call each other:
- **CANONICAL = CYS Mode-A `.harness/workflow.js`** — THE way to run THIS harness. It is the
  only runtime wired to `graph.json`. Deterministic, budget-gated, resume-safe, tool-driven.
- **ALTERNATIVE (inherited) = `prompt-runner/run.py`** — AWF's general `claude -p` batch engine.
  NOT wired to this harness's `graph.json`; it is inherited *capability*, available for ad-hoc
  long / human-in-the-loop / rate-limit-exposed batch work — NOT a second way to run this graph.

Routing rule: run this harness via its canonical runtime; reach for prompt-runner only for the
long human-driven batch case above. Never route one task through both.

Run: `python3 ../../validate_harness.py .` (build gate) then
`Workflow({ scriptPath: ".harness/workflow.js", args: {...} })`.
"""

_RUNTIME_MANIFEST = {
    "schema_version": "0.1",
    "canonical_runtime": "cys-mode-a",
    "runtimes": [
        {"name": "cys-mode-a", "role": "canonical", "entrypoint": ".harness/workflow.js",
         "driver": "Workflow tool (agent/parallel/pipeline)",
         "kind": "deterministic, tool-driven, immutable, budget-gated, resume-safe",
         "wired_to": "graph.json (this harness's contract)",
         "use_when": "default — ALL of this harness's defined work; graph.json -> workflow.js is THE path"},
        {"name": "awf-prompt-runner", "role": "inherited-alternative", "entrypoint": "prompt-runner/run.py",
         "driver": "claude -p --resume (CLI batch sessions)",
         "kind": "human-driven, stateful, rate-limit-resilient, 100+ step batch",
         "wired_to": "NOT wired to this harness's graph.json — general AWF batch executor, inherited as capability",
         "use_when": "ad-hoc long / human-in-loop / rate-limit-exposed batch tasks; NOT the harness default"},
    ],
    "routing_rule": "Run this harness via its canonical runtime (.harness/workflow.js). prompt-runner is "
                    "inherited AWF capability for long human-driven batch work, NOT a second way to run this "
                    "harness's graph. Never run the same task through both.",
    "no_conflict_note": "The two runtimes do not call each other and are not both invoked for the same task; "
                        "prompt-runner is not bound to graph.json.",
}


def _rsync(src, dst, excludes):
    args = ["rsync", "-a"] + ["--exclude=" + e for e in excludes] + [src.rstrip("/") + "/", dst.rstrip("/") + "/"]
    subprocess.run(args, check=True)


def _merge_settings(harness_dir):
    base = json.load(open(os.path.join(_GENOME, ".claude", "settings.json"), encoding="utf-8"))
    hooks = base.setdefault("hooks", {})
    ss = hooks.setdefault("SubagentStop", [])
    cmd = 'if test -f "$CLAUDE_PROJECT_DIR"/.claude/hooks/scripts/%s; then python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/scripts/%s; fi' % (_CYS_LOG_HOOK, _CYS_LOG_HOOK)
    if not any(_CYS_LOG_HOOK in json.dumps(e) for e in ss):
        ss.append({"matcher": "*", "hooks": [{"type": "command", "command": cmd, "timeout": 5000}]})
    atomic_write(os.path.join(harness_dir, ".claude", "settings.json"),
                 json.dumps(base, indent=2, ensure_ascii=False) + "\n")


def _verify(harness_dir):
    """Prove the transplanted machinery is functional, not just present."""
    errors = []
    scripts = os.path.join(harness_dir, ".claude", "hooks", "scripts")
    if not os.path.isdir(scripts):
        return ["genome hooks/scripts not transplanted"]
    py = [f for f in os.listdir(scripts) if f.endswith(".py")]
    for f in py:
        try:
            py_compile.compile(os.path.join(scripts, f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append("compile fail %s: %s" % (f, str(e).splitlines()[0]))
    # import the shared spine in an isolated subprocess (it's the load-bearing dependency)
    probe = ("import sys; sys.path.insert(0, %r); import _context_lib" % scripts)
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    if r.returncode != 0:
        errors.append("_context_lib import fail: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    return errors


def inherit(harness_dir, verify_only=False):
    harness_dir = os.path.abspath(harness_dir)
    if not os.path.isdir(_GENOME):
        raise SystemExit("genome/ not found — vendor it first (rsync AgenticWorkflow functional machinery).")
    if not verify_only:
        # 1. transplant full genome (keep child README + handle settings via merge)
        _rsync(_GENOME, harness_dir, excludes=["README.md", ".claude/settings.json"])
        # 2. merge settings.json
        _merge_settings(harness_dir)
        # 3. install CYS log hook into the AWF scripts dir
        src = os.path.join(_HERE, "templates", "hooks", _CYS_LOG_HOOK)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(harness_dir, ".claude", "hooks", "scripts", _CYS_LOG_HOOK))
        # 4. append CYS pointer to inherited CLAUDE.md (once)
        cm = os.path.join(harness_dir, "CLAUDE.md")
        if os.path.isfile(cm):
            txt = open(cm, encoding="utf-8").read()
            if "CYS Harness Engine (inherited" not in txt:
                atomic_write(cm, txt + _CLAUDE_PTR)
        # 5. runtime dirs the machinery expects
        for d in _RUNTIME_DIRS:
            p = os.path.join(harness_dir, d)
            os.makedirs(p, exist_ok=True)
            gk = os.path.join(p, ".gitkeep")
            if not os.path.exists(gk):
                open(gk, "w").close()
        # 6. provenance + runtime routing manifest (resolves the two-runtime ambiguity)
        atomic_write(os.path.join(harness_dir, ".harness", "GENOME.json"), json.dumps({
            "source": "AgenticWorkflow (READ-ONLY upstream)",
            "vendored_via": "cys-harness-creator/genome/",
            "transplant": "full functional machinery, self-contained, verbatim",
            "genome_file_count": sum(len(fs) for _, _, fs in os.walk(_GENOME)),
        }, indent=2, ensure_ascii=False) + "\n")
        atomic_write(os.path.join(harness_dir, ".harness", "RUNTIME.json"),
                     json.dumps(_RUNTIME_MANIFEST, indent=2, ensure_ascii=False) + "\n")
    # 7. verify functional
    errs = _verify(harness_dir)
    return errs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: inherit_genome.py <harness_dir> [--verify-only]", file=sys.stderr); sys.exit(2)
    errs = inherit(args[0], verify_only="--verify-only" in sys.argv)
    if errs:
        for e in errs:
            print("[genome-verify] FAIL:", e)
        print("\nGENOME INHERITANCE: %d verification error(s)" % len(errs))
        sys.exit(1)
    print("GENOME INHERITANCE: full AWF machinery transplanted + verified functional (imports OK)")
    sys.exit(0)


if __name__ == "__main__":
    main()
