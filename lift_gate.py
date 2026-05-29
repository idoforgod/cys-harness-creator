#!/usr/bin/env python3
"""CYS Harness Creator M1 — MANDATORY skill-registration lift gate.

A skill earns registration only if it MEASURABLY beats the no-skill baseline on a
discriminating test. Lift = pass_rate_with(sonnet+skill) - pass_rate_without(haiku
baseline) over the SAME prompt + SAME gold-checkable assertions. Registration is
REFUSED when lift < LIFT_GATE_THRESHOLD (0.2, from constants.json).

This module is PURE/deterministic — it never spawns agents (only the Workflow runtime
can). So it does two separable jobs:
  1. score(with_results, without_results, assertions) -> decision dict  (the gate)
  2. emit_probe(skill) -> a tiny lift_probe.workflow.js TEMPLATE string the runtime runs
     to PRODUCE with/without results (sonnet+skill vs haiku baseline, both schema'd),
     which step 1 then scores.

Results contract (per assertion, gold-checkable so scoring stays deterministic):
  {"assertions":["A1",...], "checks": {"A1": true, "A2": false, ...}}
'must' / 'must-not-violate' assertions are required (failure fails the test);
'should' assertions are counted into pass_rate but never block on their own.

CLI:
  lift_gate.py score <results.json>       -> scored decision JSON (exit 0 register, 3 refuse)
  lift_gate.py emit-probe <skill.json>    -> prints lift_probe.workflow.js to stdout
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULTS = {"LIFT_GATE_THRESHOLD": 0.2}


def _load_const(key):
    """Single source of truth is constants.json; fall back to _DEFAULTS (resume-safe)."""
    try:
        with open(os.path.join(HERE, "constants.json")) as f:
            return json.load(f).get(key, _DEFAULTS[key])
    except (OSError, ValueError, KeyError):
        return _DEFAULTS[key]


def _pass_rate(result, assertions):
    """Fraction of assertions a single condition's result satisfies.

    must / must-not-violate are gating: any one failing yields pass_rate 0.0 for that
    condition (the test is discriminating, not partial-credit on hard requirements).
    should assertions contribute fractionally but never gate. Returns (rate, passed, failed).
    """
    checks = result.get("checks", {})
    passed, failed, hard_fail = [], [], False
    for a in assertions:
        aid, pol = a["id"], a.get("polarity", "must")
        ok = bool(checks.get(aid, False))
        (passed if ok else failed).append(aid)
        if not ok and pol in ("must", "must-not-violate"):
            hard_fail = True
    rate = 0.0 if hard_fail else (len(passed) / len(assertions) if assertions else 0.0)
    return rate, passed, failed


def score(with_results, without_results, assertions):
    """The gate. with_=sonnet+skill, without_=haiku baseline, on the SAME prompt+assertions."""
    threshold = _load_const("LIFT_GATE_THRESHOLD")
    rw, pw, fw = _pass_rate(with_results, assertions)
    rn, pn, fn = _pass_rate(without_results, assertions)
    lift = round(rw - rn, 4)
    decision = "register" if lift >= threshold else "refuse"
    return {
        "pass_rate_with": round(rw, 4), "pass_rate_without": round(rn, 4),
        "lift": lift, "threshold": threshold, "decision": decision,
        "with": {"passed": pw, "failed": fw},
        "without": {"passed": pn, "failed": fn},
        "rationale": (
            "lift %.2f >= %.2f -> skill earns registration." % (lift, threshold)
            if decision == "register" else
            "lift %.2f < %.2f -> REFUSED: skill does not beat the haiku baseline enough to justify a tier upgrade."
            % (lift, threshold)),
    }


# ---- lift_probe.workflow.js TEMPLATE (Mode A; ambient agent/parallel/log/args; pure literal meta) ----
# DESIGN NOTE (empirical, M1): an earlier self-check version had each arm grade ITS OWN
# output -> the haiku baseline inflated its self-score to all-pass, so lift collapsed to 0
# and the gate measured nothing. Fix: the two arms only PRODUCE answers; a separate, BLIND
# opus grader scores both (it never learns which is skill vs baseline). Same independent-
# grader discipline as the head-to-head suite.
_PROBE_TEMPLATE = """// AUTO-EMITTED by lift_gate.py — lift probe for skill "{skill_name}". DO NOT EDIT BY HAND.
// Produces two answers (with-skill sonnet vs baseline haiku) then BLIND-grades both with one
// independent opus grader. Output feeds: lift_gate.py score <results.json>. No wall-clock/RNG.

