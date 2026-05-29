# Context Preservation System — Detailed Specification

> This document specifies the internal mechanisms of the Context Preservation System.
> Separated from CLAUDE.md — reference when modifying, debugging, or extending Hooks.

## How to Use Claude

- When `[CONTEXT RECOVERY]` message appears at session start, **must** read file at guided path using Read tool to restore previous context
- Snapshots are saved to `.claude/context-snapshots/latest.md`
- **Knowledge Archive**: `knowledge-index.jsonl` is a structured index accumulated across sessions. Recorded in both Stop hook and SessionEnd/PreCompact. Each entry includes completion_summary (tool success/failure), git_summary (change status), session_duration_entries (session length), phase (entire session stage), phase_flow (multi-stage transition flow, e.g., `research → implementation`), primary_language (primary file extension), error_patterns (Error Taxonomy 12 pattern classification + resolution matching), success_patterns (Edit/Write→Bash success sequence), tool_sequence (RLE-compressed tool sequence), final_status (success/incomplete/error/unknown), tags (path-based search tags). Grep tool enables programmatic exploration (RLM pattern).
- **Resume Protocol**: The "restoration instructions" section included in snapshots provide deterministically files-modified/referenced list and session information. `[CONTEXT RECOVERY]` output also displays completion status (tool success/failure) and Git change status. **Dynamic RLM Query Hints**: Automatically generates customized Grep query examples per session based on tags extracted from modified file paths (`extract_path_tags()`) and error information.
- Hook scripts access SOT (`state.yaml`) read-only only (Absolute Criterion 2 compliant). SOT file paths are centrally managed via `sot_paths()` helper, derived from `SOT_FILENAMES` constant (`state.yaml`, `state.yml`, `state.json`).

## Truncation Constants Centralization

Centrally define 10 truncation constants in `_context_lib.py`:
- `EDIT_PREVIEW_CHARS=1000` — Edit preview is 5 lines × 1000 chars, preserving edit intent and context
- `ERROR_RESULT_CHARS=3000` — Error messages are 3000 chars, preserving complete stack trace
- `MIN_OUTPUT_SIZE=100` — Minimum deliverable size

## Phase Transition Detection

`detect_phase_transitions()` function uses sliding window (20 tools, 50% overlap) to deterministically detect phase transitions within session (research → planning → implementation, etc.). Recorded in Knowledge Archive's `phase_flow` field.

## Decision Quality Tag Alignment

The "major design decisions" section (IMMORTAL priority) in snapshot is sorted by quality tag — `[explicit]` > `[decision]` > `[rationale]` > `[intent]` in order, filling 15 slots so everyday intent declarations (`will do` patterns) don't push out actual design decisions.

## IMMORTAL-aware Compression

When snapshot size exceeds, Phase 7 hard truncate preserves IMMORTAL section first. Truncates non-IMMORTAL content first, preserves beginning of IMMORTAL text even in extreme cases.

**Compression Audit Trail**: Each compression Phase records character count removed in HTML comment (`<!-- compression-audit: ... -->`) at snapshot end (Phase 1~7 delta + final size).

## Error Taxonomy

Classify tool errors into 12 patterns:
`file_not_found`, `permission`, `syntax`, `timeout`, `dependency`, `edit_mismatch`, `type_error`, `value_error`, `connection`, `memory`, `git_error`, `command_not_found`

Recorded in Knowledge Archive's error_patterns field, reduces "unknown" classification to ~30%. Applies negative lookahead, quantifier matching, etc. to prevent false positives.

**Error→Resolution Matching**: Detects successful tool call within 5 entries after error via file-aware matching, records in `resolution` field. Enables cross-session search via `Grep "resolution" knowledge-index.jsonl`.

## Quality Gate Status IMMORTAL Preservation

`_extract_quality_gate_state()` function extracts latest stage quality gate results from `pacs-logs/`, `review-logs/`, `verification-logs/`, preserves them as IMMORTAL section in snapshot.

## Phase Transition Snapshot Header

In sessions where multi-stage transitions are detected, displays transition flow in snapshot header in format `Phase flow: research(12) → implementation(25)`.

## Error→Resolution Auto-Surfacing

`_extract_recent_error_resolutions()` function in `restore_context.py` reads error_patterns from recent sessions in Knowledge Archive, directly displays maximum 3 error→resolution patterns in SessionStart output.

## Runtime Directory Auto-Generation

`_check_runtime_dirs()` function in `setup_init.py` automatically creates 6 directories when SOT file exists: `verification-logs/`, `pacs-logs/`, `review-logs/`, `autopilot-logs/`, `translations/`, `diagnosis-logs/`.

## System Command Filtering

In snapshot's "current work" section, automatically filters system commands like `/clear`, `/help`, captures only actual user work intent.

## Autopilot Runtime Intensification

