#!/usr/bin/env python3
"""
State Management Module — SOT read-only access, Autopilot/Team/ULW state inspection.

Functions:
  - sot_paths(project_dir) → dict
  - capture_sot(project_dir) → dict
  - read_autopilot_state(project_dir) → dict
  - validate_sot_schema(state) → bool
  - read_active_team_state(project_dir) → dict
  - detect_ulw_mode(entries) → bool
  - check_ulw_compliance(entries) → dict
  - capture_git_state(project_dir) → dict
  - extract_completion_state(entries, project_dir) → dict
  - detect_conversation_phase(tool_uses) → str
  - detect_phase_transitions(tool_uses) → list
"""

import json
import os
import re
import sys
import time
import fcntl
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import subprocess
import re
from pathlib import Path

# --- SOT file paths (single definition — Absolute Criteria 2) ---
SOT_FILENAMES = ("state.yaml", "state.yml", "state.json")

# --- Tool result error detection patterns (shared by check_ulw_compliance + extract_completion_state) ---
TOOL_ERROR_PATTERNS = [
    "Error:", "error:", "FAILED", "failed",
    "not found", "Permission denied", "No such file",
]

# --- Path tag extraction constants (A3: language-independent search tags) ---
_PATH_SKIP_NAMES = frozenset({
    "src", "lib", "dist", "build", "node_modules", "venv", ".git",
    "tests", "test", "__pycache__", ".claude", "scripts", "hooks",
})
_EXT_TAGS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "react", ".jsx": "react", ".md": "markdown",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json",
    ".sh": "shell", ".css": "css", ".html": "html",
    ".rs": "rust", ".go": "golang", ".java": "java",
}

# --- Predictive Debugging: Risk Score Constants (P1 — module-level) ---
# Used by aggregate_risk_scores() and validate_risk_scores()
# Weights per error type: higher = more indicative of fragile code
# D-7: Keys MUST match ERROR_TAXONOMY in _classify_error_patterns() (~line 2812)
#      + "unknown" for unclassified errors. Mismatch → fallback weight 0.7 applied.
_RISK_WEIGHTS = {
    "edit_mismatch": 2.0,   # File structure instability (frequent edit failures)
    "dependency": 2.5,       # High ripple effect
    "type_error": 1.5,       # Type complexity
    "syntax": 1.0,           # Repetitive — complex file indicator
    "value_error": 1.0,
    "git_error": 1.0,
    "timeout": 0.5,          # Often environmental, not code
    "file_not_found": 0.5,   # Usually one-time
    "permission": 0.5,
    "connection": 0.3,       # Network — may not be code issue
    "memory": 0.3,
    "command_not_found": 0.3,
    "unknown": 0.7,          # ~30% of errors — ignoring loses significant data
}
# Recency decay: (max_days, weight_multiplier)
# More recent errors are more relevant to current code state
_RECENCY_DECAY_DAYS = [
    (30, 1.0),              # 0-30 days: full weight
    (90, 0.5),              # 31-90 days: half weight
    (float("inf"), 0.25),   # 91+ days: quarter weight
]
# Minimum risk score to trigger PreToolUse warning
_RISK_SCORE_THRESHOLD = 3.0
# Minimum sessions in knowledge-index before activation (cold start guard)
_RISK_MIN_SESSIONS = 5

# --- Pre-compiled regex patterns (module-level — compiled once per process) ---
# Used by _extract_next_step()
_NEXT_STEP_RE = re.compile(
    r'(?:다음으로|이제|그 다음|그 후|Next,?|Now |Then )'
    r'\s*(.{10,500}?)(?:\.\s|\n\n|$)',
    re.MULTILINE,
)
# Used by _extract_decisions()
_DECISION_MARKER_RE = re.compile(r'<!--\s*DECISION:\s*(.+?)\s*-->', re.DOTALL)
_DECISION_BOLD_RE = re.compile(
    r'\*\*(?:Decision|결정|선택|채택|판단)\s*(?::|：)\*\*\s*(.+?)(?:\n|$)',
    re.IGNORECASE,
)
_DECISION_INTENT_NOISE_RE = re.compile(
    r'읽겠습니다|확인하겠습니다|시작하겠습니다|살펴보겠습니다|'
    r'진행하겠습니다|분석하겠습니다|검토하겠습니다|파악하겠습니다|'
    r'Let me read|Let me check|I\'ll start|I\'ll look',
    re.IGNORECASE,
)
_DECISION_INTENT_RE = re.compile(
    r'(?:^|\n)\s*[-*]?\s*(.{10,120}?(?:하겠습니다|로 결정|을 선택|를 채택|접근 방식|approach))',
    re.MULTILINE,
)
_DECISION_RATIONALE_RE = re.compile(
    r'(?:선택\s*이유|근거|Rationale|Reason(?:ing)?)\s*(?::|：)\s*(.+?)(?:\n|$)',
    re.IGNORECASE,
)
_DECISION_COMPARISON_RE = re.compile(
    r'(.{5,80}?)\s+(?:대신|보다는?|rather than|instead of|over)\s+(.{5,80}?)(?:\.|,|\n|$)',
    re.IGNORECASE | re.MULTILINE,
)
_DECISION_TRADEOFF_RE = re.compile(
    r'(?:trade-?off|장단점|pros?\s*(?:and|&)\s*cons?|단점은|downside)\s*(?::|：|은|는)?\s*(.+?)(?:\n|$)',
    re.IGNORECASE,
)
_DECISION_CHOICE_RE = re.compile(
    r'(?:chose|opted for|selected|decided to|went with|picked)\s+(.{10,150}?)(?:\.|,|\n|$)',
    re.IGNORECASE,
)
# Used by generate_snapshot_md() — system command filter for "Current Work" section
_SYSTEM_CMD_RE = re.compile(
    r'^\s*<command-name>|^\s*/(?:clear|help|compact|init|resume|review|login|logout|mcp|config)\b',
    re.IGNORECASE | re.MULTILINE,
)

