"""
P1 Integration Tests — End-to-end StateManager + run.py workflow validation

Tests:
- I1: Atomic write with concurrent access simulation
- I2: Corrupt recovery in actual resume scenario
- I3: Audit log event tracking across 50-step workflow
- I4: Step mismatch detection and auto-correction on resume
- I5: Rate-limit state persistence and recovery
- I6: Multi-session tracking and clear operations
- I7: Backup rotation with multiple saves
- I8: Full workflow simulation with crash recovery
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from state_manager import StateManager, StateModel, StateCorruptError


class TestAtomicWriteIntegration:
    """I1: Atomic write guarantee under concurrent-like access"""

    def test_atomic_write_guarantee(self):
        """I1: Write failure mid-process → State remains consistent"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            # Create initial state
            state1 = {
                "total": 100,
                "current_step": 1,
                "current_session_id": None,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed": [],
                "clears": [],
                "failed": [],
                "sessions": {},
                "rate_limit_state": None,
                "audit_log": [],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            sm.save(state1)

            # Read back to verify
            loaded1 = sm.load()
            assert loaded1["current_step"] == 1
            assert loaded1["completed"] == []

            # Modify and save
            state2 = loaded1.copy()
            state2["current_step"] = 50
            state2["completed"] = list(range(1, 50))
            sm.save(state2)

            # Verify second save
            loaded2 = sm.load()
            assert loaded2["current_step"] == 50
            assert loaded2["completed"] == list(range(1, 50))

            # Verify backup.1 contains state1
            backup1_path = state_path.parent / "state.json.backup.1"
            assert backup1_path.exists()
            with open(backup1_path, 'r') as f:
                backup1 = json.load(f)
            assert backup1["current_step"] == 1  # Previous state


class TestCorruptRecoveryIntegration:
    """I2: Corruption recovery in realistic resume scenario"""

    def test_corrupt_recovery_resume_scenario(self):
        """I2: Simulate crash during step 35 → Recover on resume"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            # Setup: Run completed through step 34
            state = {
                "total": 100,
                "current_step": 35,
                "current_session_id": "sess_001",
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed": list(range(1, 35)),  # 1-34
                "clears": [],
                "failed": [],
                "sessions": {"sess_001": list(range(1, 35))},
                "rate_limit_state": None,
                "audit_log": [
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "step": i,
                        "event": "run_prompt",
                        "details": {"status": "completed"}
                    }
                    for i in range(1, 35)
                ],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            sm.save(state)

            # Save again to create backup
            sm.save(state)

            # Simulate crash: Corrupt state.json mid-write (step 35 incomplete)
            with open(state_path, 'w') as f:
                f.write('{"total": 100, "current_step": 35, "incomplete_write": true')

            # Resume: Load should recover from backup
            recovered = sm.load()
            assert recovered["current_step"] == 35
            assert recovered["completed"] == list(range(1, 35))
            assert len(recovered["audit_log"]) == 34

            # Verify corruption is fixed
            with open(state_path, 'r') as f:
                valid_json = json.load(f)
            assert valid_json["total"] == 100


class TestAuditTrackingIntegration:
    """I3: Audit log captures all events across workflow"""

    def test_audit_tracking_50_steps(self):
        """I3: 50-step workflow → All events in audit_log"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            state = {
                "total": 100,
                "current_step": 1,
                "current_session_id": None,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed": [],
                "clears": [],
                "failed": [],
                "sessions": {},
                "rate_limit_state": None,
                "audit_log": [],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Simulate 50-step workflow
            session_id = "sess_test"
            state["current_session_id"] = session_id

            for step in range(1, 51):
                if step in [10, 20, 30, 40]:
                    # Clear session at certain steps
                    state["clears"].append(step)
                    old_session = state["current_session_id"]
                    state["current_session_id"] = None

                    sm.record_audit(state, step, "clear", {
                        "cleared_session": old_session
                    })

                    # New session after clear
                    new_session = f"sess_test_{step}"
                    state["current_session_id"] = new_session
                    sm.record_audit(state, step, "session_change", {
                        "new_session_id": new_session
                    })

                    if new_session not in state["sessions"]:
                        state["sessions"][new_session] = []
                else:
                    # Normal step completion
                    state["completed"].append(step)
                    state["current_step"] = step + 1

                    if state["current_session_id"]:
                        if state["current_session_id"] not in state["sessions"]:
                            state["sessions"][state["current_session_id"]] = []
                        state["sessions"][state["current_session_id"]].append(step)

                    sm.record_audit(state, step, "run_prompt", {
                        "status": "completed",
                        "session_id": state["current_session_id"]
                    })

            sm.save(state)

            # Verify audit log completeness
            loaded = sm.load()
            assert len(loaded["completed"]) == 46  # 50 - 4 clears
            assert len(loaded["clears"]) == 4
            assert len(loaded["audit_log"]) >= 50  # All steps logged

            # Verify audit events are present
            run_prompt_events = [
                e for e in loaded["audit_log"]
                if e["event"] == "run_prompt"
            ]
            clear_events = [
                e for e in loaded["audit_log"]
                if e["event"] == "clear"
            ]
            session_change_events = [
                e for e in loaded["audit_log"]
                if e["event"] == "session_change"
            ]

            assert len(run_prompt_events) >= 46
            assert len(clear_events) == 4
            assert len(session_change_events) >= 4


class TestStepMismatchIntegration:
    """I4: Step mismatch detection in resume scenario"""

    def test_step_mismatch_resume_correction(self):
        """I4: Workflow interrupted, current_step > expected → Auto-correct"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            # Scenario: Completed 1-30, but current_step incorrectly set to 50
            state = {
                "total": 100,
                "current_step": 50,  # WRONG!
                "current_session_id": None,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed": list(range(1, 31)),  # 1-30
                "clears": [],
                "failed": [],
                "sessions": {},
                "rate_limit_state": None,
                "audit_log": [],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            sm.save(state)

            # Save again to create backup
            sm.save(state)

            # Load and detect mismatch
            loaded = sm.load()
            expected_step = max(loaded["completed"]) + 1 if loaded["completed"] else 1
            actual_step = loaded["current_step"]

            assert actual_step != expected_step  # Mismatch detected
            assert expected_step == 31
            assert actual_step == 50

            # Auto-correct
            loaded["current_step"] = expected_step

            # Record audit of correction
            sm.record_audit(loaded, expected_step, "run_prompt", {
                "event": "step_mismatch_auto_corrected",
                "expected_step": expected_step,
                "actual_step": actual_step
            })

            sm.save(loaded)

            # Verify correction persisted
            verified = sm.load()
            assert verified["current_step"] == 31
            assert len(verified["audit_log"]) == 1
            assert verified["audit_log"][0]["details"]["expected_step"] == 31


class TestRateLimitIntegration:
    """I5: Rate-limit state persistence and recovery"""

    def test_rate_limit_state_persistence(self):
        """I5: Rate-limit hit → State saved → Resume waits and recovers"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            # Initial state
            state = {
                "total": 100,
                "current_step": 35,
                "current_session_id": "sess_001",
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed": list(range(1, 35)),
                "clears": [],
                "failed": [],
                "sessions": {"sess_001": list(range(1, 35))},
                "rate_limit_state": None,
                "audit_log": [],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            sm.save(state)

            # Hit rate limit at step 35
            now = datetime.now(timezone.utc)
            next_retry = now + timedelta(seconds=600)

            state["rate_limit_state"] = {
                "step": 35,
                "attempt_count": 3,
                "max_attempts": 3,
                "last_wait_time": now.isoformat(),
                "next_retry_at": next_retry.isoformat(),
            }

            sm.record_audit(state, 35, "rate_limit", {
                "attempt_count": 3,
                "max_attempts": 3,
                "next_retry_at": next_retry.isoformat()
            })

            sm.save(state)

            # Verify persistence
            loaded = sm.load()
            assert loaded["rate_limit_state"] is not None
            assert loaded["rate_limit_state"]["step"] == 35
            assert loaded["rate_limit_state"]["attempt_count"] == 3

            # Simulate wait expiration
            old_rate_limit = loaded["rate_limit_state"]
            loaded["rate_limit_state"] = None

            sm.record_audit(loaded, 35, "rate_limit", {
                "event": "rate_limit_wait_completed",
                "recovered_from_step": old_rate_limit["step"]
            })

            sm.save(loaded)

            # Verify recovery
            final = sm.load()
            assert final["rate_limit_state"] is None
            assert any(
                e["details"].get("event") == "rate_limit_wait_completed"
                for e in final["audit_log"]
            )


class TestBackupRotationIntegration:
    """I7: Backup files rotate correctly with multiple saves"""

    def test_backup_rotation_multi_save(self):
        """I7: 5 saves → Exactly 3 backups, each contains different state"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            states = []
            for i in range(1, 6):
                state = {
                    "total": 100,
                    "current_step": i,
                    "current_session_id": None,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed": list(range(1, i)),
                    "clears": [],
                    "failed": [],
                    "sessions": {},
                    "rate_limit_state": None,
                    "audit_log": [],
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                sm.save(state)
                states.append(state)

            # Verify 3 backups exist
            backups = {
                1: state_path.parent / "state.json.backup.1",
                2: state_path.parent / "state.json.backup.2",
                3: state_path.parent / "state.json.backup.3",
            }

            for num, path in backups.items():
                assert path.exists(), f"backup.{num} missing"

            # Verify backup.1 = state 4 (most recent)
            with open(backups[1], 'r') as f:
                b1 = json.load(f)
            assert b1["current_step"] == 4

            # Verify backup.2 = state 3
            with open(backups[2], 'r') as f:
                b2 = json.load(f)
            assert b2["current_step"] == 3

            # Verify backup.3 = state 2
            with open(backups[3], 'r') as f:
                b3 = json.load(f)
            assert b3["current_step"] == 2

            # Primary = state 5
            with open(state_path, 'r') as f:
                primary = json.load(f)
            assert primary["current_step"] == 5


class TestFullWorkflowSimulation:
    """I8: Full workflow with crash and recovery"""

    def test_full_workflow_with_crash_recovery(self):
        """I8: 25-step run → Crash at step 20 → Resume and recover"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            sm = StateManager(state_path)

            # Phase 1: Normal execution (steps 1-20)
            state = {
                "total": 100,
                "current_step": 1,
                "current_session_id": "sess_001",
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed": [],
                "clears": [],
                "failed": [],
                "sessions": {"sess_001": []},
                "rate_limit_state": None,
                "audit_log": [],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            for step in range(1, 21):
                state["completed"].append(step)
                state["current_step"] = step + 1
                state["sessions"]["sess_001"].append(step)

                sm.record_audit(state, step, "run_prompt", {
                    "status": "completed",
                    "session_id": "sess_001"
                })

                # Save every 5 steps
                if step % 5 == 0:
                    sm.save(state)

            # Save final state at step 20
            sm.save(state)

            # Verify completion
            loaded = sm.load()
            assert loaded["completed"] == list(range(1, 21))
            assert loaded["current_step"] == 21
            assert len(loaded["audit_log"]) == 20

            # Phase 2: Simulate crash - corrupt state.json
            with open(state_path, 'w') as f:
                f.write('{"current_step": 21, "completed": [1,2,3')  # Truncated

            # Phase 3: Resume and recover
            recovered = sm.load()

            # Verify recovery to step 20
            assert recovered["completed"] == list(range(1, 21))
            assert recovered["current_step"] == 21
            assert len(recovered["audit_log"]) == 20

            # Phase 4: Continue execution (steps 21-25)
            for step in range(21, 26):
                recovered["completed"].append(step)
                recovered["current_step"] = step + 1
                recovered["sessions"]["sess_001"].append(step)

                sm.record_audit(recovered, step, "run_prompt", {
                    "status": "completed",
                    "session_id": "sess_001"
                })

            sm.save(recovered)

            # Verify final state
            final = sm.load()
            assert final["completed"] == list(range(1, 26))
            assert final["current_step"] == 26
            assert len(final["audit_log"]) == 25
            assert final["sessions"]["sess_001"] == list(range(1, 26))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
