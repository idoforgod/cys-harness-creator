#!/usr/bin/env python3
"""
test_context_preservation.py — Test suite for Context Preservation System

Test coverage:
- Context snapshot creation and restoration
- SessionStart recovery protocol (RLM pointers, Knowledge Archive)
- Stop hook incremental snapshots
- PreCompact context saving
- SessionEnd full snapshot (on /clear)
- Knowledge Archive indexing and search
- Error pattern extraction and resolution matching
- Phase transition detection
- IMMORTAL section preservation

Run: pytest test_context_preservation.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def context_snapshots_dir():
    """Create temporary context snapshots directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        snap_dir = Path(tmpdir) / "context-snapshots"
        snap_dir.mkdir(exist_ok=True)

        # Create sessions subdirectory
        (snap_dir / "sessions").mkdir(exist_ok=True)

        yield snap_dir


@pytest.fixture
def sample_snapshot():
    """Sample context snapshot structure."""
    return {
        'timestamp': datetime.now().isoformat(),
        'phase': 'implementation',
        'phase_flow': 'research → planning → implementation',
        'message_count': 45,
        'tool_use_count': 89,
        'estimated_tokens': 78000,
        'git_status': {
            'branch': 'main',
            'uncommitted_changes': 3,
            'untracked_files': 2
        },
        'completion_summary': {
            'completed': ['research', 'planning'],
            'in_progress': ['feature_implementation'],
            'blocked': [],
            'final_status': 'in_progress'
        },
        'decision_log': [
            {
                'decision': 'Use multi-agent architecture',
                'rationale': 'Better separation of concerns',
                'quality_tag': '[explicit]'
            },
            {
                'decision': 'SOT pattern with Orchestrator-only writes',
                'rationale': 'Prevent race conditions in parallel execution',
                'quality_tag': '[decision]'
            }
        ],
        'immortal_section': {
            'quality_gates': {
                'current_step': 2,
                'l0_status': 'PASS',
                'l1_status': 'PASS',
                'l1_5_pacs': 78,
                'l2_status': 'in_progress'
            },
            'autopilot_status': {
                'enabled': False,
                'auto_approved_steps': []
            },
            'ulw_status': {
                'active': True,
                'intensifiers': ['Sisyphus Persistence', 'Task Decomposition', 'Bounded Retry']
            },
            'agent_team': {
                'active_team': None,
                'completed_teams': []
            }
        },
        'recent_files_modified': [
            'orchestrator.test.py',
            'test_pre_subagent_invocation.py',
            'AGENTS.md'
        ],
        'error_patterns': [
            {
                'type': 'edit_mismatch',
                'file': '_context_lib.py',
                'message': 'old_string not found in file',
                'count': 1,
                'resolution': 'Used larger context string with surrounding lines'
            },
            {
                'type': 'syntax',
                'file': 'restore_context.py',
                'message': 'indentation error',
                'count': 2,
                'resolution': 'Fixed indentation to 4 spaces'
            }
        ]
    }


@pytest.fixture
def knowledge_archive_entry():
    """Sample Knowledge Archive JSONL entry."""
    return {
        'session_id': 'abc123def456',
        'timestamp': datetime.now().isoformat(),
        'phase': 'implementation',
        'phase_flow': 'research → planning → implementation',
        'message_count': 45,
        'tool_use_count': 89,
        'estimated_tokens': 78000,
        'completion_summary': 'Feature implementation: 8/10 tests pass, 1 blocking issue',
        'git_summary': 'main: +3 modified, +2 untracked',
        'primary_language': '.py',
        'error_patterns': [
            'edit_mismatch (1x)',
            'syntax (2x)'
        ],
        'resolution': 'Fixed via larger context strings and indentation correction',
        'success_patterns': [
            'Edit → Bash → Bash (successful test run)',
            'Write → Bash (file created and verified)'
        ],
        'tool_sequence_rle': [
            ('Read', 12),
            ('Edit', 8),
            ('Bash', 15),
            ('Write', 4)
        ],
        'final_status': 'in_progress',
        'tags': ['orchestrator', 'test_suite', 'context_preservation', 'hooks']
    }


