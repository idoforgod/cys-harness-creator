# head-to-head eval harness (deep-research) — the 3-way falsifiability benchmark (graph.json field: this is the build gate referenced by D-9; consumes any harness's `outputs` and emits a provenance-stamped report)

## PURPOSE
Make "CYS measurably surpasses the original harness" falsifiable for the deep-research M0 dogfood. It runs the SAME deep-research query through three conditions — C1 = original revfactory/harness output, C2 = CYS harness output (the emitted workflow.js, execution_mode=workflow), C3 = no-harness single agent — then grades all three against a gold-labeled set of discriminating assertions using a blind, calibrated, multi-run protocol, and emits one report.json with a provenance stamp and a numeric win condition. The decisive design choice vs the original: it MUST report domains/assertion-classes where CYS does NOT win. It is a release-time gate (run once per release, not per skill), and its result is one of the M0 success criteria ("C2 shows measured advantage, or honest under-report").

## CONTRACT
## 1. FIXTURE FORMAT — `evals/h2h/deep-research.fixture.json`

A fixture is ONE real deep-research query + a gold-labeled discriminating-assertion set. "Discriminating" = the assertion separates a thorough, source-verified harness run from a shallow single-agent run. Each assertion is independently checkable from the report text the condition produces. `gold_value` is the ground truth; `polarity` says whether a correct report should AFFIRM or REFUTE it (refute-traps catch ungrounded/hallucinated claims).

```jsonc
{
  "fixture_schema_version": "0.1",
  "fixture_id": "dr-eu-ai-act-gpai-2026",
  "domain": "deep-research",
  "query": "What obligations does the EU AI Act impose specifically on providers of general-purpose AI (GPAI) models, what is the staggered timeline for those obligations entering into application, and how do obligations differ for GPAI models classified as posing systemic risk?",
  "query_md_path": "_workspace/00_input/query.md",   // written verbatim; matches graph.json nodes[gather].inputs
  "as_of_date": "2026-05-29",                          // freezes ground truth; graders judge against this date
  "min_distinct_sources_expected": 5,                  // used by A7 source-grounding assertion
  "assertions": [
    {
      "id": "A1",
      "class": "factual-core",
      "text": "The AI Act entered into force on 1 August 2024.",
      "gold_value": "1 August 2024",
      "polarity": "affirm",
      "discriminates": "Date precision — single agents often give the year or a vague 'mid-2024'.",
      "weight": 1.0
    },
    {
      "id": "A2",
      "class": "factual-core",
      "text": "GPAI-model obligations (Chapter V) become applicable 12 months after entry into force, i.e. on 2 August 2025.",
      "gold_value": "2 August 2025 (12 months after entry into force)",
      "polarity": "affirm",
      "discriminates": "Requires distinguishing the GPAI-specific date from the generic 2026/2027 dates — a common conflation.",
      "weight": 1.5
    },
    {
      "id": "A3",
      "class": "factual-core",
      "text": "GPAI models trained with cumulative compute greater than 10^25 FLOPs are presumed to pose systemic risk.",
      "gold_value": "10^25 FLOPs (cumulative training compute)",
      "polarity": "affirm",
      "discriminates": "Specific numeric threshold; hallucinations cluster at 10^23/10^24/10^26.",
      "weight": 1.5
    },
    {
      "id": "A4",
      "class": "obligation-coverage",
      "text": "All GPAI providers must draw up and keep up-to-date technical documentation of the model (incl. training/testing process) and make information available to downstream providers.",
      "gold_value": "Art. 53: technical documentation + downstream information/documentation",
      "polarity": "affirm",
      "discriminates": "Tests whether the report enumerates the BASE-tier obligations, not just the systemic-risk ones.",
      "weight": 1.0
    },
    {
      "id": "A5",
      "class": "obligation-coverage",
      "text": "All GPAI providers must put in place a policy to comply with EU copyright law and publish a sufficiently detailed summary of training-data content.",
      "gold_value": "Art. 53(1)(c)-(d): copyright policy + public training-data summary",
      "polarity": "affirm",
      "discriminates": "Frequently omitted by shallow runs that only cover 'risk' obligations.",
      "weight": 1.0
    },
    {
      "id": "A6",
      "class": "differential",
      "text": "Systemic-risk GPAI providers carry ADDITIONAL obligations beyond base-tier: model evaluation/adversarial testing, systemic-risk assessment and mitigation, serious-incident tracking and reporting to the AI Office, and adequate cybersecurity protection.",
      "gold_value": "Art. 55: eval+adversarial testing, risk assessment/mitigation, incident reporting to AI Office, cybersecurity",
      "polarity": "affirm",
      "discriminates": "The CORE differential the query asks for; tests synthesis, not just retrieval. Partial credit per sub-item (see grading).",
      "weight": 2.0
    },
    {
      "id": "A7",
      "class": "source-grounding",
      "text": "The report's load-bearing claims are attributed to >= 5 distinct primary/authoritative sources (e.g. EUR-Lex Regulation (EU) 2024/1689, European Commission AI Office pages, official GPAI Code of Practice).",
      "gold_value": ">=5 distinct authoritative sources with inline attribution",
      "polarity": "affirm",
      "discriminates": "Pure-retrieval depth; C3 single agent typically cites 0-2 or fabricates.",
      "weight": 1.5
    },
    {
      "id": "A8",
      "class": "refute-trap",
      "text": "The AI Act bans all general-purpose AI models above the systemic-risk compute threshold from the EU market.",
      "gold_value": "FALSE — there is no ban; systemic-risk models face additional obligations, not prohibition.",
      "polarity": "refute",
      "discriminates": "Anti-hallucination trap. A correct report must NOT assert this, and ideally explicitly contradicts it. Asserting it = fail.",
      "weight": 1.5
    }
  ]
}
```

