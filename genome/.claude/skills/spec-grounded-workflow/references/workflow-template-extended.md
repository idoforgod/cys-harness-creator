# Workflow Template — Extended (Spec-Grounded)

Standard workflow.md structure when upstream formal specifications exist.

This template **extends** `workflow-generator/references/workflow-template.md` with 5 NEW per-stage fields and 2 NEW global concerns. The baseline structure (Overview, Inherited DNA core, 3-stage with Verification/Translation/Review, Claude Code Configuration) remains inherited unchanged.

## Extended Template

```markdown
# [Workflow Name]

[One-line workflow purpose]

## Overview

- **Input**: [input data / trigger]
- **Output**: [final deliverable]
- **Frequency**: [execution cadence — daily/weekly/on-demand]
- **Autopilot**: [disabled|enabled] (default: disabled)
- **pACS**: [enabled|disabled] (default: enabled)

---

## Upstream Spec Inventory                                  [NEW — spec-grounded]

> Snapshot of upstream specifications this workflow depends on.

| Document | Path | Version | Anchored ADR |
|---|---|---|---|
| Product Requirements | `<path>` | v<x.y.z> | <ADR-NNN> |
| Functional Spec | `<path>` | v<x.y.z> | <ADR-NNN> |
| Test Plan | `<path>` | v<x.y.z> | <ADR-NNN> |
| Eval Plan | `<path>` | v<x.y.z> | <ADR-NNN> |
| Output Contract | `<path>` | v<x.y.z> | <ADR-NNN> |
| Risk Register | `<path>` | (living) | (cross-cutting) |
| Build-Time Asset Cohort | `<path>` | (versioned per asset) | <Phase 2.5 ADR-NNN equivalent> |
| Cost-Latency Policy | `<path §X.Y>` | (per upstream) | <ADR-NNN> |

### Cascade ADR Pending State

| Pending ADR | Affects | Pre-register before this workflow? |
|---|---|---|
| <ADR-NNN-amendment> | <stage / output structure> | <yes / no — rationale> |

### Cost-Latency Policy Total Budget

- **Per-execution LLM call budget**: <int | range>
- **Per-execution token budget**: <int | range>
- **Latency budget (p95)**: <ms>
- **Rate-limit tier**: <subscription | api_tier | unbounded>

---

## Inherited DNA (Parent Genome)

> This workflow inherits the complete genome of the parent organism (e.g., AgenticWorkflow).

**Constitutional Principles** (adapted to this workflow's domain):

1. **Quality Absolutism** — [domain-specific quality definition]
2. **Single-File SOT** — `.claude/state.yaml` for shared state
3. **Code Change Protocol** — Intent → Impact → Design (3-step) for code changes

**Inherited Patterns**:

| DNA Component | Inherited Form |
|---|---|
| 3-Phase Structure | Research → Planning → Implementation |
| SOT Pattern | `.claude/state.yaml` — single writer (Orchestrator/Team Lead) |
| 4-Layer QA | L0 Anti-Skip → L1 Verification → L1.5 pACS → L2 Adversarial Review |
| P1 Hallucination Prevention | Deterministic validation scripts |
| P2 Expert Delegation | Specialized sub-agents per task |
| Safety Hooks | <e.g., block_destructive_commands.py> |
| Adversarial Review | `@reviewer` + `@fact-checker` |
| Decision Log | `autopilot-logs/` |
| Context Preservation | Snapshot + Knowledge Archive + RLM restoration |

**Domain-Specific Gene Expression**: [DNA components most strongly expressed in this domain]

### Hybrid Architecture Boundary                            [NEW — when applicable]

| Module / Stage | Component | Determinism Class | Implementation Primitive |
|---|---|---|---|
| <name> | <function> | deterministic | <(hook) | Sub-agent rule lookup | Skill | code module> |
| <name> | <function> | probabilistic | <Sub-agent LLM call | Agent Team | MCP server> |

**Rationale**: [upstream spec assigns determinism class per module; integration phase verifies KPI per module]

### Multi-Sample Implementation Pattern                     [NEW — conditional]

> Required IF workflow uses Self-Consistency / multi-sample / ensemble LLM patterns.

- **Pattern**: <Sequential N+1 calls | Agent Team N parallel + Team Lead integration | Hybrid>
- **N**: <integer>
- **Variance source**: <temperature | prompt_variation | seed | ensemble_model_diversity>
- **Integration mechanism**: <T=X.X integration call | majority vote | weighted average | LLM judge | none>
- **Trade-off rationale**: <quality vs throughput vs rate_limit vs cost — explicit choice>
- **Cost impact**: <integrated with cost_budget per affected stage>
- **Failure mode**: <strategy when sample variance exceeds threshold>

---

## Research

### 1. [Stage Name]

- **Pre-processing**: [data preparation — Python script]
- **Agent**: `@<agent-name>`
- **Verification**:
  - [ ] [structural completeness criterion]
  - [ ] [pipeline connection criterion: outputs include fields needed by Step N+1]
  - [ ] [cross-stage traceability criterion: 80%+ claims include `[trace:step-N]` markers]
- **Task**: [task description]
- **Output**: `<output-path>`
- **Translation**: `@translator` → `<output>.ko.md` | none
- **Post-processing**: [data refinement]
- **Review**: `@reviewer` | `@fact-checker` | `@reviewer + @fact-checker` | none

- **spec_module_ref**:                                     [NEW]
  - doc: `<path/to/spec>.md`
    section: "§X.Y — <module name>"
    invariants_targeted: [<inv-1>, <inv-2>]

- **asset_dependencies**:                                  [NEW]
  - path: `<asset/path>`
    consumption_pattern: load_at_init | per_invocation | conditional_per_unit | lazy
    version_field_propagation: `<output_field>`
    cross_consistency_checks: [<other-asset-path>]

- **risk_awareness**:                                      [NEW]
  direct_responsibility: [<risk_id>]
  awareness: [<risk_id>]
  forwarding:
    <downstream>: [<risk_id>]

- **cost_budget**:                                         [NEW]
  llm_calls: <int | range>
  token_budget: <int | range>
  api_calls:
    - service: <name>
      count: <int | range>
      rate_limit_tier: <tier>
  latency_budget_ms: <int | "p95: <int>">
  worst_case_escalation: <strategy>

- **cascade_state**:                                       [NEW — conditional]
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-amendment>
      affects: <field or output structure>
      pre_register_recommended: <true | false>
  spec_version_dependency:
    `<spec-path>`: <required-version>
  workflow_amendment_required_if_cascade_resolves: <true | false>
  amendment_strategy: <regenerate | patch | inherit_via_field>

### 2. (human) [Review Stage]
- **Action**: [user action]
- **Command**: `/<command>`

> Note: (human) stages omit Verification (human is validator) and may omit spec_module_ref / asset_dependencies / cost_budget if pure UX gate.

---

## Planning

### 3. [Stage Name]
[Same per-stage structure as Research stages above with all 8 baseline fields + 5 NEW fields]

---

## Implementation

### N. [Stage Name]
[Same per-stage structure]

---

## Claude Code Configuration

### Sub-agents

[Sub-agent definitions per workflow-generator template — inherited unchanged]

### Agent Team (parallel collaboration when needed)

[Agent Team patterns per workflow-generator template — inherited unchanged]

### SOT (State Management)

- **SOT file**: `.claude/state.yaml`
- **Write authority**: <Orchestrator | Team Lead — single write point>
- **Asset version field propagation**:                     [NEW — spec-grounded]
  | Asset | `<asset>.version` field | Propagates to SOT |
  |---|---|---|
  | <path> | `version` | `state.outputs.step-N.<field>` |

### Hooks / Slash Commands / Required Skills / MCP Servers / Runtime Directories / Error Handling / Autopilot Logs / pACS Logs

[Per workflow-generator template — inherited unchanged]

---

## Cross-Document Consistency Report                        [NEW — spec-grounded]

> Generated automatically at workflow.md finalization (step 22 of generation procedure).

### Spec Invariant Coverage

- **Total upstream spec invariants**: <int>
- **Claimed by stages**: <int> (<percent>%)
- **Orphaned invariants**: [<list>]
- **Double-claimed invariants**: [<list>]

### Asset Consumption Coverage

- **Total upstream assets**: <int>
- **Consumed by ≥ 1 stage**: <int>
- **Unconsumed assets**: [<list>]

### Risk Coverage

- **Risks with this-workflow-owner**: <int>
- **With `direct_responsibility` stage**: <int> (<percent>%)
- **In awareness map / `awareness` or `forwarding` field**: <int>
- **Uncovered risks**: [<list>]

### Cost Budget Feasibility

- **Sum of per-stage cost_budget**: <int> calls / <int> tokens
- **Upstream Cost-Latency Policy total**: <int> calls / <int> tokens
- **Headroom**: <int> calls / <int> tokens
- **Worst-case stages exceeding rate-limit tier**: [<list>]

### Cascade Safety

- **Pending cascade ADRs**: [<list>]
- **Stages affected by each pending ADR**: { <ADR-NNN>: [<stages>] }
- **Pre-register recommended**: [<list>]
- **Amendment-after acceptable**: [<list>]

### DNA Inheritance P1 Validation

```
$ python3 .claude/hooks/scripts/validate_workflow.py --workflow-path ./workflow.md
W1: <PASS|FAIL>
W2: <PASS|FAIL>
...
W8: <PASS|FAIL>
Result: <ALL PASS | N FAIL>
```

### Anti-Overfitting Check                                  [NEW — spec-grounded]

- **Single-domain tokens in mandatory mechanics**: [<list — should be 0>]
- **Domain-specific examples confined to "Examples beyond ..." sections**: <yes | no>

```