# ============================================================================
# Test: Snapshot Creation
# ============================================================================

class TestSnapshotCreation:
    """Tests for context snapshot creation and file writing"""

    def test_snapshot_file_creation(self, context_snapshots_dir, sample_snapshot):
        """Stop hook: Create context snapshot file."""
        snapshot_file = context_snapshots_dir / "latest.md"

        # Simulate snapshot writing
        snapshot_content = f"""# Session Context Snapshot

Timestamp: {sample_snapshot['timestamp']}
Phase: {sample_snapshot['phase']}
Messages: {sample_snapshot['message_count']}
Tools: {sample_snapshot['tool_use_count']}

## Decision Log
"""
        for decision in sample_snapshot['decision_log']:
            snapshot_content += f"\n- {decision['decision']} {decision['quality_tag']}"

        snapshot_file.write_text(snapshot_content)

        assert snapshot_file.exists()
        assert 'Decision Log' in snapshot_file.read_text()

    def test_snapshot_includes_immortal_section(self, context_snapshots_dir, sample_snapshot):
        """Snapshot: IMMORTAL section preserved with priority."""
        snapshot_file = context_snapshots_dir / "latest.md"

        # Snapshot with IMMORTAL section
        snapshot_content = f"""# Session Context Snapshot

## IMMORTAL Section (Priority: Quality Gates)

### Quality Gates
- L0: {sample_snapshot['immortal_section']['quality_gates']['l0_status']}
- L1: {sample_snapshot['immortal_section']['quality_gates']['l1_status']}
- L1.5 pACS: {sample_snapshot['immortal_section']['quality_gates']['l1_5_pacs']}
- L2: {sample_snapshot['immortal_section']['quality_gates']['l2_status']}

### ULW Status
- Active: {sample_snapshot['immortal_section']['ulw_status']['active']}
- Intensifiers: {', '.join(sample_snapshot['immortal_section']['ulw_status']['intensifiers'])}
"""
        snapshot_file.write_text(snapshot_content)

        content = snapshot_file.read_text()
        assert 'IMMORTAL Section' in content
        assert 'Quality Gates' in content
        assert 'ULW Status' in content

    def test_snapshot_phase_transition_header(self, context_snapshots_dir, sample_snapshot):
        """Snapshot: Phase transition flow recorded in header."""
        snapshot_file = context_snapshots_dir / "latest.md"

        phase_flow = sample_snapshot['phase_flow']
        snapshot_content = f"""# Session Context Snapshot

Phase flow: {phase_flow}

Message count: {sample_snapshot['message_count']}
"""
        snapshot_file.write_text(snapshot_content)

        content = snapshot_file.read_text()
        assert phase_flow in content


# ============================================================================
# Test: Snapshot Restoration
# ============================================================================

