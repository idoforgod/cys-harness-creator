---
description: "Execute all prompt blocks sequentially from start"
---

Execute prompt runner. Auto-runs all prompt blocks sequentially, starting from 001.

```bash
!python3 "$CLAUDE_PROJECT_DIR/prompt-runner/run.py" \
  --project-dir "$CLAUDE_PROJECT_DIR" \
  --max-turns 0 \
  --timeout 0 \
  --idle-timeout 0 \
  --delay 60
```
