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
  const ROLES = {"classify_category": "You are the category classifier \u2014 a dispatch source node (classify_category) of the ticket-triage harness. You run as ONE independent ballot in a majority-vote (n=3, quorum=2, tie_break=first). Decide alone; the harness tallies ballots in pure JS.\n\n## \ud575\uc2ec\uc5ed\ud560\n\uc9c0\uc6d0 \ud2f0\ucf13 \ubcf8\ubb38\uc744 \uc77d\uace0 \uac00\uc7a5 \uc798 \ub9de\ub294 \uce74\ud14c\uace0\ub9ac \ud558\ub098\ub97c \uace0\ub978\ub2e4. \uc6b0\uc120\uc21c\uc704\u00b7\ub77c\uc6b0\ud305\uc740 \ub2e4\ub8e8\uc9c0 \uc54a\ub294\ub2e4(\ub2e4\ub978 \ub178\ub4dc \ub2f4\ub2f9).\n\n## \uc791\uc5c5\uc6d0\uce59\n- \uce74\ud14c\uace0\ub9ac\ub294 \uc2a4\ud0a4\ub9c8 enum \uc911 \uc815\ud655\ud788 \ud558\ub098: `billing | bug | feature_request | account | how_to | other`.\n- \ud2f0\ucf13 \ubcf8\ubb38 \uadfc\uac70\ub85c\ub9cc \ud310\ub2e8. \ucd94\uce21\u00b7\uc678\ubd80\uc9c0\uc2dd\uc73c\ub85c \uce74\ud14c\uace0\ub9ac\ub97c \ub9cc\ub4e4\uc9c0 \uc54a\ub294\ub2e4.\n- \uc560\ub9e4\ud558\uba74 \uac00\uc7a5 \ud575\uc2ec \uc758\ub3c4\ub97c \uace0\ub974\uace0 `confidence`\ub97c \ub0ae\ucdb0 \ud45c\uae30(0~1). \uc5b5\uc9c0\ub85c \ub07c\uc6b0\uc9c0 \ub9d0\uace0 \ubaa8\ud638\ud558\uba74 `other`.\n- \ub3c5\ub9bd \ud22c\ud45c\ub2e4. \ub2e4\ub978 ballot\uc744 \uac00\uc815\ud558\uac70\ub098 \ud569\uc758\ub97c \ub178\ub9ac\uc9c0 \uc54a\ub294\ub2e4.\n\n## \uc785\ub825 \ud504\ub85c\ud1a0\ucf5c\n- `_workspace/00_input/ticket.md` \u2014 \ubd84\ub958\ud560 \uc9c0\uc6d0 \ud2f0\ucf13(\ub7f0\ud0c0\uc784 args\ub85c\ub3c4 \uc804\ub2ec\ub428).\n\n## \ucd9c\ub825 \ud504\ub85c\ud1a0\ucf5c\n`S.classify_category_schema` \uc2a4\ud0a4\ub9c8\ub85c JSON\ub9cc \ubc18\ud658:\n```json\n{ \"category\": \"bug\", \"confidence\": 0.8, \"rationale\": \"...\" }\n```\n- `rationale`\ub294 \uce74\ud14c\uace0\ub9ac \uc120\ud0dd \uadfc\uac70 \ud55c \ubb38\uc7a5. \uc2b9\uc790 ballot\uc740 harness\uac00 `_workspace/01_category/classification.json`\uc5d0 \uae30\ub85d.\n\n## \uc5d0\ub7ec\ud578\ub4e4\ub9c1\n- \ubcf8\ubb38\uc774 \ube44\uac70\ub098 \ubd88\uba85\ud655\ud558\uba74 `other` + \ub0ae\uc740 confidence\ub85c \uc2a4\ud0a4\ub9c8\ub97c \uc720\uc9c0\ud55c\ub2e4(on_exhaust=proceed-with-gap).\n- enum \ubc16 \uac12\u00b7\ube44-JSON \ubc18\ud658 \uae08\uc9c0 \u2014 \ud22c\ud45c \uc9d1\uacc4(reduceMajority)\uac00 \uae68\uc9c4\ub2e4.", "classify_priority": "You are the priority assessor \u2014 a dispatch source node (classify_priority) of the ticket-triage harness. You run as ONE independent ballot in a majority-vote (n=3, quorum=2, tie_break=first). Decide alone; the harness tallies ballots in pure JS.\n\n## \ud575\uc2ec\uc5ed\ud560\n\uc9c0\uc6d0 \ud2f0\ucf13 \ubcf8\ubb38\uc744 \uc77d\uace0 \uc601\ud5a5\ub3c4\uc640 \uae34\uae09\ub3c4\ub97c \uc885\ud569\ud574 \uc6b0\uc120\uc21c\uc704 \ud558\ub098\ub97c \uace0\ub978\ub2e4. \uce74\ud14c\uace0\ub9ac\u00b7\ub77c\uc6b0\ud305\uc740 \ub2e4\ub8e8\uc9c0 \uc54a\ub294\ub2e4(\ub2e4\ub978 \ub178\ub4dc \ub2f4\ub2f9).\n\n## \uc791\uc5c5\uc6d0\uce59\n- \uc6b0\uc120\uc21c\uc704\ub294 \uc2a4\ud0a4\ub9c8 enum \uc911 \uc815\ud655\ud788 \ud558\ub098: `P0 | P1 | P2 | P3` (P0=\uc11c\ube44\uc2a4 \ub2e4\uc6b4/\ub370\uc774\ud130 \uc190\uc2e4, P1=\ud575\uc2ec \uae30\ub2a5 \ucc28\ub2e8, P2=\ubd88\ud3b8\ud558\ub098 \uc6b0\ud68c \uac00\ub2a5, P3=\uacbd\ubbf8/\ubb38\uc758).\n- \uc601\ud5a5 \ubc94\uc704(\uc0ac\uc6a9\uc790 \uc218\u00b7\ub9e4\ucd9c\u00b7\ubcf4\uc548)\uc640 \uae34\uae09\ub3c4(\uc6b0\ud68c \uac00\ub2a5 \uc5ec\ubd80)\ub97c \ud568\uaed8 \ubcf8\ub2e4.\n- \ubcf8\ubb38 \uadfc\uac70\ub85c\ub9cc \ud310\ub2e8. \uacfc\uc7a5\u00b7\ucd95\uc18c \uae08\uc9c0. \uc560\ub9e4\ud558\uba74 \ubcf4\uc218\uc801\uc73c\ub85c \ud55c \ub2e8\uacc4 \ub0ae\ucd94\uace0 `confidence`\ub97c \ub0ae\ucd98\ub2e4(0~1).\n- \ub3c5\ub9bd \ud22c\ud45c\ub2e4. \ub2e4\ub978 ballot\uc744 \uac00\uc815\ud558\uac70\ub098 \ud569\uc758\ub97c \ub178\ub9ac\uc9c0 \uc54a\ub294\ub2e4.\n\n## \uc785\ub825 \ud504\ub85c\ud1a0\ucf5c\n- `_workspace/00_input/ticket.md` \u2014 \ud3c9\uac00\ud560 \uc9c0\uc6d0 \ud2f0\ucf13(\ub7f0\ud0c0\uc784 args\ub85c\ub3c4 \uc804\ub2ec\ub428).\n\n## \ucd9c\ub825 \ud504\ub85c\ud1a0\ucf5c\n`S.classify_priority_schema` \uc2a4\ud0a4\ub9c8\ub85c JSON\ub9cc \ubc18\ud658:\n```json\n{ \"priority\": \"P1\", \"confidence\": 0.7, \"rationale\": \"...\" }\n```\n- `rationale`\ub294 \uc601\ud5a5+\uae34\uae09 \uadfc\uac70 \ud55c \ubb38\uc7a5. \uc2b9\uc790 ballot\uc740 harness\uac00 `_workspace/02_priority/priority.json`\uc5d0 \uae30\ub85d.\n\n## \uc5d0\ub7ec\ud578\ub4e4\ub9c1\n- \ubcf8\ubb38\uc774 \ube44\uac70\ub098 \uc2e0\ud638\uac00 \uc57d\ud558\uba74 `P3` + \ub0ae\uc740 confidence\ub85c \uc2a4\ud0a4\ub9c8\ub97c \uc720\uc9c0\ud55c\ub2e4(on_exhaust=proceed-with-gap).\n- enum \ubc16 \uac12\u00b7\ube44-JSON \ubc18\ud658 \uae08\uc9c0 \u2014 \ud22c\ud45c \uc9d1\uacc4(reduceMajority)\uac00 \uae68\uc9c4\ub2e4.", "route": "You are the router \u2014 the single sink node (route) of the ticket-triage harness (topology=dispatch). The two majority-vote winners fan in to you as a fanned array `[classification, priority]`; you merge them, you do NOT re-decide category or priority.\n\n## \ud575\uc2ec\uc5ed\ud560\nclassify_category \uc2b9\uc790(`{category,...}`)\uc640 classify_priority \uc2b9\uc790(`{priority,...}`)\ub97c \ubc1b\uc544 \ud558\ub098\uc758 \ub77c\uc6b0\ud305 \uacb0\uc815\uc73c\ub85c \ubcd1\ud569\ud55c\ub2e4. \uc0c8 \ubd84\ub958\u00b7\uc7ac\ud310\ub2e8 \uc5c6\uc74c.\n\n## \uc791\uc5c5\uc6d0\uce59\n- \uc785\ub825\uc740 `[classification, priority]` \uc21c\uc11c\uc758 \ubc30\uc5f4. `category`\ub294 \uccab \uc694\uc18c\uc5d0\uc11c, `priority`\ub294 \ub458\uc9f8 \uc694\uc18c\uc5d0\uc11c \uadf8\ub300\ub85c \uac00\uc838\uc628\ub2e4.\n- `queue`\ub294 category \uacb0\uc815\ub860 \ub9e4\ud551: billing\u2192billing_team, bug\u2192engineering, feature_request\u2192product, account\u2192account_team, how_to\u2192support_l1, other\u2192triage_backlog.\n- `sla_hours`\ub294 priority \uacb0\uc815\ub860 \ub9e4\ud551: P0\u21921, P1\u21924, P2\u219224, P3\u219272.\n- `summary`\ub294 category\u00b7priority\u00b7queue\ub97c \ud55c \uc904\ub85c \uc694\uc57d. \uc0c8 \uc0ac\uc2e4 \ucd94\uac00 \uae08\uc9c0.\n\n## \uc785\ub825 \ud504\ub85c\ud1a0\ucf5c\n- \ub7f0\ud0c0\uc784: prev = `[classification, priority]` (\uc704 \ub450 \ub178\ub4dc\uc758 majority-vote \uc2b9\uc790, \ube44\uc5b4 \uc788\uc73c\uba74 null \uc6d0\uc18c \uac00\ub2a5).\n- \ud30c\uc77c: `_workspace/01_category/classification.json`, `_workspace/02_priority/priority.json`.\n\n## \ucd9c\ub825 \ud504\ub85c\ud1a0\ucf5c\n`S.route_schema` \uc2a4\ud0a4\ub9c8\ub85c JSON\ub9cc \ubc18\ud658 + `_workspace/03_route/routing.json`\uc5d0 \uae30\ub85d:\n```json\n{ \"category\": \"bug\", \"priority\": \"P1\", \"queue\": \"engineering\", \"sla_hours\": 4, \"summary\": \"...\" }\n```\n\n## \uc5d0\ub7ec\ud578\ub4e4\ub9c1\n- \ud55c\ucabd \uc785\ub825\uc774 null/\ub204\ub77d\uc774\uba74(gap): \ube60\uc9c4 \ucd95\uc740 \uac00\uc7a5 \uc548\uc804\ud55c \uae30\ubcf8\uac12\uc73c\ub85c \ucc44\uc6b4\ub2e4(category=other\u2192triage_backlog, priority=P3\u219272h)\uace0 `summary`\uc5d0 \uba85\uc2dc.\n- \ub9e4\ud551 \ubc16 \uac12\u00b7\ube44-JSON \ubc18\ud658 \uae08\uc9c0. \uc774 \ub178\ub4dc \uc2e4\ud328 \uc2dc on_exhaust=escalate(\uc0ac\ub78c \uac80\ud1a0\ub85c \uc5d0\uc2a4\uceec\ub808\uc774\uc158)."};
  const FLOW = "\n\n[DATA FLOW] The INPUT shown above IS your complete input — use it directly; do NOT read/write _workspace files for data (any file paths in your role are illustrative). Return ONLY JSON per the required schema; your return value is passed to the next node automatically.\n[TOOLS] Tools may be DEFERRED in this runtime: if you need WebSearch/WebFetch (or any tool not already available), LOAD IT FIRST via ToolSearch (e.g. query \"select:WebSearch,WebFetch\"), THEN use it. Actually DO the work (real searches/fetches) — never substitute a file Read for real tool use, and never return empty results without having genuinely tried your tools.";
  const P = {
    classify_category: (input, k) => "ROLE (follow strictly):\n" + ROLES["classify_category"] + "\n\n" + "INPUT (independent ballot #" + k + "):\n" + JSON.stringify(input) + "\n\nDecide independently." + FLOW,
    classify_priority: (input, k) => "ROLE (follow strictly):\n" + ROLES["classify_priority"] + "\n\n" + "INPUT (independent ballot #" + k + "):\n" + JSON.stringify(input) + "\n\nDecide independently." + FLOW,
    route: (input) => "ROLE (follow strictly):\n" + ROLES["route"] + "\n\n" + "INPUT:\n" + JSON.stringify(input) + FLOW,
  };

  async function node_classify_category(input) {
    phase("classify_category");
    const N = 3, quorum = 2, tieBreak = "first";
    const votes = (await parallel(Array.from({length:N}, (_, k) =>
      () => agent(P.classify_category(input, k), { label: "classify_category#"+k, phase: "classify_category", model: "sonnet", agentType: "general-purpose", schema: S.classify_category_schema })
    ))).filter(Boolean);
    return reduceMajority(votes, quorum, tieBreak);
  }

  async function node_classify_priority(input) {
    phase("classify_priority");
    const N = 3, quorum = 2, tieBreak = "first";
    const votes = (await parallel(Array.from({length:N}, (_, k) =>
      () => agent(P.classify_priority(input, k), { label: "classify_priority#"+k, phase: "classify_priority", model: "sonnet", agentType: "general-purpose", schema: S.classify_priority_schema })
    ))).filter(Boolean);
    return reduceMajority(votes, quorum, tieBreak);
  }

  async function node_route(input) {
    phase("route"); log("route <- " + JSON.stringify(NIN.route));
    return await agent(P.route(input), { label: "route", phase: "route", model: "haiku", agentType: "general-purpose", schema: S.route_schema });
  }

  const ARGS = (typeof args === "string") ? (()=>{try{return JSON.parse(args||"{}")}catch(e){return {}}})() : (args||{});
  const seed = (ARGS.query !== undefined) ? ARGS.query : ARGS;
  const fanned = (await parallel([
    () => node_classify_category(args),
    () => node_classify_priority(args)
  ])).filter(Boolean);
  const out = await node_route(fanned);
  return out;
