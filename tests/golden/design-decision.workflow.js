// AUTO-EMITTED by emit_workflow.py from graph.json (schema_version 0.1). DO NOT EDIT BY HAND.
// Edit graph.json and re-emit; resume re-runs only from the first changed agent() call.
// Workflow-tool format: `export const meta` + top-level statements; agent/parallel/
// pipeline/phase/log/budget/args are AMBIENT (provided by the runner), not imported.

export const meta = {
  name: "design-decision",
  description: "design-decision harness (Mode A, emitted from graph.json schema_version 0.1)",
  phases: [
    { title: "propose", detail: "agent=proposer model=opus mech=single" },
    { title: "adjudicate", detail: "agent=debater model=sonnet mech=debate-with-judge" }
  ]
};

  const S = {
    propose_schema: {"title": "Design", "description": "Candidate technical design from the propose node (producer). Carries the decision under review, the recommended option, and the alternatives the adjudicate debate will stress-test. Matches the inlined S.propose_schema table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["decision", "recommendation", "options", "tradeoffs"], "properties": {"decision": {"type": "string", "description": "The technical design question being decided (one sentence)."}, "recommendation": {"type": "string", "description": "The single option this design recommends. Must be one of options[].name."}, "options": {"type": "array", "description": "Candidate options considered, including the recommended one.", "minItems": 1, "items": {"type": "object", "additionalProperties": false, "required": ["name", "summary"], "properties": {"name": {"type": "string", "description": "Short option label."}, "summary": {"type": "string", "description": "What the option is and how it works."}}}}, "tradeoffs": {"type": "array", "description": "Why the recommendation wins over the alternatives. One entry per material axis (cost, latency, complexity, risk, etc.).", "items": {"type": "object", "additionalProperties": false, "required": ["axis", "note"], "properties": {"axis": {"type": "string", "description": "The comparison axis."}, "note": {"type": "string", "description": "How the recommendation compares on this axis."}}}}, "revision_note": {"type": "string", "description": "On a re-proposal, what changed to address the prior verdict's concerns. Empty on the first proposal."}}},
    adjudicate_schema: {"title": "Verdict", "description": "Adjudication output for the adjudicate node (debate-with-judge). approved=true breaks the producer-reviewer loop; otherwise the producer re-proposes against concerns. Matches the inlined S.adjudicate_schema table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["approved", "chosen", "rationale", "concerns"], "properties": {"approved": {"type": "boolean", "description": "True when the proposed design is sound enough to ship; the producer-reviewer loop breaks on true."}, "chosen": {"type": "string", "description": "The option the judge endorses (an options[].name from the design). Stands even when approved=false as the current best."}, "rationale": {"type": "string", "description": "The judge's reasoning for the chosen option, distilled from the debate transcript."}, "concerns": {"type": "array", "description": "Unresolved issues the re-proposal must address. Empty when approved=true.", "items": {"type": "object", "additionalProperties": false, "required": ["issue", "severity"], "properties": {"issue": {"type": "string", "description": "What is wrong or under-justified in the design."}, "severity": {"type": "string", "enum": ["low", "med", "high"], "description": "Concern severity."}}}}}}
  };

  function ensure(min) {
    if (budget.total && budget.remaining() < min) {
      log(`budget guard: remaining ${budget.remaining()} < ${min}; aborting group`);
      throw new Error("BUDGET_GUARD");
    }
  }
  function reduceMajority(votes, quorum, tieBreak) {
    if (!votes.length) return null;
    const key = (v) => JSON.stringify(v);
    const tally = new Map();
    votes.forEach((v, i) => { const k = key(v); const e = tally.get(k) || { v, c: 0, first: i }; e.c++; tally.set(k, e); });
    let best = null;
    for (const e of tally.values()) {
      if (!best || e.c > best.c || (e.c === best.c && tieBreak === "first" && e.first < best.first)) best = e;
    }
    return best && best.c >= quorum ? best.v : (best ? best.v : votes[0]);
  }

  const NIN = {"propose": ["_workspace/00_input/decision.md"], "adjudicate": ["_workspace/01_propose/design.json"]};
  const P = {
    propose: (input) => "INPUT:\n" + JSON.stringify(input) + "\n\nFollow your agent definition. Return ONLY JSON matching the required schema.",
    adjudicate_debater: (input, t, r, k) => "INPUT:\n" + JSON.stringify(input) + "\nTRANSCRIPT:\n" + JSON.stringify(t) + "\nRound " + r + ", side " + k + ". Argue per your agent definition.",
    adjudicate_judge: (input, t) => "INPUT:\n" + JSON.stringify(input) + "\nDEBATE:\n" + JSON.stringify(t) + "\nJudge and decide. Return ONLY JSON per schema.",
  };

  async function node_propose(input) {
    phase("propose"); log("propose <- " + JSON.stringify(NIN.propose));
    return await agent(P.propose(input), { label: "propose", phase: "propose", model: "opus", agentType: "proposer", schema: S.propose_schema });
  }

  async function node_adjudicate(input) {
    phase("adjudicate"); let transcript = [];
    for (let r = 0; r < 2; r++) {
      ensure(15000);
      const turns = (await parallel(Array.from({length:2}, (_, k) =>
        () => agent(P.adjudicate_debater(input, transcript, r, k), { label: "adjudicate.debater#"+k+".r"+r, phase: "adjudicate", model: "sonnet", agentType: "debater" })
      ))).filter(Boolean);
      transcript = transcript.concat(turns);
    }
    return await agent(P.adjudicate_judge(input, transcript), { label: "adjudicate.judge", phase: "adjudicate", model: "opus", agentType: "debater", schema: S.adjudicate_schema });
  }

  const seed = (args && args.query) ? args.query : args;
  let draft = await node_propose(seed);
  for (let r = 0; r < 3; r++) {
    const review = await node_adjudicate(draft);
    if (!review || review.approved) break;
    draft = await node_propose(draft);
  }
  return draft;
