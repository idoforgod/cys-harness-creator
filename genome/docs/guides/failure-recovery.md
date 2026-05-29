# Failure Recovery Guide — Orchestrator Perspective

This guide provides comprehensive instructions for handling workflow failures and implementing Sisyphus Persistence (I-1) recovery strategies.

**Audience**: Orchestrator agents executing workflows  
**Scope**: (human) and (team) stage failures, verification gate failures, sub-agent invocation failures  
**Related**: `docs/protocols/ulw-mode.md` (I-1 Sisyphus Persistence), `docs/protocols/quality-gates.md` (verification failures)

---

## Part 1: Failure Detection & Classification

### 1.1 Failure Detection Points

Failures can occur at 6 critical points in workflow execution:

| Detection Point | Trigger | Severity |
|---|---|---|
| **Stage execution** | Deliverable generation incomplete/incorrect | Variable (P1-P4) |
| **L0 Anti-Skip Guard** | Stage skipped or step mismatch detected | CRITICAL (exit workflow) |
| **L1 Verification Gate** | Verification criteria not met (status=FAIL) | HIGH (retry or escalate) |
| **L1.5 pACS Self-Rating** | pACS score below threshold (<50) | MEDIUM (enhanced scrutiny) |
| **L2 Calibration** | Team Lead rejects aggregated pACS score | HIGH (retry or escalate) |
| **Sub-agent invocation** | Fork decision validation fails, sub-agent reports failure | HIGH (retry with alternative approach) |

### 1.2 Failure Classification

All failures fall into three categories for Sisyphus Persistence:

#### **A. Transient Failures** (Retry with Same Approach)
- Network timeout in agent invocation → Retry immediately (same approach)
- Task dependency temporarily blocked → Retry after dependency resolves
- Verification criteria marginally unmet → Minimal adjustment + retry same approach

**Recovery Strategy**: Immediate retry (≤3 times) with no approach change. If all fail → escalate.

#### **B. Logic/Design Failures** (Retry with Alternative Approach)
- Verification criteria fundamentally unmet (e.g., "Missing section X") → Redesign output structure
- pACS score RED zone (<50) → Revisit logic; generate alternative reasoning
- Sub-agent contradiction (e.g., @reviewer rejects @translator output) → Adjust input/assumptions

**Recovery Strategy**: Analyze root cause → select alternative approach → retry (max 3 approaches).

#### **C. Resource/External Failures** (Escalate)
- API rate limit exhausted → Escalate to Team Lead
- Insufficient context/information to resolve → Escalate to Team Lead
- Unresolvable contradiction (e.g., both @reviewer and @fact-checker reject same output) → Escalate

**Recovery Strategy**: Report inability with specific reason → escalate to Team Lead or user.

### 1.3 Root Cause Analysis

When a failure occurs:

1. **Collect failure context**:
   - Error message (full stack trace if available)
   - Deliverable path (if partially generated)
   - Verification criteria that failed (if L1 failure)
   - pACS score breakdown (if pACS failure)
   - Time since stage start
   - Previous retry attempts (count + approaches tried)

2. **Classify as Transient/Logic/Resource**:
   - Transient: Time-bound (timeout, temporary block)
   - Logic: Content-bound (missing section, contradictory feedback)
   - Resource: System-bound (rate limit, insufficient data)

3. **Record classification in SOT**:
   ```yaml
   steps[step-N]:
     failures:
       - attempt: 1
         timestamp: "2026-04-24T11:00:00Z"
         classification: "logic"  # or "transient" / "resource"
         root_cause: "Missing assumption in section 2.1"
         approach_used: "approach-A"
   ```

---

## Part 2: Sisyphus Persistence — 3 Retry Strategy

### 2.1 Retry Budget & Attempt Sequencing

When **I-1 Sisyphus Persistence** is active (ULW mode):

- **Maximum attempts per stage**: 3
- **Each attempt must use different approach**
- **Tracking location**: SOT `steps[step-N].retry_history[]`

#### Retry Sequencing:

