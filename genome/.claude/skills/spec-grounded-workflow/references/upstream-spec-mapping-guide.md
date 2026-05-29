# Upstream Spec → Workflow Stage Mapping Guide

How to map upstream specification modules to workflow stages with `spec_module_ref` field.

## Procedure

### Step 1: Enumerate Upstream Spec Modules

Read the upstream Functional Specification (or equivalent algorithmic spec). Each module typically has:
- A section number (`§X.Y`)
- A pseudocode signature or algorithmic description
- A list of invariants (e.g., I-X.1, I-X.2, ...)
- An optional contract conformance reference

Output: a list of `(spec_module_id, section, invariants, contract_refs)` tuples.

### Step 2: Map Modules to Stages

For each module, decide which workflow stage(s) instantiate it. Apply rules:

| Module Type | Typical Stage Placement |
|---|---|
| Input validation / sanitization | Research stage (early) |
| Lookup / mapping / classification | Research or Planning |
| Analysis / interpretation / generation | Planning |
| Aggregation / scoring / ranking | Planning |
| Rendering / formatting / output | Implementation |
| Quality gates / state machines | Implementation |

If a module spans multiple workflow stages (e.g., a state machine touched by Gates 1 and 2), reference the module from each stage with the same `spec_module_ref` block.

### Step 3: Distribute Invariants

For each invariant in the module:
- Identify which stage's outputs the invariant constrains
- Add invariant ID to that stage's `spec_module_ref.invariants_targeted`
- Verify each invariant is claimed by exactly one stage (no orphans, no double-claims)

If an invariant is naturally split (e.g., I-3.12 instrumentation at Stage A + I-3.12 behavioral acceptance at Stage B), document the split:

```yaml
spec_module_ref:
  - doc: <path>
    section: "§3 — Orchestrator"
    invariants_targeted: ["I-3.12 (instrumentation aspect)"]
```

### Step 4: Cross-Validation

Run a coverage report:

```python
all_invariants = parse_upstream_spec_invariants("<spec-path>")
claimed = {}
for stage in workflow.stages:
    for inv in stage.spec_module_ref.invariants_targeted:
        claimed.setdefault(inv, []).append(stage.id)

orphans = set(all_invariants) - set(claimed.keys())
duplicates = {inv: stages for inv, stages in claimed.items() if len(stages) > 1 and not is_split_acceptable(inv)}

assert not orphans, f"Orphaned invariants: {orphans}"
assert not duplicates, f"Double-claimed invariants: {duplicates}"
```

## Common Patterns

### Pattern A: Single-Module-Single-Stage (1:1)

Most common pattern — one spec module instantiates exactly one workflow stage.

```yaml
# Workflow Stage 5
spec_module_ref:
  - doc: <spec-path>
    section: "§7 — LLM Narrative Expansion"
    invariants_targeted: [I-7.1, I-7.2, I-7.3, I-7.4, I-7.5]
```

### Pattern B: Module-Spans-Multiple-Stages (1:N)

When one module is invoked at multiple stages (e.g., schema validator called at input + before each emission), reference from each stage.

```yaml
# Workflow Stage 1 (input validation)
spec_module_ref:
  - doc: <spec-path>
    section: "§3.4 — schema_validate"
    invariants_targeted: [I-3.4 (input invocation)]

# Workflow Stage 8 (pre-emission)
spec_module_ref:
  - doc: <spec-path>
    section: "§3.4 — schema_validate"
    invariants_targeted: [I-3.4 (pre-emission invocation)]
```

### Pattern C: Multi-Module-Single-Stage (N:1)

When a stage integrates multiple modules (e.g., orchestrator coordinates many sub-modules), reference all.

```yaml
# Workflow Stage 3 (orchestration)
spec_module_ref:
  - doc: <spec-path>
    section: "§3 — Top-Level Orchestrator"
    invariants_targeted: [I-3.1, I-3.2, I-3.3]
  - doc: <spec-path>
    section: "§5 — Free-Text Mapping"
    invariants_targeted: [I-5.1, I-5.2]
  - doc: <spec-path>
    section: "§9 — Citation Classifier"
    invariants_targeted: [I-9.1, I-9.2]
```

### Pattern D: Cross-Document Reference

When the spec module references conformance against another document (e.g., output contract), include all references.

