# Cascade State Management

How to navigate cross-document version cascade dependencies in workflow.md generation.

## When Cascade State Matters

Cascade state arises when:

1. Workflow consumes multiple upstream specifications
2. One or more specs has a **pending amendment ADR** (registered but not yet executed) OR **anticipated revision**
3. The amendment, when resolved, would change the form of the workflow.md

Common in multi-document spec systems where amendments cascade:

- **Spec ADR-NNN-amendment** triggers Test Plan amendment + Eval Plan amendment
- **Output Contract minor bump** triggers PRD field additions + Spec field additions
- **Risk register R-NNN status change** triggers mitigation locus moves
- **External standard revision** (regulatory ruling, model release, library version)

## Decision Framework

For each pending cascade ADR, decide between two strategies:

### Strategy A: `pre_register` (Recommended for material changes)

Register the cascade ADR **before** generating workflow.md. Workflow.md uses post-cascade form.

**Use when**:
- Cascade affects workflow stage **structure** (number of stages, stage boundaries)
- Cascade affects **type signatures** of spec modules referenced by workflow stages
- Cascade resolution timeline is short (within Phase 3 design window)
- Workflow regeneration cost > cascade pre-registration cost

**Example**:
```yaml
# Spec amendment changes function signature: workflow stages reference these signatures
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-amendment>
      affects: "spec_module_ref §X.Y signature (function arguments + return type)"
      pre_register_recommended: true
      rationale: "Stages 5-7 depend on signature; regeneration if amendment-after"
  workflow_amendment_required_if_cascade_resolves: true (large patch)
  amendment_strategy: regenerate
```

### Strategy B: `amendment_after` (Recommended for value-only changes)

Generate workflow.md with current spec form. Patch workflow.md after cascade resolves.

**Use when**:
- Cascade affects only **field values** (not structure)
- Cascade resolution timeline is long
- Workflow regeneration cost < cascade pre-registration cost
- Cascade is conditional on downstream probe outcome (e.g., probe-dependent ADR)

**Example**:
```yaml
# Threshold value will be calibrated post-probe
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-calibration>
      affects: "stage_5.cost_budget.latency_budget_ms (calibrated from Phase 4d probe)"
      pre_register_recommended: false
      rationale: "Calibration depends on Phase 4d probe outcome; amendment-after via patch"
  workflow_amendment_required_if_cascade_resolves: true (small patch)
  amendment_strategy: patch
```

### Strategy C: `inherit_via_field` (Use when amendment field-equivalent in current form)

Workflow.md form is identical pre/post cascade; cascade just updates field values referenced via inheritance.

**Use when**:
- Cascade only updates upstream field values
- Workflow stages reference spec sections (not specific values)
- No structural change

**Example**:
```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-table-update>
      affects: "upstream lookup table values (workflow stages reference table by section, not value)"
      pre_register_recommended: false
  workflow_amendment_required_if_cascade_resolves: false
  amendment_strategy: inherit_via_field
```

## Procedure

### Step 1: Inventory Pending Cascades

Read upstream specs and identify all pending amendment ADRs:

- ADRs with status `pending_amendment` or `cascade_required`
- Open Items (OI-XXX) that mention cascade dependencies
- Risk register entries with `severity ESCALATED` indicating future amendment

For each, document:
- ADR ID
- What it amends (which spec section / field)
- Resolution dependency (e.g., probe outcome, external review)
- Estimated resolution timeline

### Step 2: Decide Strategy per Cascade

For each pending cascade, apply decision framework:

```
1. Does cascade affect workflow stage structure?
   YES → Strategy A (pre_register) STRONGLY recommended
   NO → continue

2. Does cascade affect type signatures referenced by stages?
   YES → Strategy A (pre_register) recommended
   NO → continue

3. Is cascade resolution short-term (within Phase 3 design)?
   YES → Strategy A or C
   NO → Strategy B or C

4. Does cascade affect only upstream field values (no workflow structure change)?
   YES → Strategy C (inherit_via_field)
   NO → Strategy A or B
```

### Step 3: Document per Stage + Workflow Global

Per affected stage:
```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-amendment>
      affects: <specific field or output structure>
      pre_register_recommended: <true | false>
      rationale: <why>
  spec_version_dependency:
    <spec-path>: <required-version>
  workflow_amendment_required_if_cascade_resolves: <true | false>
  amendment_strategy: <regenerate | patch | inherit_via_field>
```

Workflow global (in Upstream Spec Inventory):
```markdown
### Cascade ADR Pending State

| Pending ADR | Affects | Strategy | Pre-register? |
|---|---|---|---|
| <ADR-NNN> | <description> | <regenerate | patch | inherit_via_field> | <yes | no> |
```

### Step 4: Cross-Cutting Cascade Resolution Decision

Some workflows benefit from **batch pre-registration** of multiple cascade ADRs at Phase 3 entry:

- Reduces cumulative amendment churn
- Locks workflow.md form for downstream phases
- Cleaner ADR ordering chain

Document at workflow header:

```markdown
### Cascade Resolution Decision (Phase 3 Entry)

**Pre-register batch**: <ADR-NNN-amendment-1, ADR-NNN-amendment-2, ADR-NNN-amendment-3>
- ADR-NNN-amendment-1 (Spec §X.Y signature): pre-register before workflow.md
- ADR-NNN-amendment-2 (Test Plan §A.B fixture): pre-register before workflow.md
- ADR-NNN-amendment-3 (Eval Plan §C.D method): pre-register before workflow.md

**Defer to amendment-after**: <ADR-NNN-calibration>
- ADR-NNN-calibration (probe-dependent threshold): amendment-after via patch when probe completes
```

## Examples Across Domains

### Implementation Pipeline (any)

```yaml
# Spec signature amendment pending
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-NNN-amendment>
      affects: "spec_module_ref §7.5 measure_deviation function signature"
      pre_register_recommended: true
      rationale: "stage 5 generation step depends on signature; regeneration cost high"
  spec_version_dependency:
    "<workflow>-spec.md": "v1.1.0"
  workflow_amendment_required_if_cascade_resolves: true
  amendment_strategy: regenerate
```

### ML Workflow with Pending Model Release

```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: model-v2-release
      affects: "stage_3.asset_dependencies model checkpoint version"
      pre_register_recommended: false
      rationale: "Model v2 release date uncertain; v1 sufficient for current Phase 3"
  amendment_strategy: patch
```

### Legal Compliance Pipeline with Pending Statute Vote

```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: statute-amendment-2026-Q3
      affects: "stage_4 jurisdiction-rules.yaml ruleset version"
      pre_register_recommended: false
      rationale: "Vote scheduled 2026-09; pre-amendment ruleset operational"
  amendment_strategy: inherit_via_field
```

### Medical AI Workflow with Pending Clinical Guideline Update

```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: clinical-guideline-v3-publication
      affects: "spec_module_ref §4.2 diagnostic criteria thresholds"
      pre_register_recommended: false
      rationale: "Guideline v3 expected late 2026; v2 currently authoritative"
  amendment_strategy: patch
```

### Financial Risk Model with Pending Regulatory Framework

```yaml
cascade_state:
  pending_cascade_adrs:
    - adr_id: basel-iv-finalization
      affects: "stage_6 capital calculation methodology"
      pre_register_recommended: true
      rationale: "Pre-registration enables seamless transition; regulatory deadline binding"
  amendment_strategy: regenerate
```

### Multi-Document Cascade Chain

```yaml
# When multiple cascades chain
cascade_state:
  pending_cascade_adrs:
    - adr_id: <ADR-A-amendment>
      affects: "Spec §7 signature"
      pre_register_recommended: true
    - adr_id: <ADR-B-amendment>
      affects: "Test Plan §3 fixture (depends on ADR-A)"
      pre_register_recommended: true
      depends_on: <ADR-A-amendment>
    - adr_id: <ADR-C-amendment>
      affects: "Eval Plan §5 method (depends on ADR-A)"
      pre_register_recommended: true
      depends_on: <ADR-A-amendment>
  amendment_strategy: regenerate (after all cascade ADRs registered)
```

## Cross-Validation

Verify cascade state is internally consistent:

```python
def validate_cascade_state(workflow):
    for stage in workflow.stages:
        for cascade in stage.cascade_state.pending_cascade_adrs:
            # Verify ADR ID references real ADR (not placeholder)
            assert adr_exists(cascade.adr_id) or cascade.adr_id.endswith("-amendment-placeholder")

            # Verify spec_version_dependency aligns
            for spec_path, required_version in stage.cascade_state.spec_version_dependency.items():
                actual_version = read_upstream_spec_version(spec_path)
                if actual_version != required_version:
                    print(f"WARNING: {spec_path} version mismatch: actual {actual_version}, required {required_version}")

        # Verify amendment_strategy is consistent with workflow_amendment_required
        if stage.cascade_state.workflow_amendment_required_if_cascade_resolves:
            assert stage.cascade_state.amendment_strategy in ["regenerate", "patch"]
        else:
            assert stage.cascade_state.amendment_strategy == "inherit_via_field"
```

## Anti-Patterns

| Anti-Pattern | Why Forbidden | Fix |
|---|---|---|
| `pre_register_recommended: false` for structural change | Workflow regeneration churn after cascade | Set to true; pre-register before workflow.md generation |
| `amendment_strategy: inherit_via_field` when amendment changes structure | Workflow form will become invalid | Use `regenerate` strategy |
| Cascade ADR ID is placeholder (TBD, NNN, ?) | Cascade dependency untrackable | Allocate explicit ADR ID |
| Pending cascade not surfaced in Upstream Spec Inventory | Workflow appears "frozen" but is actually pre-cascade | Always document pending cascade at top-level |
| `workflow_amendment_required_if_cascade_resolves: false` when amendment changes any field referenced | Stale workflow.md after cascade | Set to true; document amendment_strategy |
| Multiple chained cascades not ordered | Amendment cascade fails (B before A) | Document `depends_on` chain |