Total weight = 11.5. `weighted_pass_rate = sum(weight over passed assertions) / sum(all weights)`. Each condition's score on a run is a weighted pass-rate in [0,1].

## 2. RUNNER — how C1/C2/C3 are produced and collected

The runner is itself a Workflow tool script (`evals/h2h/runner.workflow.js`) so the eval inherits budget ceiling + resume + structured output. It is NOT the harness under test; it is a meta-driver that invokes each condition as an isolated subagent and writes raw outputs to disk.

```js
export const meta = {
  name: "h2h-deep-research",
  description: "3-way head-to-head: C1 original harness vs C2 CYS vs C3 no-harness, n runs, blind grading.",
  phases: [
    { title: "produce", detail: "Run C1/C2/C3 N times each into raw output files" },
    { title: "grade",   detail: "Blind, calibrated, 2-grader-on-contested grading" },
    { title: "report",  detail: "Median pass-rate + variance + win condition + provenance stamp" }
  ]
};

export default async function ({ agent, parallel, pipeline, phase, log, budget, args }) {
  const fx = args.fixture;                 // parsed deep-research.fixture.json
  const N  = args.n_runs ?? 3;             // n in {3,4,5}; median taken
  const seed = args.seed;                  // recorded blinding seed (no RNG builtin; derive from this)

  // ---- PRODUCE ----
  // Each condition is a subagent given ONLY the query (never the assertions).
  // Vary by run INDEX (no wall-clock / RNG allowed in workflow scripts).
  phase("produce");
  const runIdx = [...Array(N).keys()];

  async function produceC1(i) {            // ORIGINAL harness: prose .md harness, team/sub per its own design
    return agent(promptC1(fx.query, i), { label:`C1_r${i}`, phase:"produce", model:"opus", isolation:"worktree",
      schema: RAW_OUTPUT_SCHEMA });
  }
  async function produceC2(i) {            // CYS harness: invoke the EMITTED workflow.js (execution_mode=workflow)
    return agent(promptC2(fx.query, i), { label:`C2_r${i}`, phase:"produce", model:"opus", isolation:"worktree",
      schema: RAW_OUTPUT_SCHEMA });        // prompt instructs: run .harness/workflow.js via Workflow({scriptPath}) on the query
  }
  async function produceC3(i) {            // NO harness: one plain subagent, web tools, no orchestration scaffold
    return agent(promptC3(fx.query, i), { label:`C3_r${i}`, phase:"produce", model:"opus",
      schema: RAW_OUTPUT_SCHEMA });
  }

  // barrier over all 3N producer runs
  const raw = await parallel(
    runIdx.flatMap(i => [() => tag("C1",i,produceC1(i)),
                         () => tag("C2",i,produceC2(i)),
                         () => tag("C3",i,produceC3(i))])
  ).then(a => a.filter(Boolean));
  // each raw entry: { condition, run, report_md, sources[], token_cost, run_id }

  // ---- GRADE ---- (see grader protocol)
  phase("grade");
  const graded = await gradeAll({ raw, fx, seed, agent, parallel });

  // ---- REPORT ----
  phase("report");
  return buildReport({ graded, raw, fx, N, seed });  // -> report.json (schema below)
}
```

