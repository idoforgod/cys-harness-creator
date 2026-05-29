---
name: spec-grounded-workflow
description: workflow.md generation skill for spec-grounded workflows where formal upstream specifications exist (product requirements, functional spec, test plan, eval methodology, output contract, risk register, build-time asset cohort). Used when user requests "procedure design from specifications", "implementation pipeline procedure design", "rigorous workflow with assets and risks", "Phase 3 procedure design", or when upstream spec documents are present. Distinct from `workflow-generator` (idea-only or single-document generic workflow) — this skill enforces stage-level spec_module_ref + asset_dependencies + risk_awareness + cost_budget + cascade_state fields plus Hybrid Architecture and Multi-Sample documentation.
---

# Spec-Grounded Workflow Generator

Skill for generating rigorous workflow.md files when **formal upstream specifications exist**.

This skill is an **extension** of `workflow-generator` (inherits 3-stage + DNA + Verification + Translation + Review + Autopilot + pACS + validate_workflow.py P1 검증), with **5 additional per-stage fields** and **2 additional global concerns** required when upstream formal specifications, asset cohorts, risk registers, and cost-latency policies exist.

## Use Case Discrimination

| Condition | Use this skill | Use `workflow-generator` |
|---|---|---|
| Upstream PRD / Functional Spec / Eval Plan / Test Plan / Output Contract present | ✓ | ✗ |
| Build-time asset cohort to consume (lookup tables, retrieval corpus, ML models, controlled vocabulary, config files, regulatory rulesets) | ✓ | ✗ |
| Formal risk register with enumerable risk IDs (e.g., R-NNN) | ✓ | ✗ |
| Cost-latency policy with quantified budget allocation | ✓ | ✗ |
| Cascade ADR pending state to navigate | ✓ | ✗ |
| Hybrid deterministic + probabilistic architecture (e.g., RAG, agent+tool, ensemble) | ✓ | ✗ |
| Multi-sample variance control (Self-Consistency, ensemble LLM, multi-judge eval) | ✓ | ✗ |
| Idea-only OR single-document generic workflow | ✗ | ✓ |
| Generic content / research / analysis pipeline | ✗ | ✓ |

When in doubt: if the user has produced **formal specification documents** as part of an Implementation Pipeline OR equivalent rigorous design process, use this skill. Otherwise, use `workflow-generator`.

---

## Inheritance from `workflow-generator`

This skill **inherits all principles from `.claude/skills/workflow-generator/SKILL.md`** without redefinition:

- **3 Absolute Criteria** (Quality first > SOT > CCP)
- **Genome Inheritance Protocol** (`Inherited DNA` section)
- **Design Principles P1-P4** (data refinement, expert delegation, image accuracy, question rules)
- **3-Stage Structure** (Research → Planning → Implementation)
- **Verification field** (5 criterion types: structural completeness, functional goals, data consistency, pipeline connection, cross-stage traceability)
- **Translation field** (`@translator` for text deliverables)
- **Review field** (`@reviewer` / `@fact-checker` / `none`)
- **Claude Code Component Mapping** (Sub-agent / Agent Team / Hook / Slash / Skill / MCP)
- **Sub-agent vs Agent Team selection criteria** (quality-only)
- **English-First Execution**
- **Autopilot + pACS support**
- **DNA Inheritance P1 Validation** (`validate_workflow.py` W1-W8)
- **Final Generation Procedure** steps 1-13

This skill **adds** the rigor needed when upstream formal specifications, asset cohorts, risk registers, and cost-latency policies exist.

---

## Additional Per-Stage Fields (5 NEW)

When this skill generates workflow.md, every stage MUST include the following fields beyond `workflow-generator` defaults.

### Field 1 — `spec_module_ref` (Upstream Specification Cross-Reference)

Cross-reference to the upstream specification module that this stage instantiates.

```yaml
spec_module_ref:
  - doc: <path/to/upstream-spec>.md
    section: "<§X.Y — module name>"
    invariants_targeted: [<invariant_id_1>, <invariant_id_2>, ...]
```

**Purpose**: Phase 3 → downstream phase traceability. Integration tests verify workflow stage outputs satisfy the spec invariants this stage targets. Provides automatic upstream impact analysis when specs amend.

**General applicability**: Any workflow generated FROM upstream specifications. Examples beyond Implementation Pipeline:
- Medical AI workflow → references clinical guideline §X.Y
- Legal contract analysis → references statute § + case law citation
- Academic systematic review → references PRISMA methodology step
- Financial risk model → references regulatory framework (Basel, IFRS)

