# Asset Consumption Patterns

How to express `asset_dependencies` field per workflow stage.

## The 4 Consumption Patterns

### Pattern 1: `load_at_init`

Asset loaded once at module/process initialization. Asset stays in memory throughout workflow execution.

**Use when**:
- Asset is small enough to hold in memory
- Asset is read frequently across all stages
- Asset version is stable for the duration of execution

**Examples**:
- Lookup tables (rule matrix, classification table, mapping dictionary)
- Configuration files (eval-config.yaml, model parameters)
- Controlled vocabulary (injection keywords, glossary)
- Class taxonomy (section/category/document-type quota maps)

**YAML form**:
```yaml
asset_dependencies:
  - path: <relative/path>
    consumption_pattern: load_at_init
    version_field_propagation: <output_field>
```

### Pattern 2: `per_invocation`

Asset accessed per workflow invocation (e.g., per user, per request, per document, per tenant). Asset may be filtered or sliced based on invocation context.

**Use when**:
- Asset is large and only a slice is needed per invocation
- Asset is invocation-specific (different content per user/request)
- Memory-pinning the entire asset is wasteful

**Examples**:
- User-specific corpus shard (per-tenant retrieval index)
- Localized regulation set (per-jurisdiction)
- Tier-specific lookup (different cells per signature combination)
- Personalization profile

**YAML form**:
```yaml
asset_dependencies:
  - path: <relative/path>
    consumption_pattern: per_invocation
    invocation_key: <field that selects asset slice>
    version_field_propagation: <output_field>
```

### Pattern 3: `conditional_per_unit`

Asset accessed per output unit (claim, sentence, section, item) **only when** triggered by content. Avoids unnecessary lookups when content does not require the asset.

**Use when**:
- Asset is referenced by some but not all outputs
- Triggering condition can be cheaply detected before asset lookup
- Avoiding unnecessary asset access improves latency

**Examples**:
- Citation source matched per claim (not every claim has external source)
- Footnote glossary attached per term occurrence (not every word triggers)
- Conditional safety footer (only on distress-trigger sections)
- Per-language asset (only when locale != default)

**YAML form**:
```yaml
asset_dependencies:
  - path: <relative/path>
    consumption_pattern: conditional_per_unit
    trigger_condition: <when to load>
    version_field_propagation: <output_field>
```

### Pattern 4: `lazy`

Asset loaded only when triggered by error/fallback path. Default path does not access asset.

**Use when**:
- Asset is only needed for fallback / recovery / escalation
- Default path success rate is high; loading asset is wasteful most of the time
- Asset access is expensive (large file, network call, decryption)

**Examples**:
- Fallback corpus on retrieval miss
- Detailed error documentation
- Backup model weights (when primary fails)
- Manual override rules (when automated fails)

**YAML form**:
```yaml
asset_dependencies:
  - path: <relative/path>
    consumption_pattern: lazy
    trigger_condition: <error / fallback condition>
    version_field_propagation: <output_field>
```

## Version Field Propagation

When upstream specs require asset version to flow through workflow output (for traceability + cross-asset consistency check), document the propagation chain.

```yaml
asset_dependencies:
  - path: <asset>.yaml
    consumption_pattern: load_at_init
    version_field_propagation: <output.field_name>
    cross_consistency_checks:
      - <other_asset>.yaml  # versions must align (e.g., output.field_a.version == output.field_b.version)
```

