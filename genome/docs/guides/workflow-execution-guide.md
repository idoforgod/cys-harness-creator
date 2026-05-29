# Workflow Execution Guide (Orchestrator Perspective)

## Overview

This guide is written for the **Orchestrator** agent role: the entity responsible for coordinating workflow execution, managing team lifecycle, tracking state, and ensuring quality gates are met. This document covers the complete workflow execution lifecycle from initialization through team shutdown.

**Core Principle:** The Orchestrator's job is to **orchestrate, not execute**. Execution happens in `(human)` stages (direct work) and `(team)` stages (teammate delegation). The Orchestrator's role is **state management, coordination, quality verification, and escalation**.

---

## 1. Pre-Execution Setup

### 1.1 Understand the Workflow Specification

Before launching any workflow, read the complete `workflow.md` specification:

```
<workflow-root>/workflow.md
├── Stage N
│   ├── Type: (human) | (team)
│   ├── Verification: [criterion list]
│   ├── Translation: @translator | null
│   ├── Review: @reviewer | @fact-checker | null
│   └── Execution steps
```

**Critical fields for Orchestrator:**
- **Type:** Determines execution strategy (direct execution vs. team delegation)
- **Verification:** Quality gate criteria. Orchestrator must enforce these.
- **Translation:** Whether to invoke @translator after this stage
- **Review:** Whether to invoke @reviewer/@fact-checker after this stage

### 1.2 Initialize SOT (State of Truth)

Create or verify the SOT file at the project root:

```bash
cat > state.yaml << 'EOF'
current_step: 0
workflow_status: initialized
outputs: {}
auto_approved_steps: []
active_team:
  name: null
  status: null
  tasks_pending: []
  tasks_completed: []
  completed_summaries: {}
completed_teams: []
pacs:
  current_step_score: 0
  dimensions: [0, 0, 0]
  weak_dimension: null
  history: {}
  pre_mortem_flag: ""
EOF
```

**SOT Compliance (Absolute Criterion 2):** 
- Only Orchestrator writes to SOT
- All parallel agents read SOT as read-only
- No concurrent writes; Orchestrator serializes all updates

### 1.3 Create Runtime Directories

```bash
mkdir -p verification-logs pacs-logs review-logs autopilot-logs diagnosis-logs translations
```

These directories store:
- `verification-logs/` — Verification gate results
- `pacs-logs/` — pACS scoring records
- `review-logs/` — Adversarial review reports
- `autopilot-logs/` — Auto-approval decision logs
- `diagnosis-logs/` — Abductive diagnosis records (on quality gate failure)
- `translations/` — Target-language deliverables + glossary

### 1.4 Activate Autopilot (if desired)

```python
sot['autopilot']['enabled'] = True  # Auto-approve (human) stages
```

Updates to SOT are Orchestrator's responsibility. Once set, the flag is read by generated snapshots and restoration hooks.

---

## 2. (human) Stage Execution

### 2.1 Stage Start

Before the stage work begins:

1. **Verify prerequisite:** Previous stage completed AND Verification PASS
2. **Read stage specification:** Understand the exact deliverable requirements
3. **Update SOT:** Increment `current_step`, set `workflow_status: running`

```python
sot['current_step'] = N
sot['workflow_status'] = 'running'
```

### 2.2 Generate Deliverable

The stage itself is direct execution. The agent generates a deliverable (markdown document, code, analysis, etc.) according to the Verification criteria.

**Key insight:** Quality is the only metric. Absolute Criterion 1 applies: no abbreviations, no shortcuts, complete execution.

### 2.3 Save Deliverable to Disk

After the stage completes:

```bash
# Save to versioned output file
output_file="step-${N}-output.md"
echo "... deliverable content ..." > "$output_file"
```

Record the path in SOT:

```python
sot['outputs'][f'step-{N}'] = 'step-N-output.md'
```

### 2.4 Verification Gate (L0 → L1)

**L0: Anti-Skip Guard** — Verify the output file exists and is not empty (deterministic check, cannot be gamed)

```python
if not os.path.exists('step-N-output.md') or os.path.getsize('step-N-output.md') < MIN_OUTPUT_SIZE:
    # FAIL: File missing or empty
    escalate("Step N output missing or empty")
```

