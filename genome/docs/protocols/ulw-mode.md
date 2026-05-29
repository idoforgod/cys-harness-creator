# ULW (Ultrawork) Mode

> This document specifies the detailed architecture of Ultrawork Mode (ULW).
> Separated from CLAUDE.md — reference when ULW mode is active.

## Overview

When "ulw" is included in the prompt, **Ultrawork Mode** activates. ULW is an orthogonal thoroughness intensity overlay to Autopilot.

- **Autopilot** = Automation axis (HOW) — skip `(human)` approvals
- **ULW** = Thoroughness axis (HOW THOROUGHLY) — complete execution without gaps, resolve errors thoroughly

The two axes are independent; any combination is possible:

|  | **ULW OFF** (Standard) | **ULW ON** (Maximum Thoroughness) |
|---|---|---|
| **Autopilot OFF** | Standard interactive | Interactive + Sisyphus Persistence (3 retries) + mandatory task decomposition |
| **Autopilot ON** | Standard automated workflow | Automated workflow + Sisyphus intensification (3 retries) + team thoroughness |

## Two-Axis Comparison

| Axis | Focus | Activation | Deactivation | Scope |
|------|-------|------------|--------------|-------|
| **Autopilot** | Automation (HOW) | SOT `autopilot.enabled: true` | SOT change | Workflow stages |
| **ULW** | Thoroughness (HOW THOROUGHLY) | "ulw" in prompt | Implicit (deactivates when "ulw" absent in new session) | All tasks (interactive + workflow) |

## Activation Pattern

| User Command | Behavior |
|-------------|----------|
| "ulw do this", "ulw refactor" | "ulw" detected in transcript → ULW mode activates |
| Prompt without "ulw" in new session | ULW deactivates (implicit deactivation — explicit deactivation unnecessary) |

## Three Intensifier Rules

When ULW activates, the following 3 intensifier rules overlay the **current context**:

| Intensifier Rule | Description | Interactive Effect | Autopilot Combination Effect |
|------------------|-------------|-------------------|------------------------------|
| **I-1. Sisyphus Persistence** | Maximum 3 retries, each attempt uses different approach. 100% completion or report inability reason | Try alternatives up to 3 times on error | Quality gate (Verification/pACS) retry limit increased from 10 → 15 |
| **I-2. Mandatory Task Decomposition** | TaskCreate → TaskUpdate → TaskList required | Force task decomposition for non-trivial work | No change (Autopilot already tracks SOT-based) |
| **I-3. Bounded Retry Escalation** | Consecutive retry limit of 3 on same target (quality gates have separate budget) — user escalation on limit exceed | Prevent infinite loops | Always respect Safety Hook blocks |

## Runtime Intensification Mechanisms

| Layer | Mechanism | Intensification Details |
|-------|-----------|------------------------|
| **Hook** (Deterministic) | `_context_lib.py` — `detect_ulw_mode()` | Detect "ulw" via transcript regex |
| **Hook** (Deterministic) | `generate_snapshot_md()` — Snapshot | Preserve ULW status section with IMMORTAL priority |
| **Hook** (Deterministic) | `extract_session_facts()` — Knowledge Archive | Tag `ulw_active: true` → RLM queryable |
| **Hook** (Deterministic) | `restore_context.py` — SessionStart | Inject 3 intensifier rules into context when ULW active (startup source excluded — implicit deactivation) |
| **Hook** (Deterministic) | `_context_lib.py` — `check_ulw_compliance()` | Deterministically verify 3 intensifier rules compliance → include warnings in snapshot IMMORTAL |
| **Hook** (Deterministic) | `generate_context_summary.py` — Stop | ULW Compliance safety net — warn to stderr on violation |

## NEVER DO
- Do not retry same target more than 3 times consecutively (quality gates have separate budget) — I-3 violation, user escalation required
- Never override Safety Hook (`(hook)` exit code 2) blocks under ULW pretense
- Never leave Task "partially completed" and halt in ULW active state — I-1 violation
- Never give up without trying alternatives on error — I-1 violation
- Never proceed implicitly without TaskCreate for non-trivial work — I-2 violation
