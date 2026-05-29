#!/usr/bin/env python3
"""
retry_manager.py — Sisyphus Persistence (I-1) Implementation

Manages retry logic for workflow stage failures with 3-approach strategy:
- Classify failure (Transient / Logic / Resource)
- Select recovery approach (A / B / C)
- Track retry attempts in SOT
- Coordinate escalation

Activated when ULW mode is active (detect via _context_lib.detect_ulw_mode()).

Integration Points:
- Called post-failure by Orchestrator or hook scripts
- Updates SOT steps[step-N].retry_history[]
- Logs to DECISION-LOG.md
- Escalates to Team Lead when budget exhausted

Reference: docs/guides/failure-recovery.md
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
import json
import re


class FailureClassification(Enum):
    """Failure classification for Sisyphus recovery strategy selection."""
    TRANSIENT = "transient"  # Time-bound (timeout, temporary block)
    LOGIC = "logic"  # Content-bound (missing section, contradiction)
    RESOURCE = "resource"  # System-bound (rate limit, insufficient data)


class RetryApproach(Enum):
    """Recovery approaches for Attempt 1 / 2 / 3."""
    APPROACH_A = "approach-A"  # Primary, most direct
    APPROACH_B = "approach-B"  # Alternative 1 (modify assumptions/structure)
    APPROACH_C = "approach-C"  # Alternative 2 (radical redesign/pivot)


@dataclass
class FailureContext:
    """Context captured at failure point."""
    step_id: str
    stage_name: str
    error_message: str
    failure_type: FailureClassification
    deliverable_path: Optional[str] = None
    verification_criteria: Optional[List[str]] = None
    pacs_score: Optional[int] = None
    pacs_dimensions: Optional[Dict[str, int]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    elapsed_time_seconds: Optional[int] = None


@dataclass
class RetryAttempt:
    """Single retry attempt record."""
    attempt_number: int
    approach: RetryApproach
    timestamp_start: str
    timestamp_end: Optional[str] = None
    output_path: Optional[str] = None
    verification_status: Optional[str] = None  # PASS / FAIL
    pacs_score: Optional[int] = None
    failure_reason: Optional[str] = None


class ApproachSelector:
    """Selects recovery approach based on failure classification and history."""

    def __init__(self):
        """Initialize approach selector with failure-type → approach mapping."""
        self.approach_map: Dict[FailureClassification, List[RetryApproach]] = {
            FailureClassification.TRANSIENT: [
                RetryApproach.APPROACH_A,  # Simple retry
                RetryApproach.APPROACH_B,  # Extended timeout / logging
                RetryApproach.APPROACH_C,  # Alternative invocation method
            ],
            FailureClassification.LOGIC: [
                RetryApproach.APPROACH_A,  # Standard template
                RetryApproach.APPROACH_B,  # Simplified template / focus core
                RetryApproach.APPROACH_C,  # Completely different structure
            ],
            FailureClassification.RESOURCE: [
                RetryApproach.APPROACH_A,  # Immediate retry
                RetryApproach.APPROACH_B,  # Modified parameters
                RetryApproach.APPROACH_C,  # Alternative method / escalate
            ],
        }

    def select_approach_for_attempt(
        self, failure_type: FailureClassification, attempt_number: int
    ) -> Optional[RetryApproach]:
        """
        Select approach for given attempt number (1-3).

        Args:
            failure_type: Classification of failure
            attempt_number: Which attempt (1, 2, or 3)

        Returns:
            RetryApproach (APPROACH_A / APPROACH_B / APPROACH_C) or None if attempt > 3
        """
        approaches = self.approach_map.get(failure_type)
        if not approaches:
            return None

        if attempt_number < 1 or attempt_number > 3:
            return None

        return approaches[attempt_number - 1]

    def describe_approach(
        self, approach: RetryApproach, failure_type: FailureClassification
    ) -> str:
        """Generate human-readable description of approach for this failure type."""
        descriptions = {
            (FailureClassification.TRANSIENT, RetryApproach.APPROACH_A): (
                "Simple retry (same parameters)"
            ),
            (FailureClassification.TRANSIENT, RetryApproach.APPROACH_B): (
                "Extended timeout + enhanced logging"
            ),
            (FailureClassification.TRANSIENT, RetryApproach.APPROACH_C): (
                "Alternative invocation method (direct vs. sub-agent)"
            ),
            (FailureClassification.LOGIC, RetryApproach.APPROACH_A): (
                "Generate output with standard template"
            ),
            (FailureClassification.LOGIC, RetryApproach.APPROACH_B): (
                "Simplify template; focus on core sections"
            ),
            (FailureClassification.LOGIC, RetryApproach.APPROACH_C): (
                "Completely different output structure (e.g., Q&A vs. narrative)"
            ),
            (FailureClassification.RESOURCE, RetryApproach.APPROACH_A): (
                "Immediate retry (hope condition resolves)"
            ),
            (FailureClassification.RESOURCE, RetryApproach.APPROACH_B): (
                "Retry with modified parameters"
            ),
            (FailureClassification.RESOURCE, RetryApproach.APPROACH_C): (
                "Alternative resource / escalate to Team Lead"
            ),
        }
        return descriptions.get((failure_type, approach), "Unknown approach")


class RetryBudget:
    """Tracks retry budget and attempt history for a stage."""

    def __init__(self, stage_id: str, max_attempts: int = 3):
        """
        Initialize retry budget for a stage.

        Args:
            stage_id: Stage identifier (e.g., "step-research")
            max_attempts: Maximum retries (default 3 per Sisyphus Persistence)
        """
        self.stage_id = stage_id
        self.max_attempts = max_attempts
        self.attempts: List[RetryAttempt] = []
        self.current_attempt_number = 0

    def next_attempt(self, approach: RetryApproach) -> Optional[RetryAttempt]:
        """
        Request next attempt slot.

        Args:
            approach: Recovery approach for this attempt

        Returns:
            RetryAttempt object if slot available, None if budget exhausted
        """
        if self.current_attempt_number >= self.max_attempts:
            return None

        self.current_attempt_number += 1
        attempt = RetryAttempt(
            attempt_number=self.current_attempt_number,
            approach=approach,
            timestamp_start=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        self.attempts.append(attempt)
        return attempt

    def complete_attempt(
        self,
        verification_status: str,
        pacs_score: Optional[int] = None,
        output_path: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> None:
        """Record completion of current attempt."""
        if self.attempts:
            current = self.attempts[-1]
            current.timestamp_end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            current.verification_status = verification_status
            current.pacs_score = pacs_score
            current.output_path = output_path
            current.failure_reason = failure_reason

    def is_budget_exhausted(self) -> bool:
        """Check if retry budget is exhausted."""
        return self.current_attempt_number >= self.max_attempts

    def get_retry_history(self) -> List[Dict]:
        """Convert attempts to SOT format."""
        return [
            {
                "attempt": attempt.attempt_number,
                "approach": attempt.approach.value,
                "timestamp_start": attempt.timestamp_start,
                "timestamp_end": attempt.timestamp_end,
                "output_path": attempt.output_path,
                "verification_status": attempt.verification_status,
                "pacs_score": attempt.pacs_score,
                "failure_reason": attempt.failure_reason,
            }
            for attempt in self.attempts
        ]


class ErrorClassifier:
    """Analyzes error messages and verification failures to classify failure type."""

    def __init__(self):
        """Initialize error patterns for classification."""
        # Transient error patterns (time-based, usually recoverable by retry)
        self.transient_patterns = [
            r"timeout",
            r"timed out",
            r"deadline exceeded",
            r"temporarily unavailable",
            r"connection reset",
            r"ECONNREFUSED",
            r"blocked.*dependency",
        ]

        # Logic error patterns (content-based, require different approach)
        self.logic_patterns = [
            r"missing.*section",
            r"missing.*assumption",
            r"contradiction",
            r"inconsistent",
            r"logic.*weak",
            r"invalid.*inference",
            r"claim.*unverified",
            r"citation.*missing",
        ]

        # Resource error patterns (system-based, may not be retryable)
        self.resource_patterns = [
            r"rate.*limit",
            r"quota.*exceeded",
            r"insufficient.*data",
            r"insufficient.*context",
            r"API.*unavailable",
            r"resource.*exhausted",
            r"unauthorized",
            r"permission.*denied",
        ]

    def classify(self, error_message: str) -> FailureClassification:
        """
        Classify error message to determine recovery strategy.

        Args:
            error_message: Error message or verification failure reason

        Returns:
            FailureClassification (TRANSIENT / LOGIC / RESOURCE)
        """
        lower_msg = error_message.lower()

        for pattern in self.transient_patterns:
            if re.search(pattern, lower_msg, re.IGNORECASE):
                return FailureClassification.TRANSIENT

        for pattern in self.logic_patterns:
            if re.search(pattern, lower_msg, re.IGNORECASE):
                return FailureClassification.LOGIC

        for pattern in self.resource_patterns:
            if re.search(pattern, lower_msg, re.IGNORECASE):
                return FailureClassification.RESOURCE

        # Default to LOGIC if no pattern matches
        return FailureClassification.LOGIC


class RetryOrchestrator:
    """Orchestrates Sisyphus Persistence retry workflow."""

    def __init__(self):
        """Initialize orchestrator with helper instances."""
        self.approach_selector = ApproachSelector()
        self.error_classifier = ErrorClassifier()
        self.budgets: Dict[str, RetryBudget] = {}

    def create_failure_context(
        self,
        step_id: str,
        stage_name: str,
        error_message: str,
        deliverable_path: Optional[str] = None,
        verification_criteria: Optional[List[str]] = None,
        pacs_score: Optional[int] = None,
        pacs_dimensions: Optional[Dict[str, int]] = None,
    ) -> FailureContext:
        """Create failure context from stage failure data."""
        failure_type = self.error_classifier.classify(error_message)
        return FailureContext(
            step_id=step_id,
            stage_name=stage_name,
            error_message=error_message,
            failure_type=failure_type,
            deliverable_path=deliverable_path,
            verification_criteria=verification_criteria,
            pacs_score=pacs_score,
            pacs_dimensions=pacs_dimensions,
        )

    def get_recovery_plan(
        self, failure_context: FailureContext
    ) -> Tuple[bool, Optional[RetryApproach], str]:
        """
        Determine if recovery is possible and recommend approach.

        Args:
            failure_context: Captured failure context

        Returns:
            Tuple[can_retry, approach, reason]
            - can_retry: True if retry possible, False if escalate
            - approach: Recommended RetryApproach if can_retry
            - reason: Explanation for decision
        """
        budget = self._get_or_create_budget(failure_context.step_id)

        if budget.is_budget_exhausted():
            return (
                False,
                None,
                (
                    f"Sisyphus budget exhausted ({budget.max_attempts} attempts). "
                    f"Escalate to Team Lead."
                ),
            )

        # Determine next attempt number
        next_attempt = budget.current_attempt_number + 1
        approach = self.approach_selector.select_approach_for_attempt(
            failure_context.failure_type, next_attempt
        )

        if not approach:
            return (
                False,
                None,
                f"Invalid attempt number {next_attempt}. Escalate to Team Lead.",
            )

        approach_desc = self.approach_selector.describe_approach(
            approach, failure_context.failure_type
        )
        reason = (
            f"Attempt {next_attempt}/3 ({failure_context.failure_type.value}): "
            f"{approach_desc}"
        )

        return (True, approach, reason)

    def request_retry_slot(
        self, failure_context: FailureContext, approach: RetryApproach
    ) -> Optional[RetryAttempt]:
        """Request a retry slot for given failure context and approach."""
        budget = self._get_or_create_budget(failure_context.step_id)
        return budget.next_attempt(approach)

    def complete_retry_attempt(
        self,
        step_id: str,
        verification_status: str,
        pacs_score: Optional[int] = None,
        output_path: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> None:
        """Record completion of retry attempt."""
        budget = self._get_or_create_budget(step_id)
        budget.complete_attempt(verification_status, pacs_score, output_path, failure_reason)

    def get_retry_history(self, step_id: str) -> List[Dict]:
        """Get retry history for step in SOT format."""
        budget = self.budgets.get(step_id)
        if not budget:
            return []
        return budget.get_retry_history()

    def format_escalation_message(
        self, failure_context: FailureContext, step_id: str
    ) -> str:
        """Format escalation message for Team Lead."""
        budget = self._get_or_create_budget(step_id)
        history = budget.get_retry_history()

        # Build attempt summary
        attempts_summary = "\n".join(
            [
                f"  {h['attempt']}. {h['approach']} → {h['verification_status']} "
                f"(pACS: {h['pacs_score']}, {h['failure_reason']})"
                for h in history
            ]
        )

        message = f"""## Escalation: {failure_context.stage_name} — Unresolvable Failure

