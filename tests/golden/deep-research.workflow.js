// AUTO-EMITTED by emit_workflow.py from graph.json (schema_version 0.1). DO NOT EDIT BY HAND.
// Edit graph.json and re-emit; resume re-runs only from the first changed agent() call.
// Workflow-tool format: `export const meta` + top-level statements; agent/parallel/
// pipeline/phase/log/budget/args are AMBIENT (provided by the runner), not imported.

export const meta = {
  name: "deep-research",
  description: "deep-research harness (Mode A, emitted from graph.json schema_version 0.1)",
  phases: [
    { title: "gather", detail: "agent=researcher model=haiku mech=single" },
    { title: "fetch", detail: "agent=fetcher model=haiku mech=single" },
    { title: "verify", detail: "agent=verifier model=sonnet mech=reflect-then-revise" },
    { title: "synthesize", detail: "agent=synthesizer model=opus mech=single" }
  ]
};

  const S = {
    gather_schema: {"title": "Findings", "description": "Research findings produced by the gather/fetch nodes and round-tripped by the reflect-then-revise reviser. Claims must be source-backed via source_ids; sources is the evidence pool. Matches the inlined S.findings table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["claims", "sources"], "properties": {"claims": {"type": "array", "description": "Atomic factual claims extracted from research, each tied to one or more sources.", "items": {"type": "object", "additionalProperties": false, "required": ["id", "text", "source_ids", "confidence"], "properties": {"id": {"type": "string", "description": "Stable claim identifier, referenced by critique.issues[].claim_id."}, "text": {"type": "string", "description": "The claim as a single declarative sentence."}, "source_ids": {"type": "array", "description": "IDs of supporting sources from the sources array. Empty means unsupported (the reviser should drop or flag these).", "items": {"type": "string"}}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence the claim is true and source-backed, 0..1."}}}}, "sources": {"type": "array", "description": "Evidence pool. Every claim.source_ids entry should resolve to an id here.", "items": {"type": "object", "additionalProperties": false, "required": ["id", "url", "title"], "properties": {"id": {"type": "string", "description": "Stable source identifier, referenced by claim.source_ids and report.citations[].source_id."}, "url": {"type": "string", "description": "Source URL."}, "title": {"type": "string", "description": "Human-readable source title."}}}}}},
    fetch_schema: {"title": "Findings", "description": "Research findings produced by the gather/fetch nodes and round-tripped by the reflect-then-revise reviser. Claims must be source-backed via source_ids; sources is the evidence pool. Matches the inlined S.findings table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["claims", "sources"], "properties": {"claims": {"type": "array", "description": "Atomic factual claims extracted from research, each tied to one or more sources.", "items": {"type": "object", "additionalProperties": false, "required": ["id", "text", "source_ids", "confidence"], "properties": {"id": {"type": "string", "description": "Stable claim identifier, referenced by critique.issues[].claim_id."}, "text": {"type": "string", "description": "The claim as a single declarative sentence."}, "source_ids": {"type": "array", "description": "IDs of supporting sources from the sources array. Empty means unsupported (the reviser should drop or flag these).", "items": {"type": "string"}}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence the claim is true and source-backed, 0..1."}}}}, "sources": {"type": "array", "description": "Evidence pool. Every claim.source_ids entry should resolve to an id here.", "items": {"type": "object", "additionalProperties": false, "required": ["id", "url", "title"], "properties": {"id": {"type": "string", "description": "Stable source identifier, referenced by claim.source_ids and report.citations[].source_id."}, "url": {"type": "string", "description": "Source URL."}, "title": {"type": "string", "description": "Human-readable source title."}}}}}},
    verify_schema: {"title": "Findings", "description": "Research findings produced by the gather/fetch nodes and round-tripped by the reflect-then-revise reviser. Claims must be source-backed via source_ids; sources is the evidence pool. Matches the inlined S.findings table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["claims", "sources"], "properties": {"claims": {"type": "array", "description": "Atomic factual claims extracted from research, each tied to one or more sources.", "items": {"type": "object", "additionalProperties": false, "required": ["id", "text", "source_ids", "confidence"], "properties": {"id": {"type": "string", "description": "Stable claim identifier, referenced by critique.issues[].claim_id."}, "text": {"type": "string", "description": "The claim as a single declarative sentence."}, "source_ids": {"type": "array", "description": "IDs of supporting sources from the sources array. Empty means unsupported (the reviser should drop or flag these).", "items": {"type": "string"}}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence the claim is true and source-backed, 0..1."}}}}, "sources": {"type": "array", "description": "Evidence pool. Every claim.source_ids entry should resolve to an id here.", "items": {"type": "object", "additionalProperties": false, "required": ["id", "url", "title"], "properties": {"id": {"type": "string", "description": "Stable source identifier, referenced by claim.source_ids and report.citations[].source_id."}, "url": {"type": "string", "description": "Source URL."}, "title": {"type": "string", "description": "Human-readable source title."}}}}}},
    verify_critique: {"title": "Critique", "description": "Adversarial fact-checker output for the verify node (reflect-then-revise critic). approved=true breaks the revise loop early; otherwise issues drives the reviser. Matches the inlined S.critique table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["approved", "issues"], "properties": {"approved": {"type": "boolean", "description": "True when every claim is adequately source-backed; the verify loop breaks early on true."}, "issues": {"type": "array", "description": "Problems found per claim. May be empty when approved=true.", "items": {"type": "object", "additionalProperties": false, "required": ["claim_id", "problem", "severity"], "properties": {"claim_id": {"type": "string", "description": "The findings claim.id this issue targets."}, "problem": {"type": "string", "description": "What is wrong: unsupported, overstated, miscited, etc."}, "severity": {"type": "string", "enum": ["low", "med", "high"], "description": "Issue severity."}}}}}},
    synthesize_schema: {"title": "Report", "description": "Final cited research report from the synthesize node. markdown carries inline [source_id] citations; citations is the resolved reference list. Matches the inlined S.report table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["title", "markdown", "citations"], "properties": {"title": {"type": "string", "description": "Report title."}, "markdown": {"type": "string", "description": "Full report body in Markdown. Every factual sentence carries an inline [source_id] citation."}, "citations": {"type": "array", "description": "Resolved references; each source_id should match a findings source.id used in the markdown.", "items": {"type": "object", "additionalProperties": false, "required": ["source_id", "url"], "properties": {"source_id": {"type": "string", "description": "The findings source.id this citation resolves."}, "url": {"type": "string", "description": "Citation URL."}}}}}}
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

  const NIN = {"gather": ["_workspace/00_input/query.md"], "fetch": ["_workspace/01_gather/findings.json"], "verify": ["_workspace/02_fetch/findings.json"], "synthesize": ["_workspace/03_verify/findings.json"]};
  const P = {
    gather: (input) => "INPUT:\n" + JSON.stringify(input) + "\n\nFollow your agent definition. Return ONLY JSON matching the required schema.",
    fetch: (input) => "INPUT:\n" + JSON.stringify(input) + "\n\nFollow your agent definition. Return ONLY JSON matching the required schema.",
    verify_critic: (draft, r) => "DRAFT (round " + r + "):\n" + JSON.stringify(draft) + "\n\nAdversarially critique per your agent definition. If acceptable set approved=true. Return ONLY critique JSON.",
    verify_reviser: (draft, crit, r) => "DRAFT:\n" + JSON.stringify(draft) + "\nCRITIQUE:\n" + JSON.stringify(crit) + "\nRevise to fix every issue. Return ONLY corrected JSON per schema.",
    synthesize: (input) => "INPUT:\n" + JSON.stringify(input) + "\n\nFollow your agent definition. Return ONLY JSON matching the required schema.",
  };

  async function node_gather(input) {
    phase("gather"); log("gather <- " + JSON.stringify(NIN.gather));
    return await agent(P.gather(input), { label: "gather", phase: "gather", model: "haiku", agentType: "researcher", schema: S.gather_schema });
  }

  async function node_fetch(input) {
    phase("fetch"); log("fetch <- " + JSON.stringify(NIN.fetch));
    return await agent(P.fetch(input), { label: "fetch", phase: "fetch", model: "haiku", agentType: "fetcher", schema: S.fetch_schema });
  }

  async function node_verify(input) {
    phase("verify"); let draft = input;
    for (let r = 0; r < 2; r++) {
    ensure(20000);
      const crit = await agent(P.verify_critic(draft, r), { label: "verify.critic.r"+r, phase: "verify", model: "opus", agentType: "verifier", schema: S.verify_critique });
      if (!crit || crit.approved) { log("verify: critic approved at round " + r); break; }
      draft = await agent(P.verify_reviser(draft, crit, r), { label: "verify.reviser.r"+r, phase: "verify", model: "sonnet", agentType: "verifier", schema: S.verify_schema });
    }
    return draft;
  }

  async function node_synthesize(input) {
    phase("synthesize"); log("synthesize <- " + JSON.stringify(NIN.synthesize));
    ensure(30000);
    return await agent(P.synthesize(input), { label: "synthesize", phase: "synthesize", model: "opus", agentType: "synthesizer", schema: S.synthesize_schema });
  }

  const seed = (args && args.query) ? args.query : "(input provided in _workspace/00_input/)";
  const [out] = await pipeline(
    [seed],
    (prev) => node_gather(prev),
    (prev) => node_fetch(prev),
    (prev) => node_verify(prev),
    (prev) => node_synthesize(prev)
  );
  log("done: " + (out ? "ok" : "no output (budget guard or empty)"));
  return out;