**Why it matters**: integration phase verifies that `state.outputs.step-N.<field>.version` matches `<asset>.yaml.version`. Mismatch indicates:
- Asset was hot-swapped without workflow regeneration
- Cache poisoning
- Cross-asset drift (asset A references asset B's old version)

## Cross-Asset Consistency Patterns

When two or more assets must remain consistent across versions:

### Pattern A: Mirror Dependency

Asset B's version always matches Asset A's version (e.g., generated artifact + source artifact).

```yaml
asset_dependencies:
  - path: source-asset.yaml
    consumption_pattern: load_at_init
  - path: generated-asset.yaml
    consumption_pattern: load_at_init
    cross_consistency_checks:
      - source-asset.yaml: "version must match exactly"
```

### Pattern B: Schema-Reference Dependency

Asset B uses Asset A's schema. B's version must be in compatible range with A.

```yaml
asset_dependencies:
  - path: schema-asset.yaml
    consumption_pattern: load_at_init
  - path: data-asset.yaml
    consumption_pattern: load_at_init
    cross_consistency_checks:
      - schema-asset.yaml: "schema_version field >= data-asset.required_schema_version"
```

### Pattern C: Independent Versions

Assets evolve independently; consumer code handles version differences.

```yaml
asset_dependencies:
  - path: asset-a.yaml
    consumption_pattern: load_at_init
  - path: asset-b.yaml
    consumption_pattern: load_at_init
    cross_consistency_checks: []
```

## Asset Coverage Cross-Validation

After all stages have `asset_dependencies` filled, run coverage check:

```python
all_assets_in_cohort = list_assets_at_path("<asset-cohort-path>/")
consumed_by_workflow = set()
for stage in workflow.stages:
    for dep in stage.asset_dependencies:
        consumed_by_workflow.add(dep.path)

unconsumed = set(all_assets_in_cohort) - consumed_by_workflow
if unconsumed:
    print(f"WARNING: Unconsumed assets: {unconsumed}")
    # Decide: remove unused assets, OR add a stage that consumes them, OR document why kept
```

Acceptable reasons for unconsumed assets:
- Asset is used by downstream phase (Phase 4f integration test) not workflow.md itself
- Asset is reserved for future workflow extension
- Asset is documentation-only (e.g., README.md)

## Examples Across Domains

### Implementation Pipeline (any workflow)

```yaml
asset_dependencies:
  - path: <asset-cohort>/rule-matrix.yaml
    consumption_pattern: per_invocation
    invocation_key: matrix_cell_id (constructed from user inputs)
    version_field_propagation: profile.generation_method.rule_component.cell_version
```

### RAG Pipeline

```yaml
asset_dependencies:
  - path: corpus/embeddings.faiss
    consumption_pattern: load_at_init
    version_field_propagation: response.metadata.corpus_version
  - path: corpus/source-documents/
    consumption_pattern: conditional_per_unit
    trigger_condition: claim requires source citation
    cross_consistency_checks:
      - corpus/embeddings.faiss: "embeddings index matches source documents"
```

### Medical AI Inference

```yaml
asset_dependencies:
  - path: models/diagnostic-classifier.onnx
    consumption_pattern: load_at_init
    version_field_propagation: prediction.model_version
  - path: clinical-guidelines/conditions.yaml
    consumption_pattern: per_invocation
    invocation_key: predicted_condition_code
```

### Legal Contract Analysis

```yaml
asset_dependencies:
  - path: legal/taxonomy.yaml
    consumption_pattern: load_at_init
  - path: legal/jurisdiction-overrides/
    consumption_pattern: per_invocation
    invocation_key: contract.jurisdiction_code
  - path: legal/precedent-corpus/
    consumption_pattern: conditional_per_unit
    trigger_condition: clause classification == "force_majeure"
```

### Compliance / Audit

```yaml
asset_dependencies:
  - path: regulations/active-rules.yaml
    consumption_pattern: load_at_init
  - path: regulations/violation-taxonomy.yaml
    consumption_pattern: load_at_init
    cross_consistency_checks:
      - regulations/active-rules.yaml: "violation type coverage must align"
```

## Anti-Patterns

| Anti-Pattern | Why Forbidden | Fix |
|---|---|---|
| Stage references asset path that doesn't exist | Phase 4b asset codification will fail | Verify path against asset cohort listing |
| `load_at_init` for very large asset (>1GB) | Memory pressure; slow startup | Use `per_invocation` with sharding OR `lazy` with caching |
| `per_invocation` for stable lookup table | Wasteful repeated load | Use `load_at_init` |
| Missing `version_field_propagation` when version traceability is required | Phase 4f cannot verify asset version match | Add propagation field; verify in integration test |
| Hot-swapping asset without workflow regeneration | SOT drift; cross-document inconsistency | Bump workflow version when asset version changes; rerun cross-consistency check |
| Asset consumed by stage but not in upstream cohort | Asset cohort incomplete | Add asset to upstream Phase 2.5 cohort OR remove dependency |
