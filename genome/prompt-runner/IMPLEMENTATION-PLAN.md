# Phase 2 Implementation Plan

**Status**: P0 Language (blocking condition) — IN PROGRESS  
**Next**: Awaiting translator completion (DECISION-LOG.md, 2 RATELIMIT files)  
**Target**: Deploy Phase 2 after P0 completion

---

## Overview: 3 Fatal Flaws → Architecture Solutions

Based on FINAL_DESIGN_DECISIONS.md analysis, Phase 2 must resolve 3 critical issues before implementation begins.

---

## Flaw #1: FileLock is Symptom Treatment

### Problem
- Current: FileLockMutex with timeout → Designer reads state.json while Main writes
- Root cause: Architecture doesn't structurally enforce Designer as read-only
- Risk: Deadlock timeout can still lose updates if both processes access simultaneously

### Root Solution: Designer Read-Only Architecture

**Pattern Change**:
```
OLD: Main reads state.json → Designer reads state.json (race condition!)
NEW: Main writes prd.md with {current_step, outputs} → Designer reads only prd.md
```

**Code-Level Guarantee**:
- Designer function signature: `def analyze(prd_path: str) -> dict`
- Designer receives path, not state object
- Designer cannot import/access state.json module
- Static type checker enforces read-only pattern

**Effect**: Eliminates FileLock entirely → Deadlock impossible

---

## Flaw #2: Corrupt State Has No Recovery Path

### Problem
- Current: state.json validation + backup copy only
- Missing: Rollback logic when corruption detected
- Risk: Corrupted state.json blocks workflow permanently

### Root Solution: Atomic Write + Multi-Version Backup

**Implementation Strategy**:

```python
class StateManager:
    def save(self, state: dict):
        # 1. Rotate backups: backup.1 → backup.2 → backup.3
        # 2. Write to temp file first (state.json.tmp)
        # 3. Validate before commit (Pydantic StateModel)
        # 4. Atomic rename (tmp → state.json)
    
    def load(self) -> dict:
        try:
            return self._load_file(self.path)
        except (JSONDecodeError, ValidationError):
            # Try backups in order: backup.1, backup.2, backup.3
            for i in [1, 2, 3]:
                backup = self.path.parent / f"state.json.backup.{i}"
                if backup.exists():
                    try:
                        state = self._load_file(backup)
                        shutil.copy(backup, self.path)  # Restore
                        return state
                    except:
                        continue
            # All backups failed
            raise StateCorruptError("Cannot recover state")
```

**Test Cases**:
- T4: test_state_corrupt_recovery — Truncated JSON auto-restores from backup.1
- T12: test_backup_rotation — 4 successive writes → exactly 3 backups retained

**Effect**: Corruption becomes recoverable → Workflow resilience +95%

---

## Flaw #3: audit.jsonl & state.json Are Async

### Problem
- Current: state.json (step, session) + audit.jsonl (event log) — two files
- Issue: Crash can occur between updates
  ```
  T1: state.json updated (fsync success)
  T2: audit.jsonl.append() started
  T3: CRASH (before fsync)
  → Step-audit mismatch
  ```

### Root Solution: Unify into Single SOT (state.json)

**Schema Change**:
```json
{
  "current_step": 35,
  "current_session_id": "sess_...",
  "completed": [1, 2, ..., 34],
  "failed": [],
  "clears": [3, 6, 9, ...],
  "audit_log": [
    {
      "ts": "2026-04-24T14:32:10Z",
      "step": 35,
      "event": "rate_limit_detected",
      "details": {"attempt": 1}
    },
    ...
  ]
}
```

**Rotation Strategy**:
- When audit_log exceeds 10,000 entries:
  - Archive old entries to state.json.audit.archive.{date}.jsonl
  - Keep recent 5,000 in audit_log

**Effect**: No async → SOT unification → Crash safety +100%

---

## P1: Implementation Deliverables

### P1.1: Step Mismatch Recovery (run.py:main)

**Requirement**: Handle case where `current_step ≠ max(completed) + 1`

```python
def main(args):
    state = state_load()
    
    if args.resume:
        expected_step = max(state["completed"]) + 1 if state["completed"] else 1
        actual_step = state["current_step"]
        
        if actual_step != expected_step:
            log.warning(f"[RESUME] Step consistency check failed")
            log.warning(f"  Expected: {expected_step} (based on completed array)")
            log.warning(f"  Actual: {actual_step} (from state.json)")
            log.warning(f"  Auto-correcting to {expected_step}")
            state["current_step"] = expected_step
            _state_save(state)
```

**Test Cases**:
- T6: test_resume_step_mismatch — Underflow/overflow correction

---

### P1.2: Corrupt Recovery Code Skeleton

**Requirement**: Implement StateManager with atomic writes + backups

**File**: `prompt-runner/state_manager.py` (new)

