#!/usr/bin/env python3
"""
Context Parsing Module — Transcript JSONL parsing and deterministic fact extraction.

Functions:
  - parse_transcript(path) → list[dict]
  - _parse_user_entry(obj, timestamp) → list[dict]
  - _parse_assistant_entry(obj, timestamp) → list[dict]
  - _extract_tool_use_summary(tool_name, input) → str
  - _extract_tool_result_summary(content) → str

Exports constants:
  - EDIT_PREVIEW_CHARS, ERROR_RESULT_CHARS, NORMAL_RESULT_CHARS, etc.
"""


import json
import os
import re
from pathlib import Path

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


# =============================================================================
# Constants
# =============================================================================

# Token estimation: mixed Korean/English content ≈ 2.5 chars/token
CHARS_PER_TOKEN = 2.5
# Claude's context window (200K tokens)
CONTEXT_WINDOW_TOKENS = 200_000
# System prompt overhead estimate (tokens)
SYSTEM_OVERHEAD_TOKENS = 15_000
# Effective capacity
EFFECTIVE_CAPACITY = CONTEXT_WINDOW_TOKENS - SYSTEM_OVERHEAD_TOKENS
# 75% threshold
THRESHOLD_75_TOKENS = int(EFFECTIVE_CAPACITY * 0.75)
# Snapshot size target (characters) — Quality First (Absolute Criteria 1)
# Read tool handles up to 2000 lines. 100KB preserves decision context.
MAX_SNAPSHOT_CHARS = 100_000
# Dedup guard window (seconds) — reduced to avoid missing rapid changes
DEDUP_WINDOW_SECONDS = 5
# Stop hook uses wider window to reduce noise (~60→~10 saves/hour)
STOP_DEDUP_WINDOW_SECONDS = 30
# Max snapshots to retain per trigger type
MAX_SNAPSHOTS = {
    "precompact": 3,
    "sessionend": 3,
    "threshold": 2,
    "stop": 5,
}
DEFAULT_MAX_SNAPSHOTS = 3
# Knowledge Archive limits (Area 1: Cross-Session Knowledge Archive)
MAX_KNOWLEDGE_INDEX_ENTRIES = 200
MAX_SESSION_ARCHIVES = 20
# E5 Empty Snapshot Guard — section header constants
# These constants are the single definition for section headers used in both
# generate_snapshot_md() and is_rich_snapshot(). Changing a constant here
# automatically updates both the snapshot generator and the E5 Guard detector.
E5_RICH_CONTENT_MARKER = "### Files Being Edited"
E5_COMPLETION_STATE_MARKER = "## Deterministic Completion State"
E5_DESIGN_DECISIONS_MARKER = "## Key Design Decisions"
# A1: Multi-signal rich content markers for E5 Guard
# is_rich_snapshot() checks `marker in content` (substring match).
E5_RICH_SIGNALS = [
    E5_RICH_CONTENT_MARKER,         # "### Files Being Edited"
    E5_COMPLETION_STATE_MARKER,     # "## Deterministic Completion State"
    E5_DESIGN_DECISIONS_MARKER,     # "## Key Design Decisions"
]

# --- Truncation limits (Quality First — Absolute Criteria 1) ---
# Edit preview: enough to understand "why" the edit was made
EDIT_PREVIEW_CHARS = 1000
# Error result: preserve full error message (stack trace + context)
ERROR_RESULT_CHARS = 3000
# Normal tool result — Bash output, test results, execution context
NORMAL_RESULT_CHARS = 1500
# Write preview — enough to understand file intent (first ~8 lines)
WRITE_PREVIEW_CHARS = 500
# Generic tool input preview
GENERIC_INPUT_CHARS = 200
# Bash command preview
BASH_CMD_CHARS = 200
# Task prompt preview
TASK_PROMPT_CHARS = 200
# SOT content capture
SOT_CAPTURE_CHARS = 3000
# Anti-Skip Guard minimum output size (bytes)
MIN_OUTPUT_SIZE = 100


# =============================================================================
# Transcript Parsing
# =============================================================================

def parse_transcript(transcript_path):
    """
    Parse a Claude Code transcript JSONL file into structured entries.

    Returns list of dicts with keys:
        - type: 'user_message', 'assistant_text', 'tool_use', 'tool_result'
        - timestamp: ISO string
        - content: extracted content (varies by type)
        - file_path: (tool_use only, Write/Edit) deterministic file path
        - line_count: (tool_use only, Write) number of lines
    """
    entries = []
    if not transcript_path or not os.path.exists(transcript_path):
        return entries

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = obj.get("type")
                timestamp = obj.get("timestamp", "")

                if entry_type == "user":
                    entries.extend(_parse_user_entry(obj, timestamp))
                elif entry_type == "assistant":
                    entries.extend(_parse_assistant_entry(obj, timestamp))
                # Skip: progress, file-history-snapshot, system
    except Exception:
        pass

    return entries


def _parse_user_entry(obj, timestamp):
    """Extract user messages and tool results from user-type entries."""
    results = []
    message = obj.get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        # Plain text user message
        text = content.strip()
        if text and not text.startswith("<local-command-"):
            results.append({
                "type": "user_message",
                "timestamp": timestamp,
                "content": text,
            })
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")

            if block_type == "text":
                text = block.get("text", "").strip()
                if text and not text.startswith("<local-command-"):
                    results.append({
                        "type": "user_message",
                        "timestamp": timestamp,
                        "content": text,
                    })

            elif block_type == "tool_result":
                tool_content = block.get("content", "")
                is_error = block.get("is_error", False)
                summary = _extract_tool_result_summary(tool_content)
                if summary:
                    results.append({
                        "type": "tool_result",
                        "timestamp": timestamp,
                        "tool_use_id": block.get("tool_use_id", ""),
                        "is_error": is_error,
                        "content": summary,
                    })

    return results