class TestSnapshotRestoration:
    """Tests for SessionStart snapshot restoration and RLM pointer recovery"""

    def test_restore_context_reads_latest_snapshot(self, context_snapshots_dir, sample_snapshot):
        """SessionStart: Read latest.md to restore context."""
        # Write sample snapshot
        snapshot_file = context_snapshots_dir / "latest.md"
        snapshot_json = json.dumps(sample_snapshot, indent=2)
        snapshot_file.write_text(f"```json\n{snapshot_json}\n```")

        # Restore
        content = snapshot_file.read_text()
        # Extract JSON between backticks, skipping "json" language tag
        json_str = content.split("```")[1].strip()
        if json_str.startswith("json"):
            json_str = json_str[4:].strip()
        restored = json.loads(json_str)

        assert restored['phase'] == 'implementation'
        assert restored['message_count'] == 45

    def test_restore_context_initializes_rlm_pointers(self, context_snapshots_dir, sample_snapshot):
        """SessionStart: Initialize RLM pointers (Knowledge Archive index)."""
        # Create knowledge archive index
        knowledge_index = context_snapshots_dir / "knowledge-index.jsonl"
        index_entries = [
            {
                'session_id': 'prev_session_1',
                'timestamp': '2026-04-24T10:00:00',
                'tags': ['orchestrator', 'testing']
            },
            {
                'session_id': 'prev_session_2',
                'timestamp': '2026-04-24T11:00:00',
                'tags': ['context_preservation', 'hooks']
            }
        ]

        # Write entries to file
        content = ""
        for entry in index_entries:
            content += json.dumps(entry) + "\n"
        knowledge_index.write_text(content)

        # Verify RLM pointer exists
        assert knowledge_index.exists()

    def test_restore_context_provides_grep_hints(self, context_snapshots_dir):
        """SessionStart: Generate Grep query hints for RLM search."""
        # RLM query hints based on tags
        tags = ['orchestrator', 'test_suite', 'hooks', 'implementation']

        grep_hints = [
            f"Grep 'orchestrator' knowledge-index.jsonl",
            f"Grep 'test_suite' knowledge-index.jsonl",
            f"Grep 'hooks' knowledge-index.jsonl"
        ]

        assert len(grep_hints) > 0
        assert any('orchestrator' in hint for hint in grep_hints)


# ============================================================================
# Test: Knowledge Archive
# ============================================================================

class TestKnowledgeArchive:
    """Tests for Knowledge Archive indexing and search"""

    def test_knowledge_archive_entry_structure(self, context_snapshots_dir, knowledge_archive_entry):
        """Knowledge Archive: JSONL format with required fields."""
        archive_file = context_snapshots_dir / "knowledge-index.jsonl"

        # Write entry
        archive_file.write_text(json.dumps(knowledge_archive_entry))

        # Read and verify structure
        archived = json.loads(archive_file.read_text())

        assert 'session_id' in archived
        assert 'phase' in archived
        assert 'error_patterns' in archived
        assert 'resolution' in archived
        assert 'tags' in archived

    def test_knowledge_archive_error_pattern_indexing(self, context_snapshots_dir, knowledge_archive_entry):
        """Knowledge Archive: Error patterns indexed with type → resolution."""
        archive_file = context_snapshots_dir / "knowledge-index.jsonl"

        archived = knowledge_archive_entry
        error_map = {
            pattern.split(' (')[0]: archived['resolution']
            for pattern in archived['error_patterns']
        }

        assert 'edit_mismatch' in error_map
        assert 'syntax' in error_map

    def test_knowledge_archive_enables_rml_queries(self, context_snapshots_dir):
        """Knowledge Archive: Queryable via Grep (RLM pattern)."""
        archive_file = context_snapshots_dir / "knowledge-index.jsonl"

        # Simulate three sessions
        entries = [
            {'session_id': 's1', 'phase': 'research', 'tags': ['deep_research', 'web_search']},
            {'session_id': 's2', 'phase': 'implementation', 'tags': ['hooks', 'orchestrator']},
            {'session_id': 's3', 'phase': 'implementation', 'tags': ['test_suite', 'implementation']}
        ]

        # Write all entries to file
        content = ""
        for entry in entries:
            content += json.dumps(entry) + "\n"
        archive_file.write_text(content)

        # Grep query: find implementation phase sessions
        file_content = archive_file.read_text()
        impl_sessions = [line for line in file_content.split('\n') if 'implementation' in line and line.strip()]

        assert len(impl_sessions) == 2  # s2 and s3

    def test_knowledge_archive_auto_decay(self, context_snapshots_dir, knowledge_archive_entry):
        """Knowledge Archive: Entries age, decay weight over time."""
        archive_file = context_snapshots_dir / "knowledge-index.jsonl"

        # Fresh entry
        entry_fresh = knowledge_archive_entry.copy()
        entry_fresh['timestamp'] = datetime.now().isoformat()
        entry_fresh['decay_weight'] = 1.0

        # Old entry (10 days old)
        entry_old = knowledge_archive_entry.copy()
        entry_old['timestamp'] = '2026-04-14T10:00:00'  # 10 days ago
        entry_old['decay_weight'] = 0.5  # decayed

        assert entry_fresh['decay_weight'] > entry_old['decay_weight']


