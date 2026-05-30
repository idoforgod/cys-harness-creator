#!/usr/bin/env python3
"""qa_gate_runner — fire the 4-layer QA stack as a deterministic hook (PostToolUse).

WHY (M0/RR3): the AWF quality gates (L0 Anti-Skip / L1 Verification / L1.5 pACS / L2 Adversarial
Review) only fired if the orchestrator PROSE remembered to call gate_or_block after each step — the same
prose-compliance bet idoforgod makes. This hook converts them into a host-fired interlock: wired as
PostToolUse (matcher `Agent|Task|TaskUpdate`), once a step's deliverable is claimed in the SOT it runs
the gate chain and a real failure exits 2, halting the run.

SAFETY (the false-block trap): the genome validators emit `valid:false` when their target artifact is
MISSING, which gate_or_block turns into a block; firing them on every spawn would false-block a healthy
run. So this runner is EVIDENCE-GATED and split:
  - it acts only on a step RECORDED in SOT `outputs.step-N` and not yet gated (`.harness/.qa_last_gated`);
  - **L0 anti-skip is done IN-HOOK** — it checks ONLY that the recorded deliverable file exists and is
    >= MIN bytes (it does NOT shell out to validate_pacs --check-l0, which also demands the pACS log and
    would false-block a deliverable-present/log-absent step);
  - **L1 / L1.5 / L2 are FIRE-ON-PRESENCE** — each validator runs (via gate_or_block) only if its log
    file exists, so quality is enforced when the log was produced and never false-blocked when it wasn't.
Advisory-safe everywhere: missing SOT / gate_or_block / validators / output path => exit 0.

Exit: 0 allow, 2 BLOCK (first failing layer). Selftest: qa_gate_runner.py --selftest
"""
import os
import re
import subprocess
import sys

MIN_OUTPUT_SIZE = 100  # L0c non-trivial deliverable floor (matches genome MIN_OUTPUT_SIZE)


def read_outputs(state_path):
    """Return {step:int -> deliverable_path:str} from SOT `outputs`. PyYAML or regex fallback."""
    try:
        text = open(state_path, encoding="utf-8").read()
    except OSError:
        return {}
    out = {}
    try:
        import yaml
        d = yaml.safe_load(text) or {}
        for k, v in (d.get("outputs") or {}).items():
            m = re.match(r"step-(\d+)$", str(k))
            if m and v:
                out[int(m.group(1))] = str(v)
        return out
    except Exception:
        for m in re.finditer(r"\bstep-(\d+):\s*(\S+)", text):
            out[int(m.group(1))] = m.group(2)
        return out


def next_step_to_gate(recorded_steps, last_gated):
    """The lowest recorded step strictly greater than last_gated (gate in order, one per fire)."""
    pending = sorted(s for s in recorded_steps if s > last_gated)
    return pending[0] if pending else None


def l0_block(step, outputs, proj, min_size=MIN_OUTPUT_SIZE):
    """In-hook L0 anti-skip: the recorded deliverable must exist and be non-trivial. (block, reason)."""
    path = outputs.get(step)
    if not path:
        return (False, "no recorded path (advisory)")
    full = path if os.path.isabs(path) else os.path.join(proj, path)
    if not os.path.isfile(full):
        return (True, "L0 anti-skip: step-%d deliverable missing on disk: %s" % (step, path))
    if os.path.getsize(full) < min_size:
        return (True, "L0 anti-skip: step-%d deliverable < %dB (trivial/empty): %s" % (step, min_size, path))
    return (False, "ok")


def gate_layers(step, proj):
    """Ordered (layer, validator, args, fire) for L1/L1.5/L2 — fire only if the layer's log exists."""
    vdir = os.path.join(proj, ".claude", "hooks", "scripts")
    return [
        ("L1", os.path.join(vdir, "validate_verification.py"), ["--step", str(step)],
         os.path.isfile(os.path.join(proj, "verification-logs", "step-%d-verify.md" % step))),
        ("L1.5", os.path.join(vdir, "validate_pacs.py"), ["--step", str(step)],
         os.path.isfile(os.path.join(proj, "pacs-logs", "step-%d-pacs.md" % step))),
        ("L2", os.path.join(vdir, "validate_review.py"), ["--step", str(step)],
         os.path.isfile(os.path.join(proj, "review-logs", "step-%d-review.md" % step))),
    ]


def run():
    proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    state = os.path.join(proj, ".harness", "state.yaml")
    gate = os.path.join(proj, ".claude", "hooks", "scripts", "gate_or_block.py")
    if not os.path.isfile(state):
        return 0
    outputs = read_outputs(state)
    if not outputs:
        return 0
    sidecar = os.path.join(proj, ".harness", ".qa_last_gated")
    try:
        last_gated = int(open(sidecar).read().strip())
    except (OSError, ValueError):
        last_gated = -1
    step = next_step_to_gate(set(outputs), last_gated)
    if step is None:
        return 0
    # L0 in-hook (no validate_pacs coupling)
    block, reason = l0_block(step, outputs, proj)
    if block:
        sys.stderr.write("QA GATE L0 BLOCK at step %d: %s\n" % (step, reason))
        return 2
    # L1/L1.5/L2 via gate_or_block, fire-on-presence
    if os.path.isfile(gate):
        for layer, validator, args, fire in gate_layers(step, proj):
            if not fire or not os.path.isfile(validator):
                continue
            proc = subprocess.run([sys.executable, gate, validator, "--project-dir", proj] + args,
                                  capture_output=True, text=True)
            if proc.returncode == 2:
                sys.stderr.write("QA GATE %s BLOCK at step %d:\n%s\n" % (layer, step, (proc.stderr or "").strip()[:2000]))
                return 2
    try:
        with open(sidecar, "w") as f:
            f.write(str(step))
    except OSError:
        pass
    return 0


def _selftest():
    import tempfile
    failed = 0
    seq = [
        (({1, 2, 3}, -1), 1, "first ungated"),
        (({1, 2, 3}, 1), 2, "after gating 1"),
        (({1, 2, 3}, 3), None, "all gated"),
        ((set(), -1), None, "nothing recorded"),
        (({2, 5}, 2), 5, "skip already-gated"),
    ]
    for (rec, lg), want, desc in seq:
        got = next_step_to_gate(rec, lg)
        ok = got == want
        failed += 0 if ok else 1
        print("%s %-24s got=%s want=%s" % ("ok " if ok else "FAIL", desc, got, want))
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "_workspace", "n1"))
        good = os.path.join("_workspace", "n1", "ok.md")
        open(os.path.join(td, good), "w").write("x" * 200)
        l0 = [
            (l0_block(1, {1: good}, td)[0], False, "deliverable present+big -> pass"),
            (l0_block(1, {1: "_workspace/n1/missing.md"}, td)[0], True, "deliverable missing -> block"),
            (l0_block(1, {}, td)[0], False, "no recorded path -> advisory pass"),
        ]
        for got, want, desc in l0:
            ok = got == want
            failed += 0 if ok else 1
            print("%s %-34s got=%s want=%s" % ("ok " if ok else "FAIL", desc, got, want))
        os.makedirs(os.path.join(td, "verification-logs"))
        open(os.path.join(td, "verification-logs", "step-1-verify.md"), "w").write("x")
        fires = {layer: fire for layer, _v, _a, fire in gate_layers(1, td)}
        ok = fires["L1"] is True and fires["L1.5"] is False and fires["L2"] is False
        failed += 0 if ok else 1
        print("%s %-24s %s" % ("ok " if ok else "FAIL", "fire-on-presence", fires))
    print("\n%d failed" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(run())
