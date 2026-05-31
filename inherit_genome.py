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
# In-project (P1.2/B2) overlay: never pollute the host root — log dirs nest under .harness/.
_RUNTIME_DIRS_INPROJECT = [".claude/context-snapshots", ".claude/agent-memory",
                           ".harness/pacs-logs", ".harness/verification-logs"]
# In-project genome subset (evidence: workflow in-project-install-understand). The .claude/ runtime DNA
# is overlaid into the host; the ~440KB root constitution + docs are RELOCATED under .harness/genome/
# (no core hook READS them — only os.path.isfile-guarded doc-sync lints — so relocation is behavior-safe
# and never clobbers the host's own root CLAUDE.md/AGENTS.md/README).
# P0-3 (audit): the prompt-runner subprocess executor (`claude -p` batch runner) + its slash commands are a
# NON-PRIMITIVE execution path — never part of a produced harness's A1 runtime. Exclude from BOTH install modes
# (in-project already skips them via _RELOCATE_EXCLUDES + commands-skip; this covers the self-contained pour).
_NONPRIMITIVE_EXCLUDES = ["/prompt-runner", "/prompt", "*-prompts.md"]
_INPROJECT_NONCLOBBER_SUBS = ["agents", "skills", "config"]   # capability+config: host file always wins
# adversarial-review agents are L2 DNA — force-installed from genome even in-project (host copy backed up)
_MANDATORY_GENOME_AGENTS = ["reviewer.md", "fact-checker.md"]
# anchored to the genome root (leading /) so only the top-level dirs drop — keeps docs/ + all root .md
_RELOCATE_EXCLUDES = ["/.claude", "/prompt", "/prompt-runner", "/translations", "__pycache__"]
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

_CLAUDE_PTR_INPROJECT = """

---

## CYS Harness Engine (inherited as an in-project overlay)

This project hosts a CYS harness installed as an **additive overlay** (idoforgod-style in-project install) —
your own root files (`CLAUDE.md`, `AGENTS.md`, `README.md`) are PRESERVED, not replaced.
- **CYS contract** (`.harness/`): `graph.json` (immutable, machine-checked) validated by `validate_harness.py`,
  cost-gated by `warrant.py`. The orchestrator skill in `.claude/skills/<name>-orchestrator/` drives all work
  via Claude Code primitives (Agent / TeamCreate / SendMessage / TaskCreate) — the only execution runtime.
- **AWF genome** (overlay): runtime DNA merged into this project's `.claude/` (hooks, L0-L2 gates, SOT, security,
  adversarial-review agents, skills). The full AWF operating constitution + protocol docs are vendored read-only
  under `.harness/genome/` (NOT dumped into this project's root). `prompt-runner/` is NOT installed in-project.

Trigger the `<name>-orchestrator` skill for this harness's domain work; `python3 .../validate_harness.py .` is the build gate.
"""

# Default RUNTIME.json for a bare `inherit_genome.py <dir>` (no override). emit_orchestrator ALWAYS passes
# an orchestrator-canonical manifest with the real harness name; this default must NOT advertise the retired
# Mode-A workflow.js or the prompt-runner subprocess as runnable runtimes (audit: standalone CLI was dishonest).
_RUNTIME_MANIFEST = {
    "schema_version": "0.1",
    "canonical_runtime": "orchestrator-skill",
    "runtimes": [
        {"name": "orchestrator-skill", "role": "canonical",
         "entrypoint": ".claude/skills/<harness>-orchestrator/SKILL.md",
         "driver": "Claude Code primitives (Agent / TeamCreate / SendMessage / TaskCreate), live host session",
         "kind": "prose-driven, genome-active (hooks/L0-L2/SOT fire), graph.json-contracted",
         "wired_to": "graph.json (this harness's contract) via emit_orchestrator",
         "use_when": "default — ALL of this harness's work runs as a live `claude` session driven by this skill"},
    ],
    "routing_rule": "Run this harness by opening a `claude` session in its dir and triggering the "
                    "<harness>-orchestrator skill — the ONLY execution runtime. The retired Mode-A workflow.js "
                    "and the inherited prompt-runner are NOT execution paths for a produced harness.",
}


def _rsync(src, dst, excludes):
    args = ["rsync", "-a"] + ["--exclude=" + e for e in excludes] + [src.rstrip("/") + "/", dst.rstrip("/") + "/"]
    subprocess.run(args, check=True)