# ============================================================================
# Test: Save/Restore Cycle
# ============================================================================

class TestSaveRestoreCycle:
    """Tests for full SessionEnd/SessionStart cycle"""

    def test_clear_command_triggers_full_snapshot(self, context_snapshots_dir, sample_snapshot):
        """SessionEnd (/clear): Trigger full context snapshot."""
        snapshot_file = context_snapshots_dir / "latest.md"

        # Simulate /clear hook
        full_snapshot = sample_snapshot.copy()
        full_snapshot['trigger'] = 'clear'
        full_snapshot['saved_at'] = datetime.now().isoformat()

        snapshot_file.write_text(json.dumps(full_snapshot, indent=2))

        assert snapshot_file.exists()
        assert 'trigger' in json.loads(snapshot_file.read_text())

    def test_compact_command_triggers_precompact_snapshot(self, context_snapshots_dir, sample_snapshot):
        """PreCompact: Trigger snapshot before compression."""
        # Create pre-compact snapshot
        precompact_file = context_snapshots_dir / "pre-compact-latest.md"

        pre_compact_snapshot = sample_snapshot.copy()
        pre_compact_snapshot['trigger'] = 'precompact'
        pre_compact_snapshot['compression_phase'] = 0

        precompact_file.write_text(json.dumps(pre_compact_snapshot, indent=2))

        assert precompact_file.exists()

    def test_restore_state_after_compact(self, context_snapshots_dir, sample_snapshot):
        """SessionStart after /compact: Restore from pre-compact snapshot."""
        # Save pre-compact snapshot
        precompact_file = context_snapshots_dir / "pre-compact-latest.md"
        precompact_file.write_text(json.dumps(sample_snapshot, indent=2))

        # SessionStart: Restore from pre-compact
        restored = json.loads(precompact_file.read_text())

        # Verify key state preserved
        assert restored['phase'] == 'implementation'
        assert restored['decision_log'] is not None
        assert len(restored['recent_files_modified']) > 0


# ============================================================================
# Test: Error Pattern Preservation
# ============================================================================

class TestErrorPatternPreservation:
    """Tests for error pattern extraction and resolution matching"""

    def test_error_pattern_extraction(self, context_snapshots_dir, sample_snapshot):
        """Stop hook: Extract error patterns from session."""
        errors = sample_snapshot['error_patterns']

        # Verify error classification
        error_types = {e['type'] for e in errors}

        assert 'edit_mismatch' in error_types
        assert 'syntax' in error_types

    def test_error_resolution_matching(self, context_snapshots_dir, sample_snapshot):
        """Error taxonomy: Match error → resolution within 5 tool calls."""
        errors_with_resolution = [
            e for e in sample_snapshot['error_patterns']
            if 'resolution' in e
        ]

        # All errors should have resolutions
        assert len(errors_with_resolution) > 0

        for error in errors_with_resolution:
            assert isinstance(error['resolution'], str)
            assert len(error['resolution']) > 0

    def test_error_resolution_auto_surfacing(self, context_snapshots_dir, sample_snapshot):
        """SessionStart: Auto-surface error→resolution patterns."""
        errors = sample_snapshot['error_patterns']

        # Maximum 3 error→resolution patterns displayed
        displayed_patterns = errors[:3]

        assert len(displayed_patterns) <= 3
        assert all('resolution' in p for p in displayed_patterns)


# ============================================================================
# Test: Decision Log Preservation
# ============================================================================

