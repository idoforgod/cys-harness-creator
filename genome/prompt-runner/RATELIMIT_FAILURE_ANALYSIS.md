# Rate-Limit Retry Failure Analysis Report

**Date**: 2026-04-24  
**Severity**: 🔴 Critical (causes execution halt)  
**Scope**: Steps 1~110 entire range

---

## 1️⃣ Core Problem: Comment-Code Mismatch

### Problem Code (run.py:1012-1021)

```python
"""
General error: 3 retries (15s, 30s, 60s wait)
Rate limit: retry at 5-minute intervals up to 60 times (= up to 5 hours of wait)
"""

total_duration = 0
rate_limit_retries = 0
MAX_RATE_LIMIT_RETRIES = 30  # 10 min × 30 = up to 5 hours
RATE_LIMIT_WAIT = 600  # 10 minutes
```

### Contradictions

| Item | Comment | Actual Code | Result |
|------|---------|-------------|--------|
| **Wait interval** | 5 minutes | `RATE_LIMIT_WAIT = 600` (10 minutes) | ❌ **2× longer** |
| **Max retries** | 60 times | `MAX_RATE_LIMIT_RETRIES = 30` | ❌ **2× fewer** |
| **Max wait time** | 5 hours | 30 × 10 min = **300 min = 5 hours** | ✅ Matches (coincidentally) |

**Impact**: User expectation (attempt every 5 minutes × 60 times) differs significantly from actual behavior (every 10 minutes × 30 times).

---

## 2️⃣ Rate-Limit Detection Keyword Misjudgment

### Problem Code (run.py:1057)

```python
if any(kw in content for kw in ["rate limit", "hit your limit", "too many", "try again", "rate_limit", "overloaded"]):
    is_rate_limit = True
```

### Misjudgment Cases

| Keyword | Is It Rate-Limit? | Other Situations That Can Arise |
|---------|-------------------|----------------------------------|
| `"rate limit"` | ✅ Clear | - |
| `"hit your limit"` | ✅ Clear | - |
| `"rate_limit"` | ✅ Clear | - |
| `"overloaded"` | ⚠️ Ambiguous | API server overload (not rate-limit) |
| `"too many"` | ❌ **Dangerous** | "too many tokens", "too many open files", "too many requests" (multiple meanings) |
| `"try again"` | ❌ **Very dangerous** | Can be contained in **every retry-recommended error** |

### Actual Harm Scenario

```
Step 10 execution → timeout occurs → log contains "Please try again later"
↓
Keyword "try again" detected → is_rate_limit = True (misjudgment)
↓
Retry after 10-minute wait (unnecessary time waste)
↓
When it repeats, several hours are wasted
```

---

## 3️⃣ Retry Counter State Management Bug

### Problem Structure (run.py:1025-1105)

```python
while True:
    attempt += 1
    
    if attempt > 1 and rate_limit_retries == 0:  # [A]
        if attempt > max_retries:
            break
        # General retry wait
        time.sleep(...)
    
    verdict, sid, dur = run_single_prompt(...)
    
    if verdict == "success":
        return ("success", sid, total_duration)
    
    # [Error analysis block]
    is_rate_limit = False
    # ... rate-limit detection
    
    if is_session_expired and session_id is not None:
        session_id = None
        attempt = 0         # [B] Session resume
        rate_limit_retries = 0
        continue
    
    if is_rate_limit:
        rate_limit_retries += 1
        if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
            break  # [C] Unconditional loop exit
        # 10-minute wait
        time.sleep(...)
        attempt = 0  # [D] Rate-limit retry
        continue
    
    rate_limit_retries = 0  # [E] General error
```

### State Transition Analysis and Issues

#### Scenario A: Consecutive Rate-Limit Occurrences

```
Turn 1: attempt=1, rate_limit_retries=0
  → [A] condition false (attempt <= 1)
  → run → rate-limit detected
  → [D] attempt=0

Turn 2: attempt=1, rate_limit_retries=1
  → [A] condition false (attempt <= 1)
  → run → rate-limit detected
  → [D] attempt=0

...

Turn 30: attempt=1, rate_limit_retries=29
  → Works normally

Turn 31: attempt=1, rate_limit_retries=30
  → [C] post-value check rate_limit_retries (30) > MAX (30)
  ✅ break → returns ("failed", ...)
```

**Problem**: This part is **logically normal**, but **dangerous when combined with the next problem**.

#### Scenario B: Rate-Limit → General Error Transition

```
Turn 1: rate-limit detected → rate_limit_retries=1, attempt=0
Turn 2: rate-limit again → rate_limit_retries=2, attempt=0
Turn 3: this time a general error → [E] rate_limit_retries=0 reset

Turn 4: attempt=1, rate_limit_retries=0
  → [A] condition true (attempt > 1 && rate_limit_retries == 0) is false
     (because attempt = 1)
  → run → general error again
  → [E] rate_limit_retries=0

... (attempt keeps not being initialized back to 1)
```

