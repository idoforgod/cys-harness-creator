---
description: "Analyze and troubleshoot Hook infrastructure validation results"
---

## Setup Init Validation Analysis

Analyze `.claude/hooks/setup.init.log` file and resolve any issues.

### Analysis Protocol:

**Step 1 — Read Log:**
Read `.claude/hooks/setup.init.log` using Read tool.
If file not found, advise user: "Run `claude --init` to execute Setup Hook first."

**Step 2 — Classify by Severity:**
- **CRITICAL**: Context Preservation System is non-functional. Requires immediate resolution.
- **WARNING**: System operates but performance degraded. Resolution recommended.
- **INFO**: Normal items. Report only.

**Step 3 — Resolve CRITICAL Issues:**
| Issue | Resolution |
|-------|-----------|
| Script syntax error | Read script → locate syntax error → propose fix |
| Script not found | Investigate missing file cause. Check git status |
| context-snapshots/ creation failed | Check permissions (ls -la .claude/) |
| Python version < 3 | Guide Python 3 installation |
| verification-logs/ missing | Suggest directory creation (required for workflow execution) |
| pacs-logs/ missing | Suggest directory creation (required for pACS-enabled workflows) |
| autopilot-logs/ missing | Suggest directory creation (required for Autopilot mode) |

**Step 4 — Resolve WARNING Issues:**
| Issue | Resolution |
|-------|-----------|
| PyYAML not installed | Propose `pip install pyyaml` (after user confirmation) |
| .gitignore missing entry | Suggest adding `.claude/context-snapshots/` to .gitignore |
| sessions/ creation failed | Check parent directory permissions |
| SOT write safety warning | Hook script detects SOT filename + write pattern co-occurrence. Verify file:line → analyze Absolute Criteria 2 (read-only SOT) violation |

**Step 5 — Final Report:**
Format results in structured format:
```
## Setup Init Results

### Validation Summary
- Total: N items
- Passed: N
- Failed: N (CRITICAL: N, WARNING: N)

### Resolved Issues
- [Issue] → [Resolution] → [Result]

### Remaining Issues & Recommendations
- [Issue] → [Recommended Action]

### Context Preservation System Status
- [Healthy / Degraded / Non-functional]
```
