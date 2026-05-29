#!/usr/bin/env python3
"""
File Operations Module — File I/O, token estimation, cleanup, atomic writes.

Functions:
  - estimate_tokens(transcript_path) → int
  - atomic_write(filepath, content)
  - append_with_lock(filepath, content)
  - load_work_log(snapshot_dir) → dict
  - should_skip_save(snapshot_dir) → bool
  - cleanup_snapshots(snapshot_dir)
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

import fcntl
import tempfile
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
# Deterministic File Operation Extraction
# =============================================================================

def _extract_file_operations(tool_uses, work_log=None):
    """Extract file modification records using structured metadata.

    Uses entry['file_path'] (set by _parse_assistant_entry) instead of
    parsing summary strings. This is 100% deterministic.

    E3 Enhancement: Preserves per-edit details (not just aggregated summary).
    Each edit's OLD→NEW context is stored in 'details' list, preventing
    information loss from aggregation.
    """
    # Track operations per path (preserve insertion order)
    path_order = []
    ops_by_path = {}

    for tu in tool_uses:
        tool_name = tu.get("tool_name", "")

        if tool_name in ("Write", "Edit"):
            # Use structured metadata — NOT string parsing
            path = tu.get("file_path", "")
            if not path:
                continue

            if path not in ops_by_path:
                path_order.append(path)
                ops_by_path[path] = {
                    "count": 0, "last_tool": "", "last_summary": "",
                    "details": [],  # E3: per-edit detail preservation
                }

            record = ops_by_path[path]
            record["count"] += 1
            record["last_tool"] = tool_name

            if tool_name == "Write":
                line_count = tu.get("line_count", 0)
                record["last_summary"] = f"Write ({line_count} lines)"
                record["details"].append(f"Write ({line_count} lines)")
            else:
                record["last_summary"] = "Edit"
                # Extract OLD→NEW detail from content (set by _extract_tool_use_summary)
                content = tu.get("content", "Edit")
                lines = content.split("\n")
                detail_parts = []
                for line in lines[1:3]:  # OLD/NEW lines
                    stripped = line.strip()
                    if stripped:
                        detail_parts.append(stripped)
                detail_str = " | ".join(detail_parts) if detail_parts else "Edit"
                record["details"].append(detail_str)

    # Build result list in insertion order
    ops = []
    for path in path_order:
        record = ops_by_path[path]
        if record["count"] > 1:
            summary = f"{record['last_summary']}, {record['count']}회 수정"
        else:
            summary = record["last_summary"]
        ops.append({
            "path": path,
            "tool": record["last_tool"],
            "summary": summary,
            "details": record["details"],  # E3: per-edit details
        })

    # Supplement from work log (already structured)
    if work_log:
        for entry in work_log:
            path = entry.get("file_path", "")
            if path and path not in ops_by_path:
                ops_by_path[path] = True  # Mark as seen
                ops.append({
                    "path": path,
                    "tool": entry.get("tool_name", ""),
                    "summary": _truncate(entry.get("summary", ""), 100),
                    "details": [],
                })

    return ops


def _extract_read_operations(tool_uses):
    """Extract Read operations with frequency count.

    Deterministic extraction from tool_use entries.
    Tracks which files Claude was consulting during the session.
    Used for Resume Protocol and Knowledge Archive.
    """
    read_counts = {}
    for tu in tool_uses:
        if tu.get("tool_name") == "Read":
            path = tu.get("file_path", "")
            if path:
                read_counts[path] = read_counts.get(path, 0) + 1

    # Sort by frequency (most read first), then alphabetically
    return sorted(
        [{"path": p, "count": c} for p, c in read_counts.items()],
        key=lambda x: (-x["count"], x["path"]),
    )


# =============================================================================
# Token Estimation (Multi-signal)
# =============================================================================

def estimate_tokens(transcript_path, entries=None):
    """
    Multi-signal token estimation.
    Returns (estimated_tokens, signals_dict)
    """
    signals = {}

    # Signal 1: File size
    file_size = 0
    if transcript_path and os.path.exists(transcript_path):
        file_size = os.path.getsize(transcript_path)
    signals["file_size_bytes"] = file_size
    tokens_from_size = int(file_size / CHARS_PER_TOKEN)

    # Signal 2: Message count (if entries available)
    if entries:
        user_count = sum(1 for e in entries if e["type"] == "user_message")
        assistant_count = sum(1 for e in entries if e["type"] == "assistant_text")
        tool_count = sum(1 for e in entries if e["type"] == "tool_use")
        signals["user_messages"] = user_count
        signals["assistant_messages"] = assistant_count
        signals["tool_uses"] = tool_count

        # Heuristic: each substantial exchange ≈ 3-5K tokens
        tokens_from_messages = (user_count + assistant_count) * 2000 + tool_count * 1500
    else:
        tokens_from_messages = tokens_from_size

    # Signal 3: Content character count
    if entries:
        total_chars = sum(len(e.get("content", "")) for e in entries)
        signals["total_content_chars"] = total_chars
        tokens_from_chars = int(total_chars / CHARS_PER_TOKEN)
    else:
        tokens_from_chars = tokens_from_size

    # Weighted average (file size is most reliable)
    estimated = int(
        tokens_from_size * 0.5 +
        tokens_from_messages * 0.25 +
        tokens_from_chars * 0.25
    )

    # Add system overhead
    estimated += SYSTEM_OVERHEAD_TOKENS

    signals["estimated_tokens"] = estimated
    signals["threshold_75"] = THRESHOLD_75_TOKENS
    signals["over_threshold"] = estimated > THRESHOLD_75_TOKENS

    return estimated, signals


# =============================================================================
# File Operations (Atomic + Locking)
# =============================================================================

def atomic_write(filepath, content):
    """Write content atomically: temp file → rename."""
    dirpath = os.path.dirname(filepath)
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.rename(tmp_path, filepath)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def append_with_lock(filepath, content):
    """Append content with file locking (fcntl.flock)."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "a", encoding="utf-8") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(content)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_work_log(snapshot_dir):
    """Load work log entries from JSONL."""
    log_path = os.path.join(snapshot_dir, "work_log.jsonl")
    entries = []
    if not os.path.exists(log_path):
        return entries

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    return entries


# =============================================================================
# Dedup Guard
# =============================================================================

def should_skip_save(snapshot_dir, trigger=None):
    """Check if a save was done within dedup window.

    SessionEnd is exempt: /clear is an explicit user action,
    so the save must always happen regardless of dedup window.
    Stop hook uses wider window (30s) to reduce noise.
    """
    if trigger in ("sessionend",):
        return False
    latest_path = os.path.join(snapshot_dir, "latest.md")
    if os.path.exists(latest_path):
        age = time.time() - os.path.getmtime(latest_path)
        # Stop hook uses wider window (30s) to reduce noise
        window = STOP_DEDUP_WINDOW_SECONDS if trigger == "stop" else DEDUP_WINDOW_SECONDS
        if age < window:
            return True
    return False


# =============================================================================
# Snapshot Cleanup
# =============================================================================

def cleanup_snapshots(snapshot_dir):
    """Remove old snapshots, keeping recent ones per trigger type."""
    try:
        files = []
        for f in os.listdir(snapshot_dir):
            if f.endswith(".md") and f != "latest.md":
                fpath = os.path.join(snapshot_dir, f)
                files.append((f, os.path.getmtime(fpath)))

        # Group by trigger type (last part of filename before .md)
        groups = {}
        for fname, mtime in files:
            # Format: YYYYMMDD_HHMMSS_trigger.md
            parts = fname.replace(".md", "").split("_")
            trigger = parts[-1] if len(parts) >= 3 else "unknown"
            if trigger not in groups:
                groups[trigger] = []
            groups[trigger].append((fname, mtime))

        # Keep only MAX per group (sorted by mtime, newest first)
        for trigger, group_files in groups.items():
            max_keep = MAX_SNAPSHOTS.get(trigger, DEFAULT_MAX_SNAPSHOTS)
            group_files.sort(key=lambda x: x[1], reverse=True)
            for fname, _ in group_files[max_keep:]:
                try:
                    os.unlink(os.path.join(snapshot_dir, fname))
                except OSError:
                    pass
    except Exception:
        pass


# =============================================================================
# Utility Helpers
# =============================================================================

def _truncate(text, max_len):
    """Truncate text to max_len, adding ellipsis if needed."""
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _get_file_size(entries):
    """Estimate total character size from entries."""
    total = 0
    for e in entries:
        total += len(e.get("content", ""))
    return total


def _append_compression_audit(content, audit):
    """A5: Append compression audit trail as HTML comment.

    P1 Compliance: Deterministic metadata only.
    Format: single-line HTML comment (invisible in rendered MD, greppable).
    """
    if not audit:
        return content
    final_size = len(content)
    trail = " ".join(audit)
    return content + f"\n<!-- compression-audit: {trail} | final:{final_size}ch/{MAX_SNAPSHOT_CHARS}ch -->"


def _compress_snapshot(full_md, sections):
    """Quality-focused compression (절대 기준 1: 품질 우선).

    Compression priority (sacrifice order — last resort first):
      Phase 1: Deduplicate redundant entries
      Phase 2: Reduce commands section (SACRIFICABLE)
      Phase 3: Reduce work log (SACRIFICABLE)
      Phase 4: Reduce statistics section (SACRIFICABLE)
      Phase 5: Compress Git diff detail (keep stat + commits, drop full diff)
      Phase 6: Compress Claude responses (keep conclusions)
      Phase 7: Hard truncate only as absolute last resort

    Always preserved (IMMORTAL):
      Header, Current Task, Next Step*, SOT, Autopilot State*, ULW State*,
      Team State*, Design Decisions*, Resume Protocol,
      Deterministic Completion State, Git Changes (stat+commits)
      (* = conditional sections, only present when active)

    High priority (CRITICAL):
      Modified Files, Referenced Files, User Messages, Claude Responses
    """
    # A5: Compression audit trail
    audit = []
    original_size = sum(len(s) + 1 for s in sections)  # +1 for \n

    # Phase 1: Deduplicate — remove consecutive identical entries
    deduped_sections = _dedup_sections(sections)
    result = "\n".join(deduped_sections)
    p1_removed = original_size - len(result)
    if p1_removed > 0:
        audit.append(f"P1-dedup:-{p1_removed}ch")
    if len(result) <= MAX_SNAPSHOT_CHARS:
        return _append_compression_audit(result, audit)

    # Phase 2: Compress commands (keep first 3 + last 5)
    prev_size = len(result)
    compressed = _compress_section_entries(
        deduped_sections, "## 실행된 명령", keep_first=3, keep_last=5
    )
    result = "\n".join(compressed)
    p2_removed = prev_size - len(result)
    if p2_removed > 0:
        audit.append(f"P2-cmds:-{p2_removed}ch")
    if len(result) <= MAX_SNAPSHOT_CHARS:
        return _append_compression_audit(result, audit)

    # Phase 3: Compress work log (keep last 10)
    prev_size = len(result)
    compressed = _compress_section_entries(
        compressed, "## 작업 로그 요약", keep_first=0, keep_last=10
    )
    result = "\n".join(compressed)
    p3_removed = prev_size - len(result)
    if p3_removed > 0:
        audit.append(f"P3-wlog:-{p3_removed}ch")
    if len(result) <= MAX_SNAPSHOT_CHARS:
        return _append_compression_audit(result, audit)

    # Phase 4: Remove statistics section entirely (regeneratable)
    prev_size = len(result)
    compressed = _remove_section(compressed, "## 대화 통계")
    result = "\n".join(compressed)
    p4_removed = prev_size - len(result)
    if p4_removed > 0:
        audit.append(f"P4-stats:-{p4_removed}ch")
    if len(result) <= MAX_SNAPSHOT_CHARS:
        return _append_compression_audit(result, audit)

    # Phase 5: Compress Git diff detail (keep stat + commits, drop full diff)
    prev_size = len(result)
    compressed = _remove_section(compressed, "### Diff Detail")
    result = "\n".join(compressed)
    p5_removed = prev_size - len(result)
    if p5_removed > 0:
        audit.append(f"P5-diff:-{p5_removed}ch")
    if len(result) <= MAX_SNAPSHOT_CHARS:
        return _append_compression_audit(result, audit)

    # Phase 6: Compress Claude responses (preserve conclusion — last 300 chars)
    prev_size = len(result)
    compressed = _compress_responses(compressed)
    result = "\n".join(compressed)
    p6_removed = prev_size - len(result)
    if p6_removed > 0:
        audit.append(f"P6-resp:-{p6_removed}ch")
    if len(result) <= MAX_SNAPSHOT_CHARS:
        return _append_compression_audit(result, audit)

    # Phase 7: IMMORTAL-aware hard truncate (absolute last resort)
    # CM-E: Preserve IMMORTAL sections, truncate non-IMMORTAL from bottom up
    # FIX-C1: Marker-first boundary detection — each IMMORTAL marker re-enters
    # IMMORTAL mode even after a non-IMMORTAL section interrupted.
    # Old bug: single flag flipped to False on non-IMMORTAL "## " header,
    # then subsequent IMMORTAL sections were misclassified as non-IMMORTAL.
    immortal_lines = []
    other_lines = []
    in_immortal_section = False
    for line in compressed:
        # IMMORTAL marker always (re-)enters IMMORTAL mode
        if "<!-- IMMORTAL:" in line:
            in_immortal_section = True
        # Non-IMMORTAL section header exits IMMORTAL mode
        # Must check AFTER marker check so marker on same line wins
        elif line.startswith("## ") and "IMMORTAL" not in line:
            in_immortal_section = False
        if in_immortal_section or line.startswith("# Context Recovery"):
            immortal_lines.append(line)
        else:
            other_lines.append(line)

    immortal_text = "\n".join(immortal_lines)
    other_text = "\n".join(other_lines)
    audit.append(f"P7-truncate:immortal={len(immortal_text)}ch,other={len(other_text)}ch")
    budget = MAX_SNAPSHOT_CHARS - len(immortal_text) - 100
    if budget > 0:
        truncated = immortal_text + "\n" + other_text[:budget] + \
            "\n\n(... 크기 초과로 잘림 — 전체 내역은 sessions/ 아카이브 참조)"
        return _append_compression_audit(truncated, audit)
    # Even IMMORTAL exceeds limit — truncate IMMORTAL itself (preserving start)
    # Reflection fix: Use immortal_text, not Phase 6 result, to avoid
    # cutting mixed content that defeats IMMORTAL-first purpose
    # FIX-C1: Add truncation notice so restored session knows context was cut
    truncation_notice = (
        "\n\n<!-- IMMORTAL: 압축 알림 — 세션 복원 시 핵심 맥락 -->\n"
        "## ⚠ 스냅샷 압축 알림\n"
        "이 스냅샷은 Phase 7 hard truncate를 거쳤습니다. "
        "일부 비-IMMORTAL 섹션(수정 파일 목록, 작업 로그, Claude 응답 등)이 "
        "제거되었을 수 있습니다. 전체 내역은 `sessions/` 아카이브를 참조하세요.\n"
    )
    truncated = immortal_text[:MAX_SNAPSHOT_CHARS - len(truncation_notice) - 100] + \
        truncation_notice
    return _append_compression_audit(truncated, audit)


def _dedup_sections(sections):
    """Remove consecutive duplicate entries within list-style sections."""
    result = []
    prev_line = None
    for line in sections:
        # Skip consecutive identical list items
        if line.startswith("- ") and line == prev_line:
            continue
        result.append(line)
        prev_line = line
    return result


def _compress_section_entries(sections, section_header, keep_first=0, keep_last=5):
    """Compress a specific section's list entries, keeping first N + last N."""
    result = []
    in_section = False
    section_entries = []

    for line in sections:
        if section_header in line:
            in_section = True
            result.append(line)
            continue
        if in_section and line.startswith("##"):
            # End of section — emit compressed entries
            _emit_compressed_entries(result, section_entries, keep_first, keep_last)
            section_entries = []
            in_section = False
            result.append(line)
            continue
        if in_section and line.startswith("- "):
            section_entries.append(line)
            continue
        if in_section and not line.strip():
            section_entries.append(line)
            continue
        if in_section:
            # Non-list content in section (e.g., "총 기록: N개")
            result.append(line)
            continue
        result.append(line)

    # If section was the last one
    if section_entries:
        _emit_compressed_entries(result, section_entries, keep_first, keep_last)

    return result


def _emit_compressed_entries(result, entries, keep_first, keep_last):
    """Emit first N + last N entries with omission marker."""
    # Filter out blank lines for counting
    items = [e for e in entries if e.strip()]
    blanks_after = [e for e in entries if not e.strip()]

    total = len(items)
    if total <= keep_first + keep_last:
        result.extend(entries)
        return

    if keep_first > 0:
        result.extend(items[:keep_first])
    omitted = total - keep_first - keep_last
    result.append(f"  (...{omitted}개 항목 생략...)")
    result.extend(items[-keep_last:])
    if blanks_after:
        result.append("")


def _remove_section(sections, section_header):
    """Remove an entire section (header to next ## header) from sections list."""
    result = []
    in_section = False
    for line in sections:
        if section_header in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            in_section = False
            result.append(line)
            continue
        # When removing a ### subsection, stop at the next sibling ### header
        if in_section and section_header.startswith("### ") and line.startswith("### ") and section_header not in line:
            in_section = False
            result.append(line)
            continue
        if in_section and line.startswith("### ") and not section_header.startswith("### "):
            # Sub-section within removed ## section — also remove
            continue
        if not in_section:
            result.append(line)
    return result


