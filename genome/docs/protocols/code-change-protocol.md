# Code Change Protocol (CCP) — Detailed Specification

> This document specifies the detailed procedure of Absolute Criterion 3 (Code Change Protocol).
> Separated from CLAUDE.md — reference when making code changes.

## Three-Step Protocol

Before writing, modifying, adding, or deleting code, **must** internally perform the following 3 steps.
Skipping this protocol is an Absolute Criterion violation.
Always perform the protocol, but analysis depth is proportional to change scope.

### Step 1 — Intent Clarification
- Define change purpose (bug fix / feature addition / refactoring / performance) and constraints (compatibility, tech stack) in 1-2 sentences
- For minor changes (typos, comments, formatting), can execute immediately after confirming "no ripple effects"

### Step 2 — Ripple Effect Analysis
- Direct dependencies + call relationships (caller/callee)
- Structural relationships (inheritance, composition, references)
- Data model/schema/type cascading changes
- Tests, configuration, documentation, API specs
- If strong coupling or shotgun surgery risk exists, **must** notify in advance and consult with user

### Step 3 — Change Plan
- Staged change order (which files/functions first → dependency propagation → test/doc alignment)
- If opportunities to decrease coupling / increase cohesion appear, propose together (execution after user approval)

## Proportionality Rule

| Change Scope | Application Depth |
|--------------|-------------------|
| Minor (typos, comments) | Step 1 only — verify no ripple effects |
| Standard (function/logic change) | All 3 steps |
| Large-scale (architecture, API) | All 3 steps + prior user approval required |

## Communication Rules
- Avoid unnecessarily lengthy theoretical explanations; focus on concrete code and specific steps
- Attach brief reasons to important design choices
- Even if ambiguous, don't avoid work; state "reasonable assumptions" then propose best design

## Coding Anchor Points (CAP)

All CCP steps are performed while internalizing the following 4 attitudes:

- **CAP-1**: Think Before Coding — no modifications before reading code, surface tradeoffs, ask if unclear
- **CAP-2**: Simplicity First — minimal code, no speculative features / premature abstractions / unnecessary helpers
- **CAP-3**: Goal-Based Execution — define success criteria first, verify after implementation
- **CAP-4**: Surgical Changes — only requested changes, no unrelated "improvements"

> CAP is subordinate to CCP, so when conflict with Absolute Criterion 1 (quality), quality wins. Details: AGENTS.md §2 Absolute Criterion 3.
