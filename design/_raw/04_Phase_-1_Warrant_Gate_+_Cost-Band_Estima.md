# Phase -1 Warrant Gate + Cost-Band Estimator (warrant.py)

## PURPOSE
The "do you even need a harness?" off-ramp that runs BEFORE any generation/execution. Closes original-harness weakness W12 (no warrant gate → trivial tasks over-engineered into multi-agent teams). It does two deterministic things from a single user request: (1) CLASSIFY the request into exactly one of {answer-directly, single-agent, build-harness(topology, decision_mechanism)} via concrete predicates, and (2) PREVIEW cost as a band for BOTH the run (sum over graph.json nodes of tier_unit * expected_calls * mechanism_multiplier) AND the eval (lift gate + optional head-to-head), so budget.approval_required can be satisfied with a real number before a single agent() spawns. It is the producer of the budget.total figure and the topology/decision_mechanism suggestions that the rest of the pipeline (graph.json author, workflow.js emitter) consume. It is a pure, deterministic, stdlib-only Python module — NOT an agent — so it is free, repeatable, and cannot itself blow budget.

## CONTRACT
## warrant.py — interface (pure Python 3.8+, stdlib only, NO agent calls, NO wall-clock/RNG)

```python
# ============ INPUT ============
# Five predicates are extracted ONCE by the master LLM turn that invokes the gate
# (LLM is the only thing that can read prose; the gate itself is deterministic given these).
# The LLM fills WarrantInput; warrant.py does the rest with zero further model calls.

@dataclass
class WarrantInput:
    request: str                          # raw user request, verbatim (for the record/MANIFEST)
    distinct_expertise_domains: int       # >=1. count of separable skill areas (e.g. web-search, fact-verification, synthesis = 3)
    dependent_or_parallel_stages: int     # >=1. count of stages that must be ordered (pipeline) OR fanned (dispatch). 1 = atomic.
    will_be_rerun: bool                   # will this be invoked repeatedly / as a reusable skill? (amortizes harness build cost)
    objective_vs_subjective: str          # "objective" (single ground truth) | "subjective" (defensible-judgment) | "mixed"
    noisy: bool                           # is any single model call known-unreliable for this (extraction/classification/recall)?
    expected_output_tokens: int = 4000    # rough size of the FINAL artifact, for run-cost scaling

# ============ CONFIG (all hypothesis values; flagged; live in warrant_config.py) ============
MAX_FANOUT = 5                # D-5: integrator synthesis ceiling (HYPOTHESIS)
MAX_VOTERS = 5               # odd, D-5
LIFT_GATE = 0.20            # skill-unit lift threshold (HYPOTHESIS)
HEADTOHEAD_MARGIN = 0.15   # +15%p win condition (HYPOTHESIS)

# Per-tier unit cost = blended $ per expected single agent() call (input+output), HYPOTHESIS values.
# Calibrate from SubagentStop token logs (M0 success-criterion infra) then freeze per release.
TIER_UNIT_USD = {            # $ per typical call; flagged HYPOTHESIS
    "haiku":  0.004,
    "sonnet": 0.030,
    "opus":   0.150,
}
# default role->tier map (D-3), used when a node omits model:
ROLE_TIER = {
    "gather":"haiku","extract":"haiku","format":"haiku","qa-scan":"haiku",
    "voter":"haiku","debater":"sonnet","critic":"opus","reviser":"sonnet",
    "synthesis":"opus","judge":"opus","reviewer":"opus","architect":"opus",
}

# ============ OUTPUT (deterministic; written to _workspace/-1_warrant/warrant.json) ============
@dataclass
class WarrantVerdict:
    decision: str                 # "answer-directly" | "single-agent" | "build-harness"
    rationale: list[str]          # which predicate(s) fired, in plain text (audit trail)
    # populated only when decision == "build-harness":
    topology: str | None          # "pipeline" | "dispatch" | "producer-reviewer"   -> graph.json.topology
    decision_mechanism: str | None# "single"|"majority-vote"|"debate-with-judge"|"reflect-then-revise" -> per-node default
    n_agents: int | None          # min(distinct_expertise_domains, MAX_FANOUT)     -> team SIZE / fan width
    over_cap_warning: str | None  # set iff distinct_expertise_domains > MAX_FANOUT
    cost: CostBand                # always present

@dataclass
class CostBand:
    run_low_usd: float
    run_high_usd: float
    eval_low_usd: float
    eval_high_usd: float
    total_low_usd: float          # run+eval
    total_high_usd: float
    assumed_total_tokens: int     # -> proposed graph.json.budget.total_tokens (run_high converted via $→tok)
    breakdown: list[dict]         # per-node: {id, tier, expected_calls, mechanism, multiplier, low, high}
    flagged_hypothesis: bool = True

# ============ DECISION RULE (exact predicate ladder; FIRST match wins) ============
def classify(w: WarrantInput) -> str:
    # R0 answer-directly: nothing a harness buys you.
    if (w.distinct_expertise_domains <= 1
            and w.dependent_or_parallel_stages <= 1
            and not w.will_be_rerun
            and not w.noisy):
        return "answer-directly"
    # R1 single-agent: one domain, atomic, but worth a dedicated focused pass
    #   (re-run reuse OR noisy-needs-care) yet NOT multi-domain/multi-stage.
    if (w.distinct_expertise_domains <= 1
            and w.dependent_or_parallel_stages <= 1):
        return "single-agent"
    # R2 build-harness: >1 domain OR >1 ordered/parallel stage.
    return "build-harness"

# ============ TOPOLOGY + MECHANISM SUGGESTION (only when build-harness) ============
def suggest_topology(w) -> str:
    if w.dependent_or_parallel_stages >= 2 and w.distinct_expertise_domains >= 2:
        return "pipeline"        # ordered, multi-domain
    if w.distinct_expertise_domains >= 2 and w.dependent_or_parallel_stages == 1:
        return "dispatch"        # static fan-out, single stage, independent experts
    return "producer-reviewer"   # repeated improve loop (1 domain but multi-stage refinement)

def suggest_mechanism(w) -> str:
    if w.noisy and w.objective_vs_subjective == "objective":
        return "majority-vote"        # known answer, unreliable single call  (D-4)
    if w.objective_vs_subjective == "subjective":
        return "debate-with-judge"    # contested/judgment              (D-4)
    if w.topology == "producer-reviewer" or (w.dependent_or_parallel_stages >= 2 and not w.noisy):
        return "reflect-then-revise"  # single artifact iterated         (D-4)
    return "single"

# ============ TEAM SIZE (D-5) ============
def team_size(w):
    n = min(w.distinct_expertise_domains, MAX_FANOUT)
    warn = None
    if w.distinct_expertise_domains > MAX_FANOUT:
        warn = (f"fan-out width {w.distinct_expertise_domains} exceeds integrator "
                f"synthesis ceiling MAX_FANOUT={MAX_FANOUT}; group domains or use "
                f"2-stage synthesis. Capped to {MAX_FANOUT}.")
    return n, warn

# ============ COST-BAND FORMULA (the load-bearing math) ============
# mechanism_multiplier = number of billable agent() calls a node's logical step costs:
#   single             -> 1
#   majority-vote(N)   -> N                       (N parallel voters; reduce is deterministic, $0)
#   debate-with-judge  -> n_debaters*rounds + 1   (+1 = the opus judge)
#   reflect-then-revise-> 2*rounds                (critic + reviser per round)
def mechanism_multiplier(mech, *, n=3, rounds=2, n_debaters=2) -> int:
    return {
        "single": 1,
        "majority-vote": n,
        "debate-with-judge": n_debaters*rounds + 1,
        "reflect-then-revise": 2*rounds,
    }[mech]

# RUN cost = sum over graph.json.nodes of:
#   tier_unit(node.model or ROLE_TIER[role]) * expected_calls(node) * mechanism_multiplier(node.decision_mechanism)
#   where expected_calls(node) accounts for fan width (dispatch node = n_agents calls) and node.retries (+/-).
# LOW band  = base estimate * 0.6   (cache hits, short answers, no retries)
# HIGH band = base estimate * 1.8   (retries fire, long outputs, max_rounds hit)
def run_cost(nodes, *, lo=0.6, hi=1.8) -> tuple[float,float,list]:
    breakdown=[]; base=0.0
    for nd in nodes:
        tier = nd.get("model") or ROLE_TIER.get(nd["agent"], "sonnet")
        unit = TIER_UNIT_USD[tier]
        mp   = mechanism_multiplier(nd["decision_mechanism"], **nd.get("mechanism_params_norm",{}))
        ec   = nd.get("expected_calls", 1) * (1 + nd.get("retries",0)*0.5)
        cell = unit*ec*mp
        base += cell
        breakdown.append({"id":nd["id"],"tier":tier,"expected_calls":ec,
                          "mechanism":nd["decision_mechanism"],"multiplier":mp,
                          "low":round(cell*lo,4),"high":round(cell*hi,4)})
    return base*lo, base*hi, breakdown

# EVAL cost = lift gate (always) + head-to-head (optional, release-only).
#   lift gate (skill-unit, D-2/5a): with-skill(sonnet) vs baseline(haiku), single discriminating fixture, n_eval runs.
#       lift_cost = (TIER_UNIT_USD['sonnet'] + TIER_UNIT_USD['haiku']) * n_eval
#   head-to-head (D-9, 3-way C1 orig / C2 CYS / C3 no-harness), only if include_h2h:
#       h2h_cost = run_high_band(C2) * 3 (three arms, same scale) * n_runs + grader_cost
#       grader_cost = TIER_UNIT_USD['opus'] * n_assertions_graded
def eval_cost(run_hi, *, n_eval=3, include_h2h=False, n_runs=3,
              n_assertions=10) -> tuple[float,float]:
    lift = (TIER_UNIT_USD["sonnet"]+TIER_UNIT_USD["haiku"])*n_eval
    if not include_h2h:
        return lift*0.6, lift*1.8
    h2h = run_hi*3*n_runs + TIER_UNIT_USD["opus"]*n_assertions*n_runs
    return (lift+h2h)*0.6, (lift+h2h)*1.8

# assumed_total_tokens for graph.json.budget.total_tokens:
#   convert run_high_usd back to tokens at a blended $/Mtok (HYPOTHESIS, e.g. $5/Mtok) and round up to 50k.
def usd_to_budget_tokens(run_high_usd, blended_usd_per_mtok=5.0) -> int:
    raw = run_high_usd / blended_usd_per_mtok * 1_000_000
    return int(math.ceil(raw/50_000)*50_000)
```

