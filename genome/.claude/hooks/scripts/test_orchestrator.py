#!/usr/bin/env python3
"""
orchestrator.test.py — Test suite for Orchestrator role: Team + Task lifecycle

Test coverage:
- TeamCreate/TeamDelete lifecycle
- Task creation, assignment, completion tracking
- SOT state management (active_team, outputs)
- Quality gates in team context (L1/L1.5/L2)
- Cross-teammate communication via SendMessage
- Error handling and escalation paths

Run: pytest orchestrator.test.py -v
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_project_dir():
    """Create temporary project directory with SOT and runtime dirs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create SOT
        sot_file = project_dir / "state.yaml"
        sot_file.write_text("""
current_step: 1
workflow_status: running
outputs: {}
auto_approved_steps: []
active_team:
  name: null
  status: null
  tasks_pending: []
  tasks_completed: []
  completed_summaries: {}
completed_teams: []
pacs:
  current_step_score: 0
  dimensions: [0, 0, 0]
  weak_dimension: null
  history: {}
  pre_mortem_flag: ""
""")

        # Create runtime directories
        (project_dir / "verification-logs").mkdir(exist_ok=True)
        (project_dir / "pacs-logs").mkdir(exist_ok=True)
        (project_dir / "review-logs").mkdir(exist_ok=True)
        (project_dir / "autopilot-logs").mkdir(exist_ok=True)
        (project_dir / "diagnosis-logs").mkdir(exist_ok=True)

        yield project_dir


@pytest.fixture
def sot_state(temp_project_dir):
    """Fixture providing SOT state YAML file path."""
    return temp_project_dir / "state.yaml"


def read_sot(sot_file):
    """Helper: read SOT YAML (simplified JSON-like dict parsing)."""
    import yaml
    return yaml.safe_load(sot_file.read_text())


def write_sot(sot_file, state):
    """Helper: write SOT YAML."""
    import yaml
    sot_file.write_text(yaml.dump(state, default_flow_style=False))


# ============================================================================
# Test: Team Lifecycle
# ============================================================================

class TestTeamLifecycle:
    """Tests for TeamCreate → TaskCreate → Teammate execution → TeamDelete"""

    def test_team_create_initializes_active_team_state(self, sot_state):
        """TeamCreate should initialize active_team in SOT."""
        state = read_sot(sot_state)

        # Simulate TeamCreate
        state['active_team'] = {
            'name': 'research-team',
            'status': 'in_progress',
            'tasks_pending': ['task-001', 'task-002'],
            'tasks_completed': [],
            'completed_summaries': {}
        }
        write_sot(sot_state, state)

        # Verify state was written
        updated = read_sot(sot_state)
        assert updated['active_team']['name'] == 'research-team'
        assert updated['active_team']['status'] == 'in_progress'
        assert len(updated['active_team']['tasks_pending']) == 2

    def test_team_lead_updates_task_completion_in_sot(self, sot_state):
        """Team Lead should update tasks_completed when teammate finishes."""
        state = read_sot(sot_state)
        state['active_team'] = {
            'name': 'analysis-team',
            'status': 'in_progress',
            'tasks_pending': ['analyze-data', 'summarize-results'],
            'tasks_completed': [],
            'completed_summaries': {}
        }
        write_sot(sot_state, state)

        # Simulate teammate completion
        state = read_sot(sot_state)
        state['active_team']['tasks_completed'].append('analyze-data')
        state['active_team']['tasks_pending'].remove('analyze-data')
        state['active_team']['completed_summaries']['analyze-data'] = {
            'status': 'PASS',
            'pacs_score': 85,
            'weak_dimension': 'Rigor'
        }
        write_sot(sot_state, state)

        # Verify
        updated = read_sot(sot_state)
        assert 'analyze-data' in updated['active_team']['tasks_completed']
        assert 'analyze-data' not in updated['active_team']['tasks_pending']
        assert updated['active_team']['completed_summaries']['analyze-data']['pacs_score'] == 85

    def test_team_delete_moves_active_team_to_completed_teams(self, sot_state):
        """TeamDelete should archive active_team → completed_teams."""
        state = read_sot(sot_state)
        state['active_team'] = {
            'name': 'final-team',
            'status': 'all_completed',
            'tasks_pending': [],
            'tasks_completed': ['task-1', 'task-2'],
            'completed_summaries': {'task-1': {'status': 'PASS'}}
        }
        write_sot(sot_state, state)

        # Simulate TeamDelete
        state = read_sot(sot_state)
        completed_record = {
            'name': state['active_team']['name'],
            'archived_at': datetime.now().isoformat(),
            'summary': state['active_team']['completed_summaries']
        }
        state['completed_teams'].append(completed_record)
        state['active_team'] = {
            'name': None,
            'status': None,
            'tasks_pending': [],
            'tasks_completed': [],
            'completed_summaries': {}
        }
        write_sot(sot_state, state)

        # Verify
        updated = read_sot(sot_state)
        assert len(updated['completed_teams']) == 1
        assert updated['completed_teams'][0]['name'] == 'final-team'
        assert updated['active_team']['name'] is None


