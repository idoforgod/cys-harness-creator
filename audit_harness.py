#!/usr/bin/env python3
"""audit_harness — Phase-0 status audit (M4 / idoforgod Phase 0).

idoforgod's Phase 0 reads an existing harness's .claude/agents, .claude/skills and CLAUDE.md, classifies
the run as new / extend / maintain, and detects DRIFT between the files and the contract. CYS makes that
a DETERMINISTIC artifact: this tool inventories three sources, computes set-diffs, classifies the branch,
and writes .harness/audit.json — so "drift" is a checkable fact, not a prose impression (idoforgod does
it by hand). validate_harness then enforces AUDIT_VERDICT_PRESENT.

CLI: audit_harness.py <harness_dir>   ->   writes <harness_dir>/.harness/audit.json
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "lib"))
from atomic_write import atomic_write  # noqa: E402

# inherited genome agents/skills are NOT domain artifacts — exclude from drift vs the graph.
_GENOME_AGENTS = {"reviewer", "fact-checker", "translator"}
_GENOME_SKILLS = {"workflow-generator", "doctoral-writing", "spec-grounded-workflow"}


def _names(d, suffix):
    if not os.path.isdir(d):
        return set()
    return {f[:-len(suffix)] for f in os.listdir(d) if f.endswith(suffix)}


def inventory(harness_dir):
    """Domain agents/skills on disk (genome + orchestrator excluded) + presence flags."""
    agents = _names(os.path.join(harness_dir, ".claude", "agents"), ".md") - _GENOME_AGENTS
    sdir = os.path.join(harness_dir, ".claude", "skills")
    skills_all = {d for d in (os.listdir(sdir) if os.path.isdir(sdir) else []) if os.path.isdir(os.path.join(sdir, d))}
    skills = {s for s in skills_all if s not in _GENOME_SKILLS and not s.endswith("-orchestrator")}
    return {
        "agents_on_disk": agents,
        "skills_on_disk": skills,
        "has_graph": os.path.isfile(os.path.join(harness_dir, ".harness", "graph.json")),
        "has_claude_md": os.path.isfile(os.path.join(harness_dir, "CLAUDE.md")),
    }


def compute_drift(graph, agents_on_disk, skills_on_disk):
    """Set-diffs between the graph contract and what is on disk. Returns a sorted list of drift items."""
    g = graph or {}
    nodes = g.get("nodes") or []
    # R1 runs at RESEARCH on possibly hand-edited / mid-authoring graphs (BEFORE validate I5), so a node
    # missing agent/id must be SKIPPED (and reported as drift), not crash compute_drift with a raw KeyError.
    agents_in_graph = {n["agent"] for n in nodes if n.get("agent")}
    skills_in_graph = {"%s-%s" % (g.get("harness_name", ""), n["id"])
                       for n in nodes if n.get("id") and (n.get("skill_authoring") or {}).get("mode") == "skill"}
    malformed = [n for n in nodes if not n.get("agent") or not n.get("id")]
    drift = []
    for a in sorted(agents_on_disk - agents_in_graph):
        drift.append({"kind": "agent", "name": a, "issue": "on-disk-not-in-graph (orphan)"})
    for a in sorted(agents_in_graph - agents_on_disk):
        drift.append({"kind": "agent", "name": a, "issue": "in-graph-not-on-disk (missing)"})
    for s in sorted(skills_on_disk - skills_in_graph):
        drift.append({"kind": "skill", "name": s, "issue": "on-disk-not-in-graph (orphan)"})
    for s in sorted(skills_in_graph - skills_on_disk):
        drift.append({"kind": "skill", "name": s, "issue": "in-graph-not-on-disk (missing)"})
    for n in malformed:
        drift.append({"kind": "graph", "name": str(n.get("id") or n.get("agent") or "?"),
                      "issue": "node missing required id/agent (malformed contract)"})
    return drift


def classify_branch(inv, drift):
    """new = no contract and no domain agents; else maintain if drift, extend if clean."""
    if not inv["has_graph"] and not inv["agents_on_disk"]:
        return "new"
    return "maintain" if drift else "extend"


def audit(harness_dir):
    inv = inventory(harness_dir)
    graph = None
    gp = os.path.join(harness_dir, ".harness", "graph.json")
    if os.path.isfile(gp):
        try:
            graph = json.load(open(gp, encoding="utf-8"))
        except (OSError, ValueError):
            graph = None
    drift = compute_drift(graph, inv["agents_on_disk"], inv["skills_on_disk"])
    report = {
        "branch": classify_branch(inv, drift),
        "drift": drift,
        "agents_on_disk": sorted(inv["agents_on_disk"]),
        "skills_on_disk": sorted(inv["skills_on_disk"]),
        "has_graph": inv["has_graph"],
        "has_claude_md": inv["has_claude_md"],
    }
    atomic_write(os.path.join(harness_dir, ".harness", "audit.json"),
                 json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main():
    if len(sys.argv) < 2:
        print("usage: audit_harness.py <harness_dir>", file=sys.stderr); sys.exit(2)
    hd = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.join(hd, ".harness"), exist_ok=True)
    rep = audit(hd)
    print("audit: branch=%s, drift=%d item(s)%s" % (
        rep["branch"], len(rep["drift"]),
        "" if not rep["drift"] else " — " + "; ".join("%s '%s' %s" % (d["kind"], d["name"], d["issue"]) for d in rep["drift"])))


if __name__ == "__main__":
    main()
