#!/usr/bin/env python3
"""CYS Harness Creator — atomic file write (scoped port of AgenticWorkflow StateManager).

DNA: AgenticWorkflow prompt-runner/state_manager.py (atomic temp->rename + flock).
SCOPE (per integration critic): port the crash-safe write path only. The 3-version
backup ladder + StateCorruptError recovery is prompt-runner's 110-step durability need
and is OPT-IN here (a content-addressed MANIFEST is recomputable from disk).

Used by emit_workflow.py and the meta-skill for MANIFEST/harness.lock/snapshot writes,
replacing bare open(dest,'w') (the prior FATAL-FLAW: partial write on crash).
"""
import json
import os
import tempfile


def atomic_write(path, data, backup=False):
    """Write `data` (str) to `path` atomically: temp file in same dir -> fsync -> rename.

    rename(2) on the same filesystem is atomic, so a crash leaves either the old file
    or the complete new file — never a half-written one. Set backup=True to keep ONE
    previous version at `<path>.bak` (opt-in; off by default to stay lean).
    """
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    if backup and os.path.exists(path):
        try:
            os.replace(path, path + ".bak")
        except OSError:
            pass
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".swap")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:  # pin UTF-8: every reader uses encoding='utf-8' and emitted artifacts carry Korean prose (locale-independent)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, obj, backup=False, indent=2):
    atomic_write(path, json.dumps(obj, indent=indent, ensure_ascii=False) + "\n", backup=backup)