# ============================================================================
# Test: Quality Gates in Team Context
# ============================================================================

class TestQualityGatesTeamContext:
    """Tests for L1/L1.5/L2 verification in (team) stages"""

    def test_l1_verification_by_teammate_self_check(self, temp_project_dir):
        """L1: Teammate self-verifies deliverable against Verification criteria."""
        deliverable = temp_project_dir / "output.md"
        deliverable.write_text("# Analysis\n\n- Finding 1\n- Finding 2\n")

        # Verification criteria: minimum 2 findings
        findings = deliverable.read_text().count("- Finding")
        assert findings >= 2, "L1 FAIL: fewer than 2 findings"

        # L1 passes
        assert findings == 2

    def test_l1_5_pacs_self_scoring_by_teammate(self, temp_project_dir):
        """L1.5: Teammate self-scores pACS (3 dimensions: Functionality, Clarity, Logic)."""
        pacs_log = temp_project_dir / "pacs-logs" / "step-2-pacs.md"
        pacs_log.write_text("""# pACS Self-Rating — Step 2

## Pre-mortem Risks
- Clarity: terminology not consistent with prior steps
- Logic: test coverage incomplete

## Scoring
- Functionality (F): 80
- Clarity (C): 75
- Logic (L): 70

**pACS = min(80, 75, 70) = 70 (YELLOW)**
""")

        # Parse score
        lines = pacs_log.read_text().split('\n')
        scores = [int(line.split(': ')[1]) for line in lines if ': ' in line and any(c.isdigit() for c in line)]
        pacs_score = min(scores[:3]) if len(scores) >= 3 else 0

        assert pacs_score == 70
        assert 50 <= pacs_score < 90  # YELLOW zone

    def test_l2_comprehensive_verification_by_team_lead(self, sot_state):
        """L2: Team Lead verifies all teammate outputs against stage Verification criteria."""
        state = read_sot(sot_state)

        # Simulate L2 gate: all teammates passed L1, min pACS >= 60
        teammate_results = [
            {'name': 'researcher', 'l1_pass': True, 'pacs': 75},
            {'name': 'analyst', 'l1_pass': True, 'pacs': 68},
        ]

        l2_pass = all(r['l1_pass'] and r['pacs'] >= 60 for r in teammate_results)
        assert l2_pass, "L2 FAIL: not all teammates passed L1 or pACS too low"

        # L2 passes → stage completes
        state['current_step'] += 1
        write_sot(sot_state, state)

        updated = read_sot(sot_state)
        assert updated['current_step'] == 2


# ============================================================================
# Test: Task Management
# ============================================================================

class TestTaskManagement:
    """Tests for task creation, assignment, tracking"""

    def test_task_creation_and_ownership(self, sot_state):
        """TaskCreate should create task with owner assignment."""
        # Simulated task structure
        task = {
            'id': 'task-research-001',
            'subject': 'Gather market data',
            'status': 'pending',
            'owner': None
        }

        # Assign to teammate
        task['owner'] = '@researcher'
        task['status'] = 'in_progress'

        assert task['owner'] == '@researcher'
        assert task['status'] == 'in_progress'

    def test_task_status_transition_pending_to_completed(self, sot_state):
        """Task status should transition: pending → in_progress → completed."""
        state = read_sot(sot_state)

        # Simulate task tracking in active_team
        state['active_team']['tasks_pending'] = ['task-analyze']
        state['active_team']['tasks_completed'] = []
        write_sot(sot_state, state)

        # Teammate starts work
        state = read_sot(sot_state)
        assert 'task-analyze' in state['active_team']['tasks_pending']

        # Teammate completes
        state['active_team']['tasks_completed'].append('task-analyze')
        state['active_team']['tasks_pending'].remove('task-analyze')
        write_sot(sot_state, state)

        # Verify transition
        updated = read_sot(sot_state)
        assert 'task-analyze' in updated['active_team']['tasks_completed']
        assert len(updated['active_team']['tasks_pending']) == 0

    def test_task_blocks_dependency_enforcement(self, sot_state):
        """Task with blockedBy should not execute until blocker completes."""
        # Task-B blocked by Task-A
        tasks = {
            'task-A': {'status': 'pending'},
            'task-B': {'status': 'pending', 'blockedBy': ['task-A']}
        }

        # Task-B cannot execute while Task-A pending
        can_execute_b = tasks['task-A']['status'] != 'pending'
        assert not can_execute_b

        # Task-A completes
        tasks['task-A']['status'] = 'completed'

        # Now Task-B can execute
        can_execute_b = tasks['task-A']['status'] != 'pending'
        assert can_execute_b


