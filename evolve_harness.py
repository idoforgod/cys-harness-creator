#!/usr/bin/env python3
"""evolve_harness — Phase-7 harness evolution (M5 / idoforgod Phase 7).

idoforgod treats a harness as a living system: after each run it solicits feedback, ROUTES the feedback
type to the exact artifact to change, logs the change to a CLAUDE.md change-history (regression guard),
and proactively proposes evolution on recurring signals. CYS makes the routing + history a DETERMINISTIC
artifact (idoforgod does it by prose): feedback type -> target artifact via a fixed table, appended to
.harness/change-history.jsonl. The orchestrator's Evolution phase calls this; validate_harness enforces
EVOLUTION_LOG_PRESENT.

CLI: evolve_harness.py <harness_dir> --type <feedback_type> --change "..." --reason "..."
     evolve_harness.py <harness_dir> --proactive        # report recurring-feedback evolution proposals
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "lib"))
from atomic_write import atomic_write  # noqa: E402

# idoforgod Phase 7-2 feedback-routing table: feedback type -> the artifact to change.
_ROUTE = {
    "result-quality": "domain-skill-or-agent-body",   # 산출물 품질 → 그 노드의 how(스킬/agent 본문)
    "agent-role": "agent-def",                         # 에이전트 역할/추가 → .claude/agents/<agent>.md
    "workflow-order": "orchestrator",                  # 워크플로우 순서 → 오케스트레이터 SKILL
    "team-comp": "orchestrator+agents",                # 팀 구성/병합 → 오케스트레이터 + agents
    "trigger-miss": "skill-description",               # 트리거 누락 → 스킬 description
}
_PROACTIVE_THRESHOLD = 2  # same feedback type >= 2x -> propose evolution (idoforgod Phase 7-4)


def route_feedback(feedback_type):
    """Return the target artifact for a feedback type, or None if unknown."""
    return _ROUTE.get(feedback_type)


def _log_path(harness_dir):
    return os.path.join(harness_dir, ".harness", "change-history.jsonl")


def read_history(harness_dir):
    p = _log_path(harness_dir)
    if not os.path.isfile(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def record(harness_dir, date, feedback_type, change, reason):
    """Append one routed change-history entry (append-only). Returns the entry."""
    target = route_feedback(feedback_type)
    if target is None:
        raise ValueError("unknown feedback_type %r (expected one of %s)" % (feedback_type, sorted(_ROUTE)))
    entry = {"date": date, "feedback_type": feedback_type, "target": target, "change": change, "reason": reason}
    p = _log_path(harness_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    prior = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    atomic_write(p, prior + json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def proactive_proposals(history):
    """idoforgod Phase 7-4: feedback type recurring >= threshold -> a proposal to evolve."""
    counts = {}
    for e in history:
        ft = e.get("feedback_type")
        if ft:
            counts[ft] = counts.get(ft, 0) + 1
    return [{"feedback_type": ft, "count": n, "target": route_feedback(ft)}
            for ft, n in sorted(counts.items()) if n >= _PROACTIVE_THRESHOLD]


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: evolve_harness.py <harness_dir> [--type T --change C --reason R | --proactive]", file=sys.stderr)
        sys.exit(2)
    hd = os.path.abspath(args[0])

    def opt(name):
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None

    if "--proactive" in args:
        props = proactive_proposals(read_history(hd))
        if not props:
            print("no recurring feedback (>= %d) — no evolution proposed." % _PROACTIVE_THRESHOLD)
        for p in props:
            print("PROPOSE EVOLUTION: '%s' seen %dx -> change %s" % (p["feedback_type"], p["count"], p["target"]))
        return
    ft = opt("--type")
    if not ft:
        print("specify --type <feedback_type> (one of %s) or --proactive" % sorted(_ROUTE), file=sys.stderr)
        sys.exit(2)
    e = record(hd, opt("--date") or "unknown-date", ft, opt("--change") or "", opt("--reason") or "")
    print("recorded: %s -> %s (%s)" % (e["feedback_type"], e["target"], e["change"]))


if __name__ == "__main__":
    main()
