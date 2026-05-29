# Hybrid Architecture Patterns

How to document deterministic + probabilistic boundary in workflow.md when the architecture is hybrid.

## When Hybrid Architecture Documentation Required

Most modern AI workflows are hybrid:

- **RAG**: deterministic retrieval (similarity search, exact match) + probabilistic generation (LLM)
- **Agent + Tool Use**: probabilistic LLM planning + deterministic tool execution
- **Ensemble Methods**: probabilistic N model inferences + deterministic voting/aggregation
- **Citation Generation**: deterministic source matching + probabilistic paraphrase
- **Compliance + LLM**: deterministic rule check + probabilistic explanation
- **Schema-Constrained Generation**: probabilistic LLM + deterministic schema validation

If the upstream spec assigns a `determinism_class` per module (deterministic / probabilistic), workflow.md MUST document the boundary explicitly in the Inherited DNA section.

## Required Block Structure

Add to `Inherited DNA` section:

```markdown
### Hybrid Architecture Boundary

| Module / Stage | Component | Determinism Class | Implementation Primitive |
|---|---|---|---|
| <name> | <function> | deterministic | <(hook) | Sub-agent rule lookup | Skill | code module> |
| <name> | <function> | probabilistic | <Sub-agent LLM call | Agent Team | MCP server> |

**Determinism KPI per class** (per upstream spec):
- **deterministic**: bytes-identical output across N invocations on same input (Hard zero-tolerance)
- **probabilistic**: statistical bound (e.g., variance ≤ X%) measured across N samples

**Rationale**: <upstream spec section> assigns determinism class per module to enforce P1 (Hallucination Prevention) — deterministic modules anchor factual claims; probabilistic modules contribute interpretive narrative within bounded variance.
```

## Implementation Primitive Selection

For each module, select implementation primitive based on determinism class:

### Deterministic Module → Implementation Primitives

| Primitive | When to Use |
|---|---|
| **Code module** (Python/JS function) | Pure computation, lookup, schema validation |
| **(hook)** | CI-time verification (e.g., import-grep CI hook for renderer purity) |
| **Sub-agent (rule lookup)** | When orchestration via agent is cleaner than direct call |
| **Skill** | Reusable deterministic logic shared across workflows |
| **MCP server** (deterministic mode) | External deterministic service (e.g., ISBN lookup, regex API) |

### Probabilistic Module → Implementation Primitives

| Primitive | When to Use |
|---|---|
| **Sub-agent (LLM call)** | Single deep-context probabilistic inference |
| **Agent Team** | Multi-perspective parallel (Self-Consistency, ensemble) |
| **MCP server** (LLM-backed) | External LLM service with stable interface |

## Boundary Patterns

### Pattern A: Sequential Deterministic-Probabilistic-Deterministic

Most common pattern: deterministic input validation + probabilistic generation + deterministic output validation.

```markdown
### Hybrid Architecture Boundary

| Module | Component | Class | Primitive |
|---|---|---|---|
| Input Validation | schema_validate, sanitize | deterministic | code module |
| Generation | LLM narrative expansion | probabilistic | Sub-agent |
| Output Validation | schema_validate, citation match | deterministic | code module + (hook) |
```

### Pattern B: Interleaved (Deterministic Anchors + Probabilistic Bridges)

When deterministic anchors structure probabilistic bridges (RAG-like).

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Retrieval | similarity search, ranking | deterministic | code module |
| Synthesis | LLM grounded generation | probabilistic | Sub-agent |
| Source Linking | citation match | deterministic | code module |
| Reranking | LLM-as-judge OR algorithm | hybrid (probabilistic OR deterministic per choice) | Sub-agent OR code module |
```

### Pattern C: Layered (Probabilistic Wrapped by Deterministic)

When probabilistic layer is wrapped by deterministic safety/quality gates.

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Pre-Filter | keyword screen | deterministic | code module |
| LLM Layer | intent classifier | probabilistic | Sub-agent |
| Conservative Resolution | max(deterministic, probabilistic) verdict | deterministic | code module |
| Post-Filter | schema validation | deterministic | code module |
```

### Pattern D: Parallel Hybrid (Deterministic + Probabilistic Cross-Check)

When deterministic and probabilistic both compute the same target; results cross-checked.

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Rule-Based Classification | lookup table | deterministic | code module |
| LLM Classification | LLM intent classifier | probabilistic | Sub-agent |
| Consensus / Disagreement Handler | resolution logic | deterministic | code module |
```

## Determinism KPI Articulation

For each determinism class, articulate the upstream KPI:

### Deterministic KPI

```markdown
**Deterministic modules KPI**:
- Same input tuple → bytes-identical output across N≥10 invocations
- Hard zero-tolerance — any single non-determinism instance fails KPI
- Verified via snapshot test fixture (e.g., 10 stratified inputs × 10 runs × SHA256 hash equality)
- Source: <upstream spec section> (e.g., PRD §X.Y determinism KPI)
```

### Probabilistic KPI

```markdown
**Probabilistic modules KPI**:
- Statistical bound: <metric> ≤ <threshold> (e.g., free-portion deviation ≤ 2%)
- Measured via: <eval method> (e.g., sentence-embedding cosine over N samples)
- Sample size: <N>
- Source: <upstream eval plan section>
```

## Boundary Enforcement (Workflow Stage Level)

Each stage referencing a determinism class MUST:

1. Document the class in `spec_module_ref` (e.g., `determinism_class: deterministic`)
2. Match implementation primitive to class (deterministic → code/hook/Skill; probabilistic → Sub-agent/Team)
3. Include determinism-class-appropriate Verification criteria
4. Carry KPI through to integration test (Phase 4f equivalent)

```yaml
# Stage targeting deterministic module
spec_module_ref:
  - doc: <spec>
    section: "§<X> — <module>"
    invariants_targeted: [<inv-1>, <inv-2>]
    determinism_class: deterministic