# Used by Abductive Diagnosis functions — diagnosis-logs/ parsing
# Captures the FULL heading line (including H-ID) so AD9 can extract H[1-4] from it.
# E.g., "## H1: Upstream data quality issue" → captures "H1: Upstream data quality issue"
_DIAG_HYPOTHESIS_RE = re.compile(
    r"^#+\s*((?:H\d|Hypothesis)\b.+)", re.MULTILINE | re.IGNORECASE,
)
_DIAG_SELECTED_RE = re.compile(
    r"(?:Selected|Chosen|Primary)\s*(?:Hypothesis|H\d)\s*:\s*(.+)",
    re.IGNORECASE,
)
_DIAG_EVIDENCE_RE = re.compile(
    r"^-\s*\*?\*?Evidence\*?\*?\s*:\s*(.+)", re.MULTILINE | re.IGNORECASE,
)
_DIAG_GATE_RE = re.compile(
    r"Gate\s*:\s*(verification|pacs|review)", re.IGNORECASE,
)
_DIAG_SOURCE_STEP_RE = re.compile(
    r"\(source:\s*Step\s+(\d+)\)", re.IGNORECASE,
)

# =============================================================================
# SOT State Capture
# =============================================================================

def sot_paths(project_dir):
    """Build SOT file path list from SOT_FILENAMES constant (A-3: single definition)."""
    return [os.path.join(project_dir, ".claude", fn) for fn in SOT_FILENAMES]