### Field 2 — `asset_dependencies` (Build-Time Artifact Consumption)

Static build-time assets consumed by this stage.

```yaml
asset_dependencies:
  - path: <relative/path/to/asset>
    consumption_pattern: <load_at_init | per_invocation | conditional_per_unit | lazy>
    version_field_propagation: <stage_output.field_name>     # optional
    cross_consistency_checks: [<other_asset_path>]            # optional
```

**Consumption patterns**:
- `load_at_init`: asset loaded once at module initialization (e.g., lookup table, config)
- `per_invocation`: asset accessed per workflow invocation (e.g., user-specific corpus shard)
- `conditional_per_unit`: asset accessed per output unit conditional on content (e.g., reference matched per claim)
- `lazy`: asset loaded only when triggered (e.g., fallback corpus on retrieval miss)

**Purpose**: Asset codification phase (analogous to Implementation Pipeline Phase 4b) registers asset integrity tests; integration phase verifies cross-asset version consistency.

**General applicability**: Any workflow consuming static assets. Examples:
- RAG pipeline → embedding model + retrieval corpus + reranker model
- ML inference workflow → model weights + tokenizer + label vocabulary
- Compliance workflow → rule book + jurisdiction map + violation taxonomy
- Translation workflow → glossary + parallel corpus + terminology bank

### Field 3 — `risk_awareness` (Formal Risk Register Integration)

Risks (from upstream Risk Register) this stage must mitigate, surface awareness of, or forward downstream.

```yaml
risk_awareness:
  direct_responsibility: [<risk_id>]   # this stage IS the mitigation locus
  awareness: [<risk_id>]                # this stage may surface/interact with risk
  forwarding:
    <downstream_phase_or_stage>: [<risk_id>]   # cascade
```

**Purpose**: Cross-cutting risk register integration; per-stage risk mitigation locus visible in design; downstream-phase risk inheritance traceability.

**General applicability**: Any workflow with formal risk management requirements. Examples:
- Medical AI → safety risks (false negative, demographic bias, alert fatigue)
- Financial model → model risk (overfitting, regime change, data quality)
- Legal → compliance risk (jurisdiction drift, statute amendment, precedent reversal)
- Security pipeline → threat model (injection, exfiltration, privilege escalation)
- Academic review → bias risk (publication bias, selection bias, citation chain)

### Field 4 — `cost_budget` (Resource Allocation per Stage)

Resource allocation expectations for this stage (LLM calls, API calls, tokens, latency).

```yaml
cost_budget:
  llm_calls: <int | "<lo>-<hi>" range>
  token_budget: <int | "<lo>-<hi>" range>
  api_calls:                                 # optional, if external APIs used
    - service: <name>
      count: <int | range>
      rate_limit_tier: <subscription | api_tier_X | unbounded>
  latency_budget_ms: <int | "p95: <int>" | "p99: <int>">
  worst_case_escalation: <strategy_string>   # what to do when budget exceeded
```

**Purpose**: Cost-latency policy conformance per upstream Cost-Latency Policy ADR; cost calibration probe + acceptance budget validation in downstream phases.

**General applicability**: Any workflow with cost or rate-limit constraints. Examples:
- LLM API workflow → token + rate-limit budget
- Cloud compute pipeline → CPU/GPU-hour budget
- Real-time inference → latency SLA p95/p99
- High-throughput batch → throughput SLA + parallelism budget
- Cost-optimized inference → cheap-model fallback escalation

### Field 5 — `cascade_state` (Cross-Document Version Cascade Awareness)

Pending cascade ADRs / version dependencies that affect this stage.

```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-amendment | upcoming-spec-revision>
      affects: <which stage field or output structure>
      pre_register_recommended: <true | false>
  spec_version_dependency:
    <upstream_spec_path>: <version_required>
  workflow_amendment_required_if_cascade_resolves: <true | false>
  amendment_strategy: <regenerate | patch | inherit_via_field>
```

**Purpose**: Avoid stale workflow.md when upstream specs cascade-amend post-closure. Documents which cascade ADRs the workflow author chose to wait for vs proceed without.

**General applicability**: Any workflow generated against frozen-but-pending-cascade specifications. Examples:
- Multi-document spec pipelines (PRD + Spec + Test + Eval) where amendments cascade
- Regulatory compliance workflow before ruling becomes final
- ML workflow against pre-release model version
- Translation workflow before glossary v2 lockdown
- Legal workflow before statute amendment vote

