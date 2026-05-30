// CYS Harness Creator M1 — head-to-head full suite (n-run median + blind + provenance).
// Workflow-tool TEMPLATE (Mode A). Hand-authored to match the emit_workflow.py format:
// `export const meta` + top-level statements; agent/parallel/pipeline/phase/log/budget/
// args are AMBIENT (provided by the runner), NOT imported. NO default export. NO
// wall-clock / NO RNG — runs are varied by INTEGER INDEX only, so the suite is fully
// deterministic and resume-safe (resumeFromRunId re-runs from the first changed agent()).
//
// What it does, n times (run = 0..n-1):
//   C2 = CYS pipeline   : gather -> fetch -> verify(reflect-then-revise) -> synthesize
//   C3 = no-harness      : single opus pass over the same query+assertions
//   BLIND GRADE          : strip condition labels, hand the grader (A,B) with a
//                          DETERMINISTIC A=C2 / B=C3 mapping, RECORD that mapping so
//                          the grader cannot infer which side is the harness, then
//                          re-attach c2_pass_rate / c3_pass_rate from the recorded map.
// Returns { runs:[{run,c2_pass_rate,c3_pass_rate,a_is,...},...], provenance } — feed
// the runs[] array to h2h_aggregate.py for the median verdict.
//
// args: { query: string, n: int (default 3), assertions: [{id,text,polarity}],
//         harness_ref?: string (provenance: which harness graph these runs grade) }

