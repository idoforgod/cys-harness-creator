# Cost Budget Allocation Guide

How to allocate upstream Cost-Latency Policy budgets to workflow stages.

## Top-Down Allocation Procedure

### Step 1: Read Upstream Cost-Latency Policy

Locate upstream policy document (e.g., `<workflow>-prd.md §<X> Cost-Latency Policy`). Extract:

- **Per-execution LLM call budget**: total + median + worst-case
- **Per-execution token budget**: total + median + worst-case
- **API call budgets** per service (if external APIs used)
- **Latency budget** (overall + per-phase if specified)
- **Rate-limit tier** (subscription, API tier, unbounded)
- **Worst-case escalation policy** (e.g., "if budget exceeded, surface to user vs auto-retry")

### Step 2: Decompose to Stage Budgets

For each stage, decide:

- Number of LLM calls (sequential N+1 multiplied by retries)
- Token consumption per call (input + output)
- API calls to external services
- Latency contribution (sequential sum or parallel max)

Apply allocation rules:

| Stage Type | Typical LLM Call Budget |
|---|---|
| Input validation / sanitization | 0-1 per field (deterministic primary; LLM Layer 2 optional) |
| Lookup / classification | 0 (deterministic) |
| Generation with Self-Consistency N | N + 1 integration |
| Multi-step generation | N × stages |
| Aggregation / scoring | 0 (deterministic) |
| Rendering | 0 (deterministic per Spec) |
| HITL gate | 0 (no LLM; user interaction) |

### Step 3: Verify Total ≤ Policy Budget

```python
total_llm_calls = sum(stage.cost_budget.llm_calls for stage in workflow.stages)
total_tokens = sum(stage.cost_budget.token_budget for stage in workflow.stages)
total_latency = sum(stage.cost_budget.latency_budget_ms for stage in workflow.stages if sequential else max(...) for parallel groups)

assert total_llm_calls <= upstream_policy.llm_calls.total
assert total_tokens <= upstream_policy.token_budget.total
assert total_latency <= upstream_policy.latency_budget_ms.p95
```

### Step 4: Document Worst-Case Escalation per Stage

For stages with retry loops or fallback paths, document escalation:

```yaml
cost_budget:
  llm_calls: "median 4 / worst 20 (5 retries × 4 calls)"
  worst_case_escalation: "5th-failure handoff per upstream Spec §<section>; 4 user options surfaced"
```

## Budget Range Notation

When budget varies by content/path, use range notation:

```yaml
cost_budget:
  llm_calls: "1-5"            # range
  token_budget: "200-800"      # range
  latency_budget_ms: 1500      # single value
```

For Self-Consistency / multi-sample patterns:

```yaml
cost_budget:
  llm_calls: "N+1 (e.g., 4 for N=3)"
  token_budget: "(N + 1) × per_call_budget"
```

## Hierarchical Budget Patterns

### Pattern A: Flat Allocation

Each stage gets fixed share of total budget.

```yaml
# Total: 100 LLM calls, 5 stages -> 20 calls per stage
stage_1.cost_budget.llm_calls: 20
stage_2.cost_budget.llm_calls: 20
stage_3.cost_budget.llm_calls: 20
stage_4.cost_budget.llm_calls: 20
stage_5.cost_budget.llm_calls: 20
```

Rarely optimal; flat allocation usually wastes budget.

### Pattern B: Weighted Allocation

Stages with higher LLM workload get larger shares.

```yaml
# Total: 200 LLM calls
stage_1 (input validation): 5
stage_2 (mapping): 10
stage_3 (generation Self-Consistency N=3): 132 (33 sections × 4 calls)
stage_4 (aggregation): 0
stage_5 (rendering): 0
stage_6 (HITL): 0
# Reserve: 53 (25%) for retries + worst-case
```

Most common for production workflows.

### Pattern C: Probabilistic Allocation

Median + worst-case ranges per stage; total uses worst-case sum vs rate-limit tier.

```yaml
stage_1.cost_budget:
  llm_calls: "median 5 / worst 10"
stage_2.cost_budget:
  llm_calls: "median 10 / worst 30"
stage_3.cost_budget:
  llm_calls: "median 132 / worst 660"

# Aggregate
median_total: 147
worst_total: 700
upstream_policy_worst_case_limit: 845
# OK: 700 ≤ 845
```

### Pattern D: Tier-Differentiated Allocation

Different rate-limit tiers for different stages (rare but useful for hybrid pipelines).

```yaml
stage_1 (sanitization).cost_budget:
  api_calls:
    - service: openai
      count: 1
      rate_limit_tier: tier_4

stage_2 (deep analysis).cost_budget:
  api_calls:
    - service: anthropic
      count: 5
      rate_limit_tier: subscription
```

## Worst-Case Escalation Strategies

