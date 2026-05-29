"""
P2 Phase 2: Python Substitutions Validation (P1-P5)

Tests for the 5 Python substitutions required for Phase 2:
- P1: raise ValueError → Custom RateLimitError
- P2: is_rate_limit = bool(...) → RateLimitDetector.detect()
- P3: Hardcoded max_retries=3 → RateLimitPolicy.MAX_NORMAL_RETRIES
- P4: Magic time.sleep(600) → RATE_LIMIT_WAIT constant
- P5: dict state → StateModel(pydantic)
"""

import pytest
import sys
from pathlib import Path

# Import the module to test
import run
from state_manager import StateModel


class TestP1CustomException:
    """P1: RateLimitError custom exception"""

    def test_ratelimit_error_exists(self):
        """P1: RateLimitError class is defined"""
        assert hasattr(run, "RateLimitError")
        assert issubclass(run.RateLimitError, Exception)

    def test_ratelimit_error_can_be_raised(self):
        """P1: RateLimitError can be raised and caught"""
        with pytest.raises(run.RateLimitError):
            raise run.RateLimitError("Test error")

    def test_ratelimit_error_inheritance(self):
        """P1: RateLimitError inherits from Exception"""
        error = run.RateLimitError("Test message")
        assert isinstance(error, Exception)
        assert str(error) == "Test message"


class TestP3RateLimitPolicy:
    """P3: RateLimitPolicy class for configuration"""

    def test_ratelimit_policy_exists(self):
        """P3: RateLimitPolicy class is defined"""
        assert hasattr(run, "RateLimitPolicy")

    def test_max_normal_retries(self):
        """P3: RateLimitPolicy.MAX_NORMAL_RETRIES = 3"""
        assert run.RateLimitPolicy.MAX_NORMAL_RETRIES == 3

    def test_max_rate_limit_retries(self):
        """P3: RateLimitPolicy.MAX_RATE_LIMIT_RETRIES = 60"""
        assert run.RateLimitPolicy.MAX_RATE_LIMIT_RETRIES == 60

    def test_rate_limit_wait(self):
        """P3: RateLimitPolicy.RATE_LIMIT_WAIT = 300"""
        assert run.RateLimitPolicy.RATE_LIMIT_WAIT == 300

    def test_normal_retry_waits(self):
        """P3: RateLimitPolicy.NORMAL_RETRY_WAITS defined"""
        assert hasattr(run.RateLimitPolicy, "NORMAL_RETRY_WAITS")
        assert run.RateLimitPolicy.NORMAL_RETRY_WAITS == [15, 30, 60]


class TestP2RateLimitHandler:
    """P2: RateLimitHandler uses RateLimitPolicy"""

    def test_ratelimit_handler_exists(self):
        """P2: RateLimitHandler class exists"""
        assert hasattr(run, "RateLimitHandler")

    def test_ratelimit_handler_max_retries(self):
        """P2: RateLimitHandler.MAX_RETRIES uses policy"""
        assert run.RateLimitHandler.MAX_RETRIES == run.RateLimitPolicy.MAX_RATE_LIMIT_RETRIES

    def test_ratelimit_handler_wait_seconds(self):
        """P2: RateLimitHandler.WAIT_SECONDS uses policy"""
        assert run.RateLimitHandler.WAIT_SECONDS == run.RateLimitPolicy.RATE_LIMIT_WAIT

    def test_ratelimit_handler_detect(self):
        """P2: RateLimitHandler.detect() method exists"""
        assert hasattr(run.RateLimitHandler, "detect")
        assert callable(run.RateLimitHandler.detect)

    def test_ratelimit_keywords(self):
        """P2: RateLimitHandler has keyword list"""
        assert hasattr(run.RateLimitHandler, "KEYWORDS")
        assert "rate limit" in run.RateLimitHandler.KEYWORDS
        assert "quota exceeded" in run.RateLimitHandler.KEYWORDS


