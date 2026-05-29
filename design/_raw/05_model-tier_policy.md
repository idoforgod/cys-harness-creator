# model-tier policy

## PURPOSE
Deterministically decide which Claude model tier (haiku/sonnet/opus) each graph.json node runs at, so cost is controlled and quality is matched to cognitive load. It owns: (1) the role->tier DEFAULT MAP that fills node.model when a designer leaves it blank, (2) the per-agent-file frontmatter contract (model: field + 1-line model_rationale: justification), (3) the per-tier relative cost weights consumed by the cost-estimator component to produce the pre-flight band gated by budget.approval_required, and (4) two validator rules (flag opus on pure-retrieval roles; flag missing model). Anchored on the deep-research M0 dogfood (researcher/verifier/synthesizer/reporter).

## CONTRACT
## 1. Role -> tier DEFAULT MAP (the single source of truth)

```js
// model-tier-policy.js  (consumed by validator + generator + cost-estimator)
// Tier per ROLE-CLASS. The "role-class" is derived from a node's function,
// NOT a free string. node.agent + node.decision_mechanism + mechanism_params
// resolve to exactly one role-class below.

export const TIER_BY_ROLE_CLASS = {
  // --- pure-retrieval / mechanical transforms -> haiku ---
  "gather":   "haiku",   // web/file fetch, no judgment
  "extract":  "haiku",   // pull fields from fetched text into schema
  "format":   "haiku",   // serialize/markdown render, deterministic shape
  "qa-scan":  "haiku",   // checklist/regex-style pass, boolean-ish output

  // --- bounded reasoning within a fixed frame -> sonnet ---
  "voter":    "sonnet",  // one ballot in majority-vote
  "debater":  "sonnet",  // one side in debate-with-judge
  "reviser":  "sonnet",  // applies critic notes in reflect-then-revise

  // --- open-ended synthesis / final judgment -> opus ---
  "synthesis":    "opus",
  "judge":        "opus",  // debate-with-judge judge
  "critic":       "opus",  // reflect-then-revise critic
  "architecture": "opus"   // harness-design / planning roles
};

export const PURE_RETRIEVAL_ROLE_CLASSES = ["gather","extract","format","qa-scan"];
export const VALID_TIERS = ["haiku","sonnet","opus"];

// Maps a graph.json node -> its role-class.
// Decision mechanism overrides the base role for the spawned sub-roles.
export function roleClassOf(node) {
  switch (node.decision_mechanism) {
    case "majority-vote":      return "voter";   // each parallel() voter
    case "debate-with-judge":  return "debater"; // debaters; judge handled separately
    case "reflect-then-revise":return "reviser"; // reviser; critic handled separately
    case "single":
    default:                   return baseRoleClass(node.id, node.agent);
  }
}
// Sub-roles that a mechanism spawns at a DIFFERENT tier than the node default:
//   debate-with-judge -> mechanism_params.judge   (default "opus")
//   reflect-then-revise -> mechanism_params.critic (default "opus")
// The generator reads these param fields; policy default for both = "opus".

// baseRoleClass: keyword-match node.id/agent to a role-class; fallback "synthesis"
// (fail SAFE-EXPENSIVE -> opus -> so an unmapped role is never silently cheap-and-wrong;
//  validator then forces the designer to set model explicitly).
export function baseRoleClass(id, agent) {
  const s = (id + " " + agent).toLowerCase();
  if (/gather|fetch|search|retriev|collect|scan-src/.test(s)) return "gather";
  if (/extract|parse|pull/.test(s))                           return "extract";
  if (/format|render|serialize|report|writer|publish/.test(s))return "format";
  if (/qa|lint|check|verify|valid/.test(s))                   return "qa-scan";
  if (/synth|aggregate|merge|conclude/.test(s))               return "synthesis";
  if (/judge|arbiter/.test(s))                                return "judge";
  if (/critic|review/.test(s))                                return "critic";
  if (/architect|plan|design/.test(s))                        return "architecture";
  return "synthesis"; // unmapped -> opus default, must be confirmed by designer
}

// FILL: applied at generation time to any node with node.model === "" | undefined
export function resolveModel(node) {
  if (node.model && VALID_TIERS.includes(node.model)) return node.model; // explicit wins
  return TIER_BY_ROLE_CLASS[roleClassOf(node)];
}
```

NOTE on `reporter` nuance: a node whose role is "format/report" (deterministic markdown render of an already-synthesized object) is **haiku**. A node that *writes the narrative report by reasoning over raw findings* is a **synthesis** role -> **opus**. The deep-research `reporter` is the former (renders synthesizer output) -> see table row.

## 2. Agent-frontmatter contract (added/required fields)

