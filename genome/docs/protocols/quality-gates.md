# Quality Gates & P1 Validation

> This document specifies the detailed architecture of 4-layer quality assurance and P1 hallucination prevention.
> Separated from CLAUDE.md — reference when designing, debugging, or extending quality gates.

## 4-Layer Quality Assurance Architecture (L0 → L1 → L1.5 → L2)

The Orchestrator increments `current_step` sequentially only. Upon completion of each step, it must pass a maximum of 4 validation layers to proceed:

1. **L0 Anti-Skip Guard** (Deterministic) — Deliverable file existence + minimum size (100 bytes). Performed by the Hook layer's `validate_step_output()` function.
2. **L1 Verification Gate** (Semantic) — Confirms deliverable achieves 100% of `Verification` criteria through agent self-verification. Failure triggers re-execution of affected sections only (max 10 attempts). Recorded in `verification-logs/step-N-verify.md`.
3. **L1.5 pACS Self-Rating** (Confidence) — Performs Pre-mortem Protocol, then scores 3 dimensions (F/C/L). Recorded in `pacs-logs/step-N-pacs.md`. RED (< 50) triggers rework.
4. **[L2 Calibration]** (Optional) — Separate `@verifier` agent cross-validates pACS score. High-risk steps only.

> Steps without a `Verification` field proceed with Anti-Skip Guard only (backward compatible). Details: `AGENTS.md §5.3`, `§5.4`

---

## P1 Hallucination Prevention

Python code enforces 100% accuracy for repetitive operations.

### (1) Knowledge Index Schema Validation
`_validate_session_facts()` ensures RLM-required keys (session_id, tags, final_status, diagnosis_patterns, etc. — 11 keys total) exist before Knowledge Index write — supplies safe defaults if missing.

### (2) Partial Failure Isolation
`archive_and_index_session()` ensures archive file write failure does NOT block Knowledge Index update — protects RLM core assets.

### (3) SOT Write Pattern Validation
`setup_init.py`'s `_check_sot_write_safety()` detects co-existence of SOT filename + write pattern in Hook scripts via AST function-boundary analysis (Tier 1: blocks SOT reference in non-SOT scripts; Tier 2: validates per-function write patterns in SOT-aware scripts).

### (4) SOT Schema Validation
`validate_sot_schema()` validates workflow `state.yaml` structural integrity across 8 items:
- **S1-S6**: `current_step` type/range, `outputs` type/key format, future-step deliverable detection, `workflow_status` valid values, `auto_approved_steps` consistency
- **S7**: 5 pacs fields validation (S7a dimensions F/C/L 0-100, S7b current_step_score 0-100, S7c weak_dimension F/C/L, S7d history dict→{score, weak}, S7e pre_mortem_flag string)
- **S8**: 5 active_team fields validation (S8a name string, S8b status partial|all_completed, S8c tasks_completed list, S8d tasks_pending list, S8e completed_summaries dict→dict)

Executed at both SessionStart and Stop hooks.

### (5) Adversarial Review P1 Validation
`validate_review_output()` validates review report structural integrity across 5 items:
- R1: File exists
- R2: Minimum size
- R3: 4 required sections present
- R4: PASS/FAIL explicitly extractable
- R5: Issue table ≥ 1 row

`parse_review_verdict()` — extracts issue severity count via regex.
`calculate_pacs_delta()` — calculates Generator-Reviewer pACS difference (Delta ≥ 15 → re-calibration).
`validate_review_sequence()` — enforces Review PASS → Translation order via file timestamps.
Standalone script: `validate_review.py`.

### (6) Translation P1 Validation
`validate_translation_output()` validates translation deliverable across 7 items:
- T1: File exists, T2: Minimum size, T3: English source exists, T4: .ko.md extension, T5: Non-blank, T6: Heading count ±20%, T7: Code block count matches

`check_glossary_freshness()` — glossary timestamp freshness (T8).
`verify_pacs_arithmetic()` — all pACS logs' min() arithmetic correctness (T9 — generic).
`validate_verification_log()` — verification log V1a-V1c.
`validate_translation.py` mandatorily checks Review verdict=PASS.
Standalone script: `validate_translation.py`.

### (7) pACS P1 Validation
`validate_pacs_output()` validates pACS log across 6 items:
- PA1: File exists, PA2: Minimum size 50 bytes, PA3: ≥ 3 dimension scores (0-100 range), PA4: Pre-mortem section present, PA5: min() arithmetic correctness, PA7: RED block (pACS < 50 → FAIL)
- PA6 (Optional): Score-color zone consistency

Standalone script: `validate_pacs.py`.

### (8) L0 Anti-Skip Guard Code Implementation
`validate_step_output()` — L0 validation 3 items:
- L0a: File exists at SOT `outputs.step-N` path
- L0b: File size ≥ MIN_OUTPUT_SIZE (100 bytes)
- L0c: Non-blank confirmation

Dual validation via `validate_pacs.py --check-l0` for pACS + L0 together.

### (9) Predictive Debugging P1 Validation
`validate_risk_scores()` — risk-scores.json 6 items:
- RS1: Required keys present, RS2: data_sessions integer, RS3: risk_score range, RS4: error_count arithmetic, RS5: resolution_rate range, RS6: top_risk_files sorted + exist

### (10) Retry Budget P1 Validation
`validate_retry_budget.py` — deterministic retry budget judgment:
- RB1: Counter file read, RB2: ULW activation detection, RB3: Budget comparison (`retries_used < max_retries`)
- `max_retries`: 3 when ULW active, 2 when inactive
- `--increment` mode atomically increments counter write

### (11) Abductive Diagnosis P1 Validation
`validate_diagnosis_log()` — diagnosis log 10 items:
- AD1: File exists, AD2: Minimum size 100 bytes, AD3: Gate field matches, AD4: Selected hypothesis present, AD5: ≥ 1 evidence, AD6: Action Plan present, AD7: No forward references, AD8: ≥ 2 hypotheses, AD9: Selected hypothesis consistency, AD10: Previous diagnosis reference (retries > 0)

`diagnose_failure_context()` — pre-evidence collection (retry_history, upstream_evidence, hypothesis_priority, fast_path, raw_evidence). Fast-Path (FP1-FP3) enables deterministic shortcuts.
Standalone scripts: `diagnose_context.py` (pre-analysis), `validate_diagnosis.py` (post-validation).

### (12) Cross-Step Traceability P1 Validation
`validate_cross_step_traceability()` — cross-step traceability 5 items:
- CT1: Trace markers present, CT2: Referenced step deliverable exists, CT3: Section ID resolution (Warning), CT4: Minimum density ≥ 3, CT5: No forward references

Standalone script: `validate_traceability.py`.

### (13) Domain Knowledge Structure P1 Validation
`validate_domain_knowledge()` — domain-knowledge.yaml 7 items:
- DK1: File exists + YAML valid, DK2: metadata required keys, DK3: entities structure, DK4: relations reference integrity, DK5: constraints structure, DK6: Output DKS reference resolution, DK7: Constraint non-violation

Standalone script: `validate_domain_knowledge.py`. Optional — not all workflows require it.

### (14) Workflow.md DNA Inheritance P1 Validation
`validate_workflow_md()` — 8 items:
- W1: File exists, W2: Minimum size 500 bytes, W3: `## Inherited DNA` header, W4: Inherited Patterns table ≥ 3 rows, W5: Constitutional Principles section, W6: CAP references, W7: CT Verification-Validator consistency, W8: DKS Verification-Validator consistency

Standalone script: `validate_workflow.py`. Manually invoked after workflow-generator completion.
