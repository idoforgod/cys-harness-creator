"""
Fix #3 Validation — run_with_retry state-machine refactor.

Verifies:
  - State transitions: initial → normal_retry → initial
  - State transitions: initial → rate_limit_wait → initial
  - State transitions: initial → session_recovery → initial
  - Independent counter behavior (normal_attempts vs rate_limit_retries)
  - Verdict returns: success, suspicious, failed, rate_limit_exceeded
  - Hybrid scenario: session expired during rate-limit recovery
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import run


# ─── Helpers ────────────────────────────────────────────────────────

def _make_log_files(tmp_path: Path, step: int, error_text: str = ""):
    """Create the three log files run_with_retry inspects."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    err = logs_dir / f"{step:03d}.error.log"
    out = logs_dir / f"{step:03d}.log"
    stream = logs_dir / f"{step:03d}.stream.jsonl"
    err.write_text(error_text, encoding="utf-8")
    out.write_text("", encoding="utf-8")
    stream.write_text("", encoding="utf-8")
    return err, out, stream


@pytest.fixture
def patched_logs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "LOGS_DIR", tmp_path / "logs")
    (tmp_path / "logs").mkdir(exist_ok=True)
    return tmp_path / "logs"


# ─── Test: success short-circuit ────────────────────────────────────

class TestSuccessReturn:
    def test_success_no_retries(self, patched_logs_dir):
        """initial state returns ('success', sid, dur) immediately."""
        with patch.object(run, "run_single_prompt", return_value=("success", "sid-1", 1.0)):
            verdict, sid, dur = run.run_with_retry(
                step=1, prompt_file=Path("/dev/null"), session_id=None, max_retries=3,
            )
        assert verdict == "success"
        assert sid == "sid-1"
        assert dur == 1.0


# ─── Test: suspicious short-circuit ─────────────────────────────────

class TestSuspiciousReturn:
    def test_suspicious_no_retries(self, patched_logs_dir):
        """suspicious is returned without retry."""
        with patch.object(run, "run_single_prompt", return_value=("suspicious", "sid-2", 0.5)):
            verdict, sid, dur = run.run_with_retry(
                step=1, prompt_file=Path("/dev/null"), session_id=None, max_retries=3,
            )
        assert verdict == "suspicious"
        assert sid == "sid-2"


# ─── Test: normal_retry exhaustion ─────────────────────────────────

class TestNormalRetryExhaustion:
    def test_failed_after_max_retries(self, monkeypatch, patched_logs_dir):
        """initial → failed → normal_retry × max → failed verdict."""
        # Skip waits to keep test fast
        monkeypatch.setattr(run.time, "sleep", lambda *_: None)
        _make_log_files(patched_logs_dir.parent, step=1, error_text="generic crash")

        call_count = {"n": 0}
        def fake_run(*args, **kwargs):
            call_count["n"] += 1
            return ("failed", None, 0.1)

        with patch.object(run, "run_single_prompt", side_effect=fake_run):
            verdict, sid, dur = run.run_with_retry(
                step=1, prompt_file=Path("/dev/null"), session_id=None, max_retries=3,
            )

        assert verdict == "failed"
        # 1 initial + 3 retries = 4 attempts
        assert call_count["n"] == 4


# ─── Test: rate_limit_wait → exceeded ───────────────────────────────

class TestRateLimitExceeded:
    def test_rate_limit_exceeded_returns_correct_verdict(self, monkeypatch, patched_logs_dir):
        """Rate-limit beyond MAX_RATE_LIMIT_RETRIES returns rate_limit_exceeded."""
        monkeypatch.setattr(run.time, "sleep", lambda *_: None)
        # Force tiny cap so test runs fast
        monkeypatch.setattr(run, "MAX_RATE_LIMIT_RETRIES", 2)
        _make_log_files(patched_logs_dir.parent, step=5, error_text="Rate limit exceeded")

        state = {"rate_limit_state": None, "audit_log": []}

        with patch.object(run, "run_single_prompt", return_value=("failed", "sid-rl", 0.1)):
            verdict, sid, dur = run.run_with_retry(
                step=5, prompt_file=Path("/dev/null"), session_id="sid-rl",
                max_retries=3, state=state,
            )

        assert verdict == "rate_limit_exceeded"
        assert state["rate_limit_state"] is not None
        assert state["rate_limit_state"]["step"] == 5

    def test_rate_limit_does_not_consume_normal_retries(self, monkeypatch, patched_logs_dir):
        """Rate-limit retries are independent from normal_attempts.

        After rate-limit retries, switching to a non-rate-limit error
        should still allow full normal_retry budget."""
        monkeypatch.setattr(run.time, "sleep", lambda *_: None)
        monkeypatch.setattr(run, "MAX_RATE_LIMIT_RETRIES", 2)

        # First 2 calls: rate limit, then switch to generic error
        call_count = {"n": 0}
        def fake_run(*args, **kwargs):
            call_count["n"] += 1
            n = call_count["n"]
            log_path = patched_logs_dir / "010.error.log"
            if n <= 2:
                log_path.write_text("Rate limit exceeded", encoding="utf-8")
            else:
                log_path.write_text("generic transient error", encoding="utf-8")
            return ("failed", None, 0.1)

        # Pre-create log files
        _make_log_files(patched_logs_dir.parent, step=10)

        with patch.object(run, "run_single_prompt", side_effect=fake_run):
            verdict, sid, dur = run.run_with_retry(
                step=10, prompt_file=Path("/dev/null"), session_id=None, max_retries=3,
            )

        # Sequence:
        #   call 1 → rate-limit, retry (rl=1)
        #   call 2 → rate-limit, retry (rl=2)
        #   call 3 → generic, normal_retry n=1
        #   call 4 → generic, normal_retry n=2
        #   call 5 → generic, normal_retry n=3
        #   call 6 → generic, normal_attempts=4 > 3 → failed
        # Total 6 calls — confirms normal budget preserved after rate-limit
        assert verdict == "failed"
        assert call_count["n"] == 6


