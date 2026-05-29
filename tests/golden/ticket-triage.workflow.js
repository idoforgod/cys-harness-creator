// AUTO-EMITTED by emit_workflow.py from graph.json (schema_version 0.1). DO NOT EDIT BY HAND.
// Edit graph.json and re-emit; resume re-runs only from the first changed agent() call.
// Workflow-tool format: `export const meta` + top-level statements; agent/parallel/
// pipeline/phase/log/budget/args are AMBIENT (provided by the runner), not imported.

export const meta = {
  name: "ticket-triage",
  description: "ticket-triage harness (Mode A, emitted from graph.json schema_version 0.1)",
  phases: [
    { title: "classify_category", detail: "agent=classifier model=sonnet mech=majority-vote" },
    { title: "classify_priority", detail: "agent=prioritizer model=sonnet mech=majority-vote" },
    { title: "route", detail: "agent=router model=haiku mech=single" }
  ]
};

  const S = {
    classify_category_schema: {"title": "Classification", "description": "Category vote produced by one classifier ballot and the majority-vote winner of the classify_category node. tie_break=first picks the lowest-index ballot on ties. Matches the inlined S.classify_category_schema table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["category", "confidence", "rationale"], "properties": {"category": {"type": "string", "description": "The single best-fit support category for the ticket.", "enum": ["billing", "bug", "feature_request", "account", "how_to", "other"]}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence in the chosen category, 0..1. Used by tie_break=highest-confidence when configured."}, "rationale": {"type": "string", "description": "One sentence justifying the category from the ticket text."}}},
    classify_priority_schema: {"title": "Priority", "description": "Priority vote produced by one prioritizer ballot and the majority-vote winner of the classify_priority node. tie_break=first picks the lowest-index ballot on ties. Matches the inlined S.classify_priority_schema table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["priority", "confidence", "rationale"], "properties": {"priority": {"type": "string", "description": "Severity/urgency level for the ticket.", "enum": ["P0", "P1", "P2", "P3"]}, "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Confidence in the chosen priority, 0..1. Used by tie_break=highest-confidence when configured."}, "rationale": {"type": "string", "description": "One sentence justifying the priority (impact + urgency signals) from the ticket text."}}},
    route_schema: {"title": "Routing", "description": "Final routing decision from the single-sink route node. Merges the classify_category and classify_priority winners (received as the fanned [classification, priority] array) into one actionable assignment. Matches the inlined S.route_schema table in workflow.js.", "type": "object", "additionalProperties": false, "required": ["category", "priority", "queue", "sla_hours", "summary"], "properties": {"category": {"type": "string", "description": "Category carried over from the classification winner.", "enum": ["billing", "bug", "feature_request", "account", "how_to", "other"]}, "priority": {"type": "string", "description": "Priority carried over from the priority winner.", "enum": ["P0", "P1", "P2", "P3"]}, "queue": {"type": "string", "description": "Destination team queue the ticket is routed to.", "enum": ["billing_team", "engineering", "product", "account_team", "support_l1", "triage_backlog"]}, "sla_hours": {"type": "integer", "minimum": 1, "description": "Response SLA in hours, derived deterministically from priority (P0=1, P1=4, P2=24, P3=72)."}, "summary": {"type": "string", "description": "One-line routing summary for the assignee, combining category, priority, and queue."}}}
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

  const NIN = {"classify_category": ["_workspace/00_input/ticket.md"], "classify_priority": ["_workspace/00_input/ticket.md"], "route": ["_workspace/01_category/classification.json", "_workspace/02_priority/priority.json"]};
  const P = {
    classify_category: (input, k) => "INPUT (independent ballot #" + k + "):\n" + JSON.stringify(input) + "\n\nDecide independently per your agent definition. Return ONLY JSON per schema.",
    classify_priority: (input, k) => "INPUT (independent ballot #" + k + "):\n" + JSON.stringify(input) + "\n\nDecide independently per your agent definition. Return ONLY JSON per schema.",
    route: (input) => "INPUT:\n" + JSON.stringify(input) + "\n\nFollow your agent definition. Return ONLY JSON matching the required schema.",
  };

  async function node_classify_category(input) {
    phase("classify_category");
    const N = 3, quorum = 2, tieBreak = "first";
    const votes = (await parallel(Array.from({length:N}, (_, k) =>
      () => agent(P.classify_category(input, k), { label: "classify_category#"+k, phase: "classify_category", model: "sonnet", agentType: "classifier", schema: S.classify_category_schema })
    ))).filter(Boolean);
    return reduceMajority(votes, quorum, tieBreak);
  }

  async function node_classify_priority(input) {
    phase("classify_priority");
    const N = 3, quorum = 2, tieBreak = "first";
    const votes = (await parallel(Array.from({length:N}, (_, k) =>
      () => agent(P.classify_priority(input, k), { label: "classify_priority#"+k, phase: "classify_priority", model: "sonnet", agentType: "prioritizer", schema: S.classify_priority_schema })
    ))).filter(Boolean);
    return reduceMajority(votes, quorum, tieBreak);
  }

  async function node_route(input) {
    phase("route"); log("route <- " + JSON.stringify(NIN.route));
    return await agent(P.route(input), { label: "route", phase: "route", model: "haiku", agentType: "router", schema: S.route_schema });
  }

  const seed = (args && args.query) ? args.query : args;
  const fanned = (await parallel([
    () => node_classify_category(args),
    () => node_classify_priority(args)
  ])).filter(Boolean);
  const out = await node_route(fanned);
  return out;
