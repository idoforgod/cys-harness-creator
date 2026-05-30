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
# CYS-specific hooks installed alongside the AWF genome (templates/hooks -> child scripts dir).
# M0d adds the three that make DNA FIRE instead of lie dormant: spawn_counter (increments the budget
# ceiling counter), sot_init (instantiates the SOT), qa_gate_runner (fires L0-L2 via gate_or_block).
_CYS_HOOKS = ["cys_log_tokens.py", "gate_or_block.py", "budget_block.py",
              "spawn_counter.py", "sot_init.py", "qa_gate_runner.py"]
_CLAUDE_PTR = """

---

## CYS Harness Engine (inherited alongside the AgenticWorkflow genome)

This harness carries the FULL AgenticWorkflow genome above AND the CYS machine-checked contract:
- **AWF genome** (this file + `.claude/`, `docs/`): operating constitution, context-preservation +
  long-term memory hooks, 4-layer quality gates, security, adversarial-review agents, skills.
- **CYS contract** (`.harness/`): `graph.json` (immutable, machine-checked), validated by
  `validate_harness.py`, cost-gated by `warrant.py`, measured by `lift_gate`/`h2h`.

### Runtime — ONE runtime, 100% Claude Code primitives (see `.harness/RUNTIME.json`)
This harness runs as a **live `claude` session** driven by the orchestrator skill in `.claude/skills/`,
which delegates ALL work to Claude Code primitives (Agent / TeamCreate / SendMessage / TaskCreate).
**That is the only execution runtime** — there is no compiled `.js` workflow runtime and no subprocess
batch runner; the inherited `prompt-runner/` is vendored capability, NOT an execution path. The
inherited genome hooks (context-preservation + long-term memory, L0-L2 quality gates, budget ceiling,
SOT) fire in that live session.

Run: open a session in this dir (`cd <harness_dir> && claude`) and trigger the orchestrator skill;
`python3 ../../validate_harness.py .` is the build gate.
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


def _hook_cmd(script):
    return ('if test -f "$CLAUDE_PROJECT_DIR"/.claude/hooks/scripts/%s; then '
            'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/scripts/%s; fi' % (script, script))


def _union_hooks(dst, src):
    """Union source (genome) hook entries into dst (host) hooks per event, skipping any whose command-set
    already appears — so an in-project install (P1/B2) never clobbers a host project's existing hooks."""
    for event, entries in (src or {}).items():
        bucket = dst.setdefault(event, [])
        for e in entries:
            sig = json.dumps([h.get("command", "") for h in e.get("hooks", [])], sort_keys=True)
            if not any(json.dumps([h.get("command", "") for h in b.get("hooks", [])], sort_keys=True) == sig for b in bucket):
                bucket.append(e)
    return dst


def _merge_settings(harness_dir):
    genome = json.load(open(os.path.join(_GENOME, ".claude", "settings.json"), encoding="utf-8"))
    host_path = os.path.join(harness_dir, ".claude", "settings.json")
    if os.path.isfile(host_path):
        # in-project install (or re-emit): preserve the host's existing settings + UNION genome hooks in.
        try:
            base = json.load(open(host_path, encoding="utf-8"))
        except ValueError:
            base = dict(genome)
        _union_hooks(base.setdefault("hooks", {}), genome.get("hooks", {}))
    else:
        base = genome
    hooks = base.setdefault("hooks", {})
    # CYS SubagentStop token log (coarse/advisory). timeout=5s — was 5000 (ms-vs-s bug, CD-5).
    ss = hooks.setdefault("SubagentStop", [])
    if not any(_CYS_LOG_HOOK in json.dumps(e) for e in ss):
        ss.append({"matcher": "*", "hooks": [{"type": "command", "command": _hook_cmd(_CYS_LOG_HOOK), "timeout": 5}]})
    # CYS runtime spawn-count ceiling — PreToolUse(Agent|Task|TeamCreate) budget_block (exit 2).
    # Disjunction matcher covers the spawn primitive across substrate versions (R2/CD-2):
    # current Claude Code spawns via `Agent`; legacy genome prose uses `Task`; teams via `TeamCreate`.
    pre = hooks.setdefault("PreToolUse", [])
    if not any("budget_block.py" in json.dumps(e) for e in pre):
        pre.append({"matcher": "Agent|Task|TeamCreate",
                    "hooks": [{"type": "command", "command": _hook_cmd("budget_block.py"), "timeout": 5}]})
    # M0d: the missing halves that make the ceiling + gates actually FIRE.
    post = hooks.setdefault("PostToolUse", [])
    # spawn_counter increments budget.spawns_used (the counter budget_block reads at PreToolUse).
    if not any("spawn_counter.py" in json.dumps(e) for e in post):
        post.append({"matcher": "Agent|Task|TeamCreate",
                     "hooks": [{"type": "command", "command": _hook_cmd("spawn_counter.py"), "timeout": 5}]})
    # qa_gate_runner fires L0-L2 (via gate_or_block) on a claimed step — exit 2 halts a real failure.
    if not any("qa_gate_runner.py" in json.dumps(e) for e in post):
        post.append({"matcher": "Agent|Task|TaskUpdate",
                     "hooks": [{"type": "command", "command": _hook_cmd("qa_gate_runner.py"), "timeout": 15}]})
    # sot_init instantiates .harness/state.yaml on cold start (so the SOT + ceiling exist on run 1).
    starts = hooks.setdefault("SessionStart", [])
    if not any("sot_init.py" in json.dumps(e) for e in starts):
        starts.append({"matcher": "startup|clear|resume",
                       "hooks": [{"type": "command", "command": _hook_cmd("sot_init.py"), "timeout": 5}]})
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


