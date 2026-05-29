#!/usr/bin/env python3
"""
Context Preservation Library — Compatibility Layer

This module re-exports all functions from the 4 specialized sub-modules for
backward compatibility. Existing code using:
  from _context_lib import X
will continue to work without changes.

For new code, consider importing from the specialized modules directly:
  from _context_parsing import parse_transcript
  from _context_state_management import capture_sot
  from _context_snapshot_generation import generate_snapshot_md
  from _context_file_operations import atomic_write
"""

# Re-export all public functions and constants from sub-modules
from _context_parsing import (
    parse_transcript,
    CHARS_PER_TOKEN,
    CONTEXT_WINDOW_TOKENS,
    SYSTEM_OVERHEAD_TOKENS,
    EFFECTIVE_CAPACITY,
    THRESHOLD_75_TOKENS,
    MAX_SNAPSHOT_CHARS,
    DEDUP_WINDOW_SECONDS,
    STOP_DEDUP_WINDOW_SECONDS,
    MAX_SNAPSHOTS,
    DEFAULT_MAX_SNAPSHOTS,
    MAX_KNOWLEDGE_INDEX_ENTRIES,
    MAX_SESSION_ARCHIVES,
    E5_RICH_CONTENT_MARKER,
    E5_COMPLETION_STATE_MARKER,
    E5_DESIGN_DECISIONS_MARKER,
    E5_RICH_SIGNALS,
    EDIT_PREVIEW_CHARS,
    ERROR_RESULT_CHARS,
    NORMAL_RESULT_CHARS,
    WRITE_PREVIEW_CHARS,
    GENERIC_INPUT_CHARS,
    BASH_CMD_CHARS,
    TASK_PROMPT_CHARS,
    SOT_CAPTURE_CHARS,
    MIN_OUTPUT_SIZE,
)

from _context_state_management import (
    sot_paths,
    SOT_FILENAMES,
    capture_sot,
    read_autopilot_state,
    validate_sot_schema,
    read_active_team_state,
    detect_ulw_mode,
    check_ulw_compliance,
    capture_git_state,
    extract_completion_state,
    detect_conversation_phase,
    detect_phase_transitions,
    TOOL_ERROR_PATTERNS,
)

from _context_snapshot_generation import (
    generate_snapshot_md,
    _extract_decisions,
)

from _context_file_operations import (
    estimate_tokens,
    atomic_write,
    append_with_lock,
    load_work_log,
    should_skip_save,
    cleanup_snapshots,
)

# For compatibility, also export private functions that may be used internally
from _context_parsing import (
    _parse_user_entry,
    _parse_assistant_entry,
    _extract_tool_use_summary,
    _extract_tool_result_summary,
    _truncate,
)

from _context_state_management import (
    _extract_file_from_nearby_tool_use,
    _classify_phase,
    _get_per_file_diff_stats,
    _extract_next_step,
)

from _context_snapshot_generation import (
    _extract_file_operations,
    _extract_read_operations,
    _compress_snapshot,
    _dedup_sections,
    _compress_section_entries,
    _emit_compressed_entries,
    _remove_section,
    _compress_responses,
    _structure_aware_compress_line,
    _append_compression_audit,
    _get_file_size,
    archive_and_index_session,
    update_latest_with_guard,
    read_stdin_json,
    get_snapshot_dir,
)

from _context_file_operations import (
    _truncate,  # Re-imported for compatibility
)

__all__ = [
    # Core parsing
    'parse_transcript',
    'capture_sot',
    'read_autopilot_state',
    'generate_snapshot_md',
    'estimate_tokens',
    'atomic_write',
    'append_with_lock',
    'cleanup_snapshots',
    # State inspection
    'sot_paths',
    'read_active_team_state',
    'detect_ulw_mode',
    'check_ulw_compliance',
    'detect_conversation_phase',
    'detect_phase_transitions',
    'extract_completion_state',
    # Constants
    'SOT_FILENAMES',
    'MAX_SNAPSHOT_CHARS',
    'TOOL_ERROR_PATTERNS',
]