```yaml
# Workflow Stage 7 (renderer)
spec_module_ref:
  - doc: <spec-path>
    section: "§10 — Renderer"
    invariants_targeted: [I-10.1, I-10.2, ..., I-10.9]
  - doc: <contract-path>
    section: "§6 — Rendering Spec"
    contract_conformance: [C7, C9, C16, C18, C20]
```

## Edge Cases

### When Spec Has No Invariant IDs

Some upstream specs have prose constraints without numeric IDs. Convert to invariant-style assertions in `invariants_targeted`:

```yaml
invariants_targeted:
  - "Output schema validates against contract §1.1"
  - "All free-text fields sanitized before storage"
  - "No LLM call from renderer module (deterministic constraint)"
```

### When Module Determinism Class Splits Stage

If a single module is partly deterministic + partly probabilistic, the workflow stage **MUST** also document this in the Hybrid Architecture Boundary table (see SKILL.md Concern 1) and split the stage if the determinism KPI requires it.

```yaml
# Workflow Stage 5a (deterministic part)
spec_module_ref:
  - doc: <spec>
    section: "§4 — Module 1: Layer 1 Keyword Screen"
    invariants_targeted: [I-4.1, I-4.4]
    determinism_class: deterministic

# Workflow Stage 5b (probabilistic part)
spec_module_ref:
  - doc: <spec>
    section: "§4 — Module 1: Layer 2 LLM Intent Classifier"
    invariants_targeted: [I-4.2, I-4.3]
    determinism_class: probabilistic
```

### When Spec Cascade ADR Is Pending

Document `cascade_state` per stage where the cascade affects `spec_module_ref` interpretation:

```yaml
spec_module_ref:
  - doc: <spec>
    section: "§7.5 — measure_deviation"
    invariants_targeted: [I-7.4, I-7.5]
    note: "Spec v1.0.2 signature; v1.1.0 cascade pending per <ADR-NNN-amendment>"

cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-amendment>
      affects: "spec_module_ref §7.5 signature (measure_deviation function arguments)"
      pre_register_recommended: true
```

## Examples Across Domains

### Implementation Pipeline (any workflow instance)

```yaml
# Workflow stage instantiating spec §6 rule_component_lookup
spec_module_ref:
  - doc: docs/<workflow>/<workflow>-spec.md
    section: "§6 — Module 3 Rule-Component"
    invariants_targeted: [I-6.1, I-6.2, I-6.3, I-6.4]
```

### Medical AI Inference

```yaml
# Workflow stage applying clinical guideline
spec_module_ref:
  - doc: clinical-guidelines/<condition>.md
    section: "§4.2 — Diagnostic Criteria Score Computation"
    invariants_targeted:
      - "Score within validated range [0, 100]"
      - "Demographic adjustment applied per §4.3"
```

### Legal Contract Analysis

```yaml
spec_module_ref:
  - doc: legal-taxonomy.md
    section: "§7 — Force Majeure Clause Classification"
    invariants_targeted:
      - "Classification ∈ {standard, expanded, custom}"
      - "Jurisdiction-specific override applied per §7.2"
```

### RAG with Compliance

```yaml
spec_module_ref:
  - doc: rag-spec.md
    section: "§3 — Retrieval Stage"
    invariants_targeted: [I-3.1 retrieval-deterministic, I-3.2 corpus-version-pinned]
  - doc: compliance-spec.md
    section: "§5 — Source Provenance Requirements"
    invariants_targeted: ["Every retrieved chunk has source URL + retrieval timestamp"]
```

### Academic Systematic Review

```yaml
spec_module_ref:
  - doc: prisma-protocol.md
    section: "§5 — Eligibility Criteria"
    invariants_targeted:
      - "Inclusion criteria applied to all retrieved studies"
      - "Exclusion reasons logged per study"
```

## Anti-Patterns

| Anti-Pattern | Why Forbidden | Fix |
|---|---|---|
| Stage with no `spec_module_ref` when spec exists | Untraceable; integration test cannot verify spec compliance | Identify which spec module the stage instantiates; if truly novel, register spec amendment first |
| Vague `invariants_targeted: [all relevant invariants]` | Coverage check cannot enumerate; orphaned invariants undetectable | List explicit invariant IDs |
| Same invariant claimed by 3+ stages without split rationale | Ambiguous which stage's failure indicates the invariant breach | Either split with rationale or assign to single most-responsible stage |
| `spec_module_ref` references nonexistent section | Stage's spec authority claim is false | Verify section exists at upstream spec version pinned in Upstream Spec Inventory |
