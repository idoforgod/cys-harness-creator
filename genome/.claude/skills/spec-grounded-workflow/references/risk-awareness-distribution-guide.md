# Risk Awareness Distribution Guide

How to distribute upstream risk register entries to workflow stages with `risk_awareness` field.

## The 3 Classification Categories

### Category 1: `direct_responsibility`

This stage **IS the mitigation locus** for the risk. The stage's outputs and behavior directly determine whether the risk is mitigated.

**Indicators**:
- Risk register lists this workflow / stage as `owner`
- Risk mitigation steps include actions performed at this stage
- Failure of this stage's verification criteria materially advances the risk

**Example placement**:
```yaml
risk_awareness:
  direct_responsibility: [<risk_id>]
```

### Category 2: `awareness`

This stage **interacts with** the risk but is not the primary mitigation locus. The stage may surface, observe, or be affected by the risk without being responsible for resolving it.

**Indicators**:
- Risk affects this stage's inputs, processing, or outputs
- Stage may amplify or attenuate risk
- Mitigation lives elsewhere (upstream config, downstream gate, cross-cutting check)

**Example placement**:
```yaml
risk_awareness:
  awareness: [<risk_id>]
```

### Category 3: `forwarding`

This stage's outputs cascade to downstream phases where the risk is mitigated. The stage MUST forward sufficient information for downstream mitigation.

**Indicators**:
- Risk owner is a downstream phase (e.g., acceptance, continuous learning)
- This stage's output structure must include fields that downstream consumes for mitigation
- Risk awareness propagates via SOT or output contract

**Example placement**:
```yaml
risk_awareness:
  forwarding:
    <downstream_phase_or_stage>: [<risk_id>]
```

## Classification Procedure

### Step 1: Read Upstream Risk Register

Identify all risk entries. For each entry, note:
- `id` (e.g., R-NNN, RISK-N, threat-N)
- `title` / `description`
- `owner` (which workflow/phase is primarily responsible)
- `mitigation` (steps that resolve or reduce the risk)
- `awareness_loci` (upstream "Risk Awareness Coverage Map" if present)

### Step 2: For Each Risk, Decide Category per Stage

Apply rule cascade:

```
For each risk R:
  For each workflow stage S:
    if R.owner == this_workflow AND S contains the mitigation step:
      classify as direct_responsibility
    elif S interacts with R (input/processing/output affected):
      classify as awareness
    elif S's output cascades to a downstream phase that mitigates R:
      classify as forwarding to that phase
    else:
      no entry needed for this stage
```

### Step 3: Cross-Validate Coverage

Run coverage check:

```python
risks_with_this_workflow_owner = filter(risk_register, owner=this_workflow)
direct_owners = {}
for stage in workflow.stages:
    for r in stage.risk_awareness.direct_responsibility:
        direct_owners.setdefault(r, []).append(stage.id)

# Every owned risk must have a direct_responsibility stage
uncovered = [r for r in risks_with_this_workflow_owner if r not in direct_owners]
assert not uncovered, f"Risks without direct mitigation stage: {uncovered}"

# Awareness coverage map: every risk in upstream "awareness map" must appear
all_awareness = set()
for stage in workflow.stages:
    for r in stage.risk_awareness.awareness + flatten(stage.risk_awareness.forwarding):
        all_awareness.add(r)

upstream_awareness_map = parse_upstream_risk_awareness_map(risk_register)
missing_awareness = upstream_awareness_map - all_awareness
assert not missing_awareness, f"Risks in upstream awareness map missing: {missing_awareness}"
```

## Common Patterns

### Pattern A: Single-Risk-Single-Stage Direct Mitigation

Most common pattern.

```yaml
# Workflow stage that directly mitigates risk R-NNN
risk_awareness:
  direct_responsibility: [<risk_id>]
```

### Pattern B: Risk Spans Multiple Stages

Some risks have multi-step mitigation across stages.

```yaml
# Stage A — first mitigation step (e.g., schema validation)
risk_awareness:
  direct_responsibility: [<risk_id> (step 1)]

# Stage B — second mitigation step (e.g., runtime check)
risk_awareness:
  direct_responsibility: [<risk_id> (step 2)]
```

Document split in stage notes; both stages share `direct_responsibility` for the same risk.

