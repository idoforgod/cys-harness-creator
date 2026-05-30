#!/usr/bin/env python3
"""spawn_counter — the missing half of the runtime cost ceiling (PostToolUse).

WHY (M0/RR5): budget_block.py (PreToolUse) blocks when `budget.spawns_used >= max_spawns - margin`,
but NOTHING incremented `spawns_used` — the orchestrator was only told to do it in PROSE, so it stayed
0 and the ceiling never fired (verified: dogfood state.yaml `spawns_used:0` across 34 spawns). This
hook closes the loop: wired as PostToolUse with matcher `Agent|Task|TeamCreate`, it increments
`.harness/state.yaml` `budget.spawns_used` by 1 on every spawn return — by CODE, not prose.

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


def bump(text):
    """Return (new_text, new_value) with budget.spawns_used incremented by 1, or (text, None) if the
    key is absent. Surgical: only the matched integer is rewritten."""
    m = re.search(r"(\bspawns_used:\s*)(\d+)", text)
    if not m:
        return (text, None)
    new_val = int(m.group(2)) + 1
    new_text = text[:m.start()] + m.group(1) + str(new_val) + text[m.end():]
    return (new_text, new_val)


def _increment(state_path):
    """flock'd read-modify-write of just budget.spawns_used. Returns new value or None."""
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
        new_text, new_val = bump(text)
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
    _increment(state)   # advisory: None on absent file/key, never blocks
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
