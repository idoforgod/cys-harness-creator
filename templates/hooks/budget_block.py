#!/usr/bin/env python3
"""budget_block — runtime spawn-count ceiling for the primitive substrate (exit 2).

WHY (pivot blocker CD-1/R6): Mode A's hard ceiling was the Workflow runner's ambient
token meter (budget.remaining() throwing BUDGET_GUARD). On the Claude Code primitive
substrate there is NO host token meter, and per-call token usage is not reliably exposed
in hook stdin (cys_log_tokens self-documents this). So the runtime ceiling is RE-BASED on
a COUNTABLE, host-observable signal: cumulative sub-agent SPAWN COUNT vs a graph-derived
maximum. Token tally stays advisory; spawn-count is the enforceable interlock.

Wired as PreToolUse with matcher 'Agent|Task|TeamCreate'. On each spawn it reads
.harness/state.yaml `budget.spawns_used` / `budget.max_spawns` (orchestrator-maintained,
single-writer) and exits 2 when spawns_used >= max_spawns - margin. Advisory-safe: if
state.yaml or max_spawns is absent it never blocks (exit 0). The orchestrator increments
spawns_used after each spawn (single-writer SOT).

Exit: 0 allow, 2 BLOCK. Selftest: budget_block.py --selftest
"""
import os
import re
import sys


def _read_state(path):
    """Return (spawns_used, max_spawns) ints or (None, None). PyYAML if present, else regex."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return (None, None)
    try:
        import yaml  # genome ships PyYAML
        d = yaml.safe_load(text) or {}
        b = (d.get("budget") or {})
        return (b.get("spawns_used"), b.get("max_spawns"))
    except Exception:
        used = re.search(r"\bspawns_used:\s*(\d+)", text)
        mx = re.search(r"\bmax_spawns:\s*(\d+)", text)
        return (int(used.group(1)) if used else None, int(mx.group(1)) if mx else None)


def decide(spawns_used, max_spawns, margin):
    """(block, reason). Advisory-safe: missing data never blocks."""
    if max_spawns is None:
        return (False, "no max_spawns in SOT (advisory)")
    used = spawns_used or 0
    if used >= max_spawns - margin:
        return (True, "spawn ceiling: spawns_used=%d >= max_spawns(%d) - margin(%d)" % (used, max_spawns, margin))
    return (False, "ok %d/%d" % (used, max_spawns))


def _margin():
    try:
        import json
        here = os.path.dirname(os.path.abspath(__file__))
        proj = os.environ.get("CLAUDE_PROJECT_DIR", "")
        # SPAWN_CEILING_MARGIN SoT: inherit_genome stamps it into <harness>/.harness/constants.json (safe in
        # both install modes — never the host root); fall back to the harness/factory root constants.json.
        for c in (os.path.join(proj, ".harness", "constants.json"),
                  os.path.join(here, "..", "..", "..", "constants.json"),
                  os.path.join(proj, "constants.json")):
            if os.path.isfile(c):
                return json.load(open(c)).get("SPAWN_CEILING_MARGIN", 1)
    except Exception:
        pass
    return 1


def run():
    proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    state = os.path.join(proj, ".harness", "state.yaml")
    used, mx = _read_state(state)
    block, reason = decide(used, mx, _margin())
    if block:
        print("BUDGET BLOCK: %s — increase graph.budget or reduce fan-out." % reason, file=sys.stderr)
        return 2
    return 0


def _selftest():
    cases = [
        ((5, 10, 1), False, "under ceiling"),
        ((9, 10, 1), True, "at ceiling-margin"),
        ((10, 10, 1), True, "over ceiling"),
        ((0, None, 1), False, "no max -> advisory pass"),
        ((None, 8, 1), False, "no used -> treated 0, pass"),
    ]
    failed = 0
    for (u, m, mg), want, desc in cases:
        got = decide(u, m, mg)[0]
        ok = got == want
        failed += 0 if ok else 1
        print("%s %-28s got=%s want=%s" % ("ok " if ok else "FAIL", desc, got, want))
    print("\n%d/%d passed" % (len(cases) - failed, len(cases)))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(run())
