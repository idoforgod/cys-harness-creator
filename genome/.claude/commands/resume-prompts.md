---
description: "Resume interrupted prompt runner from last saved state"
---

Resume execution of stopped prompt runner. Continues from last position saved in state.json.

```bash
!python3 "$CLAUDE_PROJECT_DIR/prompt-runner/run.py" \
  --resume \
  --project-dir "$CLAUDE_PROJECT_DIR" \
  --max-turns 0 \
  --timeout 0 \
  --idle-timeout 0 \
  --delay 60
```
