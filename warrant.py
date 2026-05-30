#!/usr/bin/env python3
"""CYS Harness Creator M0 — Phase -1 warrant gate + token cost-band (SIMPLIFIED).

Pure stdlib, deterministic, NO agent calls, NO wall-clock/RNG. Runs in a plain
bash step BEFORE any generation/run so it is free, repeatable, and resume-safe.

Two deterministic jobs from one user request:
  1. classify()  -> answer-directly | single-agent | build-harness(+topology,mech,n)
  2. cost_band() -> {total_tokens, weighted_units, band, usd_estimate}  (TOKENS unit)

The gate CANNOT read prose. The master LLM turn extracts five predicates ONCE into
a small dict; the gate does the rest with zero further model calls.
"""
import argparse
import json
import os
import sys

# ---- CONSTANTS: single source of truth is constants.json (next to this file). ----
# Values are HYPOTHESIS-grade; recalibrate from SubagentStop token logs post-dogfood.
# TIER_COST_WEIGHT {1,3,5} tracks real 2026 Claude blended pricing (Opus 4.5 was price-cut
# to $5/$25 -> blended ~$10/Mtok vs haiku ~$2 = 5x, sonnet ~$6 = 3x), so weighted_units stays
# proportional to usd_estimate. DISPLAY ONLY; the hard ceiling is graph.budget.total_tokens.
_DEFAULTS = {
    "MAX_FANOUT": 5,
    "EXPECTED_TOKENS_DEFAULT": 8000,
    "TIER_COST_WEIGHT": {"haiku": 1, "sonnet": 3, "opus": 5},
    "TOKENS_PER_USD": {"haiku": 500_000, "sonnet": 166_667, "opus": 100_000},
    "BAND_LOW": 5e5,
    "BAND_MED": 5e6,
    "TEAM_COORD_TOKENS": 4000,   # per-member SendMessage/coordination overhead (team/hybrid only)
}


def _load_constants():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constants.json")
    cfg = dict(_DEFAULTS)
    try:
        with open(path) as f:
            loaded = json.load(f)
        for k in _DEFAULTS:
            if k in loaded:
                cfg[k] = loaded[k]
    except (OSError, ValueError):
        pass  # fall back to _DEFAULTS (resume-safe, no hard dependency)
    return cfg


_C = _load_constants()
MAX_FANOUT = _C["MAX_FANOUT"]
EXPECTED_TOKENS_DEFAULT = _C["EXPECTED_TOKENS_DEFAULT"]
TIER_COST_WEIGHT = _C["TIER_COST_WEIGHT"]
TOKENS_PER_USD = _C["TOKENS_PER_USD"]
BAND_LOW, BAND_MED = _C["BAND_LOW"], _C["BAND_MED"]
TEAM_COORD_TOKENS = _C["TEAM_COORD_TOKENS"]


def _fanout(node):
    """Billable agent() calls a node's logical step costs (mechanism multiplier)."""
    mech = node.get("decision_mechanism", "single")
    mp = node.get("mechanism_params", {})
    rounds = mp.get("max_rounds", node.get("max_rounds", 2))
    if mech == "single":
        return 1
    if mech == "majority-vote":
        return mp.get("n", 3)
    if mech == "debate-with-judge":
        return 2 * rounds + 1
    if mech == "reflect-then-revise":
        return 2 * rounds                      # critic + reviser per round
    return 1


def est_tokens(node):
    """estTokens = expected_tokens * fanout * (retries + 1)."""
    et = node.get("expected_tokens", EXPECTED_TOKENS_DEFAULT)
    return et * _fanout(node) * (node.get("retries", 0) + 1)


def classify(p):
    """SIMPLIFIED Phase -1 off-ramp. p = predicate dict (see __main__ for shape).

    Off-ramp when distinct_expertise_domains < 2 AND no dependent/parallel stages:
      -> single-agent normally; answer-directly only if trivial (not rerun, not noisy,
         objective). Else build-harness.
    """
    domains = max(1, int(p.get("distinct_expertise_domains", 1)))
    staged = bool(p.get("has_dependent_or_parallel_stages", False))
    rerun = bool(p.get("will_be_rerun", False))
    objective = bool(p.get("output_objective", True))
    noisy = bool(p.get("noisy", False))
    warnings = []

    if domains < 2 and not staged:
        if not rerun and not noisy and objective:
            return {"verdict": "answer-directly", "warnings": warnings,
                    "rationale": "1 domain, atomic, not rerun/noisy, objective -> no harness buys anything."}
        return {"verdict": "single-agent", "warnings": warnings,
                "rationale": "1 domain, atomic, but rerun/noisy/subjective -> one dedicated focused pass."}

    n_agents = min(domains, MAX_FANOUT)
    if domains > MAX_FANOUT:
        warnings.append(f"distinct_expertise_domains={domains} exceeds MAX_FANOUT={MAX_FANOUT}; "
                        f"group domains or use 2-stage synthesis. Capped n_agents={MAX_FANOUT}.")
    # topology: ordered/parallel multi-stage -> pipeline; multi-domain single stage -> dispatch;
    # single-domain multi-stage refinement -> producer-reviewer.
    if staged and domains >= 2:
        topology = "pipeline"
    elif domains >= 2:
        topology = "dispatch"
    else:
        topology = "producer-reviewer"
    # default mechanism (FIRST match): subjective -> debate-with-judge;
    # staged/ordered pipeline -> reflect-then-revise (single artifact iterated critic->reviser);
    # single-stage objective+noisy -> majority-vote (parallel voters on a known answer).
    if not objective:
        mech = "debate-with-judge"
    elif staged:
        mech = "reflect-then-revise"
    elif noisy:
        mech = "majority-vote"
    else:
        mech = "single"
    return {"verdict": "build-harness", "topology": topology, "decision_mechanism": mech,
            "n_agents": n_agents, "warnings": warnings,
            "rationale": f"{domains} domain(s) and/or ordered stages -> {topology} / {mech}."}