Collection rules:
- **C1 (original harness):** prompt the producer subagent to act as the original revfactory/harness would — i.e. follow the original harness `.md` scaffold checked into `evals/h2h/baselines/original-harness/` and produce a cited report. `isolation:'worktree'` so its writes don't collide. Token cost captured from the subagent's reported usage (post-hoc, via the returned schema field; live mid-flight aggregation is NOT feasible per platform constraint).
- **C2 (CYS harness):** producer subagent runs the CYS-emitted `.harness/workflow.js` against the query via `Workflow({scriptPath})`. This exercises the REAL Mode A spine: `budget.total` ceiling, `pipeline()`/`parallel()` over the graph.json `edges`, `agent({schema})` from `output_schema`. Its report is `_workspace/02_synth/report.md` (the deep-research harness's terminal output).
- **C3 (no harness):** single subagent, identical query, web search/fetch allowed, NO orchestration, NO multi-agent scaffold, NO assertion exposure. This is the floor.
- All three get the **identical** `query.md`; none ever sees `assertions[]`. Each produces a `report_md` + `sources[]` + self-reported `token_cost`.

`RAW_OUTPUT_SCHEMA` (forces StructuredOutput on each producer):
```json
{ "type":"object","required":["report_md","sources","token_cost"],
  "properties":{
    "report_md":{"type":"string"},
    "sources":{"type":"array","items":{"type":"object","required":["url","title"],
      "properties":{"url":{"type":"string"},"title":{"type":"string"}}}},
    "token_cost":{"type":"integer","description":"self-reported total tokens for this run; post-hoc only"}
  }, "additionalProperties": false }
```

## 3. GRADER PROTOCOL

Goal: a per-(condition,run) weighted pass-rate that is blind, calibrated, and robust on contested assertions.

a) **Blinding (label-strip + order-randomization, recorded seed):**
   - Strip every condition label from `report_md` before grading. Assemble a grading queue of `3*N` anonymized reports keyed by an opaque `blind_id`.
   - Deterministically permute the queue using `seed` (NO RNG builtin — use a pure index hash: `order = stableShuffle(blind_ids, seed)`; record both `seed` and the resulting `order[]` in the report).
   - The grader subagent receives: the fixture `assertions[]` + one anonymized report. It never sees the condition, the run index, or the other reports.

b) **Per-assertion judgment:** grader returns, for each assertion, `pass | fail` plus a one-line `rationale` and `confidence` in {high, low}. Polarity matters: an `affirm` assertion passes iff the report supports `gold_value`; a `refute` assertion passes iff the report does NOT assert the false claim (and ideally contradicts it). A6 (the differential) is graded with **partial credit**: 4 sub-items, score = (sub-items present)/4, contributes `weight * fraction`.

c) **Gold-seeded calibration:** before grading the real queue, the grader scores 2 **calibration reports** with known gold pass-rates that ship in the fixture pack (`evals/h2h/calib/gold_pass.md` ~ expected 1.0, `evals/h2h/calib/gold_fail.md` ~ expected ~0.25). If the grader's calibration score deviates by > 0.15 from the known value on either, the grader is rejected and re-spawned (up to `node.retries`). This is the grading analogue of `graph.json` `retries` / `on_exhaust`.

d) **2-grader majority on contested:** primary grader (`model:"sonnet"`) scores all reports. Any assertion it marks `confidence:"low"` is **contested** and re-graded by an independent second grader (`model:"opus"`, fresh subagent, same blind input). If the two disagree, a third tie-break grader (`model:"opus"`) resolves it; majority wins. Non-contested assertions stand on the single grader. (No external scheduler needed — all graders are `agent()` calls inside the workflow.)

e) **n=3-5 median + variance:** for each condition, take the **median** weighted pass-rate across its N runs (robust to one bad run) and report **variance** (population variance of the N run scores). Median is the headline; variance is the honesty signal.

`GRADER_SCHEMA`:
```json
{ "type":"object","required":["blind_id","judgments"],
  "properties":{
    "blind_id":{"type":"string"},
    "judgments":{"type":"array","items":{"type":"object",
      "required":["assertion_id","result","confidence","rationale"],
      "properties":{
        "assertion_id":{"type":"string"},
        "result":{"enum":["pass","fail","partial"]},
        "partial_fraction":{"type":"number"},
        "confidence":{"enum":["high","low"]},
        "rationale":{"type":"string"}}}}
  }, "additionalProperties": false }
```

## 4. REPORT SCHEMA — `evals/h2h/runs/<stamp>/report.json`