When Autopilot active, SessionStart injects execution rules into context, includes Autopilot status section (IMMORTAL priority) in snapshot, Stop hook detects and supplements missing Decision Log.

## ULW Mode Detection and Preservation

`detect_ulw_mode()` function detects "ulw" keyword from transcript via word-boundary regex. **Implicit deactivation**: Does not inject rules in new session (`source=startup`) even if previous snapshot has ULW status — only `clear`/`compact`/`resume` source inherits ULW.

## Predictive Debugging

`aggregate_risk_scores()` aggregates error_patterns from Knowledge Archive by file to derive risk scores (weight × decay). Executed once at SessionStart, generates `risk-scores.json` cache, `predictive_debug_guard.py` reads cache on every Edit/Write, outputs warning when threshold exceeded.

**Startup Tradeoff**: SessionStart matcher is `clear|compact|resume`, so cache not generated on initial startup (ADR-036).

**Basename merge**: When bare name and relative path mixed, automatically merge same-basename entries, prevents risk score underestimation.

---

## Hook Configuration Location

All Hooks are integrated and defined in **Project** (`.claude/settings.json`). Hook infrastructure automatically applies with just `git clone`.

- Stop → `context_guard.py --mode=stop` → `generate_context_summary.py`
- PostToolUse → `context_guard.py --mode=post-tool` → `update_work_log.py` (matcher: `Edit|Write|Bash|Task|NotebookEdit|TeamCreate|SendMessage|TaskCreate|TaskUpdate`)
- PreCompact → `context_guard.py --mode=pre-compact` → `save_context.py --trigger precompact`
- SessionStart → `context_guard.py --mode=restore` → `restore_context.py` (matcher: `clear|compact|resume`)
- **PreToolUse** → `block_destructive_commands.py` (matcher: `Bash`, independent execution — preserve exit code 2)
- **PreToolUse** → `block_test_file_edit.py` (matcher: `Edit|Write`, independent execution — `.tdd-guard` toggle)
- **PreToolUse** → `predictive_debug_guard.py` (matcher: `Edit|Write`, independent execution — warnings only)
- **PostToolUse** → `output_secret_filter.py` (matcher: `Bash|Read`, independent execution — secret detection, exit 0 warning)
- **PostToolUse** → `security_sensitive_file_guard.py` (matcher: `Edit|Write`, independent execution — sensitive file warning, exit 0)
- SessionEnd → `save_context.py --trigger sessionend` (matcher: `clear`)
- Setup (init) → `setup_init.py` — infrastructure health validation (`claude --init`)
- Setup (maintenance) → `setup_maintenance.py` — periodic health checkup (`claude --maintenance`)

### Hook Design Decisions

> **Unified `if test -f; then; fi` pattern**: All Hook commands use `if test -f; then; fi` pattern. Removes previous `|| true` pattern (latent bug that swallows exit code 2 block signals).
> **Rationale for PreToolUse Safety Hook independent execution**: `block_destructive_commands.py` and `block_test_file_edit.py` are different domain from context preservation. Exit code 2 preservation is essential, so execute directly without going through `context_guard.py`.
> **Rationale for PostToolUse Security Hook independent execution (ADR-050)**: `output_secret_filter.py` and `security_sensitive_file_guard.py` are security domain, independent concern from context preservation (`update_work_log.py`). Use their own data sources (direct transcript JSONL read, session deduplication, etc.), so execute directly without going through `context_guard.py` dispatcher.

### D-7 Intentional Duplication Instances

| # | Instance | Location A | Location B |
|---|----------|-----------|-----------|
| 1 | `REQUIRED_SCRIPTS` (20) | `setup_init.py` | `setup_maintenance.py` |
| 2 | `RISK_THRESHOLD`/`MIN_SESSIONS` | `predictive_debug_guard.py` | `_context_lib.py` |
| 3 | `ERROR_TAXONOMY` type names (12) | `_classify_error_patterns()` | `_RISK_WEIGHTS` (13) |
| 4 | ULW detection pattern | `_gather_retry_history()` | `validate_retry_budget.py` + `restore_context.py` |
| 5 | Retry limit constant | `validate_retry_budget.py` | `_context_lib.py` + `restore_context.py` |
| 6 | `SOT_FILENAMES` tuple | `_context_lib.py` `SOT_FILENAMES` | `setup_init.py` + `query_workflow.py` `_SOT_FILENAMES` |

Each D-7 instance has cross-reference comments in code; must synchronize corresponding side when one side changes.

**Automatic Validation**: `_check_doc_code_sync()` in `setup_maintenance.py` deterministically validates DC-1~DC-5:
- DC-1: Retry limit documentation ↔ code
- DC-2: Risk constant synchronization
- DC-3: ULW detection pattern synchronization
- DC-4: Retry limit constant synchronization
- DC-5: SOT_FILENAMES 3-way synchronization (`_context_lib.py` ↔ `setup_init.py` ↔ `query_workflow.py`)