def _rsync_ignore_existing(src, dst, excludes):
    """Copy only files the host LACKS (--ignore-existing) — a pre-existing host file always wins.
    Used for the in-project overlay's capability/config dirs so a host agent/skill/config is never clobbered."""
    if not os.path.isdir(src):
        return
    args = ["rsync", "-a", "--ignore-existing"] + ["--exclude=" + e for e in excludes] \
        + [src.rstrip("/") + "/", dst.rstrip("/") + "/"]
    subprocess.run(args, check=True)


def _force_install_mandatory_agents(harness_dir):
    """The adversarial-review agents (reviewer/fact-checker) are the L2 DNA — the credited head-to-head
    discriminator — so the GENOME versions must be present even in-project. The plain --ignore-existing copy
    would let a host's same-named agent win and silently disable L2 (validate's REVIEW_AGENT_PRESENT would then
    pass for the wrong reason). Here we GUARANTEE the genome versions, but never destroy a host file: any
    displaced host agent is backed up under .harness/genome/displaced/ (recoverable) with a stderr notice."""
    src_dir = os.path.join(_GENOME, ".claude", "agents")
    dst_dir = os.path.join(harness_dir, ".claude", "agents")
    os.makedirs(dst_dir, exist_ok=True)
    for fn in _MANDATORY_GENOME_AGENTS:
        src = os.path.join(src_dir, fn)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dst_dir, fn)
        if os.path.isfile(dst) and open(dst, "rb").read() != open(src, "rb").read():
            bdir = os.path.join(harness_dir, ".harness", "genome", "displaced")
            os.makedirs(bdir, exist_ok=True)
            bpath = os.path.join(bdir, fn)
            if not os.path.exists(bpath):
                shutil.copyfile(dst, bpath)
            print("[in-project] mandatory L2 agent '%s' force-installed from genome; host's version preserved at "
                  ".harness/genome/displaced/%s" % (fn, fn), file=sys.stderr)
        shutil.copyfile(src, dst)


def _transplant_overlay(harness_dir):
    """In-project (B2) transplant: an ADDITIVE OVERLAY, not a self-contained pour.
      - .claude/hooks/   -> non-clobber: a host's OWN same-named hook (incl. tuned security hooks) always wins;
                            the genome installs only the hooks the host lacks (--ignore-existing).
      - .claude/{agents,skills,config} -> copied ONLY where the host lacks the file (--ignore-existing).
      - reviewer/fact-checker -> force-installed from genome (L2 DNA), host copy backed up, never destroyed.
      - .claude/commands/ -> SKIPPED (prompt-runner-coupled; prompt-runner is not installed in-project).
      - root constitution + docs/ -> RELOCATED under .harness/genome/ (never the host root).
      - prompt/, prompt-runner/, translations/ -> SKIPPED (inert / lazy-bootstrapped).
    settings.json is handled by _merge_settings (host-preserving union), not here."""
    gclaude = os.path.join(_GENOME, ".claude")
    hclaude = os.path.join(harness_dir, ".claude")
    # runtime DNA hooks: NEVER clobber a host's own/tuned same-named hook script (security parity with
    # agents/skills/config) — the genome installs only what the host lacks.
    _rsync_ignore_existing(os.path.join(gclaude, "hooks"), os.path.join(hclaude, "hooks"),
                           excludes=["__pycache__", "_test_*.py", "test_*.py"])
    # capability + config: never clobber a host-owned file
    for sub in _INPROJECT_NONCLOBBER_SUBS:
        _rsync_ignore_existing(os.path.join(gclaude, sub), os.path.join(hclaude, sub), excludes=["__pycache__"])
    # mandatory adversarial-review agents are load-bearing DNA — guarantee the genome versions (host copy kept)
    _force_install_mandatory_agents(harness_dir)
    # constitution + protocol docs: relocate under the CYS-owned .harness/genome/ (citable, provenance-bearing)
    _rsync(_GENOME, os.path.join(harness_dir, ".harness", "genome"), excludes=_RELOCATE_EXCLUDES)