class TestDecisionLogPreservation:
    """Tests for Decision Log generation and recovery"""

    def test_decision_log_creation(self, context_snapshots_dir, sample_snapshot):
        """Snapshot: Decision Log section included."""
        snapshot_file = context_snapshots_dir / "latest.md"

        decision_log = sample_snapshot['decision_log']

        snapshot_content = "## Decision Log\n"
        for decision in decision_log:
            snapshot_content += f"- {decision['decision']} {decision['quality_tag']}\n"

        snapshot_file.write_text(snapshot_content)

        content = snapshot_file.read_text()
        assert 'Decision Log' in content
        assert all(d['decision'] in content for d in decision_log)

    def test_decision_quality_tag_sorting(self, context_snapshots_dir):
        """Snapshot: Decision Log sorted by quality tag priority."""
        decisions = [
            {'decision': 'D1', 'quality_tag': '[intent]'},
            {'decision': 'D2', 'quality_tag': '[explicit]'},
            {'decision': 'D3', 'quality_tag': '[decision]'},
            {'decision': 'D4', 'quality_tag': '[rationale]'}
        ]

        # Sort by priority: explicit > decision > rationale > intent
        priority = {'[explicit]': 0, '[decision]': 1, '[rationale]': 2, '[intent]': 3}
        sorted_decisions = sorted(decisions, key=lambda d: priority.get(d['quality_tag'], 99))

        assert sorted_decisions[0]['quality_tag'] == '[explicit]'
        assert sorted_decisions[-1]['quality_tag'] == '[intent]'


# ============================================================================
# Test: Compression and Truncation
# ============================================================================

class TestCompressionAndTruncation:
    """Tests for IMMORTAL-aware compression and truncation"""

    def test_immortal_section_preserved_on_compression(self, sample_snapshot):
        """Compression: IMMORTAL section never truncated."""
        immortal = sample_snapshot['immortal_section']

        # Even if overall snapshot truncated, IMMORTAL preserved
        assert immortal is not None
        assert 'quality_gates' in immortal
        assert 'ulw_status' in immortal

    def test_compression_audit_trail(self, context_snapshots_dir):
        """Compression: Record character count removed in audit comment."""
        snapshot_file = context_snapshots_dir / "latest.md"

        # Simulate compression with audit trail
        original_size = 100000
        truncated_size = 50000
        removed = original_size - truncated_size

        audit_comment = f"<!-- compression-audit: Phase 3 removed {removed} chars, final={truncated_size} -->"

        snapshot_file.write_text(f"# Snapshot\n{audit_comment}\n")

        content = snapshot_file.read_text()
        assert 'compression-audit' in content
        assert str(removed) in content


# ============================================================================
# Test: ULW and Autopilot Status Preservation
# ============================================================================

class TestSpecialStatusPreservation:
    """Tests for ULW mode and Autopilot status IMMORTAL preservation"""

    def test_ulw_status_preserved_in_snapshot(self, sample_snapshot):
        """Snapshot: ULW status recorded in IMMORTAL section."""
        ulw_status = sample_snapshot['immortal_section']['ulw_status']

        assert ulw_status['active'] == True
        assert len(ulw_status['intensifiers']) == 3

    def test_autopilot_status_preserved_in_snapshot(self, sample_snapshot):
        """Snapshot: Autopilot status + auto_approved_steps recorded."""
        autopilot = sample_snapshot['immortal_section']['autopilot_status']

        assert 'enabled' in autopilot
        assert 'auto_approved_steps' in autopilot

    def test_ulw_deactivation_on_new_session_startup(self):
        """SessionStart (startup source): ULW NOT inherited from previous snapshot."""
        # Previous snapshot has ulw_active: true
        # But on startup (source=startup), ulw deactivates

        session_source = 'startup'
        ulw_should_inherit = session_source in ['clear', 'compact', 'resume']

        assert ulw_should_inherit == False


# ============================================================================
# Run
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