**Problem**: The general retry wait (block [A]) may not be executed!

#### Scenario C: Session Expiration + Rate-Limit Mixed

```
Step 10:
  Turn 1: rate-limit detected → rate_limit_retries=1, attempt=0
  Turn 2: session expiration detected!
    → [B] session_id=None, attempt=0, rate_limit_retries=0
    → continue (retry with new session)
  Turn 3: rate-limit again?
    → rate_limit_retries=1 (restarted)
    → [A] condition false
    → continue
  
  ... (session expiration counter is not initialized)
  
  Turn 10: session expiration retry → rate-limit retry → cross-contamination
```

**Problem**: As session-expiration recovery and rate-limit retry become entangled, **behavior becomes unpredictable**.

---

## 4️⃣ State Mismatch with the Main Loop

### Problem Code (run.py:1618-1622)

```python
else:  # "failed"
    state_record_fail(state, step)
    log.error(f"[{step:03d}] Final failure. Halting.")
    log.error(f"  Resume command: python3 run.py --resume")
    sys.exit(1)  # ❌ Immediate termination
```

### Issues

1. **Rate-limit is a transient error but is treated as "final failure"**
   - Rate-limit exceeded (30 times) → `run_with_retry()` returns `("failed", ...)`
   - `main()` judges this as `"failed"` → `sys.exit(1)` immediate termination

2. **Ambiguous state-save timing**
   - `state_record_fail(state, step)` is called → recorded in the `failed` array
   - But rate-limit is not a failure but a **time-out**
   - On resume the same step restarts, but there is **no rate-limit state information**

3. **Disconnect from user expectation**
   - Message: "Resume command: python3 run.py --resume"
   - But there is a high chance the rate-limit is still active
   - After resuming, the same rate-limit error can repeat

---

## 5️⃣ Mismatch Between Comment Description and Actual Code Logic

### Problem Code (run.py:1044-1046)

```python
if verdict == "suspicious":
    # Quiet failure: return immediately without retry (the main loop requests user judgment)
    return ("suspicious", sid, total_duration)
```

**Comment issue**: It says "the main loop requests user judgment," but it actually does not.

Main-loop check:

```python
elif verdict == "suspicious":
    # ... auto-skip (no user judgment request)
    state_record_complete(state, step)
```

---

## 🔍 Actual Failure Scenario Reproduction

### Worst Case When the 5 Issues Above Combine

```
During Step 35 execution:
┌─────────────────────────────────────────────────────┐
│ Turns 1-5: Rate-limit (rate_limit_retries=5)       │
│ Turn 6: "try again later" detected → rate-limit    │
│          again!                                     │
│ ...                                                 │
│ Turn 30: rate_limit_retries=30 reached             │
│   → rate_limit_retries > MAX check                 │
│   → run_with_retry() breaks and returns ("failed") │
└─────────────────────────────────────────────────────┘

Main Loop:
┌─────────────────────────────────────────────────────┐
│ verdict == "failed"                                 │
│ → state_record_fail(state, 35)  (state pollution)  │
│ → log: "[035] Final failure. Halting."             │
│ → sys.exit(1)  (forced termination)                │
└─────────────────────────────────────────────────────┘

On --resume:
┌─────────────────────────────────────────────────────┐
│ Reads current_step=36 from state.json              │
│ (Step 35 is already marked failed)                 │
│ Problem: Step 35 should be retried, but there is   │
│         a chance it is skipped and execution       │
│         starts from Step 36!                       │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Summary of Findings

| Issue | Severity | Impact |
|-------|----------|--------|
| **Comment-code mismatch** | 🟡 Medium | User confusion, unpredictability |
| **Rate-limit detection misjudgment** | 🔴 High | Unnecessary time waste (hours) |
| **Counter state management** | 🔴 High | Unintended loop exit |
| **State mismatch with main** | 🔴 High | Execution halt, --resume failure |
| **Session expiration + rate-limit cross** | 🟠 Very high | Unpredictable behavior |

---

## ✅ Recommended Fix (Separate Document)

See the next document: `RATELIMIT_FIX_RECOMMENDATIONS.md`

### Hotfixes That Can Be Applied Immediately

1. **Rate-limit detection keyword precision**
   - Remove `"try again"`, `"too many"`
   - Keep only rate-limit-specific patterns

2. **Raise MAX_RATE_LIMIT_RETRIES**
   - Restore to 60 (keep 5 hours)
   - Align comment and code

3. **State management improvement**
   - Classify rate-limit cutoff as a separate state rather than "failed"
   - Record the rate-limit retry count in state.json

4. **Separate session + rate-limit state**
   - Refactor so the two state machines operate independently