```
┌─────────────────────────────────────────────────────────┐
│ STAGE START: (human) or (team) stage execution          │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │ Attempt 1: Approach A       │
        │ (Primary, most direct)      │
        └──────────┬───────────────────┘
                   │ PASS → ADVANCE
                   │ FAIL → Classify
        ┌──────────┴──────────────────┐
        │ Attempt 2: Approach B       │
        │ (Alternative 1: Modify      │
        │  assumptions/structure)     │
        └──────────┬───────────────────┘
                   │ PASS → ADVANCE
                   │ FAIL → Classify
        ┌──────────┴──────────────────┐
        │ Attempt 3: Approach C       │
        │ (Alternative 2: Radical     │
        │  redesign/pivot)            │
        └──────────┬───────────────────┘
                   │ PASS → ADVANCE
                   │ FAIL → Classify (Resource?)
        ┌──────────┴──────────────────┐
        │ All 3 attempts exhausted    │
        │ ESCALATE to Team Lead       │
        └─────────────────────────────┘
```

### 2.2 Approach Definition by Failure Type

#### **For Transient Failures** (e.g., timeout):
- Approach A: Standard retry (same parameters)
- Approach B: Extended timeout + logging
- Approach C: Alternative invocation method (e.g., direct vs. sub-agent)

#### **For Logic Failures** (e.g., "Missing section"):
- Approach A: Generate output with standard template
- Approach B: Simplify template; focus on core sections only
- Approach C: Completely different structure (e.g., Q&A format instead of narrative)

#### **For pACS Failures** (YELLOW/RED zone):
- Approach A: Add detail to weak dimension (if YELLOW)
- Approach B: Restructure for clarity (if Logic weak)
- Approach C: Request additional input/constraints from Team Lead (if RED + transient)

#### **For Sub-agent Failures** (@translator, @reviewer, @fact-checker):
- Approach A: Re-invoke with same parameters (transient?)
- Approach B: Adjust fork context (glossary, previous output) + retry
- Approach C: Alternative sub-agent (e.g., @reviewer instead of @fact-checker) or human fallback

### 2.3 Attempt Tracking & Decision Logging

For each attempt, record in SOT:

```yaml
steps[step-N]:
  retry_history:
    - attempt: 1
      approach: "approach-A"  # Human-readable label
      timestamp_start: "2026-04-24T11:00:00Z"
      timestamp_end: "2026-04-24T11:05:00Z"
      output_path: "step-N-attempt-1.md"
      verification_status: "FAIL"
      pacs_score: 45
      failure_reason: "Missing assumption in section 2.1"
    - attempt: 2
      approach: "approach-B"  # Modified assumptions
      timestamp_start: "2026-04-24T11:05:00Z"
      timestamp_end: "2026-04-24T11:10:00Z"
      output_path: "step-N-attempt-2.md"
      verification_status: "PASS"
      pacs_score: 78
      completion_timestamp: "2026-04-24T11:10:00Z"
```

Log decision to Decision Log:

```markdown
## Stage Recovery: step-N (Attempt 2/3 — Approach B)

**Previous Attempt**: Attempt 1 failed with "Missing assumption in section 2.1"

**Approach Change**: Modified section 2.1 assumptions based on previous feedback

**Execution Time**: 5 minutes (11:05–11:10)

**Result**: ✅ PASS (pACS 78/100)

**Decision**: Stage completed after 2 attempts. Proceed to next stage.
```

---

## Part 3: Failure Recovery Workflows

### 3.1 (human) Stage Failure Recovery

**Flow**:

```
(human) Stage Start (e.g., Research)
   │
   ├→ Orchestrator invokes Agent(stage_spec)
   │
   ├→ Agent generates deliverable
   │
   ├→ L0 Anti-Skip Guard: Check step matches expected step
   │   └─ FAIL? → Stage failed. Exit workflow (fatal error).
   │
   ├→ L1 Verification Gate: Check deliverable against criteria
   │   └─ FAIL? → Attempt recovery (see 3.1.1)
   │   └─ PASS? → Proceed to L1.5
   │
   ├→ L1.5 pACS Self-Rating: Agent rates own output
   │   └─ RED (<50)? → Enhanced scrutiny (see 3.1.2)
   │   └─ YELLOW (50-69)? → Proceed with caution
   │   └─ GREEN (≥70)? → Proceed normally
   │
   ├→ Translation Fork (if configured): @translator invokes
   │   └─ FAIL? → Attempt recovery (see 3.1.3)
   │   └─ PASS? → Continue
   │
   ├→ Review Fork (if configured): @reviewer/@fact-checker invokes
   │   └─ FAIL? → Attempt recovery (see 3.1.3)
   │   └─ PASS? → Continue
   │
   └→ Advance to next stage
```