def _compress_responses(sections):
    """Compress Claude responses: structure-aware compression (C-7).

    Preserves structural markers (headers, lists, code blocks, tables)
    while dropping verbose prose. More generous limits for structured content.
    """
    result = []
    in_section = False

    for line in sections:
        if "## Claude 핵심 응답" in line:
            in_section = True
            result.append(line)
            continue
        if in_section and line.startswith("##"):
            in_section = False
            result.append(line)
            continue
        if in_section and line and line[0].isdigit() and ". " in line[:5]:
            # Numbered response — structure-aware compression
            if len(line) > 500:
                result.append(_structure_aware_compress_line(line))
            else:
                result.append(line)
            continue
        result.append(line)

    return result


def _structure_aware_compress_line(text, max_prefix=120, max_conclusion=400):
    """Compress a single long text line, preserving structural markers (C-7).

    Structure-rich content (headers, lists, tables) gets more generous limits.
    """
    structural_markers = ("## ", "### ", "- ", "* ", "| ", "```", "1. ", "2. ")
    has_structure = any(m in text for m in structural_markers)

    if has_structure:
        # Structured content: keep more context
        prefix = text[:max_prefix]
        conclusion = text[-max_conclusion:]
        return f"{prefix} (...구조 보존...) {conclusion}"
    else:
        # Plain prose: standard compression
        prefix = text[:80]
        conclusion = text[-300:]
        return f"{prefix} (...) {conclusion}"


def get_snapshot_dir(project_dir=None):
    """Get the context-snapshots directory path."""
    if not project_dir:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return os.path.join(project_dir, ".claude", "context-snapshots")


def read_stdin_json():
    """Read and parse JSON from stdin (hook input)."""
    try:
        raw = sys.stdin.read()
        if raw.strip():
            return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        pass
    return {}


# =============================================================================
# E5 Guard Helper (A1: Multi-Signal Rich Content Detection)
# =============================================================================

def is_rich_snapshot(content):
    """Multi-signal rich content detection for E5 Empty Snapshot Guard.

    P1 Compliance: Deterministic — size threshold + marker counting.
    Returns True if snapshot is "rich" (should not be overwritten by empty one).

    Signals (any 2 of the following):
      1. Content length >= 3KB (aligned with E6 MIN_QUALITY_SIZE)
      2-4. Presence of E5_RICH_SIGNALS markers
    """
    if not content:
        return False

    signal_count = 0

    # Signal 1: Size threshold (aligned with E6 MIN_QUALITY_SIZE = 3000)
    if len(content.encode("utf-8")) >= 3000:
        signal_count += 1

    # Signals 2-4: Section markers
    for marker in E5_RICH_SIGNALS:
        if marker in content:
            signal_count += 1

    return signal_count >= 2


# =============================================================================
# E5 Guard + Knowledge Archive — Consolidated Helpers
# =============================================================================

def update_latest_with_guard(snapshot_dir, md_content, entries):
    """Atomically update latest.md with E5 Empty Snapshot Guard.

    Returns True if latest.md was updated, False if existing rich snapshot
    was protected from overwrite by an empty one.

    P1 Compliance: Deterministic (tool_use count + is_rich_snapshot).
    SOT Compliance: No SOT access.
    """
    latest_path = os.path.join(snapshot_dir, "latest.md")
    new_tool_count = sum(1 for e in entries if e.get("type") == "tool_use")

    if os.path.exists(latest_path) and new_tool_count == 0:
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            if is_rich_snapshot(existing_content):
                return False
        except Exception:
            pass

    atomic_write(latest_path, md_content)
    return True


def archive_and_index_session(
    snapshot_dir, md_content, session_id, trigger,
    project_dir, entries, transcript_path,
):
    """Archive snapshot + extract knowledge-index facts + cleanup.

    Consolidates the 3-step archive pattern used by all save triggers:
      1. Archive snapshot to sessions/ directory
      2. Extract session facts → knowledge-index.jsonl
      3. Rotate archives and index

    P1 Compliance: All operations deterministic.
    SOT Compliance: Read-only SOT access (via extract_session_facts).
    Timestamp format: ISO-like %Y-%m-%dT%H%M%S (unified across all triggers).
    """
    # Step 1: Archive to sessions/ (isolated — failure does NOT block Step 2)
    # RLM rationale: archive is backup; knowledge-index is the RLM-critical asset.
    # If sessions/ mkdir or write fails, Step 2 must still record the session.
    try:
        sessions_dir = os.path.join(snapshot_dir, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        archive_name = f"{ts}_{session_id[:8]}.md"
        archive_path = os.path.join(sessions_dir, archive_name)
        atomic_write(archive_path, md_content)
    except Exception:
        pass  # Non-blocking — Step 2 (RLM-critical) proceeds independently

    # Step 2: Extract session facts → knowledge-index.jsonl (RLM-critical)
    try:
        estimated_tokens, _ = estimate_tokens(transcript_path, entries)
        facts = extract_session_facts(
            session_id=session_id,
            trigger=trigger,
            project_dir=project_dir,
            entries=entries,
            token_estimate=estimated_tokens,
        )
        ki_path = os.path.join(snapshot_dir, "knowledge-index.jsonl")
        replace_or_append_session_facts(ki_path, facts)
    except Exception:
        pass  # Non-blocking

    # Step 3: Rotate archives and index (each cleanup is internally protected)
    cleanup_session_archives(snapshot_dir)
    cleanup_knowledge_index(snapshot_dir)


# =============================================================================
# Path Tag Extraction (A3: Language-Independent Search Tags)
# =============================================================================

def extract_path_tags(file_paths):
    """Extract language-independent search tags from file paths.

    P1 Compliance: Deterministic string processing only.
    Returns: sorted unique list of tag strings (max 20).

    Tag sources:
      - CamelCase splitting: "AuthService.py" → ["auth", "service"]
      - snake_case splitting: "user_auth.py" → ["user", "auth"]
      - Extension mapping: ".py" → "python"
    """
    tags = set()
    for fp in file_paths:
        if not fp:
            continue
        parts = Path(fp).parts
        for part in parts:
            name = Path(part).stem  # filename without extension
            if name.startswith(".") or name in _PATH_SKIP_NAMES:
                continue
            # CamelCase splitting: "AuthService" → ["Auth", "Service"]
            # Also handles: "getHTTPResponse" → ["get", "HTTP", "Response"]
            subtokens = re.findall(r'[A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z]|$)', name)
            for st in subtokens:
                lower = st.lower()
                if len(lower) >= 3:  # skip noise ("a", "db", "io")
                    tags.add(lower)
        # Extension tag
        ext = os.path.splitext(fp)[1].lower()
        if ext in _EXT_TAGS:
            tags.add(_EXT_TAGS[ext])
    return sorted(tags)[:20]


# =============================================================================
# Knowledge-Index Schema Validation (P1: Hallucination Prevention)
# =============================================================================

# RLM-critical keys that MUST exist in every knowledge-index entry.
# If extract_session_facts() is modified and accidentally drops a key,
# this validation fills safe defaults — writing incomplete data is better
# than writing nothing (RLM visibility > field completeness).
_KI_REQUIRED_DEFAULTS = {
    "session_id": "",
    "timestamp": "",
    "user_task": "",
    "modified_files": [],
    "read_files": [],
    "tools_used": {},
    "final_status": "unknown",
    "tags": [],
    "phase": "",
    "completion_summary": {},
    "diagnosis_patterns": [],
}


def _validate_session_facts(facts):
    """P1 Hallucination Prevention: Ensure RLM-critical keys exist before write.

    Deterministic schema enforcement — fills missing keys with safe defaults.
    Prevents malformed knowledge-index entries from breaking RLM queries like:
      Grep "tags.*python" knowledge-index.jsonl
      Grep "final_status.*success" knowledge-index.jsonl

    Returns: facts dict with all required keys guaranteed present.
    """
    for key, default_val in _KI_REQUIRED_DEFAULTS.items():
        if key not in facts:
            # Create new mutable instances to avoid shared references
            if isinstance(default_val, list):
                facts[key] = []
            elif isinstance(default_val, dict):
                facts[key] = {}
            else:
                facts[key] = default_val
    return facts


# =============================================================================
# Knowledge Archive (Area 1: Cross-Session Knowledge Archive)
# =============================================================================

def _classify_error_patterns(entries):
    """CM-1: Classify error patterns from tool results for cross-session learning.

    P1 Compliance: Regex-based deterministic classification.
    A2 Enhancement: File-aware, window-limited resolution matching.
    Returns: list of {"type": str, "tool": str, "file": str, "resolution": dict|None} (max 5).
    """
    tool_results = [e for e in entries if e["type"] == "tool_result"]
    tool_uses = [e for e in entries if e["type"] == "tool_use"]

    # Build tool_use_id → tool_name mapping
    id_to_tool = {tu.get("tool_use_id", ""): tu.get("tool_name", "") for tu in tool_uses}
    id_to_file = {tu.get("tool_use_id", ""): tu.get("file_path", "") for tu in tool_uses}

    # CM-B + E-1: Expanded error taxonomy — reduces "unknown" classification from ~80% to ~30%
    # D-7: Type names MUST match _RISK_WEIGHTS keys (~line 127). Adding a new type here
    #       without a corresponding _RISK_WEIGHTS entry → fallback weight 0.7 applied.
    ERROR_TAXONOMY = [
        ("file_not_found", re.compile(r"No such file|FileNotFoundError|ENOENT|not found", re.I)),
        ("permission", re.compile(r"Permission denied|EACCES|PermissionError|EPERM", re.I)),
        ("syntax", re.compile(r"SyntaxError|syntax error|parse error|unexpected token", re.I)),
        ("timeout", re.compile(r"timed? ?out|TimeoutError|deadline exceeded|ETIMEDOUT", re.I)),
        ("dependency", re.compile(r"ModuleNotFoundError|ImportError|Cannot find module|require\(\) failed", re.I)),
        # B-4: Added re.DOTALL — "old_string ... not found" may span multiple lines
        ("edit_mismatch", re.compile(r"old_string.*not found|not unique|no match|string not found in file", re.I | re.DOTALL)),
        # E-1: New patterns (Reflection: tightened to reduce false positives)
        ("type_error", re.compile(r"TypeError|type error|undefined is not a function|\w+ is not a function(?! of\b)", re.I)),
        ("value_error", re.compile(r"ValueError|invalid (?:value|argument|literal)|value.{0,30}out of range", re.I)),
        ("connection", re.compile(r"ConnectionError|ECONNREFUSED|ECONNRESET|network error|fetch failed", re.I)),
        ("memory", re.compile(r"MemoryError|out of memory|heap (?:space|memory|allocation|overflow)|ENOMEM|allocation failed", re.I)),
        ("git_error", re.compile(r"fatal:.*git|merge conflict|CONFLICT|not a git repository", re.I | re.DOTALL)),
        ("command_not_found", re.compile(r"command not found|not recognized|is not recognized", re.I)),
    ]

    # A2: Build position map for resolution matching (file-aware, window-limited)
    entry_id_to_pos = {}
    for i, e in enumerate(entries):
        entry_id_to_pos[id(e)] = i

    patterns = []
    for tr in tool_results:
        if not tr.get("is_error", False):
            continue
        content = tr.get("content", "")[:500]
        tid = tr.get("tool_use_id", "")
        error_type = "unknown"
        for etype, regex in ERROR_TAXONOMY:
            if regex.search(content):
                error_type = etype
                break

        # A2: Resolution matching — find successful follow-up within 5 entries
        resolution = None
        error_file = os.path.basename(id_to_file.get(tid, ""))
        err_pos = entry_id_to_pos.get(id(tr), -1)
        if err_pos >= 0:
            for next_e in entries[err_pos + 1 : err_pos + 6]:
                if next_e.get("type") != "tool_result":
                    continue
                if next_e.get("is_error", False):
                    continue
                next_tid = next_e.get("tool_use_id", "")
                next_tool = id_to_tool.get(next_tid, "")
                next_file = os.path.basename(id_to_file.get(next_tid, ""))
                # File-aware: same file must match (or error had no file context)
                if next_tool in ("Edit", "Write", "Bash") and (
                    not error_file or next_file == error_file
                ):
                    resolution = {"tool": next_tool, "file": next_file}
                    break

        patterns.append({
            "type": error_type,
            "tool": id_to_tool.get(tid, ""),
            "file": error_file,
            "resolution": resolution,
        })

    return patterns[:5]


def _extract_success_patterns(entries):
    """Extract successful tool sequence patterns for cross-session learning.

    Detects "Edit/Write → successful Bash" sequences — the canonical pattern
    for code modification followed by validation (e.g., tests, builds).

    P1 Compliance: Deterministic extraction from transcript entries.
    Returns: list of {"sequence": str, "files": list, "bash_cmd": str} (max 5).
    """
    tool_uses = [e for e in entries if e["type"] == "tool_use"]
    tool_results = [e for e in entries if e["type"] == "tool_result"]

    # Build result lookup
    result_by_id = {}
    for tr in tool_results:
        tid = tr.get("tool_use_id", "")
        if tid:
            result_by_id[tid] = tr.get("is_error", False)

    patterns = []
    # Sliding window: track consecutive Edit/Write, then look for successful Bash
    edit_buffer = []  # (tool_name, file_path)

    for tu in tool_uses:
        name = tu.get("tool_name", "")
        tid = tu.get("tool_use_id", "")
        is_err = result_by_id.get(tid, False)

        if name in ("Edit", "Write") and not is_err:
            fp = tu.get("file_path", "")
            edit_buffer.append((name, os.path.basename(fp) if fp else ""))
        elif name == "Bash" and not is_err and edit_buffer:
            # Successful Bash after Edit/Write sequence — capture pattern
            cmd = tu.get("command", "")[:100]
            seq_parts = [f"{t[0]}" for t in edit_buffer[-5:]]  # Last 5 edits
            seq_parts.append("Bash")
            files = sorted(set(t[1] for t in edit_buffer[-5:] if t[1]))
            patterns.append({
                "sequence": "→".join(seq_parts),
                "files": files[:5],
                "bash_cmd": cmd,
            })
            edit_buffer = []  # Reset buffer after capture
        elif name not in ("Edit", "Write", "Read"):
            # Non-Edit/Write/Read tool breaks the sequence (Read is transparent)
            if name != "Bash":
                edit_buffer = []

    return patterns[:5]


def _extract_pacs_from_sot(project_dir):
    """CM-1: Extract pACS min-score from SOT (read-only).

    P1 Compliance: Deterministic YAML/regex extraction.
    SOT Compliance: Read-only access.
    Returns: int or None.
    """
    if not project_dir:
        return None
    try:
        import yaml
        for sp in sot_paths(project_dir):
            if os.path.exists(sp) and not sp.endswith(".json"):
                with open(sp, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f.read())
                if isinstance(data, dict):
                    wf = data.get("workflow", {})
                    if isinstance(wf, dict):
                        pacs = wf.get("pacs", {})
                        if isinstance(pacs, dict) and "min_score" in pacs:
                            return pacs["min_score"]
    except Exception:
        pass
    return None


def _extract_team_summaries(project_dir):
    """FIX-H1: Extract active_team.completed_summaries from SOT (read-only).

    Preserves team coordination history in knowledge-index.jsonl,
    surviving snapshot rotation and Phase 6-7 compression.

    P1 Compliance: Deterministic YAML extraction.
    SOT Compliance: Read-only access.
    FIX-R4: Removed .json filter — yaml.safe_load() can parse JSON (JSON ⊂ YAML).
    Returns: dict or None.
    """
    if not project_dir:
        return None
    try:
        import yaml
        for sp in sot_paths(project_dir):
            if os.path.exists(sp):
                with open(sp, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f.read())
                if isinstance(data, dict):
                    wf = data.get("workflow", {})
                    if isinstance(wf, dict):
                        active_team = wf.get("active_team", {})
                        if isinstance(active_team, dict):
                            summaries = active_team.get("completed_summaries", {})
                            if summaries:
                                return summaries
    except Exception:
        pass
    return None


def extract_session_facts(session_id, trigger, project_dir, entries, token_estimate=0):
    """Extract deterministic session facts for knowledge-index.jsonl.

    P1 Compliance: All fields are deterministic extractions.
    No semantic inference, no heuristic judgment.
    """
    user_messages = [e for e in entries if e["type"] == "user_message"]
    tool_uses = [e for e in entries if e["type"] == "tool_use"]

    # First user message (C-2: expanded to 300 chars for richer cross-session context)
    user_task = ""
    if user_messages:
        # Skip system-injected messages
        for msg in user_messages:
            content = msg.get("content", "")
            if not (content.startswith("<") and ">" in content[:50]):
                user_task = content[:300]
                break

    # Last user instruction (deterministic) — 품질 최적화
    # 긴 세션에서 마지막 지시가 "현재 작업 상태"를 더 정확히 반영한다.
    last_instruction = ""
    if user_messages:
        for msg in reversed(user_messages):
            content = msg.get("content", "")
            if not (content.startswith("<") and ">" in content[:50]):
                if content[:300] != user_task:  # 첫 메시지와 동일하면 생략
                    last_instruction = content[:300]
                break

    # Modified files — unique paths from Write/Edit
    modified_files = sorted(set(
        tu.get("file_path", "") for tu in tool_uses
        if tu.get("tool_name") in ("Write", "Edit") and tu.get("file_path")
    ))

    # B2: Per-file modification metadata — tool type + edit count for change magnitude
    file_detail = {}
    for tu in tool_uses:
        tool_name = tu.get("tool_name", "")
        fp = tu.get("file_path", "")
        if tool_name in ("Write", "Edit") and fp:
            if fp not in file_detail:
                file_detail[fp] = {"tool": tool_name, "edits": 0}
            file_detail[fp]["edits"] += 1
            # Write overwrites; if both Write and Edit occurred, record Write
            if tool_name == "Write":
                file_detail[fp]["tool"] = "Write"

    # Read files — unique paths from Read
    read_files = sorted(set(
        tu.get("file_path", "") for tu in tool_uses
        if tu.get("tool_name") == "Read" and tu.get("file_path")
    ))

    # Tool usage counts (deterministic)
    tools_used = {}
    for tu in tool_uses:
        name = tu.get("tool_name", "unknown")
        tools_used[name] = tools_used.get(name, 0) + 1

    # CM-D + E-3: Tool sequence — consecutive distinct tool names (run-length compressed)
    # Captures work patterns like "Read→Read→Edit→Bash→Read→Edit" → "Read(2)→Edit→Bash→Read→Edit"
    tool_sequence_parts = []
    prev_tool = None
    count = 0
    for tu in tool_uses:
        name = tu.get("tool_name", "unknown")
        if name == prev_tool:
            count += 1
        else:
            if prev_tool:
                tool_sequence_parts.append(f"{prev_tool}({count})" if count > 1 else prev_tool)
            prev_tool = name
            count = 1
    if prev_tool:
        tool_sequence_parts.append(f"{prev_tool}({count})" if count > 1 else prev_tool)
    tool_sequence = "→".join(tool_sequence_parts[-30:])  # Last 30 segments to cap size

    # B-3: Phase detection — current dominant phase
    phase = detect_conversation_phase(tool_uses)

    # B-3: Primary language detection (deterministic — file extension counting)
    ext_counts = {}
    all_files = modified_files + read_files
    for fp in all_files:
        ext = os.path.splitext(fp)[1].lower()
        if ext:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
    primary_language = ""
    if ext_counts:
        primary_language = max(ext_counts, key=ext_counts.get)

    # B-3: Phase transitions (multi-phase detection, with tool_count per phase)
    transitions = detect_phase_transitions(tool_uses)
    if len(transitions) > 1:
        phase_flow = " → ".join(
            f"{t[0]}({t[2]-t[1]})" for t in transitions
        )
    else:
        phase_flow = phase

    facts = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "project": project_dir,
        "user_task": user_task,
        "modified_files": modified_files,
        "modified_files_detail": file_detail,  # B2: per-file tool + edit count
        "read_files": read_files,
        "tools_used": tools_used,
        "trigger": trigger,
        "token_estimate": token_estimate,
        "phase": phase,
        "phase_flow": phase_flow,
        "primary_language": primary_language,
        "tool_sequence": tool_sequence,  # CM-D + E-3: work pattern analysis
    }

    # A4: Search tags — language-independent path-derived keywords for RLM probing
    all_paths = modified_files + read_files
    search_tags = extract_path_tags(all_paths)
    if search_tags:
        facts["tags"] = search_tags

    if last_instruction:
        facts["last_instruction"] = last_instruction

    # E7 + E2: Completion state and git summary (deterministic, reuses existing functions)
    completion = extract_completion_state(entries, project_dir)
    git_state = capture_git_state(project_dir, max_diff_chars=500)

    facts["completion_summary"] = {
        "total_tool_calls": completion["total_tool_calls"],
        "edit_success": completion["edit_success"],
        "edit_fail": completion["edit_fail"],
        "bash_success": completion["bash_success"],
        "bash_fail": completion["bash_fail"],
    }
    facts["git_summary"] = git_state.get("status", "")[:200]

    # E-4: final_status — deterministic session outcome classification
    total_fails = completion["edit_fail"] + completion["bash_fail"]
    total_success = completion["edit_success"] + completion["bash_success"]
    if total_fails == 0 and total_success > 0:
        facts["final_status"] = "success"
    elif total_fails > 0 and total_success > total_fails:
        facts["final_status"] = "incomplete"  # Some failures but mostly succeeded
    elif total_fails > 0:
        facts["final_status"] = "error"
    else:
        facts["final_status"] = "unknown"  # No edits/bash at all (read-only session)

    # Session duration (deterministic timestamp difference)
    timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]
    if len(timestamps) >= 2:
        facts["session_duration_entries"] = len(timestamps)

    # CM-1: Cross-session knowledge enrichment fields
    # 1. Design decisions — top 5 high-signal decisions for RLM probing
    assistant_texts = [e for e in entries if e["type"] == "assistant_text"]
    all_decisions = _extract_decisions(assistant_texts)
    high_signal = [d for d in all_decisions if not d.startswith("[intent]")]
    facts["design_decisions"] = high_signal[:5]

    # 2. Error patterns — classified Bash/Edit failures for cross-session learning
    error_patterns = _classify_error_patterns(entries)
    if error_patterns:
        facts["error_patterns"] = error_patterns

    # 2.5. Success patterns — Edit/Write→Bash success sequences for cross-session learning
    success_patterns = _extract_success_patterns(entries)
    if success_patterns:
        facts["success_patterns"] = success_patterns

    # 3. pACS min-score — SOT에서 추출 (있는 경우, read-only)
    pacs_min = _extract_pacs_from_sot(project_dir)
    if pacs_min is not None:
        facts["pacs_min"] = pacs_min

    # 4. ULW mode detection — tag session for RLM cross-session queries
    ulw_state = detect_ulw_mode(entries)
    if ulw_state:
        facts["ulw_active"] = True

    # 5. FIX-H1: Team work summaries — archive to KI for RLM persistence
    # completed_summaries in snapshot IMMORTAL can be lost during Phase 6-7 compression.
    # Archiving to KI ensures cross-session team coordination history survives.
    team_summaries = _extract_team_summaries(project_dir)
    if team_summaries:
        facts["team_summaries"] = team_summaries

    # 6. Abductive Diagnosis patterns — archive to KI for cross-session learning
    diagnosis_patterns = _extract_diagnosis_patterns(project_dir)
    if diagnosis_patterns:
        facts["diagnosis_patterns"] = diagnosis_patterns

    return facts