def _parse_assistant_entry(obj, timestamp):
    """Extract assistant text and tool uses from assistant-type entries.

    For tool_use entries, structured metadata (file_path, line_count) is
    extracted directly from tool_input — NOT parsed from summary strings.
    This ensures 100% deterministic, accurate file operation tracking.
    """
    results = []
    message = obj.get("message", {})
    content = message.get("content", [])

    if isinstance(content, str):
        text = content.strip()
        if text:
            results.append({
                "type": "assistant_text",
                "timestamp": timestamp,
                "content": _truncate(text, 5000),
            })
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")

            if block_type == "text":
                text = block.get("text", "").strip()
                if text:
                    results.append({
                        "type": "assistant_text",
                        "timestamp": timestamp,
                        "content": _truncate(text, 5000),
                    })

            elif block_type == "tool_use":
                tool_name = block.get("name", "unknown")
                tool_input = block.get("input", {})
                summary = _extract_tool_use_summary(tool_name, tool_input)

                entry = {
                    "type": "tool_use",
                    "timestamp": timestamp,
                    "tool_name": tool_name,
                    "tool_use_id": block.get("id", ""),
                    "content": summary,
                }

                # Structured metadata — deterministic, no string parsing
                if tool_name == "Write":
                    entry["file_path"] = tool_input.get("file_path", "")
                    file_content = tool_input.get("content", "")
                    entry["line_count"] = len(file_content.split("\n")) if file_content else 0
                elif tool_name == "Edit":
                    entry["file_path"] = tool_input.get("file_path", "")
                elif tool_name == "Bash":
                    entry["command"] = tool_input.get("command", "")
                    entry["description"] = tool_input.get("description", "")
                elif tool_name == "Read":
                    entry["file_path"] = tool_input.get("file_path", "")

                results.append(entry)

    return results


# =============================================================================
# Extraction Rules (per-tool summarization)
# =============================================================================

def _extract_tool_use_summary(tool_name, tool_input):
    """Apply per-tool extraction rules to keep snapshots compact."""
    if tool_name in ("Write",):
        path = tool_input.get("file_path", "unknown")
        content = tool_input.get("content", "")
        lines = content.split("\n")
        preview = "\n".join(lines[:3])
        return f"Write → {path} ({len(lines)} lines)\n  Preview: {_truncate(preview, WRITE_PREVIEW_CHARS)}"

    elif tool_name in ("Edit",):
        path = tool_input.get("file_path", "unknown")
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        # B-1: First 5 lines × EDIT_PREVIEW_CHARS — preserve intent + context of "why" edit was made
        old_preview = "\n".join(old.split("\n")[:5]) if old else ""
        new_preview = "\n".join(new.split("\n")[:5]) if new else ""
        return (f"Edit → {path}\n"
                f"  OLD: {_truncate(old_preview, EDIT_PREVIEW_CHARS)}\n"
                f"  NEW: {_truncate(new_preview, EDIT_PREVIEW_CHARS)}")

    elif tool_name in ("Read",):
        path = tool_input.get("file_path", "unknown")
        return f"Read → {path}"

    elif tool_name in ("Bash",):
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        return f"Bash: {_truncate(cmd, BASH_CMD_CHARS)}" + (f" ({desc})" if desc else "")

    elif tool_name in ("Task",):
        desc = tool_input.get("description", "")
        prompt = tool_input.get("prompt", "")
        agent_type = tool_input.get("subagent_type", "")
        return f"Task ({agent_type}): {desc}\n  Prompt: {_truncate(prompt, TASK_PROMPT_CHARS)}"

    elif tool_name in ("Glob",):
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"Glob: {pattern}" + (f" in {path}" if path else "")

    elif tool_name in ("Grep",):
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        return f"Grep: {pattern}" + (f" in {path}" if path else "")

    elif tool_name in ("WebSearch",):
        query = tool_input.get("query", "")
        return f"WebSearch: {query}"

    elif tool_name in ("WebFetch",):
        url = tool_input.get("url", "")
        return f"WebFetch: {_truncate(url, 100)}"

    else:
        # Generic: show first GENERIC_INPUT_CHARS of input
        return f"{tool_name}: {_truncate(json.dumps(tool_input, ensure_ascii=False), GENERIC_INPUT_CHARS)}"


def _extract_tool_result_summary(content):
    """Extract summary from tool_result content.

    C-3: Error recovery narrative — error-containing results get expanded
    truncation limit (ERROR_RESULT_CHARS) to preserve diagnostic context.
    """
    _ERROR_PATTERNS = ("error", "Error", "ERROR", "failed", "Failed", "FAILED",
                       "traceback", "Traceback", "exception", "Exception")

    def _limit_for(text):
        if any(pat in text for pat in _ERROR_PATTERNS):
            return ERROR_RESULT_CHARS  # B-2: preserve full error message (stack trace included)
        return NORMAL_RESULT_CHARS

    if isinstance(content, str):
        return _truncate(content, _limit_for(content))
    elif isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        combined = "\n".join(texts)
        return _truncate(combined, _limit_for(combined))
    return ""

