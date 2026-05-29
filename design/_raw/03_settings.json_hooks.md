# settings.json hooks (write-lock, active-team, token-log)

## PURPOSE
Enforce write-path ownership via harness.lock, prevent concurrent team creation, and audit per-session token consumption for the deep-research M0 harness.

## CONTRACT
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "id": "write-lock-enforcement",
        "matcher": "Write|Edit",
        "if": "Edit(_workspace/**)|Write(_workspace/**)",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/harness-hooks/enforce-write-lock.sh",
            "timeout": 2
          }
        ]
      },
      {
        "id": "team-create-guard",
        "matcher": "TeamCreate",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/harness-hooks/prevent-concurrent-team.sh",
            "timeout": 2
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "id": "token-usage-log",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/harness-hooks/append-run-log.sh",
            "timeout": 5,
            "async": false
          }
        ]
      }
    ]
  }
}
```

**Hook Scripts (executable):**

1. **~/.claude/harness-hooks/enforce-write-lock.sh** (write-lock; called on PreToolUse Write|Edit):
   - Reads stdin JSON hook payload
   - Extracts: file_path, session_id, agent_id (if present), agent_type
   - Reads .harness/harness.lock (YAML: node_id → owner_session_id)
   - Resolves which node owns the target file's _workspace/ subtree
   - Compares owner to current session_id
   - Exit 0 (allow), exit 2 (deny with reason to stdout), exit 1 (error)

2. **~/.claude/harness-hooks/prevent-concurrent-team.sh** (team-guard; called on PreToolUse TeamCreate):
   - Reads stdin JSON hook payload
   - Checks ~/.claude/teams/ for any non-empty subdirectory or active team config
   - If active team found: exit 2 with error message "Team already active: $team_name"
   - Otherwise: exit 0

3. **~/.claude/harness-hooks/append-run-log.sh** (audit; called on SubagentStop):
   - Reads stdin JSON hook payload
   - Extracts: session_id, agent_id, agent_type, transcript_path
   - Reads transcript.jsonl (JSONL format; each line is a message dict)
   - Counts turns (user prompts + assistant responses in transcript)
   - Parses assistant messages for token estimates (if embedded; else use line count heuristic)
   - Computes hash of transcript for dedup
   - Appends JSON line to .harness/runs/log.jsonl: 
     { "session_id", "agent_id", "agent_type", "stop_time_iso", "turns", "tokens_est", "transcript_hash", "exit_status" }
   - Exit 0 always (observational; no blocking)
```

## DEEP-RESEARCH INSTANCE
For the deep-research harness (graph.json execution_mode=workflow, 4-node pipeline: gather → verify → synthesize → report):
- **gather node (Haiku researcher)** writes to _workspace/01_gather/findings.json via Write tool. Hook intercepts, checks harness.lock: owner=gather, session_id=abc123. Allow. 
- **verify node (Sonnet validator)** tries Write to _workspace/01_gather/findings.json (clobber attempt). Hook denies: "owner mismatch; gather owns 01_gather/, verify can only write to 02_verify/".
- **Leader session** calls TeamCreate (experimental). Hook checks ~/.claude/teams/: empty. Allow.
- **gather subagent stops** after 47 turns, ~12K tokens. Hook reads transcript.jsonl, appends { "session_id":"abc123-gather", "agent_type":"researcher", "turns":47, "tokens_est":12000, "transcript_hash":"a1b2c3..." } to .harness/runs/log.jsonl. Later run can compare hash to skip duplicate audit.

## READS
['graph.json', '.harness/harness.lock', '~/.claude/teams/*/config.json', 'transcript.jsonl (via hook stdin path)', '.harness/runs/log.jsonl (for dedup check)']

## WRITES
['.harness/runs/log.jsonl (append-only JSONL)', 'harness.lock entries (updated by prior nodes in pipeline)']

## EDGE CASES
- 1. Write-lock race: two nodes claim same _workspace/ subtree simultaneously → hook's file read may see stale lock. Mitigation: harness.lock is written by workflow.js BEFORE agent() call, so PreToolUse is guaranteed single-writer per node. 2. agent_id absent in main session PreToolUse → use session_id as fallback for ownership check. 3. SubagentStop fires AFTER transcript is finalized; transcript may be incomplete or not yet flushed to disk. Best-effort: sleep 100ms before read, or skip if file does not exist. 4. TeamCreate on experimental teams (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1) only; hook detects env var absence and no-ops gracefully. 5. transcript.jsonl line count is not equal to token count; heuristic (avg 250 tokens/turn) is approximate only. Exact count requires parsing assistant response objects for 'usage' field (not always present). 6. Concurrent SubagentStop calls from multiple subagents → append-only log mitigates via file locking (flock). 7. User bypass: WriteBypassPermissions flag or --dangerously-skip-permissions skips PreToolUse hooks. Lock is advisory, not OS-level; harness is trust boundary, not security boundary.

## FEASIBILITY
**Constraint verification (Claude Code 2.1.x):**