```jsonc
{
  "report_schema_version": "0.1",
  "provenance": {
    "schema_version": "0.1",            // graph.json schema_version under test
    "model_id": "claude-opus-4-8",      // producer model id, captured at run
    "grader_model_ids": ["claude-sonnet-4-x","claude-opus-4-8"],
    "harness_name": "deep-research",
    "harness_version": "0.1.0",         // graph.json harness_version of C2
    "original_harness_ref": "revfactory/harness@v1.2.0",  // C1 baseline pin
    "git_sha": "<sha of CYS harness repo at run>",
    "n_runs": 3,
    "blind_seed": "<seed>",
    "blind_order": ["<blind_id>", "..."],   // recorded permutation
    "fixture_id": "dr-eu-ai-act-gpai-2026",
    "as_of_date": "2026-05-29",
    "run_timestamp": "<stamped AFTER run; not from in-script clock>"
  },
  "per_condition": {
    "C1": { "median_pass_rate": 0.0, "variance": 0.0, "run_scores": [], "median_token_cost": 0 },
    "C2": { "median_pass_rate": 0.0, "variance": 0.0, "run_scores": [], "median_token_cost": 0 },
    "C3": { "median_pass_rate": 0.0, "variance": 0.0, "run_scores": [], "median_token_cost": 0 }
  },
  "per_assertion_class": {               // honesty granularity: where does CYS win / not win
    "factual-core":       { "C1":0.0,"C2":0.0,"C3":0.0 },
    "obligation-coverage":{ "C1":0.0,"C2":0.0,"C3":0.0 },
    "differential":       { "C1":0.0,"C2":0.0,"C3":0.0 },
    "source-grounding":   { "C1":0.0,"C2":0.0,"C3":0.0 },
    "refute-trap":        { "C1":0.0,"C2":0.0,"C3":0.0 }
  },
  "win_condition": {
    "spec": "C2_median >= C1_median + 0.15 AND C2_median >= C3_median + 0.15",   // 15pp hypothesis values
    "margin_over_C1_pp": 0.0,
    "margin_over_C3_pp": 0.0,
    "domains_evaluated": 1,             // M0 = deep-research only; M1 extends to 3 with ">=2/3 domains" gate
    "passed": false
  },
  "cost_normalized": {                   // win must be reported alongside cost
    "C2_pass_per_100k_tokens": 0.0,
    "C1_pass_per_100k_tokens": 0.0,
    "C3_pass_per_100k_tokens": 0.0
  },
  "honest_losses": [                     // MANDATORY: assertion-classes/assertions where C2 did NOT beat C1 or C3 by 15pp
    // { "scope":"source-grounding", "C2":0.6, "C1":0.7, "note":"original harness cited more primary law texts" }
  ],
  "verdict": "WIN | NO-WIN | MIXED",     // MIXED => some classes win, honest_losses non-empty
  "contested_count": 0,
  "calibration": { "gold_pass_observed": 1.0, "gold_fail_observed": 0.25, "grader_accepted": true }
}
```

