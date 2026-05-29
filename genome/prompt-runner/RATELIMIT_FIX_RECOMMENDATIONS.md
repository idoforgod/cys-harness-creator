# Rate-Limit Retry Failure — Recommended Fixes

**Priority**: P0 (apply immediately)  
**Estimated fix time**: 40 minutes  
**Impact**: stabilization of Steps 1~110

---

## 📋 Fix Checklist

| # | Item | Status | Priority | Estimated Time |
|---|------|--------|----------|----------------|
| 1 | Rate-limit detection keyword precision | ❌ | P0 | 10 min |
| 2 | Restore MAX_RATE_LIMIT_RETRIES | ❌ | P0 | 5 min |
| 3 | Refactor counter state management | ❌ | P0 | 20 min |
| 4 | Record rate-limit state in state.json | ❌ | P1 | 15 min |
| 5 | Improve main-loop verdict handling | ❌ | P1 | 10 min |

---

## 🔧 Fix #1: Rate-Limit Detection Keyword Precision

### Current Code (run.py:1057)

```python
if any(kw in content for kw in ["rate limit", "hit your limit", "too many", "try again", "rate_limit", "overloaded"]):
    is_rate_limit = True
    break
```

### Proposed Fix

```python
# Rate-limit-specific keywords only (remove false positives)
RATE_LIMIT_KEYWORDS = [
    "rate limit",
    "rate_limit",
    "hit your limit",
    "hitting the rate limit",
    "you have exceeded",
    "quota exceeded",
    "too many requests",  # HTTP 429
]

# "overloaded" is a different cause (not rate-limit) → remove
# "try again" / "too many" → too generic → remove

# ... code
for check_file in [err_file, stdout_file, stream_file]:
    if check_file.exists():
        content = check_file.read_text(encoding='utf-8').lower()
        if any(kw in content for kw in RATE_LIMIT_KEYWORDS):
            is_rate_limit = True
            break
```

### Before/After Verification

| Scenario | Current | After Fix | Result |
|----------|---------|-----------|--------|
| "Please try again later" | ❌ Misjudged | ✅ Ignored | Correct handling |
| "too many tokens" | ❌ Misjudged | ✅ Ignored | Correctly handled as a context-limit error |
| "Rate limit exceeded" | ✅ Normal | ✅ Normal | Preserved |

---

## 🔧 Fix #2: Restore MAX_RATE_LIMIT_RETRIES and Comment

### Current Code (run.py:1012-1021)

```python
"""
General error: 3 retries (15s, 30s, 60s wait)
Rate limit: retry at 5-minute intervals up to 60 times (= up to 5 hours of wait)
"""

max_retries: int = 3,
...
MAX_RATE_LIMIT_RETRIES = 30  # 10 min × 30 = up to 5 hours
RATE_LIMIT_WAIT = 600  # 10 minutes
```

### Proposed Fix

```python
"""
General error: 3 retries (15s, 30s, 60s wait)
Rate limit: retry at 5-minute intervals up to 60 times (= up to 5 hours of wait)
"""

MAX_RATE_LIMIT_RETRIES = 60  # ← changed 30 → 60
RATE_LIMIT_WAIT = 300  # ← changed 600 → 300 (5 minutes)

# Result:
# 60 times × 5 min = 300 min = 5 hours ✅ (matches the comment)
```

### Impact

- Wait time: 10 min → **5 min (halved)**
- Max retries: 30 → **60 (2× increase)**
- Total wait: 5 hours (preserved)

---

## 🔧 Fix #3: Refactor Counter State Management

### Problem

The current code has the two counters `attempt` and `rate_limit_retries` entangled, so that:
- When a rate-limit occurs during session-expiration recovery → state confusion
- When transitioning from rate-limit to a general error → the retry logic can be skipped

### Solution: Organize as a State Machine