When stage budget is exceeded at runtime, document the escalation:

| Strategy | Description | Use Case |
|---|---|---|
| `auto_retry_with_backoff` | Exponential backoff retry | Transient rate limits |
| `user_handoff` | Surface to user with options | Quality-over-speed workflows |
| `fallback_to_simpler_path` | Use cheaper model / fewer samples | Cost-sensitive |
| `placeholder_emission` | Emit placeholder; mark for re-generation | Async batch workflows |
| `abort_and_preserve_state` | Stop execution; preserve partial state | High-stakes workflows |

Document choice per stage:

```yaml
cost_budget:
  llm_calls: "median 4 / worst 20"
  worst_case_escalation: "user_handoff (4 options: continue / fallback / placeholder / abort)"
```

## Cost-Latency Trade-Off Documentation

When stage design choices have cost/latency trade-offs, document explicitly:

```yaml
cost_budget:
  llm_calls: 4
  latency_budget_ms: "p95: 8000"
  trade_off_rationale: |
    Self-Consistency N=3 (sequential) chosen over N=3 parallel:
    - Sequential: 8s p95 latency, no rate-limit pressure
    - Parallel: 3s p95 latency, but rate-limit failure mode
    - Quality-priority decision per Cost-Latency Policy §X.Y
```

## Examples Across Domains

### LLM API Workflow (any)

```yaml
cost_budget:
  llm_calls: 4
  token_budget: "input 500 + output 1500 = 2000 per call × 4 = 8000"
  latency_budget_ms: "p95: 5000"
  rate_limit_tier: subscription
  worst_case_escalation: "user_handoff"
```

### Cloud Compute Pipeline

```yaml
cost_budget:
  cpu_hours: 0.5
  gpu_hours: 0.1
  api_calls:
    - service: bigquery
      count: 3
      rate_limit_tier: project_quota_500qps
  latency_budget_ms: 30000
```

### Real-Time Inference

```yaml
cost_budget:
  llm_calls: 1   # single tight-budget call for SLA
  token_budget: 200
  latency_budget_ms: "p95: 200, p99: 500"
  rate_limit_tier: dedicated_capacity
  worst_case_escalation: fallback_to_simpler_path
```

### High-Throughput Batch

```yaml
cost_budget:
  parallelism: 32
  llm_calls_per_unit: 1
  total_units: "<varies>"
  rate_limit_tier: api_tier_5_50000_rpm
  worst_case_escalation: auto_retry_with_backoff
```

### Cost-Optimized Inference

```yaml
cost_budget:
  llm_calls:
    primary_model: 1
    fallback_cheap_model: 1   # only on primary failure
  trade_off_rationale: "Cheap fallback selected when primary fails to balance cost vs quality per policy §X"
```

## Cross-Stage Budget Validation

Implement coverage check:

```python
def validate_budgets(workflow, upstream_policy):
    median_calls = sum(stage.cost_budget.llm_calls.median for stage in workflow.stages)
    worst_calls = sum(stage.cost_budget.llm_calls.worst for stage in workflow.stages)

    median_tokens = sum(stage.cost_budget.token_budget.median for stage in workflow.stages)
    worst_tokens = sum(stage.cost_budget.token_budget.worst for stage in workflow.stages)

    # Median should fit comfortably
    assert median_calls <= upstream_policy.median_call_limit
    assert median_tokens <= upstream_policy.median_token_limit

    # Worst-case must respect rate limit tier
    rate_limit = upstream_policy.rate_limit_tier_capacity
    assert worst_calls / upstream_policy.execution_window_seconds <= rate_limit

    # Latency: sequential sum vs p95 budget
    sequential_latency_p95 = sum(stage.cost_budget.latency_budget_ms.p95
                                  for stage in workflow.stages if not stage.parallel_group)
    parallel_groups_p95 = max(...)
    total_latency_p95 = sequential_latency_p95 + parallel_groups_p95
    assert total_latency_p95 <= upstream_policy.latency_p95_target
```

## Anti-Patterns

| Anti-Pattern | Why Forbidden | Fix |
|---|---|---|
| Sum of stage budgets > upstream policy total | Cost-Latency Policy violation | Reduce per-stage budget OR raise upstream policy via ADR |
| Worst-case sum exceeds rate-limit tier | Production rate-limit failure | Lower N (multi-sample), use sequential vs parallel, upgrade tier with ADR |
| No `worst_case_escalation` for retry-loop stages | Failure mode unspecified | Document escalation strategy |
| Latency p95 budget without p99 awareness | Tail latency unmanaged | Add p99 ceiling; design timeout |
| `cost_budget` references nonexistent service | Operational config mismatch | Verify service name against deployment |
| Hard-coded numeric budget when upstream is in flux | Stale policy compliance | Reference upstream policy section path; bump on policy revision |