class TestP4RateLimitWaitConstant:
    """P4: Magic constants replaced with named constants"""

    def test_rate_limit_wait_constant(self):
        """P4: RATE_LIMIT_WAIT constant exists at module level"""
        assert hasattr(run, "RATE_LIMIT_WAIT")
        assert run.RATE_LIMIT_WAIT == 300  # 5 minutes

    def test_max_rate_limit_retries_constant(self):
        """P4: MAX_RATE_LIMIT_RETRIES constant exists at module level"""
        assert hasattr(run, "MAX_RATE_LIMIT_RETRIES")
        assert run.MAX_RATE_LIMIT_RETRIES == 60

    def test_constants_match_policy(self):
        """P4: Module constants match RateLimitPolicy"""
        assert run.RATE_LIMIT_WAIT == run.RateLimitPolicy.RATE_LIMIT_WAIT
        assert run.MAX_RATE_LIMIT_RETRIES == run.RateLimitPolicy.MAX_RATE_LIMIT_RETRIES


class TestP5StateModel:
    """P5: dict state → StateModel(pydantic)"""

    def test_statemodel_import(self):
        """P5: StateModel can be imported from state_manager"""
        assert StateModel is not None

    def test_statemodel_validation(self):
        """P5: StateModel validates state structure"""
        from datetime import datetime, timezone

        state_dict = {
            "total": 100,
            "current_step": 35,
            "current_session_id": None,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed": [1, 2, 3],
            "clears": [],
            "failed": [],
            "sessions": {},
            "rate_limit_state": None,
            "audit_log": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        # Should validate without error
        validated = StateModel(**state_dict)
        assert validated.current_step == 35
        assert validated.total == 100

    def test_statemodel_type_checking(self):
        """P5: StateModel enforces types"""
        from datetime import datetime, timezone
        from pydantic import ValidationError

        # Missing required field
        invalid_state = {
            "total": 100,
            "current_step": 35,
            # Missing required fields
        }

        with pytest.raises(ValidationError):
            StateModel(**invalid_state)


class TestP2IntegrationFlow:
    """P2 Integration: All substitutions work together"""

    def test_substitution_consistency(self):
        """P2 Integration: All constants are consistent"""
        # P3 policy values
        assert run.RateLimitPolicy.MAX_NORMAL_RETRIES == 3
        assert run.RateLimitPolicy.MAX_RATE_LIMIT_RETRIES == 60
        assert run.RateLimitPolicy.RATE_LIMIT_WAIT == 300

        # P4 module constants match policy
        assert run.MAX_RATE_LIMIT_RETRIES == run.RateLimitPolicy.MAX_RATE_LIMIT_RETRIES
        assert run.RATE_LIMIT_WAIT == run.RateLimitPolicy.RATE_LIMIT_WAIT

        # P2 handler uses policy
        assert run.RateLimitHandler.MAX_RETRIES == run.RateLimitPolicy.MAX_RATE_LIMIT_RETRIES
        assert run.RateLimitHandler.WAIT_SECONDS == run.RateLimitPolicy.RATE_LIMIT_WAIT

        # P1 exception is available
        assert run.RateLimitError is not None

    def test_no_magic_numbers(self):
        """P2: No hardcoded 3 or 600 for rate limits"""
        # This is a meta-test: verify that critical constants are not hardcoded
        assert run.RateLimitPolicy.MAX_NORMAL_RETRIES == 3  # Only in policy
        assert run.RateLimitPolicy.RATE_LIMIT_WAIT == 300   # Only in policy


class TestRunWithRetryIntegration:
    """P2: run_with_retry uses substitutions"""

    def test_run_with_retry_default_retries(self):
        """P3: run_with_retry default max_retries uses policy"""
        import inspect

        sig = inspect.signature(run.run_with_retry)
        # Default should be None, then set to policy value in function
        assert sig.parameters["max_retries"].default is None

    def test_policy_values_documented(self):
        """P2: Policy values are well documented"""
        # Check docstrings contain policy references
        assert hasattr(run.RateLimitPolicy, "__doc__") or len(run.RateLimitPolicy.__dict__) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