def _purge_nonprimitive(harness_dir):
    """Self-heal: remove a prompt-runner executor + prompt samples + prompt-coupled slash commands left by a
    PRIOR (pre-fix) self-contained emit, so a re-emit converges to the A1 primitive-only runtime. SELF-CONTAINED
    ONLY (callers gate on `not in_project`) — never deletes an in-project HOST's own files. Idempotent."""
    for d in ("prompt-runner", "prompt"):
        p = os.path.join(harness_dir, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    cmds = os.path.join(harness_dir, ".claude", "commands")
    if os.path.isdir(cmds):
        for f in os.listdir(cmds):
            if f.endswith("-prompts.md"):
                try:
                    os.remove(os.path.join(cmds, f))
                except OSError:
                    pass


def _union_perms(base, genome):
    """Union the genome's security permissions.deny into the host settings (in-project) — a host with its
    own settings would otherwise never adopt the genome's deny-list (security parity gap). Idempotent."""
    gd = (genome.get("permissions") or {}).get("deny") or []
    if not gd:
        return
    deny = base.setdefault("permissions", {}).setdefault("deny", [])
    for d in gd:
        if d not in deny:
            deny.append(d)


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
            # do NOT silently replace an existing settings.json with the genome's — that would drop the host's
            # own hooks/permissions/deny controls. Refuse so the operator fixes (or removes) the file first.
            raise SystemExit(
                "existing .claude/settings.json is not valid JSON (%s) — refusing to overwrite it with genome "
                "settings (your hooks/permissions would be lost). Fix or remove the file, then re-run." % host_path)
        if not isinstance(base, dict):
            base = dict(genome)   # valid JSON but not an object ([]/null/scalar): no host-structured settings to lose
        _union_hooks(base.setdefault("hooks", {}), genome.get("hooks", {}))
        _union_perms(base, genome)   # in-project: adopt genome security deny-list onto host settings
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


def inherit(harness_dir, verify_only=False, runtime_manifest=None, in_project=False):
    """Transplant the genome. runtime_manifest overrides the default (workflow.js-canonical)
    RUNTIME.json — emit_orchestrator passes an orchestrator-skill-canonical manifest for the
    primitive substrate (execution_mode agent|team|hybrid).

    in_project=True (P1.2/B2): install as an ADDITIVE OVERLAY into an existing host project instead of a
    fresh self-contained dir — only the runtime DNA + .harness/ contract land; the host's own root files
    are preserved; the genome constitution is relocated under .harness/genome/. Idoforgod-style install."""
    harness_dir = os.path.abspath(harness_dir)
    if not os.path.isdir(_GENOME):
        raise SystemExit("genome/ not found — vendor it first (rsync AgenticWorkflow functional machinery).")
    if not verify_only:
        # 1. transplant: overlay (host-preserving) in-project, else full self-contained pour
        if in_project:
            _transplant_overlay(harness_dir)
        else:
            _rsync(_GENOME, harness_dir,
                   excludes=["README.md", ".claude/settings.json"] + _NONPRIMITIVE_EXCLUDES)
            _purge_nonprimitive(harness_dir)   # self-heal a pre-fix emit that already shipped prompt-runner
        # 2. merge settings.json (host-preserving union — same path both modes)
        _merge_settings(harness_dir)
        # 3. install CYS-specific hooks into the AWF scripts dir (token log + gate/budget interlocks)
        dst_scripts = os.path.join(harness_dir, ".claude", "hooks", "scripts")
        os.makedirs(dst_scripts, exist_ok=True)
        for hook in _CYS_HOOKS:
            src = os.path.join(_HERE, "templates", "hooks", hook)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(dst_scripts, hook))
        # 4. CYS pointer on CLAUDE.md — in-project APPENDS to (and preserves) the HOST's CLAUDE.md (creating
        #    one only if the host has none); self-contained appends to the inherited genome CLAUDE.md. Once.
        cm = os.path.join(harness_dir, "CLAUDE.md")
        ptr = _CLAUDE_PTR_INPROJECT if in_project else _CLAUDE_PTR
        if os.path.isfile(cm):
            txt = open(cm, encoding="utf-8").read()
            if "CYS Harness Engine (inherited" not in txt:
                atomic_write(cm, txt + ptr)
        elif in_project:
            atomic_write(cm, ptr.lstrip("\n"))
        # 5. runtime dirs the machinery expects (in-project nests logs under .harness/, not the host root)
        for d in (_RUNTIME_DIRS_INPROJECT if in_project else _RUNTIME_DIRS):
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
            "install_mode": "in-project" if in_project else "self-contained",
            "transplant": ("additive overlay — .claude/ runtime DNA merged into host; constitution under "
                           ".harness/genome/; host root files preserved" if in_project
                           else "full functional machinery, self-contained, verbatim"),
            "genome_docs": ".harness/genome/" if in_project else ".",
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
        print("usage: inherit_genome.py <harness_dir> [--verify-only] [--in-project]", file=sys.stderr); sys.exit(2)
    errs = inherit(args[0], verify_only="--verify-only" in sys.argv, in_project="--in-project" in sys.argv)
    if errs:
        for e in errs:
            print("[genome-verify] FAIL:", e)
        print("\nGENOME INHERITANCE: %d verification error(s)" % len(errs))
        sys.exit(1)
    print("GENOME INHERITANCE: full AWF machinery transplanted + verified functional (imports OK)")
    sys.exit(0)


if __name__ == "__main__":
    main()
