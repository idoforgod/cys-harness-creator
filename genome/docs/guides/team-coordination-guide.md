# Team Coordination Guide (Team Lead Perspective)

## Overview

This guide is written for the **Team Lead** agent role within a `(team)` stage. The Team Lead is responsible for:

1. **Task decomposition** — Breaking down stage work into discrete, assignable tasks
2. **Teammate management** — Assigning tasks, monitoring progress, providing feedback
3. **Quality assurance** — L1.5 (peer self-verification) and L2 (comprehensive verification)
4. **Escalation** — Detecting failures and triggering re-execution or user escalation

**Key distinction:** Team Lead ≠ Orchestrator. The Orchestrator manages SOT and workflow-level state. The Team Lead manages the *current* `(team)` stage and its team members.

---

## 1. Team Lead Initialization

### 1.1 Understand the (team) Stage Specification

From `workflow.md`, read the `(team)` stage definition:

```yaml
Step N:
  Type: (team)
  Name: "Collaborative Analysis"
  Verification:
    - V1a: All components analyzed
    - V1b: Findings coherent across components
    - V1c: Team summary complete
  Roles:
    - @analyst (analyze component A, B, C)
    - @reviewer (review findings for consistency)
  Timeline: Expect 3-4 rounds for full completion
```

### 1.2 Team Lead Responsibilities (from Orchestrator's SOT)

The Orchestrator has already:
- Created `sot['active_team']` with `name`, `status: in_progress`, empty task/completion lists
- Set `current_step` to this stage number

Team Lead reads this and understands: "I'm leading this stage; teammates will be assigned soon."

### 1.3 Prepare the Task List

Before invocation, Team Lead designs the task structure:

```python
tasks = [
    {
        'task_id': 'analyze-component-a',
        'subject': 'Analyze Component A',
        'description': 'Detailed analysis of component A: architecture, failure modes, optimization opportunities. Criteria: [V1a-specific]',
        'owner': None,  # To be assigned
        'status': 'pending'
    },
    {
        'task_id': 'analyze-component-b',
        'subject': 'Analyze Component B',
        'description': '...',
        'owner': None,
        'status': 'pending'
    },
    {
        'task_id': 'analyze-component-c',
        'subject': 'Analyze Component C',
        'description': '...',
        'owner': None,
        'status': 'pending'
    },
    {
        'task_id': 'synthesize-findings',
        'subject': 'Synthesize and Verify Findings',
        'description': 'Cross-reference findings from components A, B, C. Check for contradictions. Derive team summary per V1b/V1c.',
        'owner': None,
        'status': 'pending',
        'blockedBy': ['analyze-component-a', 'analyze-component-b', 'analyze-component-c']
    }
]
```

---

## 2. Task Creation & Assignment (TaskCreate / TaskUpdate)

### 2.1 Create Tasks

```python
for task in tasks:
    TaskCreate(
        subject=task['subject'],
        description=task['description'],
        metadata={'stage': N, 'verification_criteria': [...]}
    )
```

### 2.2 Assign to Teammates

Once tasks are created:

```python
TaskUpdate(
    taskId='analyze-component-a',
    owner='@analyst'
)
```

Or use SendMessage to coordinate:

```python
SendMessage(
    to='@analyst',
    summary='Task assigned: analyze-component-a',
    message=f"""
    Task: Analyze Component A
    
    Deliverable: [Brief description]
    
    Verification criteria (from stage spec):
    - V1a: [specific criterion]
    - Consistency with peer analyses checked in synthesis phase
    
    Timeline: Expect to complete in ~2 turns; synthesize happens after peers report.
    
    Self-verification (L1): Before reporting, verify your deliverable against criteria.
    
    pACS self-score (L1.5): Rate yourself F/C/L before sending final report.
    """
)
```

### 2.3 Track Task Status

Monitor via TaskList:

```python
TaskList()
# Shows: [pending (unassigned), in_progress, completed, blocked]
```

Update SOT when tasks are assigned:

```python
sot['active_team']['tasks_pending'] = ['analyze-component-a', 'analyze-component-b', ...]
```

---

## 3. Teammate Execution & L1 Self-Verification

### 3.1 Teammate Responsibilities

Each teammate assigned a task is responsible for:

1. **Execute task completely** — Absolute Criterion 1 applies; no abbreviations
2. **L1 Self-Verification** — Verify own deliverable against task criteria
3. **L1.5 pACS Self-Scoring** — Rate own work on F/C/L dimensions
4. **Report completion** — Send message to Team Lead with evidence