```python
from pathlib import Path
from pydantic import BaseModel, ValidationError
import json, shutil

class StateModel(BaseModel):
    total: int
    current_step: int
    current_session_id: str | None
    status: str
    started_at: str
    completed: list[int]
    clears: list[int]
    failed: list[int]
    sessions: dict
    rate_limit_state: dict | None
    audit_log: list[dict] = []
    last_updated: str

class StateManager:
    def __init__(self, path: Path):
        self.path = path
    
    def save(self, state: dict):
        # Backup rotation + atomic write logic
        pass
    
    def load(self) -> dict:
        # Try main file, then backups in order
        pass
    
    def _rotate_audit_log(self, state: dict):
        # Archive old audit entries when exceeds 10,000
        pass
```

---

### P1.3: audit.jsonl → state.json Merge

**Requirement**: Integrate audit_log into state.json schema

**Changes**:
- Add `audit_log: list[dict]` to StateModel
- Capture events: "run_prompt", "clear", "session_change", "rate_limit"
- Implement rotation at 10,000 entries

**Schema**:
```python
audit_entry = {
    "ts": ISO8601_timestamp,
    "step": int,
    "event": "run_prompt" | "clear" | "session_change" | "rate_limit",
    "details": {...}
}
```

---

### P1.4: Test Suite (13 Concrete Tests)

| # | Test Name | Scenario | Expected | Priority |
|---|-----------|----------|----------|----------|
| T1 | test_rate_limit_keyword_detection | "Rate limit exceeded" in stderr | is_rate_limit=True | P0 |
| T2 | test_rate_limit_false_positive | "Please try again later" in stderr | is_rate_limit=False | P0 |
| T3 | test_state_schema_v1_migration | Old state dict | Migrate to v2 StateModel | P0 |
| T4 | test_state_corrupt_recovery | Truncated JSON in state.json | Load from backup.1 | P1 |
| T5 | test_audit_durability | 1000 sequential appends | All entries in audit_log | P1 |
| T6 | test_resume_step_mismatch | current_step=50, completed=[1..40] | Auto-correct to 41 | P1 |
| T7 | test_filelock_timeout | Lock held 5s, retry 1s | Success after ~5 retries | P2 |
| T8 | test_concurrent_write_race | 2 processes write simultaneously | Winner determined, loser blocked | P2 |
| T9 | test_session_expiry_detection | "Session expired" in error | is_session_expired=True | P2 |
| T10 | test_session_recovery_counter | Session error → recovery | attempt=0 after recovery | P2 |
| T11 | test_rate_limit_and_session_hybrid | Both errors in sequence | Correct state transitions | P2 |
| T12 | test_backup_rotation | 4 successive writes | Exactly 3 backups retained | P3 |
| T13 | test_main_verdict_rate_limit_exceeded | rate_limit_retries > MAX | verdict="rate_limit_exceeded" | P3 |

---

## Phase 2 Prerequisites Checklist

**P0 (Blocking)** — Must complete BEFORE any coding:
- [ ] soul.md ✅ English translation done
- [ ] AGENTS.md ✅ English translation done
- [ ] DECISION-LOG.md ⏳ Translation in progress
- [ ] RATELIMIT_FIX_RECOMMENDATIONS.md ⏳ Translation in progress
- [ ] RATELIMIT_FAILURE_ANALYSIS.md ⏳ Translation in progress
- [ ] Architecture decision: Designer read-only approved
- [ ] Architect review: 3 fatal flaws solutions approved

**P1 (High Priority)** — Can start immediately after P0:
- [ ] Step mismatch recovery code in run.py
- [ ] Corrupt recovery (atomic write + backups) code skeleton
- [ ] audit.jsonl→state.json merge design finalized
- [ ] Test suite (13 tests) concrete scenario definitions

**Non-Blocking** (Can parallelize in Phase 2):
- [ ] Python substitution checklist (P1-P5 changes)
- [ ] Test code writing
- [ ] Code review setup

---

## Quality Gates — 4 Layers

**L0: Anti-Skip Guard** — Prevent bypassing validation  
**L1: Verification Gate** — P1-P5 checklist enforcement  
**L1.5: pACS Self-Rating** — Agent-generated quality score (88+ target)  
**L2: Calibration** — Human code review feedback integration  

---

## Timeline Projection

| Phase | Task | Hours | Deliverable |
|-------|------|-------|-------------|
| P0 Language | Translate 5 documents | 6-8 | English SOT |
| Architecture Validation | Design decisions + code skeleton | 4-6 | Design doc + StateManager |
| Phase 2 Impl. | P1-P5 + 13 tests + integration | 12-16 | Production-ready code |
| Verification | Code review + quality gates | 3-4 | Deployed |
| **Total** | | **25-34** | **v9.0/10 ready** |

---

## Success Criteria

- ✅ Quality score: 6.28/10 → 9.0/10
- ✅ All 13 tests GREEN
- ✅ No concurrent write race conditions
- ✅ Corrupt state auto-recovery confirmed
- ✅ --resume with step mismatch correction verified
- ✅ audit_log durability (10,000+ entries tested)
- ✅ Designer read-only architecture enforced (type checker)

---

**Next**: Wait for P0 Language completion → Begin P1 immediately