---

## Additional Global Concerns (2 NEW)

### Concern 1 — Hybrid Architecture Boundary Documentation

When workflow has both **deterministic** components (rule-based, lookup, computation, schema validation) AND **probabilistic** components (LLM, ML inference, sampling), the `Inherited DNA` section MUST document the boundary explicitly.

**Required block** (added to Inherited DNA section):

```markdown
### Hybrid Architecture Boundary

| Module / Stage | Component | Determinism Class | Implementation Primitive |
|---|---|---|---|
| <name> | <function> | deterministic | <(hook) | Sub-agent rule lookup | Skill | code module> |
| <name> | <function> | probabilistic | <Sub-agent LLM call | Agent Team | MCP server> |
| ... | ... | ... | ... |

**Rationale**: <upstream spec> assigns determinism class per module. Integration phase verifies determinism KPI per module (deterministic modules: bytes-identical output; probabilistic modules: statistical bound).
```

**General applicability**: Most modern AI workflows are hybrid. Examples:
- RAG = retrieval [deterministic similarity] + generation [probabilistic LLM]
- Agent + tool use = LLM planning [probabilistic] + tool execution [deterministic]
- Ensemble methods = N model inferences [probabilistic] + voting/aggregation [deterministic]
- Citation generation = source matching [deterministic] + paraphrase [probabilistic]

### Concern 2 — Multi-Sample / Self-Consistency Implementation Decision

When workflow uses Self-Consistency / multi-sample / ensemble LLM patterns, the workflow.md MUST explicitly decide implementation form.

**Required block** (added to Inherited DNA section, conditional):

```markdown
### Multi-Sample Implementation Pattern

- **Pattern**: <Sequential N+1 calls | Agent Team N parallel + Team Lead integration | Hybrid>
- **N**: <integer>
- **Variance source**: <temperature | prompt_variation | seed | ensemble_model_diversity | other>
- **Integration mechanism**: <T=X.X integration call | majority vote | weighted average | LLM judge | none>
- **Trade-off**: <quality | throughput | rate_limit | cost — explicit choice rationale>
- **Cost impact**: <integrate with cost_budget per affected stage>
- **Failure mode**: <strategy when sample variance exceeds threshold>
```

**General applicability**: Any workflow using multi-sample variance control. Examples:
- LLM Self-Consistency for hallucination reduction
- Ensemble ML for uncertainty quantification
- Multi-judge LLM eval for inter-rater reliability
- N-best decoding with reranking
- Bayesian model averaging

---

## Final Generation Procedure (Extended)

This skill inherits steps 1-13 from `workflow-generator` SKILL.md §Final Generation Procedure verbatim and **adds steps 14-22**.

### Inherited Steps (1-13)

See `.claude/skills/workflow-generator/SKILL.md §Final Generation Procedure`.

### Additional Steps (14-22)

**14. Upstream Spec Inventory**

Before stage definition, enumerate upstream artifacts available:
- List PRD / Functional Spec / Eval Plan / Test Plan / Output Contract paths + versions
- List build-time asset cohort paths
- List risk register entries with owner = this workflow
- Document cascade ADR pending state
- Document upstream Cost-Latency Policy

Output: short "Upstream Spec Inventory" block at top of workflow.md (between Overview and Inherited DNA).

**15. Per-Stage Spec Module Mapping**

For each stage, identify upstream spec module and invariants targeted.

Procedure:
- Read upstream Functional Spec module pseudocode
- Map each spec module to one or more workflow stages
- Enumerate spec invariants the stage MUST satisfy
- Fill `spec_module_ref` field per stage

Cross-validation: every spec invariant from upstream must be claimed by exactly one stage (no orphans, no double-claims).

**16. Asset Consumption Mapping**

For each stage consuming assets, fill `asset_dependencies`:
- Identify which assets the spec module reads (load_asset() calls in pseudocode)
- Choose consumption pattern (load_at_init / per_invocation / conditional_per_unit / lazy)
- Document version field propagation (which output field carries asset.version)
- List cross-asset consistency checks (e.g., asset A's version must match asset B's reference)

Cross-validation: every asset in upstream cohort must be consumed by ≥ 1 stage.

**17. Risk Distribution**