1. **PreToolUse Write|Edit matcher:** Claude Code hook matcher supports tool name + glob on file_path via `if` field (e.g., `if: "Edit(_workspace/**)`). The `tool_input.file_path` is available in hook stdin JSON. ✓ Feasible.

2. **agent_id field in PreToolUse:** Per docs, agent_id is present "only when inside a subagent call." In workflow.js, agent() spawns subagents, so gather/verify/synthesize/report nodes are each their own subagent with distinct agent_id. The leader session (emit caller) has no agent_id in its PreToolUse events. Workaround: use session_id as fallback. ✓ Feasible.

3. **TeamCreate PreToolUse hook:** TeamCreate is a tool; Claude Code 2.1.32+ has PreToolUse matcher support. Hook fires BEFORE team is created, so ~/teams/ directory state is clean. ✓ Feasible.

4. **SubagentStop hook:** Documented event, fires when subagent finishes. Payload includes agent_id, agent_type, session_id, transcript_path. No token fields in payload, so hook must read transcript.jsonl directly (provided via stdin). Transcript is written by Claude Code's logger; timing is best-effort (may lag a few ms). ✓ Feasible (observational only, no blocking).

5. **Token tracking limitation:** Claude Code does NOT expose token usage in hook inputs. Transcript.jsonl does NOT always embed usage counts. Best approximation: count turns/messages + apply heuristic (250 tok/turn avg) or parse Claude API response headers (not available). SubagentStop hook has no way to get true token count; recommend post-hoc parse of transcript or integration with Anthropic usage API (requires separate service). ✓ Feasible but lossy.

6. **harness.lock read/write:** Hook reads YAML file, which is not atomic across concurrent writers. Harness.lock is NOT file-locked by hook; it assumes single writer per node (enforced by workflow.js pipeline sequencing). Bash cannot reliably implement sub-millisecond locks on POSIX. If nodes run in parallel (topology=dispatch), race conditions are possible. Mitigation: use workflow.js to sequence or pre-populate harness.lock with all node owners at launch. ✓ Feasible with assumption of sequential pipeline.

7. **Hook exit codes:** - Exit 0 = allow. - Exit 2 = deny (block tool call, send reason to user). - Exit 1 = hook error (log, allow call, do not block). ✓ Feasible.

8. **Bash tool in hook:** Hooks are shell commands by design in Claude Code settings.json. They run outside the LLM turn, so they cannot call LLM tools. Pure bash/jq is the only option. ✓ Feasible.

**Known limitations to document:**

- Write-lock is advisory (not enforced by OS). A user with --dangerously-skip-permissions or direct file system access can bypass. Harness is trust/workflow boundary, not security boundary.
- Token tracking is approximate; heuristic-based. Exact count requires Claude API usage stats (out of scope for hook).
- SubagentStop fires after transcript is written but before full cleanup; race window is ~100ms. Best-effort only.
- agent_id is absent for main leader session; use session_id fallback (less precise for multi-session harness).
- Concurrent subagent stops may write log.jsonl interleaved lines if flock not available; JSONL format is line-delimited so dedup still works.

**Validation checklist for the spec:**

✓ Reads from graph.json spine (node_id fields in harness.lock mapping).
✓ Writes to .harness/runs/log.jsonl (per-session metrics).
✓ Uses real Claude Code hook events (PreToolUse, SubagentStop).
✓ Uses real stdin JSON fields (agent_id, agent_type, session_id, tool_input.file_path, transcript_path).
✓ Compatible with Mode A workflow.js emission target.
✓ Feasible in bash; no LLM tool calls.
✓ Documents fallbacks for unavailable agent_id in main session.
✓ Explains why token tracking is best-effort.

## OPEN QUESTIONS
- 1. Should harness.lock be pre-populated by workflow.js (e.g., at Start event or via a preamble agent()) with all node owners, or should each node claim its _workspace/ subtree on first Write? (Affects: concurrent vs sequential execution safety.) Recommendation: pre-populate at Start, then validate on Write—gives determinism + safety. 2. For non-workflow harness (execution_mode=team), how should ownership be tracked? Teams do not have a fixed node DAG. Recommendation: extend harness.lock to use teammate agent_id + role name as key; leader pre-registers all teammates at spawn. 3. Should .harness/runs/log.jsonl include full transcript hash, or just a CRC32 for dedup? (Affects: disk space vs collision probability.) Recommendation: CRC32 (32 bits) with session_id + timestamp as secondary key. 4. Should the token estimate in log.jsonl be a confidence band (min/max) or a single point estimate? (Affects: cost forecasting accuracy.) Recommendation: include turns (exact), tokens_est (heuristic), and a confidence field: 'low'|'medium'|'high' based on transcript completeness. 5. For multiple teams or multiple harnesses in the same home directory, should teams and runs directories be namespaced (e.g., ~/.claude/harnesses/deep-research-v0.1/teams/)? (Affects: scalability and isolation.) Recommendation: yes, namespace by harness_name + harness_version from graph.json.