# workflow.js emitter (Mode A deterministic sub-agent runtime)

## PURPOSE
Deterministic translator: reads a validated graph.json and emits a single runnable Workflow .js script (Mode A spine, default execution path). It is a PURE function of graph.json + the agent registry (.claude/agents/*.md) + the schema files referenced by node.output_schema. No wall-clock, no RNG, no network at emit time. The emitted script, when invoked via Workflow({scriptPath}), runs the harness's sub-agents deterministically with a hard token-budget ceiling, structured output, and resumeFromRunId partial re-run. This is the component that fills the original harness's #1 gap (no execution engine) using a REAL Claude Code primitive, and is the thing the M0 head-to-head (C2=CYS) actually executes for the deep-research dogfood.

## CONTRACT
## A. PUBLIC INTERFACE OF THE EMITTER (not the emitted file)

emit(graph, opts) -> string   # returns workflow.js source text; caller writes it to <harness>/.harness/workflow.js

```python
# emit_workflow.py  (the emitter; deterministic, no time/random)
def emit(graph: dict, agents_dir: str, schemas_dir: str) -> str:
    assert graph["execution_mode"] == "workflow"   # else caller routes to Mode B (graph.json only)
    _validate_referential_integrity(graph, agents_dir, schemas_dir)  # every node.agent -> agents_dir/<agent>.md exists; every non-"" output_schema -> schemas_dir file exists; edges reference existing node ids; exactly one source node for pipeline
    order = _toposort(graph["nodes"], graph["edges"])  # stable: ties broken by node array index, NEVER by clock/random
    parts = [_emit_header_comment(graph), _emit_meta(graph, order),
             _emit_helpers(), _emit_body_open(graph),
             _emit_topology(graph, order), _emit_body_close()]
    return "\n".join(parts)
```

## B. EMIT ALGORITHM (graph.json field -> JS construct)

1) meta (PURE LITERAL, required first export):
   - meta.name        = graph.harness_name
   - meta.description = "<harness_name> harness (Mode A, emitted from graph.json schema_version <schema_version>)"
   - meta.phases      = one {title, detail} per node in toposort order; title=node.id, detail="agent=<agent> model=<model> mech=<decision_mechanism>"
   NO computed expressions inside meta (API constraint).

2) topology -> scheduler:
   - topology=="pipeline":  emit `pipeline([SEED], stage_<id0>, stage_<id1>, ...)` where stages follow toposort of edges; seed is a 1-element array `[args]`; each stage cb is `async (prev,item,i)=> <node-call>` and RETURNS the node output so it flows to the next stage. (pipeline has NO barrier between stages — correct, each node depends only on its predecessor's return.)
   - topology=="dispatch": emit `parallel([ ()=>node_<id0>(seed), ()=>node_<id1>(seed), ... ])` (BARRIER, fan-out of independent nodes over same seed) then a final reduce/synthesis node if a sink node exists in edges.
   - topology=="producer-reviewer": emit a `while` loop (producer -> reviewer -> break on reviewer.approved || round>=max_rounds), bounded by node.max_rounds.

3) EACH node -> one async fn `node_<id>(input)` that internally applies decision_mechanism, reads node.inputs (logged), calls the agent() wrapper, and does nothing else (writes happen inside the sub-agent per write_paths/harness.lock; emitter does not write files).

4) decision_mechanism -> EXACT JS wrapper (heart of the component):

   single:
   ```js
   async function node_gather(input){
     phase("gather"); log(`gather <- ["_workspace/00_input/query.md"]`);
     return await agent(P.gather(input), { label:"gather", phase:"gather",
       model:"haiku", schema:S.findings, agentType:"researcher" });
   }
   ```

   majority-vote (mechanism_params {n,quorum,tie_break}): parallel(N voters, model=node.model) + PURE-JS deterministic reduce. tie_break MUST be deterministic: "first"=lowest voter index. NO Math.random.
   ```js
   async function node_X(input){ phase("X"); const N=5,quorum=3,tieBreak="first";
     const votes=(await parallel(Array.from({length:N},(_,k)=>()=>
       agent(P.X(input,k),{label:`X#${k}`,phase:"X",model:"haiku",schema:S.s})))).filter(Boolean);
     return reduceMajority(votes,quorum,tieBreak); }   // pure helper, see C
   ```

   debate-with-judge (mechanism_params {n?,max_rounds,judge}): loop max_rounds collecting debater turns (model=sonnet), then ONE judge agent (model=mechanism_params.judge||"opus", schema=node.output_schema).
   ```js
   async function node_X(input){ phase("X"); const maxRounds=2; let transcript=[];
     for(let r=0;r<maxRounds;r++){ const turns=(await parallel(Array.from({length:2},(_,k)=>()=>
       agent(P.debater(input,transcript,r,k),{label:`debater#${k}.r${r}`,phase:"X",model:"sonnet"})))).filter(Boolean);
       transcript=transcript.concat(turns);}
     return await agent(P.judge(input,transcript),{label:"judge",phase:"X",model:"opus",schema:S.s}); }
   ```

   reflect-then-revise (mechanism_params {max_rounds,critic}): loop(critic->reviser) bounded by max_rounds; critic=mechanism_params.critic||"opus", reviser=node.model||"sonnet"; break early when critic.approved.
   ```js
   async function node_verify(input){ phase("verify"); const maxRounds=2; let draft=input;
     for(let r=0;r<maxRounds;r++){
       const crit=await agent(P.critic(draft,r),{label:`critic.r${r}`,phase:"verify",model:"opus",schema:S.critique});
       if(!crit||crit.approved) break;
       draft=await agent(P.reviser(draft,crit,r),{label:`reviser.r${r}`,phase:"verify",model:"sonnet",schema:S.findings});}
     return draft; }
   ```

5) node.model -> agent({model}); node.output_schema -> agent({schema:S.<key>}) where S maps a schema-file path to an INLINED JSONSchema loaded at EMIT time (runtime needs no fs). output_schema=="" -> omit schema (free text). node.agent -> agent({agentType:<agent>}).

6) Prompts: emitter generates `const P={...}` of prompt-builder closures, one per role used; each embeds node.inputs paths + instructions; varied across parallel branches by an INTEGER index arg (k/r), NEVER by random (satisfies "vary by agent index/label").

## C. BUDGET GUARD + PRE-FLIGHT COST BAND (emitted)

- budget.total_tokens -> `budget.total` is the workflow's native HARD ceiling (Workflow enforces: agent() THROWS once spent()>=total). Emitter does NOT re-implement counting; it ADDS a soft guard before each expensive group:
  ```js
  function ensure(min){ if(budget.total && budget.remaining()<min){
    log(`budget guard: remaining ${budget.remaining()} < ${min}; aborting group`); throw new Error("BUDGET_GUARD"); } }
  ```
  Placed before majority-vote fan-outs / debate rounds (cost multipliers). A thrown BUDGET_GUARD inside a parallel thunk -> null -> filtered, so partial results survive.
- approval_required==true -> band is NOT computed at runtime (no clock/IO at emit). The EMITTER prints a STATIC pre-flight estimate as a leading block comment AND returns it: band = sum over nodes of (mechanism_call_count * model_tier_unit_cost), call_count: single=1, majority=n, debate=n*max_rounds+1, reflect=2*max_rounds; tiers haiku<sonnet<opus. Emitted as `// PRE-FLIGHT COST BAND: ~min..max tokens across K calls (haiku x_, sonnet x_, opus x_)`. The CLI/orchestrator shows this band for approval BEFORE Workflow({scriptPath}). This is the only feasible "live budget" surface (platform constraint 3: no mid-flight cross-session token aggregation hook).

## D. RESUME (resumeFromRunId -> partial re-run)

- Resume: `Workflow({ scriptPath:"<harness>/.harness/workflow.js", resumeFromRunId:"<id>" })`.
- Relied-upon Workflow semantics: unchanged agent() call PREFIX returns cached results; FIRST changed/new agent() call onward re-runs live. So emitter MUST keep agent() ORDER and LABELS stable across re-emits:
  * Deterministic toposort (ties by array index) => stable call order.
  * Stable label per call: "<id>", "<id>#<k>", "critic.r<r>" — from node.id+index only, never time/random.
  * Prompts vary by index, not RNG => identical inputs across runs => cache-valid.
- Editing node verify (e.g. bump max_rounds) re-emits the file; resume re-runs gather/fetch from cache and re-executes verify-onward live (M0 success criterion 2).

## E. EMITTER INVARIANTS (assert before returning)

1. Output begins with `export const meta = {` (pure literal). 2. No occurrence of the current-time built-in or the random built-in anywhere in output. 3. Every agent() has model in {haiku,sonnet,opus} and a label. 4. Concurrency never exceeds caps: N<=5 voters, debaters<=5 (enforced upstream by MAX_VOTERS/MAX_FANOUT). 5. Every node in graph.nodes appears exactly once as node_<id>. 6. schema objects inlined (no runtime fs read).

## DEEP-RESEARCH INSTANCE
## FULL EMITTED workflow.js for the deep-research M0 dogfood
# graph.json drives this: topology=pipeline, execution_mode=workflow, budget.total_tokens=600000,
# nodes gather(haiku,single) -> fetch(haiku,single) -> verify(reflect-then-revise critic=opus/reviser=sonnet,max_rounds=2) -> synthesize(opus,single)
# edges: gather->fetch->verify->synthesize. Combo = "Pipeline + reflect-then-revise" (strategy D-4 release combo #1).
# Literal file the emitter writes to deep-research/.harness/workflow.js:

```js
// AUTO-EMITTED by emit_workflow.py from graph.json (schema_version 0.1). DO NOT EDIT BY HAND.
// Edit graph.json and re-emit; resume re-runs only from the first changed agent() call.
// PRE-FLIGHT COST BAND: ~95k..600k tokens across up to 7 agent calls
//   (haiku x2: gather,fetch | opus x2: critic.r0,critic.r1 | sonnet x2: reviser.r0,reviser.r1 | opus x1: synthesize)
//   budget.total = 600000 (HARD ceiling). approval_required=true -> show this band before running.

export const meta = {
  name: "deep-research",
  description: "deep-research harness (Mode A, emitted from graph.json schema_version 0.1)",
  phases: [
    { title: "gather",     detail: "agent=researcher model=haiku mech=single" },
    { title: "fetch",      detail: "agent=fetcher model=haiku mech=single" },
    { title: "verify",     detail: "agent=verifier model=sonnet mech=reflect-then-revise critic=opus" },
    { title: "synthesize", detail: "agent=synthesizer model=opus mech=single" }
  ]
};

export default async function ({ agent, parallel, pipeline, phase, log, budget, args }) {
  // ---- inlined schemas (from graph.node.output_schema; no runtime fs) ----
  const S = {
    findings: { type:"object", required:["claims","sources"], properties:{
      claims:{type:"array",items:{type:"object",required:["id","text","source_ids","confidence"],
        properties:{id:{type:"string"},text:{type:"string"},
          source_ids:{type:"array",items:{type:"string"}},confidence:{type:"number"}}}},
      sources:{type:"array",items:{type:"object",required:["id","url","title"],
        properties:{id:{type:"string"},url:{type:"string"},title:{type:"string"}}}}}},
    critique: { type:"object", required:["approved","issues"], properties:{
      approved:{type:"boolean"},
      issues:{type:"array",items:{type:"object",required:["claim_id","problem","severity"],
        properties:{claim_id:{type:"string"},problem:{type:"string"},
          severity:{type:"string",enum:["low","med","high"]}}}}}},
    report: { type:"object", required:["title","markdown","citations"], properties:{
      title:{type:"string"}, markdown:{type:"string"},
      citations:{type:"array",items:{type:"object",required:["source_id","url"],
        properties:{source_id:{type:"string"},url:{type:"string"}}}}}}
  };

  // ---- budget soft-guard (native budget.total is the HARD ceiling; this avoids half-spent fan-outs) ----
  function ensure(min){
    if (budget.total && budget.remaining() < min){
      log(`budget guard: remaining ${budget.remaining()} < ${min}; aborting group`);
      throw new Error("BUDGET_GUARD");
    }
  }

  // ---- prompt builders (vary ONLY by index r; no clock, no random) ----
  const P = {
    gather: (q) => `You are a research gatherer. Query (from _workspace/00_input/query.md):\n${q}\n`+
      `Fan out web searches, propose candidate sources and draft claims. Return JSON per schema (claims+sources).`,
    fetch: (prev) => `Given these candidate sources & draft claims:\n${JSON.stringify(prev)}\n`+
      `Fetch/read each source, attach source_ids to claims, drop unsupported claims, set confidence. Return JSON per schema.`,
    critic: (draft, r) => `Adversarial fact-checker, round ${r}. Findings:\n${JSON.stringify(draft)}\n`+
      `Find unsupported/overstated/miscited claims. If all claims are source-backed, set approved=true. Return critique JSON.`,
    reviser: (draft, crit, r) => `Reviser, round ${r}. Findings:\n${JSON.stringify(draft)}\n`+
      `Critique to address:\n${JSON.stringify(crit.issues)}\n`+
      `Fix or remove each flagged claim; keep source_ids accurate. Return corrected findings JSON.`,
    synth: (findings) => `Synthesize a cited research report from verified findings:\n${JSON.stringify(findings)}\n`+
      `Every sentence with a fact must carry an inline [source_id] citation. Return report JSON (title, markdown, citations).`
  };

  // ---- nodes (one async fn per graph node) ----
  async function node_gather(input){
    phase("gather"); log(`gather <- ["_workspace/00_input/query.md"]`);
    return await agent(P.gather(input),
      { label:"gather", phase:"gather", model:"haiku", agentType:"researcher", schema:S.findings });
  }

  async function node_fetch(prev){
    phase("fetch"); log(`fetch <- gather.findings`);
    return await agent(P.fetch(prev),
      { label:"fetch", phase:"fetch", model:"haiku", agentType:"fetcher", schema:S.findings });
  }

  // decision_mechanism = reflect-then-revise (max_rounds=2, critic=opus, reviser=sonnet)
  async function node_verify(prev){
    phase("verify"); log(`verify <- fetch.findings (reflect-then-revise, max_rounds=2)`);
    const maxRounds = 2;
    let draft = prev;
    for (let r = 0; r < maxRounds; r++){
      ensure(20000);
      const crit = await agent(P.critic(draft, r),
        { label:`critic.r${r}`, phase:"verify", model:"opus", agentType:"verifier", schema:S.critique });
      if (!crit || crit.approved){ log(`verify: critic approved at round ${r}`); break; }
      draft = await agent(P.reviser(draft, crit, r),
        { label:`reviser.r${r}`, phase:"verify", model:"sonnet", agentType:"verifier", schema:S.findings });
    }
    return draft;
  }

  async function node_synthesize(prev){
    phase("synthesize"); log(`synthesize <- verify.findings`);
    ensure(30000);
    return await agent(P.synth(prev),
      { label:"synthesize", phase:"synthesize", model:"opus", agentType:"synthesizer", schema:S.report });
  }

  // ---- topology = pipeline (edges: gather->fetch->verify->synthesize). One seed item flows all stages. ----
  const seed = (args && args.query) ? args.query : "(query.md provided in _workspace/00_input/)";
  const [report] = await pipeline(
    [seed],
    async (prev) => await node_gather(prev),
    async (prev) => await node_fetch(prev),
    async (prev) => await node_verify(prev),
    async (prev) => await node_synthesize(prev)
  );
  log(`done: ${report ? report.title : "no report (budget guard or empty)"}`);
  return report;
}
```

# Invocation (M0 dogfood, C2=CYS arm):
#   Workflow({ scriptPath:"deep-research/.harness/workflow.js", args:{ query:"<topic>" } })
# Resume after editing verify.max_rounds in graph.json then re-emit:
#   Workflow({ scriptPath:"deep-research/.harness/workflow.js", resumeFromRunId:"<runId>" })
#   -> gather & fetch return cached; verify-onward re-runs live (success criterion 2).

## READS
['<harness>/.harness/graph.json (the spine: execution_mode, topology, budget, nodes[].{id,agent,model,decision_mechanism,mechanism_params,inputs,outputs,output_schema,max_rounds}, edges[])', '<harness>/.claude/agents/*.md (referential check: every node.agent must resolve to a file)', '<harness>/schemas/*.json (each non-empty node.output_schema is loaded and INLINED into the emitted S table at emit time)']

## WRITES
['<harness>/.harness/workflow.js (the single emitted artifact; the only output of this component)', '(returned alongside) the static PRE-FLIGHT COST BAND string the CLI/orchestrator shows for approval_required gating']

## EDGE CASES
- graph.execution_mode != 'workflow' -> emitter refuses; caller routes to Mode B (graph.json contract only, no .js).
- node.agent has no matching .claude/agents/<agent>.md -> emit FAILS (build break) — satisfies M0 success criterion 3 family (broken agent ref fails validate/build).
- node.output_schema points to missing/invalid JSON file -> emit fails (cannot inline schema).
- topology=pipeline but edges form a cycle or a node is unreachable -> toposort throws; emit fails with the offending node id.
- majority-vote n is even and quorum unsatisfiable, or n>MAX_VOTERS(5) -> emit fails (caps enforced; tie_break must be deterministic, never random).
- A voter/debater/stage thunk throws at RUNTIME -> Workflow turns it to null; helpers filter Boolean so the run degrades to partial results instead of crashing (matches on_exhaust intent 'proceed-with-gap').
- budget.total reached mid-run -> native budget makes the next agent() THROW; emitted ensure() pre-empts half-spent fan-outs; pipeline returns whatever completed (report may be null -> logged).
- reflect critic returns approved=true on round 0 -> loop breaks, reviser never called (fewer tokens than the cost-band max — band is an upper bound, correct for approval).
- user skips an agent() prompt -> agent() returns null; downstream node receives null prev -> its prompt embeds 'null' and the run continues degraded (no crash), surfaced in final log line.
- graph edited and re-emitted with SAME node ids/order -> resume cache stays valid for unchanged prefix; only changed-node-onward labels re-run. Reordering nodes invalidates cache from the first moved call (documented, expected).

## FEASIBILITY
Maps 1:1 onto REAL Workflow-tool primitives, no invented surface. (A) meta is a pure object literal as required — all dynamism lives in the default-export body. (B) pipeline()/parallel() used exactly per API: pipeline has no inter-stage barrier and each stage returns the value the next consumes; parallel is a barrier with throwing-thunk->null, so majority-vote/debate fan-outs filter Boolean. (C) budget: the HARD ceiling is the tool's own budget.total (agent() throws at spent>=total) — the emitter does NOT and CANNOT re-aggregate per-call tokens across sessions mid-flight (platform constraint 3); the only added surface is a static pre-flight cost band (constraint 3a) plus an ensure() soft guard to avoid half-spent groups. (D) Determinism for resume: NO use of the wall-clock or RNG built-ins anywhere (API forbids them — they break resume); all variation is by integer index/label (k,r) — so the unchanged agent() prefix stays cache-valid and resumeFromRunId yields true partial re-run (constraint 6 / success criterion 2). (E) Model tiers follow strategy D-3 defaults (gather/fetch=haiku, reviser=sonnet, critic/synthesize=opus) and are validated upstream (opus-on-pure-retrieval flagged). Constraints explicitly respected: no TeamCreate/SendMessage (Mode B, LLM-turn only — constraint 1); no depends_on graph (edges are emit-time ordering for pipeline/parallel only — constraint 2); no live abort hook / no-progress watchdog (constraints 3,4 — replaced by budget.total + pre-flight band); no durable team-resume (constraint 5 — replaced by Workflow's own scriptPath+resumeFromRunId, the real resume substrate per constraint 6). Concurrency stays within min(16,cores-2) because MAX_VOTERS/MAX_FANOUT=5 cap fan-out upstream.

## OPEN QUESTIONS
- Does Workflow's resume cache key include the prompt STRING, or only call ordinal+label? If it keys on prompt text, editing an upstream node's prompt TEMPLATE (not its params) invalidates downstream cache even when that node's OUTPUT is unchanged — affects how surgically resume re-runs. Needs one empirical probe against the real tool before M1.
- Exact unit-cost numbers for the pre-flight band: spec uses tier-relative ordering (haiku<sonnet<opus) with placeholder token estimates. M0 should backfill real per-tier averages from SubagentStop token logging (the post-hoc reporting surface) so the band is calibrated, not guessed.
- For topology=dispatch with MORE than one sink node in edges, is the final reduce a single synthesis agent() or a deterministic JS merge? Spec assumes single-sink; multi-sink dispatch needs a rule (defer to M1 with dispatch+majority-vote release combo #2).
- Should ensure() thresholds (20k verify / 30k synth) be emitted as fixed constants or derived from the band per-node? Fixed is simpler for M0; derive in M1 once band is calibrated.