def capture_sot(project_dir):
    """
    Read SOT file (state.yaml) if it exists.
    Hook is READ-ONLY for SOT — only captures content.
    """
    for sot_path in sot_paths(project_dir):
        if os.path.exists(sot_path):
            try:
                with open(sot_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return {
                    "path": sot_path,
                    "content": _truncate(content, SOT_CAPTURE_CHARS),
                    "mtime": datetime.fromtimestamp(
                        os.path.getmtime(sot_path)
                    ).isoformat(),
                }
            except Exception:
                pass

    return None


# =============================================================================
# Autopilot State (Read-Only — SOT Compliance)
# =============================================================================

def read_autopilot_state(project_dir):
    """Read autopilot state from SOT (state.yaml). Read-only.

    Returns dict with autopilot fields if enabled, None otherwise.

    IMPORTANT: Does NOT use capture_sot() — reads state.yaml directly
    without truncation. capture_sot() truncates to 3000 chars (for snapshot
    display), which can cut the autopilot section in large SOT files.

    Schema compatibility: Supports both AGENTS.md schema (workflow.autopilot)
    and flat schema (top-level autopilot). AGENTS.md §5.1 is authoritative.

    P1 Compliance: All fields are deterministic extractions from YAML/regex.
    SOT Compliance: Read-only file access.
    """
    # Direct file read — uses sot_paths() for consistency (A-3)
    # Only YAML files (not JSON) — autopilot regex patterns assume YAML format
    # CQ-1: Renamed to avoid shadowing the sot_paths() function
    yaml_sot_paths = [p for p in sot_paths(project_dir) if not p.endswith(".json")]

    content = ""
    for sot_path in yaml_sot_paths:
        if os.path.exists(sot_path):
            try:
                with open(sot_path, "r", encoding="utf-8") as f:
                    content = f.read()
                break
            except Exception:
                continue

    if not content:
        return None

    # Try PyYAML first (precise structured parsing)
    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            # Schema compatibility: check both locations
            # AGENTS.md §5.1 schema: workflow.autopilot.enabled
            # Flat schema: autopilot.enabled (top-level)
            wf = data.get("workflow", {})
            if not isinstance(wf, dict):
                wf = {}
            ap = wf.get("autopilot") or data.get("autopilot")
            if not isinstance(ap, dict) or not ap.get("enabled"):
                return None
            return {
                "enabled": True,
                "activated_at": ap.get("activated_at", ""),
                "auto_approved_steps": ap.get("auto_approved_steps", []),
                "current_step": wf.get("current_step", 0),
                "workflow_name": wf.get("name", ""),
                "workflow_status": wf.get("status", ""),
                "outputs": wf.get("outputs", {}),
            }
    except Exception:
        pass

    # Regex fallback (when PyYAML is not available)
    # Matches both "autopilot:\n  enabled: true" at any nesting level
    enabled_match = re.search(
        r'autopilot\s*:\s*\n\s+enabled\s*:\s*(true|yes)',
        content, re.IGNORECASE
    )
    if not enabled_match:
        return None

    state = {
        "enabled": True,
        "activated_at": "",
        "auto_approved_steps": [],
        "current_step": 0,
        "workflow_name": "",
        "workflow_status": "",
        "outputs": {},
    }

    for field, pattern in [
        ("activated_at", r'activated_at\s*:\s*["\']?(.+?)["\']?\s*$'),
        ("current_step", r'current_step\s*:\s*(\d+)'),
        ("workflow_name", r'name\s*:\s*["\']?(.+?)["\']?\s*$'),
        ("workflow_status", r'status\s*:\s*["\']?(.+?)["\']?\s*$'),
    ]:
        m = re.search(pattern, content, re.MULTILINE)
        if m:
            val = m.group(1).strip()
            state[field] = int(val) if field == "current_step" else val

    # Extract auto_approved_steps list
    steps_match = re.search(r'auto_approved_steps\s*:\s*\[([^\]]*)\]', content)
    if steps_match:
        steps_str = steps_match.group(1)
        state["auto_approved_steps"] = [
            int(s.strip()) for s in steps_str.split(",")
            if s.strip().isdigit()
        ]

    # Extract outputs map
    outputs_section = re.search(
        r'outputs\s*:\s*\n((?:\s+step-\d+\s*:.+\n?)*)', content
    )
    if outputs_section:
        for m in re.finditer(
            r'(step-\d+)\s*:\s*["\']?(.+?)["\']?\s*$',
            outputs_section.group(1), re.MULTILINE
        ):
            state["outputs"][m.group(1)] = m.group(2).strip()

    return state


def validate_sot_schema(ap_state):
    """SOT Schema Validation: structural integrity of autopilot state dict.

    P1 Compliance: All checks are deterministic (type, range, format).
    SOT Compliance: Read-only — validates in-memory dict, no file I/O.
    No duplication: file existence is validate_step_output()'s responsibility.

    Args:
        ap_state: dict from read_autopilot_state(), or None

    Returns: list of warning strings (empty list = all checks passed)
    """
    if not ap_state or not isinstance(ap_state, dict):
        return []

    warnings = []

    # S1: current_step — must be int >= 0
    cs = ap_state.get("current_step")
    if cs is not None:
        if not isinstance(cs, int):
            warnings.append(
                f"SOT schema: current_step is {type(cs).__name__}, expected int"
            )
        elif cs < 0:
            warnings.append(f"SOT schema: current_step is {cs}, must be >= 0")

    # S2: outputs — must be dict
    outputs = ap_state.get("outputs")
    if outputs is not None and not isinstance(outputs, dict):
        warnings.append(
            f"SOT schema: outputs is {type(outputs).__name__}, expected dict"
        )

    # S3: outputs keys — must follow step-N or step-N-ko format
    if isinstance(outputs, dict):
        for key in outputs:
            if not isinstance(key, str) or not key.startswith("step-"):
                warnings.append(f"SOT schema: invalid output key '{key}'")
                continue
            # Extract step number — allow step-N and step-N-ko (translation)
            suffix = key[5:]  # after "step-"
            parts = suffix.split("-", 1)
            if not parts[0].isdigit():
                warnings.append(
                    f"SOT schema: output key '{key}' has non-numeric step number"
                )

    # S4: No output recorded for future steps (step number > current_step)
    if isinstance(cs, int) and isinstance(outputs, dict):
        for key in outputs:
            if isinstance(key, str) and key.startswith("step-"):
                suffix = key[5:]
                parts = suffix.split("-", 1)
                if parts[0].isdigit():
                    step_num = int(parts[0])
                    if step_num > cs:
                        warnings.append(
                            f"SOT schema: output '{key}' for future step "
                            f"(current_step={cs})"
                        )

    # S5: workflow_status — must be recognized value
    status = ap_state.get("workflow_status", "")
    if status:
        valid_statuses = {"running", "completed", "error", "paused"}
        if status not in valid_statuses:
            warnings.append(
                f"SOT schema: unrecognized workflow_status '{status}'"
            )

    # S6: auto_approved_steps — items must be int, within plausible range
    approved = ap_state.get("auto_approved_steps", [])
    if isinstance(approved, list):
        for item in approved:
            if not isinstance(item, int):
                warnings.append(
                    f"SOT schema: auto_approved_steps contains non-int: {item}"
                )
            elif isinstance(cs, int) and item > cs:
                warnings.append(
                    f"SOT schema: auto_approved_steps contains future step "
                    f"{item} (current_step={cs})"
                )

    # S7: pacs — must be dict with valid structure (if present)
    pacs = ap_state.get("pacs")
    if pacs is not None:
        if not isinstance(pacs, dict):
            warnings.append(
                f"SOT schema: pacs is {type(pacs).__name__}, expected dict"
            )
        else:
            # S7a: dimensions — dict with F, C, L keys (int 0-100)
            dims = pacs.get("dimensions")
            if dims is not None:
                if not isinstance(dims, dict):
                    warnings.append("SOT schema: pacs.dimensions must be dict")
                else:
                    for dim_key in ("F", "C", "L"):
                        dim_val = dims.get(dim_key)
                        if dim_val is not None:
                            if not isinstance(dim_val, (int, float)):
                                warnings.append(
                                    f"SOT schema: pacs.dimensions.{dim_key} is "
                                    f"{type(dim_val).__name__}, expected int"
                                )
                            elif not (0 <= dim_val <= 100):
                                warnings.append(
                                    f"SOT schema: pacs.dimensions.{dim_key} = "
                                    f"{dim_val}, must be 0-100"
                                )
            # S7b: current_step_score — int 0-100
            score = pacs.get("current_step_score")
            if score is not None:
                if not isinstance(score, (int, float)):
                    warnings.append(
                        f"SOT schema: pacs.current_step_score is "
                        f"{type(score).__name__}, expected int"
                    )
                elif not (0 <= score <= 100):
                    warnings.append(
                        f"SOT schema: pacs.current_step_score = {score}, "
                        f"must be 0-100"
                    )
            # S7c: weak_dimension — must be one of F, C, L
            weak = pacs.get("weak_dimension")
            if weak is not None and weak not in ("F", "C", "L"):
                warnings.append(
                    f"SOT schema: pacs.weak_dimension = '{weak}', "
                    f"must be one of F, C, L"
                )
            # S7d: history — must be dict of step-keys → {score, weak}
            # Schema: claude-code-patterns.md § SOT pacs field schema
            #   history:
            #     step-1: {score: 85, weak: "C"}
            history = pacs.get("history")
            if history is not None:
                if not isinstance(history, dict):
                    warnings.append(
                        f"SOT schema: pacs.history is "
                        f"{type(history).__name__}, expected dict"
                    )
                else:
                    for hkey, hval in history.items():
                        if not isinstance(hval, dict):
                            warnings.append(
                                f"SOT schema: pacs.history.{hkey} is "
                                f"{type(hval).__name__}, expected dict"
                            )
                            continue
                        hscore = hval.get("score")
                        if hscore is not None:
                            if not isinstance(hscore, (int, float)):
                                warnings.append(
                                    f"SOT schema: pacs.history.{hkey}.score "
                                    f"is {type(hscore).__name__}, expected int"
                                )
                            elif not (0 <= hscore <= 100):
                                warnings.append(
                                    f"SOT schema: pacs.history.{hkey}.score "
                                    f"= {hscore}, must be 0-100"
                                )
                        hweak = hval.get("weak")
                        if hweak is not None and hweak not in ("F", "C", "L"):
                            warnings.append(
                                f"SOT schema: pacs.history.{hkey}.weak "
                                f"= '{hweak}', must be F, C, or L"
                            )
            # S7e: pre_mortem_flag — must be string (if present)
            pmf = pacs.get("pre_mortem_flag")
            if pmf is not None and not isinstance(pmf, str):
                warnings.append(
                    f"SOT schema: pacs.pre_mortem_flag is "
                    f"{type(pmf).__name__}, expected string"
                )

    # S8: active_team — must be dict with required fields (if present)
    active_team = ap_state.get("active_team")
    if active_team is not None:
        if not isinstance(active_team, dict):
            warnings.append(
                f"SOT schema: active_team is {type(active_team).__name__}, "
                f"expected dict"
            )
        else:
            # S8a: name — must be non-empty string
            team_name = active_team.get("name")
            if team_name is not None and not isinstance(team_name, str):
                warnings.append("SOT schema: active_team.name must be string")
            # S8b: status — must be recognized value
            # Schema: claude-code-patterns.md § SOT update protocol
            #   "partial" (team work in progress) | "all_completed" (all tasks done)
            team_status = active_team.get("status")
            valid_team_statuses = {"partial", "all_completed"}
            if team_status and team_status not in valid_team_statuses:
                warnings.append(
                    f"SOT schema: active_team.status '{team_status}' "
                    f"unrecognized (expected: partial | all_completed)"
                )
            # S8c: tasks_completed — must be list (if present)
            tc = active_team.get("tasks_completed")
            if tc is not None and not isinstance(tc, list):
                warnings.append(
                    f"SOT schema: active_team.tasks_completed is "
                    f"{type(tc).__name__}, expected list"
                )
            # S8d: tasks_pending — must be list (if present)
            tp = active_team.get("tasks_pending")
            if tp is not None and not isinstance(tp, list):
                warnings.append(
                    f"SOT schema: active_team.tasks_pending is "
                    f"{type(tp).__name__}, expected list"
                )
            # S8e: completed_summaries — must be dict (if present)
            cs_summaries = active_team.get("completed_summaries")
            if cs_summaries is not None:
                if not isinstance(cs_summaries, dict):
                    warnings.append(
                        f"SOT schema: active_team.completed_summaries is "
                        f"{type(cs_summaries).__name__}, expected dict"
                    )
                else:
                    for task_id, info in cs_summaries.items():
                        if not isinstance(info, dict):
                            warnings.append(
                                f"SOT schema: active_team.completed_summaries"
                                f".{task_id} must be dict"
                            )

    return warnings


# =============================================================================
# Active Team State (Read-Only — SOT Compliance, RLM Layer 2)
# =============================================================================

def read_active_team_state(project_dir):
    """Read active_team state from SOT (state.yaml). Read-only.

    Returns dict with active_team fields if a team is active, None otherwise.
    This enables 2-Layer RLM: Layer 1 (auto snapshots) + Layer 2 (team summaries in SOT).

    Schema (from claude-code-patterns.md § SOT update protocol):
      active_team:
        name: "team-name"
        status: "partial" | "all_completed"
        tasks_completed: ["task-1", ...]
        tasks_pending: ["task-2", ...]
        completed_summaries:
          task-1:
            agent: "@researcher"
            model: "sonnet"
            output: "path/to/output.md"
            summary: "brief description"

    P1 Compliance: All fields are deterministic extractions from YAML/regex.
    SOT Compliance: Read-only file access.
    """
    # A-3: use sot_paths() — YAML only (regex parsing)
    # B-1: Renamed to avoid shadowing the sot_paths() function (same fix as CQ-1)
    yaml_sot_paths = [p for p in sot_paths(project_dir) if not p.endswith(".json")]

    content = ""
    for sot_path in yaml_sot_paths:
        if os.path.exists(sot_path):
            try:
                with open(sot_path, "r", encoding="utf-8") as f:
                    content = f.read()
                break
            except Exception:
                continue

    if not content:
        return None

    # Try PyYAML first (precise structured parsing)
    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            # Check both nested (workflow.active_team) and flat (active_team)
            wf = data.get("workflow", {})
            if not isinstance(wf, dict):
                wf = {}
            at = wf.get("active_team") or data.get("active_team")
            if not isinstance(at, dict) or not at.get("name"):
                return None
            return {
                "name": at.get("name", ""),
                "status": at.get("status", "unknown"),
                "tasks_completed": at.get("tasks_completed", []),
                "tasks_pending": at.get("tasks_pending", []),
                "completed_summaries": at.get("completed_summaries", {}),
            }
    except Exception:
        pass

    # Regex fallback (when PyYAML is not available)
    name_match = re.search(
        r'active_team\s*:\s*\n\s+name\s*:\s*["\']?(.+?)["\']?\s*$',
        content, re.MULTILINE
    )
    if not name_match:
        return None

    state = {
        "name": name_match.group(1).strip(),
        "status": "unknown",
        "tasks_completed": [],
        "tasks_pending": [],
        "completed_summaries": {},
    }

    status_match = re.search(
        r'active_team\s*:.*?status\s*:\s*["\']?(\w+)["\']?',
        content, re.DOTALL
    )
    if status_match:
        state["status"] = status_match.group(1).strip()

    # Extract task lists (YAML inline array format)
    for field in ["tasks_completed", "tasks_pending"]:
        m = re.search(rf'{field}\s*:\s*\[([^\]]*)\]', content)
        if m:
            items = [s.strip().strip("\"'") for s in m.group(1).split(",") if s.strip()]
            state[field] = items

    return state


# =============================================================================
# ULW (Ultrawork) Mode Detection
# =============================================================================

def detect_ulw_mode(entries):
    """Detect ULW (Ultrawork) mode activation from user messages.

    Scans transcript entries for the "ulw" keyword in user messages.
    Uses word-boundary regex to prevent false positives from variable names,
    file paths, or URLs (e.g., "resultw", "/usr/local/ulwrap").

    Args:
        entries: List of parsed transcript entries.

    Returns:
        dict with {active, detected_in, source_message, message_index} or None.

    P1 Compliance: Deterministic regex match on verbatim user messages.
    """
    # Word-boundary pattern: not preceded/followed by alphanumeric, underscore, slash, dot, hyphen
    ULW_PATTERN = re.compile(
        r'(?<![a-zA-Z0-9_/\-\.])ulw(?![a-zA-Z0-9_/\-\.])',
        re.IGNORECASE,
    )

    user_messages = [
        (i, e) for i, e in enumerate(entries)
        if e.get("type") == "user_message"
        and not (e.get("content", "").startswith("<") and ">" in e.get("content", "")[:50])
    ]

    for idx, (msg_index, entry) in enumerate(user_messages):
        content = entry.get("content", "")
        if ULW_PATTERN.search(content):
            return {
                "active": True,
                "detected_in": "first" if idx == 0 else "subsequent",
                "source_message": content[:500],
                "message_index": msg_index,
            }

    return None


def _extract_file_from_nearby_tool_use(entries, error_idx, window=3):
    """Extract file path from tool_use entries near an error (private helper).

    Looks backward from error_idx within `window` entries for Edit/Write
    tool_use with a file_path field.

    Note: parse_transcript() stores file_path at the entry's top level
    (not nested under "parameters" or "input") — see line 341/345 of
    _parse_assistant_entry().

    Returns:
        str or None: file path if found.
    """
    start = max(0, error_idx - window)
    for i in range(error_idx - 1, start - 1, -1):
        entry = entries[i]
        if entry.get("type") == "tool_use":
            name = entry.get("tool_name", "")
            if name in ("Edit", "Write"):
                # file_path is a top-level key set by parse_transcript()
                fp = entry.get("file_path", "")
                if fp:
                    return fp
    return None


def check_ulw_compliance(entries):
    """Verify deterministically whether 3 ULW mode intensifier rules are complied with when ULW is active.

    All checks are pure counting and pattern matching — P1 compliant.
    No heuristic inference. No AI judgment.

    Intensifiers:
      I-1. Sisyphus Persistence: error recovery + no partial completion (max 3 retries)
      I-2. Mandatory Task Decomposition: TaskCreate/TaskUpdate/TaskList usage
      I-3. Bounded Retry Escalation: no more than 3 consecutive retries on same target

    Args:
        entries: List of parsed transcript entries.

    Returns:
        dict with compliance metrics and warnings, or None if ULW inactive.
    """
    ulw_state = detect_ulw_mode(entries)
    if not ulw_state:
        return None

    # Filter: only count entries AFTER ULW activation point
    # Prevents false positives when ULW is activated in a "subsequent" message
    ulw_start_idx = ulw_state["message_index"]
    post_ulw_entries = entries[ulw_start_idx:]

    tool_uses = [e for e in post_ulw_entries if e.get("type") == "tool_use"]

    compliance = {
        "active": True,
        "task_creates": 0,
        "task_updates": 0,
        "task_lists": 0,
        "total_tool_uses": len(tool_uses),
        "errors_detected": 0,
        "post_error_actions": 0,
        "max_consecutive_retries": 0,
        "warnings": [],
    }

    # Count task management tool uses
    for tu in tool_uses:
        name = tu.get("tool_name", "")
        if name == "TaskCreate":
            compliance["task_creates"] += 1
        elif name == "TaskUpdate":
            compliance["task_updates"] += 1
        elif name == "TaskList":
            compliance["task_lists"] += 1

    # Detect errors and post-error recovery attempts
    # Uses module-level TOOL_ERROR_PATTERNS (DRY — shared with extract_completion_state)
    last_error_global_idx = -1
    # Track consecutive retries on same file for I-3
    error_file_sequence = []  # list of (file_path_or_None,)

    for i, entry in enumerate(post_ulw_entries):
        if entry.get("type") == "tool_result":
            is_error = entry.get("is_error", False)
            content = entry.get("content", "")[:500]
            if is_error or any(sig in content for sig in TOOL_ERROR_PATTERNS):
                compliance["errors_detected"] += 1
                last_error_global_idx = i
                fp = _extract_file_from_nearby_tool_use(post_ulw_entries, i)
                error_file_sequence.append(fp)

    # Count tool uses that occurred AFTER the last error (recovery attempts)
    if last_error_global_idx >= 0:
        for i, entry in enumerate(post_ulw_entries):
            if i > last_error_global_idx and entry.get("type") == "tool_use":
                compliance["post_error_actions"] += 1

    # I-3: Detect max consecutive retries on same file
    if error_file_sequence:
        max_consecutive = 1
        current_run = 1
        for j in range(1, len(error_file_sequence)):
            prev_fp = error_file_sequence[j - 1]
            curr_fp = error_file_sequence[j]
            if prev_fp and curr_fp and prev_fp == curr_fp:
                current_run += 1
                if current_run > max_consecutive:
                    max_consecutive = current_run
            else:
                current_run = 1
        compliance["max_consecutive_retries"] = max_consecutive

    # Generate deterministic warnings — mapped to 3 Intensifiers

    # W1 (I-1 Sisyphus Persistence): Errors detected but no subsequent actions
    if compliance["errors_detected"] > 0 and compliance["post_error_actions"] == 0:
        compliance["warnings"].append(
            "ULW_NO_SISYPHUS: {} errors detected, 0 follow-up actions — I-1 Sisyphus Persistence not met".format(
                compliance["errors_detected"]
            )
        )

    # W2 (I-2 Mandatory Task Decomposition): No task tracking despite significant tool usage
    if compliance["task_creates"] == 0 and compliance["total_tool_uses"] >= 5:
        compliance["warnings"].append(
            "ULW_NO_DECOMPOSITION: {} tool uses, 0 TaskCreate — I-2 Mandatory Task Decomposition not met".format(
                compliance["total_tool_uses"]
            )
        )

    # W2a (I-2 sub): Tasks created but never updated (no progress tracking)
    if compliance["task_creates"] > 0 and compliance["task_updates"] == 0:
        compliance["warnings"].append(
            "ULW_NO_PROGRESS: {} TaskCreate, 0 TaskUpdate — I-2 Progress Tracking not met".format(
                compliance["task_creates"]
            )
        )

    # W2b (I-2 sub): Tasks created but never listed (no completion verification)
    if compliance["task_creates"] > 0 and compliance["task_lists"] == 0:
        compliance["warnings"].append(
            "ULW_NO_VERIFY: TaskCreate {}회, TaskList 0회 — I-2 완료 검증 미수행".format(
                compliance["task_creates"]
            )
        )

    # W3 (I-3 Bounded Retry Escalation): Same target retried > 3 times consecutively
    if compliance["max_consecutive_retries"] > 3:
        compliance["warnings"].append(
            "ULW_RETRY_EXCEEDED: 동일 대상 연속 재시도 {}회 — I-3 Bounded Retry 초과 (최대 3회)".format(
                compliance["max_consecutive_retries"]
            )
        )

    return compliance


# =============================================================================
# Git State Capture (E2 — Ground Truth)
# =============================================================================

def capture_git_state(project_dir, max_diff_chars=8000):
    """Git 변경 상태의 결정론적 캡처 (읽기 전용, SOT 준수).

    3개 시그널을 캡처하여 모든 시나리오에서 ground-truth 제공:
    1. git status --porcelain  (현재 작업 트리 상태)
    2. git diff HEAD            (커밋되지 않은 변경)
    3. git log --oneline --stat -5  (최근 커밋 — post-commit 시나리오 대응)

    P1 Compliance: All fields are subprocess stdout captures (deterministic).
    SOT Compliance: git commands are read-only.
    """
    result = {"status": "", "diff_stat": "", "diff_content": "", "recent_commits": ""}

    def _run_git(args, max_chars=2000):
        try:
            proc = subprocess.run(
                ["git"] + args,
                cwd=project_dir, capture_output=True, text=True, timeout=5
            )
            return proc.stdout.strip()[:max_chars] if proc.returncode == 0 else ""
        except Exception:
            return ""

    result["status"] = _run_git(["status", "--porcelain"])
    result["diff_stat"] = _run_git(["diff", "--stat", "HEAD"])
    result["diff_content"] = _run_git(["diff", "HEAD"], max_chars=max_diff_chars)
    result["recent_commits"] = _run_git(
        ["log", "--oneline", "--stat", "-5"], max_chars=3000
    )

    return result


# =============================================================================
# Deterministic Completion State (E7 — Hallucination Prevention)
# =============================================================================

def extract_completion_state(entries, project_dir):
    """결정론적 완료 상태 추출 — Claude 해석 불필요.

    P1 Compliance: All fields are deterministic extractions from
    transcript entries + filesystem checks. Zero heuristic inference.

    Hallucination prevention: Claude reads FACTS, not guesses.
    - Tool call success/failure via tool_use_id ↔ tool_result matching
    - File existence via os.path.exists() at save time
    - Quantitative metrics via counting
    """
    tool_uses = [e for e in entries if e["type"] == "tool_use"]
    tool_results = [e for e in entries if e["type"] == "tool_result"]

    # 1. Tool call counts (deterministic aggregation)
    tool_counts = {}
    for tu in tool_uses:
        name = tu.get("tool_name", "unknown")
        tool_counts[name] = tool_counts.get(name, 0) + 1

    # 2. Build tool_result lookup by tool_use_id
    result_by_id = {}
    for tr in tool_results:
        tid = tr.get("tool_use_id", "")
        if not tid:
            continue
        content = tr.get("content", "")
        is_error = tr.get("is_error", False)
        # Supplementary error pattern matching (defensive — in case is_error is missing)
        # Uses module-level TOOL_ERROR_PATTERNS (DRY — shared with check_ulw_compliance)
        has_error_pattern = any(p in content for p in TOOL_ERROR_PATTERNS) if not is_error else False
        result_by_id[tid] = is_error or has_error_pattern

    # 3. Edit/Write success/failure counts (matched via tool_use_id)
    edit_success = 0
    edit_fail = 0
    write_success = 0
    write_fail = 0
    bash_success = 0
    bash_fail = 0

    for tu in tool_uses:
        tid = tu.get("tool_use_id", "")
        name = tu.get("tool_name", "")
        is_err = result_by_id.get(tid, False)

        if name == "Edit":
            if is_err:
                edit_fail += 1
            else:
                edit_success += 1
        elif name == "Write":
            if is_err:
                write_fail += 1
            else:
                write_success += 1
        elif name == "Bash":
            if is_err:
                bash_fail += 1
            else:
                bash_success += 1

    # 4. File existence verification (filesystem check at save time)
    file_verification = []
    modified_paths = []
    seen_paths = set()
    for tu in tool_uses:
        if tu.get("tool_name") in ("Edit", "Write"):
            path = tu.get("file_path", "")
            if path and path not in seen_paths:
                seen_paths.add(path)
                modified_paths.append(path)
                exists = os.path.exists(path)
                mtime = ""
                if exists:
                    try:
                        mtime = datetime.fromtimestamp(
                            os.path.getmtime(path)
                        ).strftime("%H:%M:%S")
                    except Exception:
                        pass
                file_verification.append({
                    "path": path,
                    "exists": exists,
                    "mtime": mtime,
                })

    # 5. Session timeline (deterministic timestamps)
    timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]
    first_ts = timestamps[0] if timestamps else ""
    last_ts = timestamps[-1] if timestamps else ""

    return {
        "tool_counts": tool_counts,
        "edit_success": edit_success,
        "edit_fail": edit_fail,
        "write_success": write_success,
        "write_fail": write_fail,
        "bash_success": bash_success,
        "bash_fail": bash_fail,
        "file_verification": file_verification,
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "total_tool_calls": len(tool_uses),
        "total_results": len(tool_results),
    }