### Pattern C: Stage Aware of Multiple Risks

Common for stages that aggregate or render output.

```yaml
risk_awareness:
  awareness: [<risk_id_1>, <risk_id_2>, <risk_id_3>]
  direct_responsibility: [<risk_id_4>]
```

### Pattern D: Cascade to Downstream Phase

```yaml
risk_awareness:
  forwarding:
    phase_4d_implementation: [<risk_id>]
    phase_5b_acceptance: [<risk_id>]
    phase_6_continuous_learning: [<risk_id>]
```

### Pattern E: Cross-Phase Mitigation Chain

A single risk may be mitigated incrementally across phases. Each phase's stage that contributes is a `direct_responsibility` for its layer.

```yaml
# This workflow's stage contributes to multi-phase mitigation
risk_awareness:
  direct_responsibility: [<risk_id> (Phase 3 layer contribution)]
  forwarding:
    phase_4f_integration: [<risk_id> (final closure)]
```

## Examples Across Domains

### Implementation Pipeline (any workflow)

```yaml
# Stage that validates inputs (direct mitigation for input-validation risks)
risk_awareness:
  direct_responsibility: [<input_validation_risk>]
  awareness: [<sanitization_risk>]
```

### Medical AI Workflow

```yaml
# Stage that applies bias correction
risk_awareness:
  direct_responsibility: [demographic-bias-risk]
  awareness: [false-negative-risk, alert-fatigue-risk]
  forwarding:
    clinical-validation-phase: [domain-shift-risk]
```

### Financial Risk Model

```yaml
# Stage that validates input market data
risk_awareness:
  direct_responsibility: [data-quality-risk]
  awareness: [regime-change-risk, model-overfitting-risk]
```

### Legal Compliance Pipeline

```yaml
# Stage that applies jurisdiction-specific rules
risk_awareness:
  direct_responsibility: [jurisdiction-drift-risk]
  awareness: [statute-amendment-risk]
  forwarding:
    audit-phase: [regulatory-coverage-risk]
```

### Security / Threat Detection Pipeline

```yaml
risk_awareness:
  direct_responsibility: [injection-attack-risk]
  awareness: [exfiltration-risk, privilege-escalation-risk]
  forwarding:
    incident-response-phase: [persistence-risk]
```

### Academic Systematic Review

```yaml
# Stage applying eligibility criteria
risk_awareness:
  direct_responsibility: [selection-bias-risk]
  awareness: [publication-bias-risk]
  forwarding:
    meta-analysis-phase: [heterogeneity-risk]
```

## Risk Status Update Discipline

When workflow.md generation closes (Phase 3 closure or equivalent), update upstream risk register:

```markdown
## Phase 3 Closure Updates

### Risks with this-workflow stage `direct_responsibility`

| Risk ID | Status Before | Status After | Mitigation Stage |
|---|---|---|---|
| <risk_id> | OPEN | MITIGATED at Workflow layer | <stage_id> |
| <risk_id> | PARTIALLY MITIGATED | MITIGATED at Workflow layer | <stage_id> |

### Risks with awareness extension

| Risk ID | Awareness Locus Added | Status |
|---|---|---|
| <risk_id> | <stage_id> | unchanged |
```

Cross-cutting D (Risk Register) integration: workflow.md is recorded in risk register as a mitigation locus for direct-responsibility risks.

## Anti-Patterns

| Anti-Pattern | Why Forbidden | Fix |
|---|---|---|
| Risk register has owner=this-workflow but no stage has `direct_responsibility` | Risk is unowned within workflow; cannot be closed | Add `direct_responsibility` to most-relevant stage |
| Same risk has `direct_responsibility` in 3+ stages without rationale | Ambiguous which stage failure indicates risk realization | Either split risk into sub-risks (R-NNN.a, R-NNN.b) or assign to most-responsible stage |
| Stage has `awareness` for irrelevant risks | Noise; obscures true awareness | Remove unrelated risks |
| `forwarding` to nonexistent downstream phase | Cascade chain broken | Verify downstream phase exists OR remove forwarding |
| Risk register entry not classified by any workflow stage | Coverage gap | Either add awareness/direct/forwarding OR document why workflow doesn't interact |
| Risk ID format mismatch with upstream register | ID lookup fails | Use exact upstream IDs |
