#!/usr/bin/env python3
"""spawn_counter — the missing half of the runtime cost ceiling (PostToolUse).

WHY (M0/RR5): budget_block.py (PreToolUse) blocks when `budget.spawns_used >= max_spawns - margin`,
but NOTHING incremented `spawns_used` — the orchestrator was only told to do it in PROSE, so it stayed
0 and the ceiling never fired (verified: dogfood state.yaml `spawns_used:0` across 34 spawns). This
hook closes the loop: wired as PostToolUse with matcher `Agent|Task|TeamCreate`, it increments
`.harness/state.yaml` `budget.spawns_used` on every spawn return — by CODE, not prose — by the number of
sub-agents spawned (a `TeamCreate` instantiates N members so it counts N; `Agent`/`Task` count 1).

SOT discipline: this is the ONE sanctioned non-orchestrator write to state.yaml (CONSTITUTION AC-2
amendment). It touches ONLY the reserved integer key `budget.spawns_used`, under an flock, with a
surgical regex (no reformat) so the orchestrator's single-writer ownership of every other field is
preserved. Advisory-safe: if state.yaml or the key is absent it does nothing. Always exits 0 (a counter,
never a blocker — blocking is budget_block's job).

Selftest: spawn_counter.py --selftest
"""
import os
import re
import sys


def bump(text, by=1):
    """Return (new_text, new_value) with budget.spawns_used incremented by `by`, or (text, None) if the
    key is absent. Surgical: only the matched integer is rewritten."""
    m = re.search(r"(\bspawns_used:\s*)(\d+)", text)
    if not m:
        return (text, None)
    new_val = int(m.group(2)) + by
    new_text = text[:m.start()] + m.group(1) + str(new_val) + text[m.end():]
    return (new_text, new_val)


def _spawn_increment(payload):
    """How many spawns this PostToolUse return represents. A `TeamCreate` instantiates N members in ONE
    call, so the spawn ceiling must count them all (else team mode under-counts by N-1 per team and the
    ceiling fires too late); `Agent`/`Task` spawn 1. Best-effort with a floor of 1 — any missing/odd field
    falls back to 1 (never crashes, never counts 0). Matches the emit prose 'spawns_used += 멤버수'."""
    if not isinstance(payload, dict):
        return 1
    tool = payload.get("tool_name") or payload.get("tool") or ""
    ti = payload.get("tool_input") or payload.get("input") or {}
    if tool == "TeamCreate" and isinstance(ti, dict):
        members = ti.get("members") or ti.get("agents") or []
        if isinstance(members, list) and members:
            return len(members)
    return 1


def _increment(state_path, by=1):
    """flock'd read-modify-write of just budget.spawns_used (by `by`). Returns new value or None."""
    try:
        import fcntl
    except Exception:
        fcntl = None
    try:
        fd = os.open(state_path, os.O_RDWR)
    except OSError:
        return None
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        text = os.read(fd, 10_000_000).decode("utf-8", "replace")
        new_text, new_val = bump(text, by)
        if new_val is None:
            return None
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, new_text.encode("utf-8"))
        return new_val
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
        os.close(fd)


def run():
    proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    state = os.path.join(proj, ".harness", "state.yaml")
    by = 1
    try:                                   # advisory: read the PostToolUse payload to count TeamCreate members
        if not sys.stdin.isatty():
            import json
            by = _spawn_increment(json.load(sys.stdin))
    except Exception:
        by = 1                             # any stdin/parse issue -> count this spawn as 1 (never crash/block)
    _increment(state, by)   # advisory: None on absent file/key, never blocks
    return 0


def _selftest():
    cases = [
        ("budget:\n  spawns_used: 0\n  max_spawns: 8\n", "spawns_used: 1", 1, "0 -> 1"),
        ("budget:\n  spawns_used: 7\n  max_spawns: 8\n", "spawns_used: 8", 8, "7 -> 8"),
        ("budget: {spawns_used: 3, max_spawns: 9}\n", "spawns_used: 4", 4, "inline -> 4"),
        ("workflow:\n  current_step: 0\n", None, None, "no key -> no-op"),
    ]
    failed = 0
    for text, expect_sub, expect_val, desc in cases:
        new_text, val = bump(text)
        ok = (val == expect_val) and (expect_sub is None or expect_sub in new_text)
        failed += 0 if ok else 1
        print("%s %-18s val=%s" % ("ok " if ok else "FAIL", desc, val))
    print("\n%d/%d passed" % (len(cases) - failed, len(cases)))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(run())