### 3.2 Receiving Teammate Reports

When a teammate reports completion via SendMessage:

```
From: @analyst
Message: "Task 'analyze-component-a' complete. Deliverable: analysis.md. 
L1 verification: PASS (found 12 insights per spec).
L1.5 pACS: F=85, C=80, L=82 (weak: Clarity in edge case discussion).
Ready for cross-verification (synthesis phase)."
```

Team Lead:
1. **Verify deliverable exists** — Check that analysis.md is on disk
2. **Spot-check L1 claim** — Read a few sections to ensure L1 was genuinely checked
3. **Record pACS self-score** — Note the F/C/L scores and weak dimension

### 3.3 Detect L1 Failures

If a teammate reports L1 FAIL:

```
From: @analyst
Message: "Task failed L1 verification: Found only 8 insights, spec requires 12."
```

Team Lead:
1. **Do NOT proceed** — Synthesis requires peer input
2. **Provide specific feedback:**

```python
SendMessage(
    to='@analyst',
    summary='Task analysis-component-a: L1 FAIL — Missing insights',
    message="""
    L1 Verification FAIL: Insight count insufficient
    
    Status: 8/12 required insights found
    
    Specific gaps (from deliverable review):
    - [Gap A description]
    - [Gap B description]
    
    Action: Revise analysis to include:
    1. [Specific insight category A]
    2. [Specific insight category B]
    
    Then re-verify and re-report.
    """
)
```

Wait for re-report before proceeding to synthesis.

---

## 4. L2 Comprehensive Verification (Team Lead Review)

### 4.1 When All Peers Have L1 PASS

Once all tasks report L1 PASS + pACS self-scores:

```
@analyst: "L1 PASS, pACS: F=85, C=80, L=82"
@reviewer: "L1 PASS, pACS: F=82, C=85, L=80"
@synthesizer: "Synthesis L1 PASS, pACS: F=88, C=83, L=85"
```

### 4.2 Team Lead Performs L2 Verification

L2 is **independent** verification by Team Lead against **stage-level** Verification criteria (not task-level):

```markdown
# L2 Comprehensive Verification — Step N

## Stage Verification Criteria (from workflow.md)

### V1a: All components analyzed
- Task 1 (analyze-A): PASS — 12 insights documented ✓
- Task 2 (analyze-B): PASS — 10 insights documented ✓
- Task 3 (analyze-C): PASS — 11 insights documented ✓
- **Stage-level:** All 3 components analyzed. ✓

### V1b: Findings coherent across components
- Cross-check: Same architectural patterns mentioned in A and B ✓
- Consistency: No contradictions between A and C analyses ✓
- Synthesis task performed: C-task explicitly checked consistency ✓
- **Stage-level:** Findings are mutually coherent. ✓

### V1c: Team summary complete
- Summary deliverable exists: synthesis.md ✓
- Includes: Overview, key findings, open questions, recommendations ✓
- Length/depth: Appropriate for 3-component analysis ✓
- **Stage-level:** Summary meets completeness spec. ✓
```

### 4.3 Aggregate pACS Score

Derive team stage pACS from all teammate scores:

```
Teammate scores:
- @analyst: F=85, C=80, L=82
- @reviewer: F=82, C=85, L=80
- @synthesizer: F=88, C=83, L=85

Team stage pACS calculation:
- F = mean(85, 82, 88) = 85
- C = mean(80, 85, 83) = 83
- L = mean(82, 80, 85) = 82

**Stage pACS = min(85, 83, 82) = 82 (GREEN)**
Weak dimension: Logic
```

### 4.4 If L2 FAIL

If stage-level verification fails:

```markdown
# L2 Verification FAIL — Step N

## Failed Criterion
V1b: Findings coherent across components

## Evidence of Failure
- Contradiction found:
  - Component A analysis: "Scaling bottleneck at Layer 3"
  - Component C analysis: "Layer 3 performs well under load"
  - These are incompatible.

## Root Cause (hypothesis)
- Component A analysis incomplete (didn't test under production load)
- Component C analysis didn't account for A's context

## Action Required
- Assign: @analyst to re-analyze Layer 3 with C's test conditions
- Assign: @synthesizer to re-verify consistency after A's re-work
```

Send feedback:

```python
SendMessage(
    to='@analyst',
    summary='L2 FAIL: Contradiction in Layer 3 analysis',
    message='...[detailed feedback from above]...'
)
```

Wait for re-work before advancing to next stage.

### 4.5 If L2 PASS + pACS RED

L2 PASS but pACS score < 50:

```
Stage pACS = 45 (RED) ✗

Weak dimension: Logic

Root cause: Synthesizer's logic chain has gaps; recommendations not fully justified.
```

Team Lead:
1. **Check retry budget** — Can team retry pACS scoring/rework?
2. **If budget available:**
   - Send feedback specifically on logic weakness
   - Request re-work focusing on logic justification
   - Re-score after revision
3. **If budget exhausted:**
   - Escalate to Orchestrator with evidence
   - Recommend user decision (abandon, loosen criteria, or override)

---

## 5. Managing Task Dependencies & Blocking

### 5.1 Blocking Rules

Some tasks cannot start until prerequisites complete:

```python
tasks = [
    {
        'task_id': 'task-a',
        'status': 'pending'
    },
    {
        'task_id': 'task-b',
        'status': 'pending',
        'blockedBy': ['task-a']  # task-b waits for task-a
    }
]
```

Team Lead responsibility:
- Ensure blocked tasks are not assigned until blockers complete
- When blocker completes, unblock dependent:

```python
TaskUpdate(taskId='task-b', status='blocked' → 'pending')
SendMessage(to='@assigned_to_b', message='task-a completed; task-b unblocked, ready to start')
```

### 5.2 Detecting Circular Dependencies

If tasks form a cycle (A blocks B, B blocks A), **escalate immediately**:

```python
SendMessage(
    to='orchestrator',
    message='CIRCULAR DEPENDENCY: Task A blocks B, Task B blocks A. Stage cannot proceed. User decision required.'
)
```

---

## 6. Communication Patterns (SendMessage)

### 6.1 Task Assignment Message

```python
SendMessage(
    to='@teammate_name',
    summary='Task assigned: [task_id]',
    message='''
    Task: [Subject]
    
    Description:
    [Detailed task specification]
    
    Deliverable:
    [What artifact should be produced]
    
    Verification Criteria (L1 self-check before reporting):
    - Criterion 1: [specific]
    - Criterion 2: [specific]
    
    pACS Self-Scoring (L1.5):
    Before finishing, rate your work:
    - Functionality (F): 1-100
    - Clarity (C): 1-100
    - Logic (L): 1-100
    
    Reporting Format:
    When complete, report: "L1 PASS/FAIL. pACS: F=X, C=Y, L=Z (weak: [dimension])"
    
    Timeline: Estimate [N] turns
    '''
)
```

### 6.2 Feedback Message (L1/L2 Issues)

```python
SendMessage(
    to='@teammate_name',
    summary='[Task ID]: [Issue Type] — [Issue Summary]',
    message='''
    Task: [Task ID]
    Status: [L1/L2] FAIL
    
    Issue:
    [Specific failure description with evidence]
    
    Root Cause (hypothesis):
    [What went wrong]
    
    Action:
    1. [Specific revision step 1]
    2. [Specific revision step 2]
    
    After revision:
    - Re-verify against criteria
    - Re-score pACS
    - Report completion
    '''
)
```

### 6.3 Completion Acknowledgment

```python
SendMessage(
    to='@teammate_name',
    summary='[Task ID] approved — moving to next phase',
    message='''
    Task: [Task ID]
    Status: ✓ APPROVED
    
    Your deliverable and pACS scores recorded.
    
    Next: [What happens next for this teammate]
    - [Option A: Synthesis phase with peer data]
    - [Option B: New independent task]
    - [Option C: Team wrap-up]
    '''
)
```

---

## 7. Cross-Teammate Coordination

### 7.1 Peer Awareness (without direct teammate-to-teammate comms)

Teammates may want to reference each other's work. Team Lead facilitates:

```python
SendMessage(
    to='@synthesizer',
    message='''
    Component A analysis (from @analyst):
    - 12 key insights documented in analysis-a.md
    - Weak dimension per pACS: Clarity (self-rated C=80)
    - Notable finding: "Layer 3 bottleneck"
    
    Component B analysis (from @reviewer):
    - 10 insights, pACS: F=82, C=85, L=80
    - Notable finding: "Cache efficiency improved in Layer 2"
    
    Your synthesis task: Integrate these into coherent team summary.
    Check: Do findings complement or contradict each other?
    '''
)
```

### 7.2 Detecting Peer Conflicts

If peer deliverables contradict:

```
@analyst (A analysis): "Layer 3 is a bottleneck"
@reviewer (B analysis): "Layer 3 performs well"
```

Team Lead:
1. **Don't assume error** — Context matters; might be different test conditions
2. **Request clarification:**