**L1: Verification Criteria** — Self-verify against each Verification criterion

For each criterion in `workflow.md`:
- Read criterion definition
- Check deliverable against criterion
- Record PASS/FAIL evidence

```markdown
# Verification Log — Step N

## V1a: [Criterion A]
- Status: PASS
- Evidence: [Specific quote or location in deliverable]

## V1b: [Criterion B]
- Status: PASS
- Evidence: [Specific quote or location in deliverable]
```

Save to:
```bash
verification-logs/step-N-verify.md
```

**If Verification FAIL:**
- Check retry budget: `validate_retry_budget.py --step N --gate verification --check-and-increment`
- If budget available (`can_retry: true`):
  - Run Abductive Diagnosis (see section 5)
  - Rework based on diagnosis
  - Re-verify
- If budget exhausted (`can_retry: false`):
  - Escalate to user with evidence

### 2.5 pACS Self-Rating (L1.5)

**Prerequisites:** L0 PASS AND L1 PASS (Verification)

Answer Pre-mortem Protocol questions:

```markdown
# pACS Self-Rating — Step N

## Pre-mortem Risks
- Functionality: [weakness or risk]
- Clarity: [weakness or risk]
- Logic: [weakness or risk]

## Scoring (1-100 per dimension)
- Functionality (F): [score]
- Clarity (C): [score]
- Logic (L): [score]

## pACS Score
pACS = min(F, C, L) = [score]

## Zone Classification
- < 50: RED ⚠️
- 50-69: YELLOW ⚠️
- 70-100: GREEN ✅
```

Save to:
```bash
pacs-logs/step-N-pacs.md
```

Update SOT:

```python
sot['pacs']['current_step_score'] = pacs_score
sot['pacs']['dimensions'] = [F, C, L]
sot['pacs']['weak_dimension'] = weakest_dim
sot['pacs']['history'][f'step-{N}'] = {
    'score': pacs_score,
    'dimensions': [F, C, L]
}
```

**If pACS RED (< 50):**
- Check retry budget: `validate_retry_budget.py --step N --gate pacs --check-and-increment`
- If budget available:
  - Run Abductive Diagnosis
  - Rework + re-score
- If budget exhausted:
  - Escalate to user

**If pACS YELLOW (50-69):**
- Record weak dimension in decision log
- Proceed (with enhanced review scrutiny)

### 2.6 Translation Fork (if configured)

**Prerequisites:** L1 PASS AND pACS scored

If `Translation: @translator` in workflow:

```python
fork_decision = {
    'agent': '@translator',
    'source_path': f'step-{N}-output.md',
    'target_lang': 'ko',
    'pacs_score': sot['pacs']['current_step_score'],
    'weak_dimension': sot['pacs']['weak_dimension']
}
```

Invoke `@translator` subagent. Translator:
1. Translates the deliverable
2. Updates `translations/glossary.yaml` with new terms
3. Returns translation file (e.g., `step-N-output.ko.md`)

Orchestrator:
- Verify translation file exists on disk
- Record path in SOT: `sot['outputs'][f'step-{N}-ko'] = 'step-N-output.ko.md'`
- Run Translation P1 validation: `validate_translation.py --step N --check-pacs`

### 2.7 Review Fork (if configured)

**Prerequisites:** L1 PASS

If `Review: @reviewer` or `Review: @fact-checker`:

**pACS-based routing:**
- GREEN (≥ 70): Standard @reviewer
- YELLOW (50-69): @reviewer with enhanced scrutiny
- RED (< 50): Escalation or @fact-checker for additional verification

Invoke review subagent. Reviewer:
1. Reads deliverable + pACS info
2. Performs independent assessment
3. Returns review report with Verdict (PASS/FAIL)

Orchestrator:
- Save review report: `review-logs/step-N-review.md`
- Run Review P1 validation: `validate_review.py --step N`

**If Review PASS:**
- Proceed to next stage (including Translation if not already done)

**If Review FAIL:**
- Check retry budget: `validate_retry_budget.py --step N --gate review --check-and-increment`
- If budget available:
  - Run Abductive Diagnosis
  - Rework based on diagnosis
  - Re-review