#### **3.1.1 L1 Verification Failure Recovery**

**Trigger**: `verification[step-N].status == "FAIL"`

**Recovery Steps**:

1. **Classify failure** (section 1.3)
   - Is this transient (timeout), logic (missing section), or resource (insufficient info)?

2. **If Transient**: Retry same approach (Attempt 2)
   - Orchestrator: Reset any time-dependent state
   - Invoke Agent again with same stage spec
   - Proceed to L1 verification

3. **If Logic**: Modify stage spec + retry with Approach B
   - Analyze verification failure reason
   - Modify stage spec with constraints/guidance (e.g., "Must include section X with explicit assumptions")
   - Invoke Agent again
   - Proceed to L1 verification

4. **If Resource**: Escalate
   - Report: "Cannot resolve verification failure after 2 attempts. Reason: [specific]"
   - Escalate to Team Lead

5. **After 3 Attempts**: All failed?
   - Record: `steps[step-N].completion_status = "BLOCKED"`
   - Escalate to Team Lead with full retry_history

#### **3.1.2 pACS RED Zone (Score <50) Recovery**

**Trigger**: `pacs[step-N].current_step_score < 50` (RED zone)

**Mandatory Action**: Do NOT proceed. Investigate root cause.

1. **Analyze pACS dimensions**:
   - Which dimension is lowest (F, C, L)?
   - Is there a consistent weakness pattern?

2. **Approach B — Enhanced Scrutiny**:
   - Re-run Stage with additional constraints (e.g., "Explicitly state all assumptions")
   - Focus on weak dimension (e.g., if Logic weak: "Validate each inference step")

3. **If Still RED**: Escalate
   - Reason: "pACS RED zone persists after 2 attempts"
   - Request: Team Lead guidance on stage design modification

#### **3.1.3 Sub-agent Failure Recovery** (@translator, @reviewer, @fact-checker)

**Trigger**: Sub-agent task FAIL or returns error

**Recovery Steps**:

1. **Classify failure type**:
   - @translator fails: Missing glossary entry? Bad source content?
   - @reviewer rejects: Logic weak? Assumptions unstated?
   - @fact-checker rejects: Citation missing? Claim unverified?

2. **Approach B — Adjust Fork Context**:
   - If @translator: Add glossary entry + retry
   - If @reviewer: Strengthen logic section + retry
   - If @fact-checker: Add citations + retry

3. **Approach C — Alternative Sub-agent**:
   - @translator → Fallback to human-in-loop OR retry with explicit glossary pre-creation
   - @reviewer → Escalate to Team Lead for manual L2 review
   - @fact-checker → Retry with @reviewer instead (less strict)

4. **If All Approaches Fail**: Escalate
   - Create Decision Log entry: "Sub-agent [name] failure — unresolved after 3 approaches"
   - Escalate to Team Lead

### 3.2 (team) Stage Failure Recovery

**Flow**:

```
(team) Stage Start (e.g., "Team Coordination")
   │
   ├→ Orchestrator: TeamCreate → active_team created
   │
   ├→ Orchestrator: TaskCreate for each stage requirement
   │
   ├→ Teammates: Execute assigned tasks (in parallel)
   │   └─ Failures handled per-task
   │
   ├→ Team Lead: L1 verification per task (TaskUpdate + SendMessage feedback)
   │   └─ Task L1 FAIL? → SendMessage to teammate with retry guidance
   │   └─ Task L1 PASS? → Record in SOT
   │
   ├→ Team Lead: L1.5 pACS self-rating collection
   │   └─ RED zone? → Enhanced scrutiny on that dimension
   │
   ├→ Team Lead: L2 comprehensive verification (stage-level)
   │   └─ L2 FAIL? → Stage failure recovery (see 3.2.1)
   │   └─ L2 PASS? → Proceed
   │
   └→ Orchestrator: TeamDelete → clean up active_team
```

#### **3.2.1 Team Stage L2 Failure Recovery**

**Trigger**: Team Lead `verification[stage-N].status == "FAIL"` after L1 checks

**Recovery Steps**:

1. **Identify failing task(s)**:
   - Team Lead reviews task_verification[] records
   - Which task(s) have issues? (L1 PASS but L2 FAIL)

