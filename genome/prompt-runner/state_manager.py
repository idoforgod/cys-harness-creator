"""
State Management with Atomic Write + Multi-Version Backup + Corrupt Recovery

Implements Flaw #2 and #3 from FINAL_DESIGN_DECISIONS.md:
- Flaw #2: Corrupt state has no recovery path → Solved by atomic write + 3-version backup
- Flaw #3: audit.jsonl & state.json are async → Solved by merging audit_log into state.json
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ValidationError, ConfigDict

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  State Schema (Pydantic) — Validation at Load & Save
# ═══════════════════════════════════════════════════════════════

class AuditLogEntry(BaseModel):
    """Single audit log entry"""
    ts: str  # ISO8601 timestamp
    step: int
    event: str  # "run_prompt" | "clear" | "session_change" | "rate_limit"
    details: dict


class RateLimitState(BaseModel):
    """Rate-limit state tracking"""
    step: int
    attempt_count: int
    max_attempts: int
    last_wait_time: str  # ISO8601
    next_retry_at: str   # ISO8601


class SubAgentInvocation(BaseModel):
    """Sub-agent invocation record (Phase 2: Fork Context Tracking)"""
    agent: str  # "@translator", "@reviewer", "@fact-checker", etc.
    invoked_at: str  # ISO8601 timestamp
    fork_decision: bool  # True if fork context used, False if fresh
    fork_rationale: str  # Why fork was decided (e.g., "Categorized rule: always_fork")
    glossary_discoveries: list[str] = []  # New terminology found (for @translator)
    recorded_by: str  # Always "orchestrator" — SOT write authority


class WorkflowStep(BaseModel):
    """Workflow step data including sub-agent invocations"""
    model_config = ConfigDict(extra="allow")  # Allow extra fields (outputs, pacs, etc.)

    invocations: list[SubAgentInvocation] = []  # Sub-agent fork context tracking


class StateModel(BaseModel):
    """Workflow state schema — Single Source of Truth"""
    model_config = ConfigDict(extra="allow")  # Allow extra fields for backward compatibility

    total: int
    current_step: int
    current_session_id: Optional[str] = None
    status: str  # "running" | "done"
    started_at: str  # ISO8601
    completed: list[int]
    clears: list[int]
    failed: list[int]
    sessions: dict  # {session_id: [step1, step2, ...]}
    rate_limit_state: Optional[RateLimitState] = None
    audit_log: list[AuditLogEntry] = []
    steps: dict[str, WorkflowStep] = {}  # {step-N: {invocations: [...], ...}} — Phase 2 fork context tracking
    last_updated: str  # ISO8601


# ═══════════════════════════════════════════════════════════════
#  StateManager — Atomic Write + Backup + Recovery
# ═══════════════════════════════════════════════════════════════

class StateCorruptError(Exception):
    """Raised when state cannot be recovered from any backup"""
    pass


class StateManager:
    """
    Manages workflow state with crash safety and corruption recovery.

    Three-layer approach:
    1. Primary: state.json (in-use)
    2. Backup.1: Most recent confirmed good state
    3. Backup.2, Backup.3: Historical backups for extreme corruption

    Write protocol:
    1. Rotate existing backups (backup.N → backup.N+1)
    2. Write to temporary file (state.json.tmp)
    3. Validate new state (Pydantic)
    4. Atomic rename (tmp → state.json) — atomic at filesystem level

    Read protocol:
    1. Try primary (state.json)
    2. If corrupt, try backup.1, backup.2, backup.3 in order
    3. If all fail, raise StateCorruptError with diagnostic info
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.backup_dir = self.path.parent

    def _get_backup_path(self, n: int) -> Path:
        """Get backup.N path"""
        return self.backup_dir / f"{self.path.name}.backup.{n}"

    def _load_file(self, file_path: Path) -> dict:
        """Load and validate JSON file

        Raises:
            json.JSONDecodeError: If JSON is malformed
            ValidationError: If state doesn't match schema
            FileNotFoundError: If file doesn't exist
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate against schema (will raise ValidationError if invalid)
        validated = StateModel(**data)
        return data

    def _rotate_backups(self):
        """Rotate backups: backup.1 → backup.2 → backup.3, then backup primary to backup.1"""
        if not self.path.exists():
            # First save, no backups yet
            return

        # Shift backups: backup.3 removed, backup.2→backup.3, backup.1→backup.2
        for i in range(3, 1, -1):
            src = self._get_backup_path(i - 1)
            dst = self._get_backup_path(i)
            if src.exists():
                src.rename(dst)
                log.debug(f"[StateManager] Backup rotated: {src.name} → {dst.name}")

        # Copy primary to backup.1
        if self.path.exists():
            shutil.copy2(self.path, self._get_backup_path(1))
            log.debug(f"[StateManager] Primary → backup.1")

    def save(self, state: dict):
        """Save state with atomic write + backup rotation

        Protocol:
        1. Rotate backups
        2. Write to temp file
        3. Validate temp file
        4. Atomic rename (tmp → primary)

        Args:
            state: State dict to save

        Raises:
            ValidationError: If state fails schema validation
            IOError: If file operations fail
        """
        # Step 1: Rotate backups (before changing primary)
        self._rotate_backups()

        # Step 2: Write to temporary file
        temp_path = self.backup_dir / f"{self.path.name}.tmp"
        try:
            # Update timestamp
            state["last_updated"] = datetime.now(timezone.utc).isoformat()

            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            # Step 3: Validate temp file
            with open(temp_path, 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
            validated = StateModel(**temp_data)  # Will raise ValidationError if invalid

            # Step 4: Atomic rename (filesystem level atomicity)
            temp_path.replace(self.path)
            log.debug(f"[StateManager] State saved atomically: {self.path.name}")

        except (json.JSONDecodeError, ValidationError) as e:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            log.error(f"[StateManager] Validation failed, temp file discarded: {e}")
            raise
        except IOError as e:
            log.error(f"[StateManager] File I/O error: {e}")
            raise

    def load(self) -> dict:
        """Load state with automatic corruption recovery

        Tries in order:
        1. Primary (state.json)
        2. Backup.1 (most recent good)
        3. Backup.2
        4. Backup.3

        If primary fails but backup succeeds, automatically restores backup to primary.

        Returns:
            State dict

        Raises:
            StateCorruptError: If all state.json and all backups are corrupt
        """
        # Try primary first
        try:
            data = self._load_file(self.path)
            log.debug(f"[StateManager] Loaded from primary: {self.path.name}")
            return data
        except (json.JSONDecodeError, ValidationError, FileNotFoundError) as e:
            log.warning(f"[StateManager] Primary corrupt or missing: {type(e).__name__}: {e}")

        # Try backups in order
        for i in [1, 2, 3]:
            backup_path = self._get_backup_path(i)
            if not backup_path.exists():
                continue

            try:
                data = self._load_file(backup_path)
                log.warning(f"[StateManager] Recovery: Loaded from backup.{i}")

                # Restore backup to primary
                shutil.copy2(backup_path, self.path)
                log.warning(f"[StateManager] Restored backup.{i} → {self.path.name}")

                return data
            except (json.JSONDecodeError, ValidationError) as e:
                log.warning(f"[StateManager] Backup.{i} also corrupt: {type(e).__name__}")
                continue

        # All failed
        log.error(f"[StateManager] ALL BACKUPS CORRUPT. Manual intervention required.")
        raise StateCorruptError(
            f"Cannot recover state. Checked: {self.path.name}, "
            f"backup.1, backup.2, backup.3 — all corrupt or missing. "
            f"Check state files in {self.backup_dir}"
        )

    def _rotate_audit_log(self, state: dict):
        """Rotate audit_log when it exceeds 10,000 entries

        Archives old entries to separate JSONL file, keeps recent 5,000 in state.json.

        Args:
            state: State dict (modified in-place if rotation occurs)
        """
        audit_log = state.get("audit_log", [])

        if len(audit_log) > 10000:
            # Archive old entries
            today = datetime.now(timezone.utc).date().isoformat()
            archive_path = self.backup_dir / f"state.json.audit.archive.{today}.jsonl"

            with open(archive_path, 'a', encoding='utf-8') as f:
                for entry in audit_log[:5000]:
                    # Convert AuditLogEntry to dict if needed
                    if isinstance(entry, dict):
                        f.write(json.dumps(entry) + '\n')

            # Keep recent 5000 in memory
            state["audit_log"] = audit_log[5000:]
            log.info(f"[StateManager] Audit log rotated: Archived 5000 entries to {archive_path.name}")

    def record_audit(self, state: dict, step: int, event: str, details: dict):
        """Record an event in audit_log

        Args:
            state: State dict (modified in-place)
            step: Step number
            event: Event type ("run_prompt" | "clear" | "session_change" | "rate_limit")
            details: Event-specific details
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "event": event,
            "details": details,
        }

        if "audit_log" not in state:
            state["audit_log"] = []

        state["audit_log"].append(entry)

        # Check if rotation needed
        self._rotate_audit_log(state)

    def record_subagent_invocation(self, state: dict, step_name: str, agent_name: str,
                                   fork_decision: bool, fork_rationale: str,
                                   glossary_discoveries: Optional[list[str]] = None):
        """Record a sub-agent invocation in state (Phase 2 Fork Context Tracking)

        Implements §5.1.5 Pre-Invocation Validation — SOT recording of fork decisions.

        Args:
            state: State dict (modified in-place)
            step_name: Step identifier (e.g., "step-1", "step-research")
            agent_name: Sub-agent name (e.g., "@translator", "@reviewer")
            fork_decision: Boolean — True if fork context used
            fork_rationale: Human-readable reason for fork decision
            glossary_discoveries: List of new terminology found (optional, for @translator)
        """
        if "steps" not in state:
            state["steps"] = {}

        if step_name not in state["steps"]:
            state["steps"][step_name] = {"invocations": []}

        if "invocations" not in state["steps"][step_name]:
            state["steps"][step_name]["invocations"] = []

        invocation = {
            "agent": agent_name,
            "invoked_at": datetime.now(timezone.utc).isoformat(),
            "fork_decision": fork_decision,
            "fork_rationale": fork_rationale,
            "glossary_discoveries": glossary_discoveries or [],
            "recorded_by": "orchestrator",
        }

        state["steps"][step_name]["invocations"].append(invocation)
        log.debug(f"[StateManager] Recorded sub-agent invocation: {agent_name} @ {step_name} (fork={fork_decision})")

    def get_step_invocations(self, state: dict, step_name: str) -> list[dict]:
        """Query sub-agent invocations for a given step

        Args:
            state: State dict
            step_name: Step identifier

        Returns:
            List of invocation records (empty if step/invocations not found)
        """
        return state.get("steps", {}).get(step_name, {}).get("invocations", [])

    def get_step_fork_decisions(self, state: dict, step_name: str) -> dict[str, bool]:
        """Query fork decisions by agent for a given step

        Args:
            state: State dict
            step_name: Step identifier

        Returns:
            Dict mapping agent name → fork_decision boolean
        """
        invocations = self.get_step_invocations(state, step_name)
        return {inv["agent"]: inv["fork_decision"] for inv in invocations}


# ═══════════════════════════════════════════════════════════════
#  Integration Helper
# ═══════════════════════════════════════════════════════════════

def create_state_manager(state_file_path: str) -> StateManager:
    """Factory function to create StateManager"""
    return StateManager(Path(state_file_path))