def cost_band(nodes, execution_mode="agent"):
    """Token cost-band over graph.json nodes. Returns the load-bearing pre-flight number.

    CD-3: under execution_mode team|hybrid the produced harness runs as a peer team whose
    SendMessage/self-coordination traffic is NOT captured by the per-node single-pass formula
    (warrant's known blind spot, == idoforgod's documented multi-session cost weakness). We add
    a first-order coordination term (TEAM_COORD_TOKENS per member, at sonnet weight) so the
    band shown at approval is not systematically under-counted for the team substrate."""
    total_tokens = 0
    weighted = 0
    breakdown = []
    usd = 0.0
    for nd in nodes:
        tier = nd.get("model", "sonnet")
        et = est_tokens(nd)
        wu = et * TIER_COST_WEIGHT.get(tier, TIER_COST_WEIGHT["sonnet"])
        total_tokens += et
        weighted += wu
        usd += et / TOKENS_PER_USD.get(tier, TOKENS_PER_USD["sonnet"])
        breakdown.append({"id": nd.get("id"), "model": tier, "fanout": _fanout(nd),
                          "est_tokens": et, "weighted_units": wu})
    team_coord = 0
    if execution_mode in ("team", "hybrid"):
        team_coord = TEAM_COORD_TOKENS * len(nodes)
        total_tokens += team_coord
        weighted += team_coord * TIER_COST_WEIGHT["sonnet"]
        usd += team_coord / TOKENS_PER_USD["sonnet"]
    band = "LOW" if weighted < BAND_LOW else "MEDIUM" if weighted < BAND_MED else "HIGH"
    return {"total_tokens": total_tokens, "weighted_units": weighted, "band": band,
            "usd_estimate": round(usd, 4), "execution_mode": execution_mode,
            "team_coordination_tokens": team_coord, "breakdown": breakdown}


# ---- CANONICAL deep-research dogfood (matches .harness/graph.json exactly) ----
DEEP_RESEARCH_PREDICATES = {
    "distinct_expertise_domains": 4,            # search / fetch / verify / synthesize
    "has_dependent_or_parallel_stages": True,   # gather->fetch->verify->synthesize, ordered pipeline
    "will_be_rerun": True,                       # registered reusable skill
    "output_objective": True,                    # facts objective; verify is adversarial
    "noisy": True,                               # single-pass web recall/verification unreliable
}
DEEP_RESEARCH_NODES = [
    {"id": "gather", "model": "haiku", "decision_mechanism": "single", "retries": 1},
    {"id": "fetch", "model": "haiku", "decision_mechanism": "single", "retries": 1},
    {"id": "verify", "model": "sonnet", "decision_mechanism": "reflect-then-revise",
     "mechanism_params": {"max_rounds": 2, "critic": "opus"}, "retries": 0},
    {"id": "synthesize", "model": "opus", "decision_mechanism": "single", "retries": 0},
]


def main():
    ap = argparse.ArgumentParser(description="Phase -1 warrant gate + token cost-band")
    ap.add_argument("--predicates", help="JSON file with the 5-key predicate dict")
    ap.add_argument("--graph", help="graph.json whose .nodes feed cost_band (else canonical)")
    args = ap.parse_args()

    if args.predicates:
        with open(args.predicates) as f:
            preds = json.load(f)
    else:
        preds = DEEP_RESEARCH_PREDICATES
    exec_mode = "agent"
    if args.graph:
        with open(args.graph) as f:
            g = json.load(f)
        nodes = g.get("nodes", [])
        exec_mode = g.get("execution_mode", "agent")
    else:
        nodes = DEEP_RESEARCH_NODES

    verdict = classify(preds)
    band = cost_band(nodes, execution_mode=exec_mode)
    out = {"predicates": preds, "verdict": verdict, "cost": band,
           "note": "warrant PROPOSES budget.total_tokens; graph.json is single-writer "
                   "(may double the floor for retry/variance headroom). approval_required=true "
                   "=> show band, BLOCK on explicit 'approve' before first agent() spawns."}
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