## Notation Conventions

| Notation | Meaning |
|---|---|
| `(human)` | Human review/intervention required |
| `(team)` | Agent Team parallel execution |
| `(hook)` | Automatic validation / quality gate |
| `@agent-name` | Sub-agent invocation |
| `@translator` | Translation sub-agent |
| `/command-name` | Slash command execution |
| `[skill-name]` | Skill reference |
| `Review: @reviewer | @fact-checker | none` | Stage-level adversarial review |
| `Translation: ... | none` | Stage-level translation (text deliverables only) |

(Inherited from workflow-generator)

## Field Authority Hierarchy

When fields conflict (e.g., `cost_budget` exceeds upstream policy, `cascade_state` indicates required regeneration), the authority hierarchy is:

1. **3 Absolute Criteria** (Quality > SOT > CCP) — supersede all
2. **Upstream specifications** (PRD/Spec/Eval/Test/Contract/Risk/Asset Cohort) — workflow.md MUST conform
3. **Cost-Latency Policy** — per-stage budgets MUST sum to ≤ policy total
4. **Cascade ADR pending state** — workflow.md MUST document strategy
5. **Stage-level fields** — Verification + spec_module_ref + asset_dependencies + risk_awareness consistent with upstream

When stage-level fields contradict upstream specs: regenerate upstream first OR document explicit deviation rationale in `cascade_state.amendment_strategy`.
