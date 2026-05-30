#!/usr/bin/env python3
"""gate_or_block — turn an advisory genome validator into a BLOCKING gate (exit 2).

WHY (pivot blocker R1/CD-1): the AWF quality-gate validators (validate_pacs.py,
validate_review.py, validate_verification.py, ...) emit `{"valid": false}` to stdout but
EXIT 0 even on failure — by design they are "NOT a Hook, manually invoked". So an
orchestrator calling them directly carries the same prose-compliance bet idoforgod has:
it must remember to parse the JSON and halt. Wrapping the call in gate_or_block converts
a `valid:false` verdict into a hard exit-2 — the one enforcement signal the live Claude
Code runtime honors (verified: a PreToolUse exit-2 hook actually blocks a tool call).

The orchestrator SKILL calls `gate_or_block.py <validator.py> [args...]` after each step
instead of the raw validator, so an L0/L1/L1.5/L2 FAIL becomes a real interlock.

Exit: 0 pass-through, 2 BLOCK. Selftest: gate_or_block.py --selftest
"""
import json
import os
import subprocess
import sys


def verdict(stdout, returncode):
    """(blocked, reason) from a genome validator's JSON stdout + its exit code.
    Best-effort across validator shapes; non-JSON output never blocks (advisory)."""
    try:
        d = json.loads(stdout)
    except Exception:
        # validator that already exit-2'd is a block regardless of parse
        return (returncode == 2, "validator exit 2" if returncode == 2 else "")
    if d.get("valid") is False:
        return (True, json.dumps(d.get("violations") or d.get("errors") or d, ensure_ascii=False))
    status = str(d.get("status", "")).lower()
    if status in ("fail", "failed", "error"):
        return (True, json.dumps(d, ensure_ascii=False))
    if d.get("errors"):
        return (True, json.dumps(d["errors"], ensure_ascii=False))
    if returncode == 2:
        return (True, "validator exit 2")
    return (False, "")


def run(argv):
    if not argv:
        print("gate_or_block: no validator specified", file=sys.stderr)
        return 2
    script = argv[0]
    if not os.path.isfile(script):
        # try the genome scripts dir
        proj = os.environ.get("CLAUDE_PROJECT_DIR", "")
        cand = os.path.join(proj, ".claude", "hooks", "scripts", os.path.basename(script))
        if os.path.isfile(cand):
            script = cand
        else:
            print("gate_or_block: validator not found: %s" % argv[0], file=sys.stderr)
            return 2
    proc = subprocess.run([sys.executable, script] + argv[1:], capture_output=True, text=True)
    blocked, reason = verdict(proc.stdout, proc.returncode)
    if blocked:
        print("GATE BLOCK (%s): %s" % (os.path.basename(argv[0]), reason or "valid:false"), file=sys.stderr)
        if proc.stdout.strip():
            print(proc.stdout.strip()[:2000], file=sys.stderr)
        return 2
    return 0


def _selftest():
    import tempfile
    failed = 0
    cases = [
        ('import json;print(json.dumps({"valid": True}))', 0, 0, "valid:true -> pass"),
        ('import json;print(json.dumps({"valid": False, "violations": ["x"]}))', 0, 2, "valid:false -> block"),
        ('import json;print(json.dumps({"status": "fail"}))', 0, 2, "status:fail -> block"),
        ('import json,sys;print(json.dumps({"valid": True}));sys.exit(2)', 2, 2, "exit2 -> block"),
        ('print("not json")', 0, 0, "non-json exit0 -> pass (advisory)"),
        ('import json;print(json.dumps({"valid": True, "errors": []}))', 0, 0, "empty errors -> pass"),
    ]
    with tempfile.TemporaryDirectory() as td:
        for i, (code, _exit, want, desc) in enumerate(cases):
            p = os.path.join(td, "v%d.py" % i)
            with open(p, "w") as f:
                f.write(code)
            got = run([p])
            ok = got == want
            failed += 0 if ok else 1
            print("%s %-40s got=%d want=%d" % ("ok " if ok else "FAIL", desc, got, want))
    print("\n%d/%d passed" % (len(cases) - failed, len(cases)))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(run(sys.argv[1:]))