Real Claude Code agent files (`.claude/agents/<name>.md`) already use YAML frontmatter with `model:`. This component MANDATES two fields:

```yaml
---
name: researcher
description: <existing>
tools: WebSearch, WebFetch, Read, Write
model: haiku                 # REQUIRED. one of haiku|sonnet|opus. MUST equal resolveModel() for every graph.json node that references this agent.
model_rationale: "Pure web/file retrieval, no cross-source judgment — cheapest tier."   # REQUIRED. <=120 chars, one line.
---
```

- `model:` REQUIRED, enum `haiku|sonnet|opus`. This is the real CC frontmatter key (confirmed in existing agents).
- `model_rationale:` REQUIRED new field, single line <=120 chars, states WHY this tier (load justification). Not consumed by runtime; consumed by validator (presence check) and human review.
- graph.json `node.model` is authoritative for the *run*; the agent file `model:` is the *default when invoked outside a graph*. Validator rule V3 enforces they agree.

## 3. Per-tier relative cost weights (cost-estimator input)

Relative weight = blended $/token (input+output mix ~3:1) normalized so haiku = 1.0. Derived from public Claude pricing ratios (Haiku:Sonnet:Opus ≈ 1 : 4 : 20 blended), rounded to stable integers for deterministic estimates (no RNG, no wall-clock — required by Workflow constraints).

```js
export const TIER_COST_WEIGHT = { haiku: 1, sonnet: 4, opus: 20 };

// Pre-flight estimate (Mode A pre-run band, gates budget.approval_required):
// estTokens(node) = node.expected_tokens (designer hint, default 8000)
//                 * fanout(node)          // majority-vote n; debate 2*max_rounds+1; reflect 2*max_rounds; single=1
//                 * (node.retries + 1)
// weightedCost   = Σ_nodes estTokens(node) * TIER_COST_WEIGHT[resolveModel(node)]
// Convert to a coarse BAND for approval (not a false-precision number):
export function costBand(weightedUnits) {
  if (weightedUnits < 5e5)  return "LOW";      // shown green
  if (weightedUnits < 5e6)  return "MEDIUM";
  return "HIGH";                                // shown red, stronger approval copy
}
// HARD ceiling is enforced separately by workflow.js budget.total (token count),
// per Workflow API. This weight model is for the PRE-FLIGHT human-approval band only.
```

## 4. Validator rules (this component owns 2)

```js
// V1: missing/invalid model on a node OR agent file.
function v1_missingModel(node, agentFile) {
  const errs = [];
  if (!node.model || !VALID_TIERS.includes(node.model))
    errs.push({code:"TIER_MISSING", level:"error",
      msg:`node "${node.id}".model is empty/invalid; resolveModel default = "${TIER_BY_ROLE_CLASS[roleClassOf(node)]}" — set it explicitly.`});
  if (agentFile && (!agentFile.model || !VALID_TIERS.includes(agentFile.model)))
    errs.push({code:"AGENT_TIER_MISSING", level:"error",
      msg:`agent "${node.agent}" frontmatter missing model:`});
  if (agentFile && !agentFile.model_rationale)
    errs.push({code:"RATIONALE_MISSING", level:"error",
      msg:`agent "${node.agent}" missing model_rationale:`});
  return errs;
}

// V2: opus on a pure-retrieval role -> flag.
function v2_opusOnRetrieval(node) {
  if (node.model === "opus" && PURE_RETRIEVAL_ROLE_CLASSES.includes(roleClassOf(node)))
    return [{code:"TIER_OVERSPEND", level:"warn",
      msg:`node "${node.id}" is role-class "${roleClassOf(node)}" (pure retrieval) but model=opus. Downgrade to haiku unless justified in node.tier_override_reason.`}];
  return [];
}
// Escape hatch: warn (not hard error) IF node.tier_override_reason is a non-empty string; else error.
// V3 (consistency): node.model must equal agentFile.model -> else error TIER_MISMATCH.
```

## 5. Optional ADDED graph.json fields (justified, no spine renames)

- `node.expected_tokens` (int, default 8000) — cost-estimator input.
- `node.tier_override_reason` (string) — required to silence V2 when opus is intentional on a cheap role; turns the error into a warn.
These ADD to the spine; they do not rename `model`, `decision_mechanism`, `mechanism_params`, `retries`, `budget`.

## DEEP-RESEARCH INSTANCE
Concrete assignment table for the deep-research M0 harness (graph.json nodes -> agents -> tier). topology=pipeline, execution_mode=workflow.