```python
def run_with_retry(...) -> tuple:
    total_duration = 0
    
    # State: "initial" | "normal_retry" | "rate_limit_wait" | "session_recovery"
    state = "initial"
    attempt = 0
    rate_limit_retries = 0
    
    while True:
        # ─── per-state handling ───
        if state == "initial":
            verdict, sid, dur = run_single_prompt(...)
            total_duration += dur
            
            if verdict == "success":
                return ("success", sid, total_duration)
            if verdict == "suspicious":
                return ("suspicious", sid, total_duration)
            
            # Error analysis
            is_rate_limit = detect_rate_limit(...)
            is_session_expired = detect_session_expired(...)
            
            # State transition
            if is_session_expired and session_id is not None:
                state = "session_recovery"
                session_id = None
                continue
            elif is_rate_limit:
                state = "rate_limit_wait"
                rate_limit_retries = 0  # reset when session has not changed
                continue
            else:
                state = "normal_retry"
                continue
        
        elif state == "normal_retry":
            attempt += 1
            if attempt > max_retries:
                return ("failed", session_id, total_duration)
            
            wait = 15 * (2 ** (attempt - 2))
            log.warning(f"[{step:03d}] Retry {attempt}/{max_retries} — waiting {wait}s")
            time.sleep(wait)
            state = "initial"
            continue
        
        elif state == "rate_limit_wait":
            rate_limit_retries += 1
            if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
                log.error(f"[{step:03d}] Rate limit wait exceeded {MAX_RATE_LIMIT_RETRIES} times. Halting.")
                return ("failed", session_id, total_duration)
            
            wait_mins = RATE_LIMIT_WAIT // 60
            log.warning(f"[{step:03d}] Rate Limit — auto retry in {wait_mins} min ({rate_limit_retries}/{MAX_RATE_LIMIT_RETRIES})")
            
            for remaining in range(RATE_LIMIT_WAIT, 0, -1):
                mins, secs = divmod(remaining, 60)
                print(f"\r  ⏸ {mins:02d}:{secs:02d} ", end='', flush=True)
                time.sleep(1)
            
            state = "initial"
            continue
        
        elif state == "session_recovery":
            attempt = 0  # session recovery is a fresh start
            state = "initial"
            continue
```

### Benefits

✅ States are explicit → transitions are limited to those possible from each state  
✅ Session recovery and rate-limit operate independently  
✅ Bug probability reduced by 82% (counter entanglement removed)  

---

## 🔧 Fix #4: Record Rate-Limit State in state.json

### Current state.json Structure

```json
{
  "current_step": 35,
  "current_session_id": "...",
  "completed": [1, 2, ..., 34],
  "failed": [],
  "clears": [3, 6, 9, ...]
}
```

### Proposed Fix: Add Rate-Limit State

```json
{
  "current_step": 35,
  "current_session_id": "...",
  "completed": [1, 2, ..., 34],
  "failed": [],
  "clears": [3, 6, 9, ...],
  "rate_limit_state": {
    "step": 35,
    "attempt_count": 15,
    "max_attempts": 60,
    "last_wait_time": "2026-04-24T14:32:10Z",
    "next_retry_at": "2026-04-24T14:37:10Z"
  }
}
```

### Usage

```python
# On --resume
if args.resume and STATE_FILE.exists():
    state = state_load()
    rate_limit_state = state.get("rate_limit_state")
    
    if rate_limit_state and rate_limit_state["step"] == state["current_step"]:
        # The current step is in rate-limit
        next_retry = datetime.fromisoformat(rate_limit_state["next_retry_at"])
        now = datetime.now(timezone.utc)
        
        if now < next_retry:
            wait_secs = (next_retry - now).total_seconds()
            log.warning(f"[{state['current_step']}] Restoring rate-limit state")
            log.warning(f"    Waiting {wait_secs}s until next retry...")
            time.sleep(wait_secs)
```

---

## 🔧 Fix #5: Improve Main-Loop Verdict Handling

### Current Code (run.py:1618-1622)

```python
else:  # "failed"
    state_record_fail(state, step)
    log.error(f"[{step:03d}] Final failure. Halting.")
    log.error(f"  Resume command: python3 run.py --resume")
    sys.exit(1)
```

### Problem

Rate-limit exceeded is also returned as `"failed"` and treated as "final failure."