2. **Approach B — Task Rerun**:
   - SendMessage to specific teammate: "[task-name] needs revision for [specific reason]"
   - Teammate reruns task with guidance
   - Team Lead re-verifies L1

3. **If Task Still Fails**: Escalate or reassign
   - Reassign to different teammate (if available)
   - OR escalate task to Orchestrator (human intervention)

4. **After 3 Attempts (per task)**:
   - If critical task: Escalate entire (team) stage
   - If non-critical: Skip task, mark as "Deferred" (note in SOT)

5. **If L2 Still FAIL**:
   - Record: `steps[step-N].completion_status = "BLOCKED"`
   - Escalate to user with specific failures + team lead recommendation

#### **3.2.2 Handling Task Dependency Failures**

**Trigger**: Task B blocked because Task A (which it depends on) failed

**Recovery**:

1. **Option A** (Short-term): Hold Task B, retry Task A with Approach B
   - If Task A succeeds → Task B proceeds
   - If Task A fails 3×  → Escalate entire (team) stage

2. **Option B** (Redesign): Modify Task B to not depend on Task A
   - Requires Team Lead design modification
   - Escalate to Team Lead

---

## Part 4: SOT State Management During Retries

### 4.1 Snapshot & Rollback Pattern

When retrying a failed stage:

1. **Capture pre-retry snapshot**:
   ```yaml
   steps[step-N]:
     state_snapshots:
       - attempt: 1
         snapshot_file: "step-N-attempt-1-snapshot.yaml"
         timestamp: "2026-04-24T11:00:00Z"
   ```

2. **Execute retry**:
   - Use captured snapshot as baseline
   - Modifications are localized to this attempt

3. **On success**: Commit new state to SOT
   - Update `steps[step-N].outputs[attempt-2]`
   - Update `steps[step-N].verification` with new status
   - Record timestamp in `steps[step-N].completion_timestamp`

4. **On failure**: Retain snapshot, prepare for Attempt 3
   - Do NOT overwrite `steps[step-N].state_snapshots`
   - Next attempt uses same baseline (or Team Lead provides modified baseline)

### 4.2 Decision Log State Reference

All retry decisions are logged in Decision Log with reference to SOT:

```markdown
## Retry Decision: step-research, Attempt 2

**Reference**: [state.yaml](state.yaml) → `steps[step-research].retry_history[1]`

**Classification**: Logic failure (missing assumption in section 2)

**Approach**: Approach B — Modified section 2 structure + assumptions

**Execution Result**: pACS 78/100 (PASS) — Verified 2026-04-24T11:10:00Z

**Decision**: Stage completed. Proceed to next stage.
```

---

## Part 5: Verification Gate Failure Handling

### 5.1 Retry Budget for Verification Gates

Verification gates have **separate** retry budget from Sisyphus Persistence:

| Gate | Base Budget | ULW Budget | Allocation |
|------|------------|-----------|-----------|
| L0 (Anti-Skip) | 0 | 0 | Non-retryable (fatal) |
| L1 (Verification) | 10 | 15 | Per-stage (cumulative across attempts) |
| L1.5 (pACS) | Implicit | Implicit | Sampled at each L1 pass |
| L2 (Calibration) | 10 | 15 | Per-stage (Team Lead decision) |

**Total for stage**: Up to 15 L1 retrys + 15 L2 retrys under ULW (independent budgets).

### 5.2 Escalation Criteria

After exhausting retry budget:

| Gate | Exhaustion Signal | Escalation Action |
|------|---|---|
| L0 | N/A (fatal immediately) | Exit workflow |
| L1 | 15 consecutive fails | Mark stage BLOCKED, escalate to Team Lead |
| L1.5 | Repeated RED scores after 2 Sisyphus attempts | Team Lead guidance required |
| L2 (Team) | 15 fails + teammate reassignments exhausted | Escalate to Orchestrator |

---

## Part 6: Team Stage Failure Coordination

### 6.1 Teammate Failure Reporting

When a teammate fails a task:

**Teammate → Team Lead (via SendMessage)**:
```
Task: [task-name]
Status: FAILED (L1 verification)
Reason: [specific criterion not met]
Evidence: [error message / verification result]
Attempt: [1/3]

Request: Guidance for next attempt
```

