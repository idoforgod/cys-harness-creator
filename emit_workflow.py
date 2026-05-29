#!/usr/bin/env python3
"""CYS Harness Creator M0 — workflow.js emitter (Mode A deterministic runtime).

PURE function of graph.json + agent registry + schema files. Emits one runnable
Workflow .js script. No wall-clock/RNG (resume-safe); meta is a pure literal.

The emitter is a STRUCTURAL translator only — it knows topologies and decision
mechanisms, NOT the domain. Domain behavior lives in the agent .md files, injected
at runtime via agent({agentType}). Emitted prompts are thin wrappers that pass the
prior node's output and instruct "return per schema".

  graph.execution_mode == "workflow"  (else caller routes to Mode B: graph.json only)
  topology pipeline  -> pipeline([seed], stage_per_node...)   (no inter-stage barrier)
  topology dispatch  -> parallel(thunks) barrier + optional single-sink reduce node
  topology producer-reviewer -> bounded while(producer -> reviewer)
  decision_mechanism single | majority-vote | debate-with-judge | reflect-then-revise

CLI: emit_workflow.py <harness_dir>  -> writes <harness_dir>/.harness/workflow.js
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "lib"))
from toposort import toposort  # noqa: E402
from atomic_write import atomic_write  # noqa: E402
from inherit_genome import inherit  # noqa: E402

ENSURE_DEFAULT = {"verify": 20000, "synthesize": 30000}
_TEMPLATES = os.path.join(_HERE, "templates")


def _load(path):
    with open(path) as f:
        return json.load(f)


def _check_refs(graph, harness_dir):
    """Every node.agent -> .claude/agents/<agent>.md ; every output_schema -> file (harness-root-relative)."""
    node_ids = {n["id"] for n in graph["nodes"]}
    for n in graph["nodes"]:
        ap = os.path.join(harness_dir, ".claude", "agents", n["agent"] + ".md")
        if not os.path.isfile(ap):
            raise FileNotFoundError("missing agent file for node '%s': %s" % (n["id"], ap))
        if n.get("output_schema"):
            sp = n["output_schema"] if os.path.isabs(n["output_schema"]) \
                else os.path.join(harness_dir, n["output_schema"])
            if not os.path.isfile(sp):
                raise FileNotFoundError("missing output_schema for node '%s': %s" % (n["id"], sp))
    for e in graph["edges"]:
        if e["from"] not in node_ids or e["to"] not in node_ids:
            raise ValueError("edge references unknown node: %s->%s" % (e["from"], e["to"]))


def _schema_key(node):
    return node["id"] + "_schema"


def _clean_schema(s):
    """Strip JSON-Schema META keys ($schema, $id) before inlining into agent({schema}).

    EMPIRICAL: the Workflow runtime's agent({schema}) validator rejects a schema that
    carries `$schema: ".../draft/2020-12"` (it tries to resolve it as a ref) and `$id`.
    Those keys are doc metadata, not validation constraints, so we drop them at the top
    level. Our schemas use no $ref, so nested cleaning is unnecessary.
    """
    return {k: v for k, v in s.items() if k not in ("$schema", "$id")}


def _inline_schemas(graph, harness_dir):
    """Load each node.output_schema file and return a JS object literal `const S = {...}`.

    reflect-then-revise nodes also need a critique schema for the critic pass; by
    convention the emitter inlines schemas/critique.json as `<nid>_critique` when present.
    """
    parts = []
    for n in graph["nodes"]:
        if n.get("output_schema"):
            sp = os.path.join(harness_dir, n["output_schema"])
            parts.append("    %s: %s" % (_schema_key(n), json.dumps(_clean_schema(_load(sp)))))
        if n["decision_mechanism"] == "reflect-then-revise":
            cp = os.path.join(harness_dir, "schemas", "critique.json")
            if os.path.isfile(cp):
                parts.append("    %s_critique: %s" % (n["id"], json.dumps(_clean_schema(_load(cp)))))
    return "  const S = {\n" + ",\n".join(parts) + "\n  };\n" if parts else "  const S = {};\n"


def _meta(graph, order):
    by_id = {n["id"]: n for n in graph["nodes"]}
    phases = []
    for nid in order:
        n = by_id[nid]
        phases.append('    { title: %s, detail: %s }' % (
            json.dumps(nid),
            json.dumps("agent=%s model=%s mech=%s" % (n["agent"], n["model"], n["decision_mechanism"]))))
    return ("export const meta = {\n"
            "  name: %s,\n"
            "  description: %s,\n"
            "  phases: [\n%s\n  ]\n};\n" % (
                json.dumps(graph["harness_name"]),
                json.dumps("%s harness (Mode A, emitted from graph.json schema_version %s)"
                           % (graph["harness_name"], graph["schema_version"])),
                ",\n".join(phases)))


def _node_fn(node):
    """Emit one `async function node_<id>(input)` applying its decision_mechanism."""
    nid, agent, model = node["id"], node["agent"], node["model"]
    mech = node["decision_mechanism"]
    mp = node.get("mechanism_params", {})
    schema = ("S." + _schema_key(node)) if node.get("output_schema") else "undefined"
    ensure = ENSURE_DEFAULT.get(nid)
    guard = ("    ensure(%d);\n" % ensure) if ensure else ""

    if mech == "single":
        return ('  async function node_%s(input) {\n'
                '    phase("%s"); log("%s <- " + JSON.stringify(NIN.%s));\n%s'
                '    return await agent(P.%s(input), { label: "%s", phase: "%s", model: "%s", agentType: "%s", schema: %s });\n'
                '  }\n' % (nid, nid, nid, nid, guard, nid, nid, nid, model, agent, schema))

    if mech == "majority-vote":
        n = mp.get("n", 3); quorum = mp.get("quorum", (n // 2) + 1); tb = mp.get("tie_break", "first")
        return ('  async function node_%s(input) {\n'
                '    phase("%s");%s\n'
                '    const N = %d, quorum = %d, tieBreak = %s;\n'
                '    const votes = (await parallel(Array.from({length:N}, (_, k) =>\n'
                '      () => agent(P.%s(input, k), { label: "%s#"+k, phase: "%s", model: "%s", agentType: "%s", schema: %s })\n'
                '    ))).filter(Boolean);\n'
                '    return reduceMajority(votes, quorum, tieBreak);\n'
                '  }\n' % (nid, nid, ("\n"+guard).rstrip("\n") if guard else "", n, quorum, json.dumps(tb),
                          nid, nid, nid, model, agent, schema))

    if mech == "debate-with-judge":
        rounds = mp.get("max_rounds", 2); judge = mp.get("judge", "opus"); ndeb = mp.get("n", 2)
        return ('  async function node_%s(input) {\n'
                '    phase("%s"); let transcript = [];\n'
                '    for (let r = 0; r < %d; r++) {\n'
                '      ensure(15000);\n'
                '      const turns = (await parallel(Array.from({length:%d}, (_, k) =>\n'
                '        () => agent(P.%s_debater(input, transcript, r, k), { label: "%s.debater#"+k+".r"+r, phase: "%s", model: "%s", agentType: "%s" })\n'
                '      ))).filter(Boolean);\n'
                '      transcript = transcript.concat(turns);\n'
                '    }\n'
                '    return await agent(P.%s_judge(input, transcript), { label: "%s.judge", phase: "%s", model: "%s", agentType: "%s", schema: %s });\n'
                '  }\n' % (nid, nid, rounds, ndeb, nid, nid, nid, model, agent,
                          nid, nid, nid, judge, agent, schema))

    if mech == "reflect-then-revise":
        rounds = mp.get("max_rounds", 2); critic = mp.get("critic", "opus")
        return ('  async function node_%s(input) {\n'
                '    phase("%s"); let draft = input;\n'
                '    for (let r = 0; r < %d; r++) {\n'
                '%s'
                '      const crit = await agent(P.%s_critic(draft, r), { label: "%s.critic.r"+r, phase: "%s", model: "%s", agentType: "%s", schema: S.%s_critique });\n'
                '      if (!crit || crit.approved) { log("%s: critic approved at round " + r); break; }\n'
                '      draft = await agent(P.%s_reviser(draft, crit, r), { label: "%s.reviser.r"+r, phase: "%s", model: "%s", agentType: "%s", schema: %s });\n'
                '    }\n'
                '    return draft;\n'
                '  }\n' % (nid, nid, rounds, (guard or "      ensure(15000);\n"),
                          nid, nid, nid, critic, agent, nid, nid,
                          nid, nid, nid, model, agent, schema))
    raise ValueError("unknown decision_mechanism: %s" % mech)


def _prompts(graph):
    """Generic, domain-agnostic prompt builders. Role/behavior comes from agentType."""
    out = ["  const NIN = %s;" % json.dumps({n["id"]: n.get("inputs", []) for n in graph["nodes"]})]
    out.append("  const P = {")
    for n in graph["nodes"]:
        nid, mech = n["id"], n["decision_mechanism"]
        base = ('    %s: (input) => "INPUT:\\n" + JSON.stringify(input) + '
                '"\\n\\nFollow your agent definition. Return ONLY JSON matching the required schema.",' % nid)
        if mech == "single":
            out.append(base)
        elif mech == "majority-vote":
            out.append('    %s: (input, k) => "INPUT (independent ballot #" + k + "):\\n" + JSON.stringify(input) + '
                       '"\\n\\nDecide independently per your agent definition. Return ONLY JSON per schema.",' % nid)
        elif mech == "debate-with-judge":
            out.append('    %s_debater: (input, t, r, k) => "INPUT:\\n" + JSON.stringify(input) + '
                       '"\\nTRANSCRIPT:\\n" + JSON.stringify(t) + "\\nRound " + r + ", side " + k + ". Argue per your agent definition.",' % nid)
            out.append('    %s_judge: (input, t) => "INPUT:\\n" + JSON.stringify(input) + '
                       '"\\nDEBATE:\\n" + JSON.stringify(t) + "\\nJudge and decide. Return ONLY JSON per schema.",' % nid)
        elif mech == "reflect-then-revise":
            out.append('    %s_critic: (draft, r) => "DRAFT (round " + r + "):\\n" + JSON.stringify(draft) + '
                       '"\\n\\nAdversarially critique per your agent definition. If acceptable set approved=true. Return ONLY critique JSON.",' % nid)
            out.append('    %s_reviser: (draft, crit, r) => "DRAFT:\\n" + JSON.stringify(draft) + '
                       '"\\nCRITIQUE:\\n" + JSON.stringify(crit) + "\\nRevise to fix every issue. Return ONLY corrected JSON per schema.",' % nid)
    out.append("  };")
    return "\n".join(out) + "\n"


def _helpers():
    return (
        "  function ensure(min) {\n"
        "    if (budget.total && budget.remaining() < min) {\n"
        "      log(`budget guard: remaining ${budget.remaining()} < ${min}; aborting group`);\n"
        "      throw new Error(\"BUDGET_GUARD\");\n"
        "    }\n"
        "  }\n"
        "  function reduceMajority(votes, quorum, tieBreak) {\n"
        "    if (!votes.length) return null;\n"
        "    const key = (v) => JSON.stringify(v);\n"
        "    const tally = new Map();\n"
        "    votes.forEach((v, i) => { const k = key(v); const e = tally.get(k) || { v, c: 0, first: i }; e.c++; tally.set(k, e); });\n"
        "    let best = null;\n"
        "    for (const e of tally.values()) {\n"
        "      if (!best || e.c > best.c || (e.c === best.c && tieBreak === \"first\" && e.first < best.first)) best = e;\n"
        "    }\n"
        "    return best && best.c >= quorum ? best.v : (best ? best.v : votes[0]);\n"
        "  }\n")


def _topology(graph, order):
    by_id = {n["id"]: n for n in graph["nodes"]}
    top = graph["topology"]
    if top == "pipeline":
        stages = ",\n".join("    (prev) => node_%s(prev)" % nid for nid in order)
        return ('  const seed = (args && args.query) ? args.query : "(input provided in _workspace/00_input/)";\n'
                '  const [out] = await pipeline(\n    [seed],\n%s\n  );\n'
                '  log("done: " + (out ? "ok" : "no output (budget guard or empty)"));\n'
                '  return out;\n' % stages)
    if top == "dispatch":
        # fan-out all source nodes in parallel; if a single sink exists, reduce through it.
        targets = {e["to"] for e in graph["edges"]}
        sources = [nid for nid in order if nid not in targets] or order
        sinks = [nid for nid in order if nid not in {e["from"] for e in graph["edges"]}]
        thunks = ",\n".join("    () => node_%s(args)" % nid for nid in sources)
        body = ('  const seed = (args && args.query) ? args.query : args;\n'
                '  const fanned = (await parallel([\n%s\n  ])).filter(Boolean);\n' % thunks)
        if len(sinks) == 1 and sinks[0] not in sources:
            body += '  const out = await node_%s(fanned);\n  return out;\n' % sinks[0]
        else:
            # M0: single-sink assumption documented; multi-sink reduce deferred to M1.
            body += '  return fanned;  // M0: multi-sink reduce deferred to M1 (single-sink assumed)\n'
        return body
    if top == "producer-reviewer":
        prod, rev = order[0], (order[1] if len(order) > 1 else order[0])
        rounds = max((by_id[n].get("max_rounds", 2) for n in (prod, rev)), default=2)
        return ('  const seed = (args && args.query) ? args.query : args;\n'
                '  let draft = await node_%s(seed);\n'
                '  for (let r = 0; r < %d; r++) {\n'
                '    const review = await node_%s(draft);\n'
                '    if (!review || review.approved) break;\n'
                '    draft = await node_%s(draft);\n'
                '  }\n  return draft;\n' % (prod, rounds, rev, prod))
    raise ValueError("unknown topology: %s" % top)


def emit(graph, harness_dir):
    assert graph["execution_mode"] == "workflow", "Mode B (team) is not emitted; graph.json is the contract"
    _check_refs(graph, harness_dir)
    order = toposort(graph["nodes"], graph["edges"])

    header = ("// AUTO-EMITTED by emit_workflow.py from graph.json (schema_version %s). DO NOT EDIT BY HAND.\n"
              "// Edit graph.json and re-emit; resume re-runs only from the first changed agent() call.\n"
              "// Workflow-tool format: `export const meta` + top-level statements; agent/parallel/\n"
              "// pipeline/phase/log/budget/args are AMBIENT (provided by the runner), not imported.\n"
              % graph["schema_version"])
    # Top-level-statement format (matches the Workflow tool): NO default-export wrapper.
    # Helpers/S/P/node functions are top-level declarations; the topology runs as top-level
    # await with a final `return` (supported by the runner). top-level await/return are why
    # plain `node --check` does not apply — the runner wraps the body.
    body = []
    body.append(_inline_schemas(graph, harness_dir).rstrip("\n"))
    body.append(_helpers().rstrip("\n"))
    body.append(_prompts(graph).rstrip("\n"))
    for nid in order:
        body.append(_node_fn(next(n for n in graph["nodes"] if n["id"] == nid)).rstrip("\n"))
    body.append(_topology(graph, order).rstrip("\n"))
    out = header + "\n" + _meta(graph, order) + "\n" + "\n\n".join(body) + "\n"

    # emitter invariants
    assert out.lstrip().startswith("//") and "export const meta = {" in out
    assert "export default" not in out  # must be top-level-statement format
    assert "Date.now(" not in out and "Math.random(" not in out and "new Date(" not in out
    return out


def _node_table(graph):
    rows = ["  | node | agent | model | mechanism |", "  |---|---|---|---|"]
    for n in graph["nodes"]:
        rows.append("  | %s | %s | %s | %s |" % (n["id"], n["agent"], n["model"], n["decision_mechanism"]))
    return "\n".join(rows)


def emit_genome(graph, harness_dir):
    """Write the CYS genome-visualization harness.md, then TRANSPLANT THE FULL
    AgenticWorkflow genome (전수/유전) via inherit_genome — every harness inherits the
    complete long-harness machinery, self-contained, real code, verified functional.
    Returns the genome-verify error list ([] = ok)."""
    # 1) harness.md genome visualization (CYS view of the inherited constitution)
    tpl = os.path.join(_TEMPLATES, "inherited-dna.md.tmpl")
    if os.path.isfile(tpl):
        mechs = sorted(set(n["decision_mechanism"] for n in graph["nodes"]))
        md = open(tpl, encoding="utf-8").read()
        repl = {
            "{{HARNESS_NAME}}": graph["harness_name"], "{{TOPOLOGY}}": graph["topology"],
            "{{MECHANISMS}}": ", ".join(mechs), "{{NODE_COUNT}}": str(len(graph["nodes"])),
            "{{NODE_TABLE}}": _node_table(graph),
            "{{BUDGET_TOKENS}}": str(graph["budget"]["total_tokens"]),
            "{{APPROVAL}}": str(graph["budget"]["approval_required"]).lower(),
        }
        for k, v in repl.items():
            md = md.replace(k, v)
        atomic_write(os.path.join(harness_dir, "harness.md"), md)
    # 2) FULL genome transplant + verify (the inheritance the user mandated)
    return inherit(harness_dir)


def main():
    if len(sys.argv) < 2:
        print("usage: emit_workflow.py <harness_dir>", file=sys.stderr); sys.exit(2)
    harness_dir = os.path.abspath(sys.argv[1])
    graph = _load(os.path.join(harness_dir, ".harness", "graph.json"))
    js = emit(graph, harness_dir)
    dest = os.path.join(harness_dir, ".harness", "workflow.js")
    atomic_write(dest, js)
    errs = emit_genome(graph, harness_dir)
    if errs:
        print("emitted %s (%d bytes); GENOME VERIFY FAILED:" % (dest, len(js)))
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("emitted %s (%d bytes) + FULL AWF genome transplanted & verified functional" % (dest, len(js)))


if __name__ == "__main__":
    main()
