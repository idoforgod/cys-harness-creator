# DESIGN COMPONENT 4 — The Eval / Parity-Proof Harness + Feature-Parity Matrix

> Master Claude · DESIGN-ONLY pass (locked decision 1: no code written this pass).
> Conforms to locked decisions 1-8 + R1-R4. Sources read first-hand: `/tmp/ido/README.md`,
> `/tmp/ido/skills_harness_SKILL.md` + 6 references, `validate_harness.py`, `lift_gate.py`,
> `h2h_aggregate.py`, `warrant.py`, `emit_orchestrator.py`, `graph.schema.json`,
> `tests/test_factory.py`, `references/testing-and-measurement.md`, `IMPLEMENTATION-STATUS.md`.

This component answers four questions:
- **(a)** The 8-use-case eval design — topology + primitive mix + PASS criteria per case.
- **(b)** The PASS/FAIL definition for "cys-harness-creator works" — the factory self-test + CI/regression.
- **(c)** The feature-parity matrix — every idoforgod feature → CYS mechanism → status.
- **(d)** How `lift_gate` + `h2h` get WIRED INTO the build (currently orphaned).

A foundational note that governs all four: **two eval layers, never conflated.**

| Layer | What is graded | Substrate | Determinism | Tooling |
|---|---|---|---|---|
| **L-factory** (build correctness) | Did the factory EMIT the right harness for the prompt? | pure Python, no agent spawn | byte-deterministic | `validate_harness.py` + new `eval_topology.py` matcher, run in `tests/test_factory.py` |
| **L-runtime** (harness effectiveness) | Does the emitted harness BEAT no-harness baseline? | live `claude` session | statistical (n-run median) | `lift_gate` (per skill) + `h2h_aggregate` (per harness) |

The 8 use cases are graded **primarily at L-factory** (machine-checkable, runs in CI free), and **conditionally at L-runtime** (the expensive head-to-head, gated behind quota — the P5 lesson). This split is the only way to make "all 8 pass" a CI gate without burning a quota window per commit.

---

## (a) THE 8-USE-CASE EVAL DESIGN

### a.0 The matching primitive: `expected_harness` spec

Each use case is a **golden expectation** — a small JSON spec asserting what the factory MUST produce from the exact README prompt. The factory runs (warrant → graph.json → emit_orchestrator → validate), then a new pure matcher `eval_topology.py` compares the emitted artifacts against `expected_harness`. This is the L-factory acceptance test.

```jsonc
// tests/golden/usecases/<case>.expected.json  (the machine-checkable acceptance spec)
{
  "case": "deep-research",
  "prompt": "<EXACT text from /tmp/ido/README.md>",
  "warrant": { "verdict": "build-harness", "topology": "dispatch|pipeline|producer-reviewer" },
  "topology": "dispatch",                       // graph.topology MUST equal this
  "execution_mode_in": ["team", "hybrid"],      // emitted execution_mode MUST be one of these
  "primitive_mix": {                            // R3: full-stack composition assertions
    "orchestrator_skill": true,                 // .claude/skills/<name>-orchestrator/SKILL.md exists
    "agent_defs_min": 3,                        // >=N files in .claude/agents/
    "uses_team_primitive": true,                // SKILL.md names TeamCreate/SendMessage/TaskCreate
    "uses_subagent_primitive": true,            // SKILL.md names Agent(
    "hooks_settings_json": true,                // .claude/settings.json wires the genome+gate hooks
    "domain_skills_min": 1                      // .claude/skills/<non-orchestrator> count (hybrid authoring, decision 5)
  },
  "agents_must_include": ["researcher", "verifier", "synthesizer"],  // role-class presence, fuzzy
  "decision_mechanism_must_include": ["reflect-then-revise"],        // cross-validation present
  "dna": {                                      // R4 + decision 6/7: DNA must FIRE, not lie dormant
    "memory_first_class": true,                 // context-snapshots wired + RLM store declared
    "qa_stack_wired": ["L0","L1","L1.5","L2"],  // gate_or_block hooks present in settings.json
    "cross_run_memory": true                    // .harness/memory/ RLM store + consult step in orchestrator
  },
  "lift_threshold": 0.2,                         // per authored domain skill (Gate 2)
  "h2h_margin_pp": 15                            // C2 vs C3 (Gate 3, run only in the quota-gated lane)
}
```

