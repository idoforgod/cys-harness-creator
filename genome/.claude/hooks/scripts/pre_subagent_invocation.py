#!/usr/bin/env python3
"""
Pre-Sub-agent Invocation Validator

Executes BEFORE Task() call to validate fork context decision and ensure
deterministic fork decisions with audit traceability.

Implements Phase 2 Design (Revision 3) sub-agent categorization rules:
- @translator: always_fork (glossary persistence requires isolation)
- @reviewer: always_fork (independent L2 calibration requires isolated context)
- @fact-checker: always_fresh (stateless verification logic)
- [New agent TBD]: team_decision (requires explicit ADR before 2nd invocation)

Configuration: Loaded from .claude/config/categorization.yaml (SOT).
Fallback: Hardcoded CATEGORIZATION dict (for backward compatibility).
"""

import datetime
import json
import os
import sys
from typing import Dict, Literal, Optional

try:
    import yaml
except ImportError:
    yaml = None


# Hardcoded fallback (used if categorization.yaml not found or PyYAML unavailable)
_CATEGORIZATION_FALLBACK = {
    "@translator": "always_fork",
    "@reviewer": "always_fork",
    "@fact-checker": "always_fresh",
}


def _load_categorization() -> dict:
    """Load categorization rules from YAML config or fallback to hardcoded dict."""
    # Try to load from categorization.yaml
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    yaml_path = os.path.join(project_dir, ".claude", "config", "categorization.yaml")

    if os.path.isfile(yaml_path) and yaml:
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            agents = config.get("agents", {})
            if agents:
                # Extract agent name → rule mapping
                categorization = {}
                for agent_name, agent_config in agents.items():
                    if isinstance(agent_config, dict) and "rule" in agent_config:
                        categorization[agent_name] = agent_config["rule"]
                return categorization
        except Exception:
            pass  # Fall through to fallback

    # Fallback: use hardcoded dict
    return _CATEGORIZATION_FALLBACK


# Sub-agent Categorization Rules (loaded from .claude/config/categorization.yaml)
CATEGORIZATION = _load_categorization()


def get_fork_rule(subagent_name: str) -> Literal["always_fork", "always_fresh", "team_decision", "unknown"]:
    """
    Look up fork rule for a sub-agent.

    Returns one of:
      - 'always_fork': Sub-agent runs in isolated fork context
      - 'always_fresh': Sub-agent runs with fresh context (no accumulated state)
      - 'team_decision': Fork decision deferred to team (requires ADR before 2nd invocation)
      - 'unknown': Sub-agent not in CATEGORIZATION dict → error
    """
    return CATEGORIZATION.get(subagent_name, "unknown")


def validate_and_set_fork_context(subagent_name: str, context_depth: Optional[int] = None) -> Dict:
    """
    Validate fork rule and record decision before Task() invocation.

    Performs 3-step validation:
      1. Check Categorization Rule: Look up in CATEGORIZATION dict
         - Known rule → proceed
         - Unknown agent → raise RuntimeError (blocks invocation)
      2. Return Context: Pass fork decision to Task invocation
      3. Fork decision is logged to state.yaml audit_log via StateManager (SOT)

    Args:
        subagent_name: Agent name (e.g., "@translator", "@reviewer")
        context_depth: Optional context complexity metric (used for team_decision logic)

    Returns:
        dict with keys:
          - agent: subagent name
          - rule: fork rule ('always_fork', 'always_fresh', 'team_decision')
          - should_fork: boolean (True if rule is 'always_fork')
          - timestamp: ISO8601 timestamp
          - recorded_by: "orchestrator"

    Raises:
        RuntimeError: If agent is unknown (not in CATEGORIZATION)

    Note:
        Fork decisions are now recorded via StateManager.record_subagent_invocation()
        → state.yaml audit_log (SOT). DECISION-LOG.md is reserved for ADRs only.
    """
    rule = get_fork_rule(subagent_name)

    if rule == "unknown":
        raise RuntimeError(
            f"Unknown Sub-agent: {subagent_name}. "
            f"Create ADR with explicit categorization decision (always_fork|always_fresh|team_decision) "
            f"before using this agent. "
            f"Reference: AGENTS.md §5.2 Sub-agent Categorization Rules."
        )

    decision = {
        "agent": subagent_name,
        "rule": rule,
        "should_fork": (rule == "always_fork"),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "recorded_by": "orchestrator",
    }

    return decision


# =============================================================================
# Test Suite
# =============================================================================