export const meta = {
  name: "h2h-suite",
  description: "head-to-head full suite (n-run median + blind grade + provenance) — C2 CYS pipeline vs C3 no-harness baseline",
  phases: [
    { title: "run", detail: "loop run=0..n-1: build C2 + C3, blind-grade A/B" },
    { title: "c2", detail: "CYS pipeline gather(haiku)->fetch(haiku)->verify(sonnet+opus critic)->synthesize(opus)" },
    { title: "c3", detail: "no-harness baseline: single opus pass (agent=baseline)" },
    { title: "grade", detail: "blind A/B grader (opus) vs assertions, A=C2 mapping recorded" },
    { title: "aggregate", detail: "collect per-run scorecards for h2h_aggregate.py" }
  ]
};

  // ---- inlined schemas (mirror emitted workflow.js: schemas live in S.<id>_*) ----
  const S = {
    // C2 pipeline final report (same contract as examples/deep-research report.json).
    report_schema: {"title":"Report","type":"object","additionalProperties":false,"required":["title","markdown","citations"],"properties":{"title":{"type":"string"},"markdown":{"type":"string","description":"Full report body in Markdown. Every factual sentence carries an inline [source_id] citation."},"citations":{"type":"array","items":{"type":"object","additionalProperties":false,"required":["source_id","url"],"properties":{"source_id":{"type":"string"},"url":{"type":"string"}}}}}},
    // intermediate findings (gather/fetch/verify) — claims + sources pool.
    findings_schema: {"title":"Findings","type":"object","additionalProperties":false,"required":["claims","sources"],"properties":{"claims":{"type":"array","items":{"type":"object","additionalProperties":false,"required":["id","text","source_ids","confidence"],"properties":{"id":{"type":"string"},"text":{"type":"string"},"source_ids":{"type":"array","items":{"type":"string"}},"confidence":{"type":"number","minimum":0,"maximum":1}}}},"sources":{"type":"array","items":{"type":"object","additionalProperties":false,"required":["id","url","title"],"properties":{"id":{"type":"string"},"url":{"type":"string"},"title":{"type":"string"}}}}}},
    // verify critic output (reflect-then-revise) — approved breaks the loop early.
    critique_schema: {"title":"Critique","type":"object","additionalProperties":false,"required":["approved","issues"],"properties":{"approved":{"type":"boolean"},"issues":{"type":"array","items":{"type":"object","additionalProperties":false,"required":["claim_id","problem","severity"],"properties":{"claim_id":{"type":"string"},"problem":{"type":"string"},"severity":{"type":"string","enum":["low","med","high"]}}}}}},
    // blind grader verdict over the assertion set for ONE labelled candidate.
    grade_schema: {"title":"Grade","type":"object","additionalProperties":false,"required":["candidate","pass_rate","passed","failed"],"properties":{"candidate":{"type":"string","enum":["A","B"],"description":"Which blind label was graded. Grader never sees the condition."},"pass_rate":{"type":"number","minimum":0,"maximum":1,"description":"fraction of MUST/MUST-NOT assertions satisfied"},"passed":{"type":"array","items":{"type":"string"},"description":"assertion ids satisfied"},"failed":{"type":"array","items":{"type":"string"},"description":"assertion ids violated"}}}
  };

  // ---- budget guard (verbatim from emitted workflow.js) ----
  function ensure(min) {
    if (budget.total && budget.remaining() < min) {
      log(`budget guard: remaining ${budget.remaining()} < ${min}; aborting group`);
      throw new Error("BUDGET_GUARD");
    }
  }

  // ---- StructuredOutput-resilient agent call (P1.4 hardening) ----
  // A schema'd agent() that "completed without calling StructuredOutput" returns null and, if recorded as a
  // 0 pass_rate, silently SKEWS the median (the exact 7/12-failed flakiness seen in the n=5 suite). Here we
  // RETRY up to ATTEMPTS (varying the label so the runner can't return a cached null), and return null only
  // after exhausting — the caller then DROPS the run rather than scoring it 0.
  const ATTEMPTS = (args && Number.isInteger(args.attempts) && args.attempts > 0) ? args.attempts : 3;
  async function tryAgent(prompt, opts) {
    for (let i = 0; i < ATTEMPTS; i++) {
      try {
        const r = await agent(prompt, i === 0 ? opts : Object.assign({}, opts, { label: opts.label + ".retry" + i }));
        if (r) return r;
      } catch (e) { log("tryAgent " + opts.label + " attempt " + i + " threw: " + (e && e.message)); continue; }
      log("tryAgent " + opts.label + " attempt " + i + " produced no StructuredOutput; retrying");
    }
    log("tryAgent " + opts.label + " exhausted " + ATTEMPTS + " attempts -> null (run will be dropped)");
    return null;
  }

  const QUERY = (args && args.query) ? args.query : "(query provided in _workspace/00_input/)";
  const N = (args && Number.isInteger(args.n) && args.n > 0) ? args.n : 3;
  const ASSERTIONS = (args && Array.isArray(args.assertions)) ? args.assertions : [];
  const HARNESS_REF = (args && args.harness_ref) ? args.harness_ref : "examples/deep-research";
  const A_CTX = JSON.stringify(ASSERTIONS);

  // ---- prompt builders (run index varies the run; NO RNG/clock) ----
  const P = {
    gather: (q, run) => "RUN_INDEX:" + run + "\nQUERY:\n" + q +
      "\n\nFollow the researcher agent definition: fan-out web searches, collect candidate sources + draft claims. Return ONLY findings JSON per schema.",
    fetch: (f) => "FINDINGS:\n" + JSON.stringify(f) +
      "\n\nFollow the fetcher agent definition: fetch sources, attach source_ids, drop unsupported claims. Return ONLY findings JSON per schema.",
    verify_critic: (draft, r) => "DRAFT (round " + r + "):\n" + JSON.stringify(draft) +
      "\n\nAdversarially fact-check per the verifier agent definition. If every claim is source-backed set approved=true. Return ONLY critique JSON.",
    verify_reviser: (draft, crit, r) => "DRAFT:\n" + JSON.stringify(draft) + "\nCRITIQUE:\n" + JSON.stringify(crit) +
      "\nRevise to fix every issue (round " + r + "). Return ONLY corrected findings JSON per schema.",
    synthesize: (f) => "VERIFIED FINDINGS:\n" + JSON.stringify(f) +
      "\n\nFollow the synthesizer agent definition: write a cited report, inline [source_id] on every fact. Return ONLY report JSON per schema.",
    // C3 baseline: ONE opus pass, no tools/pipeline, same query+assertions. Same output contract for fair grading.
    baseline: (q, run) => "RUN_INDEX:" + run + "\nQUERY:\n" + q +
      "\nThe answer will be graded against these assertions:\n" + A_CTX +
      "\n\nWrite the best single-pass cited report you can with no harness/tools beyond your own knowledge and reasoning. Return ONLY report JSON per the same Report schema.",
    // BLIND grader: sees a label (A|B) + the report, NEVER the condition. Grades vs assertions.
    grade: (label, report) => "BLIND CANDIDATE " + label + " (you do NOT know which system produced it):\n" + JSON.stringify(report) +
      "\n\nASSERTIONS:\n" + A_CTX +
      "\n\nGrade this candidate. pass_rate = (# MUST and MUST-NOT-VIOLATE assertions satisfied) / (# MUST and MUST-NOT-VIOLATE assertions). List passed[] and failed[] assertion ids. Set candidate=\"" + label + "\". Return ONLY grade JSON per schema."
  };

  // ---- C2: CYS pipeline (gather->fetch->verify reflect-then-revise->synthesize) ----
  async function run_c2(run) {
    phase("c2");
    const [out] = await pipeline(
      [QUERY],
      async (q) => { phase("c2"); ensure(8000); return await tryAgent(P.gather(q, run), { label: "c2.gather.run" + run, phase: "c2", model: "haiku", agentType: "researcher", schema: S.findings_schema }); },
      async (f) => { if (!f) return null; ensure(8000); return await tryAgent(P.fetch(f), { label: "c2.fetch.run" + run, phase: "c2", model: "haiku", agentType: "fetcher", schema: S.findings_schema }); },
      async (f) => {
        if (!f) return null;
        let draft = f;
        for (let r = 0; r < 2; r++) {            // reflect-then-revise, max_rounds=2 (constants.MAX_ROUNDS)
          ensure(20000);
          const crit = await tryAgent(P.verify_critic(draft, r), { label: "c2.verify.critic.r" + r + ".run" + run, phase: "c2", model: "opus", agentType: "verifier", schema: S.critique_schema });
          if (!crit || crit.approved) { log("c2.verify approved at round " + r + " (run " + run + ")"); break; }
          const revised = await tryAgent(P.verify_reviser(draft, crit, r), { label: "c2.verify.reviser.r" + r + ".run" + run, phase: "c2", model: "sonnet", agentType: "verifier", schema: S.findings_schema });
          if (revised) draft = revised;          // a flaky revise keeps the prior draft rather than nulling the run
        }
        return draft;
      },
      async (f) => { if (!f) return null; ensure(30000); return await tryAgent(P.synthesize(f), { label: "c2.synthesize.run" + run, phase: "c2", model: "opus", agentType: "synthesizer", schema: S.report_schema }); }
    );
    return out;
  }

  // ---- C3: no-harness baseline (single opus pass) ----
  async function run_c3(run) {
    phase("c3"); ensure(8000);
    return await tryAgent(P.baseline(QUERY, run), { label: "c3.baseline.run" + run, phase: "c3", model: "opus", agentType: "baseline", schema: S.report_schema });
  }

  // ---- blind grade ONE run: A=C2, B=C3 (DETERMINISTIC mapping, RECORDED) ----
  async function grade_run(run, c2_report, c3_report) {
    phase("grade");
    // Deterministic, recorded label map: A is always C2, B is always C3. The grader is
    // told only "candidate A" / "candidate B" and the assertions — never the condition —
    // so the grade is blind; we re-attach the real condition from this recorded map.
    const a_is = "C2", b_is = "C3";
    ensure(16000);
    const [gradeA, gradeB] = await parallel([
      () => tryAgent(P.grade("A", c2_report), { label: "grade.A.run" + run, phase: "grade", model: "opus", agentType: "grader", schema: S.grade_schema }),
      () => tryAgent(P.grade("B", c3_report), { label: "grade.B.run" + run, phase: "grade", model: "opus", agentType: "grader", schema: S.grade_schema })
    ]);
    // DROP, don't false-zero: a run missing a report or a grade after retries is INVALID and is EXCLUDED from
    // the aggregate, so a StructuredOutput flake can never masquerade as a real 0 and skew the median.
    const valid = !!(c2_report && c3_report
                     && gradeA && typeof gradeA.pass_rate === "number"
                     && gradeB && typeof gradeB.pass_rate === "number");
    if (!valid) {
      log("h2h run " + run + " DROPPED (invalid: missing report/grade after " + ATTEMPTS + " attempts)");
      return { run, valid: false, reason: "missing report or grade after " + ATTEMPTS + " attempts" };
    }
    return {
      run, valid: true,
      a_is, b_is,                                // recorded blind mapping (audit)
      c2_pass_rate: gradeA.pass_rate,            // A=C2
      c3_pass_rate: gradeB.pass_rate,            // B=C3
      c2_passed: gradeA.passed || [],
      c2_failed: gradeA.failed || [],
      c3_passed: gradeB.passed || [],
      c3_failed: gradeB.failed || []
    };
  }

  // ---- main: n runs, collect per-run scorecards (drop invalid runs honestly) ----
  const runs = [];
  let attempted = 0, dropped = 0;
  for (let run = 0; run < N; run++) {
    phase("run"); log("h2h run " + run + " of " + N);
    attempted++;
    const [c2_report, c3_report] = await parallel([
      () => run_c2(run),
      () => run_c3(run)
    ]);
    const scored = await grade_run(run, c2_report, c3_report);
    if (scored.valid) runs.push(scored); else dropped++;
  }
  if (runs.length === 0) log("WARNING: 0 valid runs of " + attempted + " — all dropped (StructuredOutput flakes); raise --attempts or re-run");

  phase("aggregate");
  const result = {
    runs,                                        // -> feed runs[] to h2h_aggregate.py (valid runs only)
    provenance: {
      schema_version: "0.1",
      harness_ref: HARNESS_REF,
      n_runs: N,
      n_attempted: attempted,
      n_valid: runs.length,
      n_dropped: dropped,
      blind_mapping: "A=C2, B=C3 (deterministic, recorded per run)",
      hardening: "StructuredOutput-resilient: each agent retried up to " + ATTEMPTS + "x; a run missing a report/"
        + "grade after retries is DROPPED (not scored 0) so flakes never skew the median",
      note: "model_id + git_sha are stamped by h2h_aggregate.py from CLI/file (not knowable inside Mode A scripts)."
    }
  };
  log("h2h-suite done: " + runs.length + " valid / " + attempted + " attempted (" + dropped + " dropped)");
  return result;