export const meta = {{
  name: "lift-probe-{skill_name}",
  description: "skill-registration lift probe (with-skill sonnet vs baseline haiku, independent blind grader) for {skill_name}",
  phases: [
    {{ title: "answer", detail: "with_skill (sonnet, skill inlined) + baseline (haiku) produce answers" }},
    {{ title: "grade", detail: "one blind opus grader scores both vs assertions" }}
  ]
}};

  const ASSERTIONS = {assertions_js};
  const PROMPT = {prompt_js};
  // Skill injection is via PROMPT INLINING (Workflow agent() has no `skill:` option; proven
  // options are agentType/schema/model/label/phase). with_skill prepends the skill guidance.
  const SKILL_INSTRUCTIONS = {skill_instructions_js};

  const ANSWER_SCHEMA = {{ "type": "object", "additionalProperties": false,
    "required": ["answer"], "properties": {{ "answer": {{ "type": "string" }} }} }};
  const GRADE_SCHEMA = {{ "type": "object", "additionalProperties": false,
    "required": ["checks"], "properties": {{ "checks": {{ "type": "object",
      "description": "assertion_id -> satisfied (true/false), judged strictly and independently.",
      "additionalProperties": {{ "type": "boolean" }} }} }} }};

  const ANSWER = (withSkill) =>
    (withSkill && SKILL_INSTRUCTIONS ? "FOLLOW THIS SKILL GUIDANCE:\\n" + SKILL_INSTRUCTIONS + "\\n\\n" : "") +
    "TASK:\\n" + PROMPT + "\\n\\nProduce the best answer you can. Return ONLY JSON {{answer:string}}.";
  const ASSERT_TXT = ASSERTIONS.map((a) => a.id + " [" + (a.polarity || "must") + "]: " + a.text).join("\\n");
  const GRADE = (label, answer) =>
    "BLIND CANDIDATE " + label + " (you do NOT know which system produced it):\\n" + answer +
    "\\n\\nASSERTIONS:\\n" + ASSERT_TXT +
    "\\n\\nFor EACH assertion id, judge strictly whether the answer satisfies it. Return ONLY JSON {{checks:{{id:boolean}}}}.";

  // 1) produce both answers (NO self-grading)
  phase("answer");
  const [withAns, baseAns] = await parallel([
    () => agent(ANSWER(true),  {{ label: "with_skill", phase: "answer", model: "sonnet", schema: ANSWER_SCHEMA }}),
    () => agent(ANSWER(false), {{ label: "baseline",   phase: "answer", model: "haiku",  schema: ANSWER_SCHEMA }})
  ]);
  // 2) one BLIND independent grader scores each (A=with-skill, B=baseline; recorded, grader-blind)
  phase("grade");
  const [gWith, gBase] = await parallel([
    () => agent(GRADE("A", (withAns && withAns.answer) || ""), {{ label: "grade.with", phase: "grade", model: "opus", schema: GRADE_SCHEMA }}),
    () => agent(GRADE("B", (baseAns && baseAns.answer) || ""), {{ label: "grade.base", phase: "grade", model: "opus", schema: GRADE_SCHEMA }})
  ]);

  const out = {{
    skill: "{skill_name}",
    assertions: ASSERTIONS,
    blind_map: {{ A: "with_skill", B: "baseline" }},
    with_results: {{ checks: (gWith && gWith.checks) || {{}} }},
    without_results: {{ checks: (gBase && gBase.checks) || {{}} }}
  }};
  log("lift-probe done; pass to: lift_gate.py score results.json");
  return out;
"""


def emit_probe(skill):
    """Emit the lift_probe.workflow.js TEMPLATE for one skill spec.

    skill = {"name", "prompt", "assertions":[{"id","text","polarity"}...]}. The runtime
    runs it; its returned {skill, assertions, with_results, without_results} IS the
    results.json that `score` consumes.
    """
    name = skill["name"]
    assertions = skill["assertions"]
    return _PROBE_TEMPLATE.format(
        skill_name=name,
        assertions_js=json.dumps(assertions),
        prompt_js=json.dumps(skill["prompt"]),
        skill_instructions_js=json.dumps(skill.get("instructions", "")),
    )


def main():
    ap = argparse.ArgumentParser(description="M1 skill-registration lift gate (pure scorer + probe emitter)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("score", help="score a runtime results.json -> register/refuse")
    sp.add_argument("results", help="JSON: {assertions, with_results, without_results}")
    ep = sub.add_parser("emit-probe", help="emit lift_probe.workflow.js for a skill.json")
    ep.add_argument("skill", help="JSON: {name, prompt, assertions}")
    args = ap.parse_args()

    if args.cmd == "score":
        with open(args.results) as f:
            r = json.load(f)
        out = score(r["with_results"], r["without_results"], r["assertions"])
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        sys.exit(0 if out["decision"] == "register" else 3)
    else:
        with open(args.skill) as f:
            skill = json.load(f)
        sys.stdout.write(emit_probe(skill))


if __name__ == "__main__":
    main()