- If budget exhausted:
  - Escalate to user
  - **DO NOT proceed to next stage**

### 2.8 Advance to Next Stage

After all gates PASS and forks complete:

```python
sot['current_step'] += 1
sot['workflow_status'] = 'running'
# For Autopilot: record auto-approval decision
if autopilot_enabled:
    sot['auto_approved_steps'].append(N)
    decision_log = f"""
    # Autopilot Decision — Step {N}
    
    Stage: (human) {stage_name}
    
    Options: [Full execution based on spec]
    
    Selection: Complete execution per workflow.md
    
    Rationale: Autopilot mode activated; quality maximized per Absolute Criterion 1
    """
    save('autopilot-logs/step-N-decision.md', decision_log)
```

---

## 3. (team) Stage Execution

### 3.1 Team Creation (TeamCreate)

Create a team to coordinate multiple agents:

```python
team_name = f"team-stage-{N}"
team = {
    'name': team_name,
    'status': 'in_progress',
    'tasks_pending': [],  # Will be populated by TaskCreate
    'tasks_completed': [],
    'completed_summaries': {}
}
sot['active_team'] = team
```

### 3.2 Task Creation (TaskCreate)

Decompose stage work into tasks:

```python
tasks = [
    {
        'id': 'task-001',
        'subject': 'Analyze component A',
        'description': 'Detailed requirements...',
        'owner': '@analyst',
        'status': 'pending'
    },
    {
        'id': 'task-002',
        'subject': 'Review findings',
        'description': '...',
        'owner': '@reviewer',
        'status': 'pending',
        'blockedBy': ['task-001']  # Wait for task-001 to complete
    }
]

for task in tasks:
    sot['active_team']['tasks_pending'].append(task['id'])
```

### 3.3 Teammate Execution & L1 Self-Verification

Each teammate works on their assigned task:

1. **Execute task completely** (Absolute Criterion 1 applies)
2. **Self-verify (L1)** — Verify own deliverable against task criteria
3. **Report to Orchestrator** via SendMessage with pACS self-score (L1.5)

### 3.4 Team Lead L2 Comprehensive Verification

When each teammate completes, Team Lead (Orchestrator):

1. **Verify all teammate outputs** against stage Verification criteria
2. **Aggregate pACS scores** from all teammates
3. **Determine stage pACS** = aggregate score
4. **Update SOT**:

```python
sot['active_team']['tasks_completed'].append(task_id)
sot['active_team']['tasks_pending'].remove(task_id)
sot['active_team']['completed_summaries'][task_id] = {
    'status': 'PASS',
    'pacs_score': teammate_score,
    'deliverable': path
}
```

**If L2 FAIL or teammate pACS RED:**
- Send feedback + re-execution instructions via SendMessage
- Re-verify after teammate re-work

### 3.5 Team Shutdown (TeamDelete)

When all tasks complete:

```python
sot['active_team']['status'] = 'all_completed'

# Archive team
completed_record = {
    'name': sot['active_team']['name'],
    'archived_at': datetime.now().isoformat(),
    'summary': sot['active_team']['completed_summaries']
}
sot['completed_teams'].append(completed_record)

# Reset active team
sot['active_team'] = {
    'name': None,
    'status': None,
    'tasks_pending': [],
    'tasks_completed': [],
    'completed_summaries': {}
}
```

---

## 4. Verification Gate Enforcement

### 4.1 Gate Sequencing

Verification gates apply to `(human)` stages only. Sequence:

```
Stage Start
    ↓
L0: Anti-Skip Guard (file exists + non-empty)
    ↓
L1: Verification Criteria (self-verify against spec)
    ↓
L1.5: pACS Self-Rating (Pre-mortem + F/C/L scoring)
    ↓
L2: (if team) Comprehensive Verification (Team Lead reviews all outputs)
    ↓
Translation/Review Forks (if configured)
    ↓
Stage Complete → Advance to Next Step
```

### 4.2 Retry Budget Management

Quality gate failures trigger retries up to budget:

| Gate | Standard Budget | ULW Mode |
|------|-----------------|----------|
| Verification (L0+L1) | 10 | 15 |
| pACS (L1.5) | 10 | 15 |
| Review (L2 for teams) | 5 | 10 |

Check and consume budget:

```bash
python3 validate_retry_budget.py \
  --step N \
  --gate verification|pacs|review \
  --project-dir . \
  --check-and-increment
```

Returns: `{"can_retry": true/false, "remaining": N, ...}`

### 4.3 Abductive Diagnosis on Failure

When quality gate FAIL and retry available:

```bash
# Step A: Pre-evidence collection
python3 diagnose_context.py --step N --gate verification --project-dir .

# Returns: evidence bundle (Fast-Path eligibility, root cause pointers)
```

**If Fast-Path eligible:**
- FP1/FP2: Execute immediate re-fix
- FP3: Escalate to user

**If no Fast-Path:**
- Analyze evidence
- Generate 2-4 hypotheses with rationales
- Select strongest hypothesis
- Re-execute per diagnosis

Record diagnosis:

```markdown
# Diagnosis — Step N Verification FAIL

## Evidence Summary
- [Fast-Path eligibility and pointers]

## Hypotheses
1. H1: [Root cause A]
   - Rationale: [Evidence linking to A]
   - Re-fix: [Specific action]

2. H2: [Root cause B]
   ...

## Selected: H2
Action: [Specific re-execution plan]
```

Save to: `diagnosis-logs/step-N-verification-{timestamp}.md`

---

## 5. State Consistency & Persistence

### 5.1 SOT Write Pattern (Absolute Criterion 2)

**Rule:** Only Orchestrator writes to SOT.

Safe pattern:

```python
# Read current SOT
sot = yaml.safe_load(open('state.yaml'))

# Make updates (atomic per logical transaction)
sot['current_step'] = N
sot['outputs']['step-N'] = output_path
sot['pacs']['history'][f'step-{N}'] = pacs_info

# Atomic write (all-or-nothing)
atomic_write('state.yaml', yaml.dump(sot))
```

**Never:**
- Allow agents to write SOT directly
- Use concurrent writes from multiple agents
- Update SOT in-place without reading first (stale read risk)

### 5.2 Context Snapshots & Restoration

Session end triggers automatic snapshot save:

```bash
python3 generate_context_summary.py --project-dir . --trigger stop
```

Snapshot includes:
- Decision log (major design decisions, ordered by quality tag)
- Quality gate status (current L0-L2, pACS history)
- Completion state (current_step, workflow_status)
- Error patterns (recent failures + resolutions)
- IMMORTAL section (ULW status, team status, etc.)

On session resumption, Orchestrator restores via:

```bash
# Read recovery guidance
cat .claude/context-snapshots/latest.md

# Restore RLM pointers
# [Knowledge Archive index points to previous sessions]
```

---

## 6. Cross-Workflow Transitions

### 6.1 DNA Inheritance (Child Workflow Spawn)

When a child workflow is created (e.g., via workflow-generator skill):

```python
# Child inherits parent's genome (9 core components)
child_workflow = {
    'constitution': parent['constitution'],  # Absolute Criteria
    'structure': parent['structure'],  # CLAUDE.md conventions
    'verification': parent['verification'],  # Quality gate system
    'safety': parent['safety'],  # Hook security system
    'memory': parent['memory'],  # Context Preservation System
    'criticism': parent['criticism'],  # Adversarial review
    'transparency': parent['transparency'],  # Decision logs
    'orchestration': parent['orchestration'],  # Team + Task lifecycle
    'recovery': parent['recovery'],  # Failure-recovery + diagnosis
}
```

Orchestrator for child workflow:
- Reads parent's `soul.md` to understand heritage
- Inherits all protocols (Autopilot, ULW, quality gates)
- Executes with same standards

---

## 7. Orchestrator Responsibilities Summary

| Responsibility | Tool/Function | Trigger |
|---|---|---|
| **Initialize** | `sot_paths()`, mkdir | Workflow start |
| **Coordinate execution** | `workflow.md` parsing | Stage start |
| **Verify output quality** | L0/L1/L1.5 gates | Stage completion |
| **Manage team** | TeamCreate/Delete | `(team)` stage start/end |
| **Assign tasks** | TaskCreate/Update | Team creation |
| **Route to sub-agents** | Fork decisions | Verification/pACS PASS |
| **Handle failures** | Abductive Diagnosis | Quality gate FAIL |
| **Manage retries** | Retry budget tracking | Any failure |
| **Record decisions** | Decision log + snapshots | Session stop |
| **Advance workflow** | SOT.current_step ++ | All gates PASS |