Distribute risk register entries to stages:
- For each risk with owner = this workflow → assign to one stage as `direct_responsibility`
- For each risk where this workflow's stage interacts with risk → mark as `awareness`
- For each risk where this stage's output cascades to downstream phases → mark as `forwarding`

Cross-validation: every risk register entry with this-workflow-owner must have ≥ 1 stage with `direct_responsibility`. Every risk in upstream "Risk Awareness Coverage Map" must appear in at least one stage's `awareness` or `forwarding`.

**18. Cost Budget Allocation**

For each stage with LLM calls / API calls / latency-sensitive operations:
- Read upstream Cost-Latency Policy total budget
- Allocate per-stage budget consistent with Cost-Latency Policy
- Document worst-case escalation strategy

Cross-validation: sum of per-stage budgets ≤ upstream policy total budget; worst-case sums respect rate-limit tier.

**19. Cascade State Annotation**

Document pending cascade ADRs + version dependencies in `cascade_state` per affected stage:
- Identify which upstream specs have pending amendments
- Decide pre-register vs proceed-without strategy
- Mark stages whose form would change if cascade resolves

Decision: pre-register cascade ADRs **before** workflow.md generation when the cascade would materially change stage structure (rather than just updating field values). Otherwise, proceed with current spec form + amendment-after strategy.

**20. Hybrid Architecture Documentation**

If workflow has both deterministic and probabilistic components, add Hybrid Architecture Boundary table to Inherited DNA section.

Read upstream Functional Spec to identify each module's `determinism_class`. Map each to implementation primitive (Sub-agent / hook / Agent Team / Skill / MCP).

**21. Multi-Sample Decision**

If workflow uses Self-Consistency / multi-sample / ensemble, add Multi-Sample Implementation Pattern block.

Decision rubric:
- Sequential N+1 calls: lower throughput, no parallel rate-limit pressure, simpler integration
- Agent Team N parallel + integration: higher throughput, parallel rate-limit pressure, requires SOT design (Absolute Criterion 2)
- Hybrid: e.g., N=2 sequential + 1 integration if rate limit < N parallel

Output: explicit trade-off rationale tied to upstream Cost-Latency Policy + reliability constraints.

**22. Cross-Document Consistency Check**

Before workflow.md finalization, verify:
- Every upstream spec invariant claimed by exactly one stage (`spec_module_ref` aggregation)
- Every upstream asset consumed by ≥ 1 stage (`asset_dependencies` aggregation)
- Every upstream risk with this-workflow-owner has `direct_responsibility` stage; every risk in awareness map appears in `awareness` or `forwarding`
- Sum of `cost_budget` ≤ upstream Cost-Latency Policy total
- All `cascade_state.pending_cascade_adrs` reference real ADRs (not placeholders)
- Hybrid Architecture Boundary table covers all modules
- Multi-Sample Implementation Pattern block present if and only if multi-sample used

Cross-validation report: produce a brief "Cross-Document Consistency Report" appended to workflow.md or as separate file (e.g., `workflow-consistency-report.md`) before P1 validation.

---

## Templates and References

| Reference file | Purpose |
|---|---|
| `references/workflow-template-extended.md` | Extended workflow.md template (adds 5 fields + 2 global concerns) |
| `references/upstream-spec-mapping-guide.md` | Procedure for mapping upstream spec modules → workflow stages |
| `references/asset-consumption-patterns.md` | 4 consumption patterns + version propagation discipline |
| `references/risk-awareness-distribution-guide.md` | direct vs awareness vs forwarding classification procedure |
| `references/cost-budget-allocation-guide.md` | Top-down budget allocation + worst-case escalation patterns |
| `references/cascade-state-management.md` | Pre-register vs amendment-after decision criteria |
| `references/hybrid-architecture-patterns.md` | Deterministic/probabilistic boundary representation |
| `references/multi-sample-implementation-patterns.md` | Sequential vs parallel + variance source + integration mechanism |

For base patterns (Sub-agent / Team / Hook / Skill / MCP / SOT / Context Injection), refer to `workflow-generator/references/` — those are inherited unchanged.

---

## Anti-Overfitting Discipline

This skill MUST remain domain-agnostic. Authors and users MUST NOT:

- Reference specific risk IDs from any one workflow (use `<risk_id>` placeholder)
- Reference specific spec module names (use `<spec-path>` and `<§X.Y>` placeholders)
- Embed domain-specific examples in mandatory mechanics (place all domain examples behind "Examples beyond ..." sections)
- Hard-code numeric thresholds tied to a specific workflow