```python
SendMessage(
    to='@analyst',
    message='''
    Potential contradiction found:
    
    Your analysis (A): "Layer 3 bottleneck under load"
    Peer analysis (B): "Layer 3 performs well"
    
    Possible explanations:
    1. Different test conditions (production vs. test)
    2. Different aspects of Layer 3 (frontend vs. backend)
    3. One analysis incomplete
    
    Please clarify: What test conditions / Layer 3 aspects did you analyze?
    '''
)
```

---

## 8. Recording Completion (Update SOT)

### 8.1 When All Tasks L1 PASS

```python
# Update SOT for Orchestrator to read
sot['active_team']['tasks_completed'].append(task_id)
sot['active_team']['tasks_pending'].remove(task_id)
sot['active_team']['completed_summaries'][task_id] = {
    'status': 'PASS',
    'pacs_score': teammate_pacs,
    'pacs_dimensions': [F, C, L],
    'deliverable': path_to_file,
    'weak_dimension': weakest_dim
}
```

### 8.2 Stage Completion (All Tasks L1 PASS + L2 PASS + pACS Scored)

Team Lead signals to Orchestrator:

```python
SendMessage(
    to='orchestrator',
    summary='Stage N team complete — L2 PASS',
    message=f'''
    Team Stage {N} Complete
    
    Team: {team_name}
    
    Task Summary:
    - Task A: PASS, pACS 85
    - Task B: PASS, pACS 82
    - Task C: PASS, pACS 88
    - Synthesis: PASS, pACS 85
    
    Stage-Level Verification:
    - V1a: All components analyzed ✓
    - V1b: Findings coherent ✓
    - V1c: Team summary complete ✓
    
    Stage pACS: {stage_pacs} ({zone})
    Weak dimension: {weak_dim}
    
    Deliverable: {path_to_team_summary}
    
    Action: Orchestrator may now execute Translation/Review forks.
    '''
)
```

Orchestrator then:
- Updates SOT
- Records stage completion
- Triggers Translation/Review if configured
- Advances to next stage

---

## 9. Common Issues & Troubleshooting

### Q: Teammate missing/offline during task execution?
**A:**
1. Check TaskList — is task still `in_progress`?
2. Send SendMessage reminder — may just need a prompt
3. If no response after reasonable time:
   - Reassign task to another teammate
   - Request user decision on continuation

### Q: Peer deliverables contradict — how to handle?
**A:**
1. Do NOT assume one is wrong
2. Request clarification from both teammates
3. If genuine conflict: Synthesizer resolves by selecting most-justified position
4. Document conflict + resolution in synthesis deliverable

### Q: Synthesis task incomplete due to missing peer work?
**A:**
1. Identify missing peer task
2. Send message to responsible teammate requesting urgency
3. If peer task fails: Escalate (stage L2 cannot pass without peer input)

### Q: pACS score is RED but L2 PASS?
**A:**
1. Verify L2 assessment — stage meets Verification criteria ✓
2. pACS RED indicates *how well* it was done, not whether it's done
3. Check retry budget; if available, rework to improve weak dimension
4. If budget exhausted: Escalate with evidence of trade-off

### Q: Task blocked but blocker isn't advancing?
**A:**
1. Check blocker task status — is it genuinely complete?
2. Send message to blocker task owner requesting priority
3. If blocker fails: Escalate (dependent tasks cannot complete)

---

## 10. Escalation Paths

### 10.1 When to Escalate to Orchestrator

| Scenario | Message Content |
|---|---|
| **L2 FAIL** | Evidence, which V1x criterion failed, root cause hypothesis |
| **Circular dependency** | Task IDs forming the cycle |
| **Teammate unavailable** | Task ID, how long missing, action recommended |
| **pACS RED after retries** | Stage pACS score, weak dimension, retry count |
| **Contradiction unresolvable** | Conflicting findings, both analyses, why contradiction matters |

### 10.2 Escalation Message Template

```python
SendMessage(
    to='orchestrator',
    summary='[Stage N] ESCALATION — [Issue Type]',
    message='''
    Stage: Step N ([Team Name])
    Issue: [Brief issue type]
    
    Summary:
    [1-2 sentence issue description]
    
    Evidence:
    [Specific facts, task IDs, scores, deliverable quotes]
    
    Root Cause (hypothesis):
    [What likely caused this]
    
    Attempted Resolution:
    [What Team Lead tried]
    
    Options:
    1. [Option A with pros/cons]
    2. [Option B with pros/cons]
    3. [Option C with pros/cons]
    
    Recommendation:
    [Which option, why]
    
    Required Decision:
    [What Orchestrator/user must decide]
    '''
)
```