---

## 8. Error Handling & Escalation

### 8.1 Escalation Conditions

Escalate to user when:

1. **Retry budget exhausted** (10 verification retries, 15 in ULW)
   ```
   → User decision required: Continue anyway? Abandon?
   ```

2. **Same hypothesis selected 3x consecutively** (I-3 violation in ULW)
   ```
   → Infinite loop detected: different approach needed
   ```

3. **Fast-Path FP3 triggered** (Fast-Path analysis inconclusive)
   ```
   → Evidence insufficient: requires human judgment
   ```

4. **Review FAIL after max retries**
   ```
   → Quality gate cannot be satisfied: review block prevents proceeding
   ```

### 8.2 Escalation Message Format

```markdown
# Escalation — Step N [Verification|pACS|Review] FAIL

## Summary
- Gate: [which gate failed]
- Retries exhausted: [current/max]
- Current pACS: [score or N/A]

## Evidence
[Verification failures, pACS weak dimensions, review verdict]

## Last Diagnosis
- Selected hypothesis: [H1/H2/H3/H4]
- Attempted action: [what was tried]
- Result: [why it didn't work]

## Options
1. **Modify stage spec** — Change Verification criteria (looser/clearer)
2. **Continue anyway** — Skip quality gate (not recommended)
3. **Abandon workflow** — Start over with different approach

## User Action Required
[Specific instruction]
```

---

## 9. Advanced: Autopilot Mode Mechanics

### 9.1 Autopilot Intensification

When `sot['autopilot']['enabled'] = True`:

| Hook Event | Behavior |
|---|---|
| **SessionStart** | Inject 6 execution rules into context; display previous deliverable results |
| **Stop** (snapshot) | Generate auto-approval Decision Log automatically |
| **Stage completion** | Auto-record decision without human gate |

### 9.2 Autopilot Decision Log

Generated automatically for each `(human)` stage:

```markdown
# Autopilot Decision — Step N

## Stage
Name: [stage name]  
Type: (human)  
Spec: [link to workflow.md section]

## Options
[Deliverable requirements as presented by stage Verification]

## Selection
**Complete execution per workflow.md**

## Rationale
Autopilot mode active.  
Quality maximized per Absolute Criterion 1.  
No abbreviations — full execution enforced.

## pACS Calibration
[Previous stage weak dimension → focus area for this stage]
```

Save to: `autopilot-logs/step-N-decision.md`

---

## 10. Troubleshooting

### Q: Stage stuck in Verification FAIL after N retries?
**A:** 
1. Run: `validate_retry_budget.py --step N --check` → Check remaining budget
2. If budget exhausted: Escalate (Section 8)
3. If budget available: Ensure Abductive Diagnosis is running (Section 4.3)

### Q: Team member is not progressing?
**A:**
1. Check: `sot['active_team']['tasks_pending']` — Is task assigned?
2. Verify: TeamCreate was executed and recorded in SOT
3. Send message: `SendMessage(to=teammate, message="...feedback...")`

### Q: pACS score seems inconsistent?
**A:**
1. Check: Pre-mortem Protocol answered for all dimensions
2. Verify: pACS = min(F, C, L), not average
3. Confirm: Weak dimension correctly identified

### Q: Review FAIL — How to proceed?
**A:**
1. Check: Is retry budget available? `validate_retry_budget.py --step N --gate review`
2. Run Abductive Diagnosis (Section 4.3)
3. If FP3 escalation: Contact user for decision

---

## References

- **AGENTS.md** — Complete agent directives and quality gate specifications
- **quality-gates.md** — Detailed L0-L2 4-layer architecture
- **autopilot-execution.md** — Full Autopilot mode execution checklist
- **ulw-mode.md** — ULW mode intensifier rules (I-1, I-2, I-3)
- **code-change-protocol.md** — CCP 3-step protocol for code modifications

---

**Last Updated:** 2026-04-24  
**Status:** Production Ready  
**Quality Score:** Comprehensive Orchestrator Reference
