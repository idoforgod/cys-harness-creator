// AUTO-EMITTED by lift_gate.py — lift probe for skill "cited-research". DO NOT EDIT BY HAND.
// Produces two answers (with-skill sonnet vs baseline haiku) then BLIND-grades both with one
// independent opus grader. Output feeds: lift_gate.py score <results.json>. No wall-clock/RNG.

export const meta = {
  name: "lift-probe-cited-research",
  description: "skill-registration lift probe (with-skill sonnet vs baseline haiku, independent blind grader) for cited-research",
  phases: [
    { title: "answer", detail: "with_skill (sonnet, skill inlined) + baseline (haiku) produce answers" },
    { title: "grade", detail: "one blind opus grader scores both vs assertions" }
  ]
};

  const ASSERTIONS = [{"id": "A1", "text": "Every factual sentence carries an inline [source_id] citation", "polarity": "must"}, {"id": "A2", "text": "At least 3 distinct sources are listed with URLs", "polarity": "must"}, {"id": "A3", "text": "No fabricated/uncited statistics", "polarity": "must-not-violate"}];
  const PROMPT = "In 4-6 sentences, summarize the documented reliability limitations of multi-agent LLM systems as of 2026.";
  // Skill injection is via PROMPT INLINING (Workflow agent() has no `skill:` option; proven
  // options are agentType/schema/model/label/phase). with_skill prepends the skill guidance.
  const SKILL_INSTRUCTIONS = "Attach an inline [source_id] citation to EVERY factual sentence. End with a Sources list of at least 3 distinct, real sources, each with an id and URL. Never state a fact without a citation.";

  const ANSWER_SCHEMA = { "type": "object", "additionalProperties": false,
    "required": ["answer"], "properties": { "answer": { "type": "string" } } };
  const GRADE_SCHEMA = { "type": "object", "additionalProperties": false,
    "required": ["checks"], "properties": { "checks": { "type": "object",
      "description": "assertion_id -> satisfied (true/false), judged strictly and independently.",
      "additionalProperties": { "type": "boolean" } } } };

  const ANSWER = (withSkill) =>
    (withSkill && SKILL_INSTRUCTIONS ? "FOLLOW THIS SKILL GUIDANCE:\n" + SKILL_INSTRUCTIONS + "\n\n" : "") +
    "TASK:\n" + PROMPT + "\n\nProduce the best answer you can. Return ONLY JSON {answer:string}.";
  const ASSERT_TXT = ASSERTIONS.map((a) => a.id + " [" + (a.polarity || "must") + "]: " + a.text).join("\n");
  const GRADE = (label, answer) =>
    "BLIND CANDIDATE " + label + " (you do NOT know which system produced it):\n" + answer +
    "\n\nASSERTIONS:\n" + ASSERT_TXT +
    "\n\nFor EACH assertion id, judge strictly whether the answer satisfies it. Return ONLY JSON {checks:{id:boolean}}.";

  // 1) produce both answers (NO self-grading)
  phase("answer");
  const [withAns, baseAns] = await parallel([
    () => agent(ANSWER(true),  { label: "with_skill", phase: "answer", model: "sonnet", schema: ANSWER_SCHEMA }),
    () => agent(ANSWER(false), { label: "baseline",   phase: "answer", model: "haiku",  schema: ANSWER_SCHEMA })
  ]);
  // 2) one BLIND independent grader scores each (A=with-skill, B=baseline; recorded, grader-blind)
  phase("grade");
  const [gWith, gBase] = await parallel([
    () => agent(GRADE("A", (withAns && withAns.answer) || ""), { label: "grade.with", phase: "grade", model: "opus", schema: GRADE_SCHEMA }),
    () => agent(GRADE("B", (baseAns && baseAns.answer) || ""), { label: "grade.base", phase: "grade", model: "opus", schema: GRADE_SCHEMA })
  ]);

  const out = {
    skill: "cited-research",
    assertions: ASSERTIONS,
    blind_map: { A: "with_skill", B: "baseline" },
    with_results: { checks: (gWith && gWith.checks) || {} },
    without_results: { checks: (gBase && gBase.checks) || {} }
  };
  log("lift-probe done; pass to: lift_gate.py score results.json");
  return out;