implementation_primitive: code module + (hook for purity check)

verification:
  - "[ ] Snapshot test: 10 stratified inputs × 10 invocations → bytes-identical output (SHA256 hash equality)"
  - "[ ] No LLM call in module code path (verified via import-grep)"
  - "[ ] No random.seed() in module code path"
```

```yaml
# Stage targeting probabilistic module
spec_module_ref:
  - doc: <spec>
    section: "§<Y> — <module>"
    invariants_targeted: [<inv-3>]
    determinism_class: probabilistic

implementation_primitive: Sub-agent (LLM call) OR Agent Team (multi-sample)

verification:
  - "[ ] Output meets statistical bound: <metric> ≤ <threshold>"
  - "[ ] Eval methodology per upstream Eval Plan §<X>"
```

## Examples Across Domains

### Implementation Pipeline (any workflow)

```markdown
### Hybrid Architecture Boundary

| Module | Component | Class | Primitive |
|---|---|---|---|
| §3 Orchestrator | pipeline control | deterministic | code module |
| §4 Module 1 Layer 1 | keyword screen | deterministic | code module |
| §4 Module 1 Layer 2 | LLM intent classifier | probabilistic | Sub-agent |
| §6 Module 3 | rule lookup | deterministic | code module |
| §7 Module 4 | LLM narrative expansion (Self-Consistency N=3) | probabilistic | Sub-agent (sequential) OR Agent Team (parallel) |
| §9 Module 6 | citation classifier | deterministic | code module |
| §10 Module 7 | renderer | deterministic | code module + (hook) |
| §12 Module 9 | aggregation | deterministic | code module |
```

### RAG Pipeline

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Retrieval | embedding similarity + filter | deterministic | code module |
| Reranking | cross-encoder | probabilistic | Sub-agent |
| Source Selection | top-k threshold | deterministic | code module |
| Generation | LLM grounded synthesis | probabilistic | Sub-agent |
| Citation Linking | claim-to-source match | deterministic | code module |
```

### Medical AI Inference

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Image Preprocessing | normalization | deterministic | code module |
| Diagnostic Classifier | CNN inference | probabilistic | code module (ML model) |
| Confidence Calibration | Platt scaling | deterministic | code module |
| Demographic Adjustment | rule-based correction | deterministic | code module |
| Explanation Generation | LLM rationale | probabilistic | Sub-agent |
```

### Legal Contract Analysis

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Clause Extraction | NER + rule | deterministic | code module |
| Clause Classification | LLM | probabilistic | Sub-agent |
| Jurisdiction Match | lookup table | deterministic | code module |
| Risk Assessment | LLM with rules | hybrid | Agent Team |
| Citation Generation | precedent lookup | deterministic | code module |
```

### Financial Risk Model

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Market Data Validation | schema + range check | deterministic | code module |
| Volatility Forecast | GARCH model | probabilistic | code module (statistical model) |
| Stress Scenario | rule-based | deterministic | code module |
| Narrative Report | LLM | probabilistic | Sub-agent |
```

### Compliance Pipeline

```markdown
| Module | Component | Class | Primitive |
|---|---|---|---|
| Rule Match | regex + ruleset | deterministic | code module |
| Edge-Case Classification | LLM | probabilistic | Sub-agent |
| Conservative Resolution | max-severity rule | deterministic | code module |
| Audit Trail | logging | deterministic | (hook) |
```

## Anti-Patterns

| Anti-Pattern | Why Forbidden | Fix |
|---|---|---|
| Hybrid module without explicit boundary documentation | Determinism KPI cannot be enforced per class | Add Hybrid Architecture Boundary table |
| LLM in deterministic module | Determinism KPI breached | Move LLM call to separate probabilistic module; conservative resolution if cross-check needed |
| Random seed without deterministic seed-pinning | Bytes-identical output not guaranteed | Pin seed at module init (e.g., random.seed(0)) OR move to probabilistic class |
| Probabilistic module without statistical bound articulation | Quality KPI undefined | Articulate metric + threshold per upstream eval plan |
| Implementation primitive mismatched with class | E.g., code module for probabilistic LLM, or Sub-agent for pure lookup | Match per primitive selection table |
| LLM call inside renderer/output module | Defeats purity guarantee | Move LLM to upstream stage; renderer reads pre-computed result |
