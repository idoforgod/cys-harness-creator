#!/usr/bin/env python3
"""
Snapshot Generation Module — MD snapshot creation, compression, and indexing.

Functions:
  - generate_snapshot_md(...) → str
  - _extract_file_operations(...) → dict
  - _extract_decisions(...) → list
  - Compression functions (_compress_snapshot, etc.)
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
import time
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
# Next Step Extraction (CM-3)
# =============================================================================

def _extract_next_step(assistant_texts):
    """CM-3: Extract forward-looking statement from last assistant response.

    Captures the next action Claude was about to take, enabling task-based
    session resumption instead of summary-based guessing.

    P1 Compliance: Regex-based deterministic extraction.
    Returns: str or None (first match from last response, max 500 chars).
    """
    if not assistant_texts:
        return None

    # FIX-M4: Search last 5 assistant responses (expanded from 3) for forward-looking patterns
    # In long sessions (100+ turns), actual next-step may not be in last 3 responses
    # CM-F: Expanded from 200→500 chars to preserve structured action plans
    # Pattern: module-level _NEXT_STEP_RE (compiled once per process)
    for entry in reversed(assistant_texts[-5:]):
        content = entry.get("content", "")
        match = _NEXT_STEP_RE.search(content)
        if match:
            return match.group(0).strip()[:500]
    return None


# =============================================================================
# Decision Extraction (C-1)
# =============================================================================

def _extract_decisions(assistant_texts):
    """Extract structured design decisions from assistant responses.

    Detects:
    1. Explicit markers: <!-- DECISION: ... -->
    2. Structured patterns: **Decision:** / **결정:** / **선택:**
    3. Implicit intent patterns: "~하겠습니다", "선택 이유:", "approach:"
    4. Rationale patterns: "이유:", "근거:", "Rationale:", "because"

    P1 Compliance: Regex-based deterministic extraction.
    Returns: list of decision strings (max 20).
    """
    decisions = []
    # All patterns are module-level pre-compiled (_DECISION_*_RE constants)
    # Pattern 1: HTML comment markers (_DECISION_MARKER_RE)
    # Pattern 2: Bold markers (_DECISION_BOLD_RE)
    # Pattern 3: Implicit intent + noise filter (_DECISION_INTENT_RE, _DECISION_INTENT_NOISE_RE)
    # Pattern 4: Rationale (_DECISION_RATIONALE_RE)
    # Pattern 5-7: Comparison, trade-off, choice (_DECISION_COMPARISON_RE, _DECISION_TRADEOFF_RE, _DECISION_CHOICE_RE)

    for entry in assistant_texts:
        content = entry.get("content", "")
        for match in _DECISION_MARKER_RE.finditer(content):
            decisions.append(("[explicit] " + match.group(1).strip())[:300])
        for match in _DECISION_BOLD_RE.finditer(content):
            decisions.append(("[decision] " + match.group(1).strip())[:300])
        for match in _DECISION_INTENT_RE.finditer(content):
            matched_text = match.group(1).strip()
            # CM-2: Skip routine action declarations (noise)
            if _DECISION_INTENT_NOISE_RE.search(matched_text):
                continue
            decisions.append(("[intent] " + matched_text)[:300])
        for match in _DECISION_RATIONALE_RE.finditer(content):
            decisions.append(("[rationale] " + match.group(1).strip())[:300])
        # CM-A + E-2: New high-signal decision patterns
        for match in _DECISION_COMPARISON_RE.finditer(content):
            decisions.append(("[decision] " + match.group(0).strip())[:300])
        for match in _DECISION_TRADEOFF_RE.finditer(content):
            decisions.append(("[rationale] " + match.group(0).strip())[:300])
        for match in _DECISION_CHOICE_RE.finditer(content):
            decisions.append(("[decision] " + match.group(0).strip())[:300])

    # Dedup while preserving order
    seen = set()
    unique = []
    for d in decisions:
        if d not in seen:
            seen.add(d)
            unique.append(d)

    # CM-2 + FIX-M1: Stratified slot allocation — 20 slots total
    # High-signal: [explicit] up to 5, [decision] up to 7, [rationale] up to 5
    # Overflow: [intent] fills remaining slots (noise-reduced via filter)
    _DECISION_PRIORITY = {"[explicit]": 0, "[decision]": 1, "[rationale]": 2, "[intent]": 3}
    # B-3: Safer tag extraction — use find() on prefix only to avoid false matches
    # from ']' characters in the decision content itself
    def _get_decision_tag(d):
        if d.startswith("["):
            end = d.find("]")
            if 0 < end < 20:  # Tags are short ([explicit], [intent], etc.)
                return d[:end + 1]
        return ""
    unique.sort(key=lambda d: _DECISION_PRIORITY.get(_get_decision_tag(d), 4))

    # FIX-M1: Expanded from 15→20 slots with proportional allocation
    # High-signal slots (up to 15): [explicit] + [decision] + [rationale]
    # Overflow slots (up to 5): [intent] fills remaining capacity
    high_signal = [d for d in unique if not d.startswith("[intent]")]
    intent_only = [d for d in unique if d.startswith("[intent]")]
    high_count = min(len(high_signal), 15)
    intent_budget = 20 - high_count  # Intent gets whatever high-signal doesn't use
    result = high_signal[:high_count] + intent_only[:intent_budget]
    return result[:20]


# =============================================================================
# MD Snapshot Generation (Deterministic Data Only)
# =============================================================================

def generate_snapshot_md(session_id, trigger, project_dir, entries, work_log=None, sot_content=None):
    """Generate comprehensive MD snapshot from parsed entries.

    Design Principle (P1 + RLM):
      - Code produces ONLY deterministic, structured facts
      - NO heuristic inference (progress, decisions, pending actions)
      - Claude interprets meaning when reading the snapshot

    v3 Enhancements:
      - E7: Deterministic Completion State (hallucination prevention)
      - E2: Git state capture (ground truth, post-commit aware)
      - E3: Per-edit detail preservation (aggregation loss prevention)
      - E4: Claude response priority selection + section promotion

    Section survival priority (truncation order):
      1-10: IMMORTAL  (Header, Task, Next Step*, SOT, Autopilot*, ULW*, Team*, Decisions*, Resume, Completion State, Git)
      11-14: CRITICAL  (Modified Files, Referenced Files, User Messages, Claude Responses)
      15-17: SACRIFICABLE (Statistics, Commands, Work Log)
      (* = conditional sections, only present when active)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Classify entries
    user_messages = [e for e in entries if e["type"] == "user_message"]
    assistant_texts = [e for e in entries if e["type"] == "assistant_text"]
    tool_uses = [e for e in entries if e["type"] == "tool_use"]

    # Filtered user messages (exclude system-injected tags like <system-reminder>)
    user_msgs_filtered = [
        m for m in user_messages
        if not (m["content"].startswith("<") and ">" in m["content"][:50])
    ]

    # Pre-compute structured data (used by multiple sections)
    file_ops = _extract_file_operations(tool_uses, work_log)
    read_ops = _extract_read_operations(tool_uses)
    completion_state = extract_completion_state(entries, project_dir)
    git_state = capture_git_state(project_dir)
    conversation_phase = detect_conversation_phase(tool_uses)  # C-5
    phase_transitions = detect_phase_transitions(tool_uses)  # P1-3: multi-phase flow
    diff_stats = _get_per_file_diff_stats(project_dir)  # C-4
    decisions = _extract_decisions(assistant_texts)  # C-1

    # Build MD sections
    sections = []

    # ━━━ SURVIVAL PRIORITY 1: IMMORTAL ━━━

    # Header (P1-3: include phase flow if multi-phase detected)
    sections.append(f"# Context Recovery — Session {session_id}")
    sections.append(f"> Saved: {now} | Trigger: {trigger}")
    sections.append(f"> Project: {project_dir}")
    sections.append(f"> Total entries: {len(entries)} | User msgs: {len(user_messages)} | Tool uses: {len(tool_uses)}")
    if len(phase_transitions) > 1:
        phase_flow = " → ".join(
            f"{t[0]}({t[2]-t[1]})" for t in phase_transitions
        )
        sections.append(f"> Phase flow: {phase_flow}")
    else:
        sections.append(f"> Phase: {conversation_phase}")
    sections.append("")

    # Section 1: Current Task (first + last user message — verbatim)
    # CM-6: IMMORTAL — user messages are the ground truth for task context
    sections.append("## 현재 작업 (Current Task)")
    sections.append("<!-- IMMORTAL: 사용자 작업 지시 — 세션 복원의 핵심 맥락 -->")
    # CM-C: Filter system commands (/clear, /help, etc.) — show real task, not commands
    # Pattern: module-level _SYSTEM_CMD_RE (compiled once per process)
    real_user_msgs = [m for m in user_messages if not _SYSTEM_CMD_RE.search(m.get("content", ""))]
    if real_user_msgs:
        first_msg = real_user_msgs[0]["content"]
        sections.append(_truncate(first_msg, 3000))
        # Last instruction from filtered (non-continuation) messages
        real_filtered = [m for m in user_msgs_filtered if not _SYSTEM_CMD_RE.search(m.get("content", ""))]
        if real_filtered and len(real_filtered) > 1:
            last_msg = real_filtered[-1]["content"]
            if last_msg != first_msg:
                sections.append("")
                sections.append(f"**최근 지시 (Latest Instruction):** {_truncate(last_msg, 1500)}")
    elif user_messages:
        # Fallback: all messages are system commands, show the first one anyway
        sections.append(_truncate(user_messages[0]["content"], 3000))
    else:
        sections.append("(사용자 메시지 없음)")

    sections.append("")

    # Section 1.5: Next Step (IMMORTAL — cognitive resumption anchor)
    # CM-3: Promoted to independent IMMORTAL section for Phase 7 hard truncate survival
    next_step = _extract_next_step(assistant_texts)
    if next_step:
        sections.append("## 다음 단계 (Next Step)")
        sections.append("<!-- IMMORTAL: 세션 복원 시 인지적 연속성의 핵심 — 다음 행동 지시 -->")
        sections.append(next_step)
        sections.append("")

    # Section 2: SOT State (deterministic file read)
    sections.append("## SOT 상태 (Workflow State)")
    if sot_content:
        sections.append(f"파일: `{sot_content['path']}`")
        sections.append(f"수정 시각: {sot_content['mtime']}")
        sections.append("```yaml")
        sections.append(sot_content["content"])
        sections.append("```")
    else:
        sections.append("SOT 파일 없음 (state.yaml/state.json 미발견)")
    sections.append("")

    # Section 2.5: Autopilot State (IMMORTAL — conditional, only when active)
    try:
        ap_state = read_autopilot_state(project_dir)
        if ap_state:
            sections.append("## Autopilot 상태 (Autopilot State)")
            sections.append("<!-- IMMORTAL: 세션 복원 시 반드시 보존 -->")
            sections.append("")
            sections.append(f"- **활성화**: Yes")
            if ap_state.get("activated_at"):
                sections.append(f"- **활성화 시각**: {ap_state['activated_at']}")
            sections.append(f"- **워크플로우**: {ap_state.get('workflow_name', 'N/A')}")
            sections.append(f"- **현재 단계**: Step {ap_state.get('current_step', '?')}")
            sections.append(f"- **상태**: {ap_state.get('workflow_status', 'N/A')}")
            approved = ap_state.get("auto_approved_steps", [])
            if approved:
                sections.append(f"- **자동 승인된 단계**: {approved}")
            sections.append("")

            # SOT schema validation (P1 — structural integrity)
            schema_warnings = validate_sot_schema(ap_state)
            if schema_warnings:
                sections.append("### SOT 스키마 검증 (Schema Validation)")
                for warning in schema_warnings:
                    sections.append(f"  [WARN] {warning}")
                sections.append("")

            # Per-step output validation (Anti-Skip Guard)
            outputs = ap_state.get("outputs", {})
            if outputs:
                sections.append("### 단계별 산출물 검증 (Anti-Skip Guard)")
                for step_num in sorted(
                    int(k.replace("step-", "")) for k in outputs.keys()
                    if k.startswith("step-")
                ):
                    # FIX-R1+R3: Pass ap_state (flat dict with "outputs" key)
                    # and handle list return type from unified validate_step_output
                    is_valid, l0_warnings = validate_step_output(
                        project_dir, step_num, ap_state
                    )
                    mark = "[OK]" if is_valid else "[FAIL]"
                    reason = l0_warnings[0] if l0_warnings else f"Step {step_num}: OK"
                    sections.append(f"  {mark} {reason}")
                sections.append("")
    except Exception:
        pass  # Non-blocking — autopilot section is supplementary

    # Section 2.55: Quality Gate State (IMMORTAL — conditional, only when gate logs exist)
    # Preserves Verification/pACS/Review state for session recovery during retry/rework
    try:
        gate_lines = _extract_quality_gate_state(project_dir)
        if gate_lines:
            sections.append("## 품질 게이트 상태 (Quality Gate State)")
            sections.append(
                "<!-- IMMORTAL: 세션 복원 시 Verification/pACS/Review 재개 맥락 -->"
            )
            sections.append("")
            sections.extend(gate_lines)
            sections.append("")
    except Exception:
        pass  # Non-blocking — quality gate section is supplementary

    # Section 2.6: Active Team State (IMMORTAL — conditional, only when team active)
    try:
        team_state = read_active_team_state(project_dir)
        if team_state:
            sections.append("## Agent Team 상태 (Active Team State)")
            sections.append("<!-- IMMORTAL: 세션 복원 시 반드시 보존 — RLM Layer 2 -->")
            sections.append("")
            sections.append(f"- **팀 이름**: {team_state['name']}")
            sections.append(f"- **상태**: {team_state['status']}")
            completed = team_state.get("tasks_completed", [])
            pending = team_state.get("tasks_pending", [])
            if completed:
                sections.append(f"- **완료 Task**: {completed}")
            if pending:
                sections.append(f"- **대기 Task**: {pending}")
            sections.append("")

            # Completed summaries (RLM Layer 2 — team work summaries)
            summaries = team_state.get("completed_summaries", {})
            if summaries:
                sections.append("### Teammate 작업 요약 (RLM Layer 2)")
                for task_id, info in summaries.items():
                    if isinstance(info, dict):
                        agent = info.get("agent", "?")
                        model = info.get("model", "?")
                        output = info.get("output", "?")
                        summary = info.get("summary", "")
                        sections.append(f"- **{task_id}** ({agent}, {model}): {output}")
                        if summary:
                            sections.append(f"  - {summary}")
                sections.append("")
    except Exception:
        pass  # Non-blocking — team section is supplementary

    # Section 2.65: ULW State (IMMORTAL — conditional, only when active)
    try:
        ulw_state = detect_ulw_mode(entries)
        if ulw_state:
            sections.append("## ULW 상태 (Ultrawork Mode State)")
            sections.append("<!-- IMMORTAL: 세션 복원 시 반드시 보존 -->")
            sections.append("")
            sections.append(f"- **활성화**: Yes")
            sections.append(f"- **감지 위치**: {ulw_state['detected_in']} user message (index {ulw_state['message_index']})")
            sections.append(f"- **원본 지시**: {_truncate(ulw_state['source_message'], 500)}")

            # Show Autopilot combination state
            ap_state = read_autopilot_state(project_dir)
            if ap_state:
                sections.append(f"- **Autopilot 결합**: Yes (ULW가 Autopilot을 강화 — 재시도 한도 10→15회)")
            else:
                sections.append(f"- **Autopilot 결합**: No (대화형 + ULW)")
            sections.append("")

            sections.append("### ULW 강화 규칙 (Intensifiers)")
            sections.append("1. **I-1. Sisyphus Persistence**: 최대 3회 재시도, 각 시도는 다른 접근법. 100% 완료 또는 불가 사유 보고")
            sections.append("2. **I-2. Mandatory Task Decomposition**: TaskCreate → TaskUpdate → TaskList 필수")
            sections.append("3. **I-3. Bounded Retry Escalation**: 동일 대상 3회 초과 재시도 금지 — 초과 시 사용자 에스컬레이션")
            sections.append("")

            # ULW Compliance Guard — deterministic rule compliance check
            ulw_compliance = check_ulw_compliance(entries)
            if ulw_compliance:
                sections.append("### 준수 상태 (Compliance Guard)")
                sections.append(f"- TaskCreate: {ulw_compliance['task_creates']}회")
                sections.append(f"- TaskUpdate: {ulw_compliance['task_updates']}회")
                sections.append(f"- TaskList: {ulw_compliance['task_lists']}회")
                sections.append(f"- 총 도구 사용: {ulw_compliance['total_tool_uses']}회")
                if ulw_compliance["errors_detected"] > 0:
                    sections.append(f"- 에러 감지: {ulw_compliance['errors_detected']}건")
                    sections.append(f"- 에러 후 조치: {ulw_compliance['post_error_actions']}건")
                if ulw_compliance["max_consecutive_retries"] > 0:
                    sections.append(f"- 최대 연속 재시도: {ulw_compliance['max_consecutive_retries']}회")
                warnings = ulw_compliance.get("warnings", [])
                if warnings:
                    sections.append("")
                    sections.append("**⚠ 강화 규칙 위반 감지:**")
                    for w in warnings:
                        sections.append(f"- {w}")
                else:
                    sections.append("")
                    sections.append("✅ 모든 강화 규칙 준수")
                sections.append("")
    except Exception:
        pass  # Non-blocking — ULW section is supplementary

    # Section 2.6.5: Diagnosis State (IMMORTAL, conditional)
    try:
        diag_dir = os.path.join(project_dir, "diagnosis-logs")
        if os.path.isdir(diag_dir):
            diag_files = sorted([
                f for f in os.listdir(diag_dir) if f.endswith(".md")
            ])
            if diag_files:
                sections.append("### Diagnosis State")
                sections.append("<!-- IMMORTAL: 세션 경계에서 진단 맥락 보존 -->")
                sections.append("")
                # Show last 3 diagnosis logs
                for df in diag_files[-3:]:
                    dpath = os.path.join(diag_dir, df)
                    try:
                        with open(dpath, "r", encoding="utf-8") as f:
                            dcontent = f.read(1000)
                        sel = _DIAG_SELECTED_RE.search(dcontent)
                        gate_m = _DIAG_GATE_RE.search(dcontent)
                        sections.append(
                            f"- `{df}`: gate={gate_m.group(1) if gate_m else '?'}, "
                            f"hypothesis={sel.group(1).strip() if sel else '?'}"
                        )
                    except Exception:
                        sections.append(f"- `{df}`: (parse error)")
                sections.append("")
    except Exception:
        pass  # Non-blocking — diagnosis section is supplementary

    # Section 2.7: Design Decisions (C-1 — IMMORTAL, conditional)
    if decisions:
        sections.append(f"{E5_DESIGN_DECISIONS_MARKER} (Design Decisions)")
        sections.append("<!-- IMMORTAL: 세션 복원 시 '왜' 그 결정을 했는지 보존 -->")
        sections.append("")
        for i, dec in enumerate(decisions, 1):
            sections.append(f"{i}. {dec}")
        sections.append("")

    # Section 3: Resume Protocol (deterministic — P1 compliant)
    sections.append("## 복원 지시 (Resume Protocol)")
    sections.append("<!-- Python 결정론적 생성 — P1 준수 -->")
    sections.append("")
    if file_ops:
        sections.append(E5_RICH_CONTENT_MARKER)
        for op in file_ops:
            # C-4: per-file change summary from git diff
            diff_suffix = ""
            if diff_stats:
                # Match by basename or relative path
                rel_path = os.path.relpath(op['path'], project_dir) if os.path.isabs(op['path']) else op['path']
                stats = diff_stats.get(rel_path)
                if not stats:
                    # Try 2-level suffix match (dir/file) to reduce false matches
                    parent = os.path.basename(os.path.dirname(op['path']))
                    basename = os.path.basename(op['path'])
                    suffix_2 = os.path.join(parent, basename) if parent else basename
                    for dp, ds in diff_stats.items():
                        if dp.endswith(suffix_2):
                            stats = ds
                            break
                    # Final fallback: basename-only (accept ambiguity)
                    if not stats:
                        for dp, ds in diff_stats.items():
                            if dp.endswith(basename):
                                stats = ds
                                break
                if stats:
                    diff_suffix = f" (+{stats[0]}/-{stats[1]})"
            sections.append(f"- `{op['path']}` ({op['tool']}, {op['summary']}){diff_suffix}")
    if read_ops:
        sections.append("### 참조하던 파일")
        for op in read_ops[:10]:
            sections.append(f"- `{op['path']}` (Read, {op['count']}회)")
    transcript_size = _get_file_size(entries)
    estimated_tokens = int(transcript_size / CHARS_PER_TOKEN)
    last_tool = ""
    if tool_uses:
        last_tu = tool_uses[-1]
        last_tool_name = last_tu.get("tool_name", "")
        last_tool_path = last_tu.get("file_path", "")
        last_tool = last_tool_name
        if last_tool_path:
            last_tool += f" → {last_tool_path}"
    sections.append("### 세션 정보")
    sections.append(f"- 종료 트리거: {trigger}")
    sections.append(f"- 추정 토큰: ~{estimated_tokens:,}")
    if last_tool:
        sections.append(f"- 마지막 도구: {last_tool}")
    sections.append("")

    # Section 4: Deterministic Completion State (E7 — hallucination prevention)
    sections.append(f"{E5_COMPLETION_STATE_MARKER} (Deterministic Completion State)")
    sections.append("<!-- Python 결정론적 생성 — Claude 해석 불필요, 직접 참조 -->")
    sections.append("")
    cs = completion_state
    sections.append("### 도구 호출 결과")
    # Show major tools with success/failure for Edit/Write/Bash
    for tk in ["Edit", "Write", "Bash", "Read", "Task", "Grep", "Glob"]:
        count = cs["tool_counts"].get(tk, 0)
        if count > 0:
            if tk == "Edit":
                sections.append(
                    f"- Edit: {count}회 호출 → {cs['edit_success']} 성공, {cs['edit_fail']} 실패"
                )
            elif tk == "Write":
                sections.append(
                    f"- Write: {count}회 호출 → {cs['write_success']} 성공, {cs['write_fail']} 실패"
                )
            elif tk == "Bash":
                sections.append(
                    f"- Bash: {count}회 호출 → {cs['bash_success']} 성공, {cs['bash_fail']} 실패"
                )
            else:
                sections.append(f"- {tk}: {count}회 호출")
    # Other tools not in the main list
    other_tools = {
        k: v for k, v in cs["tool_counts"].items()
        if k not in ("Edit", "Write", "Bash", "Read", "Task", "Grep", "Glob")
    }
    for name, count in sorted(other_tools.items()):
        sections.append(f"- {name}: {count}회 호출")
    sections.append("")

    if cs["file_verification"]:
        sections.append("### 파일 상태 검증 (저장 시점)")
        sections.append("| 파일 | 존재 | 최종수정 |")
        sections.append("|------|------|---------|")
        for fv in cs["file_verification"]:
            exists_mark = "✓" if fv["exists"] else "✗"
            short_path = os.path.basename(fv["path"])
            sections.append(f"| `{short_path}` | {exists_mark} | {fv['mtime']} |")
        sections.append("")

    if cs["first_timestamp"] or cs["last_timestamp"]:
        sections.append("### 세션 타임라인")
        if cs["first_timestamp"]:
            sections.append(f"- 시작: {cs['first_timestamp']}")
        if cs["last_timestamp"]:
            sections.append(f"- 종료: {cs['last_timestamp']}")
        sections.append("")

    # A6: 최근 도구 호출 시간순 기록 — 에러-복구 패턴 보존
    recent_tools = [
        e for e in entries
        if e.get("type") == "tool_use" and e.get("tool_name")
    ][-10:]  # 마지막 10개
    if recent_tools:
        # Pre-build error lookup: O(n) once instead of O(10n) nested scan
        result_errors = {}
        for e2 in entries:
            if e2.get("type") == "tool_result":
                tid = e2.get("tool_use_id", "")
                if tid and e2.get("is_error"):
                    result_errors[tid] = True
        sections.append("### 최근 도구 활동 (시간순)")
        for rt in recent_tools:
            tool = rt.get("tool_name", "?")
            fp = rt.get("file_path", "")
            ts = rt.get("timestamp", "")[-8:]  # HH:MM:SS
            short_fp = os.path.basename(fp) if fp else ""
            tu_id = rt.get("tool_use_id", "")
            result_tag = " ← ERROR" if result_errors.get(tu_id) else ""
            suffix = f" → `{short_fp}`" if short_fp else ""
            sections.append(f"- [{ts}] {tool}{suffix}{result_tag}")
        sections.append("")

    # Section 5: Git Changes (E2 — ground truth, post-commit aware)
    if any(git_state.values()):
        sections.append("## Git 변경 상태 (Git Changes)")
        if git_state["status"]:
            sections.append("### Working Tree")
            sections.append(f"```\n{git_state['status']}\n```")
        elif not git_state["diff_stat"]:
            sections.append("### Working Tree")
            sections.append("```\nclean (변경 없음)\n```")
        if git_state["diff_stat"]:
            sections.append("### Uncommitted Changes")
            sections.append(f"```\n{git_state['diff_stat']}\n```")
        if git_state["diff_content"]:
            sections.append("### Diff Detail")
            sections.append(f"```diff\n{git_state['diff_content']}\n```")
        if git_state["recent_commits"]:
            sections.append("### Recent Commits")
            sections.append(f"```\n{git_state['recent_commits']}\n```")
        sections.append("")

    # ━━━ SURVIVAL PRIORITY 2: CRITICAL ━━━

    # Section 6: Modified Files with per-edit details (E3)
    sections.append("## 수정된 파일 (Modified Files)")
    if file_ops:
        for op in file_ops:
            sections.append(f"### `{op['path']}` ({op['tool']}, {op['summary']})")
            if op.get("details"):
                for j, detail in enumerate(op["details"], 1):
                    sections.append(f"  {j}. {_truncate(detail, 200)}")
            sections.append("")
    else:
        sections.append("(파일 수정 기록 없음)")
    sections.append("")

    # Section 7: Referenced Files
    sections.append("## 참조된 파일 (Referenced Files)")
    if read_ops:
        sections.append("| 파일 경로 | 횟수 |")
        sections.append("|----------|------|")
        for op in read_ops[:20]:
            sections.append(f"| `{op['path']}` | {op['count']} |")
    else:
        sections.append("(파일 참조 기록 없음)")
    sections.append("")

    # Section 8: User Messages (verbatim — last N)
    sections.append("## 사용자 요청 이력 (User Messages)")
    if user_msgs_filtered:
        for i, msg in enumerate(user_msgs_filtered[-12:], 1):
            sections.append(f"{i}. {_truncate(msg['content'], 800)}")
    else:
        sections.append("(사용자 메시지 없음)")
    sections.append("")

    # Section 9: Claude Key Responses (E4 — priority selection, promoted)
    sections.append("## Claude 핵심 응답 (Key Responses)")
    meaningful_texts = [
        t for t in assistant_texts
        if len(t["content"]) > 100
    ]
    if meaningful_texts:
        # Priority markers for structured progress reports
        PRIORITY_MARKERS = [
            "Done", "완료", "PASS", "FAIL", "TODO",
            "남은", "진행", "요약", "검증", "수정 완료",
            "## ", "| ", "```",
        ]

        def _priority_score(t):
            content = t["content"]
            score = sum(1 for m in PRIORITY_MARKERS if m in content)
            if len(content) > 500:
                score += 1
            if len(content) > 1000:
                score += 1
            return score

        # Last 3 responses always preserved (most recent context)
        last_3 = meaningful_texts[-3:]
        last_3_ids = set(id(t) for t in last_3)
        # From remaining, select top 5 by priority score
        remaining = [
            t for t in meaningful_texts
            if id(t) not in last_3_ids
        ]
        remaining.sort(key=_priority_score, reverse=True)
        top_priority = remaining[:5]
        # Merge and output in original chronological order
        selected_ids = set(id(t) for t in last_3 + top_priority)
        selected_responses = [t for t in meaningful_texts if id(t) in selected_ids]
        for i, txt in enumerate(selected_responses, 1):
            content = txt["content"]
            if len(content) > 2500:
                # A5: Structure-preserving compression — keep header + conclusion
                # Split: first 1200 chars (intro/structure) + last 1000 chars (conclusion)
                head = content[:1200]
                tail = content[-1000:]
                omitted = len(content) - 2200
                sections.append(f"{i}. {head}\n  [...{omitted}자 생략...]\n  {tail}")
            else:
                sections.append(f"{i}. {content}")
    else:
        sections.append("(Claude 응답 없음)")
    sections.append("")

    # ━━━ SURVIVAL PRIORITY 3: SACRIFICABLE ━━━

    # Section 10: Statistics
    sections.append("## 대화 통계")
    sections.append(f"- 총 메시지: {len(user_msgs_filtered) + len(assistant_texts)}개")
    sections.append(f"- 도구 사용: {len(tool_uses)}회")
    sections.append(f"- 추정 토큰: ~{estimated_tokens:,}")
    sections.append(f"- 저장 트리거: {trigger}")
    if user_msgs_filtered:
        last_msg = _truncate(user_msgs_filtered[-1]["content"], 200)
        sections.append(f"- 마지막 사용자 메시지: \"{last_msg}\"")
    sections.append("")

    # Section 11: Commands Executed
    sections.append("## 실행된 명령 (Commands Executed)")
    bash_ops = [t for t in tool_uses if t.get("tool_name") == "Bash"]
    if bash_ops:
        for op in bash_ops[-20:]:
            cmd = _truncate(op.get("command", ""), 150)
            desc = op.get("description", "")
            if cmd:
                sections.append(f"- `{cmd}`" + (f" ({desc})" if desc else ""))
            else:
                sections.append(f"- {op['content']}")
    else:
        sections.append("(명령 실행 기록 없음)")
    sections.append("")

    # Section 12: Work Log Summary
    if work_log:
        sections.append("## 작업 로그 요약 (Work Log Summary)")
        sections.append(f"총 기록: {len(work_log)}개")
        for entry in work_log[-25:]:
            ts = entry.get("timestamp", "")
            tool = entry.get("tool_name", "")
            summary = entry.get("summary", "")
            sections.append(f"- [{ts}] {tool}: {summary}")
        sections.append("")

    # Combine and enforce size limit
    full_md = "\n".join(sections)

    if len(full_md) > MAX_SNAPSHOT_CHARS:
        full_md = _compress_snapshot(full_md, sections)

    return full_md

