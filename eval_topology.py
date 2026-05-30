#!/usr/bin/env python3
"""eval_topology — the 8-use-case parity matcher (M7 / R2).

The reframed benchmark is FEATURE PARITY with idoforgod: the factory must EMIT a conforming harness for
every idoforgod README use case (Deep Research, Website Dev, Webtoon, YouTube, Code Review, Tech Docs,
Data Pipeline, Marketing). This is the build-level (L-factory) check: given a use-case graph + its emitted
orchestrator SKILL + the expected shape, confirm topology/exec_mode/primitive-mix/DNA all match. (Run-level
h2h is the separate, quota-gated lane.)

match() is pure (graph, skill_text, expected) -> list of mismatches (empty = pass).
CLI: eval_topology.py <harness_dir> <expected.json>
"""
import json
import os
import sys

_TOPO_HDR = {"fan-out-fan-in": "fan-out/fan-in", "supervisor": "supervisor",
             "expert-pool": "expert-pool", "hierarchical": "hierarchical"}


def match(graph, skill_text, expected):
    """Return a list of mismatches (empty => the emitted harness conforms to the expected use-case shape)."""
    m = []
    if graph.get("topology") != expected.get("topology"):
        m.append("topology %r != expected %r" % (graph.get("topology"), expected.get("topology")))
    if graph.get("execution_mode") != expected.get("exec_mode"):
        m.append("exec_mode %r != expected %r" % (graph.get("execution_mode"), expected.get("exec_mode")))
    # all-6 primitive floor (A2): both Agent Teams and Sub-agents present
    if "TeamCreate(" not in skill_text:
        m.append("orchestrator lacks TeamCreate( (A2 all-primitive floor)")
    if "Agent(" not in skill_text:
        m.append("orchestrator lacks Agent( (sub-agent)")
    # mandatory DNA sections (R4 + M5/M6)
    for marker, label in (("메모리 운영", "Context-Preservation memory"),
                          ("교차-실행 도메인 메모리", "Tier-II cross-run memory"),
                          ("진화", "Phase-7 evolution")):
        if marker not in skill_text:
            m.append("missing DNA section: %s" % label)
    # first-class topology recipe (the 4 beyond pipeline/dispatch/producer-reviewer)
    hdr = _TOPO_HDR.get(graph.get("topology"))
    if hdr and ("### 토폴로지: " + hdr) not in skill_text:
        m.append("topology recipe absent for %r" % graph.get("topology"))
    return m


def main():
    if len(sys.argv) < 3:
        print("usage: eval_topology.py <harness_dir> <expected.json>", file=sys.stderr); sys.exit(2)
    hd, ep = os.path.abspath(sys.argv[1]), sys.argv[2]
    graph = json.load(open(os.path.join(hd, ".harness", "graph.json"), encoding="utf-8"))
    expected = json.load(open(ep, encoding="utf-8"))
    sk = os.path.join(hd, ".claude", "skills", graph["harness_name"] + "-orchestrator", "SKILL.md")
    skill_text = open(sk, encoding="utf-8").read() if os.path.isfile(sk) else ""
    mism = match(graph, skill_text, expected)
    if mism:
        print("FAIL (%s): %s" % (expected.get("use_case", "?"), "; ".join(mism)))
        sys.exit(1)
    print("PASS: %s conforms (topology=%s, exec_mode=%s)" % (
        expected.get("use_case", "?"), graph.get("topology"), graph.get("execution_mode")))


if __name__ == "__main__":
    main()