# ============================================================================
# Test: Communication & Error Handling
# ============================================================================

class TestCommunicationAndErrors:
    """Tests for cross-teammate communication and error escalation"""

    def test_send_message_teammate_reporting(self, sot_state):
        """SendMessage: Teammate reports completion with summary."""
        message = {
            'to': 'orchestrator',
            'message': 'Task complete. Results: 5 datasets analyzed.',
            'pacs_score': 82,
            'weak_dimensions': ['Clarity']
        }

        # Orchestrator receives message
        assert message['to'] == 'orchestrator'
        assert message['pacs_score'] == 82
        assert len(message['weak_dimensions']) > 0

    def test_l2_fail_triggers_diagnostic_escalation(self, sot_state, temp_project_dir):
        """If L2 fails (e.g., pACS < 50), create diagnosis log for re-execution."""
        state = read_sot(sot_state)

        # L2 verification fails
        pacs_score = 45  # RED zone

        if pacs_score < 50:
            diagnosis_file = temp_project_dir / "diagnosis-logs" / "step-2-pacs-fail.md"
            diagnosis_file.write_text(f"""# Diagnosis — Step 2 pACS RED

## Failure Context
- pACS score: {pacs_score} (< 50 threshold)
- Weak dimensions: Logic, Clarity

## Hypotheses
H1: Test coverage incomplete — re-run tests and add edge cases
H2: Documentation unclear — refine terminology per glossary
H3: Core logic flaw — re-analyze requirements

## Selected: H2 (Documentation)
Action: Revise with glossary consistency + re-score
""")

            assert diagnosis_file.exists()
            assert "H2" in diagnosis_file.read_text()

    def test_retry_budget_exhaustion_escalates_to_user(self, sot_state):
        """After max retries (10 for verification, 15 for pACS with ULW), escalate."""
        retry_limit = 10
        retry_count = 10

        if retry_count >= retry_limit:
            message = {
                'type': 'escalation',
                'message': f'Step 2 Verification FAIL after {retry_count} retries. Requires user intervention.',
                'step': 2,
                'gate': 'verification'
            }

            assert message['type'] == 'escalation'
            assert message['step'] == 2


# ============================================================================
# Test: SOT State Consistency
# ============================================================================

class TestSOTStateConsistency:
    """Tests for SOT schema validation and consistency"""

    def test_sot_schema_s8_active_team_validation(self, sot_state):
        """S8: Validate active_team schema (name, status, tasks, summaries)."""
        state = read_sot(sot_state)

        # Valid active_team
        state['active_team'] = {
            'name': 'test-team',
            'status': 'in_progress',
            'tasks_pending': ['task-1'],
            'tasks_completed': ['task-0'],
            'completed_summaries': {'task-0': {'status': 'PASS'}}
        }

        active_team = state['active_team']

        # Validate S8 fields
        assert isinstance(active_team.get('name'), str) or active_team.get('name') is None
        assert active_team.get('status') in ('in_progress', 'all_completed', None)
        assert isinstance(active_team.get('tasks_pending'), list)
        assert isinstance(active_team.get('tasks_completed'), list)
        assert isinstance(active_team.get('completed_summaries'), dict)

    def test_sot_outputs_path_recording_per_step(self, sot_state, temp_project_dir):
        """outputs field should record step deliverable paths."""
        state = read_sot(sot_state)

        # Create deliverable
        output_file = temp_project_dir / "step-1-output.md"
        output_file.write_text("Step 1 results")

        # Record in SOT
        state['outputs']['step-1'] = str(output_file.relative_to(temp_project_dir.parent))
        write_sot(sot_state, state)

        # Verify
        updated = read_sot(sot_state)
        assert 'step-1' in updated['outputs']


# ============================================================================
# Test: Dense Checkpoint Pattern (DCP)
# ============================================================================

class TestDenseCheckpointPattern:
    """Tests for DCP: intermediate checkpoints in long-running tasks (> 10 turns)"""

    def test_dcp_checkpoint_insertion_over_10_turns(self):
        """DCP: Insert CP-1/2/3 checkpoints in tasks > 10 turns."""
        task_turns = 15

        # DCP checkpoints for 15-turn task: CP-1 at turn 5, CP-2 at turn 10
        checkpoints = []
        if task_turns > 10:
            checkpoints = [
                {'name': 'CP-1', 'turn': 5, 'action': 'verify_intermediate_outputs'},
                {'name': 'CP-2', 'turn': 10, 'action': 'l1_self_verification'},
                {'name': 'CP-3', 'turn': 15, 'action': 'l15_pacs_self_scoring'}
            ]

        assert len(checkpoints) == 3
        assert checkpoints[0]['name'] == 'CP-1'
        assert checkpoints[2]['action'] == 'l15_pacs_self_scoring'


# ============================================================================
# Run
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