---

## 11. Team Lead Responsibilities Summary

| Responsibility | When | Tool |
|---|---|---|
| **Design task decomposition** | Stage start | Internal task design |
| **Create and assign tasks** | Immediately after design | TaskCreate, TaskUpdate |
| **Monitor task progress** | Ongoing | TaskList, SendMessage |
| **Verify L1 (peer)** | After each task reports | Read deliverable, verify criteria |
| **Receive L1.5 pACS** | After peer reports | Record scores |
| **Perform L2 (stage-level)** | After all L1 PASS | Verify stage Verification criteria |
| **Aggregate pACS** | After all L1.5 complete | Calculate min(F,C,L) per team |
| **Provide feedback** | On L1/L2 failure | SendMessage with specific guidance |
| **Update SOT** | On task/stage completion | Record in sot['active_team'] |
| **Escalate failures** | Retry budget exhausted or unresolvable issues | SendMessage to Orchestrator |

---

## 12. Example: Complete (team) Stage Execution

### Stage Spec (from workflow.md)

```
Step 3:
  Type: (team)
  Name: "Data Quality Analysis"
  Verification:
    - V1a: Data sources validated
    - V1b: Quality issues identified
    - V1c: Remediation plan documented
```

### Execution Flow

**T=0: Task Design**

```
Task 1: "Validate Source A" → @analyst
  Deliverable: source-a-validation.md
  Criteria: Check schema, integrity, freshness
  
Task 2: "Validate Source B" → @analyst (secondary)
  Deliverable: source-b-validation.md
  Criteria: Same as Task 1
  
Task 3: "Cross-Source Quality Check" → @reviewer
  Deliverable: quality-assessment.md
  Blockers: [Task 1, Task 2]
  Criteria: Identify conflicts, data consistency
  
Task 4: "Remediation Plan" → @synthesizer
  Deliverable: remediation-plan.md
  Blockers: [Task 3]
  Criteria: Cover all issues found, prioritize, estimate effort
```

**T=1-2: Task Execution**

- @analyst executes Task 1 & 2 in parallel
- @reviewer waits (blocked on Task 1 & 2)
- @synthesizer waits (blocked on Task 3)

**T=2: L1 Reports**

```
@analyst: "Tasks 1&2 L1 PASS. Found 5 issues in A, 3 in B. 
pACS: F=88, C=82, L=85 (weak: Clarity). Ready for cross-check."

@reviewer: "Unblocked! Starting Task 3 now."
```

**T=3-4: Cross-Check & Synthesis**

```
@reviewer: "Task 3 L1 PASS. Conflicting schemas found between A & B (fixable). 
pACS: F=85, C=88, L=83. @synthesizer can now start plan."

@synthesizer: "Starting Task 4 with peer data..."
```

**T=5: Synthesis Complete**

```
@synthesizer: "Task 4 L1 PASS. Remediation plan covers all 8 issues 
(5 from A, 3 from B), estimated effort 3 weeks. 
pACS: F=90, C=87, L=85 (weak: Logic—one step needs more detail, but critical path clear)."
```

**T=5: Team Lead L2 Verification**

```
V1a: Data sources validated
  ✓ Task 1: Source A validated (schema, integrity, freshness)
  ✓ Task 2: Source B validated
  → PASS

V1b: Quality issues identified
  ✓ Task 3: 8 issues identified (5 from A, 3 from B, 1 conflict)
  → PASS

V1c: Remediation plan documented
  ✓ Task 4: Plan covers all issues, effort estimate, priorities
  → PASS

**L2 VERDICT: PASS**

Stage pACS = min(88, 87, 85) = 85 (GREEN)
Weak dimension: Logic (but not critical)
```

**T=5: Completion**

```
Team Lead → Orchestrator:
"Stage 3 team complete. L2 PASS, pACS 85. Deliverable: remediation-plan.md.
Ready for next stage (Translation/Review if configured)."

Orchestrator → Updates SOT, advances workflow.
```

---

## References

- **AGENTS.md** — L1/L1.5/L2 gate definitions
- **quality-gates.md** — Comprehensive quality gate system
- **CLAUDE.md** — Team + Task lifecycle basics
- **workflow-execution-guide.md** — Orchestrator perspective (counterpart to this guide)

---

**Last Updated:** 2026-04-24  
**Status:** Production Ready  
**Quality Score:** Comprehensive Team Lead Reference