def replace_or_append_session_facts(ki_path, facts):
    """Append session facts to knowledge-index.jsonl with session_id dedup.

    If an entry with the same session_id already exists, replaces it
    (later saves have more complete data — e.g., sessionend after threshold).

    A-1: Reads under shared lock, writes via atomic temp→rename under exclusive lock.
         Even if the process crashes mid-write, the original file is never corrupted.
    A-2: Empty/missing session_id skips dedup (appends as new unique entry).
    A-3: Empty session_id triggers UUID fallback to prevent unbounded dedup bypass.

    P1 Compliance: All operations are deterministic (JSON read/filter/write).
    SOT Compliance: Only called from save_context.py and _trigger_proactive_save.
    """
    session_id = facts.get("session_id", "")

    # A-3: Empty session_id fallback — generate UUID to enable dedup on retry
    if not session_id or session_id == "unknown":
        import uuid
        session_id = f"auto-{uuid.uuid4().hex[:12]}"
        facts["session_id"] = session_id

    # P1 Schema Validation: Ensure RLM-critical keys exist before write
    facts = _validate_session_facts(facts)

    parent_dir = os.path.dirname(ki_path)
    os.makedirs(parent_dir, exist_ok=True)

    # Use a dedicated lock file to separate read/write locking from the data file.
    # This avoids the truncate-then-write vulnerability entirely.
    lock_path = ki_path + ".lock"

    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Read existing entries (file may not exist yet)
            lines = []
            if os.path.exists(ki_path):
                try:
                    with open(ki_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except Exception:
                    pass

            # Filter out existing entry with same session_id (dedup)
            kept = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                    if entry.get("session_id") == session_id:
                        continue  # Remove old entry — will be replaced
                except json.JSONDecodeError:
                    kept.append(stripped + "\n")
                    continue
                kept.append(stripped + "\n")

            # Append new entry
            kept.append(json.dumps(facts, ensure_ascii=False) + "\n")

            # A-1: Atomic write — temp file + rename. If crash happens,
            # either old file or new file exists, never a half-written state.
            atomic_write(ki_path, "".join(kept))
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except Exception:
        # Non-blocking fallback: append-only (no dedup, but no data loss)
        try:
            with open(ki_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(facts, ensure_ascii=False) + "\n")
        except Exception:
            pass


def cleanup_knowledge_index(snapshot_dir):
    """Rotate knowledge-index.jsonl to keep MAX_KNOWLEDGE_INDEX_ENTRIES entries.

    Deterministic: keeps the most recent N entries, removes oldest.
    """
    ki_path = os.path.join(snapshot_dir, "knowledge-index.jsonl")
    if not os.path.exists(ki_path):
        return

    try:
        lines = []
        with open(ki_path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]

        if len(lines) <= MAX_KNOWLEDGE_INDEX_ENTRIES:
            return

        # Keep only the most recent entries
        trimmed = lines[-MAX_KNOWLEDGE_INDEX_ENTRIES:]
        atomic_write(ki_path, "".join(trimmed))
    except Exception:
        pass


def cleanup_session_archives(snapshot_dir):
    """Rotate session archives to keep MAX_SESSION_ARCHIVES files.

    Keeps most recent by modification time.
    """
    sessions_dir = os.path.join(snapshot_dir, "sessions")
    if not os.path.isdir(sessions_dir):
        return

    try:
        files = []
        for f in os.listdir(sessions_dir):
            if f.endswith(".md"):
                fpath = os.path.join(sessions_dir, f)
                files.append((fpath, os.path.getmtime(fpath)))

        if len(files) <= MAX_SESSION_ARCHIVES:
            return

        # Sort by mtime, newest first — remove oldest
        files.sort(key=lambda x: x[1], reverse=True)
        for fpath, _ in files[MAX_SESSION_ARCHIVES:]:
            try:
                os.unlink(fpath)
            except OSError:
                pass
    except Exception:
        pass


# =============================================================================
# Quality Gate State Extraction (Context Memory Optimization)
# =============================================================================


def _extract_quality_gate_state(project_dir):
    """Extract latest Quality Gate state for IMMORTAL snapshot preservation.

    Scans pacs-logs/, review-logs/, verification-logs/ for the most recent
    step's quality gate results. Provides session recovery context when
    a session dies during Verification retry, pACS RED rework, or Review FAIL.

    P1 Compliance: Filesystem + regex only.
    SOT Compliance: Read-only access to log directories.

    Returns: list of markdown lines (empty if no gate logs exist).
    """
    lines = []

    # Find the highest step number across all gate log directories
    max_step = 0
    gate_dirs = {
        "pacs": os.path.join(project_dir, "pacs-logs"),
        "review": os.path.join(project_dir, "review-logs"),
        "verify": os.path.join(project_dir, "verification-logs"),
    }
    _step_re = re.compile(r"step-(\d+)")

    for gate_type, gate_dir in gate_dirs.items():
        if not os.path.isdir(gate_dir):
            continue
        try:
            for fname in os.listdir(gate_dir):
                m = _step_re.search(fname)
                if m:
                    step = int(m.group(1))
                    if step > max_step:
                        max_step = step
        except OSError:
            continue

    if max_step == 0:
        return lines

    lines.append(f"최신 검증 단계: **Step {max_step}**")

    # pACS score for the latest step
    pacs_path = os.path.join(
        project_dir, "pacs-logs", f"step-{max_step}-pacs.md"
    )
    if os.path.exists(pacs_path):
        try:
            with open(pacs_path, "r", encoding="utf-8") as f:
                pacs_content = f.read(2000)
            if not pacs_content.strip():
                raise ValueError("empty pACS file")
            # Extract pACS score
            pacs_match = re.search(
                r"pACS\s*=.*?=\s*(\d{1,3})|pACS\s*=\s*(\d{1,3})",
                pacs_content, re.IGNORECASE,
            )
            if pacs_match:
                score = pacs_match.group(1) or pacs_match.group(2)
                lines.append(f"- **pACS**: {score}")
            # Extract weak dimension
            weak_match = re.search(
                r"(?:weak|약점)\s*(?:dimension|차원)\s*[:=]\s*([FCL])",
                pacs_content, re.IGNORECASE,
            )
            if weak_match:
                lines.append(f"- **약점 차원**: {weak_match.group(1)}")
            # Extract pre-mortem first line
            pm_match = re.search(
                r"(?:Pre-mortem|사전 부검).*?\n(.*?)(?:\n|$)",
                pacs_content, re.IGNORECASE,
            )
            if pm_match:
                pm_line = pm_match.group(1).strip()[:200]
                if pm_line:
                    lines.append(f"- **Pre-mortem**: {pm_line}")
        except Exception:
            pass

    # Review verdict for the latest step
    review_path = os.path.join(
        project_dir, "review-logs", f"step-{max_step}-review.md"
    )
    if os.path.exists(review_path):
        review_data = parse_review_verdict(review_path)
        verdict = review_data.get("verdict", "N/A")
        critical = review_data.get("critical_count", 0)
        warning = review_data.get("warning_count", 0)
        reviewer_pacs = review_data.get("reviewer_pacs")
        lines.append(
            f"- **Review**: {verdict} "
            f"(Critical: {critical}, Warning: {warning})"
        )
        if reviewer_pacs:
            lines.append(f"- **Reviewer pACS**: {reviewer_pacs}")

    # Verification status for the latest step
    verify_path = os.path.join(
        project_dir, "verification-logs", f"step-{max_step}-verify.md"
    )
    if os.path.exists(verify_path):
        try:
            with open(verify_path, "r", encoding="utf-8") as f:
                verify_content = f.read(2000)
            pass_count = len(re.findall(
                r"\bPASS\b", verify_content, re.IGNORECASE
            ))
            fail_count = len(re.findall(
                r"\bFAIL\b", verify_content, re.IGNORECASE
            ))
            lines.append(
                f"- **Verification**: PASS {pass_count}건, FAIL {fail_count}건"
            )
        except Exception:
            pass

    # Diagnosis status for the latest step (if diagnosis-logs/ exists)
    diag_dir = os.path.join(project_dir, "diagnosis-logs")
    if os.path.isdir(diag_dir):
        try:
            diag_files = [
                f for f in os.listdir(diag_dir)
                if f.startswith(f"step-{max_step}-") and f.endswith(".md")
            ]
            if diag_files:
                latest_diag = sorted(diag_files)[-1]
                diag_path = os.path.join(diag_dir, latest_diag)
                with open(diag_path, "r", encoding="utf-8") as f:
                    diag_content = f.read(2000)
                selected = _DIAG_SELECTED_RE.search(diag_content)
                gate_match = _DIAG_GATE_RE.search(diag_content)
                diag_gate = gate_match.group(1) if gate_match else "?"
                diag_hyp = selected.group(1).strip() if selected else "?"
                lines.append(
                    f"- **Diagnosis**: gate={diag_gate}, hypothesis={diag_hyp}"
                )
        except Exception:
            pass

    return lines


# =============================================================================
# Adversarial Review Validation (P1: Hallucination Prevention — Enhanced L2)
# =============================================================================
# These functions provide deterministic validation for the Adversarial Review
# system. All checks are regex/filesystem/arithmetic — zero LLM interpretation.
# SOT Compliance: Read-only access to review-logs/ and pacs-logs/.

# Required sections in a review report (regex patterns for section headers)
_REVIEW_REQUIRED_SECTIONS = [
    re.compile(r"^#+\s*Pre-mortem", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^#+\s*Issues\s+Found", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^#+\s*Independent\s+pACS", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^#+\s*Verdict", re.MULTILINE | re.IGNORECASE),
]

# Verdict extraction: "## Verdict: PASS" or "## Verdict: FAIL"
_REVIEW_VERDICT_RE = re.compile(
    r"^#+\s*Verdict\s*:\s*[*_~`]*\s*(PASS|FAIL)(?:\b|[*_~`])",
    re.MULTILINE | re.IGNORECASE,
)

# Issues table row: "| N | Severity | ..." — at least 4 pipe-separated cells
_REVIEW_ISSUE_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|", re.MULTILINE
)

# Severity extraction from issues table rows
_REVIEW_CRITICAL_RE = re.compile(r"\bCritical\b", re.IGNORECASE)
_REVIEW_WARNING_RE = re.compile(r"\bWarning\b", re.IGNORECASE)
_REVIEW_SUGGESTION_RE = re.compile(r"\bSuggestion\b", re.IGNORECASE)

# pACS score extraction: "F | 85 |" or "Reviewer pACS = min(F,C,L) = 72"
_REVIEW_PACS_DIM_RE = re.compile(
    r"^\|\s*([FCL])\s*\|\s*(\d{1,3})\s*\|", re.MULTILINE
)
_REVIEW_PACS_FINAL_RE = re.compile(
    r"Reviewer\s+pACS\s*=.*?=\s*(\d{1,3})", re.IGNORECASE
)
_REVIEW_GENERATOR_PACS_RE = re.compile(
    r"Generator\s+pACS\s*=\s*(\d{1,3})", re.IGNORECASE
)


def validate_review_output(project_dir, step_number):
    """Anti-Skip Guard for Adversarial Review outputs.

    P1 Compliance: All 5 checks are deterministic (filesystem + regex).
    SOT Compliance: Read-only access to review-logs/.

    Checks:
      R1: review-logs/step-{N}-review.md exists
      R2: File size >= MIN_OUTPUT_SIZE (100 bytes)
      R3: All 4 required sections present (Pre-mortem, Issues, pACS, Verdict)
      R4: Verdict is explicitly PASS or FAIL
      R5: Issues table has >= 1 data row (rubber-stamp prevention)

    Args:
        project_dir: Project root directory path
        step_number: Step number (int) to validate

    Returns:
        tuple: (is_valid: bool, verdict: str|None, issues_count: int,
                warnings: list[str])
        - is_valid: True only if all R1-R5 pass
        - verdict: "PASS" or "FAIL" or None if not extractable
        - issues_count: Number of issue rows found
        - warnings: List of human-readable failure reasons
    """
    warnings = []
    review_path = os.path.join(
        project_dir, "review-logs", f"step-{step_number}-review.md"
    )

    # R1: File existence
    if not os.path.exists(review_path):
        warnings.append(
            f"R1 FAIL: review-logs/step-{step_number}-review.md not found"
        )
        return (False, None, 0, warnings)

    # R2: Minimum size
    try:
        size = os.path.getsize(review_path)
    except OSError:
        warnings.append(f"R2 FAIL: Cannot read file size: {review_path}")
        return (False, None, 0, warnings)

    if size < MIN_OUTPUT_SIZE:
        warnings.append(
            f"R2 FAIL: Review too small ({size} bytes, min {MIN_OUTPUT_SIZE})"
        )
        return (False, None, 0, warnings)

    # Read content for R3-R5
    try:
        with open(review_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        warnings.append(f"R2 FAIL: Cannot read file: {e}")
        return (False, None, 0, warnings)

    # R3: Required sections
    for i, pattern in enumerate(_REVIEW_REQUIRED_SECTIONS):
        section_names = ["Pre-mortem", "Issues Found", "Independent pACS", "Verdict"]
        if not pattern.search(content):
            warnings.append(f"R3 FAIL: Missing required section: {section_names[i]}")

    # R4: Verdict extraction
    verdict_match = _REVIEW_VERDICT_RE.search(content)
    verdict = verdict_match.group(1).upper() if verdict_match else None
    if verdict is None:
        warnings.append("R4 FAIL: No explicit PASS/FAIL verdict found")

    # R5: Issues table rows (rubber-stamp prevention)
    issue_rows = _REVIEW_ISSUE_ROW_RE.findall(content)
    issues_count = len(issue_rows)
    if issues_count < 1:
        warnings.append("R5 FAIL: No issues found in table (minimum 1 required)")

    is_valid = len(warnings) == 0
    return (is_valid, verdict, issues_count, warnings)


def parse_review_verdict(review_path):
    """Extract PASS/FAIL verdict and issue severity counts from review report.

    P1 Compliance: Regex-based extraction only, no LLM interpretation.
    Useful for Orchestrator to make deterministic proceed/rework decisions.

    Args:
        review_path: Absolute path to review-logs/step-N-review.md

    Returns:
        dict with keys:
        - verdict: "PASS" | "FAIL" | None
        - critical_count: int (number of Critical issues)
        - warning_count: int (number of Warning issues)
        - suggestion_count: int (number of Suggestion issues)
        - reviewer_pacs: int | None (reviewer's pACS score)
        - pacs_dimensions: dict | None ({"F": int, "C": int, "L": int})
    """
    result = {
        "verdict": None,
        "critical_count": 0,
        "warning_count": 0,
        "suggestion_count": 0,
        "reviewer_pacs": None,
        "pacs_dimensions": None,
    }

    if not os.path.exists(review_path):
        return result

    try:
        with open(review_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return result

    # Verdict
    verdict_match = _REVIEW_VERDICT_RE.search(content)
    if verdict_match:
        result["verdict"] = verdict_match.group(1).upper()

    # Issue severity counts from table rows
    issue_rows = _REVIEW_ISSUE_ROW_RE.findall(content)
    # Each row is like "| 1 | Critical | file:line | Problem | Fix |"
    # We need to check each full row line for severity
    for row_start in _REVIEW_ISSUE_ROW_RE.finditer(content):
        # Get the full line containing this row
        line_start = content.rfind("\n", 0, row_start.start()) + 1
        line_end = content.find("\n", row_start.start())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]

        if _REVIEW_CRITICAL_RE.search(line):
            result["critical_count"] += 1
        elif _REVIEW_WARNING_RE.search(line):
            result["warning_count"] += 1
        elif _REVIEW_SUGGESTION_RE.search(line):
            result["suggestion_count"] += 1

    # Reviewer pACS dimensions
    dims = {}
    for dim_match in _REVIEW_PACS_DIM_RE.finditer(content):
        dim_name = dim_match.group(1).upper()
        dim_score = int(dim_match.group(2))
        if 0 <= dim_score <= 100:
            dims[dim_name] = dim_score

    if len(dims) == 3 and all(k in dims for k in ("F", "C", "L")):
        result["pacs_dimensions"] = dims

    # Reviewer pACS final score
    pacs_match = _REVIEW_PACS_FINAL_RE.search(content)
    if pacs_match:
        score = int(pacs_match.group(1))
        if 0 <= score <= 100:
            result["reviewer_pacs"] = score
    elif result["pacs_dimensions"]:
        # Fallback: calculate from dimensions (min of F, C, L)
        result["reviewer_pacs"] = min(result["pacs_dimensions"].values())

    return result


def calculate_pacs_delta(project_dir, step_number):
    """Calculate |generator_pACS - reviewer_pACS| for reconciliation detection.

    P1 Compliance: Pure arithmetic — no LLM interpretation.
    Reads from pacs-logs/step-N-pacs.md (generator) and
    review-logs/step-N-review.md (reviewer).

    A delta >= 15 indicates potential miscalibration and may require
    reconciliation (either generator inflated or reviewer too harsh).

    Args:
        project_dir: Project root directory path
        step_number: Step number (int)

    Returns:
        dict with keys:
        - generator_score: int | None
        - reviewer_score: int | None
        - delta: int | None (absolute difference, None if either score missing)
        - needs_reconciliation: bool (True if delta >= 15)
    """
    result = {
        "generator_score": None,
        "reviewer_score": None,
        "delta": None,
        "needs_reconciliation": False,
    }

    # Extract generator pACS from pacs-logs/step-N-pacs.md
    generator_path = os.path.join(
        project_dir, "pacs-logs", f"step-{step_number}-pacs.md"
    )
    if os.path.exists(generator_path):
        try:
            with open(generator_path, "r", encoding="utf-8") as f:
                gen_content = f.read()
            # Pattern: "pACS = min(F, C, L) = 85" or "pACS = 85"
            gen_match = re.search(
                r"pACS\s*=.*?=\s*(\d{1,3})|pACS\s*=\s*(\d{1,3})",
                gen_content, re.IGNORECASE
            )
            if gen_match:
                score_str = gen_match.group(1) or gen_match.group(2)
                score = int(score_str)
                if 0 <= score <= 100:
                    result["generator_score"] = score
        except (IOError, UnicodeDecodeError, ValueError):
            pass

    # Extract reviewer pACS from review report
    review_path = os.path.join(
        project_dir, "review-logs", f"step-{step_number}-review.md"
    )
    review_data = parse_review_verdict(review_path)
    result["reviewer_score"] = review_data.get("reviewer_pacs")

    # Calculate delta
    if result["generator_score"] is not None and result["reviewer_score"] is not None:
        result["delta"] = abs(result["generator_score"] - result["reviewer_score"])
        result["needs_reconciliation"] = result["delta"] >= 15

    return result


def _read_sot_outputs(project_dir):
    """Read SOT file and return outputs dict. Read-only.

    P1 Compliance: Deterministic file read + parse.
    SOT Compliance: Read-only access.

    Returns:
        dict: outputs section from SOT, or {} on any failure.
    """
    for sot_file in sot_paths(project_dir):
        if not os.path.exists(sot_file):
            continue
        try:
            with open(sot_file, "r", encoding="utf-8") as f:
                content = f.read()
            if sot_file.endswith(".json"):
                import json
                data = json.loads(content)
            else:
                try:
                    import yaml
                    data = yaml.safe_load(content)
                except ImportError:
                    continue
            if isinstance(data, dict):
                outputs = data.get("outputs", {})
                return outputs if isinstance(outputs, dict) else {}
        except Exception:
            continue
    return {}


def _find_translation_files_for_step(project_dir, step_number):
    """Discover translation files for a step via 3-tier fallback.

    Tier 1: SOT outputs.step-{N}-ko (explicit ko path from SOT)
    Tier 2: translations/ directory (legacy compatibility)
    Tier 3: Sibling *.ko.md next to SOT outputs.step-{N} (same-dir convention
             per translator.md: "output file must be in the same directory
             as the English original")

    P1 Compliance: Filesystem operations only.
    SOT Compliance: Read-only access via _read_sot_outputs().

    Returns:
        list: Existing translation file paths (deduplicated by realpath).
    """
    found = []
    seen = set()

    def _add(path):
        rp = os.path.realpath(path)
        if rp not in seen and os.path.exists(path):
            seen.add(rp)
            found.append(path)

    # --- Tier 1 & 3: Read SOT once ---
    outputs = _read_sot_outputs(project_dir)
    if outputs:
        # Tier 1: Explicit ko path from SOT outputs
        ko_key = f"step-{step_number}-ko"
        ko_val = outputs.get(ko_key)
        if ko_val:
            ko_path = (
                ko_val if os.path.isabs(ko_val)
                else os.path.join(project_dir, ko_val)
            )
            _add(ko_path)

        # Tier 3: Sibling .ko.md next to original output file
        orig_key = f"step-{step_number}"
        orig_val = outputs.get(orig_key)
        if orig_val:
            orig_path = (
                orig_val if os.path.isabs(orig_val)
                else os.path.join(project_dir, orig_val)
            )
            base, ext = os.path.splitext(orig_path)
            sibling = f"{base}.ko{ext}" if ext else f"{orig_path}.ko.md"
            _add(sibling)

    # --- Tier 2: translations/ directory (legacy) ---
    translations_dir = os.path.join(project_dir, "translations")
    if os.path.isdir(translations_dir):
        prefix = f"step-{step_number}"
        try:
            for fname in os.listdir(translations_dir):
                if fname.startswith(prefix) and fname.endswith(".ko.md"):
                    _add(os.path.join(translations_dir, fname))
        except OSError:
            pass

    return found


def validate_review_sequence(project_dir, step_number):
    """Verify that review PASS preceded translation start.

    P1 Compliance: File timestamp comparison — deterministic.
    Prevents translating flawed output (review FAIL → no translation).

    Translation file discovery uses 3-tier fallback:
      Tier 1: SOT outputs.step-{N}-ko (explicit path)
      Tier 2: translations/ directory (legacy)
      Tier 3: Sibling *.ko.md next to original (translator.md convention)

    Checks:
      1. review-logs/step-{N}-review.md exists with PASS verdict
      2. If translation (*.ko.md) exists for this step, review file must be older

    Args:
        project_dir: Project root directory path
        step_number: Step number (int)

    Returns:
        tuple: (is_valid: bool, warning: str | None)
        - is_valid: True if sequence is correct or no translation exists
        - warning: Human-readable issue description, None if valid
    """
    review_path = os.path.join(
        project_dir, "review-logs", f"step-{step_number}-review.md"
    )

    # 3-tier translation file discovery
    translation_files = _find_translation_files_for_step(project_dir, step_number)

    # No translation files → sequence is trivially valid
    if not translation_files:
        return (True, None)

    # Translation exists but no review → violation
    if not os.path.exists(review_path):
        return (
            False,
            f"Step {step_number}: Translation exists but no review report found. "
            f"Review must PASS before translation.",
        )

    # Check review verdict
    review_data = parse_review_verdict(review_path)
    if review_data["verdict"] != "PASS":
        return (
            False,
            f"Step {step_number}: Translation exists but review verdict is "
            f"{review_data['verdict'] or 'UNKNOWN'} (must be PASS).",
        )

    # Timestamp check: review must be older than (or same as) translation
    try:
        review_mtime = os.path.getmtime(review_path)
    except OSError:
        return (
            False,
            f"Step {step_number}: Cannot read review file timestamp.",
        )

    for tf in translation_files:
        try:
            trans_mtime = os.path.getmtime(tf)
            if trans_mtime < review_mtime:
                return (
                    False,
                    f"Step {step_number}: Translation {os.path.basename(tf)} "
                    f"(mtime {trans_mtime:.0f}) is older than review "
                    f"(mtime {review_mtime:.0f}). Translation may precede review.",
                )
        except OSError:
            continue

    return (True, None)


# =============================================================================
# Translation P1 Validation (T1-T9) + Universal pACS + Verification Log P1
# =============================================================================
# These functions provide deterministic validation for:
#   1. Translation outputs (T1-T7 in validate_translation_output)
#   2. Glossary freshness (T8 in check_glossary_freshness)
#   3. pACS arithmetic across ALL log types (T9 — universal)
#   4. Verification log structural integrity (V1a-V1c)
# All checks are regex/filesystem/arithmetic — zero LLM interpretation.
# SOT Compliance: Read-only access to SOT, translations/, pacs-logs/, verification-logs/.

# --- Translation structural comparison (T6, T7) ---
_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_CODE_BLOCK_FENCE_RE = re.compile(r"^```", re.MULTILINE)

# --- Universal pACS arithmetic verification (T9) ---
# Dimension row: "| F | 85 |", "| Ft (Fidelity) | 85 |", "| Ct (Completeness) | 72 |"
_PACS_DIM_UNIVERSAL_RE = re.compile(
    r"^\|\s*([A-Z][a-z]?)\s*(?:\([^)]*\))?\s*\|\s*(\d{1,3})\s*\|",
    re.MULTILINE,
)
# Explicit min formula: "pACS = min(F, C, L) = 75" or "Translation pACS = min(Ft,Ct,Nt) = 72"
_PACS_WITH_MIN_RE = re.compile(
    r"pACS\s*=\s*min\s*\([^)]+\)\s*=\s*(\d{1,3})",
    re.IGNORECASE,
)
# Simple score (no min formula): "pACS = 85" — used as fallback
_PACS_SIMPLE_RE = re.compile(
    r"pACS\s*=\s*(\d{1,3})\b",
    re.IGNORECASE,
)

# --- Verification log structural integrity (V1) ---
# Per-criterion result: "- [x] Criterion: PASS" or "- Criterion: FAIL"
_VERIFY_CRITERION_CHECKLIST_RE = re.compile(
    r"^[-*]\s*\[?\s*[xX✅❌ ]?\s*\]?\s*(.+?)[:：]\s*(PASS|FAIL)",
    re.MULTILINE | re.IGNORECASE,
)
# Table format: "| Criterion | PASS | evidence |"
_VERIFY_CRITERION_TABLE_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*(PASS|FAIL)\s*\|",
    re.MULTILINE | re.IGNORECASE,
)
# Overall result: "## Overall: PASS", "Overall Result: FAIL"
_VERIFY_OVERALL_RE = re.compile(
    r"(?:Overall|Total|종합|최종)\s*(?:Result|결과|Verdict|판정)?\s*[:：]\s*(PASS|FAIL)",
    re.IGNORECASE,
)
# Table header words to skip when parsing verification log tables
_VERIFY_TABLE_HEADER_WORDS = frozenset({
    "criterion", "criteria", "check", "기준", "항목",
    "dimension", "result", "evidence", "---",
})


def validate_translation_output(project_dir, step_number):
    """Anti-Skip Guard for Translation outputs (T1-T7).

    P1 Compliance: All 7 checks are deterministic (filesystem + regex).
    SOT Compliance: Read-only access via _read_sot_outputs().

    Checks:
      T1: Translation file exists (3-tier discovery via _find_translation_files_for_step)
      T2: Translation file size >= MIN_OUTPUT_SIZE (100 bytes)
      T3: English source file exists (from SOT outputs)
      T4: Translation file has .ko.md extension
      T5: Translation content is non-empty (not just whitespace)
      T6: Structural completeness — heading count EN ≈ KO (±20% tolerance)
      T7: Code block preservation — code block fence count EN == KO

    Args:
        project_dir: Project root directory path
        step_number: Step number (int) to validate

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
        - is_valid: True only if all T1-T7 pass
        - warnings: List of human-readable failure reasons
    """
    warnings = []

    # --- T1: Translation file existence (3-tier discovery) ---
    translation_files = _find_translation_files_for_step(project_dir, step_number)
    if not translation_files:
        warnings.append(
            f"T1 FAIL: No translation file found for step {step_number} "
            f"(checked SOT ko key, translations/ dir, sibling .ko.md)"
        )
        return (False, warnings)

    # Use first discovered translation file as primary
    ko_path = translation_files[0]

    # --- T2: Minimum size ---
    try:
        ko_size = os.path.getsize(ko_path)
    except OSError:
        warnings.append(f"T2 FAIL: Cannot read file size: {ko_path}")
        return (False, warnings)

    if ko_size < MIN_OUTPUT_SIZE:
        warnings.append(
            f"T2 FAIL: Translation too small ({ko_size} bytes, min {MIN_OUTPUT_SIZE})"
        )

    # --- T3: English source file existence ---
    outputs = _read_sot_outputs(project_dir)
    en_path = None
    if outputs:
        en_val = outputs.get(f"step-{step_number}")
        if en_val:
            en_path = (
                en_val if os.path.isabs(en_val)
                else os.path.join(project_dir, en_val)
            )

    if en_path is None:
        warnings.append(
            f"T3 FAIL: No English source path in SOT outputs.step-{step_number}"
        )
    elif not os.path.exists(en_path):
        warnings.append(f"T3 FAIL: English source not found: {en_path}")

    # --- T4: .ko.md extension ---
    ko_basename = os.path.basename(ko_path)
    if not ko_basename.endswith(".ko.md"):
        warnings.append(
            f"T4 FAIL: Translation filename '{ko_basename}' does not end with .ko.md"
        )

    # --- T5-T7: Content-based checks (require reading files) ---
    ko_content = None
    try:
        with open(ko_path, "r", encoding="utf-8") as f:
            ko_content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        warnings.append(f"T5 FAIL: Cannot read translation file: {e}")

    if ko_content is not None:
        # T5: Non-empty content
        if not ko_content.strip():
            warnings.append("T5 FAIL: Translation file contains only whitespace")

        # T6 & T7 require English source content
        en_content = None
        if en_path and os.path.exists(en_path):
            try:
                with open(en_path, "r", encoding="utf-8") as f:
                    en_content = f.read()
            except (IOError, UnicodeDecodeError) as e:
                warnings.append(
                    f"T6/T7 SKIP: English source exists but unreadable: {e}"
                )

        if en_content is not None and ko_content.strip():
            # T6: Structural completeness
            t6_valid, t6_msg = _check_structural_completeness(en_content, ko_content)
            if not t6_valid:
                warnings.append(t6_msg)

            # T7: Code block preservation
            t7_valid, t7_msg = _check_code_block_preservation(en_content, ko_content)
            if not t7_valid:
                warnings.append(t7_msg)

    is_valid = len(warnings) == 0
    return (is_valid, warnings)


def _check_structural_completeness(en_content, ko_content):
    """T6: Heading count comparison between EN and KO documents.

    P1 Compliance: Regex counting — deterministic.

    Tolerance: KO headings within ±20% of EN count (minimum ±1).
    Minor structural adjustments by translator are acceptable;
    major omissions are not.

    Args:
        en_content: English document content (str)
        ko_content: Korean document content (str)

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    en_headings = len(_HEADING_RE.findall(en_content))
    ko_headings = len(_HEADING_RE.findall(ko_content))

    if en_headings == 0:
        return (True, "T6 SKIP: No headings in English source")

    # ±20% tolerance (minimum ±1 for small documents)
    tolerance = max(1, int(en_headings * 0.2))
    diff = abs(en_headings - ko_headings)

    if diff > tolerance:
        return (
            False,
            f"T6 FAIL: Heading count mismatch — EN={en_headings}, KO={ko_headings} "
            f"(tolerance ±{tolerance})",
        )

    return (True, f"T6 PASS: EN={en_headings}, KO={ko_headings}")


def _check_code_block_preservation(en_content, ko_content):
    """T7: Code block fence count must match exactly between EN and KO.

    P1 Compliance: Regex counting — deterministic.
    Per translator.md: "Code blocks are NEVER translated — Keep all code."
    Triple-backtick fences must be preserved 1:1.

    Args:
        en_content: English document content (str)
        ko_content: Korean document content (str)

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    en_fences = len(_CODE_BLOCK_FENCE_RE.findall(en_content))
    ko_fences = len(_CODE_BLOCK_FENCE_RE.findall(ko_content))

    if en_fences == 0:
        return (True, "T7 SKIP: No code blocks in English source")

    if en_fences != ko_fences:
        return (
            False,
            f"T7 FAIL: Code block fence count mismatch — EN={en_fences}, KO={ko_fences} "
            f"(must be exact match)",
        )

    return (True, f"T7 PASS: {en_fences} code fences preserved")


def check_glossary_freshness(project_dir, step_number):
    """T8: Verify glossary was updated during/after translation.

    P1 Compliance: File timestamp comparison — deterministic.
    Per translator.md protocol: Step 5 (Update Glossary) → Step 6 (Write Output).

    Checks:
      - translations/glossary.yaml exists
      - glossary.yaml was modified within 1 hour of translation file

    Args:
        project_dir: Project root directory path
        step_number: Step number (int) to validate

    Returns:
        tuple: (is_valid: bool, warning: str | None)
        - is_valid: True if glossary is fresh or no translation exists
        - warning: Human-readable issue description, None if valid
    """
    glossary_path = os.path.join(project_dir, "translations", "glossary.yaml")

    if not os.path.exists(glossary_path):
        return (
            False,
            "T8 FAIL: translations/glossary.yaml not found — "
            "translator must create/update glossary (Step 5)",
        )

    # Find translation files for timestamp comparison
    translation_files = _find_translation_files_for_step(project_dir, step_number)
    if not translation_files:
        return (True, None)  # No translation → T8 trivially valid

    try:
        glossary_mtime = os.path.getmtime(glossary_path)
    except OSError:
        return (False, "T8 FAIL: Cannot read glossary.yaml timestamp")

    ko_path = translation_files[0]
    try:
        ko_mtime = os.path.getmtime(ko_path)
    except OSError:
        return (False, f"T8 FAIL: Cannot read translation file timestamp: {ko_path}")

    # Tolerance: glossary should be modified within 1 hour of translation
    # (translator protocol: Step 5 → Step 6, typically within same session)
    staleness = ko_mtime - glossary_mtime
    if staleness > 3600:
        return (
            False,
            f"T8 FAIL: Glossary is stale — modified {staleness:.0f}s before "
            f"translation (max 3600s). Translator may have skipped Step 5.",
        )

    return (True, None)


def verify_pacs_arithmetic(pacs_log_path):
    """T9: Universal pACS arithmetic verification.

    P1 Compliance: Regex + arithmetic — deterministic.
    Applies to ALL pACS log types (general, translation, reviewer).

    Verifies that the reported pACS score equals min(dimension scores).
    This catches AI hallucination where dimension scores are stated but
    min() is calculated incorrectly.

    Strategy:
      1. Prefer explicit min() formula match (e.g., "pACS = min(F,C,L) = 75")
      2. Fallback to simple "pACS = N" if unambiguous (exactly 1 match)
      3. Skip if ambiguous (multiple simple matches without min formula)

    Supports dimension naming patterns:
      - General: F, C, L (Faithfulness, Completeness, Logic)
      - Translation: Ft, Ct, Nt (Fidelity, Completeness, Naturalness)
      - Any single/two-letter uppercase dimension codes

    Ambiguity guard: If the same dimension letter appears with different
    scores (e.g., generator and reviewer tables in same file), verification
    is skipped to avoid false alarms.

    Args:
        pacs_log_path: Absolute path to any pACS log file

    Returns:
        tuple: (is_valid: bool, warning: str | None)
        - is_valid: True if arithmetic is correct or cannot be verified
        - warning: Human-readable issue description, None if valid
    """
    if not os.path.exists(pacs_log_path):
        return (True, None)  # No file → nothing to verify

    try:
        with open(pacs_log_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return (True, None)  # Unreadable → graceful skip

    # --- Extract dimension scores ---
    dims = {}
    seen_dim_scores = {}  # dim -> list of scores (for ambiguity detection)
    for match in _PACS_DIM_UNIVERSAL_RE.finditer(content):
        dim_name = match.group(1)
        dim_score = int(match.group(2))
        if 0 <= dim_score <= 100:
            if dim_name in seen_dim_scores:
                seen_dim_scores[dim_name].append(dim_score)
            else:
                seen_dim_scores[dim_name] = [dim_score]
            dims[dim_name] = dim_score

    if len(dims) < 2:
        return (True, None)  # Not enough dimensions → skip

    # Ambiguity guard: same dimension with different scores → skip
    for scores in seen_dim_scores.values():
        if len(set(scores)) > 1:
            return (True, None)

    # --- Extract reported final score ---
    # Strategy: prefer explicit min() formula over simple "pACS = N"
    min_match = _PACS_WITH_MIN_RE.search(content)
    if min_match:
        reported_score = int(min_match.group(1))
    else:
        # Fallback: simple "pACS = N" (no min formula)
        simple_matches = _PACS_SIMPLE_RE.findall(content)
        if len(simple_matches) == 1:
            reported_score = int(simple_matches[0])
        else:
            return (True, None)  # 0 or multiple → ambiguous → skip

    # --- Verify arithmetic ---
    expected_score = min(dims.values())
    if reported_score != expected_score:
        dim_str = ", ".join(f"{k}={v}" for k, v in sorted(dims.items()))
        return (
            False,
            f"T9 FAIL: pACS arithmetic error in {os.path.basename(pacs_log_path)} — "
            f"reported {reported_score} but min({dim_str}) = {expected_score}",
        )

    return (True, None)


def extract_remediations(warnings, remediations_dict):
    """Central remediation extraction — replaces 7 inline loops across validators.

    P1 Compliance: Deterministic prefix matching + completeness self-check.
    Called by all validate_*.py scripts after validation completes.

    Matches warnings starting with "{CODE} FAIL" to _REMEDIATIONS keys.
    Also performs P1-F completeness self-check: if a FAIL code has no matching
    remediation entry, adds a warning to the returned dict.

    Args:
        warnings: list of warning strings from validator (e.g., ["PA1 FAIL: ..."])
        remediations_dict: dict mapping check codes to fix instructions

    Returns:
        dict: {code: remediation_text, ...} for matched FAIL codes.
              If a FAIL code has no remediation, includes:
              {code: "NO_REMEDIATION: check code '{code}' missing from _REMEDIATIONS"}
    """
    if not warnings or not remediations_dict:
        return {}

    result = {}
    for w in warnings:
        # C-1: Defensive type guard — non-string elements (None, int, etc.) skip
        if not isinstance(w, str) or "FAIL" not in w:
            continue
        matched = False
        for code in remediations_dict:
            if w.startswith(f"{code} FAIL"):
                result[code] = remediations_dict[code]
                matched = True
                break
        # P1-F: Completeness self-check — detect missing remediation entries
        if not matched:
            # Extract the check code prefix (e.g., "PA1" from "PA1 FAIL: ...")
            fail_idx = w.find(" FAIL")
            if fail_idx > 0:
                fail_code = w[:fail_idx].strip()
                # H-2: Only accept valid code format (PA1, T9, V1a, RV1, etc.)
                # Reject multi-word or malformed prefixes
                if (fail_code
                        and re.match(r'^[A-Z]+\d+[a-z]?$', fail_code)
                        and fail_code not in result):
                    result[fail_code] = (
                        f"NO_REMEDIATION: check code '{fail_code}' missing "
                        f"from _REMEDIATIONS — add an entry to the validator script"
                    )
    return result


def validate_pacs_output(project_dir, step_number, pacs_type="general"):
    """PA1-PA7: pACS log structural integrity + arithmetic + RED threshold.

    P1 Compliance: All validation is deterministic (regex + arithmetic).
    SOT Compliance: Read-only — no file writes.

    Checks:
      PA1: pACS log file exists
      PA2: Minimum file size (≥ 50 bytes — pACS logs are concise)
      PA3: Dimension scores present (F/C/L or Ft/Ct/Nt, each 0-100)
      PA4: Pre-mortem section present (mandatory before scoring)
      PA5: pACS = min(dimensions) arithmetic correctness (delegates to verify_pacs_arithmetic)
      PA7: RED threshold — pACS < 50 blocks step advancement (FAIL)

    Optional:
      PA6: Color zone validation — score vs declared zone (RED/YELLOW/GREEN)

    Args:
        project_dir: Absolute path to project root
        step_number: Workflow step number
        pacs_type: "general" | "translation" | "review"
                   Determines expected file name pattern

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
    """
    warnings = []

    # Determine file path based on type
    if pacs_type == "translation":
        pacs_filename = f"step-{step_number}-translation-pacs.md"
    elif pacs_type == "review":
        pacs_filename = f"step-{step_number}-review-pacs.md"
    else:
        pacs_filename = f"step-{step_number}-pacs.md"

    pacs_path = os.path.join(project_dir, "pacs-logs", pacs_filename)

    # PA1: File exists
    if not os.path.exists(pacs_path):
        return (False, [f"PA1 FAIL: pACS log not found: {pacs_filename}"])

    try:
        with open(pacs_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        return (False, [f"PA1 FAIL: Cannot read {pacs_filename}: {e}"])

    # PA2: Minimum size
    if len(content.strip()) < 50:
        warnings.append(f"PA2 FAIL: {pacs_filename} too small ({len(content)} bytes, min 50)")

    # PA3: Dimension scores present (0-100 range)
    dims_found = {}
    for match in _PACS_DIM_UNIVERSAL_RE.finditer(content):
        dim_name = match.group(1)
        dim_score = int(match.group(2))
        if 0 <= dim_score <= 100:
            dims_found[dim_name] = dim_score

    if len(dims_found) < 3:
        warnings.append(
            f"PA3 FAIL: Expected ≥ 3 dimension scores, found {len(dims_found)}: "
            f"{', '.join(f'{k}={v}' for k, v in dims_found.items()) or 'none'}"
        )
    else:
        # PA6 (optional): Color zone validation
        reported_pacs = None
        min_match = _PACS_WITH_MIN_RE.search(content)
        if min_match:
            reported_pacs = int(min_match.group(1))
        else:
            simple_matches = _PACS_SIMPLE_RE.findall(content)
            if len(simple_matches) == 1:
                reported_pacs = int(simple_matches[0])

        if reported_pacs is not None:
            # PA7: RED threshold — score < 50 blocks step advancement
            if reported_pacs < 50:
                warnings.append(
                    f"PA7 FAIL: pACS={reported_pacs} (RED zone, < 50) — "
                    f"rework required before step advancement"
                )

            # PA6 (optional): Check zone consistency
            content_upper = content.upper()
            if reported_pacs < 50 and "GREEN" in content_upper:
                warnings.append(
                    f"PA6 WARN: pACS={reported_pacs} (RED zone) but GREEN declared"
                )
            elif reported_pacs >= 70 and "RED" in content_upper:
                warnings.append(
                    f"PA6 WARN: pACS={reported_pacs} (GREEN zone) but RED declared"
                )

    # PA4: Pre-mortem section present
    _pre_mortem_patterns = [
        "pre-mortem", "Pre-mortem", "Pre-Mortem", "PRE-MORTEM",
        "사전 부검", "pre mortem", "프리모템",
        "what could go wrong", "약점", "weakness", "risk",
    ]
    has_pre_mortem = any(p in content for p in _pre_mortem_patterns)
    if not has_pre_mortem:
        warnings.append(
            "PA4 FAIL: Pre-mortem section not found — mandatory before pACS scoring"
        )

    # PA5: Arithmetic correctness (delegates to verify_pacs_arithmetic)
    arith_valid, arith_warning = verify_pacs_arithmetic(pacs_path)
    if not arith_valid and arith_warning:
        warnings.append(arith_warning)

    # Determine overall validity
    has_fail = any("FAIL" in w for w in warnings)
    return (not has_fail, warnings)


def validate_step_output(project_dir, step_number, sot_data=None):
    """L0 Anti-Skip Guard: Validate step output file exists and meets minimum size.

    P1 Compliance: Deterministic file system checks only.
    SOT Compliance: Read-only — no file writes.

    Called by Orchestrator before advancing current_step.
    This is the code implementation of L0 Anti-Skip Guard,
    previously only a design-level checklist item.

    Checks:
      L0a: Output file exists (path from SOT outputs.step-N)
      L0b: File size ≥ MIN_OUTPUT_SIZE (100 bytes)
      L0c: File is not all whitespace

    Args:
        project_dir: Absolute path to project root
        step_number: Workflow step number to validate
        sot_data: Parsed SOT dict or read_autopilot_state() result (optional).
                  If None, reads SOT from disk.
                  Supports three data shapes:
                    1. read_autopilot_state() result: {"outputs": {"step-1": "path"}, ...}
                    2. Raw SOT (AGENTS.md schema): {"workflow": {"outputs": {"step-1": "path"}}}
                    3. Raw SOT (flat schema): {"outputs": {"step-1": "path"}}

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
    """
    warnings = []

    # Load SOT if not provided
    if sot_data is None:
        for sot_path in sot_paths(project_dir):
            if os.path.exists(sot_path):
                try:
                    import yaml
                    with open(sot_path, "r", encoding="utf-8") as f:
                        sot_data = yaml.safe_load(f) or {}
                    break
                except Exception:
                    pass
        if sot_data is None:
            return (False, ["L0 FAIL: SOT file not found — cannot determine output path"])

    # FIX-R2: Extract outputs — handle both flat and nested SOT schemas
    # Shape 1 (read_autopilot_state / flat): {"outputs": {"step-1": "path"}}
    # Shape 2 (raw YAML nested): {"workflow": {"outputs": {"step-1": "path"}}}
    outputs = sot_data.get("outputs", {})
    if not outputs and isinstance(sot_data.get("workflow"), dict):
        outputs = sot_data["workflow"].get("outputs", {})
    step_key = f"step-{step_number}"
    output_path_raw = outputs.get(step_key)

    if not output_path_raw:
        return (False, [f"L0a FAIL: No output path in SOT outputs.{step_key}"])

    # Resolve relative path
    output_path = os.path.join(project_dir, output_path_raw)

    # L0a: File exists
    if not os.path.exists(output_path):
        return (False, [f"L0a FAIL: Output file not found: {output_path_raw}"])

    # L0b: Minimum size
    try:
        file_size = os.path.getsize(output_path)
    except OSError as e:
        return (False, [f"L0a FAIL: Cannot stat output file: {e}"])

    if file_size < MIN_OUTPUT_SIZE:
        warnings.append(
            f"L0b FAIL: Output file too small ({file_size} bytes, min {MIN_OUTPUT_SIZE}): "
            f"{output_path_raw}"
        )

    # L0c: Not all whitespace
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read(MIN_OUTPUT_SIZE + 10)
        if not content.strip():
            warnings.append(f"L0c FAIL: Output file is empty/whitespace-only: {output_path_raw}")
    except (IOError, UnicodeDecodeError):
        pass  # Binary files are OK (e.g., images)

    has_fail = any("FAIL" in w for w in warnings)
    return (not has_fail, warnings)


def validate_verification_log(project_dir, step_number):
    """V1: Verification log structural integrity (V1a-V1c).

    P1 Compliance: Filesystem + regex — deterministic.
    SOT Compliance: Read-only access to verification-logs/.

    Checks:
      V1a: verification-logs/step-{N}-verify.md exists + size >= MIN_OUTPUT_SIZE
      V1b: Each criterion has explicit PASS/FAIL marking (checklist or table)
      V1c: Logical consistency — if any criterion is FAIL, overall must be FAIL

    Args:
        project_dir: Project root directory path
        step_number: Step number (int) to validate

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
        - is_valid: True only if V1a-V1c pass
        - warnings: List of human-readable failure reasons
    """
    warnings = []
    verify_path = os.path.join(
        project_dir, "verification-logs", f"step-{step_number}-verify.md"
    )

    # V1a: File existence + minimum size
    if not os.path.exists(verify_path):
        warnings.append(
            f"V1a FAIL: verification-logs/step-{step_number}-verify.md not found"
        )
        return (False, warnings)

    try:
        size = os.path.getsize(verify_path)
    except OSError:
        warnings.append(f"V1a FAIL: Cannot read file size: {verify_path}")
        return (False, warnings)

    if size < MIN_OUTPUT_SIZE:
        warnings.append(
            f"V1a FAIL: Verification log too small "
            f"({size} bytes, min {MIN_OUTPUT_SIZE})"
        )

    # Read content for V1b-V1c
    try:
        with open(verify_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        warnings.append(f"V1a FAIL: Cannot read file: {e}")
        return (False, warnings)

    # V1b: Extract per-criterion PASS/FAIL results
    criteria = []
    # Try checklist format: "- [x] Criterion: PASS"
    for match in _VERIFY_CRITERION_CHECKLIST_RE.finditer(content):
        criteria.append({
            "name": match.group(1).strip(),
            "result": match.group(2).upper(),
        })
    # Also try table format: "| Criterion | PASS |"
    for match in _VERIFY_CRITERION_TABLE_RE.finditer(content):
        name = match.group(1).strip()
        # Skip table header and separator rows
        if name.lower().rstrip("-") in _VERIFY_TABLE_HEADER_WORDS:
            continue
        if name.startswith("-"):
            continue
        criteria.append({
            "name": name,
            "result": match.group(2).upper(),
        })

    if not criteria:
        warnings.append(
            "V1b FAIL: No per-criterion PASS/FAIL results found "
            "(expected checklist or table format)"
        )

    # V1c: Logical consistency — any FAIL criterion → overall must be FAIL
    has_individual_fail = any(c["result"] == "FAIL" for c in criteria)
    overall_match = _VERIFY_OVERALL_RE.search(content)
    if overall_match:
        overall_result = overall_match.group(1).upper()
        if has_individual_fail and overall_result == "PASS":
            failed_names = [c["name"] for c in criteria if c["result"] == "FAIL"]
            warnings.append(
                f"V1c FAIL: Logical inconsistency — overall is PASS but "
                f"these criteria are FAIL: {', '.join(failed_names)}"
            )
    elif criteria:
        warnings.append(
            "V1c FAIL: No overall PASS/FAIL result found in verification log"
        )

    is_valid = len(warnings) == 0
    return (is_valid, warnings)


# =============================================================================
# Predictive Debugging: Risk Score Aggregation (P1 — Deterministic)
# =============================================================================

def aggregate_risk_scores(ki_path, project_dir):
    """Aggregate per-file risk scores from knowledge-index.jsonl.

    P1 Compliance: All operations are deterministic arithmetic.
    No semantic inference — pure counting, weighting, and decay.

    Called by: restore_context.py at SessionStart (once per session).
    Output: dict suitable for JSON serialization to risk-scores.json.

    Data flow:
      knowledge-index.jsonl → read entries → extract error_patterns
      → per-file error counting → weight application → recency decay
      → resolution rate calculation → validate → return
    """
    # Read all knowledge-index entries
    entries = []
    if not ki_path or not os.path.exists(ki_path):
        return _empty_risk_data(project_dir)

    try:
        with open(ki_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return _empty_risk_data(project_dir)

    if len(entries) < _RISK_MIN_SESSIONS:
        return _empty_risk_data(project_dir, data_sessions=len(entries))

    # Per-file error accumulation
    # Key: relative path → {error_types: {type: count}, total_weighted: float,
    #                        resolved_count: int, total_count: int, last_error_date: str}
    file_risks = {}
    now_ts = time.time()

    for entry in entries:
        error_patterns = entry.get("error_patterns", [])
        if not isinstance(error_patterns, list):
            continue

        # Parse entry timestamp for recency decay
        entry_ts = entry.get("timestamp", "")
        entry_age_days = _timestamp_to_age_days(entry_ts, now_ts)

        # Determine recency weight
        recency_weight = _RECENCY_DECAY_DAYS[-1][1]  # default: oldest bracket
        for max_days, weight in _RECENCY_DECAY_DAYS:
            if entry_age_days <= max_days:
                recency_weight = weight
                break

        # Get modified files from this session (for file↔error association)
        modified_files = entry.get("modified_files", [])

        for ep in error_patterns:
            if not isinstance(ep, dict):
                continue
            error_type = ep.get("type", "unknown")
            error_file = ep.get("file", "")
            resolution = ep.get("resolution")
            has_resolution = isinstance(resolution, dict) and bool(resolution)

            # Determine which file(s) to attribute the error to
            # Priority: error-specific file > session modified files
            target_files = []
            if error_file:
                target_files = [error_file]
            else:
                # No specific file — attribute to all modified files
                target_files = [os.path.basename(f) for f in modified_files[:5]]

            for tf in target_files:
                # Normalize to relative path
                rel_path = _normalize_to_relative(tf, project_dir, modified_files)
                if not rel_path:
                    continue

                if rel_path not in file_risks:
                    file_risks[rel_path] = {
                        "error_types": {},
                        "total_weighted": 0.0,
                        "resolved_count": 0,
                        "total_count": 0,
                        "last_error_date": "",
                    }

                fr = file_risks[rel_path]
                # Apply type weight × recency weight
                type_weight = _RISK_WEIGHTS.get(error_type, 0.7)
                weighted_score = type_weight * recency_weight
                fr["total_weighted"] += weighted_score
                fr["error_types"][error_type] = fr["error_types"].get(error_type, 0) + 1
                fr["total_count"] += 1
                if has_resolution:
                    fr["resolved_count"] += 1

                # Track most recent error date
                entry_date = entry_ts[:10] if len(entry_ts) >= 10 else ""
                if entry_date > fr["last_error_date"]:
                    fr["last_error_date"] = entry_date

    # P1-FIX: Merge entries with same basename but different paths
    # (bare names like "_context_lib.py" vs relative ".claude/hooks/scripts/_context_lib.py")
    # Keep the longest (most specific) path as canonical key, sum scores.
    basename_groups = {}
    for rel_path, fr in file_risks.items():
        bname = os.path.basename(rel_path)
        if bname not in basename_groups:
            basename_groups[bname] = []
        basename_groups[bname].append((rel_path, fr))

    merged_risks = {}
    for bname, group in basename_groups.items():
        if len(group) == 1:
            merged_risks[group[0][0]] = group[0][1]
        else:
            # Pick longest path as canonical (most specific)
            canonical_path = max(group, key=lambda x: len(x[0]))[0]
            merged = {
                "error_types": {},
                "total_weighted": 0.0,
                "resolved_count": 0,
                "total_count": 0,
                "last_error_date": "",
            }
            for _, fr in group:
                merged["total_weighted"] += fr["total_weighted"]
                merged["total_count"] += fr["total_count"]
                merged["resolved_count"] += fr["resolved_count"]
                for etype, cnt in fr["error_types"].items():
                    merged["error_types"][etype] = (
                        merged["error_types"].get(etype, 0) + cnt
                    )
                if fr["last_error_date"] > merged["last_error_date"]:
                    merged["last_error_date"] = fr["last_error_date"]
            merged_risks[canonical_path] = merged

    # Build output
    files_output = {}
    for rel_path, fr in merged_risks.items():
        resolution_rate = (
            fr["resolved_count"] / fr["total_count"]
            if fr["total_count"] > 0
            else 0.0
        )
        files_output[rel_path] = {
            "risk_score": round(fr["total_weighted"], 2),
            "error_count": fr["total_count"],
            "error_types": fr["error_types"],
            "last_error_session": fr["last_error_date"],
            "resolution_rate": round(resolution_rate, 2),
        }

    # Sort by risk_score descending for top_risk_files
    sorted_files = sorted(
        files_output.keys(),
        key=lambda k: files_output[k]["risk_score"],
        reverse=True,
    )
    top_risk = [
        f for f in sorted_files[:10]
        if files_output[f]["risk_score"] >= _RISK_SCORE_THRESHOLD
    ]

    risk_data = {
        "generated_at": datetime.now().isoformat(),
        "data_sessions": len(entries),
        "project_dir": project_dir,
        "risk_threshold": _RISK_SCORE_THRESHOLD,
        "files": files_output,
        "top_risk_files": top_risk,
    }

    # P1: Self-validation before return
    validation_warnings = validate_risk_scores(risk_data)
    if validation_warnings:
        risk_data["_validation_warnings"] = validation_warnings

    return risk_data


def validate_risk_scores(risk_data):
    """P1 Risk Score Validation (RS1-RS6).

    Deterministic schema enforcement for risk-scores.json.
    Follows the same pattern as validate_sot_schema (S1-S8),
    validate_review_output (R1-R5), validate_translation_output (T1-T7).

    Returns: list of warning strings (empty = all checks pass).
    """
    warnings = []

    if not isinstance(risk_data, dict):
        warnings.append("RS1 FAIL: risk_data is not a dict")
        return warnings

    # RS1: Required top-level keys
    required_keys = {"generated_at", "data_sessions", "files", "top_risk_files", "risk_threshold"}
    missing = required_keys - set(risk_data.keys())
    if missing:
        warnings.append(f"RS1 FAIL: Missing required keys: {missing}")

    # RS2: data_sessions is int >= 0
    ds = risk_data.get("data_sessions")
    if not isinstance(ds, int) or ds < 0:
        warnings.append(f"RS2 FAIL: data_sessions must be int >= 0, got {ds!r}")

    # RS3-RS5: Per-file validation
    files = risk_data.get("files", {})
    if not isinstance(files, dict):
        warnings.append("RS3 FAIL: files must be a dict")
    else:
        for fpath, fdata in files.items():
            if not isinstance(fdata, dict):
                warnings.append(f"RS3 FAIL: files[{fpath!r}] is not a dict")
                continue

            # RS3: risk_score is numeric >= 0
            score = fdata.get("risk_score")
            if not isinstance(score, (int, float)) or score < 0:
                warnings.append(
                    f"RS3 FAIL: files[{fpath!r}].risk_score must be "
                    f"numeric >= 0, got {score!r}"
                )

            # RS4: error_count >= sum(error_types.values())
            ec = fdata.get("error_count", 0)
            et = fdata.get("error_types", {})
            if isinstance(et, dict) and isinstance(ec, int):
                type_sum = sum(
                    v for v in et.values() if isinstance(v, (int, float))
                )
                if ec < type_sum:
                    warnings.append(
                        f"RS4 FAIL: files[{fpath!r}].error_count ({ec}) < "
                        f"sum(error_types) ({type_sum})"
                    )

            # RS5: resolution_rate is float, 0.0 <= rate <= 1.0
            rr = fdata.get("resolution_rate")
            if rr is not None:
                if not isinstance(rr, (int, float)) or rr < 0.0 or rr > 1.0:
                    warnings.append(
                        f"RS5 FAIL: files[{fpath!r}].resolution_rate must be "
                        f"0.0-1.0, got {rr!r}"
                    )

    # RS6: top_risk_files entries exist in files dict and sorted by risk_score desc
    top = risk_data.get("top_risk_files", [])
    if isinstance(top, list) and isinstance(files, dict):
        for tf in top:
            if tf not in files:
                warnings.append(
                    f"RS6 FAIL: top_risk_files entry {tf!r} not found in files"
                )
        # Check sort order
        scores = [
            files.get(tf, {}).get("risk_score", 0)
            for tf in top if tf in files
        ]
        if scores != sorted(scores, reverse=True):
            warnings.append(
                "RS6 FAIL: top_risk_files not sorted by risk_score desc"
            )

    return warnings


def _empty_risk_data(project_dir, data_sessions=0):
    """Return empty risk data structure (cold start / no data)."""
    return {
        "generated_at": datetime.now().isoformat(),
        "data_sessions": data_sessions,
        "project_dir": project_dir,
        "risk_threshold": _RISK_SCORE_THRESHOLD,
        "files": {},
        "top_risk_files": [],
    }


def _timestamp_to_age_days(ts_str, now_ts):
    """Convert ISO timestamp string to age in days.

    P1 Compliance: Deterministic datetime parsing.
    Returns float (days). Returns 365.0 on parse failure (conservative decay).
    """
    if not ts_str:
        return 365.0
    try:
        # Handle both "2026-02-20T15:30:00" and "2026-02-20T153000" formats
        dt = datetime.fromisoformat(
            ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str
        )
        age_seconds = now_ts - dt.timestamp()
        return max(0.0, age_seconds / 86400.0)
    except (ValueError, TypeError, OSError):
        return 365.0  # Conservative: treat unparseable as old


def _normalize_to_relative(filename, project_dir, modified_files):
    """Normalize a filename to project-relative path.

    Strategy:
      1. If filename is a bare name, find full path in modified_files
      2. If filename is absolute and under project_dir, make relative
      3. Otherwise return as-is (best effort)

    P1 Compliance: Deterministic string operations only.
    Returns: relative path string, or empty string on failure.
    """
    if not filename:
        return ""

    # Case 1: Bare filename (no path separator) — find in modified_files
    if not os.path.isabs(filename) and os.sep not in filename:
        for mf in modified_files:
            if os.path.basename(mf) == filename:
                if os.path.isabs(mf) and project_dir:
                    try:
                        return os.path.relpath(mf, project_dir)
                    except ValueError:
                        return mf
                return mf
        return filename  # Return bare filename as-is (best effort)

    # Case 2: Absolute path — make relative to project
    if os.path.isabs(filename) and project_dir:
        try:
            return os.path.relpath(filename, project_dir)
        except ValueError:
            return filename

    return filename


# ---------------------------------------------------------------------------
# Workflow.md DNA Inheritance P1 Validation (W1-W8)
# ---------------------------------------------------------------------------

# Module-level compiled regex for W3/W4 checks (process-lifetime, one-time cost)
_WORKFLOW_INHERITED_DNA_RE = re.compile(
    r"^##\s+Inherited DNA", re.MULTILINE
)
_WORKFLOW_INHERITED_TABLE_RE = re.compile(
    r"Inherited Patterns[^\n]*\n(?:\s*\n)?"  # header line + optional blank
    r"(\|[^\n]+\n)"                           # table header row
    r"(\|[-| :]+\n)"                          # separator row
    r"((?:\|[^\n]+\n)*)",                     # data rows
    re.MULTILINE,
)
_WORKFLOW_CONSTITUTIONAL_RE = re.compile(
    r"Constitutional Principles", re.IGNORECASE
)
_WORKFLOW_CAP_RE = re.compile(
    r"CAP-[1-4]|코딩\s*기준점|Coding\s*Anchor\s*Points", re.IGNORECASE
)
# W7: Cross-step traceability Verification → validate_traceability post-processing
_WORKFLOW_CT_VERIFICATION_RE = re.compile(
    r"교차\s*단계\s*추적성|cross[- ]?step\s*traceability|trace:step-",
    re.IGNORECASE,
)
_WORKFLOW_CT_POSTPROCESS_RE = re.compile(
    r"validate_traceability", re.IGNORECASE,
)
# W8: DKS Verification → validate_domain_knowledge post-processing
_WORKFLOW_DKS_VERIFICATION_RE = re.compile(
    r"domain[- ]?knowledge|도메인\s*지식\s*구조|\[dks:|domain-knowledge\.yaml",
    re.IGNORECASE,
)
_WORKFLOW_DKS_POSTPROCESS_RE = re.compile(
    r"validate_domain_knowledge", re.IGNORECASE,
)


def validate_workflow_md(workflow_path):
    """W1-W8: Generated workflow.md structural integrity for DNA inheritance.

    P1 Compliance: All validation is deterministic (regex + string checks).
    SOT Compliance: Read-only — no file writes.

    Checks:
      W1: Workflow file exists and is readable
      W2: Minimum file size (≥ 500 bytes — workflow files are substantial)
      W3: '## Inherited DNA' header present
      W4: Inherited Patterns table present (≥ 3 data rows)
      W5: Constitutional Principles section present
      W6: Coding Anchor Points (CAP) reference present
      W7: If Verification mentions cross-step traceability, validate_traceability
          post-processing must be present (Verification-Validator consistency)
      W8: If workflow references domain knowledge, validate_domain_knowledge
          post-processing must be present (Verification-Validator consistency)

    Args:
        workflow_path: Absolute path to generated workflow.md

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
    """
    warnings = []

    # W1: File exists
    if not os.path.exists(workflow_path):
        return (False, [f"W1 FAIL: Workflow file not found: {workflow_path}"])

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        return (False, [f"W1 FAIL: Cannot read workflow: {e}"])

    # W2: Minimum size
    if len(content.strip()) < 500:
        warnings.append(
            f"W2 FAIL: Workflow too small ({len(content)} bytes, min 500)"
        )

    # W3: Inherited DNA header
    if not _WORKFLOW_INHERITED_DNA_RE.search(content):
        warnings.append(
            "W3 FAIL: '## Inherited DNA' section not found in workflow"
        )

    # W4: Inherited Patterns table (≥ 3 data rows)
    table_match = _WORKFLOW_INHERITED_TABLE_RE.search(content)
    if table_match:
        data_rows_text = table_match.group(3)
        data_rows = [
            line for line in data_rows_text.split("\n")
            if line.strip().startswith("|")
        ]
        if len(data_rows) < 3:
            warnings.append(
                f"W4 FAIL: Inherited Patterns table has {len(data_rows)} "
                f"data rows, expected ≥ 3"
            )
    else:
        warnings.append("W4 FAIL: Inherited Patterns table not found")

    # W5: Constitutional Principles
    if not _WORKFLOW_CONSTITUTIONAL_RE.search(content):
        warnings.append(
            "W5 FAIL: Constitutional Principles section not found"
        )

    # W6: Coding Anchor Points (CAP) reference
    if not _WORKFLOW_CAP_RE.search(content):
        warnings.append(
            "W6 FAIL: Coding Anchor Points (CAP) reference not found"
        )

    # W7: Verification-Validator consistency — Cross-Step Traceability
    # If any Verification criteria mentions traceability, the workflow must
    # include validate_traceability post-processing to enforce P1 validation.
    if _WORKFLOW_CT_VERIFICATION_RE.search(content):
        if not _WORKFLOW_CT_POSTPROCESS_RE.search(content):
            warnings.append(
                "W7 FAIL: Workflow references cross-step traceability in "
                "Verification criteria but has no validate_traceability.py "
                "Post-processing command"
            )

    # W8: Verification-Validator consistency — Domain Knowledge Structure
    # If the workflow references domain knowledge (DKS), the workflow must
    # include validate_domain_knowledge post-processing.
    if _WORKFLOW_DKS_VERIFICATION_RE.search(content):
        if not _WORKFLOW_DKS_POSTPROCESS_RE.search(content):
            warnings.append(
                "W8 FAIL: Workflow references domain knowledge structure but "
                "has no validate_domain_knowledge.py Post-processing command"
            )

    has_fail = any("FAIL" in w for w in warnings)
    return (not has_fail, warnings)


# ---------------------------------------------------------------------------
# Cross-Step Traceability P1 Validation (CT1-CT5)
# ---------------------------------------------------------------------------

# Module-level compiled regex for trace marker extraction
# Format: [trace:step-N:section-id] or [trace:step-N:section-id:locator]
_TRACE_MARKER_RE = re.compile(
    r'\[trace:step-(\d+):([a-z0-9_-]+)(?::([a-z0-9_-]+))?\]',
    re.IGNORECASE,
)
# Heading extraction for section-id resolution (CT3)
_HEADING_SLUG_RE = re.compile(r'^#+\s+(.+)$', re.MULTILINE)

# Minimum number of trace markers required (CT4)
_MIN_TRACE_MARKERS = 3


def validate_cross_step_traceability(project_dir, step_number, sot_data=None):
    """CT1-CT5: Cross-step traceability structural integrity.

    P1 Compliance: Filesystem + regex — deterministic.
    SOT Compliance: Read-only — reads SOT outputs for path resolution.

    Validates that a step's output contains trace markers referencing
    previous steps, enabling horizontal (cross-step) verification.

    Checks:
      CT1: Trace markers exist in output (>= 1)
      CT2: Referenced step outputs exist on disk (SOT outputs.step-N path)
      CT3: Section IDs resolve to headings in source files (Warning only)
      CT4: Minimum trace marker density (>= MIN_TRACE_MARKERS)
      CT5: No forward references (step-N where N >= current step)

    Args:
        project_dir: Absolute path to project root
        step_number: Current step number being validated
        sot_data: Parsed SOT dict (optional). If None, reads from disk.

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
    """
    warnings = []
    trace_count = 0
    verified_count = 0

    # Load SOT if not provided
    if sot_data is None:
        for sp in sot_paths(project_dir):
            if os.path.exists(sp):
                try:
                    import yaml
                    with open(sp, "r", encoding="utf-8") as f:
                        sot_data = yaml.safe_load(f) or {}
                    break
                except Exception:
                    pass
        if sot_data is None:
            return (False, ["CT FAIL: SOT file not found — cannot resolve output paths"])

    # Extract outputs from SOT (handle nested and flat schemas)
    outputs = sot_data.get("outputs", {})
    if not outputs and isinstance(sot_data.get("workflow"), dict):
        outputs = sot_data["workflow"].get("outputs", {})

    # Step 1 has no previous steps — traceability N/A
    if step_number <= 1:
        return (True, ["CT SKIP: Step 1 has no previous steps — traceability N/A"])

    # Get current step output path
    step_key = f"step-{step_number}"
    output_path_raw = outputs.get(step_key)
    if not output_path_raw:
        return (False, [f"CT FAIL: No output path in SOT outputs.{step_key}"])

    output_path = os.path.join(project_dir, output_path_raw)
    if not os.path.exists(output_path):
        return (False, [f"CT FAIL: Output file not found: {output_path_raw}"])

    # Read output content
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        return (False, [f"CT FAIL: Cannot read output file: {e}"])

    # Extract all trace markers
    markers = _TRACE_MARKER_RE.findall(content)
    trace_count = len(markers)

    # CT1: At least one trace marker must exist
    if trace_count == 0:
        warnings.append("CT1 FAIL: No [trace:step-N:...] markers found in output")
        return (False, warnings)

    # CT4: Minimum density
    if trace_count < _MIN_TRACE_MARKERS:
        warnings.append(
            f"CT4 FAIL: Only {trace_count} trace markers found, "
            f"minimum {_MIN_TRACE_MARKERS} required"
        )

    # Validate each marker
    for ref_step_str, section_id, locator in markers:
        ref_step = int(ref_step_str)

        # CT5: No forward references
        if ref_step >= step_number:
            warnings.append(
                f"CT5 FAIL: Forward reference [trace:step-{ref_step}:...] "
                f"in step {step_number} — must reference earlier steps only"
            )
            continue

        # CT2: Referenced step output exists
        ref_step_key = f"step-{ref_step}"
        ref_output_raw = outputs.get(ref_step_key)
        if not ref_output_raw:
            warnings.append(
                f"CT2 FAIL: Referenced step-{ref_step} has no output in SOT"
            )
            continue

        ref_output_path = os.path.join(project_dir, ref_output_raw)
        if not os.path.exists(ref_output_path):
            warnings.append(
                f"CT2 FAIL: Referenced output file not found: {ref_output_raw}"
            )
            continue

        # CT3: Section ID resolution (Warning only, not FAIL)
        try:
            with open(ref_output_path, "r", encoding="utf-8") as f:
                ref_content = f.read()
            headings = _HEADING_SLUG_RE.findall(ref_content)
            slugified = [_slugify_heading(h) for h in headings]
            if section_id.lower() not in slugified:
                warnings.append(
                    f"CT3 WARNING: Section '{section_id}' not resolved in "
                    f"step-{ref_step} headings (may be a sub-section or ID)"
                )
            else:
                verified_count += 1
        except (IOError, UnicodeDecodeError):
            verified_count += 1  # Can't read = trust the reference

    # Append metadata as info (not FAIL)
    warnings.append(
        f"CT INFO: trace_count={trace_count}, verified_count={verified_count}"
    )

    has_fail = any("FAIL" in w for w in warnings)
    return (not has_fail, warnings)


def _slugify_heading(heading_text):
    """Convert a markdown heading to a slug for section-id matching.

    Matches the trace marker convention: lowercase, alphanumeric + hyphens.
    Strips markdown artifacts: links [text](url) → text, bold/italic markers,
    backticks, and other non-alphanumeric characters.
    """
    slug = heading_text.strip()
    # Remove markdown links: [text](url) → text
    slug = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', slug)
    # Remove inline code backticks
    slug = re.sub(r'`([^`]*)`', r'\1', slug)
    slug = slug.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-')
    return slug


# ---------------------------------------------------------------------------
# Domain Knowledge Structure P1 Validation (DK1-DK7)
# ---------------------------------------------------------------------------

# Module-level compiled regex for DKS reference markers
# Format: [dks:entity-id] or [dks:relation-id]
_DKS_REF_RE = re.compile(r'\[dks:([a-z0-9_-]+)\]', re.IGNORECASE)
# Valid ID format: lowercase letter start, alphanumeric + hyphens + underscores
# Character class MUST match _DKS_REF_RE capture group (D-7: both allow [a-z0-9_-])
_DKS_ID_RE = re.compile(r'^[a-z][a-z0-9_-]*$')


def validate_domain_knowledge(project_dir, check_output_step=None, sot_data=None):
    """DK1-DK7: Domain Knowledge Structure structural integrity.

    P1 Compliance: Filesystem + YAML parse + regex — deterministic.
    SOT Compliance: Read-only — no file writes.

    Validates domain-knowledge.yaml schema and optionally cross-references
    with step output DKS markers.

    Checks:
      DK1: File exists and YAML is valid
      DK2: metadata contains required keys (domain, schema_version)
      DK3: entities structure (id unique + slug format, type string, attributes dict)
      DK4: relations referential integrity (subject/object -> entities.id, confidence valid)
      DK5: constraints structure (id, description, check present)
      DK6: (--check-output) Output DKS markers resolve to entity/relation IDs
      DK7: (--check-output) Constraint non-violation (best-effort numeric check)

    Args:
        project_dir: Absolute path to project root
        check_output_step: Step number to cross-check DKS markers (optional)
        sot_data: Parsed SOT dict (optional). If None, reads from disk.

    Returns:
        tuple: (is_valid: bool, warnings: list[str])
    """
    warnings = []

    dk_path = os.path.join(project_dir, "domain-knowledge.yaml")

    # DK1: File exists and YAML is valid
    if not os.path.exists(dk_path):
        return (False, ["DK1 FAIL: domain-knowledge.yaml not found"])

    try:
        import yaml
        with open(dk_path, "r", encoding="utf-8") as f:
            dk_data = yaml.safe_load(f)
        if not isinstance(dk_data, dict):
            return (False, ["DK1 FAIL: domain-knowledge.yaml is not a valid YAML mapping"])
    except Exception as e:
        return (False, [f"DK1 FAIL: Cannot parse domain-knowledge.yaml: {e}"])

    # DK2: metadata required keys
    metadata = dk_data.get("metadata", {})
    if not isinstance(metadata, dict):
        warnings.append("DK2 FAIL: 'metadata' must be a mapping")
    else:
        for key in ("domain", "schema_version"):
            if key not in metadata:
                warnings.append(f"DK2 FAIL: metadata.{key} is missing")

    # DK3: entities structure
    entities = dk_data.get("entities", [])
    entity_ids = set()
    if not isinstance(entities, list):
        warnings.append("DK3 FAIL: 'entities' must be a list")
        entities = []

    for i, entity in enumerate(entities):
        if not isinstance(entity, dict):
            warnings.append(f"DK3 FAIL: entities[{i}] is not a mapping")
            continue
        eid = entity.get("id")
        if not eid:
            warnings.append(f"DK3 FAIL: entities[{i}] missing 'id'")
        elif not _DKS_ID_RE.match(str(eid)):
            warnings.append(
                f"DK3 FAIL: entities[{i}].id '{eid}' is not valid slug format "
                f"(lowercase letter start, alphanumeric + hyphens)"
            )
        else:
            if eid in entity_ids:
                warnings.append(f"DK3 FAIL: Duplicate entity id '{eid}'")
            entity_ids.add(eid)

        if not isinstance(entity.get("type"), str):
            warnings.append(f"DK3 FAIL: entities[{i}].type must be a string")
        if not isinstance(entity.get("attributes", {}), dict):
            warnings.append(f"DK3 FAIL: entities[{i}].attributes must be a mapping")

    # DK4: relations referential integrity
    relations = dk_data.get("relations", [])
    relation_ids = set()
    valid_confidences = {"high", "medium", "low"}
    if not isinstance(relations, list):
        if relations is not None:
            warnings.append("DK4 FAIL: 'relations' must be a list")
        relations = []

    for i, rel in enumerate(relations):
        if not isinstance(rel, dict):
            warnings.append(f"DK4 FAIL: relations[{i}] is not a mapping")
            continue
        rid = rel.get("id")
        if rid:
            if rid in relation_ids:
                warnings.append(f"DK4 FAIL: Duplicate relation id '{rid}'")
            relation_ids.add(rid)

        subj = rel.get("subject")
        obj = rel.get("object")
        if subj and subj not in entity_ids:
            warnings.append(
                f"DK4 FAIL: relations[{i}].subject '{subj}' not found in entities"
            )
        if obj and obj not in entity_ids:
            warnings.append(
                f"DK4 FAIL: relations[{i}].object '{obj}' not found in entities"
            )
        conf = rel.get("confidence")
        if conf and str(conf).lower() not in valid_confidences:
            warnings.append(
                f"DK4 FAIL: relations[{i}].confidence '{conf}' must be "
                f"high|medium|low"
            )

    # DK5: constraints structure
    constraints = dk_data.get("constraints", [])
    if not isinstance(constraints, list):
        if constraints is not None:
            warnings.append("DK5 FAIL: 'constraints' must be a list")
        constraints = []

    for i, con in enumerate(constraints):
        if not isinstance(con, dict):
            warnings.append(f"DK5 FAIL: constraints[{i}] is not a mapping")
            continue
        for key in ("id", "description", "check"):
            if key not in con:
                warnings.append(f"DK5 FAIL: constraints[{i}] missing '{key}'")

    # DK6 + DK7: Output cross-check (optional)
    if check_output_step is not None:
        _validate_dks_output_refs(
            project_dir, check_output_step, entity_ids, relation_ids,
            constraints, dk_data, sot_data, warnings,
        )

    # Summary info
    warnings.append(
        f"DK INFO: entity_count={len(entity_ids)}, "
        f"relation_count={len(relation_ids)}, "
        f"constraint_count={len(constraints)}"
    )

    has_fail = any("FAIL" in w for w in warnings)
    return (not has_fail, warnings)


def _validate_dks_output_refs(
    project_dir, step_number, entity_ids, relation_ids,
    constraints, dk_data, sot_data, warnings,
):
    """DK6-DK7: Cross-check DKS references in step output.

    DK6: All [dks:xxx] markers resolve to entity or relation IDs.
    DK7: Best-effort numeric constraint validation.
    """
    # Load SOT if not provided
    if sot_data is None:
        for sp in sot_paths(project_dir):
            if os.path.exists(sp):
                try:
                    import yaml
                    with open(sp, "r", encoding="utf-8") as f:
                        sot_data = yaml.safe_load(f) or {}
                    break
                except Exception:
                    pass
        if sot_data is None:
            warnings.append("DK6 SKIP: SOT file not found — cannot resolve output path")
            return

    # Extract outputs from SOT
    outputs = sot_data.get("outputs", {})
    if not outputs and isinstance(sot_data.get("workflow"), dict):
        outputs = sot_data["workflow"].get("outputs", {})

    step_key = f"step-{step_number}"
    output_path_raw = outputs.get(step_key)
    if not output_path_raw:
        warnings.append(f"DK6 SKIP: No output path in SOT outputs.{step_key}")
        return

    output_path = os.path.join(project_dir, output_path_raw)
    if not os.path.exists(output_path):
        warnings.append(f"DK6 SKIP: Output file not found: {output_path_raw}")
        return

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        warnings.append(f"DK6 SKIP: Cannot read output: {e}")
        return

    # DK6: Resolve DKS markers
    all_ids = entity_ids | relation_ids
    dks_refs = _DKS_REF_RE.findall(content)
    unresolved = []
    for ref_id in dks_refs:
        if ref_id.lower() not in {eid.lower() for eid in all_ids}:
            unresolved.append(ref_id)

    if unresolved:
        warnings.append(
            f"DK6 FAIL: Unresolved DKS references: {', '.join(unresolved)}"
        )

    # DK7: Best-effort constraint validation (numeric sum checks)
    entities_list = dk_data.get("entities", []) if dk_data else []
    for con in constraints:
        check_str = str(con.get("check", ""))
        sum_match = re.match(
            r'sum\((\w+)\)\s*<=\s*(\d+(?:\.\d+)?)', check_str
        )
        if sum_match:
            field_name = sum_match.group(1)
            max_val = float(sum_match.group(2))
            total = 0.0
            found_any = False
            for entity in entities_list:
                attrs = entity.get("attributes", {})
                if field_name in attrs:
                    try:
                        val_str = str(attrs[field_name]).replace("%", "").replace("$", "")
                        total += float(val_str)
                        found_any = True
                    except (ValueError, TypeError):
                        pass
            if found_any and total > max_val:
                warnings.append(
                    f"DK7 FAIL: Constraint '{con.get('id', '?')}' violated: "
                    f"sum({field_name})={total} > {max_val}"
                )


# =============================================================================
# Abductive Diagnosis Layer (P1: Deterministic Pre/Post Analysis)
# =============================================================================
# Inserts a 3-step diagnosis (P1 pre-evidence → LLM judgment → P1 post-validation)
# between quality gate FAIL and retry. Existing 4-layer QA is NOT modified.
# SOT Compliance: Read-only access to SOT, verification-logs/, pacs-logs/,
#                 review-logs/, diagnosis-logs/.
# P1 Compliance: All evidence gathering and validation is deterministic.


def diagnose_failure_context(project_dir, step, gate, sot_data=None):
    """Pre-analysis: Gather deterministic evidence bundle for a failed quality gate.

    Called by Orchestrator AFTER a gate FAIL and BEFORE retry.
    Returns a dict with structured evidence for LLM-based hypothesis selection.

    Args:
        project_dir: Project root path.
        step: Step number that failed.
        gate: One of 'verification', 'pacs', 'review'.
        sot_data: Optional pre-loaded SOT dict (avoids re-reading).

    Returns:
        dict with keys: step, gate, retry_history, upstream_evidence,
                        hypothesis_priority, fast_path, raw_evidence.
    """
    retry_history = _gather_retry_history(project_dir, step, gate)
    upstream_evidence = _gather_upstream_evidence(project_dir, step, sot_data)
    hypothesis_priority = _determine_hypothesis_priority(
        retry_history, upstream_evidence, gate
    )
    fast_path = _check_fast_path_eligibility(
        project_dir, step, gate, retry_history, sot_data=sot_data
    )
    raw_evidence = _gather_raw_evidence(project_dir, step, gate)

    return {
        "step": step,
        "gate": gate,
        "retry_history": retry_history,
        "upstream_evidence": upstream_evidence,
        "hypothesis_priority": hypothesis_priority,
        "fast_path": fast_path,
        "raw_evidence": raw_evidence,
    }


def _gather_retry_history(project_dir, step, gate):
    """Read retry counter and previous diagnosis logs for this step+gate.

    Returns:
        dict with keys: retries_used (int), max_retries (int),
                        previous_diagnoses (list of dicts).
    """
    # D-7: Retry limit constants must match validate_retry_budget.py
    # DEFAULT_MAX_RETRIES and ULW_MAX_RETRIES. Change both files together.
    _DEFAULT_MAX_RETRIES = 10
    _ULW_MAX_RETRIES = 15

    result = {
        "retries_used": 0,
        "max_retries": _DEFAULT_MAX_RETRIES,
        "previous_diagnoses": [],
    }

    # Read retry counter
    counter_dir = os.path.join(project_dir, f"{gate}-logs")
    counter_file = os.path.join(counter_dir, f".step-{step}-retry-count")
    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r", encoding="utf-8") as f:
                result["retries_used"] = int(f.read().strip() or "0")
        except (ValueError, OSError):
            pass

    # Detect ULW mode for max_retries adjustment (10 → 15)
    # D-7: ULW detection pattern must match validate_retry_budget.py _ULW_SNAPSHOT_RE
    # and restore_context.py — all use "ULW 상태" section header presence.
    snapshot_path = os.path.join(
        project_dir, ".claude", "context-snapshots", "latest.md"
    )
    if os.path.exists(snapshot_path):
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                content = f.read(8000)  # First 8KB only
            if re.search(r"ULW 상태|Ultrawork Mode State", content):
                result["max_retries"] = _ULW_MAX_RETRIES
        except OSError:
            pass

    # Gather previous diagnosis logs
    diag_dir = os.path.join(project_dir, "diagnosis-logs")
    if os.path.isdir(diag_dir):
        try:
            for fname in sorted(os.listdir(diag_dir)):
                if fname.startswith(f"step-{step}-{gate}-") and fname.endswith(".md"):
                    fpath = os.path.join(diag_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        selected = _DIAG_SELECTED_RE.search(content)
                        result["previous_diagnoses"].append({
                            "file": fname,
                            "selected_hypothesis": selected.group(1).strip() if selected else "unknown",
                        })
                    except OSError:
                        pass
        except OSError:
            pass

    return result


def _gather_upstream_evidence(project_dir, step, sot_data=None):
    """Collect evidence from upstream step outputs referenced by SOT.

    Returns:
        dict with keys: upstream_outputs (list of {step, path, exists, size}),
                        sot_current_step (int), sot_status (str).
    """
    result = {
        "upstream_outputs": [],
        "sot_current_step": step,
        "sot_status": "unknown",
    }

    # Load SOT if not provided
    if sot_data is None:
        sot_data = {}
        try:
            import yaml
            for sp in sot_paths(project_dir):
                if os.path.exists(sp):
                    with open(sp, "r", encoding="utf-8") as f:
                        sot_data = yaml.safe_load(f) or {}
                    break
        except Exception:
            pass

    result["sot_current_step"] = sot_data.get("current_step", step)
    result["sot_status"] = sot_data.get("workflow_status", "unknown")

    # Gather upstream outputs (steps 1..step-1)
    # Guard: YAML `outputs: null` returns None, not {}
    outputs = sot_data.get("outputs") or {}
    for prev_step in range(1, step):
        key = f"step-{prev_step}"
        path_raw = outputs.get(key, "")
        if not path_raw:
            continue
        full_path = os.path.join(project_dir, path_raw)
        result["upstream_outputs"].append({
            "step": prev_step,
            "path": path_raw,
            "exists": os.path.exists(full_path),
            "size": os.path.getsize(full_path) if os.path.exists(full_path) else 0,
        })

    return result


def _determine_hypothesis_priority(retry_history, upstream_evidence, gate):
    """Rule-based hypothesis prioritization based on available evidence.

    Four hypothesis categories (H1, H2, H3, H4):
        H1: Upstream data quality (missing/thin upstream outputs)
        H2: Current step execution gap (most common)
        H3: Criteria interpretation error (rare)
        H4: Capability gap — missing tool, script, or infrastructure

    Returns:
        list of dicts with keys: id (str), label (str), priority (int 1-3),
                                  reason (str).
    """
    hypotheses = []

    # H1: Upstream data quality — check if any upstream output is missing/thin
    thin_upstreams = []
    for uo in upstream_evidence.get("upstream_outputs", []):
        if not uo.get("exists"):
            thin_upstreams.append(f"step-{uo['step']} missing")
        elif uo.get("size", 0) < MIN_OUTPUT_SIZE:
            thin_upstreams.append(f"step-{uo['step']} thin ({uo['size']}B)")

    h1_priority = 1 if thin_upstreams else 3
    hypotheses.append({
        "id": "H1",
        "label": "Upstream data quality issue",
        "priority": h1_priority,
        "reason": "; ".join(thin_upstreams) if thin_upstreams else "All upstream outputs present and adequate",
    })

    # H2: Current step execution gap — most common, default high priority
    prev_diag = retry_history.get("previous_diagnoses", [])
    h2_priority = 2 if prev_diag else 1
    # If previous diagnosis already selected H2, lower priority (try different hypothesis)
    if prev_diag and any(
        d.get("selected_hypothesis", "").startswith("H2") or
        "execution" in d.get("selected_hypothesis", "").lower()
        for d in prev_diag
    ):
        h2_priority = 2

    hypotheses.append({
        "id": "H2",
        "label": "Current step execution gap",
        "priority": h2_priority,
        "reason": f"{len(prev_diag)} previous diagnosis(es)" if prev_diag else "First attempt",
    })

    # H3: Criteria interpretation error — higher priority for review gate
    h3_priority = 2 if gate == "review" else 3
    hypotheses.append({
        "id": "H3",
        "label": "Criteria interpretation error",
        "priority": h3_priority,
        "reason": "Review gate benefits from criteria re-examination" if gate == "review" else "Low prior probability",
    })

    # H4: Capability gap — missing tool, script, or infrastructure
    # Elevated priority when: (a) repeated retries with same H2, (b) error
    # patterns suggest missing commands/tools. OpenAI harness pattern:
    # "build the missing capability rather than retrying manually."
    h4_priority = 3  # default: low
    h2_repeats = sum(
        1 for d in prev_diag
        if d.get("selected_hypothesis", "").startswith("H2")
    )
    if h2_repeats >= 2:
        # Two H2 attempts failed → likely not an execution gap but a missing capability
        h4_priority = 1
    hypotheses.append({
        "id": "H4",
        "label": "Capability gap — missing tool, script, or infrastructure",
        "priority": h4_priority,
        "reason": (
            f"H2 selected {h2_repeats} times without resolution — "
            "consider building missing capability"
            if h2_repeats >= 2
            else "Low prior probability — check after H2 exhausted"
        ),
    })

    # Sort by priority (1 = highest)
    hypotheses.sort(key=lambda h: h["priority"])
    return hypotheses


def _check_fast_path_eligibility(project_dir, step, gate, retry_history,
                                 sot_data=None):
    """Deterministic fast-path checks (FP1-FP3) that skip LLM diagnosis.

    FP1: Missing output file — diagnosis is trivially 'file not generated'.
    FP2: Empty/near-empty output — diagnosis is 'incomplete generation'.
    FP3: Identical retry — same hypothesis selected twice without change.

    Args:
        sot_data: Optional pre-loaded SOT dict (avoids redundant I/O).

    Returns:
        dict with keys: eligible (bool), reason (str), fp_id (str or None).
    """
    result = {"eligible": False, "reason": "", "fp_id": None}

    # FP1: Missing output file for current step
    try:
        if sot_data is None:
            import yaml
            sot_data = {}
            for sp in sot_paths(project_dir):
                if os.path.exists(sp):
                    with open(sp, "r", encoding="utf-8") as f:
                        sot_data = yaml.safe_load(f) or {}
                    break
        # Guard: YAML `outputs: null` returns None, not {}
        outputs = sot_data.get("outputs") or {}
        step_key = f"step-{step}"
        output_path_raw = outputs.get(step_key, "")
        if output_path_raw:
            full_path = os.path.join(project_dir, output_path_raw)
            if not os.path.exists(full_path):
                result["eligible"] = True
                result["reason"] = f"FP1: Output file missing — {output_path_raw}"
                result["fp_id"] = "FP1"
                return result
            # FP2: Empty/near-empty output
            fsize = os.path.getsize(full_path)
            if fsize < MIN_OUTPUT_SIZE:
                result["eligible"] = True
                result["reason"] = f"FP2: Output too small ({fsize}B < {MIN_OUTPUT_SIZE}B)"
                result["fp_id"] = "FP2"
                return result
    except Exception:
        pass

    # FP3: Identical retry — same hypothesis selected in 2+ previous diagnoses
    prev_diag = retry_history.get("previous_diagnoses", [])
    if len(prev_diag) >= 2:
        selected = [d.get("selected_hypothesis", "") for d in prev_diag[-2:]]
        if selected[0] and selected[0] == selected[1]:
            result["eligible"] = True
            result["reason"] = f"FP3: Same hypothesis '{selected[0]}' selected twice — escalate"
            result["fp_id"] = "FP3"
            return result

    return result


def _gather_raw_evidence(project_dir, step, gate):
    """Bundle raw log content for the failing gate.

    Returns:
        dict with keys: gate_log_path (str), gate_log_excerpt (str),
                        pacs_log_excerpt (str or None).
    """
    result = {
        "gate_log_path": "",
        "gate_log_excerpt": "",
        "pacs_log_excerpt": None,
    }

    # Determine log path based on gate type
    if gate == "verification":
        log_path = os.path.join(
            project_dir, "verification-logs", f"step-{step}-verify.md"
        )
    elif gate == "pacs":
        log_path = os.path.join(
            project_dir, "pacs-logs", f"step-{step}-pacs.md"
        )
    elif gate == "review":
        log_path = os.path.join(
            project_dir, "review-logs", f"step-{step}-review.md"
        )
    else:
        return result

    result["gate_log_path"] = log_path
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                # Read only first ERROR_RESULT_CHARS to avoid OOM on large logs
                result["gate_log_excerpt"] = f.read(ERROR_RESULT_CHARS)
        except OSError:
            pass

    # Always include pacs log if available (even for non-pacs gates)
    if gate != "pacs":
        pacs_path = os.path.join(
            project_dir, "pacs-logs", f"step-{step}-pacs.md"
        )
        if os.path.exists(pacs_path):
            try:
                with open(pacs_path, "r", encoding="utf-8") as f:
                    result["pacs_log_excerpt"] = f.read(ERROR_RESULT_CHARS)
            except OSError:
                pass

    return result


def validate_diagnosis_log(project_dir, step, gate):
    """P1 Post-validation: Verify diagnosis log structural integrity (AD1-AD10).

    Called after LLM writes the diagnosis log. All checks are deterministic.

    Args:
        project_dir: Project root path.
        step: Step number.
        gate: One of 'verification', 'pacs', 'review'.

    Returns:
        tuple(is_valid: bool, warnings: list[str])

    Checks:
        AD1: Diagnosis log file exists in diagnosis-logs/
        AD2: Minimum file size (≥ 100 bytes)
        AD3: Gate field matches expected gate
        AD4: Selected hypothesis present (H1/H2/H3/H4)
        AD5: Evidence section present (≥ 1 evidence item)
        AD6: Action plan section present
        AD7: No forward step references (source: Step N where N > step)
        AD8: Hypothesis count ≥ 2 (must consider alternatives)
        AD9: Selected hypothesis is one of the listed hypotheses
        AD10: Previous diagnosis referenced (if retry > 0)
    """
    warnings = []

    # AD1: File exists
    diag_dir = os.path.join(project_dir, "diagnosis-logs")
    # Find the latest diagnosis log for this step+gate
    diag_path = None
    if os.path.isdir(diag_dir):
        candidates = sorted([
            f for f in os.listdir(diag_dir)
            if f.startswith(f"step-{step}-{gate}-") and f.endswith(".md")
        ])
        if candidates:
            diag_path = os.path.join(diag_dir, candidates[-1])

    if not diag_path or not os.path.exists(diag_path):
        warnings.append(
            f"AD1 FAIL: No diagnosis log found for step-{step} gate={gate} "
            f"in diagnosis-logs/"
        )
        return False, warnings

    # Read content
    try:
        with open(diag_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        warnings.append(f"AD1 FAIL: Cannot read diagnosis log — {e}")
        return False, warnings

    # AD2: Minimum size
    if len(content) < 100:
        warnings.append(
            f"AD2 FAIL: Diagnosis log too small ({len(content)}B < 100B)"
        )

    # AD3: Gate field matches
    gate_match = _DIAG_GATE_RE.search(content)
    if gate_match:
        found_gate = gate_match.group(1).lower()
        if found_gate != gate.lower():
            warnings.append(
                f"AD3 FAIL: Gate mismatch — expected '{gate}', found '{found_gate}'"
            )
    else:
        warnings.append("AD3 FAIL: No Gate field found in diagnosis log")

    # AD4: Selected hypothesis present
    selected_match = _DIAG_SELECTED_RE.search(content)
    if not selected_match:
        warnings.append("AD4 FAIL: No selected hypothesis found")

    # AD5: Evidence items (≥ 1)
    evidence_items = _DIAG_EVIDENCE_RE.findall(content)
    if len(evidence_items) < 1:
        warnings.append(
            f"AD5 FAIL: Insufficient evidence items ({len(evidence_items)} < 1)"
        )

    # AD6: Action plan section
    action_plan_re = re.compile(
        r"^#+\s*(?:Action\s*Plan|Recommended\s*Action|Next\s*Steps?)\b",
        re.MULTILINE | re.IGNORECASE,
    )
    if not action_plan_re.search(content):
        warnings.append("AD6 FAIL: No Action Plan section found")

    # AD7: No forward step references
    source_refs = _DIAG_SOURCE_STEP_RE.findall(content)
    for ref_step_str in source_refs:
        ref_step = int(ref_step_str)
        if ref_step > step:
            warnings.append(
                f"AD7 FAIL: Forward reference to Step {ref_step} (current: {step})"
            )

    # AD8: Hypothesis count ≥ 2
    hypotheses_found = _DIAG_HYPOTHESIS_RE.findall(content)
    if len(hypotheses_found) < 2:
        warnings.append(
            f"AD8 FAIL: Insufficient hypotheses ({len(hypotheses_found)} < 2)"
        )

    # AD9: Selected hypothesis is one of the listed ones
    # Extract H-IDs only from hypothesis headings (not from arbitrary body text)
    if selected_match and hypotheses_found:
        listed_h_ids = set()
        for h_text in hypotheses_found:
            h_id_match = re.search(r"\bH[1-4]\b", h_text)
            if h_id_match:
                listed_h_ids.add(h_id_match.group())
        selected_h_id = re.search(
            r"\bH[1-4]\b", selected_match.group(1).strip()
        )
        if selected_h_id and selected_h_id.group() not in listed_h_ids:
            warnings.append(
                f"AD9 FAIL: Selected hypothesis '{selected_h_id.group()}' "
                f"not found among listed hypotheses {listed_h_ids}"
            )

    # AD10: Previous diagnosis referenced (if retry > 0)
    retry_history = _gather_retry_history(project_dir, step, gate)
    if retry_history["retries_used"] > 0 and retry_history["previous_diagnoses"]:
        prev_ref_re = re.compile(
            r"(?:previous|prior|earlier)\s+(?:diagnosis|attempt|retry)",
            re.IGNORECASE,
        )
        if not prev_ref_re.search(content):
            warnings.append(
                "AD10 WARNING: No reference to previous diagnosis "
                f"(retry #{retry_history['retries_used']})"
            )

    # Determine overall validity (any FAIL → invalid)
    is_valid = not any("FAIL" in w for w in warnings)
    return is_valid, warnings


def _extract_diagnosis_patterns(project_dir):
    """Extract diagnosis patterns from diagnosis-logs/ for Knowledge Archive.

    Scans diagnosis-logs/ for completed diagnosis files and extracts
    step, gate, selected_hypothesis, and evidence summary.

    Returns:
        list of dicts with keys: step, gate, selected_hypothesis, evidence_count.
    """
    patterns = []
    diag_dir = os.path.join(project_dir, "diagnosis-logs")
    if not os.path.isdir(diag_dir):
        return patterns

    try:
        for fname in sorted(os.listdir(diag_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(diag_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract step and gate from filename: step-N-gate-timestamp.md
                parts = fname.replace(".md", "").split("-")
                step_num = None
                gate_name = None
                for i, p in enumerate(parts):
                    if p == "step" and i + 1 < len(parts):
                        try:
                            step_num = int(parts[i + 1])
                        except ValueError:
                            pass
                    if p in ("verification", "pacs", "review"):
                        gate_name = p

                selected = _DIAG_SELECTED_RE.search(content)
                evidence_items = _DIAG_EVIDENCE_RE.findall(content)

                patterns.append({
                    "step": step_num,
                    "gate": gate_name,
                    "selected_hypothesis": (
                        selected.group(1).strip() if selected else "unknown"
                    ),
                    "evidence_count": len(evidence_items),
                })
            except OSError:
                pass
    except OSError:
        pass

    return patterns