# =============================================================================
# Conversation Phase Detection (C-5)
# =============================================================================

def _classify_phase(tool_uses):
    """Classify a set of tool uses into a single phase.

    P1 Compliance: Deterministic classification based on tool proportions.
    Returns: 'research', 'planning', 'implementation', 'orchestration', or 'unknown'
    """
    if not tool_uses:
        return "unknown"

    read_tools = sum(1 for t in tool_uses if t.get("tool_name") in
                     ("Read", "Grep", "Glob", "WebSearch", "WebFetch"))
    write_tools = sum(1 for t in tool_uses if t.get("tool_name") in
                      ("Edit", "Write", "Bash"))
    plan_tools = sum(1 for t in tool_uses if t.get("tool_name") in
                     ("AskUserQuestion", "EnterPlanMode", "ExitPlanMode"))
    task_tools = sum(1 for t in tool_uses if t.get("tool_name") in
                     ("Task", "TaskCreate", "TaskUpdate", "TeamCreate", "SendMessage"))

    total = len(tool_uses)

    if plan_tools > 0 and plan_tools >= write_tools:
        return "planning"
    if task_tools > total * 0.3:
        return "orchestration"
    if read_tools > total * 0.6:
        return "research"
    if write_tools > total * 0.4:
        return "implementation"
    if read_tools > write_tools:
        return "research"
    return "implementation"