### Approval gate (satisfies graph.json.budget.approval_required)
The gate PRINTS the CostBand and BLOCKS: generation/run proceeds only on explicit user "approve". This is the ONLY feasible budget control point that is both deterministic and pre-flight (per platform fact #3: no live token-abort hook). The in-run hard ceiling is the separate workflow.js `budget.total` throw; warrant.py merely SETS that number. Post-hoc per-session token truth comes from SubagentStop logs and is used to recalibrate TIER_UNIT_USD between releases.

## DEEP-RESEARCH INSTANCE
## Deep-research M0 dogfood — concrete instantiation

DOGFOOD REQUEST (anchored to the registered deep-research skill: "fan-out web searches → fetch sources → adversarially verify claims → synthesize a cited report"):
> "Research the current state of durable-execution / checkpoint-resume support across agent-orchestration frameworks (LangGraph, Temporal-for-agents, OpenAI Agents SDK, CrewAI) and produce a cited comparison of what each actually persists and resumes."

### Predicate extraction (WarrantInput)
```json
{
  "request": "<above>",
  "distinct_expertise_domains": 3,        // (1) web-search/gather, (2) adversarial fact-verification, (3) synthesis-with-citation
  "dependent_or_parallel_stages": 3,      // gather -> verify -> synthesize, strictly ordered = pipeline
  "will_be_rerun": true,                  // it's a registered reusable skill
  "objective_vs_subjective": "mixed",     // facts are objective; the comparison framing is judgment
  "noisy": true,                          // single-pass web recall + claim verification is unreliable
  "expected_output_tokens": 6000
}
```

### Verdict (deterministic output)
```json
{
  "decision": "build-harness",            // R2: 3 domains > 1 AND 3 stages > 1
  "rationale": [
    "distinct_expertise_domains=3 (>1) -> multi-domain",
    "dependent_or_parallel_stages=3 (>1, ordered) -> pipeline topology",
    "noisy=true on objective sub-task -> verify node gets majority-vote",
    "mixed/iterative final artifact -> synthesis node gets reflect-then-revise"
  ],
  "topology": "pipeline",                 // -> graph.json.topology = "pipeline"
  "decision_mechanism": "reflect-then-revise",  // node-level overrides below; this is the harness DEFAULT
  "n_agents": 3,                          // min(3, MAX_FANOUT=5); no over-cap warning
  "over_cap_warning": null
}
```
This MATCHES the spine example: execution_mode="workflow", topology="pipeline". It maps to a 3-node pipeline:
- node `gather` : model=haiku, decision_mechanism="single" (or majority-vote if recall noisy), fan width = up to 5 search threads
- node `verify`: model=sonnet voters, decision_mechanism="majority-vote", mechanism_params {n:3, quorum:2}
- node `synthesize`: model=opus, decision_mechanism="reflect-then-revise", mechanism_params {max_rounds:2, critic:"opus"}

### Cost-band (HYPOTHESIS units flagged)
```
RUN breakdown (per node, base * [0.6,1.8]):
  gather (haiku, single, fan=5 search calls):  0.004 * 5      * 1            = $0.020 base
  verify (sonnet voters, majority-vote n=3):   0.030 * 1      * 3            = $0.090 base
  synthesize (opus, reflect rounds=2):         0.150 * 1      * (2*2=4)      = $0.600 base
  RUN base = $0.710  ->  run_low $0.43   run_high $1.28
EVAL:
  lift gate (sonnet+haiku, n_eval=3):          (0.030+0.004)*3 = $0.102 base -> $0.06 / $0.18
  head-to-head OFF for routine runs (release-only): when ON,
     h2h = run_high($1.28)*3 arms*3 runs + opus*10 assertions*3 = $11.52 + $4.50 = $16.02 base
TOTAL (routine, h2h OFF): low $0.49   high $1.46
TOTAL (release, h2h ON):  low ~$10.5  high ~$31.5
assumed_total_tokens (run_high $1.28 @ $5/Mtok, ceil 50k) = 300,000
```
NOTE the spine example sets budget.total_tokens=600000 (2 runs of headroom); the gate's computed 300k is the single-run floor, doubled to 600k for retry/variance headroom — that is the number written into graph.json.budget.total_tokens and enforced by workflow.js `budget.total`. approval_required=true => this band is shown and must be approved before the first agent() spawns.

## READS
['_workspace/00_input/query.md (the raw user request, for the predicate-extraction LLM turn and the audit record)', 'warrant_config.py (MAX_FANOUT, LIFT_GATE, HEADTOHEAD_MARGIN, TIER_UNIT_USD, ROLE_TIER — all HYPOTHESIS values, frozen per release)', 'graph.json (when a draft graph already exists, run_cost() iterates its .nodes for the precise per-node band; reads .topology, .budget for round-trip consistency check)']

## WRITES
['_workspace/-1_warrant/warrant.json (the WarrantVerdict + CostBand — the audit artifact the next phase reads)', 'proposes graph.json.budget.total_tokens (assumed_total_tokens) and graph.json.topology + per-node decision_mechanism defaults (consumed by the graph.json author component, NOT written directly to avoid two writers of the spine)', 'stdout: the human-readable cost band + BLOCKING approval prompt (satisfies budget.approval_required)']

## EDGE CASES
- distinct_expertise_domains <= 0: clamp to 1, log bad input
- distinct_expertise_domains > MAX_FANOUT: cap n_agents to 5, set over_cap_warning, recommend 2-stage synthesis (adds one opus integrator call to cost)
- will_be_rerun=true + single-domain + atomic: stays single-agent (R1); reuse justifies skill packaging, not multi-agent topology
- objective_vs_subjective='mixed': biases toward reflect-then-revise unless noisy+objective (then majority-vote)
- existing graph.json budget.total_tokens disagrees with gate by >2x: emit consistency warning, never silently overwrite (single-writer rule for the spine)
- node missing model: field -> ROLE_TIER fallback by role; unknown role -> 'sonnet' + flag
- include_h2h=true on routine run: ~20x cost, label release-only, require second explicit confirmation
- Workflow resume (resumeFromRunId): band is cold-run upper bound; cached agent() prefixes are free, actual spend lower — annotate band accordingly

## FEASIBILITY
Maps cleanly to REAL primitives. (1) warrant.py is plain stdlib Python invoked by the master in a normal bash step BEFORE any agent()/Workflow call — it is NOT an agent, costs $0, is 100% deterministic and resume-safe (no wall-clock/RNG, per Workflow API constraint). (2) The approval gate is the ONLY pre-flight budget control the platform actually supports: platform fact #3 rules out a live token-abort hook, so we use exactly the two feasible mechanisms — (a) pre-flight cost estimate + human approval (this component) and (b) post-hoc per-session token reporting via SubagentStop (separate component, feeds TIER_UNIT_USD recalibration). (3) The number this gate produces flows into workflow.js `budget.total`, which IS a real hard ceiling (agent() THROWS past it) — so the estimate is backed by a real runtime guard, not just advisory prose. (4) mechanism_multiplier maps 1:1 to the spine's decision_mechanism -> workflow.js expansion (majority-vote=parallel(N), debate=loop n*rounds + judge agent(), reflect=loop 2*rounds), so the cost math and the emitted code share one source of truth. (5) topology suggestion maps to the spine's topology field which the emitter turns into pipeline()/parallel()/loop. CONSTRAINTS RESPECTED: does not rename any spine field (only ADDS warrant.json + proposes budget.total_tokens/topology); does not attempt team scheduling (gate is mode-agnostic, defaults execution_mode=workflow per M0 decision); TIER_UNIT_USD and all thresholds are explicitly flagged HYPOTHESIS and isolated in warrant_config.py for per-release recalibration from real SubagentStop logs — honoring the strategy's "claim discipline" (no unbacked numbers shipped as fact).

## OPEN QUESTIONS
- TIER_UNIT_USD values are pure HYPOTHESIS ($0.004/$0.030/$0.150 per call) — must be calibrated from real SubagentStop token logs in the first M0 deep-research run before any cost band is trusted. What blended $/call do haiku/sonnet/opus actually hit on this workload?
- LOW/HIGH band factors (0.6 / 1.8) are guessed — validate against observed run variance; deep-research's web-fetch step has high external-latency-driven retry variance that may push HIGH past 1.8x.
- Should expected_calls for a fan-out gather node be the n_agents width (up to 5) or the actual number of search queries (often >5)? The dogfood assumes fan=5 search calls = n_agents, but real deep-research may issue 10-20 queries inside one gather agent — does that count as 1 agent() call (cheap) or N (expensive)? Resolve by measuring whether gather is one agent doing many WebSearch tool calls (1 agent() = 1 billing unit) vs parallel(N) search subagents.
- Is the 5-predicate set sufficient, or is a 6th predicate 'external_tool_dependency' (MCP/web availability) needed to bump trivial-looking requests up to single-agent? Defer until counterexamples appear in dogfood.
- budget.total_tokens doubling (300k single-run -> 600k spine value) for retry headroom: is 2x the right multiplier, or should it be 1 + (sum of node.retries weighting)? Tie to actual retry-fire rate from logs.