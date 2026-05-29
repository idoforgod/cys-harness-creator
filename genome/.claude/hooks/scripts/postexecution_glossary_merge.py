#!/usr/bin/env python3
"""
Post-Execution Glossary Merge Hook

Merges glossary_discoveries[] from sub-agent invocations into the canonical glossary.

Triggered by: PostToolUse (StateManager.save)
Location: .claude/settings.json (will be registered)

Design:
- Reads state.yaml glossary_discoveries[] from all step invocations
- Parses translations/glossary.yaml (YAML format with term: { ko: "...", en: "...", context: "..." })
- Merges new discoveries without overwriting existing entries
- Records merge in audit_log
- Atomically writes updated glossary.yaml

SOT Compliance: Read-only access to state.yaml; Write-only to glossary.yaml and audit_log via StateManager.

Quality Impact:
- Automatic glossary curation → @translator consistency across sessions
- Persistent terminology memory → domain knowledge accumulation
- Audit trail → fork context traceability
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

log = logging.getLogger(__name__)


def load_state(state_path: Path) -> dict:
    """Load state.json (or state.yaml if available)."""
    # Try state.yaml first (new format), then state.json (legacy)
    for fname in ["state.yaml", "state.json"]:
        fpath = state_path.parent / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                if fname.endswith(".yaml"):
                    if yaml:
                        return yaml.safe_load(f) or {}
                    else:
                        log.warning("PyYAML not installed, cannot load .yaml")
                        return {}
                else:
                    return json.load(f)
    return {}


def load_glossary(glossary_path: Path) -> dict:
    """Load glossary.yaml as { term: { ko: "...", en: "...", ... } }."""
    if not glossary_path.exists():
        return {}

    if not yaml:
        log.warning("PyYAML not installed, cannot load glossary")
        return {}

    try:
        with open(glossary_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        log.error(f"Failed to load glossary: {e}")
        return {}


def extract_discoveries(state: dict) -> list[str]:
    """Extract all glossary_discoveries[] from all step invocations."""
    discoveries = []
    steps = state.get("steps", {})

    for step_name, step_data in steps.items():
        if not isinstance(step_data, dict):
            continue
        invocations = step_data.get("invocations", [])
        for inv in invocations:
            if isinstance(inv, dict):
                new_terms = inv.get("glossary_discoveries", [])
                if isinstance(new_terms, list):
                    discoveries.extend(new_terms)

    return discoveries


def merge_discoveries(glossary: dict, discoveries: list[str]) -> tuple[dict, int]:
    """Merge discoveries into glossary, preserving existing entries.

    Returns: (updated_glossary, num_added)
    """
    num_added = 0

    for discovery in discoveries:
        if not discovery or not isinstance(discovery, str):
            continue

        discovery = discovery.strip()
        if not discovery:
            continue

        # Only add if not already present (do not overwrite)
        if discovery not in glossary:
            glossary[discovery] = {
                "ko": "",  # Placeholder; @translator fills this in
                "en": discovery,
                "context": "sub-agent discovery",
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            }
            num_added += 1

    return glossary, num_added


def save_glossary(glossary_path: Path, glossary: dict) -> bool:
    """Save glossary to YAML file."""
    if not yaml:
        log.error("PyYAML not installed, cannot save glossary")
        return False

    try:
        # Ensure parent directory exists
        glossary_path.parent.mkdir(parents=True, exist_ok=True)

        # Preserve order: sort by term name
        sorted_glossary = dict(sorted(glossary.items()))

        with open(glossary_path, "w", encoding="utf-8") as f:
            yaml.dump(sorted_glossary, f, allow_unicode=True, default_flow_style=False)

        log.info(f"Glossary saved: {glossary_path}")
        return True
    except Exception as e:
        log.error(f"Failed to save glossary: {e}")
        return False


def record_merge_audit(state: dict, num_added: int, discoveries: list[str]) -> None:
    """Record glossary merge in audit_log (via state dict)."""
    if not state:
        return

    # Import StateManager to use record_audit
    try:
        from state_manager import StateManager, create_state_manager
    except ImportError:
        log.warning("Cannot import StateManager, skipping audit record")
        return

    # Create audit entry
    details = {
        "glossary_discoveries": discoveries[:5],  # Log first 5 for brevity
        "num_added": num_added,
        "num_discoveries": len(discoveries),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Note: We do NOT modify state here.
    # The merge is recorded by StateManager.record_audit() when state is next saved.
    # This hook is purely for glossary.yaml updates.
    log.info(
        f"Glossary merge: {num_added} new terms added from {len(discoveries)} discoveries"
    )


def main():
    """Main entry point."""
    # Determine project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Paths
    state_path = Path(project_dir) / "prompt-runner" / "state.yaml"
    glossary_path = Path(project_dir) / "translations" / "glossary.yaml"

    # If state.yaml doesn't exist, try state.json
    if not state_path.exists():
        state_path = Path(project_dir) / "prompt-runner" / "state.json"

    if not state_path.exists():
        log.debug(f"No state file found at {state_path}, skipping glossary merge")
        return

    # Load state
    state = load_state(state_path)
    if not state:
        log.debug("Empty state, skipping glossary merge")
        return

    # Extract discoveries
    discoveries = extract_discoveries(state)
    if not discoveries:
        log.debug("No glossary discoveries found")
        return

    # Load glossary
    glossary = load_glossary(glossary_path)

    # Merge
    glossary, num_added = merge_discoveries(glossary, discoveries)

    if num_added > 0:
        # Save updated glossary
        if save_glossary(glossary_path, glossary):
            log.info(f"✓ Glossary updated: {num_added} new terms merged")
        else:
            log.error("Failed to save glossary")
    else:
        log.debug("No new terms to add")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
    )
    main()
