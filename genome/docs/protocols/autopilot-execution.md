# Autopilot Execution Protocol

> This document is a detailed checklist for executing workflows in Autopilot mode.
> Separated from CLAUDE.md — reference only during workflow execution.

## Activation Pattern

| User Command | Behavior |
|-------------|----------|
| "Run in autopilot mode", "Execute workflow in automatic mode", "Execute fully automatic" | Set SOT `autopilot.enabled: true` then start workflow |
| "Deactivate autopilot", "Switch to manual mode" | Set SOT `autopilot.enabled: false` — applies from next `(human)` stage |

## Checkpoint Behavior

| Checkpoint | Autopilot Behavior |
|-----------|-------------------|
| `(human)` + Slash Command | Generate complete deliverable → auto-approve with quality-maximization defaults → record decision log |
| AskUserQuestion | Auto-select quality-maximization option among choices → record decision log |
| `(hook)` exit code 2 | **No change** — block as is, deliver feedback, retry |

## Decision Log

Auto-approved decisions recorded in `autopilot-logs/step-N-decision.md`: stage, options, selection rationale (based on Absolute Criterion 1).
Standard Decision Log template: `references/autopilot-decision-template.md`

## Runtime Intensification Mechanisms

| Layer | Mechanism | Intensification Details |
|-------|-----------|------------------------|
| **Hook** (Deterministic) | `restore_context.py` — SessionStart | Inject 6 execution rules + previous stage deliverable validation results into context when Autopilot active |
| **Hook** (Deterministic) | `generate_snapshot_md()` — Snapshot | Preserve Autopilot status + Agent Team status sections with IMMORTAL priority |
| **Hook** (Deterministic) | `generate_context_summary.py` — Stop | Detect auto-approval patterns → generate supplementary Decision Log if missing (safety net) |
| **Hook** (Deterministic) | `update_work_log.py` — PostToolUse | Track stage progression with `autopilot_step` field |
| **Prompt** (Behavioral induction) | Execution Checklist (below) | Specify mandatory actions at stage start/execution/completion |

> Hook layer accesses SOT read-only only (Absolute Criterion 2 compliant), writing only to `context-snapshots/` and `autopilot-logs/`.

---

## Execution Checklist (MANDATORY)

When executing workflows in Autopilot mode, **must** perform the following checklist for each stage.

### Before each stage starts
- [ ] Verify SOT `current_step`
- [ ] Verify previous stage deliverable file exists + is not empty
- [ ] Verify previous stage deliverable path recorded in SOT `outputs`
- [ ] Read stage `Verification` criteria — recognize "100% completion" definition first (AGENTS.md §5.3)

### During stage execution
- [ ] Execute all stage work **completely** (no abbreviations — Absolute Criterion 1)
- [ ] Generate deliverable in **complete quality**

### After stage completion (Verification Gate — only stages with `Verification` field)
- [ ] Save deliverable file to disk
- [ ] Self-verify deliverable against each `Verification` criterion
- [ ] If failure criterion present:
  - [ ] Check+consume P1 retry budget: `python3 .claude/hooks/scripts/validate_retry_budget.py --step N --gate verification --project-dir . --check-and-increment`
  - [ ] `can_retry: true` → **Perform Abductive Diagnosis** (see diagnosis subsection below) → re-execute based on diagnosis
  - [ ] `can_retry: false` → User escalation (retry budget exhausted, counter not incremented)
- [ ] Verify all criteria PASS
- [ ] Create `verification-logs/step-N-verify.md`
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_verification.py --step N --project-dir .`
- [ ] Verify P1 result `valid: true` (all V1a-V1c passed)

### After stage completion (Cross-Step Traceability — only stages with traceability criterion in Verification)
- [ ] Verify deliverable contains minimum 3 `[trace:step-N:section-id]` markers
- [ ] All markers reference only previous stages (no forward references)
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_traceability.py --step N --project-dir .`
- [ ] Verify P1 result `valid: true` (all CT1-CT5 passed)
- [ ] If CT3 WARNING (unresolved section ID) present, re-verify marker accuracy

### After stage completion (Domain Knowledge Structure — only workflows using DKS pattern, optional)
- [ ] DKS construction stage: Run P1 validation: `python3 .claude/hooks/scripts/validate_domain_knowledge.py --project-dir .`
- [ ] Verify P1 result `valid: true` (all DK1-DK5 passed)
- [ ] DKS reference stage (deliverable contains `[dks:xxx]` markers): Run P1 cross-validation: `python3 .claude/hooks/scripts/validate_domain_knowledge.py --project-dir . --check-output --step N`
- [ ] Verify P1 cross-validation result `valid: true` (all DK6-DK7 inclusive passed)

### After stage completion (pACS — perform after Verification Gate pass)
- [ ] Answer 3 Pre-mortem Protocol questions (AGENTS.md §5.4)
- [ ] Score F, C, L 3 dimensions → derive pACS = min(F, C, L)
- [ ] Create `pacs-logs/step-N-pacs.md`
- [ ] Update SOT `pacs` field (current_step_score, dimensions, weak_dimension, history)
- [ ] If pACS RED (< 50):
  - [ ] Check+consume P1 retry budget: `python3 .claude/hooks/scripts/validate_retry_budget.py --step N --gate pacs --project-dir . --check-and-increment`
  - [ ] `can_retry: true` → **Perform Abductive Diagnosis** (see diagnosis subsection below) → rework based on diagnosis + re-score
  - [ ] `can_retry: false` → User escalation (retry budget exhausted, counter not incremented)