**Team Lead → Teammate (via SendMessage)**:
```
Task: [task-name] — Attempt 2

**Feedback**: [Specific guidance on what to change]

**Approach**: [Approach B description]

**Execution**: [Retry deadline, if applicable]

**Success Criteria**: [Modified criteria if Approach B requires changes]
```

### 6.2 Handling Contradictory Feedback

When teammates disagree (e.g., Teammate A says "Include section X", Teammate B says "Section X is redundant"):

1. **Team Lead** identifies contradiction in L1 verification records
2. **Team Lead** synthesizes guidance:
   ```
   Both feedback items are valid in different contexts.
   Approach B: Restructure output to address both concerns.
   [Specific guidance on how to combine]
   ```
3. **Reassign** to teammate with additional context
4. **If still contradictory**: Escalate to Orchestrator (design flaw in stage requirements)

---

## Part 7: Example Walkthroughs

### 7.1 (human) Stage Failure — Logic Failure + Sisyphus Recovery

**Scenario**: Research stage fails L1 verification ("Missing assumptions in section 2")

```
ATTEMPT 1: Research Stage (Approach A)
├─ Agent generates research output (standard template)
├─ L1 Verification: FAIL — "Section 2 lacks explicit assumptions"
├─ Classification: Logic failure
├─ Time taken: 5 minutes
└─ Decision: Retry with Approach B

ATTEMPT 2: Research Stage (Approach B)
├─ Orchestrator modifies stage spec:
│  "Include explicit 'Assumptions' subsection in Section 2"
├─ Agent generates output with modified structure
├─ L1 Verification: PASS (all criteria met)
├─ L1.5 pACS: 78/100 (GREEN zone)
├─ Translation fork: @translator succeeds
├─ Review fork: @reviewer approves (pACS 82/100)
├─ Time taken: 5 minutes
└─ Result: STAGE COMPLETED

SOT recorded:
steps[step-research]:
  retry_history:
    - attempt: 1
      approach: "approach-A"
      status: "FAIL"
      failure_reason: "Missing assumptions in section 2"
    - attempt: 2
      approach: "approach-B"
      status: "PASS"
      pacs_score: 82

Decision Log:
## Research Stage Recovery (Attempt 2 SUCCESS)
Approach B modifications (explicit Assumptions subsection) resolved section 2 weakness.
Stage completed within Sisyphus budget. Proceed to Planning stage.
```

### 7.2 (team) Stage Failure — Task Reassignment Recovery

**Scenario**: (team) stage Planning has 4 tasks; Task 2 (Analysis) fails L1

```
TASK 1: Literature Review
├─ Teammate A executes
├─ L1 Verification: PASS
└─ Status: COMPLETE

TASK 2: Analysis  ←← FAILURE
├─ Teammate B executes
├─ L1 Verification: FAIL — "Analysis lacks quantitative evidence"
├─ Attempt: 1/3
├─ Team Lead sends feedback:
│  "Approach B: Add 2-3 quantitative case studies to Section 3.2"
├─ Teammate B reruns task
├─ L1 Verification: PASS (after revision)
├─ Status: COMPLETE
└─ Time spent: 8 minutes

TASK 3: Synthesis
├─ Teammate C executes
├─ L1 Verification: PASS
└─ Status: COMPLETE

TASK 4: Final Review
├─ Teammate D executes
├─ L1 Verification: PASS
└─ Status: COMPLETE

(team) Stage L2 Verification:
├─ Team Lead reviews all tasks
├─ pACS aggregation: min(F=85, C=80, L=78) = 78/100
├─ L2 Verification: PASS
└─ Result: STAGE COMPLETED

SOT recorded:
steps[step-planning]:
  tasks:
    - task_id: "task-2-analysis"
      status: "PASS"
      attempt_count: 2
      teammate: "Teammate B"
      retry_reason: "Quantitative evidence missing"

Decision Log:
## Planning Stage (team) — Task 2 Recovery
Task 2 (Analysis) required 1 retry for quantitative evidence.
All 4 tasks completed within retry budget. Stage L2 passed.
```

---

## Part 8: Common Failure Scenarios & Solutions