| graph node id | node.agent | role-class | decision_mechanism | resolveModel() -> node.model | TIER_COST_WEIGHT | model_rationale (frontmatter) |
|---|---|---|---|---|---|---|
| gather | researcher | gather | single | haiku | 1 | "Pure web/file retrieval, no cross-source judgment — cheapest tier." |
| verify | verifier | voter | majority-vote {n:3,quorum:2} | sonnet (x3 voters) | 4 each | "Bounded adversarial claim-check within a fixed rubric — mid tier." |
| synthesize | synthesizer | synthesis | single | opus | 20 | "Open-ended cross-source synthesis + narrative reasoning — top tier." |
| report | reporter | format | single | haiku | 1 | "Deterministic markdown render of synthesizer's structured output — cheapest tier." |

Mechanism sub-role tiers for `verify` (majority-vote): 3 voter agent() calls at sonnet inside parallel(), then a deterministic JS reduce (quorum=2) — the reduce is code, NOT an agent, so $0 model cost. If deep-research instead used debate-with-judge on synthesize, the judge sub-role would default to opus (mechanism_params.judge="opus"), debaters sonnet.

Worked pre-flight estimate (expected_tokens default 8000, retries from spine row example):
- gather: 8000 * 1 fanout * (1+1 retry) * weight 1 = 16,000 units
- verify: 8000 * 3 fanout * (1+0) * weight 4 = 96,000 units
- synthesize: 8000 * 1 * (1+0) * weight 20 = 160,000 units
- report: 8000 * 1 * (1+0) * weight 1 = 8,000 units
- TOTAL ≈ 280,000 weighted units -> costBand("LOW") -> green approval card.
This pre-flight band is shown because graph.json budget.approval_required=true. Separately, workflow.js sets budget.total = graph.budget.total_tokens (600000) as the HARD runtime ceiling per Workflow API.

V2 self-check on this instance: gather & report are haiku (pass), verify sonnet (pass), synthesize opus on role-class "synthesis" (NOT pure-retrieval, pass). No TIER_OVERSPEND. All four agents carry model + model_rationale -> V1/V3 pass.

## READS
['graph.json', '.claude/agents/researcher.md', '.claude/agents/verifier.md', '.claude/agents/synthesizer.md', '.claude/agents/reporter.md']

## WRITES
['model-tier-policy.js', 'graph.json (node.model fill)', 'validator findings stream']

## EDGE CASES
- unmapped role -> opus + forced explicit (V1)
- majority-vote reduce is code, zero model cost
- judge/critic tier from mechanism_params not node default
- intentional opus on cheap role needs tier_override_reason
- explicit node.model always wins
- reporter haiku only if rendering not reasoning
- agent vs node model mismatch -> V3 error
- weights are relative integers, resume-safe

## FEASIBILITY
Maps cleanly to REAL primitives: (1) node.model -> agent({model:'haiku'|'sonnet'|'opus'}) in workflow.js (Mode A) — the only tiers the Workflow agent() opt accepts. (2) Agent-file model:/model_rationale: are plain YAML frontmatter keys; model: is confirmed present in existing real .claude/agents/*.md (e.g. topic-researcher.md model: sonnet) — model_rationale: is a new sidecar key, harmless to the runtime (CC ignores unknown frontmatter keys), used only by validator + humans. (3) Cost weights feed the PRE-FLIGHT estimate + approval card — the ONLY feasible budget gate per constraint #3 (no live cross-session token-abort hook exists). The HARD ceiling is the Workflow budget.total token guard (constraint #6), which is real and orthogonal to this weight model; post-hoc per-session actuals come via SubagentStop (constraint #3b), not from this component. (4) Everything is deterministic: roleClassOf/resolveModel/costBand are pure functions of graph.json — no RNG, no current-time, so they are resume-safe and reproducible across Workflow re-runs (constraint on RNG/wall-clock). CONSTRAINT acknowledged: in Mode B (team) the policy can only ADVISE tier in the agent prompt — TeamCreate/Agent spawns cannot be deterministically tiered by an external driver (constraint #1); Mode A (Workflow) is where this policy is enforceable, which is why M0 spine defaults execution_mode=workflow.

## OPEN QUESTIONS
- Should reflect-then-revise's critic default be opus (current spec) or sonnet to save cost when revisions are minor? Proposed: opus default, allow mechanism_params.critic='sonnet' override.
- Should TIER_COST_WEIGHT track 1M-context surcharge tiers (e.g. opus[1m]) as a separate weight? M0 ignores context-length surcharge; flag if deep-research inputs exceed 200k.
- Is node.expected_tokens worth designer burden, or should the estimator use a fixed per-tier default (haiku 6k / sonnet 8k / opus 12k)? Leaning toward per-tier default to reduce required fields.
- Confirm with master whether model_rationale should be a hard error (current) or warn in M0 to reduce friction on the first dogfood.