## 5. NUMERIC WIN CONDITION + HONESTY RULE
- **Win (M0, single domain):** `C2_median >= C1_median + 0.15` AND `C2_median >= C3_median + 0.15` (15pp = hypothesis value, re-tuned from run-log per D-8 residual decision #5).
- **M1 multi-domain:** the same per-domain test must hold on `>= 2/3` domains.
- **Honesty rule (non-negotiable, the differentiator vs original):** `honest_losses[]` MUST enumerate every assertion-class where C2 fails the +15pp margin over EITHER C1 or C3, even when the overall `verdict` is WIN. If `honest_losses` is non-empty but the aggregate passes, `verdict = "MIXED"`. A report with `verdict:"WIN"` and unexamined losses is invalid.
- Cost must always be reported next to the win (`cost_normalized`); a win achieved at 5x tokens is reported as such, not hidden.

## DEEP-RESEARCH INSTANCE
Fixture `dr-eu-ai-act-gpai-2026`: query = EU AI Act GPAI obligations + staggered timeline + systemic-risk differential. 8 gold-labeled discriminating assertions across 5 classes — factual-core (A1 entry-into-force 1 Aug 2024; A2 GPAI date 2 Aug 2025; A3 10^25 FLOPs threshold), obligation-coverage (A4 technical documentation/downstream info; A5 copyright policy + training-data summary), differential (A6 systemic-risk additional obligations, partial-credit over 4 sub-items — the query's core ask), source-grounding (A7 >=5 distinct authoritative sources), refute-trap (A8 the false 'GPAI ban' claim). Total weight 11.5. This query is chosen because it has a frozen, checkable ground truth as of 2026-05-29, and its difficulty gradient (precise dates/thresholds + a synthesis differential + a hallucination trap) is exactly where a real deep-research harness (gather -> verify -> synthesize, matching graph.json nodes `gather`/`verify`) should beat a single agent. C1 runs the original revfactory/harness scaffold; C2 runs the CYS-emitted `.harness/workflow.js` (execution_mode=workflow, topology=pipeline) via Workflow({scriptPath}); C3 is one plain subagent. n=3 runs each, blind-graded, median pass-rate. report.json carries the provenance stamp pinning model_id, harness_version 0.1.0, original_harness_ref revfactory/harness@v1.2.0, git_sha, blind_seed.

## READS
['evals/h2h/deep-research.fixture.json (query + gold assertions)', '_workspace/00_input/query.md (graph.json nodes[].inputs — the query handed identically to C1/C2/C3)', '.harness/workflow.js (the CYS-emitted Mode A spine that C2 executes; produced from graph.json execution_mode=workflow + topology + edges)', 'graph.json (provenance: schema_version, harness_name, harness_version; node.model and node.output_schema inform what C2 actually runs)', 'evals/h2h/baselines/original-harness/ (the C1 original-harness scaffold to reproduce)', 'evals/h2h/calib/gold_pass.md, evals/h2h/calib/gold_fail.md (grader calibration anchors)']

## WRITES
['evals/h2h/runs/<stamp>/raw/{C1,C2,C3}_r<i>.json (raw producer outputs + self-reported token_cost)', 'evals/h2h/runs/<stamp>/graded/<blind_id>.json (per-report grader judgments)', 'evals/h2h/runs/<stamp>/report.json (the provenance-stamped verdict — the release gate artifact)', 'evals/h2h/runs/<stamp>/blind_map.json (blind_id -> condition,run; written AFTER grading to preserve blinding)']

## EDGE CASES
- see edgeCases array above

## FEASIBILITY
Maps cleanly to REAL Claude Code primitives. The runner is a Workflow tool script, so it inherits the verified Mode A guarantees: budget.total ceiling (constraint #6), resumeFromRunId (constraint #5/#6), agent({schema}) StructuredOutput enforcement (#6), and parallel()/pipeline() deterministic scheduling for SUB-agents (#6). All producers and graders are agent() calls — no TeamCreate, so no external-scheduling impossibility (#1) and no TaskCreate depends_on need (#2); ordering is via parallel barrier + sequential phases, not a dependency graph. Token cost is POST-HOC self-report only, honoring constraint #3 (no reliable live cross-session token aggregation hook; only SubagentStop post-hoc reporting is feasible) — cost_normalized is explicitly labeled best-effort. No wall-clock watchdog and no RNG are used (constraint #4 and the Workflow 'no current-time/random builtins' rule): run variation = agent index, blinding = recorded seed via stable hash, run_timestamp stamped after the run. C2 exercising the emitted .harness/workflow.js via Workflow({scriptPath}) is the in-session deterministic substrate (Part C correction) — the eval literally runs the same runtime the harness emits. It honors the graph.json spine field names verbatim (schema_version, harness_name, harness_version, execution_mode='workflow', topology, nodes[].model, nodes[].output_schema, nodes[].inputs, edges, retries, on_exhaust) and only ADDS the eval-layer schemas (fixture, grader, report) with justification, renaming none. Release-cadence (once per release, not per skill) matches D-9 and keeps the decision-mechanism cost multiplier bounded.

## OPEN QUESTIONS
- Is the 15pp margin and n=3 the right starting hypothesis, or should M0 start at n=5 to get usable variance from one fixture? (D-8 leaves the number to run-log re-tuning.)
- Should C1 be a faithful re-run of the original harness scaffold by a subagent, or a one-time frozen captured output committed to baselines/? A frozen capture is cheaper and more reproducible but risks staleness vs model/version drift.
- Partial-credit weighting for A6 (4 equal sub-items) vs weighting the AI-Office incident-reporting sub-item higher — does sub-item weighting bias the differential class?
- Single fixture per domain in M0 is statistically thin; do we need 2-3 fixtures for deep-research before any claim, or is one defensible as a dogfood proof?
- How to authoritatively capture token_cost given only self-report — is SubagentStop hook logging into a per-run file reliable enough to upgrade cost_normalized from best-effort to authoritative?