**Stage**: {failure_context.step_id}
**Attempt Count**: {budget.current_attempt_number}/{budget.max_attempts}

**Approaches Tried**:
{attempts_summary}

**Failure Classification**: {failure_context.failure_type.value}
**Root Cause**: {failure_context.error_message}

**Request**: Team Lead intervention required

**Evidence**:
- Deliverable: {failure_context.deliverable_path}
- Verification criteria: {failure_context.verification_criteria}
- pACS score: {failure_context.pacs_score}
- Timestamp: {failure_context.timestamp}
"""
        return message

    def _get_or_create_budget(self, step_id: str) -> RetryBudget:
        """Get or create retry budget for stage."""
        if step_id not in self.budgets:
            self.budgets[step_id] = RetryBudget(step_id, max_attempts=3)
        return self.budgets[step_id]


# ============================================================================
# Testing (pytest)
# ============================================================================

def test_error_classifier():
    """Test error classification."""
    classifier = ErrorClassifier()

    assert classifier.classify("timeout occurred") == FailureClassification.TRANSIENT
    assert classifier.classify("missing section 2") == FailureClassification.LOGIC
    assert classifier.classify("rate limit exceeded") == FailureClassification.RESOURCE


def test_approach_selector():
    """Test approach selection."""
    selector = ApproachSelector()

    # Transient failure should suggest simple retry first
    approach_1 = selector.select_approach_for_attempt(
        FailureClassification.TRANSIENT, 1
    )
    assert approach_1 == RetryApproach.APPROACH_A

    # Logic failure should suggest different structure for attempt 2
    approach_2 = selector.select_approach_for_attempt(FailureClassification.LOGIC, 2)
    assert approach_2 == RetryApproach.APPROACH_B

    # Out of range should return None
    assert selector.select_approach_for_attempt(FailureClassification.LOGIC, 4) is None


def test_retry_budget():
    """Test retry budget tracking."""
    budget = RetryBudget("step-1", max_attempts=3)

    # Request attempt 1
    attempt_1 = budget.next_attempt(RetryApproach.APPROACH_A)
    assert attempt_1 is not None
    assert attempt_1.attempt_number == 1

    # Complete attempt 1
    budget.complete_attempt("FAIL", pacs_score=45, failure_reason="Missing section")

    # Request attempt 2
    attempt_2 = budget.next_attempt(RetryApproach.APPROACH_B)
    assert attempt_2 is not None
    assert attempt_2.attempt_number == 2

    # Complete attempt 2
    budget.complete_attempt("PASS", pacs_score=78)

    # Check history
    history = budget.get_retry_history()
    assert len(history) == 2
    assert history[0]["approach"] == "approach-A"
    assert history[1]["approach"] == "approach-B"


def test_retry_orchestrator():
    """Test retry orchestrator."""
    orchestrator = RetryOrchestrator()

    # Create failure context
    failure_context = orchestrator.create_failure_context(
        step_id="step-research",
        stage_name="Research",
        error_message="missing assumptions in section 2",
        pacs_score=45,
    )

    assert failure_context.failure_type == FailureClassification.LOGIC

    # Get recovery plan
    can_retry, approach, reason = orchestrator.get_recovery_plan(failure_context)
    assert can_retry is True
    assert approach == RetryApproach.APPROACH_A
    assert "Attempt 1/3" in reason

    # Request retry slot
    attempt = orchestrator.request_retry_slot(failure_context, approach)
    assert attempt.attempt_number == 1

    # Complete attempt 1 (failed)
    orchestrator.complete_retry_attempt(
        "step-research",
        "FAIL",
        pacs_score=45,
        failure_reason="Still missing assumptions",
    )

    # Get plan for attempt 2
    can_retry, approach, reason = orchestrator.get_recovery_plan(failure_context)
    assert can_retry is True
    assert approach == RetryApproach.APPROACH_B
    assert "Attempt 2/3" in reason


if __name__ == "__main__":
    import sys

    # Run basic tests
    try:
        test_error_classifier()
        test_approach_selector()
        test_retry_budget()
        test_retry_orchestrator()
        print("✅ All tests passed")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