def detect_conversation_phase(tool_uses):
    """Detect current conversation phase from tool usage patterns.

    P1 Compliance: Deterministic classification based on tool proportions.
    Returns: 'research', 'planning', 'implementation', 'orchestration', or 'unknown'
    """
    return _classify_phase(tool_uses)


def detect_phase_transitions(tool_uses, window_size=20):
    """B-4: Detect phase transitions within a session.

    Splits tool_uses into sliding windows and classifies each,
    identifying where the phase changed (e.g., research → implementation).

    P1 Compliance: Deterministic — window-based classification.
    Returns: list of (phase, start_index, end_index) tuples.
    """
    if not tool_uses or len(tool_uses) < window_size:
        return [(_classify_phase(tool_uses), 0, len(tool_uses))]

    phases = []
    current_phase = None
    phase_start = 0

    for i in range(0, len(tool_uses), window_size // 2):  # 50% overlap
        window = tool_uses[i:i + window_size]
        phase = _classify_phase(window)

        if phase != current_phase:
            if current_phase is not None:
                phases.append((current_phase, phase_start, i))
            current_phase = phase
            phase_start = i

    # Add final phase
    if current_phase is not None:
        phases.append((current_phase, phase_start, len(tool_uses)))

    return phases if phases else [("unknown", 0, len(tool_uses))]


# =============================================================================
# Per-File Diff Stats (C-4)
# =============================================================================

def _get_per_file_diff_stats(project_dir):
    """Get per-file line change counts from git diff --numstat.

    P1 Compliance: deterministic subprocess output.
    Returns: dict of {filepath: (added, removed)} or empty dict.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--numstat", "HEAD"],
            cwd=project_dir, capture_output=True, text=True, timeout=5
        )
        if proc.returncode != 0:
            return {}
        result = {}
        for line in proc.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                added, removed, filepath = parts[0], parts[1], parts[2]
                result[filepath] = (added, removed)
        return result
    except Exception:
        return {}