def test_get_fork_rule_always_fork():
    """Test: @translator returns always_fork rule"""
    rule = get_fork_rule("@translator")
    assert rule == "always_fork", f"Expected 'always_fork', got '{rule}'"
    print("✓ test_get_fork_rule_always_fork PASS")


def test_get_fork_rule_always_fresh():
    """Test: @fact-checker returns always_fresh rule"""
    rule = get_fork_rule("@fact-checker")
    assert rule == "always_fresh", f"Expected 'always_fresh', got '{rule}'"
    print("✓ test_get_fork_rule_always_fresh PASS")


def test_get_fork_rule_unknown():
    """Test: unknown agent returns unknown rule"""
    rule = get_fork_rule("@unknown-agent")
    assert rule == "unknown", f"Expected 'unknown', got '{rule}'"
    print("✓ test_get_fork_rule_unknown PASS")


def test_validate_and_set_fork_context_success():
    """Test: validate_and_set_fork_context succeeds for known agent"""
    decision = validate_and_set_fork_context("@reviewer")
    assert decision["agent"] == "@reviewer"
    assert decision["rule"] == "always_fork"
    assert decision["should_fork"] is True
    assert decision["recorded_by"] == "orchestrator"
    assert "timestamp" in decision
    print("✓ test_validate_and_set_fork_context_success PASS")


def test_validate_and_set_fork_context_unknown_raises():
    """Test: validate_and_set_fork_context raises RuntimeError for unknown agent"""
    try:
        validate_and_set_fork_context("@unknown-agent")
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "Unknown Sub-agent" in str(e)
        assert "@unknown-agent" in str(e)
        print("✓ test_validate_and_set_fork_context_unknown_raises PASS")


def test_categorization_completeness():
    """Test: CATEGORIZATION dict has all known agents"""
    assert "@translator" in CATEGORIZATION
    assert "@reviewer" in CATEGORIZATION
    assert "@fact-checker" in CATEGORIZATION
    assert CATEGORIZATION["@translator"] == "always_fork"
    assert CATEGORIZATION["@reviewer"] == "always_fork"
    assert CATEGORIZATION["@fact-checker"] == "always_fresh"
    print("✓ test_categorization_completeness PASS")


def run_tests():
    """Run all tests and report results"""
    tests = [
        test_get_fork_rule_always_fork,
        test_get_fork_rule_always_fresh,
        test_get_fork_rule_unknown,
        test_validate_and_set_fork_context_success,
        test_validate_and_set_fork_context_unknown_raises,
        test_categorization_completeness,
    ]

    print("=" * 70)
    print("Running pre_subagent_invocation.py tests")
    print("=" * 70)

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAIL: {e}")
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


def _hook_main():
    """PreToolUse(Agent|Task) hook entry: read the spawn payload from stdin, resolve the
    fork rule, log it. CYS R3 fix — previously __main__ ignored stdin and only ran tests,
    so the hook was a no-op. Normalizes the BARE subagent_type (e.g. 'reviewer') to the
    '@'-prefixed categorization key. Advisory by default (exit 0); set
    CYS_PRESUBAGENT_BLOCK_UNKNOWN=1 to hard-block (exit 2) unregistered agents — only safe
    once a categorization.yaml entry is auto-emitted per harness node (else it self-blocks)."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    if not raw.strip():
        return 0
    try:
        data = json.loads(raw)
    except Exception:
        return 0
    ti = data.get("tool_input", {}) or {}
    name = ti.get("subagent_type") or ti.get("subagentType") or ti.get("agent_type") or ""
    if not name:
        return 0  # not a sub-agent spawn payload
    key = name if name.startswith("@") else "@" + name  # normalize bare -> @key
    rule = get_fork_rule(key)
    if rule == "unknown" and os.environ.get("CYS_PRESUBAGENT_BLOCK_UNKNOWN") == "1":
        print("pre_subagent: agent=%s rule=unknown — BLOCKED (register in "
              ".claude/config/categorization.yaml)" % name, file=sys.stderr)
        return 2
    print("pre_subagent: agent=%s rule=%s" % (name, rule), file=sys.stderr)
    return 0


if __name__ == "__main__":
    # --selftest or interactive (no piped stdin) -> run the test suite (back-compat).
    # Piped stdin (the real PreToolUse hook path) -> resolve+log the spawn (R3 fix).
    if "--selftest" in sys.argv or sys.stdin.isatty():
        sys.exit(0 if run_tests() else 1)
    sys.exit(_hook_main())