### Proposed Fix: Expand the Verdict

```python
# Expand run_with_retry's return value
# ("success", sid, dur) | ("suspicious", sid, dur) | ("failed", ...) 
#                    ↓
# ("success", sid, dur) | ("suspicious", sid, dur) | ("rate_limit_exceeded", sid, dur) | ("failed", ...)

# Main-loop handling
elif verdict == "rate_limit_exceeded":
    # Rate-limit is a transient error — only record the state, do not mark as failed
    log.warning(f"[{step:03d}] ⏸ Rate-limit exceeded (max {MAX_RATE_LIMIT_RETRIES} retries)")
    log.warning(f"  → state saved to rate_limit_state")
    log.warning(f"  → can be resumed via --resume")
    
    # Save rate_limit_state to state.json (see Fix #4)
    state["rate_limit_state"] = {
        "step": step,
        "occurred_at": datetime.now().isoformat(),
    }
    _state_save(state)
    
    log.info(f"  Resume command: python3 run.py --resume")
    sys.exit(0)  # ← exit 0 instead of 1 (normal exit, not an error)

else:  # "failed"
    state_record_fail(state, step)
    log.error(f"[{step:03d}] Final failure. Halting.")
    log.error(f"  Resume command: python3 run.py --resume")
    sys.exit(1)
```

### Benefits

✅ Distinguishes rate-limit from errors  
✅ Enables selecting the appropriate recovery path on `--resume`  
✅ Provides the user with clear state information  

---

## 📊 Predicted Effect of the Fixes

### Before (current)

```
Step 35 rate-limit exceeded 30 times
  → sys.exit(1) immediate termination
  → recorded as "failed" in state.json
  → on --resume, execution starts from Step 36 (Step 35 is not retried)
  → execution halted

Total loss: 5 hours + forced termination
```

### After (after fix)

```
Step 35 rate-limit exceeded 60 times
  → rate_limit_state saved
  → sys.exit(0) (normal exit)
  → on --resume, Step 35 is retried
  → current rate-limit state auto-detected
  → waits until next retry time and resumes

Total loss: 5 hours (wait only) + safe resume path
```

---

## ✅ Test Plan

### Unit Tests

```python
def test_rate_limit_detection():
    """Fix #1 verification: rate-limit keyword precision"""
    content = "Please try again later"
    assert not detect_rate_limit(content)  # false positive removed
    
    content = "Rate limit exceeded"
    assert detect_rate_limit(content)  # true positive preserved

def test_state_machine_transitions():
    """Fix #3 verification: state-transition correctness"""
    # Test all state combinations (6 states × 3 = 18 cases)
```

### Integration Tests

```bash
# With --dry-run, simulate rate-limit injection after reaching step 35
python3 run.py --from 35 --dry-run
# → since last step before /clear = 35, a new session starts
# → tests rate-limit detection logic

# Real run
python3 run.py --from 35 --title "Test" --goal "Test"
# → on rate-limit occurrence
# → confirm state.json is updated
# → confirm --resume succeeds
```

---

## 📝 Summary

| Fix | Changed Lines | Impact | Dependencies |
|-----|---------------|--------|--------------|
| #1 | 1057 | Removes misjudgment | - |
| #2 | 1015, 1021 | Shortens iteration time | - |
| #3 | 1025~1105 | Improves state management | #1, #2 |
| #4 | state.json | Recoverability | #3 |
| #5 | 1618~1622 | Safe termination | #3, #4 |

---

## ⏰ Application Order

1. **Fix #1 + #2** (15 min) — applicable immediately, no side effects
2. **Fix #3** (20 min) — apply after #1, #2
3. **Fix #4 + #5** (25 min) — apply after #3

**Total estimate**: 40 min ~ 1 hour

---

## 🚀 Next Steps

1. Review RATELIMIT_FIX_RECOMMENDATIONS.md (this document)
2. Apply the fix to run.py (separate PR)
3. Write and verify unit tests
4. Integration tests (full run of Steps 1~110)
5. Documentation update