| Scenario | Classification | Recovery Approach | Time |
|----------|---|---|---|
| Sub-agent timeout | Transient | Attempt 2: Extend timeout | 1 min |
| Verification criterion vague | Logic | Attempt 2: Add clarifying constraint | 5 min |
| pACS logic weak (<50) | Logic | Attempt 2: Strengthen inference steps | 10 min |
| Teammate conflict (contradiction) | Logic | Team Lead synthesis + rerun | 5 min |
| API rate limit exhausted | Resource | Escalate to Team Lead (wait time) | N/A |
| Missing background information | Resource | Escalate to user (input needed) | N/A |
| Unresolvable sub-agent failure | Resource | Human fallback OR escalate | N/A |

---

## Part 9: Troubleshooting & Escalation

### 9.1 When to Escalate (Non-Retryable)

**DO NOT RETRY** — Escalate immediately:

1. **L0 Anti-Skip Guard failure**
   - Stage/step mismatch detected
   - Action: Exit workflow, report to user

2. **Resource unavailable** (3 attempts unsuccessful)
   - API rate limit, insufficient data, network down
   - Action: Escalate to Team Lead with context

3. **Unresolvable logic contradiction** (3 approaches failed)
   - Both @reviewer and @fact-checker reject same output
   - Multiple teammates give conflicting requirements
   - Action: Escalate to Team Lead for design review

4. **Sisyphus budget exhausted**
   - 3 attempts with 3 different approaches all failed
   - Root cause still undiagnosed
   - Action: Report inability + request Team Lead intervention

### 9.2 Escalation Message Format

When escalating to Team Lead:

```markdown
## Escalation: [Stage Name] — Unresolvable Failure

**Stage**: step-[N]-[name]
**Attempt Count**: 3/3 (Sisyphus budget exhausted)

**Approaches Tried**:
1. Approach A — [Description] → FAIL ([Reason])
2. Approach B — [Description] → FAIL ([Reason])
3. Approach C — [Description] → FAIL ([Reason])

**Root Cause Analysis**:
- Classification: [Transient / Logic / Resource]
- Diagnosis: [Specific finding]
- Blocker: [What prevents further automatic recovery]

**Request**: [Specific action needed from Team Lead]
- Option 1: [Suggestion A]
- Option 2: [Suggestion B]

**Evidence**: [Link to SOT, Decision Log, output files]
```

---

## Part 10: Recovery Metrics & Monitoring

### 10.1 Tracking Recovery Success

Record recovery metrics in SOT:

```yaml
workflow_metrics:
  failure_recovery:
    total_stages: 5
    stages_with_retries: 2
    total_retry_attempts: 3  # Cumulative across all stages
    successful_recoveries: 2  # Attempts that led to PASS
    escalations: 0
    sisyphus_budget_exhaustion: 0
    recovery_rate: "100%"  # (successful_recoveries / total_retry_attempts)
    average_retry_time: "6 minutes"
```

### 10.2 Failure Pattern Analysis (Post-Workflow)

After workflow completion, Team Lead can analyze:

```yaml
failure_analysis:
  - stage: "step-research"
    failure_type: "logic"
    root_cause: "Missing assumptions"
    approach_success: "approach-B worked"
    lesson: "Stage spec needs explicit 'Assumptions' guidance"
  - stage: "step-planning"
    failure_type: "transient"
    root_cause: "Timeout in sub-agent"
    approach_success: "Simple retry worked"
    lesson: "Sub-agent timeout needs longer deadline"
```

---

## Summary

**Sisyphus Persistence (I-1)** implementation:

1. ✅ Detect failure → Classify (Transient/Logic/Resource)
2. ✅ Select recovery approach (A/B/C based on classification)
3. ✅ Attempt retry (max 3 total attempts)
4. ✅ Track in SOT `retry_history[]` + Decision Log
5. ✅ Escalate on resource failure or budget exhaustion
6. ✅ For (team) stages, coordinate via Team Lead

**Critical NEVER DO**:
- Never skip classification and just retry
- Never exceed 3 attempts per stage without escalation
- Never retry same approach more than once (I-3 violation)
- Never ignore L0 Anti-Skip Guard failures
- Never leave task "partially done" without escalation (I-1 violation)

**Related Documentation**:
- `ulw-mode.md` — Full ULW mode specification
- `quality-gates.md` — Verification gate details
- `workflow-execution-guide.md` — Stage execution pre-requisites
- `team-coordination-guide.md` — (team) stage coordination details
