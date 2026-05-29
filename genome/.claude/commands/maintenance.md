---
description: "Analyze Hook system health checks and perform cleanup operations"
---

## Setup Maintenance Check Results Analysis

Analyze `.claude/hooks/setup.maintenance.log` file and perform necessary cleanup operations.

### Analysis Protocol:

**Step 1 — Read Log:**
Read `.claude/hooks/setup.maintenance.log` using Read tool.
If file not found, advise user: "Run `claude --maintenance` to execute Maintenance Hook first."

**Step 2 — Per-Item Analysis:**

| Item | Action on WARN/FAIL |
|------|-------------------|
| **Session archives** | List archives > 30 days old → AskUserQuestion for deletion confirmation |
| **Knowledge index** | Identify malformed JSON lines → propose removal |
| **Work log** | If > 1MB, propose cleanup of older logs (backup first) |
| **Script syntax** | Read error script → propose fix |
| **Doc-code sync** | Code constants ↔ doc values mismatch — identify files/values from WARN message → correct document or code |
| **verification-logs/** | Clean up verification logs > 30 days old |
| **pacs-logs/** | Clean up pACS logs > 30 days old |
| **autopilot-logs/** | Clean up Decision Log entries > 30 days old |

**Step 3 — Cleanup Operations (User Confirmation Required):**

⚠️ **Never Delete:**
- `knowledge-index.jsonl` — RLM Knowledge Archive (cross-session knowledge)
- `latest.md` — Latest snapshot (session recovery foundation)

Safe to Delete (after user confirmation):
- `sessions/*.md` — Session archives > 30 days old
- `work_log.jsonl` — Abnormally large work logs (backup first)

**Step 4 — Final Report:**
```
## Maintenance Results

### Health Status Summary
- Total: N items
- Healthy: N
- Issues: N

### Cleanup Operations Performed
- [Operation] → [Result]

### System Status
- Context Preservation System: [Healthy / Needs Attention]
- Knowledge Archive: [N entries, NKB]
- Session Archives: [N files, NKB]
```

### Recommended Execution Schedule:
- **Weekly**: During regular use
- **As-needed**: After Hook script changes, or on session restoration issues