def _init_memory_store(harness_dir):
    """Seed the Tier-II cross-run domain memory store (M6) — the RLM 'external environment' the harness
    queries programmatically across repeated RUNS. IDEMPOTENT: only creates missing seed files, never
    clobbers accumulated runs/knowledge (so memory accretes run over run)."""
    mem = os.path.join(harness_dir, ".harness", "memory")
    os.makedirs(os.path.join(mem, "runs"), exist_ok=True)
    os.makedirs(os.path.join(mem, "risk"), exist_ok=True)
    seeds = {
        "archive.manifest.json": json.dumps({
            "schema_version": "0.1",
            "purpose": "Tier-II cross-run domain memory (RLM external environment) — query programmatically, never bulk-load",
            "sections": {
                "runs/index.jsonl": "thin append-only probe; one line per run. Grep it, then Read only matched runs/<id>/.",
                "domain-knowledge.yaml": "IMMORTAL DKS: entities/relations/constraints, reused as L1 verification criteria.",
                "risk/decisions.jsonl": "IMMORTAL standing decisions / risks (e.g. 'never use source X')."},
            "query_recipe": "Grep '<query tokens>' .harness/memory/runs/index.jsonl -> Read .harness/memory/runs/<run_id>/* on a hit only",
        }, indent=2, ensure_ascii=False) + "\n",
        "domain-knowledge.yaml": ("# IMMORTAL domain knowledge (DKS) — entities/relations/constraints,"
                                  " accreted across runs.\nentities: {}\nrelations: []\nconstraints: []\n"),
        os.path.join("runs", "index.jsonl"): "",
        os.path.join("risk", "decisions.jsonl"): "",
    }
    for rel, content in seeds.items():
        p = os.path.join(mem, rel)
        if not os.path.exists(p):
            atomic_write(p, content)


def inherit(harness_dir, verify_only=False, runtime_manifest=None):
    """Transplant the genome. runtime_manifest overrides the default (workflow.js-canonical)
    RUNTIME.json — emit_orchestrator passes an orchestrator-skill-canonical manifest for the
    primitive substrate (execution_mode agent|team|hybrid)."""
    harness_dir = os.path.abspath(harness_dir)
    if not os.path.isdir(_GENOME):
        raise SystemExit("genome/ not found — vendor it first (rsync AgenticWorkflow functional machinery).")
    if not verify_only:
        # 1. transplant full genome (keep child README + handle settings via merge)
        _rsync(_GENOME, harness_dir, excludes=["README.md", ".claude/settings.json"])
        # 2. merge settings.json
        _merge_settings(harness_dir)
        # 3. install CYS-specific hooks into the AWF scripts dir (token log + gate/budget interlocks)
        dst_scripts = os.path.join(harness_dir, ".claude", "hooks", "scripts")
        for hook in _CYS_HOOKS:
            src = os.path.join(_HERE, "templates", "hooks", hook)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(dst_scripts, hook))
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
        # 5.5 Tier-II cross-run domain memory store (M6 / RLM external environment)
        _init_memory_store(harness_dir)
        # 6. provenance + runtime routing manifest (resolves the two-runtime ambiguity)
        atomic_write(os.path.join(harness_dir, ".harness", "GENOME.json"), json.dumps({
            "source": "AgenticWorkflow (READ-ONLY upstream)",
            "vendored_via": "cys-harness-creator/genome/",
            "transplant": "full functional machinery, self-contained, verbatim",
            "genome_file_count": sum(len(fs) for _, _, fs in os.walk(_GENOME)),
        }, indent=2, ensure_ascii=False) + "\n")
        atomic_write(os.path.join(harness_dir, ".harness", "RUNTIME.json"),
                     json.dumps(runtime_manifest or _RUNTIME_MANIFEST, indent=2, ensure_ascii=False) + "\n")
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