# ─── Test: session_recovery transition ──────────────────────────────

class TestSessionRecovery:
    def test_session_expired_falls_back_to_new_session(self, monkeypatch, patched_logs_dir):
        """session_id=non-None + session expired keyword → session_id=None on next call."""
        monkeypatch.setattr(run.time, "sleep", lambda *_: None)

        captured_session_ids = []
        call_count = {"n": 0}

        def fake_run(step, prompt_file, session_id, **kwargs):
            captured_session_ids.append(session_id)
            call_count["n"] += 1
            log_path = patched_logs_dir / f"{step:03d}.error.log"
            if call_count["n"] == 1:
                log_path.write_text("session not found", encoding="utf-8")
                return ("failed", None, 0.1)
            return ("success", "new-sid", 0.1)

        _make_log_files(patched_logs_dir.parent, step=20)

        with patch.object(run, "run_single_prompt", side_effect=fake_run):
            verdict, sid, dur = run.run_with_retry(
                step=20, prompt_file=Path("/dev/null"), session_id="old-sid",
                max_retries=3,
            )

        assert verdict == "success"
        assert captured_session_ids[0] == "old-sid"
        assert captured_session_ids[1] is None  # fallback to new session

    def test_session_recovery_resets_counters(self, monkeypatch, patched_logs_dir):
        """Session recovery resets both normal_attempts and rate_limit_retries."""
        monkeypatch.setattr(run.time, "sleep", lambda *_: None)
        monkeypatch.setattr(run, "MAX_RATE_LIMIT_RETRIES", 5)

        call_count = {"n": 0}
        def fake_run(step, prompt_file, session_id, **kwargs):
            call_count["n"] += 1
            n = call_count["n"]
            log_path = patched_logs_dir / f"{step:03d}.error.log"
            if n == 1:
                # rate-limit on first call
                log_path.write_text("Rate limit exceeded", encoding="utf-8")
                return ("failed", session_id, 0.1)
            if n == 2:
                # session expiry on retry
                log_path.write_text("session not found", encoding="utf-8")
                return ("failed", session_id, 0.1)
            # subsequent calls succeed
            log_path.write_text("", encoding="utf-8")
            return ("success", "post-recovery-sid", 0.1)

        _make_log_files(patched_logs_dir.parent, step=30)

        with patch.object(run, "run_single_prompt", side_effect=fake_run):
            verdict, sid, dur = run.run_with_retry(
                step=30, prompt_file=Path("/dev/null"), session_id="initial-sid",
                max_retries=3,
            )

        # After session recovery, the third call succeeds
        assert verdict == "success"
        assert call_count["n"] == 3


# ─── Test: helper function ──────────────────────────────────────────

class TestSessionExpiredDetector:
    def test_detect_session_expired_keyword(self, tmp_path):
        err = tmp_path / "001.error.log"
        out = tmp_path / "001.log"
        stream = tmp_path / "001.stream.jsonl"
        err.write_text("Error: session not found", encoding="utf-8")
        out.write_text("", encoding="utf-8")
        stream.write_text("", encoding="utf-8")

        assert run._detect_session_expired(err, out, stream) is True

    def test_no_false_positive_on_normal_error(self, tmp_path):
        err = tmp_path / "001.error.log"
        out = tmp_path / "001.log"
        stream = tmp_path / "001.stream.jsonl"
        err.write_text("Error: connection refused", encoding="utf-8")
        out.write_text("", encoding="utf-8")
        stream.write_text("", encoding="utf-8")

        assert run._detect_session_expired(err, out, stream) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
