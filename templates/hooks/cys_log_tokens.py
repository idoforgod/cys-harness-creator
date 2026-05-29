#!/usr/bin/env python3
"""SubagentStop hook (M0, best-effort): append per-session token/exit to runs/log.jsonl.

LIMIT (verified): Claude Code does NOT reliably expose per-call token usage in hook
stdin. This is COARSE, POST-HOC reporting only — NOT a live budget abort (the hard
ceiling is workflow.js budget.total). Records whatever the payload carries; usage may
be absent. Never blocks (always exits 0).
"""
import json
import os
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # never block the agent
    rec = {
        "session_id": payload.get("session_id"),
        "agent": payload.get("agent_type") or payload.get("subagent_type"),
        "stop_reason": payload.get("stop_reason") or payload.get("reason"),
        "usage": payload.get("usage"),  # often absent; recorded if present
    }
    root = os.environ.get("HARNESS_ROOT") or os.getcwd()
    logp = os.path.join(root, ".harness", "runs", "log.jsonl")
    try:
        os.makedirs(os.path.dirname(logp), exist_ok=True)
        with open(logp, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