`eval_topology.py` (new, pure/deterministic, ~120 lines) reads the emitted harness dir + this spec and emits a `<case>.match.json` report with a boolean `pass` and a per-assertion breakdown. **PASS at L-factory = `validate_harness.py` exits 0 AND `eval_topology.py` reports all assertions true.**

### a.1 Why these 8 exercise distinct topologies

The 8 prompts were chosen by idoforgod to span its 6 patterns. CYS's warrant maps each to its `topology × decision_mechanism` algebra. The mapping below is the **design contract** — each `expected.json` encodes one row.

| # | Use case (README prompt intent) | idoforgod pattern | CYS topology | exec_mode | decision_mechanism (key node) | primitive mix highlight |
|---|---|---|---|---|---|---|
| 1 | **Deep Research** — multi-angle (web/academic/community) → cross-validate → report | Fan-out/Fan-in + team | `dispatch` | `team` | `reflect-then-revise` on synth (cross-validate) | TeamCreate fan-out + SendMessage finding-share + sink synth |
| 2 | **Website Development** — design→frontend→backend→QA coordinated pipeline | Hierarchical + pipeline | `pipeline` | `hybrid` | `single` per stage, `reflect-then-revise` at QA | pipeline of sub-agents + team at integration + **incremental QA agent** (qa-guide) |
| 3 | **Webtoon/Comic** — story/char/panel/dialogue, agents review each other | Producer-Reviewer | `producer-reviewer` | `team` | `debate-with-judge` (style-consistency arbitration) | producer↔reviewer SendMessage loop |
| 4 | **YouTube Content Planning** — research/script/SEO/thumbnail, supervisor-coordinated | Supervisor | `dispatch` | `team` | `single` workers + supervisor synth | TeamCreate + TaskCreate shared list (supervisor pattern) |
| 5 | **Code Review & Refactoring** — parallel arch/security/perf/style → merge | Fan-out/Fan-in | `dispatch` | `agent` | `majority-vote` not needed; `single` fan-out + sink merge | parallel `Agent(run_in_background)` fan-out + merge sink |
| 6 | **Technical Documentation** — analyze/write/example/review pipeline | Pipeline | `pipeline` | `agent` | `reflect-then-revise` at review | sequential sub-agents + reviewer node |
| 7 | **Data Pipeline Design** — schema/ETL/validation/monitoring, hierarchical sub-tasks | Hierarchical Delegation | `pipeline` (flattened 2-level) | `hybrid` | `single` + `debate-with-judge` on schema | top sub-agent delegates; flattened to 2 levels (idoforgod's own depth-≤2 rule) |
| 8 | **Marketing Campaign** — market/copy/visual/A-B-test, iterative quality review | team + iterative review | `producer-reviewer` | `team` | `reflect-then-revise` (iterative quality) | team generate → reviewer critique → revise loop |

Coverage proof: all 3 CYS topologies hit (pipeline ×3, dispatch ×3, producer-reviewer ×2); all 3 primitive exec modes hit (agent ×2, team ×4, hybrid ×2); all 4 decision mechanisms hit (single, majority-vote available, debate-with-judge ×2, reflect-then-revise ×4). The mix is the R3 proof that produced harnesses compose ALL primitives, not just sequential sub-agents.

> **Design note on cases 4 & 5 (supervisor / dynamic dispatch).** IMPLEMENTATION-STATUS marks `dispatch(dynamic)` + supervisor dynamic allocation as M1-deferred — emit makes **static fan-out only**. So case 4's "supervisor" and case 5's "parallel fan-out" are both modeled as **static `dispatch`** (pre-assigned workers + sink), which is what the factory can actually emit today. The `expected.json` for case 4 asserts `topology=dispatch` + `uses_team_primitive` (TaskCreate shared list approximates the supervisor's dynamic feel) and explicitly does NOT assert runtime dynamic re-allocation. This keeps the eval honest against the real emit surface (no aspirational PASS).

### a.2 The PASS criterion per case (machine-checkable acceptance test)

A use case PASSES (at L-factory) iff ALL of the following hold — every clause is an exit-code or a JSON boolean, no human judgment:

```
PASS(case) :=
  C1  warrant.classify(prompt-predicates) == expected.warrant            # right verdict
  C2  graph.topology == expected.topology                                # right topology emitted
  C3  graph.execution_mode in expected.execution_mode_in                 # right primitive substrate
  C4  validate_harness.py <emitted> --json  ->  status == "pass" (exit 0)# all ~20 build-gate codes green
  C5  eval_topology.py asserts primitive_mix.* all true                  # R3: ALL-primitive composition present
        - orchestrator skill present (GRAPH_SKILL_CONSISTENCY already enforces node coverage)
        - >= agent_defs_min agent files
        - team cases: SKILL.md contains TeamCreate AND SendMessage AND TaskCreate  (NEW emit, see d/gap)
        - agent/hybrid cases: SKILL.md contains Agent(
        - settings.json wires hooks (HOOK_REGISTERED already enforces)
        - >= domain_skills_min authored domain skills, AND each authored skill's graph node
          carries authoring_decision != "inline"  (decision 5 machine-check, see below)
  C6  eval_topology.py asserts dna.* all true                            # R4 + decision 6/7
        - memory_first_class: context_guard wired (HOOK_REGISTERED) AND latest.md template present
        - qa_stack_wired == [L0,L1,L1.5,L2]: settings.json wires gate_or_block for each layer (NEW, see d/gap)
        - cross_run_memory: .harness/memory/ store dir + orchestrator P0 "consult prior runs" step
  C7  for each authored domain skill: lift_gate.score(...) decision == "register" (lift >= 0.2)   # Gate 2 wired (d)
  C8  (quota-gated lane only) h2h verdict for the case != "BASELINE-WINS" by >margin               # Gate 3
```

C1-C6 are **free** (pure Python, run every commit in CI). C7 needs the lift probe runtime (one cheap sonnet-vs-haiku probe per authored skill). C8 is the expensive live head-to-head — run on demand in the quota-gated lane, NOT per commit (P5 lesson: a single n≥5 h2h exhausts a quota window).

**The acceptance test is graded, not binary across the suite:** the factory "works" when **C1-C6 PASS for all 8** (the build-correctness bar) and **C7 PASSes for every authored skill** (registration bar). C8 is a separate, slower honesty bar (see b.4).

### a.3 Concrete per-case `expected.json` deltas (the load-bearing fields)

Only the fields that differ from the schema in a.0 are shown; everything else inherits defaults.

- **1 Deep Research** — `topology:dispatch`, `exec_mode_in:[team,hybrid]`, `agents:[researcher,fetcher,verifier,synthesizer]`, `mechanism:[reflect-then-revise]`, `uses_team_primitive:true`, `domain_skills_min:1` (the `cited-research` skill — already exists as a lift fixture). This is the dogfood case; reuse `examples/deep-research`.
- **2 Website Development** — `topology:pipeline`, `exec_mode_in:[hybrid]`, `agents:[designer,frontend,backend,qa-inspector]`, `mechanism:[reflect-then-revise]`, `dna.qa_stack_wired` MUST include L2 (the qa-guide boundary-cross QA agent is the headline feature here), `agents_must_include` requires a `qa-inspector` whose authored skill encodes the **boundary cross-compare** checklist.
- **3 Webtoon** — `topology:producer-reviewer`, `exec_mode_in:[team]`, `agents:[story-writer,char-designer,panel-planner,dialogue-editor]`, `mechanism:[debate-with-judge]` (style-consistency arbitration), `uses_team_primitive:true` (review-each-other = SendMessage loop).
- **4 YouTube** — `topology:dispatch`, `exec_mode_in:[team]`, `agents:[trend-researcher,scriptwriter,seo-optimizer,thumbnail-planner]`, supervisor synth node, `uses_team_primitive:true` (TaskCreate shared list).
- **5 Code Review** — `topology:dispatch`, `exec_mode_in:[agent]`, `agents:[arch-reviewer,security-reviewer,perf-reviewer,style-reviewer]`, sink `merge` node, `uses_subagent_primitive:true`, `uses_team_primitive:false` (this is the deliberate sub-agent-only case — proves the factory still picks sub-agents when comms are unneeded; mirrors idoforgod's own "fan-out → sub-agents" guidance).
- **6 Tech Docs** — `topology:pipeline`, `exec_mode_in:[agent]`, `agents:[endpoint-analyzer,doc-writer,example-generator,completeness-reviewer]`, `mechanism:[reflect-then-revise]` at review.
- **7 Data Pipeline** — `topology:pipeline`, `exec_mode_in:[hybrid]`, `agents:[schema-designer,etl-author,validation-author,monitoring-author]`, `mechanism:[debate-with-judge]` on schema, flattened to depth-2 (assert NO node has a child-team; hierarchical → flattened pipeline).
- **8 Marketing** — `topology:producer-reviewer`, `exec_mode_in:[team]`, `agents:[market-researcher,copywriter,visual-conceptor,abtest-planner]`, `mechanism:[reflect-then-revise]` (iterative quality review loop), `uses_team_primitive:true`.

---

## (b) PASS/FAIL DEFINITION FOR "cys-harness-creator works"

### b.1 The factory self-test runs all 8

Extend `tests/test_factory.py` (the existing factory-native suite) with a new class `TestEightUseCases`. It is **driven by the golden specs**, so adding a 9th case is data, not code.

```
class TestEightUseCases(unittest.TestCase):
    # data-driven: iterate tests/golden/usecases/*.expected.json
    def test_warrant_verdict(self, case):        # C1 — warrant.classify matches
    def test_topology_and_mode(self, case):      # C2,C3 — graph fields match (uses a frozen graph.json fixture per case)
    def test_validate_gate_clean(self, case):    # C4 — validate_harness on the frozen emitted harness -> exit 0
    def test_primitive_mix(self, case):          # C5 — eval_topology primitive_mix assertions
    def test_dna_present(self, case):            # C6 — eval_topology dna assertions
    def test_authored_skill_lift(self, case):    # C7 — lift_gate.score on the frozen probe results -> "register"
```

**Critical design choice (so CI stays pure & fast, per the existing suite's stated discipline "no genome, no live runs"):** the suite does NOT spawn agents and does NOT re-run a full genome transplant. Instead each case ships a **frozen golden harness** under `tests/golden/usecases/<case>/` containing the committed `graph.json` + emitted `SKILL.md` + `settings.json` excerpt + a frozen `lift_results.json` (the recorded output of one real probe run, committed like a VCR cassette). The tests assert the emitters/validators/matchers/scorers produce the expected verdicts **over the frozen inputs** — exactly the pattern `TestEmitDeterminism` already uses with `tests/golden/*.workflow.js`. This makes all of C1-C7 byte-deterministic and CI-safe.

### b.2 What artifacts prove each case passed

Per case, committed under `tests/golden/usecases/<case>/`:

| Artifact | Proves | Gate |
|---|---|---|
| `<case>.expected.json` | the acceptance spec (a.0) | — |
| `.harness/graph.json` | topology/mode/mechanism the factory authored | C1-C3 |
| `validate.report.json` | `{"status":"pass","errors":[]}` (frozen exit-0 proof) | C4 |
| `.claude/skills/<name>-orchestrator/SKILL.md` | full-primitive composition prose (TeamCreate/Agent/SendMessage present) | C5 |
| `.claude/settings.json` (excerpt) | genome + L0-L2 gate hooks wired | C5,C6 |
| `match.json` (from `eval_topology.py`) | every primitive_mix + dna assertion true | C5,C6 |
| `<skill>.lift_results.json` + `<skill>.lift_verdict.json` | recorded probe + `decision:"register"` | C7 |
| `evals/<case>.verdict.json` (quota lane only) | real h2h verdict (may be INCONCLUSIVE/BASELINE-WINS — honest) | C8 |

The suite asserts these are internally consistent: e.g. `validate.report.json` must be re-derivable by running `validate_harness.py` over the committed harness (so the cassette can't rot silently), and `lift_verdict.json` must equal `lift_gate.score(lift_results.json)` re-run live. **A cassette that no longer reproduces its frozen verdict fails the test** — this is the regression tripwire.

### b.3 How this becomes a CI / regression suite

- **Per-commit lane (free, blocking):** `make test` → `python3 -m unittest discover -s tests`. Runs the existing 35 inherited + factory-native classes PLUS `TestEightUseCases` C1-C7 over the frozen cassettes. Zero agent spawns, zero network, sub-second. **A red here blocks merge.** This is the "cys-harness-creator works" gate.
- **Golden-refresh lane (manual, on factory change):** when an emitter/validator/warrant rule changes intentionally, a maintainer runs `make refresh-goldens` (new Makefile target) which re-emits all 8 harnesses from their `graph.json` and re-records `validate.report.json` + `match.json`. The diff is reviewed in the PR exactly like the existing `tests/golden/*.workflow.js` byte-goldens. This is the controlled way to update expectations — never edit cassettes by hand.
- **Quota-gated head-to-head lane (manual / scheduled, non-blocking):** `make h2h CASE=deep-research` runs the live C8 head-to-head via the resumable driver (`_workspace/h2h/run_h2h.py` already exists, handles quota-reset windows + incremental save + resume — the P5 artifact). Writes `evals/<case>.verdict.json`. `validate_harness.py`'s `MEASUREMENT_DRIFT` check then guards that no doc claims CYS-WINS unless a verdict on disk shows it. **C8 is honesty-gated, not pass-gated:** a BASELINE-WINS verdict does NOT fail CI — it fails any doc that lies about it.

### b.4 The crisp PASS/FAIL definition

> **cys-harness-creator WORKS** ⟺ for all 8 golden use cases: C1-C6 PASS (build-correctness: right verdict, right topology, right primitive substrate, clean build gate, full-primitive composition present, memory+QA+cross-run DNA present) AND C7 PASS for every authored domain skill (each registered skill beats the haiku baseline by ≥0.2). 
>
> **C8 (h2h ≥ +15pp) is NOT part of the "works" definition** — per locked decision 4 the benchmark is FEATURE PARITY, not performance superiority. C8 is run for rigor and reported honestly; a non-winning verdict is recorded, never hidden, and never fabricated (the +37.5pp lesson, enforced by `MEASUREMENT_DRIFT`).

FAIL modes and their meaning: C1/C2/C3 red → warrant/topology-selection logic regressed (wrong harness for the prompt). C4 red → build gate broken or emit produced an invalid harness. C5 red → a primitive went missing (e.g. team emit silently fell back to sub-agent emit — the current gap). C6 red → DNA went dormant (e.g. L0-L2 not wired as hooks). C7 red → an authored skill is dead weight (doesn't beat haiku → should be inlined per decision 5, not registered).

---

## (c) THE FEATURE-PARITY MATRIX

Status legend (decision 4 = capability parity, form-adopt where the form IS the Claude-native mechanism):
- **has-equivalent** — CYS already has a direct mechanism (often stronger: a machine-check vs prose).
- **form-adopted** — CYS adopts idoforgod's FORM because the form is the Claude-native mechanism (esp. `.claude/skills/`, `.claude/agents/`, TeamCreate).
- **capability-via-CYS-superset** — covered by a CYS mechanism that subsumes the idoforgod feature (no 1:1 form, but the capability is present and stronger).
- **to-build** — gap; design specifies the build (these feed the backlog in d + this component).

| # | idoforgod feature (SKILL.md + 6 refs) | CYS mechanism | Status |
|---|---|---|---|
| 1 | **Agent definition generation** (`.claude/agents/*.md`) | `emit_orchestrator._write_agent_files` emits per-node agent files with runtime-enforced `model`+`tools`+`maxTurns` frontmatter | **form-adopted** (CYS adds machine-enforced tier + least-privilege tools) |
| 2 | **Skill generation** (`.claude/skills/<name>/SKILL.md`) | orchestrator SKILL emitted today; **per-node DOMAIN skill emitter** is the gap (decision 5 hybrid authoring) | **to-build** (domain-skill emitter + `authoring_decision` graph field) |
| 3 | **Agent Teams as default** (TeamCreate/SendMessage/TaskCreate) | `execution_mode:team` exists in schema + warrant cost-band; but **emit is byte-identical to agent emit — team primitives never generated** | **to-build** (real team emit) + **form-adopted** (the primitives are the native form) |
| 4 | **7 topologies** (pipeline/dispatch/fan-out-fan-in/producer-reviewer/supervisor/expert-pool/hierarchical — graph.schema.json enum) | 7 topology × 4 decision-mechanism algebra; mapping table in `architecture-patterns.md §7`. pipeline=pipeline, fan-out=dispatch, producer-reviewer=producer-reviewer, supervisor≈static dispatch, hierarchical≈flattened pipeline, expert-pool≈conditional dispatch | **capability-via-CYS-superset** (orthogonal 2-axis is strictly more expressive); supervisor-dynamic + expert-pool dynamic are **M1-deferred → to-build** |
| 5 | **Agent separation, 4 axes** (expertise/parallelism/context/reuse) | preserved verbatim in `architecture-patterns.md §10`; warrant `n_agents` cap (MAX_FANOUT=5) operationalizes it | **has-equivalent** |
| 6 | **Pushy descriptions** (active trigger phrasing + follow-up keywords) | `emit_orchestrator` stamps follow-up keywords ("다시 실행/재실행/수정/보완…") into orchestrator description; `AGENT_FRONTMATTER` gate enforces description present | **form-adopted** + machine-checked presence |
| 7 | **Progressive disclosure** (metadata/SKILL-body/references 3-tier) | `skill-writing-guide.md` preserves the doctrine; orchestrator SKILL + `references/` already structured this way; **to-build:** enforce body ≤500 lines + ToC-on-large as a gate when domain-skill emitter lands | **has-equivalent** (doctrine) + **to-build** (size gate) |
| 8 | **With/without lift test** (A/B skill value) | `lift_gate.py` — with-skill(sonnet) vs haiku baseline, blind independent grader, threshold 0.2, register/refuse exit code | **has-equivalent** (stronger: blind grader + deterministic scorer + cost-tier baseline) — currently **orphaned, see (d)** |
| 9 | **Trigger near-miss verification** (should / should-NOT, near-miss focus) | preserved in `testing-and-measurement.md §8`; **to-build:** a `trigger_eval.py` runner + genome-skill-collision check (CYS children inherit many skills → higher collision risk) | **has-equivalent** (doctrine) + **to-build** (runner) |
| 10 | **QA boundary-cross-comparison** (qa-agent-guide: "양쪽 동시 읽기", 7 real bugs, incremental QA) | `qa-guide.md` preserves the methodology; warrant can author a `qa-scan` node; **to-build:** make case-2/website emit a `qa-inspector` domain skill carrying the boundary-cross checklist as an authored skill | **form-adopted** (qa agent) + **to-build** (authored QA skill from guide) |
| 11 | **Phase 0 Status Audit** (drift detect + new/extend/maintain branch) | SKILL.md "Phase 0: 컨텍스트 확인" exists as prose; **to-build:** a real `phase0_audit.py` that reads existing `.claude/agents` + `.claude/skills` + CLAUDE.md, diffs against `graph.json`, emits new/extend/maintain verdict | **to-build** |
| 12 | **Phase 7 Harness Evolution** (feedback routing + change-history + proactive triggers) | git repo = rollback substrate (Phase 7 exists); change-history table doctrine present; **to-build:** evolution loop that routes feedback→target (skill/agent/orchestrator), appends CLAUDE.md change-history, and the **cross-run memory feeds it** (decision 7) | **to-build** |
| 13 | **CLAUDE.md pointer + change-history** (minimal pointer, not full inventory) | genome ships CLAUDE.md; **to-build:** factory appends a `## 하네스: <domain>` pointer block (trigger rule + change-history table) on emit, and Phase-7 evolution appends rows | **to-build** (emit step) |
| 14 | **Team-default decision** (team is THE default mode) | CYS DELIBERATELY DIVERGES: `agent` is default, `team` promoted only after P5 proof (cost-band + dogfood). This is a **conscious capability-parity-not-form choice** — team is fully supported (decision 3) but not blindly default | **has-equivalent** (team capability) with documented divergence on default (locked decision, not a gap) |
| 15 | **Orchestrator skill + data-passing** (Phase 5) | `emit_orchestrator` emits orchestrator SKILL naming every node (GRAPH_SKILL_CONSISTENCY gate); `_workspace/` file-passing + inputs/outputs in graph.json | **form-adopted** + machine-checked (idoforgod cannot detect prose-vs-graph drift; CYS can) |
| 16 | **Model: opus everywhere** | REJECTED by design → role→tier policy (`TIER_OVERSPEND` V2 gate). idoforgod's "all opus" is the anti-pattern CYS machine-blocks | **capability-via-CYS-superset** (deliberate improvement, not parity gap) |

**Net:** 4 has-equivalent, 4 form-adopted, 2 capability-via-CYS-superset, and **6 to-build** (#2 domain-skill emitter, #3 team emit, #4 dynamic dispatch/expert-pool, #9 trigger runner, #11 Phase-0 audit, #12/#13 Phase-7 evolution + CLAUDE.md pointer). The 6 to-build items are exactly the GAPS the prompt names, and they sequence into the backlog. **Capability parity is reached when the 6 to-build land; form is adopted wherever the form is the Claude-native primitive (agents/skills/teams).**

---

## (d) WIRING lift_gate + h2h INTO THE BUILD (currently orphaned)

Today `lift_gate.py` and `h2h_aggregate.py` are correct, tested (`TestLiftGate`, and h2h via fixtures), and **never invoked by the build** — they exist as CLI tools the SKILL.md merely mentions in Phase 7. Nothing in `emit_orchestrator.py` or `validate_harness.py` calls them, so an authored skill can be registered and a harness shipped **without ever being measured**. The wiring closes that loop.

### d.1 Lift gate → wired at skill-authoring time (Gate 2, per authored domain skill)

The trigger is the **new domain-skill emitter** (parity item #2). The rule (machine-encoded):

1. **`authoring_decision` becomes a required graph.json node field** (decision 5 made machine-checkable). Enum: `inline` | `authored`. `validate_harness.py` gains an `AUTHORING_DECISION` check: a node may be `authored` only if it declares a reason matching decision-5's criteria — `reused_by` (≥2 node ids), `large` (true), or `conditional` (true). Authoring a skill that meets none → build error (prevents skill sprawl).
2. For every `authored` node, the emitter ALSO emits a `lift_probe` skill-spec (`{name, prompt, instructions, assertions}`) derived from the node's output_schema + the case's discriminating assertions, and writes it to `evals/probes/<skill>.skill.json`.
3. **New validate check `LIFT_UNMEASURED`** (error): every `authored` node must have a committed `evals/<skill>.lift_verdict.json` whose `decision == "register"`. No verdict, or `refuse` → build fails with the message "authored skill <x> does not beat haiku baseline (lift <l> < 0.2) — inline it (set authoring_decision:inline) or strengthen it." This is the mechanism that turns lift from advisory into **a precondition of shipping an authored skill**.
4. The verdict is produced by the existing two-step flow run from a new Makefile target `make lift SKILL=<name>`: `lift_gate.py emit-probe` → runtime runs the probe (sonnet+skill vs haiku, blind opus grader) → `lift_gate.py score` → commit `lift_results.json` + `lift_verdict.json`. In CI this is the **frozen cassette** (b.1) so the per-commit lane stays free; the live run happens at authoring time in the quota lane.

Net effect: **decision 5's hybrid authoring is now enforced by lift** — you cannot author a domain skill unless it measurably earns its tier upgrade, and inlining is the cheaper default. This directly implements "every authored skill/harness is measured."

### d.2 H2H → wired at harness-completion time (Gate 3, per harness)

The trigger is **Phase 7 (git + evolution)** + the quota-gated CI lane (b.3). The wiring:

1. The emitter writes a per-harness `evals/<domain>.scorecard.json` (discriminating assertions for THIS harness — generalize the existing `deep-research.scorecard.json` template; C2=CYS harness, C3=no-harness single-opus, same output contract for fair grading).
2. A new Makefile target `make h2h CASE=<domain>` drives the resumable runner (`run_h2h.py`, already built for P5 quota-window resume) → produces `evals/<domain>.runs.json` → `h2h_aggregate.py` → `evals/<domain>.verdict.json` (median delta, variance, provenance: git_sha + harness_version + model_id).
3. **`MEASUREMENT_DRIFT` (already wired in `validate_harness.py`) is the enforcement**: it already blocks any README/SKILL doc that advertises "CYS-WINS" unless a verdict on disk shows it. We EXTEND it minimally: also block if a doc cites a specific delta_pp that disagrees with the on-disk verdict's delta_pp (the precise +37.5pp regression class). This makes h2h results **load-bearing on what the harness is allowed to claim**, even though winning is not required (decision 4).
4. The evolution loop (parity #12) reads `verdict.json`: a `BASELINE-WINS` or high-variance verdict becomes a proactive evolution trigger ("this harness underperforms — propose adding an L2 reviewer node / strengthening assertions"), and the cross-run memory (decision 7) records the verdict per run so the harness improves across runs.

### d.3 Where the two gates sit in the integrated R1 workflow

The R1 frame is **Research → Planning(=human approval) → Implementation**, with idoforgod phases nested. The two measurement gates slot in deterministically:

```
RESEARCH stage
  Phase -1 warrant (Gate 0 verdict)           [machine]
  Phase 0  status audit (parity #11)          [machine, to-build]
  Phase 1  domain analysis
PLANNING stage  (carries the human review/approval point)
  Phase 2  graph.json authoring (+ authoring_decision per node)   [single-writer]
  Phase 3  agent + schema authoring
  Phase 4  skill generation: orchestrator + AUTHORED domain skills
           └─► Gate 2  lift_gate per authored skill  (d.1, LIFT_UNMEASURED) [measure]
  Phase 5  integration & orchestration emit (team/agent/hybrid primitives)
  Phase 6a validate_harness (Gate 1, BLOCKING) + warrant cost-band (Gate 0, BLOCKING approval)  [human approves here]
IMPLEMENTATION stage
  Phase 6b run the harness as a live session (genome fires)
  Phase 7  git + evolution
           └─► Gate 3  h2h per harness  (d.2, MEASUREMENT_DRIFT)  [measure, quota-gated]
```

So **Gate 2 fires inside Planning/Phase-4** (a skill must be measured before it's registered into the plan), and **Gate 3 fires inside Implementation/Phase-7** (the completed harness is measured before it may claim superiority). Both were orphaned; both now have a machine-check (`LIFT_UNMEASURED` / `MEASUREMENT_DRIFT`) that makes the measurement a build/claim precondition rather than a suggestion.

---

## SEQUENCED BACKLOG (this component's build items, design-only)

Ordered so each item is independently shippable and unblocks the eval bar:

1. **`eval_topology.py` + 8 `expected.json` specs + frozen cassettes** → unlocks C1-C6 in CI (the "works" gate over build-correctness). *Verify: `TestEightUseCases` C1-C6 green over committed cassettes.*
2. **`authoring_decision` graph field + schema + `AUTHORING_DECISION` validate check** → makes decision 5 machine-checkable. *Verify: `test_factory` rejects an `authored` node with no qualifying reason.*
3. **Domain-skill emitter** (parity #2) → emits authored skills + their `lift_probe` specs. *Verify: a 2-node-reuse case emits one authored skill; an inline case emits none.*
4. **`LIFT_UNMEASURED` validate check + `make lift`** (d.1) → wires Gate 2 into the build. *Verify: build fails when an authored skill's verdict is `refuse`/absent.*
5. **Real team emit** (parity #3) → `emit_orchestrator` generates TeamCreate/SendMessage/TaskCreate prose for `team`/`hybrid` modes (today byte-identical to agent emit). *Verify: C5 `uses_team_primitive` true for cases 1/3/4/8.*
6. **L0-L2 + budget hooks wired as real hooks** (R4, gap) → settings.json PostToolUse runs `gate_or_block` for each layer; spawns_used incremented by hook not prose. *Verify: C6 `qa_stack_wired==[L0,L1,L1.5,L2]`.*
7. **Phase-0 audit + Phase-7 evolution + CLAUDE.md pointer/change-history** (parity #11/#12/#13) → completes the lifecycle. *Verify: re-running the factory on an existing harness yields a new/extend/maintain verdict and a change-history row.*
8. **`make h2h` quota lane + `MEASUREMENT_DRIFT` delta-pp extension** (d.2) → wires Gate 3 + claim honesty. *Verify: a doc citing a wrong delta_pp fails validate.*
9. **Cross-run RLM memory store** (decision 7) → `.harness/memory/` external store, consulted programmatically (Grep/Read, never whole-loaded), fed by each run's outputs/verdict. *Verify: orchestrator P0 reads prior-run memory; second run cites it.*

Items 1-4 are the **minimum to make the 8-case eval a real CI gate**; 5-9 close the remaining parity gaps and light up the dormant DNA.