Domain examples ARE permitted in **example sections** to illustrate generality, but mandatory mechanics use abstract placeholders.

Anti-overfitting check during skill maintenance:
1. Search this SKILL.md for any single-workflow-specific token (instance-specific identifiers from particular domains: personality typology codes, project acronyms, specific risk IDs, specific URL fragments). Result expected: 0 matches in mandatory mechanics.
2. Verify each "General applicability" section lists ≥ 3 distinct domains.
3. Verify Use Case Discrimination table has examples from ≥ 4 distinct domains.

---

## Suitable Use Cases (Multi-Domain)

| Domain | Trigger Specs | This skill |
|---|---|---|
| Implementation Pipeline Phase 3 (any workflow instance) | PRD + Spec + Eval + Test + Contract + Risk + Asset Cohort | ✓ |
| RAG pipeline with regulatory compliance | Compliance spec + retrieval corpus + risk register + cost budget | ✓ |
| Medical AI inference workflow | Clinical guideline spec + safety risk register + ML asset cohort + latency SLA | ✓ |
| Legal contract analysis pipeline | Legal taxonomy spec + cited-source corpus + accuracy eval methodology + jurisdiction risk | ✓ |
| Financial risk model workflow | Risk methodology + market data corpus + regulatory ruleset + cost-compute budget | ✓ |
| Academic systematic review workflow | PRISMA methodology + database corpus + bias risk register + reviewer-time budget | ✓ |
| Compliance / audit pipeline | Regulation ruleset + transaction corpus + audit risk register + processing time SLA | ✓ |
| Generic blog content pipeline | (idea-only; no formal specs) | ✗ → workflow-generator |
| Simple research/analysis workflow | (no formal specs) | ✗ → workflow-generator |
| Single-document workflow | (single PDF/spec attached, no upstream chain) | ✗ → workflow-generator |

---

## Distill Validation (Optional but Recommended)

After generation, review workflow.md quality:

1. **Spec coverage**: Does every upstream spec module map to ≥ 1 stage?
2. **Asset coverage**: Does every upstream asset have ≥ 1 consumer stage?
3. **Risk coverage**: Does every direct-owner risk have a `direct_responsibility` stage?
4. **Budget feasibility**: Do per-stage budgets sum to ≤ upstream policy total?
5. **Cascade safety**: Does any unresolved cascade ADR require workflow regeneration if it resolves?
6. **DNA P1 validation**: Run `python3 .claude/hooks/scripts/validate_workflow.py --workflow-path ./workflow.md` → confirm W1-W8 pass
7. **Anti-overfitting**: Run search for domain-specific tokens; confirm 0 matches in mandatory mechanics

Reference: `prompt/distill-partner.md` (inherited from workflow-generator).

---

## Generation Output Structure

A workflow.md generated by this skill has the following structure (additions over `workflow-generator` baseline marked NEW):

```
# <Workflow Name>

## Overview
- Input / Output / Frequency / Autopilot / pACS

## Upstream Spec Inventory                                      [NEW]
- PRD / Spec / Eval / Test / Contract / Risk / Asset Cohort paths + versions
- Cascade ADR pending state summary
- Cost-Latency Policy total budget reference

## Inherited DNA (Parent Genome)
- 3 Absolute Criteria + Inherited Patterns (workflow-generator baseline)
- Hybrid Architecture Boundary                                  [NEW]
- Multi-Sample Implementation Pattern                           [NEW conditional]

## Research / Planning / Implementation
Each stage:
- Pre-processing / Agent / Verification / Task / Output / Translation / Post-processing / Review (workflow-generator baseline)
- spec_module_ref                                               [NEW]
- asset_dependencies                                            [NEW]
- risk_awareness                                                [NEW]
- cost_budget                                                   [NEW]
- cascade_state                                                 [NEW conditional]

## Claude Code Configuration
- Sub-agents / Agent Teams / Hooks / Slash Commands / Skills / MCP / Runtime Directories / Error Handling (workflow-generator baseline)

## Cross-Document Consistency Report                            [NEW]
- Spec coverage / Asset coverage / Risk coverage / Budget feasibility / Cascade safety
```

The 5 NEW per-stage fields and 2 NEW global concerns provide the rigor needed when upstream formal specifications exist; the workflow remains compatible with `workflow-generator` infrastructure and `validate_workflow.py` P1 validation.
