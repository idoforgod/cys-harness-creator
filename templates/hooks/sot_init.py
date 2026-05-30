#!/usr/bin/env python3
"""sot_init — instantiate the SOT state.yaml at session start (SessionStart).

WHY (M0/RR5): Absolute Criterion 2 makes `.harness/state.yaml` the single-writer SOT that wakes
ap_state-gated AWF features and feeds budget_block's ceiling. But nothing CREATED it — the orchestrator
was told in PROSE to "write/update state.yaml", so on a fresh run the file was absent, `max_spawns` was
unknown, and budget_block stayed advisory (never fired). This hook seeds the SOT deterministically.

Wired as SessionStart (matcher `startup|clear|resume`). If `.harness/state.yaml` already exists it does
NOTHING (never clobbers the orchestrator's live state — single-writer is preserved; this only handles
the cold-start case). `max_spawns` is estimated from graph.json so the ceiling has a real bound on run 1.

Exit 0 always. Selftest: sot_init.py --selftest
"""
import json
import os
import sys


def estimate_max_spawns(graph):
    """Conservative upper bound on sub-agent spawns implied by the graph — mirrors the per-node spawn
    fan-out the orchestrator prose would set. Errs slightly generous so the ceiling never false-blocks a
    legitimate run; budget_block still caps runaway fan-out."""
    total = 0
    for n in (graph.get("nodes") or []):
        mech = n.get("decision_mechanism", "single")
        mp = n.get("mechanism_params") or {}
        if mech == "majority-vote":
            total += int(mp.get("n", 3))
        elif mech == "debate-with-judge":
            total += int(mp.get("n", 2)) + 1            # debaters + judge
        elif mech == "reflect-then-revise":
            total += 1 + int(mp.get("max_rounds", 2))   # generator + critic/reviser rounds
        else:
            total += 1
        if n.get("review"):
            total += 1                                  # L2 adversarial reviewer
    return total or 1


def seed_yaml(max_spawns):
    return (
        "# .harness/state.yaml — SOT (orchestrator single-writer; seeded by sot_init on cold start).\n"
        "workflow:\n"
        "  current_step: 0\n"
        "  status: running\n"
        "outputs: {}\n"
        "budget:\n"
        "  spawns_used: 0\n"
        "  max_spawns: %d\n"
        "pacs: {}\n"
        "audit_log: []\n" % int(max_spawns)
    )


def run():
    proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    state = os.path.join(proj, ".harness", "state.yaml")
    if os.path.isfile(state):
        return 0  # live SOT exists — never clobber (single-writer)
    gpath = os.path.join(proj, ".harness", "graph.json")
    if not os.path.isfile(gpath):
        return 0  # no contract to seed from (advisory)
    try:
        graph = json.load(open(gpath, encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    os.makedirs(os.path.dirname(state), exist_ok=True)
    tmp = state + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(seed_yaml(estimate_max_spawns(graph)))
    os.replace(tmp, state)
    return 0


def _selftest():
    cases = [
        ({"nodes": [{"decision_mechanism": "single"}]}, 1, "single node"),
        ({"nodes": [{"decision_mechanism": "majority-vote", "mechanism_params": {"n": 5}}]}, 5, "majority n=5"),
        ({"nodes": [{"decision_mechanism": "debate-with-judge", "mechanism_params": {"n": 2}}]}, 3, "debate 2+judge"),
        ({"nodes": [{"decision_mechanism": "single", "review": {"agent": "reviewer"}}]}, 2, "single+review"),
        ({"nodes": [{"decision_mechanism": "single"}, {"decision_mechanism": "single"}]}, 2, "two singles"),
        ({"nodes": []}, 1, "empty -> floor 1"),
    ]
    failed = 0
    for g, want, desc in cases:
        got = estimate_max_spawns(g)
        ok = got == want
        failed += 0 if ok else 1
        print("%s %-22s got=%d want=%d" % ("ok " if ok else "FAIL", desc, got, want))
    # seed shape sanity
    y = seed_yaml(8)
    shape_ok = "spawns_used: 0" in y and "max_spawns: 8" in y and "current_step: 0" in y
    failed += 0 if shape_ok else 1
    print("%s seed_yaml shape" % ("ok " if shape_ok else "FAIL"))
    print("\n%d/%d passed" % (len(cases) + 1 - failed, len(cases) + 1))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(run())