- [ ] If pACS YELLOW (50-69): Record weak dimension in Decision Log then proceed
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_pacs.py --step N --check-l0 --project-dir .`
- [ ] Verify P1 result `valid: true` (all PA1-PA7 + L0 passed)
- [ ] Record deliverable path in SOT `outputs`
- [ ] Increment SOT `current_step` by 1
- [ ] For `(human)` stages: Create `autopilot-logs/step-N-decision.md`
- [ ] For `(human)` stages: Add to SOT `auto_approved_steps`

### Additional checklist for `(team)` stages
- [ ] Right after `TeamCreate` → record SOT `active_team` (name, status, tasks_pending)
- [ ] Each Teammate performs self-verification against their Task's validation criteria before reporting (L1 — AGENTS.md §5.3)
- [ ] Each Teammate performs self-scored pACS after L1 pass (L1.5 — internal completion, include score in report message)
- [ ] When each Teammate completes → Team Lead performs comprehensive verification (L2) against stage validation criteria + derives stage pACS
- [ ] If L2 FAIL or Teammate pACS RED → SendMessage with specific feedback + re-execution instructions
- [ ] When each Teammate completes → update SOT `active_team.tasks_completed` + `completed_summaries`
- [ ] When all Tasks complete → record SOT `outputs`, increment `current_step` by 1, set `active_team.status` → `all_completed`
- [ ] Right after `TeamDelete` → move SOT `active_team` → `completed_teams`
- [ ] Verify Teammate deliverables include Decision Rationale + Cross-Reference Cues

### After stage completion (Adversarial Review — only stages with `Review: @reviewer|@fact-checker`)
- [ ] Call Sub-agent specified in `Review:` field (recommended: `isolation: "worktree"` — protect Orchestrator context, details: `reviewer.md § Context Isolation`)
- [ ] Save review report to `review-logs/step-N-review.md`
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_review.py --step N --project-dir . --check-pacs-arithmetic`
- [ ] Verify P1 result `valid: true` (all R1-R5 passed)
- [ ] Verify Verdict:
  - [ ] PASS → proceed to next stage (including Translation)
  - [ ] FAIL → Check+consume P1 retry budget: `python3 .claude/hooks/scripts/validate_retry_budget.py --step N --gate review --project-dir . --check-and-increment`
  - [ ] `can_retry: true` → **Perform Abductive Diagnosis** (see diagnosis subsection below) → rework based on diagnosis
  - [ ] `can_retry: false` → User escalation (retry budget exhausted, counter not incremented)
- [ ] If pACS Delta ≥ 15 → record in Decision Log + document re-calibration reason
- [ ] Do not execute Translation in Review FAIL state

### When Quality Gate FAIL — Abductive Diagnosis (perform if retry available)
- [ ] Step A — P1 pre-evidence collection: `python3 .claude/hooks/scripts/diagnose_context.py --step N --gate {verification|pacs|review} --project-dir .`
- [ ] Check Fast-Path: `fast_path.eligible == true` → FP1/FP2 immediate re-execution, FP3 user escalation
- [ ] If no Fast-Path → Step B — LLM diagnosis: analyze root cause based on evidence bundle + hypothesis prioritization
- [ ] Create diagnosis log: `diagnosis-logs/step-N-{gate}-{timestamp}.md`
- [ ] Step C — P1 post-validation: `python3 .claude/hooks/scripts/validate_diagnosis.py --step N --gate {verification|pacs|review} --project-dir .`
- [ ] Verify P1 result `valid: true` (all AD1-AD10 passed)
- [ ] Execute rework based on selected hypothesis (H1/H2/H3/H4) per diagnosis result

### After stage completion (Translation — only stages with `Translation: @translator`)
- [ ] Call `@translator` sub-agent (include reference to `translations/glossary.yaml`)
- [ ] Verify translation file (`*.ko.md`) exists on disk
- [ ] Verify translation file not empty
- [ ] Record translation path in SOT `outputs.step-N-ko`
- [ ] Verify `translations/glossary.yaml` updated
- [ ] Complete Translation pACS scoring (Ft/Ct/Nt) (per `@translator` Step 4, AGENTS.md §5.4)
- [ ] Create Translation pACS log (`pacs-logs/step-N-translation-pacs.md`)
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_translation.py --step N --project-dir . --check-pacs --check-sequence`
- [ ] Verify P1 result `valid: true` (all T1-T9 + sequence passed)

---

## NEVER DO

- Do not increment `current_step` by 2 or more at once
- Do not proceed to next stage without deliverable
- Never skip quality for "automation sake" — Absolute Criterion 1 violation
- Never ignore `(hook)` exit code 2 blocks
- Never let Teammate directly modify SOT in `(team)` stage — only Team Lead updates SOT
- Never initialize `active_team` as empty object on session restore — must preserve existing `completed_summaries` (conservative resumption protocol)
- Never proceed to next stage with failed Verification criterion — user escalation after max 10 retries (15 if ULW active)
- Never falsely record Verification criterion as "all PASS" — specific Evidence required for each criterion
- Never skip Pre-mortem Protocol and assign pACS score alone — weakness recognition is prerequisite for scoring
- Never execute pACS independently without Verification Gate — L1 pass is prerequisite for L1.5
- Never assign all pACS scores as 90+ — score consistency with weaknesses identified in Pre-mortem required
- Never execute Translation in Review FAIL state — Review PASS is prerequisite for Translation
- Never PASS Review with 0 issues — P1 validation automatically rejects (R5 check)
- Never score Reviewer pACS after referencing Generator pACS — independent scoring required
- Never retry on quality gate FAIL using same approach without diagnosis — Abductive Diagnosis or Fast-Path required
- Never record only 1 hypothesis in diagnosis log — minimum 2 hypotheses comparison (AD8)
- Never select same hypothesis as previous diagnosis 3 times consecutively — FP3 escalation (I-3 coordination)
